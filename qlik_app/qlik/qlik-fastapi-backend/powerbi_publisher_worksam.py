# """
# powerbi_publisher.py  -  QlikAI Accelerator
# Publishes a semantic model to Microsoft Fabric / Power BI Premium workspace.

# Strategy:
#   1. Fabric Items API  (POST /v1/workspaces/{id}/semanticModels)
#      - Requires: definition.pbism (version 1.0) + model.bim (TMSL V3)
#      - model.bim MUST have compatibilityLevel=1550, defaultPowerBIDataSourceVersion="powerBI_V3"
#      - Tables MUST have explicit columns (Fabric does NOT infer from M on create)
#   2. Push Dataset API  (fallback - limited, no M Query)

# Auth: Service Principal client credentials (silent - no user interaction).
# """

# from ast import expr
# import base64
# import json
# import logging
# import os
# import re
# import time
# from typing import Any, Dict, List, Optional

# import requests

# logger = logging.getLogger(__name__)

# # ─────────────────────────────────────────────────────────────────────────────
# # Public entry point
# # ─────────────────────────────────────────────────────────────────────────────

# def publish_semantic_model(
#     dataset_name: str,
#     tables_m: List[Dict[str, Any]],
#     relationships: List[Dict[str, Any]] = None,
#     access_token: str = "",
#     data_source_path: str = "",
#     db_connection_string: str = "",
#     workspace_id: str = "",
# ) -> Dict[str, Any]:
#     """
#     Publish tables as a Power BI semantic model.

#     Each item in tables_m must have:
#         name         - table name
#         m_expression - full M Query (let ... in ...)
#         source_type  - 'inline' | 'csv' | 'qvd' | 'sql' | 'resident'
#         fields       - list of {name, type} dicts  <- used to build columns in BIM
#     """
#     relationships = relationships or []

#     if not workspace_id:
#         workspace_id = os.getenv("POWERBI_WORKSPACE_ID", "")
#     if not workspace_id:
#         return {"success": False, "error": "POWERBI_WORKSPACE_ID not set"}

#     if db_connection_string:
#         tables_m = _rewrite_for_db_connect(tables_m, db_connection_string)

#     token = access_token or _acquire_sp_token()
#     return _Publisher(workspace_id=workspace_id, access_token=token).publish(
#         dataset_name, tables_m, relationships, data_source_path
#     )


# # ─────────────────────────────────────────────────────────────────────────────
# # Auth
# # ─────────────────────────────────────────────────────────────────────────────

# def _acquire_sp_token(
#     scope: str = "https://analysis.windows.net/powerbi/api/.default",
# ) -> str:
#     """Acquire token via Service Principal (client credentials)."""
#     try:
#         import msal
#         tenant_id     = os.getenv("POWERBI_TENANT_ID", "")
#         client_id     = os.getenv("POWERBI_CLIENT_ID", "")
#         client_secret = os.getenv("POWERBI_CLIENT_SECRET", "")
#         if not all([tenant_id, client_id, client_secret]):
#             logger.warning("[Auth] SP credentials missing from environment")
#             return ""
#         app = msal.ConfidentialClientApplication(
#             client_id,
#             authority=f"https://login.microsoftonline.com/{tenant_id}",
#             client_credential=client_secret,
#         )
#         result = app.acquire_token_for_client(scopes=[scope])
#         token = result.get("access_token", "")
#         if token:
#             logger.info("[Auth] SP token acquired: %s", scope)
#         else:
#             logger.warning("[Auth] SP token failed: %s", result.get("error_description"))
#         return token
#     except Exception as exc:
#         logger.warning("[Auth] SP token error: %s", exc)
#         return ""


# def initiate_device_code_flow() -> Dict[str, Any]:
#     try:
#         import msal
#         tenant_id = os.getenv("POWERBI_TENANT_ID", "")
#         client_id = os.getenv("POWERBI_CLIENT_ID", "")
#         app = msal.PublicClientApplication(
#             client_id,
#             authority=f"https://login.microsoftonline.com/{tenant_id}",
#         )
#         flow = app.initiate_device_flow(
#             scopes=["https://analysis.windows.net/powerbi/api/.default"]
#         )
#         _cache_device_flow(flow)
#         return {
#             "success": True,
#             "device_code_url": "https://microsoft.com/devicelogin",
#             "user_code": flow.get("user_code", ""),
#             "message": flow.get("message", ""),
#         }
#     except Exception as exc:
#         return {"success": False, "error": str(exc)}


# def complete_device_code_flow() -> Dict[str, Any]:
#     try:
#         import msal
#         flow = _load_device_flow()
#         if not flow:
#             return {"success": False, "error": "No pending device code flow"}
#         tenant_id = os.getenv("POWERBI_TENANT_ID", "")
#         client_id = os.getenv("POWERBI_CLIENT_ID", "")
#         app = msal.PublicClientApplication(
#             client_id,
#             authority=f"https://login.microsoftonline.com/{tenant_id}",
#         )
#         result = app.acquire_token_by_device_flow(flow)
#         token = result.get("access_token", "")
#         if token:
#             _cache_user_token(token)
#             _clear_device_flow()
#             return {"success": True, "access_token": token}
#         return {"success": False, "error": result.get("error_description", "unknown")}
#     except Exception as exc:
#         return {"success": False, "error": str(exc)}


# def get_cached_user_token() -> str:
#     try:
#         path = _token_cache_path()
#         if os.path.exists(path):
#             data = json.loads(open(path).read())
#             if time.time() < data.get("expires_at", 0):
#                 return data.get("token", "")
#     except Exception:
#         pass
#     return ""


# # ─────────────────────────────────────────────────────────────────────────────
# # DB Connect rewriter
# # ─────────────────────────────────────────────────────────────────────────────

# def _rewrite_for_db_connect(
#     tables_m: List[Dict[str, Any]], connection: str
# ) -> List[Dict[str, Any]]:
#     out = []
#     for t in tables_m:
#         src = t.get("source_type", "").lower()
#         expr = t.get("m_expression", "")
#         if src == "resident" or "Table.NestedJoin" in expr:
#             out.append(t)
#             continue
#         if src in ("sql", "odbc") or "Sql.Database" in expr or "Odbc.Query" in expr:
#             out.append(t)
#             continue
#         new_expr = (
#             f'let\n'
#             f'    Source = Odbc.Query("{connection}", "SELECT * FROM [{t["name"]}]"),\n'
#             f'    Result = Source\nin\n    Result'
#         )
#         out.append({**t, "m_expression": new_expr, "source_type": "odbc"})
#     return out


# # ─────────────────────────────────────────────────────────────────────────────
# # Helper functions
# # ─────────────────────────────────────────────────────────────────────────────

# _QLIK_TO_TABULAR = {
#     "integer":   "int64",
#     "float":     "double",
#     "money":     "decimal",
#     "date":      "dateTime",
#     "datetime":  "dateTime",
#     "timestamp": "dateTime",
#     "boolean":   "boolean",
#     "bool":      "boolean",
#     "number":    "double",
# }


# def _tabular_type(qlik_type: str) -> str:
#     return _QLIK_TO_TABULAR.get((qlik_type or "").lower(), "string")


# def _infer_type_from_name(name: str) -> str:
#     """Infer type from column name heuristics."""
#     n = name.lower().strip()
#     if any(x in n for x in ["date", "time", "timestamp", "created", "updated", "dob", "birth"]):
#         return "date"
#     if any(x in n for x in ["price", "cost", "amount", "revenue", "salary", "rate", "total", "tax", "discount", "margin"]):
#         return "number"
#     if any(x in n for x in ["id", "count", "qty", "quantity", "year", "month", "day", "num", "age", "rank", "km", "tons", "knots", "cc", "speed"]):
#         return "integer"
#     return "string"


# # def _extract_fields_from_m(expr: str) -> list:
# #     """Extract column names and types from #table() type signature in M expression."""
# #     match = re.search(r"type\s+table\s+\[(.+?)\]", expr, re.DOTALL)
# #     if not match:
# #         logger.warning("[BIM] Could not extract fields from M expression")
# #         return []
# #     cols_str = match.group(1)
# #     type_map = {
# #         "text":       "string",
# #         "number":     "number",
# #         "date":       "date",
# #         "datetime":   "datetime",
# #         "logical":    "boolean",
# #         "Int64.Type": "integer",
# #     }
# #     fields = []
# #     for part in cols_str.split(","):
# #         part = part.strip()
# #         if "=" not in part:
# #             continue
# #         col_name = part.split("=")[0].strip().strip('#').strip('"')
# #         col_type_raw = part.split("=")[1].strip()
# #         mapped_type = type_map.get(col_type_raw, "string")
# #         if mapped_type == "string":
# #             mapped_type = _infer_type_from_name(col_name)
# #         fields.append({"name": col_name, "type": mapped_type})
# #     logger.info("[BIM] Extracted %d fields: %s", len(fields), [f["name"] for f in fields])
# #     return fields if fields else []
# def _extract_fields_from_m(expr: str) -> list:
#     """Extract column names and types from M expression.
    
#     Handles multiple patterns:
#     1. type table [col1 = type text, col2 = type number]
#     2. Table.TransformColumnTypes(..., {{"col1", type text}, {"col2", type number}})
#     3. CSV headers (last resort - from PromoteHeaders)
#     """
#     import re
    
#     type_map = {
#         "text": "string",
#         "number": "number", 
#         "date": "date",
#         "datetime": "datetime",
#         "logical": "boolean",
#         "Int64.Type": "integer",
#         "type text": "string",
#         "type number": "number",
#         "type date": "date",
#     }
    
#     fields = []
    
#     # Pattern 1: Table.TransformColumnTypes pattern (most common from mquery_converter)
#     # Looks for: {{"ColumnName", type text}, {"AnotherColumn", type number}}
#     transform_pattern = r'Table\.TransformColumnTypes\s*\(\s*[^,]+?\s*,\s*\{\s*(.+?)\s*\}\s*\)'
#     match = re.search(transform_pattern, expr, re.DOTALL)
#     if match:
#         cols_str = match.group(1)
#         logger.info("[Extract] Found Table.TransformColumnTypes pattern")
        
