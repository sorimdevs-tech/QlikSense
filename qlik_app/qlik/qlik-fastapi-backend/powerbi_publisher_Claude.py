"""
powerbi_publisher.py  –  QlikAI Accelerator
Publishes a semantic model to Microsoft Fabric / Power BI Premium workspace.

Strategy:
  1. Fabric Items API  (POST /v1/workspaces/{id}/semanticModels)
     – Requires: definition.pbism (version 1.0) + model.bim (TMSL V3)
     – model.bim MUST have compatibilityLevel=1550, defaultPowerBIDataSourceVersion="powerBI_V3"
     – Tables MUST have explicit columns (Fabric does NOT infer from M on create)
  2. Push Dataset API  (fallback — limited, no M Query)

Auth: Service Principal client credentials (silent — no user interaction).
"""

import base64
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────────────────

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
        name         – table name
        m_expression – full M Query (let … in …)
        source_type  – 'inline' | 'csv' | 'qvd' | 'sql' | 'resident'
        fields       – list of {name, type} dicts  ← used to build columns in BIM
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


# ──────────────────────────────────────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────────────────────
# DB Connect rewriter
# ──────────────────────────────────────────────────────────────────────────────

def _rewrite_for_db_connect(
    tables_m: List[Dict[str, Any]], connection: str
) -> List[Dict[str, Any]]:
    out = []
    for t in tables_m:
        src = t.get("source_type", "").lower()
        expr = t.get("m_expression", "")
        if src == "resident" or "Table.NestedJoin" in expr:
            out.append(t); continue
        if src in ("sql", "odbc") or "Sql.Database" in expr or "Odbc.Query" in expr:
            out.append(t); continue
        new_expr = (
            f'let\n'
            f'    Source = Odbc.Query("{connection}", "SELECT * FROM [{t["name"]}]"),\n'
            f'    Result = Source\nin\n    Result'
        )
        out.append({**t, "m_expression": new_expr, "source_type": "odbc"})
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Publisher
# ──────────────────────────────────────────────────────────────────────────────

_QLIK_TO_TABULAR = {
    "integer": "int64",
    "float":   "double",
    "money":   "decimal",
    "date":    "dateTime",
    "datetime": "dateTime",
    "timestamp": "dateTime",
    "boolean": "boolean",
    "bool":    "boolean",
}

def _tabular_type(qlik_type: str) -> str:
    return _QLIK_TO_TABULAR.get((qlik_type or "").lower(), "string")


