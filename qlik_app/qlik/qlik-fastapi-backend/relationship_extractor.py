# """
# Relationship Extractor for Qlik → Power BI Migration

# How Qlik handles relationships vs. how Power BI needs them:

#   QLIK:   Associative engine — any two tables sharing a field name
#           are automatically joined at query time. No explicit FK
#           definitions exist in the loadscript.

#   POWER BI: Requires explicit relationships defined in the Model layer.
#             M Query (Power Query) cannot define relationships —
#             they live in the Tabular Model (TMSL/XMLA).

# This module:
#   1. Extracts implicit Qlik relationships from shared / renamed fields
#   2. Outputs them as:
#        - Relationship summary (human readable)
#        - TMSL JSON  (for REST API / XMLA deployment)
#        - M Query documentation block (comments in each table query)
# """

# import re
# import json
# import logging
# from typing import Dict, Any, List, Optional
# from collections import defaultdict

# logger = logging.getLogger(__name__)


# # ─────────────────────────────────────────────────────────────────────────────
# # Data classes (plain dicts for JSON-compatibility)
# # ─────────────────────────────────────────────────────────────────────────────

# def make_relationship(
#     from_table: str,
#     from_column: str,
#     to_table: str,
#     to_column: str,
#     cardinality: str = "oneToMany",   # oneToMany | manyToOne | manyToMany | oneToOne
#     cross_filter: str = "single",     # single | both
#     is_active: bool = True,
#     note: str = "",
# ) -> Dict[str, Any]:
#     return {
#         "from_table":   from_table,
#         "from_column":  from_column,
#         "to_table":     to_table,
#         "to_column":    to_column,
#         "cardinality":  cardinality,
#         "cross_filter": cross_filter,
#         "is_active":    is_active,
#         "note":         note,
#     }


# # ─────────────────────────────────────────────────────────────────────────────
# # Main extractor
# # ─────────────────────────────────────────────────────────────────────────────

# class RelationshipExtractor:
#     """
#     Extract Power BI relationships from a parsed Qlik LoadScript.

#     Qlik encodes relationships in two ways:
#       1. SAME field name in two tables  →  implicit auto-join
#       2. AS alias renaming              →  explicit FK (e.g. DealerID AS [DealerID-ServiceID])
#          When two tables rename different source columns to the same name,
#          that name is the join key.

#     Usage
#     -----
#     extractor = RelationshipExtractor(tables)   # tables = generator.tables
#     relationships = extractor.extract()
#     tmsl = extractor.to_tmsl_json()
#     """

#     # Tables that are Qlik-internal scaffolding — never included
#     _INTERNAL_PREFIXES = ("__city", "__geo", "__")

#     def __init__(self, tables: List[Dict[str, Any]]):
#         # Filter out internal tables
#         self.tables = [
#             t for t in tables
#             if not any(t["name"].lower().startswith(p) for p in self._INTERNAL_PREFIXES)
#         ]
#         self._relationships: List[Dict[str, Any]] = []
#         self._extracted = False

#     # ─────────────────────────────────────────────────────────────────────
#     # Public API
#     # ─────────────────────────────────────────────────────────────────────

#     def extract(self) -> List[Dict[str, Any]]:
#         """Return list of relationship dicts."""
#         if not self._extracted:
#             self._relationships = self._find_relationships()
#             self._extracted = True
#         return self._relationships

#     def to_tmsl_json(self, indent: int = 2) -> str:
#         """
#         Return TMSL JSON suitable for patching a Power BI semantic model
#         via the XMLA endpoint or REST API.

#         POST to: POST /groups/{workspaceId}/datasets/{datasetId}/executeQueries
#         Or apply via Tabular Editor / XMLA write endpoint.
#         """
#         rels = self.extract()
#         tmsl_rels = []
#         for r in rels:
#             name = (
#                 "%s_%s_to_%s_%s" % (
#                     r["from_table"], r["from_column"],
#                     r["to_table"],   r["to_column"],
#                 )
#             ).replace(" ", "_").replace("-", "_").replace(".", "_")