#         # Parse each column: {"name", type X}
#         col_pattern = r'\{\s*"([^"]+)"\s*,\s*(Int64\.Type|type\s+\w+)\s*\}'
#         for col_match in re.finditer(col_pattern, cols_str):
#             col_name = col_match.group(1)
#             col_type_raw = col_match.group(2).strip()
#             col_type = type_map.get(col_type_raw, "string")
#             # Infer from name if generic string
#             if col_type == "string":
#                 col_type = _infer_type_from_name(col_name)
#             fields.append({"name": col_name, "type": col_type})
        
#         if fields:
#             logger.info("[Extract] Extracted %d fields from TransformColumnTypes: %s", 
#                        len(fields), [f["name"] for f in fields])
#             return fields
    
#     # Pattern 2: type table [...] pattern (for #table() definitions)
#     match = re.search(r"type\s+table\s+\[(.+?)\]", expr, re.DOTALL)
#     if match:
#         cols_str = match.group(1)
#         logger.info("[Extract] Found type table pattern")
        
#         for part in cols_str.split(","):
#             part = part.strip()
#             if "=" not in part:
#                 continue
#             try:
#                 col_name = part.split("=")[0].strip().strip('#').strip('"')
#                 col_type_raw = part.split("=")[1].strip()
#                 col_type = type_map.get(col_type_raw, "string")
#                 if col_type == "string":
#                     col_type = _infer_type_from_name(col_name)
#                 fields.append({"name": col_name, "type": col_type})
#             except:
#                 continue
        
#         if fields:
#             logger.info("[Extract] Extracted %d fields from type table: %s",
#                        len(fields), [f["name"] for f in fields])
#             return fields
    
#     # Pattern 3: Fallback - extract from PromoteHeaders (CSV source)
#     if "PromoteHeaders" in expr or "PromotedHeaders" in expr:
#         logger.info("[Extract] Detected CSV PromoteHeaders - will infer schema at runtime")
#         # Return empty - will use default placeholder
#         return []
    
#     logger.warning("[Extract] Could not extract fields from M expression - will use placeholder")
#     return []


# # Note: The M expression must have explicit column definitions for Fabric API to work.


# def _fix_multiline_rows(expr: str) -> str:
#     """
#     Ensure every data row in a #table() M expression is on a single line.
#     Rows start with { and end with } or },
#     Any continuation lines are joined onto the opening line.
#     """
#     lines = expr.split("\n")
#     result = []
#     in_row = False
#     current_row = ""

#     for line in lines:
#         stripped = line.strip()

#         if in_row:
#             current_row += " " + stripped
#             # Row complete when closing brace found (with or without trailing comma)
#             if re.search(r'\}\s*,?\s*$', stripped):
#                 result.append(current_row)
#                 current_row = ""
#                 in_row = False
#         else:
#             if stripped.startswith('{"') or stripped.startswith("{'"):
#                 if re.search(r'\}\s*,?\s*$', stripped):
#                     # Complete row on one line
#                     result.append(line)
#                 else:
#                     # Incomplete row - start buffering
#                     in_row = True
#                     current_row = line.rstrip()
#             else:
#                 result.append(line)

#     if current_row:
#         result.append(current_row)

#     return "\n".join(result)


# def _sanitize_m(expr: str) -> str:
#     """M expressions from mquery_converter are already valid - return as-is."""
#     return expr


# # ─────────────────────────────────────────────────────────────────────────────
# # Publisher
# # ─────────────────────────────────────────────────────────────────────────────

# class _Publisher:

#     def __init__(self, workspace_id: str, access_token: str = ""):
#         self.workspace_id = workspace_id
#         self.token = access_token
#         self.pbi_headers = {
#             "Authorization": f"Bearer {self.token}",
#             "Content-Type": "application/json",
#         }

#     # -- main entry -----------------------------------------------------------

#     def publish(
#         self,
#         dataset_name: str,
#         tables_m: List[Dict[str, Any]],
#         relationships: List[Dict[str, Any]],
#         data_source_path: str,
#     ) -> Dict[str, Any]:
#         if not self.token:
#             flow = initiate_device_code_flow()
#             return {
#                 "success": False, "auth_required": True,
#                 "device_code_url": flow.get("device_code_url"),
#                 "user_code": flow.get("user_code"),
#                 "message": flow.get("message", ""),
#                 "error": "Authentication required.",
#             }

#         result = self._deploy_via_fabric(dataset_name, tables_m, relationships, data_source_path)
#         if result.get("success"):
#             return result

#         logger.warning("[Publisher] Fabric API failed (%s) — Push dataset fallback", result.get("error"))
#         return self._deploy_push_dataset(dataset_name, tables_m)

#     # -- BIM builder ----------------------------------------------------------

#     def _build_bim(
#         self,
#         dataset_name: str,
#         tables_m: List[Dict[str, Any]],
#         relationships: List[Dict[str, Any]],
#         data_source_path: str,
#     ) -> str:
#         tmd_tables = []
#         for t in tables_m:
#             expr = t.get("m_expression", "").strip()
#             if not expr:
#                 continue
#             logger.info("==== RAW M FROM tables_m FOR TABLE %s ====", t["name"])
#             logger.info("\n%s\n", expr)    
#             fields = t.get("fields", [])
#             logger.info("[BIM] Table '%s' fields: %s", t["name"], fields)
#             if not fields:
#                 fields = _extract_fields_from_m(expr)
#                 logger.info("[BIM] Extracted fields for '%s': %s", t["name"], fields)

#             columns = []
#             for f in fields:
#                 columns.append({
#                     "name": f["name"],
#                     "dataType": _tabular_type(f.get("type", "string")),
#                     "sourceColumn": f["name"],
#                     "summarizeBy": "none",
#                     "annotations": [{"name": "SummarizationSetBy", "value": "Automatic"}]
#                 })

#             if not columns:
#                 columns = [{
#                     "name": "Value",
#                     "dataType": "string",
#                     "sourceColumn": "Value",
#                     "summarizeBy": "none",
#                     "annotations": [{"name": "SummarizationSetBy", "value": "Automatic"}]
#                 }]

#             fixed_expr = _fix_multiline_rows(_sanitize_m(expr))
#             logger.info("==== FINAL M SENT TO FABRIC FOR TABLE %s ====", t["name"])
#             logger.info("\n%s\n", fixed_expr)
#             tmd_tables.append({
#                 "name": t["name"],
#                 "columns": columns,
#                 "partitions": [{
#                     "name": f"{t['name']}-Partition",
#                     "mode": "import",
#                     "source": {
#                         "type": "m",
#                         "expression": fixed_expr.splitlines()
#                     }
#                 }]
#             })

#         tmd_rels = []
#         for r in relationships:
#             ft = r.get("fromTable") or r.get("from_table", "")
#             fc = r.get("fromColumn") or r.get("from_column", "")
#             tt = r.get("toTable")   or r.get("to_table", "")
#             tc = r.get("toColumn")  or r.get("to_column", "")
#             if ft and fc and tt and tc:
#                 tmd_rels.append({
#                     "name": f"{ft}_{fc}_{tt}_{tc}",
#                     "fromTable": ft, "fromColumn": fc,
#                     "toTable": tt,   "toColumn": tc,
#                     "crossFilteringBehavior": "oneDirection"
#                 })

#         expressions = []
#         if data_source_path:
#             expressions.append({
#                 "name": "DataSourcePath",
#                 "kind": "m",
#                 "expression": [f'"{data_source_path}"']
#             })

#         bim = {
#             "name": dataset_name,
#             "compatibilityLevel": 1550,
#             "model": {
#                 "culture": "en-US",
#                 "dataAccessOptions": {
#                     "legacyRedirects": True,
#                     "returnErrorValuesAsNull": True
#                 },
#                 "defaultPowerBIDataSourceVersion": "powerBI_V3",
#                 "sourceQueryCulture": "en-US",
#                 "tables": tmd_tables,
#                 "relationships": tmd_rels,
#                 "expressions": expressions,
#                 "annotations": [
#                     {"name": "PBIDesktopVersion", "value": "2.130.930.0"},
#                     {"name": "createdBy", "value": "QlikAI_Accelerator"},
#                 ]
#             }
#         }
#         return json.dumps(bim, ensure_ascii=False, indent=2)

#     # -- Strategy 1: Fabric Items API -----------------------------------------

#     def _deploy_via_fabric(
#         self,
#         dataset_name: str,
#         tables_m: List[Dict[str, Any]],
#         relationships: List[Dict[str, Any]],
#         data_source_path: str,
#     ) -> Dict[str, Any]:
#         try:
#             fabric_token = _acquire_sp_token("https://api.fabric.microsoft.com/.default")
#             if not fabric_token:
#                 fabric_token = self.token

#             headers = {
#                 "Authorization": f"Bearer {fabric_token}",
#                 "Content-Type": "application/json",
#             }

#             bim_json = self._build_bim(dataset_name, tables_m, relationships, data_source_path)
#             with open("debug_model.bim", "w", encoding="utf-8") as f:
#                 f.write(bim_json)
#             bim_b64   = base64.b64encode(bim_json.encode("utf-8")).decode("ascii")
#             pbism_b64 = base64.b64encode(b'{"version":"1.0"}').decode("ascii")

#             payload = {
#                 "displayName": dataset_name,
#                 "definition": {
#                     "parts": [
#                         {"path": "definition.pbism", "payload": pbism_b64, "payloadType": "InlineBase64"},
#                         {"path": "model.bim",        "payload": bim_b64,   "payloadType": "InlineBase64"},
#                     ]
#                 }
#             }

#             url = (
#                 f"https://api.fabric.microsoft.com/v1/workspaces"
#                 f"/{self.workspace_id}/semanticModels"
#             )
#             logger.info("[Fabric API] POST %s", url)

#             bim_obj = json.loads(bim_json)
#             for tbl in bim_obj.get("model", {}).get("tables", []):
#                 parts = tbl.get("partitions", [{}])
#                 expr_lines = parts[0].get("source", {}).get("expression", [])
#                 expr_preview = "\n".join(expr_lines)[:1000]
#                 logger.info("[Fabric API] Table '%s' M expression:\n%s", tbl["name"], expr_preview)

#             resp = requests.post(url, headers=headers, json=payload, timeout=60)
#             logger.info("[Fabric API] Response: %d %s", resp.status_code, resp.text[:400])

#             if resp.status_code in (200, 201, 202):
#                 dataset_id = ""

#                 location_header = resp.headers.get("Location") or resp.headers.get("location")
#                 if location_header:
#                     match = re.search(r"[0-9a-fA-F-]{36}", location_header)
#                     if match:
#                         dataset_id = match.group(0)
#                         logger.info("[Fabric API] Dataset ID from initial header: %s", dataset_id)

