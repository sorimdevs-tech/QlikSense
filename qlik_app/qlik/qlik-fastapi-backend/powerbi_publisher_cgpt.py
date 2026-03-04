"""
powerbi_publisher.py
Zero-touch Power BI semantic model publisher
PPU + Fabric compatible
"""

import base64
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------

def publish_semantic_model(
    dataset_name: str,
    tables_m: List[Dict[str, Any]],
    workspace_id: str,
    relationships: Optional[List[Dict[str, Any]]] = None,
    data_source_path: str = "",
    db_connection_string: str = "",
    access_token: str = "",
) -> Dict[str, Any]:

    publisher = _Publisher(workspace_id, access_token)

    if db_connection_string.strip():
        tables_m = _rewrite_for_db_connect(tables_m, db_connection_string)

    return publisher.publish(
        dataset_name,
        tables_m,
        relationships or [],
        data_source_path,
    )

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _acquire_sp_token(scope: str) -> str:
    try:
        import msal

        tenant_id = os.getenv("POWERBI_TENANT_ID", "")
        client_id = os.getenv("POWERBI_CLIENT_ID", "")
        client_secret = os.getenv("POWERBI_CLIENT_SECRET", "")

        if not all([tenant_id, client_id, client_secret]):
            return ""

        authority = f"https://login.microsoftonline.com/{tenant_id}"
        app = msal.ConfidentialClientApplication(
            client_id,
            authority=authority,
            client_credential=client_secret,
        )

        result = app.acquire_token_for_client(scopes=[scope])
        return result.get("access_token", "")

    except Exception as e:
        logger.warning("[Auth] SP token error: %s", e)
        return ""


def get_cached_user_token() -> str:
    try:
        path = os.path.join(os.path.dirname(__file__), ".pbi_user_token.json")
        if not os.path.exists(path):
            return ""
        with open(path) as f:
            data = json.load(f)
        if time.time() < data.get("expires_at", 0) - 60:
            return data.get("access_token", "")
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# DB Connect rewrite
# ---------------------------------------------------------------------------

def _rewrite_for_db_connect(
    tables_m: List[Dict[str, Any]],
    connection_string: str,
) -> List[Dict[str, Any]]:

    rewritten = []

    for t in tables_m:
        source_type = t.get("source_type", "")
        if source_type == "resident":
            rewritten.append(t)
            continue

        table_name = t["name"]

        new_expr = (
            f'let\n'
            f'    Source = Odbc.Query(\n'
            f'        "{connection_string}",\n'
            f'        "SELECT * FROM [{table_name}]"\n'
            f'    )\n'
            f'in\n'
            f'    Source'
        )

        rewritten.append({**t, "m_expression": new_expr, "source_type": "odbc"})

    return rewritten


# ---------------------------------------------------------------------------
# Publisher
# ---------------------------------------------------------------------------