#             tmsl_rels.append({
#                 "name":                  name,
#                 "fromTable":             r["from_table"],
#                 "fromColumn":            r["from_column"],
#                 "toTable":               r["to_table"],
#                 "toColumn":              r["to_column"],
#                 "crossFilteringBehavior": r["cross_filter"],
#                 "isActive":              r["is_active"],
#             })

#         return json.dumps(
#             {
#                 "createOrReplace": {
#                     "object": {"database": "<your_dataset_name>"},
#                     "model": {"relationships": tmsl_rels},
#                 }
#             },
#             indent=indent,
#         )

#     def to_summary(self) -> str:
#         """Human-readable relationship summary."""
#         rels = self.extract()
#         if not rels:
#             return "No relationships detected."

#         lines = [
#             "=" * 70,
#             "DETECTED RELATIONSHIPS  (%d)" % len(rels),
#             "=" * 70,
#             "",
#             "  %-28s  %-28s  %-12s" % ("FROM (many side)", "TO (one side)", "Join Key"),
#             "  " + "-" * 72,
#         ]
#         for r in rels:
#             card_arrow = "→" if "one" in r["cardinality"].lower() else "↔"
#             lines.append(
#                 "  %-28s %s %-28s  [%s]" % (
#                     r["from_table"],
#                     card_arrow,
#                     r["to_table"],
#                     r["from_column"] if r["from_column"] == r["to_column"]
#                     else "%s = %s" % (r["from_column"], r["to_column"]),
#                 )
#             )
#             if r.get("note"):
#                 lines.append("  %-28s   %-28s  ↑ %s" % ("", "", r["note"]))
#         lines.append("")
#         return "\n".join(lines)

#     def to_m_query_comment_block(self) -> str:
#         """
#         Generate a comment block to prepend to each M Query table
#         explaining what relationships it participates in.
#         Returns a dict keyed by table name.
#         """
#         rels = self.extract()
#         comments: Dict[str, List[str]] = defaultdict(list)

#         for r in rels:
#             key_desc = (
#                 "[%s]" % r["from_column"]
#                 if r["from_column"] == r["to_column"]
#                 else "[%s] = [%s]" % (r["from_column"], r["to_column"])
#             )
#             comments[r["from_table"]].append(
#                 "// Relationship → %s on %s  (%s)"
#                 % (r["to_table"], key_desc, r["cardinality"])
#             )
#             comments[r["to_table"]].append(
#                 "// Relationship ← %s on %s  (%s)"
#                 % (r["from_table"], key_desc, r["cardinality"])
#             )

#         result = {}
#         for table_name, lines in comments.items():
#             result[table_name] = (
#                 "// " + "─" * 60 + "\n"
#                 + "// RELATIONSHIPS for: %s\n" % table_name
#                 + "// (Define these in Power BI Model view or via TMSL)\n"
#                 + "\n".join(lines) + "\n"
#                 + "// " + "─" * 60 + "\n"
#             )
#         return result

#     # ─────────────────────────────────────────────────────────────────────
#     # Core extraction logic
#     # ─────────────────────────────────────────────────────────────────────

#     def _find_relationships(self) -> List[Dict[str, Any]]:
#         """
#         Find all relationships by scanning for shared field names across tables.

#         Qlik rule: if two tables both have a field with the same name,
#         they are joined on that field. Aliasing (AS) is what creates or
#         renames those shared keys.
#         """
#         # Build field → [table, ...] map
#         field_map: Dict[str, List[str]] = defaultdict(list)
#         for table in self.tables:
#             for field in table.get("fields", []):
#                 field_map[field].append(table["name"])

#         relationships: List[Dict[str, Any]] = []
#         seen_pairs: set = set()

#         for field, table_list in field_map.items():
#             if len(table_list) < 2:
#                 continue

#             # Determine which table is the "one" side (dimension) vs "many" (fact)
#             for i in range(len(table_list)):
#                 for j in range(i + 1, len(table_list)):
#                     t1, t2 = table_list[i], table_list[j]
#                     pair_key = tuple(sorted([t1, t2, field]))
#                     if pair_key in seen_pairs:
#                         continue
#                     seen_pairs.add(pair_key)