#                 if resp.status_code == 202:
#                     op_url = resp.headers.get("Location")
#                     polled_id = self._poll(op_url, headers) if op_url else ""
#                     dataset_id = dataset_id or polled_id
#                 else:
#                     dataset_id = (resp.json() if resp.text.strip() else {}).get("id", "")

#                 if dataset_id == "SUCCEEDED_NO_ID":
#                     dataset_id = self._find_dataset_id(dataset_name, headers)
#                     logger.info("[Fabric API] Looked up dataset ID: %s", dataset_id)

#                 if dataset_id:
#                     logger.info("[Fabric API] Created: %s", dataset_id)
#                     return {
#                         "success": True,
#                         "method": "fabric_items_api",
#                         "dataset_id": dataset_id,
#                         "dataset_name": dataset_name,
#                         "workspace_url": f"https://app.powerbi.com/groups/{self.workspace_id}",
#                         "dataset_url": (
#                             f"https://app.powerbi.com/groups/{self.workspace_id}"
#                             f"/datasets/{dataset_id}"
#                         ),
#                         "message": (
#                             f"Semantic model '{dataset_name}' deployed via Fabric API "
#                             f"with {len(tables_m)} table(s) and full M Query support."
#                         ),
#                     }
#                 return {"success": False, "error": "Async op succeeded but no dataset ID returned"}

#             return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:400]}"}

#         except Exception as exc:
#             logger.exception("[Fabric API] Unexpected error")
#             return {"success": False, "error": str(exc)}

#     def _poll(self, op_url: str, headers: Dict, max_wait: int = 120) -> str:
#         logger.info("[Fabric API] Polling: %s", op_url)
#         for i in range(max_wait // 3):
#             time.sleep(3)
#             try:
#                 r = requests.get(op_url, headers=headers, timeout=15)
#                 if r.ok:
#                     body = r.json()
#                     status = body.get("status", "")
#                     logger.info("[Fabric API] Poll %d: %s", i + 1, status)
#                     if status == "Succeeded":
#                         logger.info("[Fabric API] Full success body: %s", json.dumps(body))
#                         return "SUCCEEDED_NO_ID"
#                     if status in ("Failed", "Cancelled"):
#                         logger.warning("[Fabric API] Op %s: %s", status, body)
#                         return ""
#             except Exception as ex:
#                 logger.warning("[Fabric API] Poll error: %s", ex)
#         logger.warning("[Fabric API] Polling timed out after %ds", max_wait)
#         return ""

#     def _find_dataset_id(self, dataset_name: str, headers: Dict) -> str:
#         """Look up a semantic model by name in the workspace."""
#         try:
#             url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.workspace_id}/semanticModels"
#             r = requests.get(url, headers=headers, timeout=15)
#             if r.ok:
#                 items = r.json().get("value", [])
#                 for item in items:
#                     if item.get("displayName") == dataset_name:
#                         return item.get("id", "")
#         except Exception as ex:
#             logger.warning("[Fabric API] Lookup error: %s", ex)
#         return ""

#     # -- Strategy 2: Push Dataset (fallback) ----------------------------------

#     def _deploy_push_dataset(
#         self,
#         dataset_name: str,
#         tables_m: List[Dict[str, Any]],
#     ) -> Dict[str, Any]:
#         try:
#             tables_payload = []
#             for t in tables_m:
#                 fields = t.get("fields", [])
#                 if fields:
#                     cols = [
#                         {"name": f["name"], "dataType": _tabular_type(f.get("type", "string"))}
#                         for f in fields
#                     ]
#                 else:
#                     cols = [{"name": "Value", "dataType": "string"}]
#                 tables_payload.append({"name": t["name"], "columns": cols})

#             payload = {
#                 "name": dataset_name,
#                 "defaultMode": "Push",
#                 "tables": tables_payload,
#             }
#             url = f"https://api.powerbi.com/v1.0/myorg/groups/{self.workspace_id}/datasets"
#             resp = requests.post(url, headers=self.pbi_headers, json=payload, timeout=30)

#             if resp.status_code in (200, 201, 202):
#                 dataset_id = resp.json().get("id", "")
#                 return {
#                     "success": True,
#                     "method": "push_dataset_fallback",
#                     "dataset_id": dataset_id,
#                     "dataset_name": dataset_name,
#                     "workspace_url": f"https://app.powerbi.com/groups/{self.workspace_id}",
#                     "message": (
#                         "Created via Push dataset fallback. "
#                         "Fabric API failed - no M Query or Model View."
#                     ),
#                 }
#             return {
#                 "success": False,
#                 "error": f"Push dataset failed: {resp.status_code} {resp.text[:300]}",
#             }
#         except Exception as exc:
#             logger.exception("[Push] Error")
#             return {"success": False, "error": str(exc)}


# # ─────────────────────────────────────────────────────────────────────────────
# # Token / flow cache helpers
# # ─────────────────────────────────────────────────────────────────────────────

# def _token_cache_path() -> str:
#     return os.path.join(os.path.dirname(__file__), ".pb_token_cache.json")

# def _device_flow_cache_path() -> str:
#     return os.path.join(os.path.dirname(__file__), ".pb_device_flow.json")

# def _cache_user_token(token: str):
#     try:
#         with open(_token_cache_path(), "w") as f:
#             json.dump({"token": token, "expires_at": time.time() + 3500}, f)
#     except Exception:
#         pass

# def _cache_device_flow(flow: Dict):
#     try:
#         with open(_device_flow_cache_path(), "w") as f:
#             json.dump(flow, f)
#     except Exception:
#         pass

# def _load_device_flow() -> Optional[Dict]:
#     try:
#         path = _device_flow_cache_path()
#         if os.path.exists(path):
#             with open(path) as f:
#                 return json.load(f)
#     except Exception:
#         pass
#     return None

# def _clear_device_flow():
#     try:
#         path = _device_flow_cache_path()
#         if os.path.exists(path):
#             os.unlink(path)
#     except Exception:
#         pass






# """
# powerbi_publisher.py  -  QlikAI Accelerator
# Publishes a semantic model to Microsoft Fabric / Power BI Premium workspace.

# Strategy:
#   1. Fabric Items API  (POST /v1/workspaces/{id}/semanticModels)
#      - Requires: definition.pbism (version 1.0) + model.bim (TMSL V3)
#      - model.bim MUST have compatibilityLevel=1550, defaultPowerBIDataSourceVersion="powerBI_V3"
#      - Tables MUST have explicit columns (Fabric does NOT infer from M on create)
#   2. Push Dataset API  (fallback - limited, no M Query)

# Auth: Service Principal client credentials (silent - no user interaction).
# """

# from ast import expr
# import base64
# import json
# import logging
# import os
# import re
# import time
# from typing import Any, Dict, List, Optional

# import requests

# logger = logging.getLogger(__name__)

# # ─────────────────────────────────────────────────────────────────────────────
# # Public entry point
# # ─────────────────────────────────────────────────────────────────────────────

# def publish_semantic_model(
#     dataset_name: str,
#     tables_m: List[Dict[str, Any]],
#     relationships: List[Dict[str, Any]] = None,
#     access_token: str = "",
#     data_source_path: str = "",
#     db_connection_string: str = "",
#     workspace_id: str = "",
# ) -> Dict[str, Any]:
#     """
#     Publish tables as a Power BI semantic model.

#     Each item in tables_m must have:
#         name         - table name
#         m_expression - full M Query (let ... in ...)
#         source_type  - 'inline' | 'csv' | 'qvd' | 'sql' | 'resident'
#         fields       - list of {name, type} dicts  <- used to build columns in BIM
#     """
#     relationships = relationships or []

#     if not workspace_id:
#         workspace_id = os.getenv("POWERBI_WORKSPACE_ID", "")
#     if not workspace_id:
#         return {"success": False, "error": "POWERBI_WORKSPACE_ID not set"}

#     if db_connection_string:
#         tables_m = _rewrite_for_db_connect(tables_m, db_connection_string)

#     token = access_token or _acquire_sp_token()
#     return _Publisher(workspace_id=workspace_id, access_token=token).publish(
#         dataset_name, tables_m, relationships, data_source_path
#     )


# # ─────────────────────────────────────────────────────────────────────────────
# # Auth
# # ─────────────────────────────────────────────────────────────────────────────

# def _acquire_sp_token(
#     scope: str = "https://analysis.windows.net/powerbi/api/.default",
# ) -> str:
#     """Acquire token via Service Principal (client credentials)."""
#     try:
#         import msal
#         tenant_id     = os.getenv("POWERBI_TENANT_ID", "")
#         client_id     = os.getenv("POWERBI_CLIENT_ID", "")
#         client_secret = os.getenv("POWERBI_CLIENT_SECRET", "")
#         if not all([tenant_id, client_id, client_secret]):
#             logger.warning("[Auth] SP credentials missing from environment")
#             return ""
#         app = msal.ConfidentialClientApplication(
#             client_id,
#             authority=f"https://login.microsoftonline.com/{tenant_id}",
#             client_credential=client_secret,
#         )
#         result = app.acquire_token_for_client(scopes=[scope])
#         token = result.get("access_token", "")
#         if token:
#             logger.info("[Auth] SP token acquired: %s", scope)
#         else:
#             logger.warning("[Auth] SP token failed: %s", result.get("error_description"))
#         return token
#     except Exception as exc:
#         logger.warning("[Auth] SP token error: %s", exc)
#         return ""


# def initiate_device_code_flow() -> Dict[str, Any]:
#     try:
#         import msal
#         tenant_id = os.getenv("POWERBI_TENANT_ID", "")
#         client_id = os.getenv("POWERBI_CLIENT_ID", "")
#         app = msal.PublicClientApplication(
#             client_id,
#             authority=f"https://login.microsoftonline.com/{tenant_id}",
#         )
#         flow = app.initiate_device_flow(
#             scopes=["https://analysis.windows.net/powerbi/api/.default"]
#         )
#         _cache_device_flow(flow)
#         return {
#             "success": True,
#             "device_code_url": "https://microsoft.com/devicelogin",
#             "user_code": flow.get("user_code", ""),
#             "message": flow.get("message", ""),
#         }
#     except Exception as exc:
#         return {"success": False, "error": str(exc)}


