"""
mquery_converter.py
───────────────────
Converts parsed Qlik table definitions into Power Query M expressions
suitable for embedding in a Power BI BIM partition.

FIXES (v2):
  1. SharePoint URLs now always quoted correctly in M expressions
  2. Qlik-qualified column names (Table_Name.ColumnName) stripped to plain column name
  3. SharePoint sources always use SharePoint.Files() — no File.Contents()
  4. Composite key columns (DealerID-ServiceID) always typed as text, never integer
  5. URL passed as base_path is auto-detected as SharePoint and generates correct M
"""

from __future__ import annotations
import re
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# TYPE MAPPING
# ─────────────────────────────────────────────────────────────────────────────

_QLIK_TO_M_TYPE: Dict[str, str] = {
    "string":    "type text",
    "text":      "type text",
    "number":    "type number",
    "integer":   "Int64.Type",
    "int":       "Int64.Type",
    "float":     "type number",
    "double":    "type number",
    "decimal":   "type number",
    "currency":  "type number",
    "money":     "type number",
    "date":      "type date",
    "time":      "type time",
    "datetime":  "type datetime",
    "timestamp": "type datetime",
    "boolean":   "type logical",
    "bool":      "type logical",
    "bit":       "type logical",
    "mixed":     "type any",
    "wildcard":  "type text",
    "unknown":   "type text",
}

_QLIK_TO_M_TYPE_FOR_TABLE: Dict[str, str] = {
    "string":    "text",
    "text":      "text",
    "number":    "number",
    "integer":   "Int64.Type",
    "int":       "Int64.Type",
    "float":     "number",
    "double":    "number",
    "decimal":   "number",
    "currency":  "number",
    "money":     "number",
    "date":      "date",
    "time":      "time",
    "datetime":  "datetime",
    "timestamp": "datetime",
    "boolean":   "logical",
    "bool":      "logical",
    "bit":       "logical",
    "mixed":     "any",
    "wildcard":  "text",
    "unknown":   "text",
}

_DEFAULT_M_TYPE = "type text"
_DEFAULT_M_TYPE_FOR_TABLE = "text"


def _m_type(qlik_type: str, col_name: str = "") -> str:
    """M type with 'type' prefix — for TransformColumnTypes.

    Rules:
    - Composite key columns (containing '-') → always text (e.g. DealerID-ServiceID)
    - All other columns → use inferred Qlik type mapped to M type
    - Dot-qualified names handled before this call by _strip_qlik_qualifier
    """
    # Composite key columns always text (Power BI can't use them as keys otherwise)
    if "-" in col_name:
        return "type text"
    return _QLIK_TO_M_TYPE.get(str(qlik_type).lower().strip(), _DEFAULT_M_TYPE)


def _m_type_for_table(qlik_type: str, col_name: str = "") -> str:
    """M type WITHOUT 'type' prefix — for #table() column signatures."""
    if "-" in col_name:
        return "text"
    return _QLIK_TO_M_TYPE_FOR_TABLE.get(str(qlik_type).lower().strip(), _DEFAULT_M_TYPE_FOR_TABLE)


def _normalize_path(path: str) -> str:
    """Strip lib:// prefix from Qlik source paths."""
    path = re.sub(r"^lib://[^/]*/", "", path)
    path = re.sub(r"^lib://", "", path)
    return path


def _sanitize_col_name(name: str) -> str:
    if re.match(r"^[A-Za-z_][A-Za-z0-9_ ]*$", name):
        return name
    return f'#"{name}"'