class _Publisher:

    def __init__(self, workspace_id: str, access_token: str = ""):
        self.workspace_id = workspace_id
        self.token = access_token
        self.pbi_headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    # ── main entry ────────────────────────────────────────────────────────────

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

    # ── BIM builder ───────────────────────────────────────────────────────────

    def _build_bim(
        self,
        dataset_name: str,
        tables_m: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        data_source_path: str,
    ) -> str:
        """
        Build a TMSL V3 model.bim.

        Confirmed working requirements (from Microsoft docs + community):
        • compatibilityLevel = 1550
        • defaultPowerBIDataSourceVersion = "powerBI_V3"
        • Each table must have explicit 'columns' array
        • M expression stored as array of strings (one per line)
        • definition.pbism version "1.0" = TMSL/model.bim format
        """
        tmd_tables = []
        for t in tables_m:
            expr = t.get("m_expression", "").strip()
            if not expr:
                continue

            # Build explicit columns from fields metadata
            fields = t.get("fields", [])
            columns = []
            for i, f in enumerate(fields):
                col = {
                    "name": f["name"],
                    "dataType": _tabular_type(f.get("type", "string")),
                    "sourceColumn": f["name"],
                    "summarizeBy": "none",
                    "annotations": [{"name": "SummarizationSetBy", "value": "Automatic"}]
                }
                columns.append(col)

            # If no field metadata, add a placeholder — Fabric needs at least one column
            if not columns:
                columns = [{
                    "name": "Value",
                    "dataType": "string",
                    "sourceColumn": "Value",
                    "summarizeBy": "none",
                    "annotations": [{"name": "SummarizationSetBy", "value": "Automatic"}]
                }]

            tmd_tables.append({
                "name": t["name"],
                "columns": columns,
                "partitions": [{
                    "name": f"{t['name']}-Partition",
                    "mode": "import",
                    "source": {
                        "type": "m",
                        "expression": expr.splitlines()
                    }
                }]
            })

        tmd_rels = []
        for r in relationships:
            ft = r.get("fromTable") or r.get("from_table", "")
            fc = r.get("fromColumn") or r.get("from_column", "")
            tt = r.get("toTable")   or r.get("to_table", "")
            tc = r.get("toColumn")  or r.get("to_column", "")
            if ft and fc and tt and tc:
                tmd_rels.append({
                    "name": f"{ft}_{fc}_{tt}_{tc}",
                    "fromTable": ft, "fromColumn": fc,
                    "toTable": tt, "toColumn": tc,
                    "crossFilteringBehavior": "oneDirection"
                })

        expressions = []
        if data_source_path:
            expressions.append({
                "name": "DataSourcePath",
                "kind": "m",
                "expression": [json.dumps(data_source_path)]
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

    # ── Strategy 1: Fabric Items API ──────────────────────────────────────────

    def _deploy_via_fabric(
        self,
        dataset_name: str,
        tables_m: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        data_source_path: str,
    ) -> Dict[str, Any]:
        try:
            # Fabric API requires its own scope
            fabric_token = _acquire_sp_token("https://api.fabric.microsoft.com/.default")
            if not fabric_token:
                fabric_token = self.token

            headers = {
                "Authorization": f"Bearer {fabric_token}",
                "Content-Type": "application/json",
            }

            bim_json = self._build_bim(dataset_name, tables_m, relationships, data_source_path)
            bim_b64  = base64.b64encode(bim_json.encode("utf-8")).decode("ascii")

            # definition.pbism: version "1.0" means TMSL / model.bim format
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
            # Log each table's M expression for debugging
            bim_obj = json.loads(bim_json)
            for tbl in bim_obj.get("model", {}).get("tables", []):
                parts = tbl.get("partitions", [{}])
                expr_lines = parts[0].get("source", {}).get("expression", [])
                expr_preview = "\n".join(expr_lines)[:300]
                logger.info("[Fabric API] Table '%s' M expression:\n%s", tbl["name"], expr_preview)

            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            logger.info("[Fabric API] Response: %d %s", resp.status_code, resp.text[:400])

            if resp.status_code in (200, 201, 202):
                if resp.status_code == 202:
                    op_url = resp.headers.get("Location") or resp.headers.get("x-ms-operation-id")
                    dataset_id = self._poll(op_url, headers) if op_url else ""
                else:
                    dataset_id = (resp.json() if resp.text.strip() else {}).get("id", "")

                if dataset_id:
                    logger.info("[Fabric API] Created: %s", dataset_id)
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
                        return body.get("createdItemId") or body.get("id", "")
                    if status in ("Failed", "Cancelled"):
                        logger.warning("[Fabric API] Op %s: %s", status, body)
                        return ""
            except Exception as ex:
                logger.warning("[Fabric API] Poll error: %s", ex)
        logger.warning("[Fabric API] Polling timed out after %ds", max_wait)
        return ""

    # ── Strategy 2: Push Dataset (fallback) ───────────────────────────────────

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
                    cols = [
                        {"name": f["name"], "dataType": _tabular_type(f.get("type", "string"))}
                        for f in fields
                    ]
                else:
                    cols = [{"name": "Value", "dataType": "string"}]
                tables_payload.append({"name": t["name"], "columns": cols})

            payload = {
                "name": dataset_name,
                "defaultMode": "Push",
                "tables": tables_payload,
            }
            url = f"https://api.powerbi.com/v1.0/myorg/groups/{self.workspace_id}/datasets"
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
                        "⚠️ Created via Push dataset fallback. "
                        "Fabric API failed — no M Query or Model View."
                    ),
                }
            return {
                "success": False,
                "error": f"Push dataset failed: {resp.status_code} {resp.text[:300]}",
            }
        except Exception as exc:
            logger.exception("[Push] Error")
            return {"success": False, "error": str(exc)}


# ──────────────────────────────────────────────────────────────────────────────
# Token / flow cache helpers
# ──────────────────────────────────────────────────────────────────────────────

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
        p = _device_flow_cache_path()
        if os.path.exists(p):
            return json.loads(open(p).read())
    except Exception:
        pass
    return None

def _clear_device_flow():
    try:
        p = _device_flow_cache_path()
        if os.path.exists(p): os.remove(p)
    except Exception:
        pass