# def complete_device_code_flow() -> Dict[str, Any]:
#     try:
#         import msal
#         flow = _load_device_flow()
#         if not flow:
#             return {"success": False, "error": "No pending device code flow"}
#         tenant_id = os.getenv("POWERBI_TENANT_ID", "")
#         client_id = os.getenv("POWERBI_CLIENT_ID", "")
#         app = msal.PublicClientApplication(
#             client_id,
#             authority=f"https://login.microsoftonline.com/{tenant_id}",
#         )
#         result = app.acquire_token_by_device_flow(flow)
#         token = result.get("access_token", "")
#         if token:
#             _cache_user_token(token)
#             _clear_device_flow()
#             return {"success": True, "access_token": token}
#         return {"success": False, "error": result.get("error_description", "unknown")}
#     except Exception as exc:
#         return {"success": False, "error": str(exc)}


# def get_cached_user_token() -> str:
#     try:
#         path = _token_cache_path()
#         if os.path.exists(path):
#             data = json.loads(open(path).read())
#             if time.time() < data.get("expires_at", 0):
#                 return data.get("token", "")
#     except Exception:
#         pass
#     return ""


# # ─────────────────────────────────────────────────────────────────────────────
# # DB Connect rewriter
# # ─────────────────────────────────────────────────────────────────────────────

# def _rewrite_for_db_connect(
#     tables_m: List[Dict[str, Any]], connection: str
# ) -> List[Dict[str, Any]]:
#     out = []
#     for t in tables_m:
#         src = t.get("source_type", "").lower()
#         expr = t.get("m_expression", "")
#         if src == "resident" or "Table.NestedJoin" in expr:
#             out.append(t)
#             continue
#         if src in ("sql", "odbc") or "Sql.Database" in expr or "Odbc.Query" in expr:
#             out.append(t)
#             continue
#         new_expr = (
#             f'let\n'
#             f'    Source = Odbc.Query("{connection}", "SELECT * FROM [{t["name"]}]"),\n'
#             f'    Result = Source\nin\n    Result'
#         )
#         out.append({**t, "m_expression": new_expr, "source_type": "odbc"})
#     return out


# # ─────────────────────────────────────────────────────────────────────────────
# # Helper functions
# # ─────────────────────────────────────────────────────────────────────────────

# _QLIK_TO_TABULAR = {
#     "integer":   "int64",
#     "float":     "double",
#     "money":     "decimal",
#     "date":      "dateTime",
#     "datetime":  "dateTime",
#     "timestamp": "dateTime",
#     "boolean":   "boolean",
#     "bool":      "boolean",
#     "number":    "double",
# }


# def _tabular_type(qlik_type: str) -> str:
#     return _QLIK_TO_TABULAR.get((qlik_type or "").lower(), "string")


# def _infer_type_from_name(name: str) -> str:
#     """Infer type from column name heuristics.

#     Rules:
#     - Fields containing '-' are composite keys (DealerID-ServiceID) → always string
#     - Qlik qualified names like Table.FieldName → strip prefix, use just FieldName
#     - Fields ending with 'Number' (EngineNumber, ChassisNumber) → string, not integer
#     """
#     # Composite key: contains hyphen → always string (never integer/date)
#     if "-" in name:
#         return "string"
#     # Strip Qlik table-qualified prefix: "Dealer_Master.City_GeoInfo" → "City_GeoInfo"
#     n = name.split(".")[-1].lower().strip() if "." in name else name.lower().strip()
#     if any(x in n for x in ["date", "time", "timestamp", "created", "updated", "dob", "birth"]):
#         return "date"
#     if any(x in n for x in ["price", "cost", "amount", "revenue", "salary", "rate", "total", "tax", "discount", "margin"]):
#         return "number"
#     # "number" suffix (e.g. EngineNumber, ChassisNumber, Phone) → string
#     if n.endswith("number") or n.endswith("phone") or n.endswith("code"):
#         return "string"
#     if any(x in n for x in ["qty", "quantity", "year", "month", "day", "age", "rank", "km", "tons", "knots", "cc", "speed"]):
#         return "integer"
#     # Only plain "id" at end → integer (not "modelid" with table prefix)
#     if n == "id" or n.endswith("_id") and not n.endswith("number"):
#         return "integer"
#     if "count" in n:
#         return "integer"
#     return "string"


# # def _extract_fields_from_m(expr: str) -> list:
# #     """Extract column names and types from #table() type signature in M expression."""
# #     match = re.search(r"type\s+table\s+\[(.+?)\]", expr, re.DOTALL)
# #     if not match:
# #         logger.warning("[BIM] Could not extract fields from M expression")
# #         return []
# #     cols_str = match.group(1)
# #     type_map = {
# #         "text":       "string",
# #         "number":     "number",
# #         "date":       "date",
# #         "datetime":   "datetime",
# #         "logical":    "boolean",
# #         "Int64.Type": "integer",
# #     }
# #     fields = []
# #     for part in cols_str.split(","):
# #         part = part.strip()
# #         if "=" not in part:
# #             continue
# #         col_name = part.split("=")[0].strip().strip('#').strip('"')
# #         col_type_raw = part.split("=")[1].strip()
# #         mapped_type = type_map.get(col_type_raw, "string")
# #         if mapped_type == "string":
# #             mapped_type = _infer_type_from_name(col_name)
# #         fields.append({"name": col_name, "type": mapped_type})
# #     logger.info("[BIM] Extracted %d fields: %s", len(fields), [f["name"] for f in fields])
# #     return fields if fields else []
# def _extract_fields_from_m(expr: str) -> list:
#     """Extract column names and types from M expression.

#     Handles multiple patterns:
#     1. Table.TransformColumnTypes(..., {{"col1", type text}, {"col2", type number}})
#     2. type table [col1 = type text, col2 = type number]
#     3. CSV headers (last resort - from PromoteHeaders)

#     IMPORTANT: Qlik qualified field names like "Dealer_Master.City_GeoInfo" are
#     stripped to just "City_GeoInfo" — the CSV column has the plain name only.
#     Composite key fields like "DealerID-ServiceID" stay as-is but are typed as string.
#     """
#     import re

#     type_map = {
#         "text": "string",
#         "number": "number",
#         "date": "date",
#         "datetime": "datetime",
#         "logical": "boolean",
#         "Int64.Type": "integer",
#         "type text": "string",
#         "type number": "number",
#         "type date": "date",
#         "type datetime": "datetime",
#         "type logical": "boolean",
#         "type number": "number",
#     }

#     def _clean_col_name(raw: str) -> str:
#         """Strip Qlik table-qualified prefix from column name."""
#         # "Dealer_Master.City_GeoInfo" → "City_GeoInfo"
#         # "DealerID-ServiceID" → "DealerID-ServiceID" (keep as-is)
#         if "." in raw and not raw.startswith("#"):
#             return raw.split(".", 1)[-1]
#         return raw

#     fields = []

#     # Pattern 1: Table.TransformColumnTypes pattern (most common from mquery_converter)
#     transform_pattern = r'Table\.TransformColumnTypes\s*\(\s*[^,]+?\s*,\s*\{\s*(.+?)\s*\}\s*\)'
#     match = re.search(transform_pattern, expr, re.DOTALL)
#     if match:
#         cols_str = match.group(1)
#         logger.info("[Extract] Found Table.TransformColumnTypes pattern")

#         col_pattern = r'\{\s*"([^"]+)"\s*,\s*(Int64\.Type|type\s+\w+)\s*\}'
#         for col_match in re.finditer(col_pattern, cols_str):
#             raw_name = col_match.group(1)
#             col_name = _clean_col_name(raw_name)
#             col_type_raw = col_match.group(2).strip()
#             col_type = type_map.get(col_type_raw, "string")
#             # Composite key or qualified field → always string
#             if "-" in raw_name or (col_type == "string" and col_name != raw_name):
#                 col_type = "string"
#             elif col_type == "string":
#                 col_type = _infer_type_from_name(col_name)
#             fields.append({"name": col_name, "type": col_type})

#         if fields:
#             logger.info("[Extract] Extracted %d fields from TransformColumnTypes: %s",
#                         len(fields), [f["name"] for f in fields])
#             return fields

#     # Pattern 2: type table [...] pattern (for #table() definitions)
#     match = re.search(r"type\s+table\s+\[(.+?)\]", expr, re.DOTALL)
#     if match:
#         cols_str = match.group(1)
#         logger.info("[Extract] Found type table pattern")

#         for part in cols_str.split(","):
#             part = part.strip()
#             if "=" not in part:
#                 continue
#             try:
#                 raw_name = part.split("=")[0].strip().strip('#').strip('"')
#                 col_name = _clean_col_name(raw_name)
#                 col_type_raw = part.split("=")[1].strip()
#                 col_type = type_map.get(col_type_raw, "string")
#                 if "-" in raw_name or (col_type == "string" and col_name != raw_name):
#                     col_type = "string"
#                 elif col_type == "string":
#                     col_type = _infer_type_from_name(col_name)
#                 fields.append({"name": col_name, "type": col_type})
#             except Exception:
#                 continue

#         if fields:
#             logger.info("[Extract] Extracted %d fields from type table: %s",
#                         len(fields), [f["name"] for f in fields])
#             return fields

#     # Pattern 3: Fallback - extract from PromoteHeaders (CSV source)
#     if "PromoteHeaders" in expr or "PromotedHeaders" in expr:
#         logger.info("[Extract] Detected CSV PromoteHeaders - will infer schema at runtime")
#         return []

#     logger.warning("[Extract] Could not extract fields from M expression - will use placeholder")
#     return []


# # Note: The M expression must have explicit column definitions for Fabric API to work.


# def _fix_multiline_rows(expr: str) -> str:
#     """
#     Ensure every data row in a #table() M expression is on a single line.
#     Rows start with { and end with } or },
#     Any continuation lines are joined onto the opening line.
#     """
#     lines = expr.split("\n")
#     result = []
#     in_row = False
#     current_row = ""

#     for line in lines:
#         stripped = line.strip()

#         if in_row:
#             current_row += " " + stripped
#             # Row complete when closing brace found (with or without trailing comma)
#             if re.search(r'\}\s*,?\s*$', stripped):
#                 result.append(current_row)
#                 current_row = ""
#                 in_row = False
#         else:
#             if stripped.startswith('{"') or stripped.startswith("{'"):
#                 if re.search(r'\}\s*,?\s*$', stripped):
#                     # Complete row on one line
#                     result.append(line)
#                 else:
#                     # Incomplete row - start buffering
#                     in_row = True
#                     current_row = line.rstrip()
#             else:
#                 result.append(line)