def _strip_qlik_qualifier(col_name: str) -> str:
    """
    Strip Qlik table-qualified prefix from column name.
    
    'Dealer_Master.City_GeoInfo'  →  'City_GeoInfo'
    'Model_Master.ModelID'        →  'ModelID'
    'DealerID-ServiceID'          →  'DealerID-ServiceID'  (composite key, keep as-is)
    '#"Something"'                →  '#"Something"'        (already escaped)
    
    This is critical because the actual CSV column is just 'City_GeoInfo',
    not the Qlik-qualified 'Dealer_Master.City_GeoInfo'.
    """
    if not col_name or col_name.startswith("#"):
        return col_name
    # Only strip the prefix if there's a dot AND no hyphen (composite keys keep their name)
    if "." in col_name and "-" not in col_name:
        return col_name.split(".", 1)[-1]
    return col_name


def _is_sharepoint_url(url: str) -> bool:
    """Check if a URL is a SharePoint URL."""
    cleaned = url.strip().strip('"').strip("'")
    return "sharepoint.com" in cleaned.lower()


def _quote_url(url: str) -> str:
    """Ensure a URL is properly quoted for M expressions."""
    cleaned = url.strip().strip('"').strip("'")
    return f'"{cleaned}"'


# ─────────────────────────────────────────────────────────────────────────────
# SHAREPOINT M QUERY BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_sharepoint_m(
    site_url: str,
    filename: str,
    folder_path: str,
    delimiter: str,
    encoding: int,
    transform_step: str,
    final_step: str,
    is_qvd: bool = False,
) -> str:
    """
    Build a correct SharePoint.Files() M expression.
    
    This is the ONLY correct way to read files from SharePoint in Power BI:
      1. SharePoint.Files(site_url) — lists all files in the site
      2. Table.SelectRows — filter by folder path AND filename
      3. FileBinary — get the file binary content
      4. Csv.Document — parse as CSV
      5. Table.PromoteHeaders — promote first row as headers
      6. Table.TransformColumnTypes — apply data types
    
    The site_url must be properly quoted as a string literal.
    The folder_path must end with a trailing slash.
    """
    qvd_comment = "    // QVD converted to CSV — SharePoint.Files() reads the CSV version\n" if is_qvd else ""
    
    # Extract the folder NAME from folder_path for Text.Contains filter
    # folder_path examples:
    #   "https://site.sharepoint.com/sites/ddrive/CSVFilesDatas/"  -> "CSVFilesDatas"
    #   "https://site.sharepoint.com/sites/ddrive/SchoolFiles/"    -> "SchoolFiles"
    #   "https://site.sharepoint.com/sites/ddrive/"                -> use site name as fallback
    folder_name = folder_path.rstrip("/").rsplit("/", 1)[-1] if folder_path else ""
    if not folder_name or folder_name == site_url.rstrip("/").rsplit("/", 1)[-1]:
        # folder_path points to root — no subfolder filter, just match filename
        folder_filter = f"        each Text.Lower([Name]) = Text.Lower(\"{filename}\")"
    else:
        folder_filter = (
            f"        each Text.Contains([#\"Folder Path\"], \"{folder_name}\")\n"
            f"             and Text.Lower([Name]) = Text.Lower(\"{filename}\")"
        )

    m = (
        f"let\n"
        f"{qvd_comment}"
        f"    Source = SharePoint.Files(\n"
        f"        \"{site_url}\",\n"
        f"        [ApiVersion = 15]\n"
        f"    ),\n"
        f"    FilteredFile = Table.SelectRows(\n"
        f"        Source,\n"
        f"{folder_filter}\n"
        f"    ),\n"
        f"    FileBinary = FilteredFile{{0}}[Content],\n"
        f"    CsvData = Csv.Document(\n"
        f"        FileBinary,\n"
        f"        [Delimiter=\"{delimiter}\", Encoding={encoding}, QuoteStyle=QuoteStyle.Csv]\n"
        f"    ),\n"
        f"    PromotedHeaders = Table.PromoteHeaders(CsvData, [PromoteAllScalars=true])"
        f"{transform_step}\n"
        f"in\n"
        f"    {final_step}"
    )
    return m


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CONVERTER
# ─────────────────────────────────────────────────────────────────────────────