class _Publisher:

    def __init__(self, workspace_id: str, access_token: str = ""):
        self.workspace_id = workspace_id
        self.base_url = "https://api.powerbi.com/v1.0/myorg"

        # IMPORTANT: Prefer user token for PPU
        self.token = access_token or get_cached_user_token()

        if not self.token:
            # Only fallback to SP if Premium
            self.token = _acquire_sp_token(
                "https://analysis.windows.net/powerbi/api/.default"
            )

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------

    def publish(
        self,
        dataset_name: str,
        tables_m: List[Dict],
        relationships: List[Dict],
        data_source_path: str,
    ) -> Dict[str, Any]:

        if not self.token:
            return {
                "success": False,
                "error": "No valid Power BI token available.",
            }

        tmsl = self._build_tmsl(
            dataset_name, tables_m, relationships, data_source_path
        )

        # Strategy 1: Fabric API
        result = self._deploy_via_fabric_definition(dataset_name, tmsl)
        if result.get("success"):
            return result

        # Strategy 2: Push dataset fallback
        return self._deploy_push_dataset(dataset_name, tables_m, relationships)

    # ------------------------------------------------------------------
    # TMSL builder
    # ------------------------------------------------------------------

    def _build_tmsl(
        self,
        dataset_name: str,
        tables_m: List[Dict],
        relationships: List[Dict],
        data_source_path: str,
    ) -> Dict[str, Any]:

        tables = []

        for t in tables_m:
            expr = t.get("m_expression", "").strip()
            if not expr:
                continue

            tables.append({
                "name": t["name"],
                "partitions": [{
                    "name": f"{t['name']}-Partition",
                    "mode": "import",
                    "source": {
                        "type": "m",
                        "expression": expr.splitlines(),
                    },
                }],
            })

        rels = []
        for r in relationships:
            if all(k in r for k in ("fromTable", "fromColumn", "toTable", "toColumn")):
                rels.append({
                    "name": f"{r['fromTable']}_{r['toTable']}",
                    "fromTable": r["fromTable"],
                    "fromColumn": r["fromColumn"],
                    "toTable": r["toTable"],
                    "toColumn": r["toColumn"],
                    "crossFilteringBehavior": "oneDirection",
                })

        return {
            "createOrReplace": {
                "object": {"database": dataset_name},
                "database": {
                    "name": dataset_name,
                    "compatibilityLevel": 1550,
                    "model": {
                        "culture": "en-US",
                        "tables": tables,
                        "relationships": rels,
                        "expressions": [{
                            "name": "DataSourcePath",
                            "kind": "m",
                            "expression": json.dumps(data_source_path or ""),
                        }],
                    },
                },
            }
        }

    # ------------------------------------------------------------------
    # Fabric Items API (Corrected + PPU Safe)
    # ------------------------------------------------------------------

    def _deploy_via_fabric_definition(
        self,
        dataset_name: str,
        tmsl: Dict[str, Any],
    ) -> Dict[str, Any]:

        try:
            # Prefer USER token (PPU requirement)
            fabric_token = self.token

            if not fabric_token:
                fabric_token = _acquire_sp_token(
                    "https://api.fabric.microsoft.com/.default"
                )

            if not fabric_token:
                return {"success": False, "error": "No Fabric token available."}

            headers = {
                "Authorization": f"Bearer {fabric_token}",
                "Content-Type": "application/json",
            }

            bim = {
                "database": {
                    "name": dataset_name,
                    "compatibilityLevel": 1550,
                    "model": tmsl["createOrReplace"]["database"]["model"],
                }
            }

            bim_b64 = base64.b64encode(
                json.dumps(bim).encode("utf-8")
            ).decode("ascii")

            pbism_b64 = base64.b64encode(
                json.dumps({"version": "1.0"}).encode("utf-8")
            ).decode("ascii")

            payload = {
                "displayName": dataset_name,
                "definition": {
                    "parts": [
                        {
                            "path": "definition.pbism",
                            "payload": pbism_b64,
                            "payloadType": "InlineBase64",
                        },
                        {
                            "path": "model.bim",
                            "payload": bim_b64,
                            "payloadType": "InlineBase64",
                        },
                    ]
                },
            }

            url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.workspace_id}/semanticModels"

            resp = requests.post(url, headers=headers, json=payload, timeout=60)

            if resp.status_code in (200, 201):
                dataset_id = resp.json().get("id", "")
            elif resp.status_code == 202:
                op_url = resp.headers.get("Location")
                dataset_id = self._poll_fabric_operation(op_url, headers)
            else:
                return {
                    "success": False,
                    "error": f"Fabric API failed: {resp.status_code} {resp.text[:300]}",
                }

            return {
                "success": True,
                "method": "fabric_items_api",
                "dataset_id": dataset_id,
                "dataset_name": dataset_name,
                "workspace_url": f"https://app.powerbi.com/groups/{self.workspace_id}",
            }

        except Exception as e:
            logger.exception("Fabric API error")
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------

    def _poll_fabric_operation(
        self,
        op_url: str,
        headers: Dict[str, str],
        timeout: int = 60,
    ) -> str:

        for _ in range(timeout // 3):
            time.sleep(3)
            resp = requests.get(op_url, headers=headers, timeout=15)
            if not resp.ok:
                continue

            body = resp.json()
            if body.get("status") == "Succeeded":
                return body.get("createdItemId", "")
            if body.get("status") in ("Failed", "Cancelled"):
                return ""

        return ""

    # ------------------------------------------------------------------
    # Push Dataset fallback
    # ------------------------------------------------------------------

    def _deploy_push_dataset(
        self,
        dataset_name: str,
        tables_m: List[Dict],
        relationships: List[Dict],
    ) -> Dict[str, Any]:

        try:
            tables = []

            for t in tables_m:
                cols = re.findall(
                    r'\{"([^"]+)",\s*(?:type|Int64)',
                    t.get("m_expression", ""),
                )
                columns = [{"name": c, "dataType": "string"} for c in cols]
                if not columns:
                    columns = [{"name": "Value", "dataType": "string"}]

                tables.append({"name": t["name"], "columns": columns})

            payload = {
                "name": dataset_name,
                "defaultMode": "Push",
                "tables": tables,
            }

            url = f"{self.base_url}/groups/{self.workspace_id}/datasets"

            resp = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30,
            )

            if resp.ok:
                dataset_id = resp.json().get("id", "")
                return {
                    "success": True,
                    "method": "push_dataset",
                    "dataset_id": dataset_id,
                }

            return {"success": False, "error": resp.text[:300]}

        except Exception as e:
            return {"success": False, "error": str(e)}