#     if current_row:
#         result.append(current_row)

#     return "\n".join(result)


# def _sanitize_m(expr: str) -> str:
#     """M expressions from mquery_converter are already valid - return as-is."""
#     return expr


# # ─────────────────────────────────────────────────────────────────────────────
# # Publisher
# # ─────────────────────────────────────────────────────────────────────────────

# class _Publisher:

#     def __init__(self, workspace_id: str, access_token: str = ""):
#         self.workspace_id = workspace_id
#         self.token = access_token
#         self.pbi_headers = {
#             "Authorization": f"Bearer {self.token}",
#             "Content-Type": "application/json",
#         }

#     # -- main entry -----------------------------------------------------------

#     def publish(
#         self,
#         dataset_name: str,
#         tables_m: List[Dict[str, Any]],
#         relationships: List[Dict[str, Any]],
#         data_source_path: str,
#     ) -> Dict[str, Any]:
#         if not self.token:
#             flow = initiate_device_code_flow()
#             return {
#                 "success": False, "auth_required": True,
#                 "device_code_url": flow.get("device_code_url"),
#                 "user_code": flow.get("user_code"),
#                 "message": flow.get("message", ""),
#                 "error": "Authentication required.",
#             }

#         result = self._deploy_via_fabric(dataset_name, tables_m, relationships, data_source_path)
#         if result.get("success"):
#             return result

#         logger.warning("[Publisher] Fabric API failed (%s) — Push dataset fallback", result.get("error"))
#         return self._deploy_push_dataset(dataset_name, tables_m)

#     # -- BIM builder ----------------------------------------------------------

#     def _build_bim(
#         self,
#         dataset_name: str,
#         tables_m: List[Dict[str, Any]],
#         relationships: List[Dict[str, Any]],
#         data_source_path: str,
#     ) -> str:
#         tmd_tables = []
#         for t in tables_m:
#             expr = t.get("m_expression", "").strip()
#             if not expr:
#                 continue
#             logger.info("==== RAW M FROM tables_m FOR TABLE %s ====", t["name"])
#             logger.info("\n%s\n", expr)    
#             fields = t.get("fields", [])
#             logger.info("[BIM] Table '%s' fields: %s", t["name"], fields)
#             if not fields:
#                 fields = _extract_fields_from_m(expr)
#                 logger.info("[BIM] Extracted fields for '%s': %s", t["name"], fields)

#             columns = []
#             for f in fields:
#                 columns.append({
#                     "name": f["name"],
#                     "dataType": _tabular_type(f.get("type", "string")),
#                     "sourceColumn": f["name"],
#                     "summarizeBy": "none",
#                     "annotations": [{"name": "SummarizationSetBy", "value": "Automatic"}]
#                 })

#             if not columns:
#                 columns = [{
#                     "name": "Value",
#                     "dataType": "string",
#                     "sourceColumn": "Value",
#                     "summarizeBy": "none",
#                     "annotations": [{"name": "SummarizationSetBy", "value": "Automatic"}]
#                 }]

#             fixed_expr = _fix_multiline_rows(_sanitize_m(expr))
#             logger.info("==== FINAL M SENT TO FABRIC FOR TABLE %s ====", t["name"])
#             logger.info("\n%s\n", fixed_expr)
#             tmd_tables.append({
#                 "name": t["name"],
#                 "columns": columns,
#                 "partitions": [{
#                     "name": f"{t['name']}-Partition",
#                     "mode": "import",
#                     "source": {
#                         "type": "m",
#                         "expression": fixed_expr.splitlines()
#                     }
#                 }]
#             })

#         tmd_rels = []
#         for r in relationships:
#             ft = r.get("fromTable") or r.get("from_table", "")
#             fc = r.get("fromColumn") or r.get("from_column", "")
#             tt = r.get("toTable")   or r.get("to_table", "")
#             tc = r.get("toColumn")  or r.get("to_column", "")
#             if ft and fc and tt and tc:
#                 tmd_rels.append({
#                     "name": f"{ft}_{fc}_{tt}_{tc}",
#                     "fromTable": ft, "fromColumn": fc,
#                     "toTable": tt,   "toColumn": tc,
#                     "crossFilteringBehavior": "oneDirection"
#                 })

#         expressions = []
#         if data_source_path:
#             expressions.append({
#                 "name": "DataSourcePath",
#                 "kind": "m",
#                 "expression": [f'"{data_source_path}"']
#             })

#         bim = {
#             "name": dataset_name,
#             "compatibilityLevel": 1550,
#             "model": {
#                 "culture": "en-US",
#                 "dataAccessOptions": {
#                     "legacyRedirects": True,
#                     "returnErrorValuesAsNull": True
#                 },
#                 "defaultPowerBIDataSourceVersion": "powerBI_V3",
#                 "sourceQueryCulture": "en-US",
#                 "tables": tmd_tables,
#                 "relationships": tmd_rels,
#                 "expressions": expressions,
#                 "annotations": [
#                     {"name": "PBIDesktopVersion", "value": "2.130.930.0"},
#                     {"name": "createdBy", "value": "QlikAI_Accelerator"},
#                 ]
#             }
#         }
#         return json.dumps(bim, ensure_ascii=False, indent=2)

#     # -- Strategy 1: Fabric Items API -----------------------------------------

#     def _deploy_via_fabric(
#         self,
#         dataset_name: str,
#         tables_m: List[Dict[str, Any]],
#         relationships: List[Dict[str, Any]],
#         data_source_path: str,
#     ) -> Dict[str, Any]:
#         try:
#             fabric_token = _acquire_sp_token("https://api.fabric.microsoft.com/.default")
#             if not fabric_token:
#                 fabric_token = self.token

#             headers = {
#                 "Authorization": f"Bearer {fabric_token}",
#                 "Content-Type": "application/json",
#             }

#             bim_json = self._build_bim(dataset_name, tables_m, relationships, data_source_path)
#             with open("debug_model.bim", "w", encoding="utf-8") as f:
#                 f.write(bim_json)
#             bim_b64   = base64.b64encode(bim_json.encode("utf-8")).decode("ascii")
#             pbism_b64 = base64.b64encode(b'{"version":"1.0"}').decode("ascii")

#             payload = {
#                 "displayName": dataset_name,
#                 "definition": {
#                     "parts": [
#                         {"path": "definition.pbism", "payload": pbism_b64, "payloadType": "InlineBase64"},
#                         {"path": "model.bim",        "payload": bim_b64,   "payloadType": "InlineBase64"},
#                     ]
#                 }
#             }

#             url = (
#                 f"https://api.fabric.microsoft.com/v1/workspaces"
#                 f"/{self.workspace_id}/semanticModels"
#             )
#             logger.info("[Fabric API] POST %s", url)

#             bim_obj = json.loads(bim_json)
#             for tbl in bim_obj.get("model", {}).get("tables", []):
#                 parts = tbl.get("partitions", [{}])
#                 expr_lines = parts[0].get("source", {}).get("expression", [])
#                 expr_preview = "\n".join(expr_lines)[:1000]
#                 logger.info("[Fabric API] Table '%s' M expression:\n%s", tbl["name"], expr_preview)

#             resp = requests.post(url, headers=headers, json=payload, timeout=60)
#             logger.info("[Fabric API] Response: %d %s", resp.status_code, resp.text[:400])

#             if resp.status_code in (200, 201, 202):
#                 dataset_id = ""

#                 location_header = resp.headers.get("Location") or resp.headers.get("location")
#                 if location_header:
#                     match = re.search(r"[0-9a-fA-F-]{36}", location_header)
#                     if match:
#                         dataset_id = match.group(0)
#                         logger.info("[Fabric API] Dataset ID from initial header: %s", dataset_id)

#                 if resp.status_code == 202:
#                     op_url = resp.headers.get("Location")
#                     polled_id = self._poll(op_url, headers) if op_url else ""
#                     dataset_id = dataset_id or polled_id
#                 else:
#                     dataset_id = (resp.json() if resp.text.strip() else {}).get("id", "")

#                 if dataset_id == "SUCCEEDED_NO_ID":
#                     dataset_id = self._find_dataset_id(dataset_name, headers)
#                     logger.info("[Fabric API] Looked up dataset ID: %s", dataset_id)

#                 if dataset_id:
#                     logger.info("[Fabric API] Created: %s", dataset_id)
#                     return {
#                         "success": True,
#                         "method": "fabric_items_api",
#                         "dataset_id": dataset_id,
#                         "dataset_name": dataset_name,
#                         "workspace_url": f"https://app.powerbi.com/groups/{self.workspace_id}",
#                         "dataset_url": (
#                             f"https://app.powerbi.com/groups/{self.workspace_id}"
#                             f"/datasets/{dataset_id}"
#                         ),
#                         "message": (
#                             f"Semantic model '{dataset_name}' deployed via Fabric API "
#                             f"with {len(tables_m)} table(s) and full M Query support."
#                         ),
#                     }
#                 return {"success": False, "error": "Async op succeeded but no dataset ID returned"}

#             return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:400]}"}

#         except Exception as exc:
#             logger.exception("[Fabric API] Unexpected error")
#             return {"success": False, "error": str(exc)}

#     def _poll(self, op_url: str, headers: Dict, max_wait: int = 120) -> str:
#         logger.info("[Fabric API] Polling: %s", op_url)
#         for i in range(max_wait // 3):
#             time.sleep(3)
#             try:
#                 r = requests.get(op_url, headers=headers, timeout=15)
#                 if r.ok:
#                     body = r.json()
#                     status = body.get("status", "")
#                     logger.info("[Fabric API] Poll %d: %s", i + 1, status)
#                     if status == "Succeeded":
#                         logger.info("[Fabric API] Full success body: %s", json.dumps(body))
#                         return "SUCCEEDED_NO_ID"
#                     if status in ("Failed", "Cancelled"):
#                         logger.warning("[Fabric API] Op %s: %s", status, body)
#                         return ""
#             except Exception as ex:
#                 logger.warning("[Fabric API] Poll error: %s", ex)
#         logger.warning("[Fabric API] Polling timed out after %ds", max_wait)
#         return ""

