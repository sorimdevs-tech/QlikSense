"""
migration_api_convert_patch.py
───────────────────────────────
INSTRUCTIONS: In your migration_api.py, find the section starting with:

    @router.post("/convert-to-mquery")
    async def convert_to_mquery_endpoint(

Replace EVERYTHING from that decorator down to (and including) the
closing `except Exception as exc:` block with the code below.

Also add this import near the top of migration_api.py (after the existing imports):

    from pydantic import BaseModel as _PydanticBase
    from typing import Optional as _Optional

Or just add these two lines near the top of the file with the other imports.
"""

# ── ADD THESE NEAR THE TOP OF migration_api.py ──────────────────────────────
# from pydantic import BaseModel as _PydanticBase
# from typing import Optional as _Optional

# ── REPLACE THE ENTIRE /convert-to-mquery ENDPOINT WITH THIS ────────────────

import json
import os
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, Query
from pydantic import BaseModel


class _ConvertBody(BaseModel):
    """POST body for /convert-to-mquery — carries the large parsed_script_json."""
    parsed_script_json: Optional[str] = None


# ---------------------------------------------------------------------------
# POST /convert-to-mquery
# ---------------------------------------------------------------------------
# NOTE: Copy this entire function (including the @router.post decorator)
#       into migration_api.py, replacing the old convert_to_mquery_endpoint.
# ---------------------------------------------------------------------------

# @router.post("/convert-to-mquery")   ← keep your existing decorator
async def convert_to_mquery_endpoint(
    body: Optional[_ConvertBody] = None,
    # parsed_script_json moved to BODY — keep as optional query param for
    # backwards compatibility with any tooling that still uses query params
    parsed_script_json_q: str = Query(
        "", alias="parsed_script_json",
        description="Full parse result JSON (prefer sending in POST body for large scripts)"
    ),
    table_name:         str = Query("", description="Specific table to convert (empty = all tables)"),
    base_path:          str = Query("[DataSourcePath]", description="Base path / SharePoint URL for file sources"),
    connection_string:  str = Query("", description="ODBC connection string for SQL sources"),
):
    """
    Phase 6: Convert parsed LoadScript to Power Query M expressions.

    parsed_script_json can be sent as:
      1. POST body JSON: {"parsed_script_json": "..."}   ← PREFERRED (no URL length limit)
      2. Query parameter: ?parsed_script_json=...         ← legacy, may fail for large scripts

    Returns M Query for the requested table plus any upstream dependency queries.
    If table_name is empty, returns M expressions for ALL tables.

    base_path: pass your SharePoint site URL here (e.g. https://company.sharepoint.com/sites/data)
               The converter will automatically use SharePoint.Files() instead of File.Contents().
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("[convert_to_mquery_endpoint] ENDPOINT: /convert-to-mquery")
    logger.info("[convert_to_mquery_endpoint] Table: %s | base_path: %s", table_name or "(all)", base_path)
    logger.info("=" * 80)

    # ── Resolve parsed_script_json: POST body takes priority over query param ──
    resolved_json = (
        (body.parsed_script_json if body and body.parsed_script_json else None)
        or parsed_script_json_q
        or ""
    )
    if not resolved_json.strip():
        raise HTTPException(
            status_code=400,
            detail=(
                "parsed_script_json is required. "
                "Send it in the POST body as JSON: {\"parsed_script_json\": \"...\"} "
                "or as a query parameter (not recommended for large scripts)."
            )
        )

    # ── 1. Parse the JSON payload ────────────────────────────────────────────
    try:
        parse_result: Dict[str, Any] = json.loads(resolved_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in parsed_script_json: {exc}")

    # ── 2. Extract tables list ───────────────────────────────────────────────
    tables: List[Dict[str, Any]] = (
        parse_result.get("details", {}).get("tables", [])
        or parse_result.get("tables", [])
    )
    raw_script: str = parse_result.get("raw_script", "")

    if not tables and not raw_script:
        raise HTTPException(
            status_code=400,
            detail="No tables found in parsed_script_json. Re-run /parse-loadscript first."
        )

    # ── 3. Convert using MQueryConverter ────────────────────────────────────
    try:
        from mquery_converter import MQueryConverter
        converter = MQueryConverter()
        all_table_names = {t["name"] for t in tables}

        if table_name:
            # Single-table mode
            target = next(
                (t for t in tables if t["name"] == table_name),
                None
            )
            if not target:
                # Case-insensitive fallback
                target = next(
                    (t for t in tables if t["name"].lower() == table_name.lower()),
                    None
                )
            if not target:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Table '{table_name}' not found. "
                        f"Available tables: {sorted(all_table_names)}"
                    )
                )

            m_expr = converter.convert_one(
                target,
                base_path=base_path,
                connection_string=connection_string or None,
                all_table_names=all_table_names,
            )

            # For RESIDENT tables, include the source table's M as a dependency
            dep_queries: Dict[str, str] = {}
            if target.get("source_type") == "resident":
                src_name = target.get("source_path", "")
                src_table = next((t for t in tables if t["name"] == src_name), None)
                if src_table:
                    dep_queries[src_name] = converter.convert_one(
                        src_table,
                        base_path=base_path,
                        connection_string=connection_string or None,
                        all_table_names=all_table_names,
                    )

            resident_note = (
                f" [!] RESIDENT table -- also include '{target.get('source_path')}' query in your dataset."
                if target.get("source_type") == "resident" else ""
            )

            logger.info(
                "[convert_to_mquery_endpoint] [OK] Converted table '%s' [%s]",
                table_name, target.get("source_type", "")
            )

            return {
                "status":             "success",
                "table_name":         table_name,
                "source_type":        target.get("source_type", "unknown"),
                "m_query":            m_expr,
                "query_length":       len(m_expr),
                "dependency_queries": dep_queries,
                "message":            f"M Query generated for '{table_name}'.{resident_note}",
                "statistics": {
                    "total_tables_available": len(tables),
                    "resident_dependencies":  len(dep_queries),
                },
            }

        else:
            # All-tables mode — convert every table
            all_converted = converter.convert_all(
                tables,
                base_path=base_path,
                connection_string=connection_string or None,
            )

            # Build a combined M script: each table as a named section
            parts = []
            for item in all_converted:
                parts.append(
                    f"// \n"
                    f"// Table: {item['name']}  [{item['source_type']}]\n"
                    f"// \n"
                    f"{item['m_expression']}"
                )
            combined_m = "\n\n".join(parts)

            resident_tables = [t for t in all_converted if t["source_type"] == "resident"]

            logger.info(
                "[convert_to_mquery_endpoint] [OK] Converted %d tables (%d RESIDENT)",
                len(all_converted), len(resident_tables)
            )

            return {
                "status":       "success",
                "table_name":   "",
                "m_query":      combined_m,
                "query_length": len(combined_m),
                "all_tables":   all_converted,
                "message":      (
                    f"M Query generated for all {len(all_converted)} table(s)."
                    + (
                        f" Note: {len(resident_tables)} RESIDENT table(s) -- "
                        "ensure all source queries are included in your dataset."
                        if resident_tables else ""
                    )
                ),
                "statistics": {
                    "total_tables_converted":    len(all_converted),
                    "total_fields_converted":    sum(len(t.get("fields", [])) for t in tables),
                    "resident_tables":           len(resident_tables),
                },
            }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[convert_to_mquery_endpoint] Conversion failed")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {exc}")