#                     one_side, many_side = self._determine_cardinality_sides(
#                         t1, t2, field
#                     )
#                     cardinality, note = self._classify_relationship(
#                         one_side, many_side, field
#                     )

#                     relationships.append(make_relationship(
#                         from_table=many_side,
#                         from_column=field,
#                         to_table=one_side,
#                         to_column=field,
#                         cardinality=cardinality,
#                         cross_filter="single",
#                         is_active=True,
#                         note=note,
#                     ))

#         # Sort: dimension tables first, fact tables last
#         fact_keywords = ["fact", "master", "history", "detail", "trans"]
#         def sort_key(r):
#             return (
#                 any(kw in r["from_table"].lower() for kw in fact_keywords),
#                 r["from_table"],
#             )
#         relationships.sort(key=sort_key)
#         return relationships

#     def _determine_cardinality_sides(
#         self, t1: str, t2: str, field: str
#     ):
#         """
#         Determine which table is the 'one' side and which is 'many'.

#         Heuristics (in priority order):
#           1. Table named *_Master / *_Dim / *_Details (without 'Fact') → one side
#           2. Fewer fields → likely a dimension (one side)
#           3. Table name contains 'Fact' or 'History' → many side
#           4. Default: t1 = one, t2 = many
#         """
#         dim_keywords  = ["master", "dim", "lookup", "ref", "vin_details",
#                          "variant_master", "model_master", "dealer_master"]
#         fact_keywords = ["fact", "history", "transaction", "detail", "sales"]

#         t1_lower = t1.lower()
#         t2_lower = t2.lower()

#         t1_is_dim  = any(kw in t1_lower for kw in dim_keywords)
#         t2_is_dim  = any(kw in t2_lower for kw in dim_keywords)
#         t1_is_fact = any(kw in t1_lower for kw in fact_keywords)
#         t2_is_fact = any(kw in t2_lower for kw in fact_keywords)

#         if t1_is_dim and not t2_is_dim:
#             return t1, t2   # t1=one, t2=many
#         if t2_is_dim and not t1_is_dim:
#             return t2, t1
#         if t1_is_fact and not t2_is_fact:
#             return t2, t1   # t2=one, t1=many
#         if t2_is_fact and not t1_is_fact:
#             return t1, t2

#         # Fallback: fewer fields = dimension
#         t1_fields = next((len(t["fields"]) for t in self.tables if t["name"] == t1), 99)
#         t2_fields = next((len(t["fields"]) for t in self.tables if t["name"] == t2), 99)
#         if t1_fields <= t2_fields:
#             return t1, t2
#         return t2, t1

#     def _classify_relationship(
#         self, one_side: str, many_side: str, field: str
#     ):
#         """Return (cardinality_string, note)."""
#         one_lower  = one_side.lower()
#         many_lower = many_side.lower()

#         # Shared descriptive fields (ModelName, VariantName, ServiceType, ServiceCost)
#         # are usually denormalized copies in Qlik — warn about this
#         denorm_hint_fields = {"servicetype", "servicecost", "fueltype", "vehiclechannel"}
#         if field.lower().replace("-","").replace("_","") in denorm_hint_fields:
#             return (
#                 "manyToMany",
#                 "⚠️  '%s' looks denormalized (same value in both tables). "
#                 "Consider using a bridge table or filtering to one direction." % field,
#             )

#         return (
#             "oneToMany",
#             "%s.[%s] is the unique key; %s has many rows per key."
#             % (one_side, field, many_side),
#         )


# # ─────────────────────────────────────────────────────────────────────────────
# # Standalone usage / integration helper
# # ─────────────────────────────────────────────────────────────────────────────

# def extract_relationships(tables: List[Dict[str, Any]]) -> Dict[str, Any]:
#     """
#     Convenience function. Pass generator.tables, get back everything needed.