#     def _find_dataset_id(self, dataset_name: str, headers: Dict) -> str:
#         """Look up a semantic model by name in the workspace."""
#         try:
#             url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.workspace_id}/semanticModels"
#             r = requests.get(url, headers=headers, timeout=15)
#             if r.ok:
#                 items = r.json().get("value", [])
#                 for item in items:
#                     if item.get("displayName") == dataset_name:
#                         return item.get("id", "")
#         except Exception as ex:
#             logger.warning("[Fabric API] Lookup error: %s", ex)
#         return ""

#     # -- Strategy 2: Push Dataset (fallback) ----------------------------------

#     def _deploy_push_dataset(
#         self,
#         dataset_name: str,
#         tables_m: List[Dict[str, Any]],
#     ) -> Dict[str, Any]:
#         try:
#             tables_payload = []
#             for t in tables_m:
#                 fields = t.get("fields", [])
#                 if fields:
#                     cols = [
#                         {"name": f["name"], "dataType": _tabular_type(f.get("type", "string"))}
#                         for f in fields
#                     ]
#                 else:
#                     cols = [{"name": "Value", "dataType": "string"}]
#                 tables_payload.append({"name": t["name"], "columns": cols})

#             payload = {
#                 "name": dataset_name,
#                 "defaultMode": "Push",
#                 "tables": tables_payload,
#             }
#             url = f"https://api.powerbi.com/v1.0/myorg/groups/{self.workspace_id}/datasets"
#             resp = requests.post(url, headers=self.pbi_headers, json=payload, timeout=30)

#             if resp.status_code in (200, 201, 202):
#                 dataset_id = resp.json().get("id", "")
#                 return {
#                     "success": True,
#                     "method": "push_dataset_fallback",
#                     "dataset_id": dataset_id,
#                     "dataset_name": dataset_name,
#                     "workspace_url": f"https://app.powerbi.com/groups/{self.workspace_id}",
#                     "message": (
#                         "Created via Push dataset fallback. "
#                         "Fabric API failed - no M Query or Model View."
#                     ),
#                 }
#             return {
#                 "success": False,
#                 "error": f"Push dataset failed: {resp.status_code} {resp.text[:300]}",
#             }
#         except Exception as exc:
#             logger.exception("[Push] Error")
#             return {"success": False, "error": str(exc)}


# # ─────────────────────────────────────────────────────────────────────────────
# # Token / flow cache helpers
# # ─────────────────────────────────────────────────────────────────────────────

# def _token_cache_path() -> str:
#     return os.path.join(os.path.dirname(__file__), ".pb_token_cache.json")

# def _device_flow_cache_path() -> str:
#     return os.path.join(os.path.dirname(__file__), ".pb_device_flow.json")

# def _cache_user_token(token: str):
#     try:
#         with open(_token_cache_path(), "w") as f:
#             json.dump({"token": token, "expires_at": time.time() + 3500}, f)
#     except Exception:
#         pass

# def _cache_device_flow(flow: Dict):
#     try:
#         with open(_device_flow_cache_path(), "w") as f:
#             json.dump(flow, f)
#     except Exception:
#         pass

# def _load_device_flow() -> Optional[Dict]:
#     try:
#         path = _device_flow_cache_path()
#         if os.path.exists(path):
#             with open(path) as f:
#                 return json.load(f)
#     except Exception:
#         pass
#     return None

# def _clear_device_flow():
#     try:
#         path = _device_flow_cache_path()
#         if os.path.exists(path):
#             os.unlink(path)
#     except Exception:
#         pass



"""
powerbi_publisher.py  -  QlikAI Accelerator
Publishes a semantic model to Microsoft Fabric / Power BI Premium workspace.

Strategy:
  1. Fabric Items API  (POST /v1/workspaces/{id}/semanticModels)
     - Requires: definition.pbism (version 1.0) + model.bim (TMSL V3)
     - model.bim MUST have compatibilityLevel=1550, defaultPowerBIDataSourceVersion="powerBI_V3"
     - Tables MUST have explicit columns (Fabric does NOT infer from M on create)
  2. Push Dataset API  (fallback - limited, no M Query)

Auth: Service Principal client credentials (silent - no user interaction).

FIXES (v2):
  - Qlik-qualified column names (Table.Column) stripped to plain column name in BIM
  - Composite key columns (DealerID-ServiceID) always typed as string, never integer
  - Field extraction now handles SharePoint.Files() M expressions correctly
"""

from ast import expr
import base64
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def publish_semantic_model(
    dataset_name: str,
    tables_m: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]] = None,
    access_token: str = "",
    data_source_path: str = "",
    db_connection_string: str = "",
    workspace_id: str = "",
) -> Dict[str, Any]:
    """
    Publish tables as a Power BI semantic model.

    Each item in tables_m must have:
        name         - table name
        m_expression - full M Query (let ... in ...)
        source_type  - 'inline' | 'csv' | 'qvd' | 'sql' | 'resident'
        fields       - list of {name, type} dicts  <- used to build columns in BIM
    """
    relationships = relationships or []

    if not workspace_id:
        workspace_id = os.getenv("POWERBI_WORKSPACE_ID", "")
    if not workspace_id:
        return {"success": False, "error": "POWERBI_WORKSPACE_ID not set"}

    if db_connection_string:
        tables_m = _rewrite_for_db_connect(tables_m, db_connection_string)

    token = access_token or _acquire_sp_token()
    return _Publisher(workspace_id=workspace_id, access_token=token).publish(
        dataset_name, tables_m, relationships, data_source_path
    )


# ─────────────────────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────────────────────

def _acquire_sp_token(
    scope: str = "https://analysis.windows.net/powerbi/api/.default",
) -> str:
    """Acquire token via Service Principal (client credentials)."""
    try:
        import msal
        tenant_id     = os.getenv("POWERBI_TENANT_ID", "")
        client_id     = os.getenv("POWERBI_CLIENT_ID", "")
        client_secret = os.getenv("POWERBI_CLIENT_SECRET", "")
        if not all([tenant_id, client_id, client_secret]):
            logger.warning("[Auth] SP credentials missing from environment")
            return ""
        app = msal.ConfidentialClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret,
        )
        result = app.acquire_token_for_client(scopes=[scope])
        token = result.get("access_token", "")
        if token:
            logger.info("[Auth] SP token acquired: %s", scope)
        else:
            logger.warning("[Auth] SP token failed: %s", result.get("error_description"))
        return token
    except Exception as exc:
        logger.warning("[Auth] SP token error: %s", exc)
        return ""


def initiate_device_code_flow() -> Dict[str, Any]:
    try:
        import msal
        tenant_id = os.getenv("POWERBI_TENANT_ID", "")
        client_id = os.getenv("POWERBI_CLIENT_ID", "")
        app = msal.PublicClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
        )
        flow = app.initiate_device_flow(
            scopes=["https://analysis.windows.net/powerbi/api/.default"]
        )
        _cache_device_flow(flow)
        return {
            "success": True,
            "device_code_url": "https://microsoft.com/devicelogin",
            "user_code": flow.get("user_code", ""),
            "message": flow.get("message", ""),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def complete_device_code_flow() -> Dict[str, Any]:
    try:
        import msal
        flow = _load_device_flow()
        if not flow:
            return {"success": False, "error": "No pending device code flow"}
        tenant_id = os.getenv("POWERBI_TENANT_ID", "")
        client_id = os.getenv("POWERBI_CLIENT_ID", "")
        app = msal.PublicClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
        )
        result = app.acquire_token_by_device_flow(flow)
        token = result.get("access_token", "")
        if token:
            _cache_user_token(token)
            _clear_device_flow()
            return {"success": True, "access_token": token}
        return {"success": False, "error": result.get("error_description", "unknown")}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def get_cached_user_token() -> str:
    try:
        path = _token_cache_path()
        if os.path.exists(path):
            data = json.loads(open(path).read())
            if time.time() < data.get("expires_at", 0):
                return data.get("token", "")
    except Exception:
        pass
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# DB Connect rewriter
# ─────────────────────────────────────────────────────────────────────────────

def _rewrite_for_db_connect(
    tables_m: List[Dict[str, Any]], connection: str
) -> List[Dict[str, Any]]:
    out = []
    for t in tables_m:
        src = t.get("source_type", "").lower()
        expr = t.get("m_expression", "")
        if src == "resident" or "Table.NestedJoin" in expr:
            out.append(t)
            continue
        if src in ("sql", "odbc") or "Sql.Database" in expr or "Odbc.Query" in expr:
            out.append(t)
            continue
        new_expr = (
            f'let\n'
            f'    Source = Odbc.Query("{connection}", "SELECT * FROM [{t["name"]}]"),\n'
            f'    Result = Source\nin\n    Result'
        )
        out.append({**t, "m_expression": new_expr, "source_type": "odbc"})
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

_QLIK_TO_TABULAR = {
    "integer":   "int64",
    "float":     "double",
    "money":     "decimal",
    "date":      "dateTime",
    "datetime":  "dateTime",
    "timestamp": "dateTime",
    "boolean":   "boolean",
    "bool":      "boolean",
    "number":    "double",
}


def _tabular_type(qlik_type: str) -> str:
    return _QLIK_TO_TABULAR.get((qlik_type or "").lower(), "string")


def _strip_qlik_qualifier(col_name: str) -> str:
    """
    Strip Qlik table-qualified prefix from column name.
    
    'Dealer_Master.City_GeoInfo'  →  'City_GeoInfo'
    'Model_Master.ModelID'        →  'ModelID'
    'DealerID-ServiceID'          →  'DealerID-ServiceID'  (composite key, no change)
    '#"Something"'                →  '#"Something"'        (escaped, no change)
    
    This is critical: the actual CSV column name is just 'City_GeoInfo',
    NOT the Qlik-qualified 'Dealer_Master.City_GeoInfo'. Using the qualified
    name as a BIM column causes column-not-found errors at query time.
    """
    if not col_name or col_name.startswith("#"):
        return col_name
    # Only strip if dot present AND no hyphen (composite keys like DealerID-ServiceID keep their name)
    if "." in col_name and "-" not in col_name:
        return col_name.split(".", 1)[-1]
    return col_name