class MQueryConverter:

    # ============================================================
    # PUBLIC
    # ============================================================

    def convert_all(
        self,
        tables: List[Dict[str, Any]],
        base_path: str = "[DataSourcePath]",
        connection_string: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        results = []

        for table in tables:
            m_expr, notes = self._dispatch(table, base_path, connection_string)
            results.append({
                "name":         table["name"],
                "source_type":  table["source_type"],
                "m_expression": m_expr,
                "fields":       table["fields"],
                "notes":        notes,
                "source_path":  table.get("source_path", ""),
                "options":      table.get("options", {}),
            })

        logger.info("[MQueryConverter] Converted %d table(s)", len(results))
        return results

    def convert_one(
        self,
        table: Dict[str, Any],
        base_path: str = "[DataSourcePath]",
        connection_string: Optional[str] = None,
        all_table_names: Optional[set] = None,
    ) -> str:
        m_expr, _ = self._dispatch(table, base_path, connection_string)
        return m_expr

    # ============================================================
    # DISPATCH
    # ============================================================

    def _dispatch(self, table, base_path, connection_string):
        dispatch = {
            "inline":   self._m_inline,
            "csv":      self._m_csv,
            "excel":    self._m_excel,
            "json":     self._m_json,
            "xml":      self._m_xml,
            "parquet":  self._m_parquet,
            "qvd":      self._m_qvd,
            "resident": self._m_resident,
            "sql":      self._m_sql,
        }
        handler = dispatch.get(table.get("source_type"), self._m_placeholder)
        try:
            return handler(table, base_path, connection_string)
        except Exception as exc:
            logger.warning("[MQuery] Error converting '%s': %s", table.get("name"), exc)
            return self._m_placeholder(table, base_path, connection_string), f"Conversion error: {exc}"

    # ============================================================
    # SHARED TYPE TRANSFORM STEP
    # ============================================================

    def _apply_types(self, fields: List[Dict], previous_step: str):
        """
        Returns (transform_step_str, final_step_name).

        FIX: Use the ORIGINAL CSV column name, not the Qlik alias.

        Rules:
        1. If field has a simple [FieldName] or FieldName expression:
           - CSV column is the ORIGINAL name (expression), not the alias
           - e.g. [DealerID] AS [DealerID-ServiceID] -> use DealerID (in CSV)
        2. If field has a complex expression (APPLYMAP, functions, etc.):
           - This is Qlik-computed, not in the CSV -> SKIP it
        3. Strip Qlik table-qualified prefixes (Table.Column -> Column)
        4. Composite key columns (containing -) always typed as text
        5. Datatype is properly mapped from Qlik inferred type
        """
        typed = [f for f in fields if f.get("name") not in ("*", "")]
        if not typed:
            return "", previous_step

        pairs = []
        seen_cols = set()
        for f in typed:
            expr      = f.get("expression", "") or ""
            alias     = f.get("alias") or ""
            field_name = f.get("name", "")

            # Determine if this is a simple column reference or computed expression
            expr_clean = expr.strip()
            is_simple_col = (
                # [FieldName] bracket style
                (expr_clean.startswith("[") and expr_clean.endswith("]"))
                # PlainFieldName no spaces/operators
                or re.match(r"^[A-Za-z_][A-Za-z0-9_.]*$", expr_clean)
                # Empty expression = direct field reference
                or not expr_clean
            )

            if is_simple_col:
                # Use the ORIGINAL field name from CSV (strip brackets)
                if expr_clean.startswith("[") and expr_clean.endswith("]"):
                    csv_col = expr_clean[1:-1]
                elif expr_clean:
                    csv_col = expr_clean
                else:
                    # Fallback: use alias stripped, then name stripped
                    csv_col = _strip_qlik_qualifier(alias or field_name)
            else:
                # Complex expression (APPLYMAP, functions, arithmetic)
                # This column does NOT exist in the CSV file — skip it
                logger.debug("[apply_types] Skipping computed field: %s expr=%s", field_name, expr_clean[:60])
                continue

            # Strip Qlik table-qualified prefix e.g. Dealer_Master.City -> City
            csv_col = _strip_qlik_qualifier(csv_col)

            if not csv_col or csv_col in seen_cols:
                continue
            seen_cols.add(csv_col)

            # Get correct M datatype
            m_type = _m_type(f.get("type", "string"), csv_col)
            pairs.append(f'{{"{csv_col}", {m_type}}}')

        if not pairs:
            return "", previous_step

        pairs_str = ",\n        ".join(pairs)
        transform = (
            f",\n"
            f"    TypedTable = Table.TransformColumnTypes(\n"
            f"        {previous_step},\n"
            f"        {{\n        {pairs_str}\n        }}\n"
            f"    )"
        )
        return transform, "TypedTable"

    # ============================================================
    # SHAREPOINT URL HELPERS
    # ============================================================

    def _get_sharepoint_parts(self, base_path: str, source_path: str, opts: dict):
        """
        Extract SharePoint site URL, folder path, and filename from inputs.

        Priority for folder selection:
          1. opts["sp_subfolder"]      — user selected from Browse dropdown (e.g. "CSVFilesDatas")
          2. opts["sharepoint_folder"] — alternative key for same
          3. source_path has a /      — extract folder from the path
          4. No folder info            — use root (no subfolder filter)

        Returns (site_url, folder_path, filename) all as plain strings (unquoted).
        """
        site_url = base_path.strip().strip('"').strip("'").rstrip("/")

        # Priority 1 & 2: user-selected folder from UI Browse dropdown
        sp_subfolder = (
            opts.get("sp_subfolder", "").strip()
            or opts.get("sharepoint_folder", "").strip()
        )

        if sp_subfolder:
            # User explicitly chose a folder — use it directly
            folder_path = f"{site_url}/{sp_subfolder.strip('/')}/"
        elif "/" in source_path:
            # Priority 3: extract from source_path (e.g. "Data/marks.csv" -> "Data")
            folder_part = source_path.rsplit("/", 1)[0]
            folder_path = f"{site_url}/{folder_part}/"
        else:
            # Priority 4: no folder info — root level, no subfolder filter
            folder_path = f"{site_url}/"

        # Determine filename
        filename = source_path.rsplit("/", 1)[-1] if "/" in source_path else source_path
        if not filename:
            table_name = opts.get("table_name", "Table")
            filename = f"{table_name}.csv"

        return site_url, folder_path, filename

    # ============================================================
    # INLINE
    # ============================================================

    def _m_inline(self, table, base_path, _cs):
        opts   = table.get("options", {})
        fields = table["fields"]

        headers = opts.get(
            "inline_headers",
            [f["name"] for f in fields if f["name"] != "*"]
        )
        rows = opts.get("inline_sample", [])

        # Column type defs — NO "type" prefix inside #table() signature
        type_defs = ", ".join(
            f"{_sanitize_col_name(h)} = "
            f"{_m_type_for_table(next((f['type'] for f in fields if f['name'] == h), 'string'), h)}"
            for h in headers
        )

        # Build data rows
        row_strs = []
        for row in rows:
            vals = []
            for h in headers:
                v = str(row.get(h, ""))
                v = v.strip("'")
                v = v.replace('"', '""')
                v = v.replace("\n", " ")
                v = v.replace("\r", "")
                v = " ".join(v.split())
                vals.append(f'"{v}"')
            row_strs.append("{" + ", ".join(vals) + "}")

        rows_m = (
            "{\n        " + ",\n        ".join(row_strs) + "\n    }"
            if row_strs else "{}"
        )

        # Safety: ensure no row spans multiple lines
        rows_m = re.sub(r',\s*\n\s*"', ', "', rows_m)

        m = (
            f"let\n"
            f"    Source = #table(\n"
            f"        type table [{type_defs}],\n"
            f"        {rows_m}\n"
            f"    )\n"
            f"in\n"
            f"    Source"
        )
        return m, f"Inline table with {len(rows)} row(s). Data embedded directly."

    # ============================================================
    # CSV
    # ============================================================

    def _m_csv(self, table, base_path, _cs):
        path   = _normalize_path(table.get("source_path", ""))
        fields = table["fields"]
        opts   = table.get("options", {})

        delimiter = opts.get("delimiter", ",")
        encoding  = 65001
        enc_str   = opts.get("encoding", "")
        if enc_str:
            enc_map = {"UTF-8": 65001, "UTF8": 65001, "UTF-16": 1200, "UTF16": 1200}
            encoding = enc_map.get(enc_str.upper().replace("-", ""), encoding)

        transform, final = self._apply_types(fields, "PromotedHeaders")

        # ── SharePoint: use SharePoint.Files() (correct, cloud-safe) ──
        if _is_sharepoint_url(base_path):
            opts["table_name"] = table.get("name", "Table")
            site_url, folder_path, filename = self._get_sharepoint_parts(base_path, path, opts)

            m = _build_sharepoint_m(
                site_url=site_url,
                filename=filename,
                folder_path=folder_path,
                delimiter=delimiter,
                encoding=encoding,
                transform_step=transform,
                final_step=final,
            )
        else:
            # Local/on-prem: use File.Contents()
            if base_path.strip().startswith("["):
                # It's a parameter reference like [DataSourcePath]
                path_expr = f"{base_path} & \"/{path}\""
            else:
                clean_bp = base_path.strip().strip('"').strip("'")
                path_expr = f'"{clean_bp}/{path}"'

            m = (
                f"let\n"
                f"    FilePath = {path_expr},\n"
                f"    Source = Csv.Document(\n"
                f"        File.Contents(FilePath),\n"
                f"        [Delimiter=\"{delimiter}\", Encoding={encoding}, QuoteStyle=QuoteStyle.Csv]\n"
                f"    ),\n"
                f"    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true])"
                f"{transform}\n"
                f"in\n"
                f"    {final}"
            )
        return m, f"CSV source: {path}"

    # ============================================================
    # EXCEL
    # ============================================================

    def _m_excel(self, table, base_path, _cs):
        path   = _normalize_path(table.get("source_path", ""))
        sheet  = table.get("options", {}).get("sheet", "Sheet1")
        fields = table["fields"]

        transform, final = self._apply_types(fields, "PromotedHeaders")

        if _is_sharepoint_url(base_path):
            opts = table.get("options", {})
            opts["table_name"] = table.get("name", "Table")
            site_url, folder_path, filename = self._get_sharepoint_parts(base_path, path, opts)

            m = (
                f"let\n"
                f"    Source = SharePoint.Files(\n"
                f"        \"{site_url}\",\n"
                f"        [ApiVersion = 15]\n"
                f"    ),\n"
                f"    FilteredFile = Table.SelectRows(\n"
                f"        Source,\n"
                f"        each Text.Contains([#\"Folder Path\"], \"{folder_path.rstrip(chr(47)).rsplit(chr(47),1)[-1]}\")\n"
                f"             and Text.Lower([Name]) = Text.Lower(\"{filename}\")\n"
                f"    ),\n"
                f"    FileBinary = FilteredFile{{0}}[Content],\n"
                f"    ExcelData = Excel.Workbook(FileBinary, null, true),\n"
                f"    SheetData = ExcelData{{[Item=\"{sheet}\", Kind=\"Sheet\"]}}[Data],\n"
                f"    PromotedHeaders = Table.PromoteHeaders(SheetData, [PromoteAllScalars=true])"
                f"{transform}\n"
                f"in\n"
                f"    {final}"
            )
        else:
            if base_path.strip().startswith("["):
                path_expr = f"{base_path} & \"/{path}\""
            else:
                clean_bp = base_path.strip().strip('"').strip("'")
                path_expr = f'"{clean_bp}/{path}"'

            m = (
                f"let\n"
                f"    FilePath = {path_expr},\n"
                f"    Source = Excel.Workbook(File.Contents(FilePath), null, true),\n"
                f"    SheetData = Source{{[Item=\"{sheet}\", Kind=\"Sheet\"]}}[Data],\n"
                f"    PromotedHeaders = Table.PromoteHeaders(SheetData, [PromoteAllScalars=true])"
                f"{transform}\n"
                f"in\n"
                f"    {final}"
            )
        return m, f"Excel source: {path}, sheet: {sheet}"

    # ============================================================
    # JSON
    # ============================================================

    def _m_json(self, table, base_path, _cs):
        path   = _normalize_path(table.get("source_path", ""))
        fields = table["fields"]

        expand_cols = [_strip_qlik_qualifier(f.get("alias") or f["name"]) for f in fields if f["name"] != "*"]
        col_list    = ", ".join(f'"{c}"' for c in expand_cols)

        transform, final = self._apply_types(fields, "Expanded")

        if _is_sharepoint_url(base_path):
            opts = table.get("options", {})
            opts["table_name"] = table.get("name", "Table")
            site_url, folder_path, filename = self._get_sharepoint_parts(base_path, path, opts)

            m = (
                f"let\n"
                f"    Source = SharePoint.Files(\n"
                f"        \"{site_url}\",\n"
                f"        [ApiVersion = 15]\n"
                f"    ),\n"
                f"    FilteredFile = Table.SelectRows(\n"
                f"        Source,\n"
                f"        each Text.Contains([#\"Folder Path\"], \"{folder_path.rstrip(chr(47)).rsplit(chr(47),1)[-1]}\")\n"
                f"             and Text.Lower([Name]) = Text.Lower(\"{filename}\")\n"
                f"    ),\n"
                f"    FileBinary = FilteredFile{{0}}[Content],\n"
                f"    Source2 = Json.Document(FileBinary),\n"
                f"    ToTable = Table.FromList(Source2, Splitter.SplitByNothing(), null, null, ExtraValues.Error),\n"
                f"    Expanded = Table.ExpandRecordColumn(ToTable, \"Column1\",\n"
                f"        {{{col_list}}},\n"
                f"        {{{col_list}}}\n"
                f"    )"
                f"{transform}\n"
                f"in\n"
                f"    {final}"
            )
        else:
            if base_path.strip().startswith("["):
                path_expr = f"{base_path} & \"/{path}\""
            else:
                clean_bp = base_path.strip().strip('"').strip("'")
                path_expr = f'"{clean_bp}/{path}"'

            m = (
                f"let\n"
                f"    FilePath = {path_expr},\n"
                f"    Source = Json.Document(File.Contents(FilePath)),\n"
                f"    ToTable = Table.FromList(Source, Splitter.SplitByNothing(), null, null, ExtraValues.Error),\n"
                f"    Expanded = Table.ExpandRecordColumn(ToTable, \"Column1\",\n"
                f"        {{{col_list}}},\n"
                f"        {{{col_list}}}\n"
                f"    )"
                f"{transform}\n"
                f"in\n"
                f"    {final}"
            )
        return m, f"JSON source: {path}. Assumes array of records at root level."

    # ============================================================
    # XML
    # ============================================================

    def _m_xml(self, table, base_path, _cs):
        path   = _normalize_path(table.get("source_path", ""))
        fields = table["fields"]

        transform, final = self._apply_types(fields, "Source")

        if _is_sharepoint_url(base_path):
            opts = table.get("options", {})
            opts["table_name"] = table.get("name", "Table")
            site_url, folder_path, filename = self._get_sharepoint_parts(base_path, path, opts)

            m = (
                f"let\n"
                f"    Source = SharePoint.Files(\n"
                f"        \"{site_url}\",\n"
                f"        [ApiVersion = 15]\n"
                f"    ),\n"
                f"    FilteredFile = Table.SelectRows(\n"
                f"        Source,\n"
                f"        each Text.Contains([#\"Folder Path\"], \"{folder_path.rstrip(chr(47)).rsplit(chr(47),1)[-1]}\")\n"
                f"             and Text.Lower([Name]) = Text.Lower(\"{filename}\")\n"
                f"    ),\n"
                f"    FileBinary = FilteredFile{{0}}[Content],\n"
                f"    Source2 = Xml.Tables(FileBinary)"
                f"{transform}\n"
                f"in\n"
                f"    {final}"
            )
        else:
            if base_path.strip().startswith("["):
                path_expr = f"{base_path} & \"/{path}\""
            else:
                clean_bp = base_path.strip().strip('"').strip("'")
                path_expr = f'"{clean_bp}/{path}"'

            m = (
                f"let\n"
                f"    FilePath = {path_expr},\n"
                f"    Source = Xml.Tables(File.Contents(FilePath))"
                f"{transform}\n"
                f"in\n"
                f"    {final}"
            )
        return m, f"XML source: {path}. Review nested table expansion manually."

    # ============================================================
    # PARQUET
    # ============================================================

    def _m_parquet(self, table, base_path, _cs):
        path   = _normalize_path(table.get("source_path", ""))
        fields = table["fields"]

        transform, final = self._apply_types(fields, "Source")

        if _is_sharepoint_url(base_path):
            opts = table.get("options", {})
            opts["table_name"] = table.get("name", "Table")
            site_url, folder_path, filename = self._get_sharepoint_parts(base_path, path, opts)

            m = (
                f"let\n"
                f"    Source = SharePoint.Files(\n"
                f"        \"{site_url}\",\n"
                f"        [ApiVersion = 15]\n"
                f"    ),\n"
                f"    FilteredFile = Table.SelectRows(\n"
                f"        Source,\n"
                f"        each Text.Contains([#\"Folder Path\"], \"{folder_path.rstrip(chr(47)).rsplit(chr(47),1)[-1]}\")\n"
                f"             and Text.Lower([Name]) = Text.Lower(\"{filename}\")\n"
                f"    ),\n"
                f"    FileBinary = FilteredFile{{0}}[Content],\n"
                f"    Source2 = Parquet.Document(FileBinary)"
                f"{transform}\n"
                f"in\n"
                f"    {final}"
            )
        else:
            if base_path.strip().startswith("["):
                path_expr = f"{base_path} & \"/{path}\""
            else:
                clean_bp = base_path.strip().strip('"').strip("'")
                path_expr = f'"{clean_bp}/{path}"'

            m = (
                f"let\n"
                f"    FilePath = {path_expr},\n"
                f"    Source = Parquet.Document(File.Contents(FilePath))"
                f"{transform}\n"
                f"in\n"
                f"    {final}"
            )
        return m, f"Parquet source: {path}."

    # ============================================================
    # QVD (CSV fallback — SharePoint version reads pre-converted CSV)
    # ============================================================

    def _m_qvd(self, table, base_path, _cs):
        path     = _normalize_path(table.get("source_path", ""))
        csv_path = re.sub(r"\.qvd$", ".csv", path, flags=re.IGNORECASE)
        fields   = table["fields"]
        opts     = table.get("options", {})

        transform, final = self._apply_types(fields, "PromotedHeaders")

        if _is_sharepoint_url(base_path):
            opts["table_name"] = table.get("name", "Table")
            site_url, folder_path, filename = self._get_sharepoint_parts(base_path, csv_path, opts)
            # Ensure filename has .csv extension
            if not filename.lower().endswith(".csv"):
                filename = re.sub(r"\.qvd$", ".csv", filename, flags=re.IGNORECASE)

            m = _build_sharepoint_m(
                site_url=site_url,
                filename=filename,
                folder_path=folder_path,
                delimiter=",",
                encoding=65001,
                transform_step=transform,
                final_step=final,
                is_qvd=True,
            )
        else:
            if base_path.strip().startswith("["):
                path_expr = f"{base_path} & \"/{csv_path}\""
            else:
                clean_bp = base_path.strip().strip('"').strip("'")
                path_expr = f'"{clean_bp}/{csv_path}"'

            m = (
                f"let\n"
                f"    // QVD not supported natively — expects pre-converted CSV\n"
                f"    FilePath = {path_expr},\n"
                f"    Source = Csv.Document(\n"
                f"        File.Contents(FilePath),\n"
                f"        [Delimiter=\",\", Encoding=65001]\n"
                f"    ),\n"
                f"    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true])"
                f"{transform}\n"
                f"in\n"
                f"    {final}"
            )
        return m, f"QVD fallback (pre-convert to CSV): {path}"

    # ============================================================
    # RESIDENT
    # ============================================================

    def _m_resident(self, table, base_path, _cs):
        source_table = table.get("source_path", "UnknownTable")
        fields       = table["fields"]

        # Strip Qlik-qualified names for column selection
        selected = [
            _strip_qlik_qualifier(f.get("alias") or f["name"])
            for f in fields if f["name"] != "*"
        ]

        if selected:
            select_step = (
                f",\n    Selected = Table.SelectColumns({source_table},\n"
                f"        {{{', '.join(chr(34) + c + chr(34) for c in selected)}}}\n"
                f"    )"
            )
            intermediate = "Selected"
        else:
            select_step = ""
            intermediate = source_table

        transform, final = self._apply_types(fields, intermediate)

        m = (
            f"let\n"
            f"    // References another Power BI query: {source_table}\n"
            f"    {source_table} = {source_table}"
            f"{select_step}"
            f"{transform}\n"
            f"in\n"
            f"    {final}"
        )
        return m, f"RESIDENT load from '{source_table}'."

    # ============================================================
    # SQL
    # ============================================================

    def _m_sql(self, table, base_path, connection_string):
        source_table = table.get("source_path", "dbo.UnknownTable")
        fields       = table["fields"]
        conn         = connection_string or "[OdbcConnectionString]"

        selected = [
            _strip_qlik_qualifier(f.get("alias") or f["name"])
            for f in fields if f["name"] != "*"
        ]
        col_list = ", ".join(f"[{c}]" for c in selected) if selected else "*"

        transform, final = self._apply_types(fields, "Source")

        m = (
            f"let\n"
            f"    ConnectionString = {conn},\n"
            f"    Source = Odbc.Query(\n"
            f"        ConnectionString,\n"
            f"        \"SELECT {col_list} FROM {source_table}\"\n"
            f"    )"
            f"{transform}\n"
            f"in\n"
            f"    {final}"
        )
        return m, f"SQL/ODBC source: {source_table}."

    # ============================================================
    # PLACEHOLDER
    # ============================================================

    def _m_placeholder(self, table, base_path, _cs):
        fields = table["fields"]

        type_defs = ", ".join(
            f"{_sanitize_col_name(_strip_qlik_qualifier(f.get('alias') or f['name']))} = "
            f"{_m_type(f.get('type', 'string'), f.get('alias') or f['name'])}"
            for f in fields if f["name"] != "*"
        ) or "Column1 = type text"

        m = (
            f"let\n"
            f"    // Placeholder — source type '{table.get('source_type', 'unknown')}' not auto-converted.\n"
            f"    // Original load: {table.get('source_path', 'N/A')}\n"
            f"    Source = #table(\n"
            f"        type table [{type_defs}],\n"
            f"        {{}}\n"
            f"    )\n"
            f"in\n"
            f"    Source"
        )
        return m, f"Source type '{table.get('source_type')}' requires manual configuration."


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE
# ─────────────────────────────────────────────────────────────────────────────

def convert_to_mquery(
    tables: List[Dict[str, Any]],
    base_path: str = "[DataSourcePath]",
    connection_string: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Convert parsed Qlik tables to M expressions."""
    return MQueryConverter().convert_all(tables, base_path, connection_string)