#     Returns:
#     {
#         "relationships":    [...],     # list of relationship dicts
#         "tmsl_json":        "...",     # TMSL patch JSON string
#         "summary":          "...",     # human-readable text
#         "table_comments":   {...},     # dict[table_name] → comment block string
#     }
#     """
#     extractor = RelationshipExtractor(tables)
#     return {
#         "relationships":  extractor.extract(),
#         "tmsl_json":      extractor.to_tmsl_json(),
#         "summary":        extractor.to_summary(),
#         "table_comments": extractor.to_m_query_comment_block(),
#     }




"""
BULK RELATIONSHIP EXTRACTOR FOR ALL QLIK APPS
Extract relationships from ALL Qlik apps automatically
No need to click individual tables - extracts ALL relationships
"""

import logging
from typing import List, Dict, Any, Set, Tuple
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

# ============================================================================
# BULK RELATIONSHIP EXTRACTOR
# ============================================================================

class BulkRelationshipExtractor:
    """
    Analyzes ALL Qlik apps and extracts ALL relationships automatically
    
    Features:
    - Scans all apps in Qlik Sense
    - Analyzes all tables in each app
    - Detects all foreign key relationships
    - Builds complete relationship graph
    - Generates CSV for all tables
    - Ready for bulk publishing to Power BI
    """
    
    def __init__(self, apps_with_tables: Dict[str, List[Dict[str, Any]]]):
        """
        Initialize with apps and their tables
        
        Format:
        {
            "app-001": {
                "appName": "Sales Analytics",
                "tables": [
                    {
                        "name": "Sales",
                        "fields": [
                            {"name": "SalesID", "type": "integer"},
                            {"name": "CustomerID", "type": "integer"},
                            ...
                        ]
                    }
                ]
            }
        }
        """
        self.apps_with_tables = apps_with_tables
        self.all_relationships = {}  # app_id -> [relationships]
        self.all_csv_data = {}  # app_id -> {table_name -> csv}
        self.extracted = False
    
    def extract_all_relationships(self) -> Dict[str, Any]:
        """
        Extract relationships from ALL apps
        Returns complete analysis with relationships, CSV, and deployment info
        """
        
        logger.info(f"🔗 Bulk Extracting Relationships from {len(self.apps_with_tables)} apps...")
        
        extraction_result = {
            "timestamp": datetime.now().isoformat(),
            "totalApps": len(self.apps_with_tables),
            "apps": {},
            "stats": {
                "totalTables": 0,
                "totalFields": 0,
                "totalRelationships": 0,
                "appsWithRelationships": 0
            }
        }
        
        for app_id, app_data in self.apps_with_tables.items():
            logger.info(f"📊 Processing app: {app_data.get('appName', app_id)}")
            
            tables = app_data.get("tables", [])
            
            # Extract relationships for this app
            relationships = self._extract_app_relationships(tables)
            
            # Generate CSV for all tables
            csv_payloads = self._generate_all_csv_data(tables)
            
            # Store for later use
            self.all_relationships[app_id] = relationships
            self.all_csv_data[app_id] = csv_payloads
            
            # Build app result
            app_result = {
                "appId": app_id,
                "appName": app_data.get("appName", "Unknown"),
                "tableCount": len(tables),
                "fieldCount": sum(len(t.get("fields", [])) for t in tables),
                "relationships": relationships,
                "relatedTables": self._get_related_tables(relationships),
                "csvTables": list(csv_payloads.keys()),
                "csvSize": sum(len(csv) for csv in csv_payloads.values()),
                "readyForPublish": len(relationships) > 0 or len(tables) > 0
            }
            
            extraction_result["apps"][app_id] = app_result
            
            # Update stats
            extraction_result["stats"]["totalTables"] += len(tables)
            extraction_result["stats"]["totalFields"] += app_result["fieldCount"]
            extraction_result["stats"]["totalRelationships"] += len(relationships)
            if len(relationships) > 0:
                extraction_result["stats"]["appsWithRelationships"] += 1
            
            logger.info(
                f"  ✓ {len(tables)} tables, "
                f"{len(relationships)} relationships, "
                f"{len(csv_payloads)} CSV tables"
            )
        
        self.extracted = True
        return extraction_result
    
    def _extract_app_relationships(self, tables: List[Dict]) -> List[Dict]:
        """
        Extract ALL relationships from app tables using intelligent detection
        """
        
        relationships = []
        processed_pairs = set()
        
        # Build field map for all tables
        field_map = defaultdict(list)
        table_by_name = {}
        
        for table in tables:
            table_name = table.get("name", "")
            table_by_name[table_name] = table
            
            for field in table.get("fields", []):
                field_name = field.get("name", "")
                field_map[field_name.lower()].append(table_name)
        
        # Strategy 1: Detect via ID field naming (FK → PK pattern)
        relationships.extend(
            self._detect_id_field_relationships(tables, field_map, processed_pairs)
        )
        
        # Strategy 2: Detect via shared fields
        relationships.extend(
            self._detect_shared_field_relationships(tables, field_map, processed_pairs)
        )
        
        # Strategy 3: Detect via naming conventions
        relationships.extend(
            self._detect_naming_convention_relationships(tables, field_map, processed_pairs)
        )
        
        # Remove duplicates and invalid relationships
        relationships = self._deduplicate_relationships(relationships)
        
        return relationships
    
    def _detect_id_field_relationships(
        self,
        tables: List[Dict],
        field_map: Dict,
        processed_pairs: Set
    ) -> List[Dict]:
        """
        Strategy 1: Detect relationships via ID naming
        Pattern: {TableName}ID field in one table → TableName.ID in another
        
        Example:
          Sales table has "CustomerID" field
          Customer table has "ID" or "CustomerID" field
          → Relationship: Sales.CustomerID → Customer.ID
        """
        
        relationships = []
        
        for table in tables:
            table_name = table.get("name", "")
            
            for field in table.get("fields", []):
                field_name = field.get("name", "")
                
                # Check if field ends with "ID" (potential FK)
                if not field_name.lower().endswith("id"):
                    continue
                
                # Extract potential table name (remove "ID" suffix)
                potential_ref_table = field_name[:-2]  # Remove "ID"
                
                # Look for matching table
                for other_table in tables:
                    other_table_name = other_table.get("name", "")
                    
                    if other_table_name == table_name:
                        continue  # Skip self-references
                    
                    # Check if other table name matches (case-insensitive)
                    if other_table_name.lower() == potential_ref_table.lower():
                        
                        # Find matching PK in other table
                        pk_field = self._find_primary_key(other_table)
                        
                        pair_key = tuple(sorted([
                            (table_name, field_name),
                            (other_table_name, pk_field)
                        ]))
                        
                        if pair_key not in processed_pairs:
                            processed_pairs.add(pair_key)
                            
                            # Determine cardinality
                            cardinality = self._determine_cardinality(
                                table_name, field_name,
                                other_table_name, pk_field
                            )
                            
                            relationships.append({
                                "fromTable": table_name,
                                "fromColumn": field_name,
                                "toTable": other_table_name,
                                "toColumn": pk_field,
                                "cardinality": cardinality,
                                "detectionMethod": "ID_FIELD_NAMING",
                                "confidence": 0.95
                            })
        
        return relationships
    
    def _detect_shared_field_relationships(
        self,
        tables: List[Dict],
        field_map: Dict,
        processed_pairs: Set
    ) -> List[Dict]:
        """
        Strategy 2: Detect relationships via shared field names
        Pattern: Two tables share the same field name
        
        Example:
          Sales table has "RegionID"
          Region table has "RegionID"
          → Relationship: Sales.RegionID → Region.RegionID
        """
        
        relationships = []
        
        for field_lower, table_list in field_map.items():
            if len(table_list) < 2:
                continue  # Need at least 2 tables with same field
            
            for i, table1_name in enumerate(table_list):
                for table2_name in table_list[i+1:]:
                    
                    pair_key = tuple(sorted([(table1_name, field_lower), (table2_name, field_lower)]))
                    
                    if pair_key in processed_pairs:
                        continue
                    
                    processed_pairs.add(pair_key)
                    
                    # Determine which is PK and which is FK
                    is_pk_1 = self._is_primary_key(field_lower)
                    is_pk_2 = self._is_primary_key(field_lower)
                    
                    if is_pk_1 or is_pk_2:
                        # One side is likely PK, other is FK
                        fk_table = table2_name if is_pk_1 else table1_name
                        pk_table = table1_name if is_pk_1 else table2_name
                    else:
                        # Use table size heuristic (smaller table = dimension = PK side)
                        table1 = next((t for t in tables if t.get("name") == table1_name), {})
                        table2 = next((t for t in tables if t.get("name") == table2_name), {})
                        
                        fields1 = len(table1.get("fields", []))
                        fields2 = len(table2.get("fields", []))
                        
                        if fields1 <= fields2:
                            pk_table, fk_table = table1_name, table2_name
                        else:
                            pk_table, fk_table = table2_name, table1_name
                    
                    # Find actual field name (preserve case)
                    actual_field = self._find_field_by_lower(field_lower, pk_table, tables)
                    
                    relationships.append({
                        "fromTable": fk_table,
                        "fromColumn": actual_field,
                        "toTable": pk_table,
                        "toColumn": actual_field,
                        "cardinality": "ManyToOne",
                        "detectionMethod": "SHARED_FIELD",
                        "confidence": 0.8
                    })
        
        return relationships
    
    def _detect_naming_convention_relationships(
        self,
        tables: List[Dict],
        field_map: Dict,
        processed_pairs: Set
    ) -> List[Dict]:
        """
        Strategy 3: Detect via naming conventions
        Pattern: Specific field names that indicate relationships
        
        Examples:
          - CountryID → Country table
          - CustomerKey → Customer table
          - ProductFK → Product table
        """
        
        relationships = []
        
        naming_patterns = {
            "CountryID": "Country",
            "CustomerID": "Customer",
            "ProductID": "Product",
            "RegionID": "Region",
            "CategoryID": "Category",
            "SalesID": "Sales",
            "OrderID": "Order",
            "UserID": "User",
            "CompanyID": "Company",
            "DepartmentID": "Department",
            "EmployeeID": "Employee",
        }
        
        for table in tables:
            table_name = table.get("name", "")
            
            for field in table.get("fields", []):
                field_name = field.get("name", "")
                
                for pattern, ref_table_name in naming_patterns.items():
                    if pattern.lower() == field_name.lower():
                        # Found a matching pattern
                        # Look for the referenced table
                        for other_table in tables:
                            other_name = other_table.get("name", "")
                            
                            if other_name.lower() == ref_table_name.lower():
                                pk_field = self._find_primary_key(other_table)
                                
                                pair_key = tuple(sorted([
                                    (table_name, field_name),
                                    (other_name, pk_field)
                                ]))
                                
                                if pair_key not in processed_pairs:
                                    processed_pairs.add(pair_key)
                                    
                                    relationships.append({
                                        "fromTable": table_name,
                                        "fromColumn": field_name,
                                        "toTable": other_name,
                                        "toColumn": pk_field,
                                        "cardinality": "ManyToOne",
                                        "detectionMethod": "NAMING_PATTERN",
                                        "confidence": 0.85
                                    })
        
        return relationships
    
    def _find_primary_key(self, table: Dict) -> str:
        """Find primary key field in a table"""
        
        fields = table.get("fields", [])
        
        # Strategy 1: Look for field ending with "ID"
        for field in fields:
            name = field.get("name", "")
            if name.lower().endswith("id"):
                return name
        
        # Strategy 2: Look for "ID" field exactly
        for field in fields:
            name = field.get("name", "")
            if name.lower() == "id" or name.lower() == "pk":
                return name
        
        # Strategy 3: First field (often ID in data warehouses)
        if fields:
            return fields[0].get("name", "ID")
        
        return "ID"
    
    def _is_primary_key(self, field_name: str) -> bool:
        """Check if field name indicates it's a primary key"""
        lower = field_name.lower()
        return lower == "id" or lower == "pk" or "id" in lower
    
    def _find_field_by_lower(self, field_lower: str, table_name: str, tables: List[Dict]) -> str:
        """Find actual field name (with correct case) by lowercase search"""
        for table in tables:
            if table.get("name") == table_name:
                for field in table.get("fields", []):
                    if field.get("name", "").lower() == field_lower:
                        return field.get("name", field_lower)
        return field_lower
    
    def _determine_cardinality(
        self,
        from_table: str,
        from_column: str,
        to_table: str,
        to_column: str
    ) -> str:
        """Determine relationship cardinality"""
        
        # If from field is FK (ends with ID), it's many-to-one
        if from_column.lower().endswith("id"):
            return "ManyToOne"
        
        # Default to ManyToOne for safety
        return "ManyToOne"
    
    def _deduplicate_relationships(self, relationships: List[Dict]) -> List[Dict]:
        """Remove duplicate relationships, keeping highest confidence"""
        
        seen = {}
        
        for rel in relationships:
            key = (
                rel["fromTable"],
                rel["fromColumn"],
                rel["toTable"],
                rel["toColumn"]
            )
            
            if key not in seen or rel.get("confidence", 0) > seen[key].get("confidence", 0):
                seen[key] = rel
        
        return list(seen.values())
    
    def _get_related_tables(self, relationships: List[Dict]) -> List[str]:
        """Get list of all related tables from relationships"""
        tables = set()
        for rel in relationships:
            tables.add(rel["fromTable"])
            tables.add(rel["toTable"])
        return sorted(list(tables))
    
    def _generate_all_csv_data(self, tables: List[Dict]) -> Dict[str, str]:
        """Generate sample CSV data for all tables"""
        
        csv_payloads = {}
        
        for table in tables:
            table_name = table.get("name", "")
            fields = table.get("fields", [])
            
            if not fields:
                continue
            
            # Build header
            header = ",".join([f.get("name", "") for f in fields])
            
            # Generate 5 sample rows
            rows = []
            for i in range(1, 6):
                row_values = []
                for field in fields:
                    field_name = field.get("name", "").lower()
                    field_type = field.get("type", "text").lower()
                    
                    # Generate sample value based on field type and name
                    if "id" in field_name or "key" in field_name:
                        value = str(1000 + i)
                    elif "date" in field_name:
                        value = f"2024-01-{(i%28)+1:02d}"
                    elif "amount" in field_name or "price" in field_name or "sale" in field_name:
                        value = str(10000 + (i * 1000))
                    elif "name" in field_name:
                        names = ["John", "Jane", "Bob", "Alice", "Charlie"]
                        value = names[i % len(names)]
                    elif "count" in field_name or "qty" in field_name:
                        value = str(i * 10)
                    else:
                        value = f"Sample_{i}"
                    
                    row_values.append(value)
                
                rows.append(",".join(row_values))
            
            # Combine header and rows
            csv_payloads[table_name] = header + "\n" + "\n".join(rows)
        
        return csv_payloads


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def demo_bulk_extraction():
    """
    Demonstrate bulk relationship extraction from all apps
    """
    
    print("\n" + "="*80)
    print("BULK RELATIONSHIP EXTRACTION - ALL APPS")
    print("="*80)
    
    # Sample data: Multiple apps with their tables
    apps_with_tables = {
        "app-sales-001": {
            "appName": "Sales Analytics",
            "tables": [
                {
                    "name": "Sales",
                    "fields": [
                        {"name": "SalesID", "type": "integer"},
                        {"name": "OrderDate", "type": "date"},
                        {"name": "CustomerID", "type": "integer"},
                        {"name": "ProductID", "type": "integer"},
                        {"name": "RegionID", "type": "integer"},
                        {"name": "Amount", "type": "numeric"}
                    ]
                },
                {
                    "name": "Customer",
                    "fields": [
                        {"name": "CustomerID", "type": "integer"},
                        {"name": "CustomerName", "type": "text"},
                        {"name": "CountryID", "type": "integer"},
                        {"name": "Segment", "type": "text"}
                    ]
                },
                {
                    "name": "Product",
                    "fields": [
                        {"name": "ProductID", "type": "integer"},
                        {"name": "ProductName", "type": "text"},
                        {"name": "CategoryID", "type": "integer"},
                        {"name": "Price", "type": "numeric"}
                    ]
                },
                {
                    "name": "Category",
                    "fields": [
                        {"name": "CategoryID", "type": "integer"},
                        {"name": "CategoryName", "type": "text"}
                    ]
                },
                {
                    "name": "Region",
                    "fields": [
                        {"name": "RegionID", "type": "integer"},
                        {"name": "RegionName", "type": "text"}
                    ]
                },
                {
                    "name": "Country",
                    "fields": [
                        {"name": "CountryID", "type": "integer"},
                        {"name": "CountryName", "type": "text"}
                    ]
                }
            ]
        },
        "app-customer-002": {
            "appName": "Customer Insights",
            "tables": [
                {
                    "name": "Customer",
                    "fields": [
                        {"name": "CustomerID", "type": "integer"},
                        {"name": "Name", "type": "text"},
                        {"name": "Email", "type": "text"},
                        {"name": "SegmentID", "type": "integer"}
                    ]
                },
                {
                    "name": "Segment",
                    "fields": [
                        {"name": "SegmentID", "type": "integer"},
                        {"name": "SegmentName", "type": "text"}
                    ]
                },
                {
                    "name": "Orders",
                    "fields": [
                        {"name": "OrderID", "type": "integer"},
                        {"name": "CustomerID", "type": "integer"},
                        {"name": "OrderDate", "type": "date"},
                        {"name": "OrderAmount", "type": "numeric"}
                    ]
                }
            ]
        },
        "app-inventory-003": {
            "appName": "Inventory Management",
            "tables": [
                {
                    "name": "Stock",
                    "fields": [
                        {"name": "StockID", "type": "integer"},
                        {"name": "ProductID", "type": "integer"},
                        {"name": "WarehouseID", "type": "integer"},
                        {"name": "Quantity", "type": "integer"},
                        {"name": "LastUpdated", "type": "date"}
                    ]
                },
                {
                    "name": "Product",
                    "fields": [
                        {"name": "ProductID", "type": "integer"},
                        {"name": "ProductName", "type": "text"},
                        {"name": "SKU", "type": "text"}
                    ]
                },
                {
                    "name": "Warehouse",
                    "fields": [
                        {"name": "WarehouseID", "type": "integer"},
                        {"name": "WarehouseName", "type": "text"},
                        {"name": "Location", "type": "text"}
                    ]
                }
            ]
        }
    }
    
    # Create extractor
    extractor = BulkRelationshipExtractor(apps_with_tables)
    
    # Extract all relationships
    result = extractor.extract_all_relationships()
    
    # Print results
    print(f"\n✅ EXTRACTION COMPLETE")
    print(f"   Total Apps: {result['totalApps']}")
    print(f"   Total Tables: {result['stats']['totalTables']}")
    print(f"   Total Fields: {result['stats']['totalFields']}")
    print(f"   Total Relationships: {result['stats']['totalRelationships']}")
    print(f"   Apps with Relationships: {result['stats']['appsWithRelationships']}")
    
    # Print per-app results
    print(f"\n📊 PER-APP ANALYSIS:")
    print("-" * 80)
    
    for app_id, app_result in result["apps"].items():
        print(f"\n🔹 {app_result['appName']} (ID: {app_id})")
        print(f"   Tables: {app_result['tableCount']}")
        print(f"   Fields: {app_result['fieldCount']}")
        print(f"   Relationships: {len(app_result['relationships'])}")
        print(f"   CSV Size: {app_result['csvSize']} bytes")
        print(f"   Ready for Power BI: {'✅ Yes' if app_result['readyForPublish'] else '❌ No'}")
        
        if app_result['relationships']:
            print(f"   Relationships:")
            for rel in app_result['relationships']:
                print(
                    f"     • {rel['fromTable']}.{rel['fromColumn']} → "
                    f"{rel['toTable']}.{rel['toColumn']} ({rel['cardinality']})"
                )
        
        print(f"   Tables for Power BI: {', '.join(app_result['csvTables'])}")
    
    print("\n" + "="*80)
    print("✨ ALL APPS ANALYZED - READY FOR BULK PUBLISHING TO POWER BI")
    print("="*80)
    
    return result


if __name__ == "__main__":
    demo_bulk_extraction()