def _infer_type_from_name(name: str) -> str:
    """Infer type from column name heuristics.

    Rules:
    - Fields containing '-' are composite keys (DealerID-ServiceID) → always string
    - Qlik qualified names like Table.FieldName → strip prefix first
    - Fields ending with 'Number' (EngineNumber, ChassisNumber) → string, not integer
    """
    # Composite key → always string
    if "-" in name:
        return "string"
    # Strip Qlik table-qualified prefix
    n = name.split(".")[-1].lower().strip() if "." in name else name.lower().strip()
    if any(x in n for x in ["date", "time", "timestamp", "created", "updated", "dob", "birth"]):
        return "date"
    if any(x in n for x in ["price", "cost", "amount", "revenue", "salary", "rate", "total", "tax", "discount", "margin"]):
        return "number"
    # "number" suffix (e.g. EngineNumber, ChassisNumber, Phone) → string
    if n.endswith("number") or n.endswith("phone") or n.endswith("code"):
        return "string"
    if any(x in n for x in ["qty", "quantity", "year", "month", "day", "age", "rank", "km", "tons", "knots", "cc", "speed"]):
        return "integer"
    # Only plain "id" at end → integer (not "modelid" with table prefix)
    if n == "id" or (n.endswith("_id") and not n.endswith("number")):
        return "integer"
    if "count" in n:
        return "integer"
    return "string"


def _extract_fields_from_m(expr: str) -> list:
    """Extract column names and types from M expression.

    Handles multiple patterns:
    1. Table.TransformColumnTypes (from mquery_converter - most common)
    2. type table [...] (for #table() inline definitions)
    3. SharePoint.Files() patterns (same structure, just different Source)

    KEY FIX: Qlik-qualified field names like 'Dealer_Master.City_GeoInfo' are
    stripped to just 'City_GeoInfo' — matching the actual CSV column name.
    Composite key fields like 'DealerID-ServiceID' stay as-is and are always string.
    """
    type_map = {
        "text": "string",
        "number": "number",
        "date": "date",
        "datetime": "datetime",
        "logical": "boolean",
        "Int64.Type": "integer",
        "type text": "string",
        "type number": "number",
        "type date": "date",
        "type datetime": "datetime",
        "type logical": "boolean",
    }

    fields = []

    # Pattern 1: Table.TransformColumnTypes — most common output from mquery_converter
    # Matches: {"ColumnName", type text} or {"ColumnName", Int64.Type}
    transform_pattern = r'Table\.TransformColumnTypes\s*\(\s*[^,]+?\s*,\s*\{\s*(.+?)\s*\}\s*\)'
    match = re.search(transform_pattern, expr, re.DOTALL)
    if match:
        cols_str = match.group(1)
        logger.info("[Extract] Found Table.TransformColumnTypes pattern")

        col_pattern = r'\{\s*"([^"]+)"\s*,\s*(Int64\.Type|type\s+\w+)\s*\}'
        for col_match in re.finditer(col_pattern, cols_str):
            raw_name = col_match.group(1)
            # CRITICAL: strip Qlik-qualified prefix → use plain CSV column name
            col_name = _strip_qlik_qualifier(raw_name)
            col_type_raw = col_match.group(2).strip()
            col_type = type_map.get(col_type_raw, "string")

            # Composite key → always string
            if "-" in raw_name:
                col_type = "string"
            elif col_type == "string":
                col_type = _infer_type_from_name(col_name)

            fields.append({"name": col_name, "type": col_type})
            
            # Log when we strip a Qlik qualifier (helps debug)
            if col_name != raw_name:
                logger.info("[Extract] Stripped Qlik qualifier: '%s' → '%s'", raw_name, col_name)

        if fields:
            logger.info("[Extract] Extracted %d fields from TransformColumnTypes: %s",
                        len(fields), [f["name"] for f in fields])
            return fields

    # Pattern 2: type table [...] for #table() inline definitions
    match = re.search(r"type\s+table\s+\[(.+?)\]", expr, re.DOTALL)
    if match:
        cols_str = match.group(1)
        logger.info("[Extract] Found type table pattern")

        for part in cols_str.split(","):
            part = part.strip()
            if "=" not in part:
                continue
            try:
                raw_name = part.split("=")[0].strip().strip('#').strip('"')
                col_name = _strip_qlik_qualifier(raw_name)
                col_type_raw = part.split("=")[1].strip()
                col_type = type_map.get(col_type_raw, "string")
                if "-" in raw_name:
                    col_type = "string"
                elif col_type == "string":
                    col_type = _infer_type_from_name(col_name)
                fields.append({"name": col_name, "type": col_type})
            except Exception:
                continue

        if fields:
            logger.info("[Extract] Extracted %d fields from type table: %s",
                        len(fields), [f["name"] for f in fields])
            return fields

    # Pattern 3: SharePoint.Files or PromoteHeaders without TransformColumnTypes
    if "SharePoint.Files" in expr or "PromoteHeaders" in expr or "PromotedHeaders" in expr:
        logger.info("[Extract] Detected SharePoint/PromoteHeaders source - schema inferred at runtime")
        return []

    logger.warning("[Extract] Could not extract fields from M expression - will use placeholder")
    return []


def _fix_multiline_rows(expr: str) -> str:
    """
    Ensure every data row in a #table() M expression is on a single line.
    """
    lines = expr.split("\n")
    result = []
    in_row = False
    current_row = ""

    for line in lines:
        stripped = line.strip()

        if in_row:
            current_row += " " + stripped
            if re.search(r'\}\s*,?\s*$', stripped):
                result.append(current_row)
                current_row = ""
                in_row = False
        else:
            if stripped.startswith('{"') or stripped.startswith("{'"):
                if re.search(r'\}\s*,?\s*$', stripped):
                    result.append(line)
                else:
                    in_row = True
                    current_row = line.rstrip()
            else:
                result.append(line)

    if current_row:
        result.append(current_row)

    return "\n".join(result)


def _sanitize_m(expr: str) -> str:
    """M expressions from mquery_converter are already valid - return as-is."""
    return expr


# ─────────────────────────────────────────────────────────────────────────────
# Publisher
# ─────────────────────────────────────────────────────────────────────────────

