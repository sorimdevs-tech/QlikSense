# powerbi_dataset_publisher.py - Cloud-Optimized REST Push + M Queries
import os
import json
from typing import Dict, Any, List
from msal import ConfidentialClientApplication
import requests
from pydantic import BaseModel

class PublisherConfig(BaseModel):
    tenant_id: str
    client_id: str
    client_secret: str
    workspace_id: str
    dataset_name: str

def get_powerbi_token(config: PublisherConfig) -> str:
    app = ConfidentialClientApplication(
        config.client_id, authority=f"https://login.microsoftonline.com/{config.tenant_id}",
        client_credential=config.client_secret
    )
    result = app.acquire_token_for_client(scopes=["https://analysis.windows.net/powerbi/api/.default"])
    if "access_token" not in result: raise ValueError(f"Auth failed: {result.get('error_description')}")
    return result["access_token"]  # [web:6]

def generate_cloud_m(table: Dict[str, Any]) -> str:
    """Generates cloud-friendly M query using Web.Contents for SharePoint CSVs"""
    filename = table['source_path'].split('/')[-1].replace('.qvd', '.csv')  # QVD → CSV fallback
    path = f"[DataSourcePath] & '/{filename}'"
    m_base = f"""
let
    FilePath = {path},
    Source = Csv.Document(Web.Contents(FilePath), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
in
    Promoted
"""
    # Add type transforms from fields
    types = {f['name']: f.get('type', 'text') for f in table.get('fields', [])}
    type_map = {"number": "type number", "date": "type date", "text": "type text"}
    typed = "Table.TransformColumnTypes(Promoted,{{" + ", ".join(f'"{k}", {type_map.get(v, "type text")}' for k,v in types.items()) + "}})"
    return m_base.replace("Promoted", typed, 1)  # [web:28]

def tables_to_push_schema(parse_result: Dict[str, Any]) -> Dict[str, Any]:
    dataset = {
        "name": parse_result.get("dataset_name", "QlikConvertedDataset"),
        "defaultMode": "Push",
        "parameters": [{"name": "DataSourcePath", "type": "string", "mode": "Required"}],
        "tables": []
    }
    for table in parse_result["tables"]:
        cols = [{"name": f["name"], "dataType": "string"} for f in table.get("fields", [])]  # Infer later
        dataset["tables"].append({"name": table["table_name"], "columns": cols})
    dataset["m_queries"] = {t["table_name"]: generate_cloud_m(t) for t in parse_result["tables"]}  # Bonus: Store M
    return dataset  # [web:20]

def publish_from_parse_result(parse_result: Dict[str, Any], config: PublisherConfig) -> Dict[str, Any]:
    token = get_powerbi_token(config)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    schema = tables_to_push_schema(parse_result)