class _Publisher:

    def __init__(self, workspace_id: str, access_token: str = ""):
        self.workspace_id = workspace_id
        self.token = access_token
        self.pbi_headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    # -- main entry -----------------------------------------------------------

    def publish(
        self,
        dataset_name: str,
        tables_m: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        data_source_path: str,
    ) -> Dict[str, Any]:
        if not self.token:
            flow = initiate_device_code_flow()
            return {
                "success": False, "auth_required": True,
                "device_code_url": flow.get("device_code_url"),
                "user_code": flow.get("user_code"),
                "message": flow.get("message", ""),
                "error": "Authentication required.",
            }

        result = self._deploy_via_fabric(dataset_name, tables_m, relationships, data_source_path)
        if result.get("success"):
            return result

        logger.warning("[Publisher] Fabric API failed (%s) — Push dataset fallback", result.get("error"))
        return self._deploy_push_dataset(dataset_name, tables_m)

    # -- BIM builder ----------------------------------------------------------

    def _build_bim(
        self,
        dataset_name: str,
        tables_m: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        data_source_path: str,
    ) -> str:
        tmd_tables = []
        for t in tables_m:
            expr = t.get("m_expression", "").strip()
            if not expr:
                continue
            logger.info("==== RAW M FROM tables_m FOR TABLE %s ====", t["name"])
            logger.info("\n%s\n", expr)

            fields = t.get("fields", [])
            logger.info("[BIM] Table '%s' raw fields from tables_m: %s", t["name"], fields)

            if not fields:
                fields = _extract_fields_from_m(expr)
                logger.info("[BIM] Extracted fields for '%s': %s", t["name"], fields)
            else:
                # CRITICAL: Even when fields are provided, strip Qlik-qualified names
                # to match what the M query actually produces as column names.
                fixed_fields = []
                for f in fields:
                    raw_name = f.get("name", "")
                    plain_name = _strip_qlik_qualifier(raw_name)
                    # Composite keys always string
                    ftype = f.get("type", "string")
                    if "-" in raw_name:
                        ftype = "string"
                    fixed_fields.append({"name": plain_name, "type": ftype})
                    if plain_name != raw_name:
                        logger.info("[BIM] Fixed column name: '%s' → '%s'", raw_name, plain_name)
                fields = fixed_fields
                logger.info("[BIM] Fixed fields for '%s': %s", t["name"], fields)

            columns = []
            for f in fields:
                columns.append({
                    "name": f["name"],
                    "dataType": _tabular_type(f.get("type", "string")),
                    "sourceColumn": f["name"],
                    "summarizeBy": "none",
                    "annotations": [{"name": "SummarizationSetBy", "value": "Automatic"}]
                })

            if not columns:
                columns = [{
                    "name": "Value",
                    "dataType": "string",
                    "sourceColumn": "Value",
                    "summarizeBy": "none",
                    "annotations": [{"name": "SummarizationSetBy", "value": "Automatic"}]
                }]

            fixed_expr = _fix_multiline_rows(_sanitize_m(expr))
            logger.info("==== FINAL M SENT TO FABRIC FOR TABLE %s ====", t["name"])
            logger.info("\n%s\n", fixed_expr)
            tmd_tables.append({
                "name": t["name"],
                "columns": columns,
                "partitions": [{
                    "name": f"{t['name']}-Partition",
                    "mode": "import",
                    "source": {
                        "type": "m",
                        "expression": fixed_expr.splitlines()
                    }
                }]
            })

        tmd_rels = []
        for r in relationships:
            ft = r.get("fromTable") or r.get("from_table", "")
            fc = r.get("fromColumn") or r.get("from_column", "")
            tt = r.get("toTable")   or r.get("to_table", "")
            tc = r.get("toColumn")  or r.get("to_column", "")
            # CRITICAL: Strip Qlik-qualified names from relationship columns too
            fc = _strip_qlik_qualifier(fc)
            tc = _strip_qlik_qualifier(tc)
            if ft and fc and tt and tc:
                tmd_rels.append({
                    "name": f"{ft}_{fc}_{tt}_{tc}",
                    "fromTable": ft, "fromColumn": fc,
                    "toTable": tt,   "toColumn": tc,
                    "crossFilteringBehavior": "oneDirection"
                })

        expressions = []
        if data_source_path:
            expressions.append({
                "name": "DataSourcePath",
                "kind": "m",
                "expression": [f'"{data_source_path}"']
            })

        bim = {
            "name": dataset_name,
            "compatibilityLevel": 1550,
            "model": {
                "culture": "en-US",
                "dataAccessOptions": {
                    "legacyRedirects": True,
                    "returnErrorValuesAsNull": True
                },
                "defaultPowerBIDataSourceVersion": "powerBI_V3",
                "sourceQueryCulture": "en-US",
                "tables": tmd_tables,
                "relationships": tmd_rels,
                "expressions": expressions,
                "annotations": [
                    {"name": "PBIDesktopVersion", "value": "2.130.930.0"},
                    {"name": "createdBy", "value": "QlikAI_Accelerator"},
                ]
            }
        }
        return json.dumps(bim, ensure_ascii=False, indent=2)

    # -- Strategy 1: Fabric Items API -----------------------------------------

    def _deploy_via_fabric(
        self,
        dataset_name: str,
        tables_m: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        data_source_path: str,
    ) -> Dict[str, Any]:
        try:
            fabric_token = _acquire_sp_token("https://api.fabric.microsoft.com/.default")
            if not fabric_token:
                fabric_token = self.token

            headers = {
                "Authorization": f"Bearer {fabric_token}",
                "Content-Type": "application/json",
            }

            bim_json = self._build_bim(dataset_name, tables_m, relationships, data_source_path)
            with open("debug_model.bim", "w", encoding="utf-8") as f:
                f.write(bim_json)
            bim_b64   = base64.b64encode(bim_json.encode("utf-8")).decode("ascii")
            pbism_b64 = base64.b64encode(b'{"version":"1.0"}').decode("ascii")

            payload = {
                "displayName": dataset_name,
                "definition": {
                    "parts": [
                        {"path": "definition.pbism", "payload": pbism_b64, "payloadType": "InlineBase64"},
                        {"path": "model.bim",        "payload": bim_b64,   "payloadType": "InlineBase64"},
                    ]
                }
            }

            url = (
                f"https://api.fabric.microsoft.com/v1/workspaces"
                f"/{self.workspace_id}/semanticModels"
            )
            logger.info("[Fabric API] POST %s", url)

            bim_obj = json.loads(bim_json)
            for tbl in bim_obj.get("model", {}).get("tables", []):
                parts = tbl.get("partitions", [{}])
                expr_lines = parts[0].get("source", {}).get("expression", [])
                expr_preview = "\n".join(expr_lines)[:1000]
                logger.info("[Fabric API] Table '%s' M expression:\n%s", tbl["name"], expr_preview)

            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            logger.info("[Fabric API] Response: %d %s", resp.status_code, resp.text[:400])

            if resp.status_code in (200, 201, 202):
                dataset_id = ""

                location_header = resp.headers.get("Location") or resp.headers.get("location")
                if location_header:
                    match = re.search(r"[0-9a-fA-F-]{36}", location_header)
                    if match:
                        dataset_id = match.group(0)
                        logger.info("[Fabric API] Dataset ID from initial header: %s", dataset_id)

                if resp.status_code == 202:
                    op_url = resp.headers.get("Location")
                    polled_id = self._poll(op_url, headers) if op_url else ""
                    if polled_id == "SUCCEEDED_NO_ID":
                        dataset_id = ""
                else:
                    dataset_id = (resp.json() if resp.text.strip() else {}).get("id", "")

                # After polling/response, must lookup actual semantic model ID by name
                # The Location header ID is the Operation ID (temporary), NOT the model ID
                if not dataset_id or dataset_id == "SUCCEEDED_NO_ID":
                    dataset_id = self._find_dataset_id(dataset_name, headers)
                    logger.info("[Fabric API] Looked up semantic model ID: %s", dataset_id)

                if dataset_id:
                    logger.info("[Fabric API] Created: %s", dataset_id)
                    
                    # Trigger refresh using Power BI API (NOT Fabric Items API)
                    pbi_token = _acquire_sp_token("https://analysis.windows.net/powerbi/api/.default")
                    pbi_headers = {
                        "Authorization": f"Bearer {pbi_token}",
                        "Content-Type": "application/json",
                    }
                    self._trigger_refresh(dataset_id, pbi_headers)
                    
                    return {
                        "success": True,
                        "method": "fabric_items_api",
                        "dataset_id": dataset_id,
                        "dataset_name": dataset_name,
                        "workspace_url": f"https://app.powerbi.com/groups/{self.workspace_id}",
                        "dataset_url": (
                            f"https://app.powerbi.com/groups/{self.workspace_id}"
                            f"/datasets/{dataset_id}"
                        ),
                        "message": (
                            f"Semantic model '{dataset_name}' deployed via Fabric API "
                            f"with {len(tables_m)} table(s) and full M Query support."
                        ),
                    }
                return {"success": False, "error": "Async op succeeded but no dataset ID returned"}

            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:400]}"}

        except Exception as exc:
            logger.exception("[Fabric API] Unexpected error")
            return {"success": False, "error": str(exc)}

    def _poll(self, op_url: str, headers: Dict, max_wait: int = 120) -> str:
        logger.info("[Fabric API] Polling: %s", op_url)
        for i in range(max_wait // 3):
            time.sleep(3)
            try:
                r = requests.get(op_url, headers=headers, timeout=15)
                if r.ok:
                    body = r.json()
                    status = body.get("status", "")
                    logger.info("[Fabric API] Poll %d: %s", i + 1, status)
                    if status == "Succeeded":
                        logger.info("[Fabric API] Full success body: %s", json.dumps(body))
                        return "SUCCEEDED_NO_ID"
                    if status in ("Failed", "Cancelled"):
                        logger.warning("[Fabric API] Op %s: %s", status, body)
                        return ""
            except Exception as ex:
                logger.warning("[Fabric API] Poll error: %s", ex)
        logger.warning("[Fabric API] Polling timed out after %ds", max_wait)
        return ""

    def _find_dataset_id(self, dataset_name: str, headers: Dict) -> str:
        """Look up a semantic model by name in the workspace.
        
        CRITICAL: After async model creation (202 response), the Location header
        contains an Operation ID (temporary). We must query the workspace to get
        the REAL semantic model ID to use for subsequent operations like refresh.
        """
        try:
            url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.workspace_id}/semanticModels"
            logger.info("[Fabric API] Looking up real semantic model ID by name: %s", dataset_name)
            r = requests.get(url, headers=headers, timeout=15)
            if r.ok:
                items = r.json().get("value", [])
                logger.info("[Fabric API] Found %d semantic models in workspace", len(items))
                for item in items:
                    display_name = item.get("displayName", "")
                    item_id = item.get("id", "")
                    if display_name == dataset_name:
                        logger.info("[Fabric API] ✅ Matched '%s' → ID: %s", display_name, item_id)
                        return item_id
                logger.warning("[Fabric API] ⚠️  No semantic model found with name: %s", dataset_name)
            else:
                logger.warning("[Fabric API] Lookup failed: %d %s", r.status_code, r.text[:200])
        except Exception as ex:
            logger.warning("[Fabric API] Lookup error: %s", ex)
        return ""

    def _trigger_refresh(self, dataset_id: str, headers: Dict) -> bool:
        try:
            # Use Power BI API endpoint for semantic model refresh
            url = (
                f"https://api.powerbi.com/v1.0/myorg/groups/"
                f"{self.workspace_id}/datasets/{dataset_id}/refreshes"
            )

            logger.info("[Power BI API] Triggering refresh: POST %s", url)
            logger.info("[Power BI API] Using semantic model ID: %s", dataset_id)

            resp = requests.post(url, headers=headers, json={}, timeout=30)

            if resp.status_code in (200, 202):
                logger.info("[Power BI API] ✅ Refresh triggered successfully - M query will execute and data will load")
                return True
            elif resp.status_code == 404:
                logger.warning("[Power BI API] ⚠️  404: Dataset not found. Verify the semantic model ID is correct")
                return False
            else:
                logger.warning(
                    "[Power BI API] Refresh failed: %d %s",
                    resp.status_code,
                    resp.text[:300]
                )
                return False

        except Exception as ex:
            logger.error("[Power BI API] Refresh error: %s", ex)
            return False

    # -- Strategy 2: Push Dataset (fallback) ----------------------------------

    def _deploy_push_dataset(
        self,
        dataset_name: str,
        tables_m: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        try:
            tables_payload = []
            for t in tables_m:
                fields = t.get("fields", [])
                if fields:
                    cols = []
                    for f in fields:
                        plain_name = _strip_qlik_qualifier(f.get("name", ""))
                        ftype = f.get("type", "string")
                        if "-" in f.get("name", ""):
                            ftype = "string"
                        cols.append({"name": plain_name, "dataType": _tabular_type(ftype)})
                else:
                    cols = [{"name": "Value", "dataType": "string"}]
                tables_payload.append({"name": t["name"], "columns": cols})

            payload = {
                "name": dataset_name,
                "defaultMode": "Push",
                "tables": tables_payload,
            }
            # url = f"https://api.powerbi.com/v1.0/myorg/groups/{self.workspace_id}/datasets"
            url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.workspace_id}/items/{dataset_id}/refreshes"
            resp = requests.post(url, headers=self.pbi_headers, json=payload, timeout=30)

            if resp.status_code in (200, 201, 202):
                dataset_id = resp.json().get("id", "")
                return {
                    "success": True,
                    "method": "push_dataset_fallback",
                    "dataset_id": dataset_id,
                    "dataset_name": dataset_name,
                    "workspace_url": f"https://app.powerbi.com/groups/{self.workspace_id}",
                    "message": (
                        "Created via Push dataset fallback. "
                        "Fabric API failed - no M Query or Model View."
                    ),
                }
            return {
                "success": False,
                "error": f"Push dataset failed: {resp.status_code} {resp.text[:300]}",
            }
        except Exception as exc:
            logger.exception("[Push] Error")
            return {"success": False, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# Token / flow cache helpers
# ─────────────────────────────────────────────────────────────────────────────

def _token_cache_path() -> str:
    return os.path.join(os.path.dirname(__file__), ".pb_token_cache.json")

def _device_flow_cache_path() -> str:
    return os.path.join(os.path.dirname(__file__), ".pb_device_flow.json")

def _cache_user_token(token: str):
    try:
        with open(_token_cache_path(), "w") as f:
            json.dump({"token": token, "expires_at": time.time() + 3500}, f)
    except Exception:
        pass

def _cache_device_flow(flow: Dict):
    try:
        with open(_device_flow_cache_path(), "w") as f:
            json.dump(flow, f)
    except Exception:
        pass

def _load_device_flow() -> Optional[Dict]:
    try:
        path = _device_flow_cache_path()
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return None

def _clear_device_flow():
    try:
        path = _device_flow_cache_path()
        if os.path.exists(path):
            os.unlink(path)
    except Exception:
        pass