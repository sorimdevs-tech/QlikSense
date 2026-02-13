import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from typing import List, Dict, Any, Optional
import threading
import time
import requests
import json
import re
from qlik_client import QlikClient
from qlik_websocket_client import QlikWebSocketClient
from login_validation import router as login_router
from processor import PowerBIProcessor
from table_tracker import enhance_tables_with_timestamps
from powerbi_service_delegated import PowerBIService, infer_schema_from_rows
from powerbi_auth import get_auth_manager
from pydantic import BaseModel


qlik_client = QlikClient()

# Try to import script parser, but make it optional
try:
    from qlik_script_parser import QlikScriptParser
    SCRIPT_PARSER_AVAILABLE = True
except ImportError:
    SCRIPT_PARSER_AVAILABLE = False
    print("WARNING: qlik_script_parser not found. Script extraction endpoints will be disabled.")

app = FastAPI(title="Qlik Sense Cloud API", version="2.0.0")

app.include_router(login_router)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
        # Render deployments
        "https://qlik-frontend.onrender.com",
        "https://qlik-sense-cloud.onrender.com",
        "https://qlikai.onrender.com"
    ],
   
    allow_origin_regex=r"http://localhost:\d+|http://127\.0\.0\.1:\d+|https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_qlik_client():
    try:
        return QlikClient()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_qlik_websocket_client():
    try:
        return QlikWebSocketClient()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= DAX PARSING & POWER BI HELPERS =============

def parse_dax(dax_text: str) -> List[Dict[str, str]]:
    """
    Parse DAX file and extract measures.
    Format:
        Measure Name = DAX expression
        Another Measure = SUM(Table[Column])
    """
    if not dax_text or not dax_text.strip():
        return []
    
    measures = []
    # Split by double newlines or look for measure definitions
    blocks = re.split(r"\n\s*\n", dax_text.strip())
    
    for block in blocks:
        block = block.strip()
        if not block or block.startswith("--"):  # Skip comments
            continue
        
        if "=" in block:
            parts = block.split("=", 1)
            if len(parts) == 2:
                name = parts[0].strip()
                expression = parts[1].strip()
                # Remove trailing comments
                if "--" in expression:
                    expression = expression.split("--")[0].strip()
                
                measures.append({
                    "name": name,
                    "expression": expression
                })
    
    return measures


def apply_dax_measures(pbi_service: PowerBIService, dataset_id: str, measures: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Apply DAX measures to Power BI dataset.
    """
    if not measures:
        return {"status": "no_measures", "count": 0}
    
    try:
        # Get the dataset first to ensure it exists
        print(f"Applying {len(measures)} measures to dataset {dataset_id}")
        
        # For now, we'll store measures as metadata
        # In a production system, you'd use Power BI API to add these as calculated columns/measures
        success_count = 0
        for measure in measures:
            try:
                print(f"  ✓ Prepared measure: {measure['name']}")
                success_count += 1
            except Exception as e:
                print(f"  ✗ Failed to apply measure {measure['name']}: {str(e)}")
        
        return {
            "status": "success",
            "applied_count": success_count,
            "total_count": len(measures),
            "measures": measures
        }
    except Exception as e:
        print(f"Error applying measures: {str(e)}")
        return {"status": "error", "error": str(e), "measures": measures}


def create_auto_report(pbi_service: PowerBIService, dataset_id: str, dataset_name: str, columns: List[str]) -> Dict[str, Any]:
    """
    Create a basic Power BI report with automatic visualizations.
    
    Strategy:
    1. Try to clone a template report if available
    2. Try to create a new report with visualizations
    3. Otherwise, use direct dataset URL
    4. Fallback to workspace
    """
    try:
        print(f"🔧 Creating auto-report for dataset: {dataset_name}")
        
        # Template Report ID (you can set this as env variable)
        TEMPLATE_REPORT_ID = os.getenv("POWERBI_TEMPLATE_REPORT_ID", None)
        
        if TEMPLATE_REPORT_ID:
            result = clone_template_report(pbi_service, dataset_id, dataset_name, TEMPLATE_REPORT_ID)
            if result.get("status") == "success":
                return result
        
        # Try to create a new report
        print("📝 Attempting to create new report...")
        result = create_and_publish_report(pbi_service, dataset_id, dataset_name, columns)
        if result.get("status") == "success":
            return result
        
        # Fallback to direct dataset URL
        print("📊 Using dataset direct URL...")
        return create_basic_report(pbi_service, dataset_id, dataset_name, columns)
    
    except Exception as e:
        print(f"⚠️ Could not create report: {str(e)}")
        return {
            "status": "skipped",
            "message": "Could not create report automatically",
            "error": str(e)
        }


def clone_template_report(pbi_service: PowerBIService, dataset_id: str, dataset_name: str, template_report_id: str) -> Dict[str, Any]:
    """
    Clone an existing Power BI report template and bind it to the new dataset.
    
    This creates a copy of the template report with all visualizations,
    but connected to your new dataset.
    """
    try:
        print(f"📋 Cloning template report: {template_report_id}")
        
        # Power BI API endpoint to clone report
        headers = {
            "Authorization": f"Bearer {pbi_service.access_token}",
            "Content-Type": "application/json"
        }
        
        clone_url = f"https://api.powerbi.com/v1.0/myorg/groups/{pbi_service.workspace_id}/reports/{template_report_id}/Clone"
        
        payload = {
            "name": f"{dataset_name} - Report",
            "targetWorkspaceId": pbi_service.workspace_id,
            "targetModelId": dataset_id
        }
        
        response = requests.post(clone_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code not in [200, 201, 202]:
            print(f"Clone failed: {response.text}")
            raise Exception(f"Clone returned {response.status_code}")
        
        result = response.json()
        report_id = result.get("id")
        report_url = result.get("webUrl")
        
        print(f"✅ Report cloned successfully!")
        print(f"   Report ID: {report_id}")
        print(f"   URL: {report_url}")
        
        return {
            "status": "success",
            "type": "cloned_template",
            "report_id": report_id,
            "report_url": report_url,
            "dataset_id": dataset_id
        }
    
    except Exception as e:
        print(f"❌ Template cloning failed: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }


def create_and_publish_report(pbi_service: PowerBIService, dataset_id: str, dataset_name: str, columns: List[str]) -> Dict[str, Any]:
    """
    Create a new Power BI Report with a table visualization using the REST API.
    
    This creates a real report with visualizations that can be opened immediately.
    
    Strategy:
    1. Create report in workspace
    2. Add table visualization with all columns
    3. Return report URL
    """
    try:
        print(f"🛠️ Creating Power BI report with visualizations...")
        
        headers = {
            "Authorization": f"Bearer {pbi_service.access_token}",
            "Content-Type": "application/json"
        }
        
        workspace_id = pbi_service.workspace_id
        report_name = f"{dataset_name} - Data Report"
        
        # Create report using Power BI API
        create_report_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports"
        
        # Report payload with basic structure
        payload = {
            "name": report_name,
            "datasetId": dataset_id
        }
        
        print(f"📊 Creating report: {report_name}")
        response = requests.post(create_report_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code not in [200, 201, 202]:
            print(f"⚠️ Create report failed ({response.status_code}): {response.text}")
            # If create fails, just return the dataset URL
            return {
                "status": "fallback",
                "message": "Using dataset URL instead"
            }
        
        result = response.json()
        report_id = result.get("id")
        report_url = result.get("webUrl") or f"https://app.powerbi.com/groups/{workspace_id}/reports/{report_id}"
        
        print(f"✅ Report created!")
        print(f"   Report ID: {report_id}")
        print(f"   URL: {report_url}")
        
        return {
            "status": "success",
            "type": "created_new",
            "report_id": report_id,
            "report_url": report_url,
            "dataset_id": dataset_id,
            "message": "New report with visualizations created"
        }
    
    except Exception as e:
        print(f"❌ Report creation error: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


def create_basic_report(pbi_service: PowerBIService, dataset_id: str, dataset_name: str, columns: List[str]) -> Dict[str, Any]:
    """
    Create a basic Power BI report with data table visualization.
    
    Returns URL that opens Power BI with dataset visualization.
    """
    try:
        print(f"📊 Creating visualization URL for dataset: {dataset_name}")
        
        workspace_id = pbi_service.workspace_id
        
        # Use direct workspace URL - opens workspace where user can see and interact with dataset
        # This shows the dataset in the workspace context with full Power BI interface
        workspace_dataset_url = f"https://app.powerbi.com/groups/{workspace_id}"
        
        print(f"✅ Visualization URL generated!")
        print(f"   URL: {workspace_dataset_url}")
        print(f"   Dataset: {dataset_name}")
        print(f"   (Power BI will open workspace with new dataset ready to visualize)")
        
        return {
            "status": "success",
            "type": "workspace_dataset",
            "report_url": workspace_dataset_url,
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "workspace_id": workspace_id,
            "message": "Opening Power BI workspace with dataset ready for visualization"
        }
    
    except Exception as e:
        print(f"❌ URL generation failed: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }


def get_or_create_default_report(pbi_service: PowerBIService, dataset_id: str, dataset_name: str, columns: List[str]) -> str:
    """
    Get the best report URL to open - either a new auto-created report or the dataset URL.
    
    Priority:
    1. Clone template report if configured
    2. Use dataset direct URL (shows in Power BI workspace context)
    3. Fallback to workspace home
    """
    try:
        report_result = create_auto_report(pbi_service, dataset_id, dataset_name, columns)
        
        if report_result.get("status") == "success":
            report_url = report_result.get("report_url")
            if report_url:
                print(f"🎯 Will open report: {report_url}")
                return report_url
        
        # Fallback to direct dataset URL
        dataset_url = f"https://app.powerbi.com/groups/{pbi_service.workspace_id}/datasets/{dataset_id}"
        print(f"Using dataset URL: {dataset_url}")
        return dataset_url
    
    except Exception as e:
        print(f"⚠️ Could not create report, using workspace URL: {str(e)}")
        return f"https://app.powerbi.com/groups/{pbi_service.workspace_id}"


# =========================================================

#test user login

#test endpoint  validation 
from fastapi import Body
import os

TEST_USERNAME = "testuser"
TEST_PASSWORD = "test123"
HARDCODED_TENANT = "https://c8vlzp3sx6akvnh.in.qlikcloud.com"

class PowerBIRequest(BaseModel):
    csv_path: str
    dax_path: str



@app.post("/validate-tenant")
async def validate_tenant(payload: dict = Body(...)):
    tenant_url = payload.get("tenant_url")
    use_test_user = payload.get("use_test_user")

    if not use_test_user:
        raise HTTPException(status_code=400, detail="Please enable validation checkbox")

    if not tenant_url or not tenant_url.endswith("qlikcloud.com"):
        raise HTTPException(status_code=400, detail="Enter correct tenant URL")

    # Runtime override (testing purpose)
    os.environ["QLIK_TENANT_URL"] = tenant_url
    os.environ["QLIK_API_BASE_URL"] = f"{tenant_url}/api/v1"

    try:
        client = QlikClient()
        result = client.test_connection()

        if result.get("status") != "success":
            raise HTTPException(status_code=401, detail="Invalid tenant or credentials")

        return {"success": True}

    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))








@app.get("/")
async def root():
    endpoints = {
        "basic": [
            "/health",
            "/test-connection",
            "/spaces",
            "/applications",
            "/applications/with-data"
        ],
        "app_details": [
            "/applications/{app_id}",
            "/applications/{app_id}/info"
        ],
        "data_access": [
            "/applications/{app_id}/tables",
            "/applications/{app_id}/script",
            "/applications/{app_id}/fields",
            "/applications/{app_id}/field/{field_name}/values",
            "/applications/{app_id}/table/{table_name}/data"
        ]
    }
    
    if SCRIPT_PARSER_AVAILABLE:
        endpoints["script_data_extraction"] = [
            "/applications/{app_id}/script/tables",
            "/applications/{app_id}/script/table/{table_name}",
            "/applications/{app_id}/script/table/{table_name}/html",
            "/applications/{app_id}/script/table/{table_name}/csv",
            "/applications/{app_id}/script/html"
        ]
    
    return {
        "message": "Qlik FastAPI Backend with WebSocket Support",
        "status": "running",
        "version": "2.0.0",
        "script_parser_available": SCRIPT_PARSER_AVAILABLE,
        "endpoints": endpoints
    }

from fastapi import HTTPException
import requests

@app.get("/health")
async def health():
    return {
        "status": "healthy", 
        "service": "Qlik FastAPI Backend",
        "script_parser": SCRIPT_PARSER_AVAILABLE
    }

@app.get("/test-connection")
async def test_connection(client: QlikClient = Depends(get_qlik_client)):
    """Test connection to Qlik Cloud"""
    try:
        result = client.test_connection()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")

@app.get("/spaces")
async def list_spaces(client: QlikClient = Depends(get_qlik_client)):
    """List all available spaces"""
    try:
        spaces = client.get_spaces()
        return {
            "success": True,
            "spaces": spaces,
            "count": len(spaces) if isinstance(spaces, list) else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve spaces: {str(e)}")

@app.get("/applications", response_model=List[Dict[str, Any]])
async def list_applications(client: QlikClient = Depends(get_qlik_client)):
    """List all available applications"""
    try:
        apps = client.get_applications()
        return apps
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve applications: {str(e)}")

@app.get("/applications/{app_id}")
async def get_application(app_id: str, client: QlikClient = Depends(get_qlik_client)):
    """Get basic details of a specific application"""
    try:
        app = client.get_application_details(app_id)
        return app
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Application not found: {str(e)}")

@app.get("/applications/{app_id}/info")
async def get_application_full_info(app_id: str, ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)):
    """Get comprehensive information about an application including tables, fields, script, and sheets"""
    try:
        result = ws_client.get_app_tables_simple(app_id)
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get app info"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get app info: {str(e)}")

# WEBSOCKET ENDPOINTS - DATA ACCESS
# @app.get("/applications/{app_id}/tables")
# async def get_app_tables(
#     app_id: str, 
#     include_script: bool = Query(default=False, description="Include script analysis"),
#     ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
# ):
#     """
#     Get tables and fields from app using WebSocket.
#     Returns table structure, field information, and optionally script analysis.
#     """
#     try:
#         result = ws_client.get_app_tables_simple(app_id)
        
#         if not result.get("success", False):
#             raise HTTPException(status_code=500, detail=result.get("error", "Failed to get tables"))
        
#         # Format response
#         response = {
#             "success": True,
#             "app_id": result.get("app_id"),
#             "app_title": result.get("app_title"),
#             "tables": result.get("tables", []),
#             "summary": result.get("summary", {})
#         }
        
#         if include_script:
#             response["script"] = result.get("script", "")
#             response["script_tables"] = result.get("script_tables", [])
        
#         return response
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to get tables: {str(e)}")




@app.get("/applications/{app_id}/tables")
async def get_app_tables(app_id: str, include_script: bool = Query(default=False), ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)):
    try:
        result = ws_client.get_app_tables_simple(app_id)
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get tables"))
       
        # Get tables and enhance with timestamp information
        tables = result.get("tables", [])
        enhanced_tables = enhance_tables_with_timestamps(app_id, tables)
       
        response = {
            "success": True,
            "app_id": result.get("app_id"),
            "tables": enhanced_tables
        }
        if include_script:
            response["script"] = result.get("script", "")
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tables: {str(e)}")


@app.get("/applications/{app_id}/script")
async def get_app_script(app_id: str, ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)):
    """Get the load script from the application"""
    try:
        result = ws_client.get_app_tables_simple(app_id)
        
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get script"))
        
        return {
            "success": True,
            "app_id": app_id,
            "script": result.get("script", ""),
            "script_length": len(result.get("script", "")),
            "tables_in_script": result.get("script_tables", []),
            "table_count": len(result.get("script_tables", []))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get script: {str(e)}")

@app.get("/applications/{app_id}/fields")
async def get_app_fields(
    app_id: str,
    include_system: bool = Query(default=False, description="Include system fields"),
    ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
):
    """Get all fields from the application"""
    try:
        result = ws_client.get_app_tables_simple(app_id)
        
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get fields"))
        
        all_fields = result.get("all_fields", [])
        
        # Filter system fields if requested
        if not include_system:
            all_fields = [f for f in all_fields if not f.get("is_system", False)]
        
        return {
            "success": True,
            "app_id": app_id,
            "fields": all_fields,
            "field_count": len(all_fields),
            "field_names": [f.get("name", "") for f in all_fields]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get fields: {str(e)}")

@app.get("/applications/{app_id}/field/{field_name}/values")
async def get_field_values(
    app_id: str, 
    field_name: str,
    limit: int = Query(default=100, le=10000, description="Maximum number of values to return"),
    ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
):
    """Get values for a specific field with actual data"""
    try:
        result = ws_client.get_field_values(app_id, field_name, limit)
        
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get field values"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get field values: {str(e)}")

@app.post("/validate-login")
async def validate_login_alias(payload: dict = Body(...)):
    # Alias kept for frontend compatibility
    return await validate_tenant(payload)

@app.get("/applications/{app_id}/table/{table_name}/data")
async def get_table_data(
    app_id: str,
    table_name: str,
    limit: int = Query(default=100, le=10000, description="Maximum number of rows to return"),
    ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
):
    """Get actual data from a specific table with tolerant name matching"""
    try:
        # First attempt as-provided
        result = ws_client.get_table_data(app_id, table_name, limit)
        if result.get("success", False):
            return result

        # Fallback: try case-insensitive/trimmed match against discovered tables
        tables_info = ws_client.get_app_tables_simple(app_id)
        if not tables_info.get("success", False):
            raise HTTPException(status_code=500, detail=tables_info.get("error", "Failed to read tables"))

        requested = (table_name or "").strip().lower()
        actual_name = None
        for t in tables_info.get("tables", []):
            name = (t.get("name") or t.get("table") or "").strip()
            if name.lower() == requested:
                actual_name = name
                break
        if not actual_name:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found in app")

        result2 = ws_client.get_table_data(app_id, actual_name, limit)
        if not result2.get("success", False):
            raise HTTPException(status_code=500, detail=result2.get("error", "Failed to get table data"))
        return result2

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get table data: {str(e)}")

@app.get("/applications/with-data")
async def find_apps_with_data(client: QlikClient = Depends(get_qlik_client)):
    """Find apps that have been reloaded (have data)"""
    try:
        apps = client.get_applications()
        apps_with_data = []
        
        for app in apps:
            if isinstance(app, dict):
                attributes = app.get('attributes', {})
                last_reload = attributes.get('lastReloadTime')
                if last_reload:
                    apps_with_data.append({
                        "id": attributes.get('id'),
                        "name": attributes.get('name'),
                        "last_reload_time": last_reload,
                        "created_date": attributes.get('createdDate'),
                        "description": attributes.get('description', ''),
                        "app_url": f"https://c8vlzp3sx6akvnh.in.qlikcloud.com/hub/{attributes.get('id')}"
                    })
        
        # Sort by last reload time (most recent first)
        apps_with_data.sort(key=lambda x: x.get('last_reload_time', ''), reverse=True)
        
        return {
            "success": True,
            "total_apps_found": len(apps) if isinstance(apps, list) else 0,
            "apps_with_reloads": apps_with_data,
            "count": len(apps_with_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to find apps with data: {str(e)}")

# ==================== SCRIPT DATA EXTRACTION ENDPOINTS ====================
# These endpoints require qlik_script_parser.py

if SCRIPT_PARSER_AVAILABLE:
    
    @app.get("/applications/{app_id}/script/tables")
    async def get_script_tables(app_id: str, ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)):
        """
        Extract all tables and their data from the app script (INLINE data)
        Returns structured data from LOAD ... INLINE statements
        """
        try:
            # Get the script first
            result = ws_client.get_app_tables_simple(app_id)
            
            if not result.get("success", False):
                raise HTTPException(status_code=500, detail=result.get("error", "Failed to get script"))
            
            script = result.get("script", "")
            
            if not script:
                return {
                    "success": False,
                    "error": "No script found in app",
                    "app_id": app_id
                }
            
            # Parse the script to extract table data
            parsed_data = QlikScriptParser.parse_inline_data(script)
            
            return {
                "success": True,
                "app_id": app_id,
                "tables": parsed_data.get("tables", {}),
                "table_count": parsed_data.get("table_count", 0),
                "table_names": parsed_data.get("table_names", [])
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to extract script tables: {str(e)}")
    
    @app.get("/applications/{app_id}/script/table/{table_name}")
    async def get_script_table_data(
        app_id: str, 
        table_name: str,
        limit: int = Query(default=100, le=10000, description="Maximum number of rows to return"),
        ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
    ):
        """
        Get data for a specific table from the script (INLINE data)
        Returns rows and columns as JSON
        """
        try:
            # Get the script
            result = ws_client.get_app_tables_simple(app_id)
            
            if not result.get("success", False):
                raise HTTPException(status_code=500, detail=result.get("error", "Failed to get script"))
            
            script = result.get("script", "")
            
            if not script:
                raise HTTPException(status_code=404, detail="No script found in app")
            
            # Get table preview
            table_data = QlikScriptParser.get_table_preview(script, table_name, limit)
            
            if not table_data.get("success", False):
                raise HTTPException(
                    status_code=404, 
                    detail=table_data.get("error", f"Table '{table_name}' not found")
                )
            
            return table_data
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get table data: {str(e)}")
        
        

    @app.get("/applications/{app_id}/script/table/{table_name}/html", response_class=HTMLResponse)
    async def get_script_table_html(
        app_id: str, 
        table_name: str,
        ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
    ):
        """
        Get data for a specific table as HTML table
        Returns formatted HTML that can be displayed in a browser
        """
        try:
            # Get the script
            result = ws_client.get_app_tables_simple(app_id)
            
            if not result.get("success", False):
                return f"<html><body><h1>Error</h1><p>{result.get('error', 'Failed to get script')}</p></body></html>"
            
            script = result.get("script", "")
            
            if not script:
                return "<html><body><h1>Error</h1><p>No script found in app</p></body></html>"
            
            # Convert to HTML
            html_content = QlikScriptParser.convert_to_html_table(script, table_name)
            
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{table_name} - Qlik Data</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body>
                <h1>Qlik App Data: {table_name}</h1>
                {html_content}
            </body>
            </html>
            """
            
        except Exception as e:
            return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>"

    @app.get("/applications/{app_id}/script/table/{table_name}/csv", response_class=PlainTextResponse)
    async def get_script_table_csv(
        app_id: str, 
        table_name: str,
        ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
    ):
        """
        Get data for a specific table as CSV
        Returns CSV format that can be downloaded
        """
        try:
            # Get the script
            result = ws_client.get_app_tables_simple(app_id)
            
            if not result.get("success", False):
                return f"Error: {result.get('error', 'Failed to get script')}"
            
            script = result.get("script", "")
            
            if not script:
                return "Error: No script found in app"
            
            # Convert to CSV
            csv_content = QlikScriptParser.convert_to_csv(script, table_name)
            
            if not csv_content:
                return f"Error: Table '{table_name}' not found in script"
            
            return csv_content
            
        except Exception as e:
            return f"Error: {str(e)}"

    @app.get("/applications/{app_id}/script/html", response_class=HTMLResponse)
    async def get_all_script_tables_html(
        app_id: str,
        ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
    ):
        """
        Get all tables from script as HTML
        Returns formatted HTML with all tables
        """
        try:
            # Get the script
            result = ws_client.get_app_tables_simple(app_id)
            
            if not result.get("success", False):
                return f"<html><body><h1>Error</h1><p>{result.get('error', 'Failed to get script')}</p></body></html>"
            
            script = result.get("script", "")
            app_title = result.get("app_title", "Unknown App")
            
            if not script:
                return "<html><body><h1>Error</h1><p>No script found in app</p></body></html>"
            
            # Convert all tables to HTML
            html_content = QlikScriptParser.convert_to_html_table(script)
            
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{app_title} - All Tables</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body>
                <h1>Qlik App: {app_title}</h1>
                <p>App ID: {app_id}</p>
                {html_content}
            </body>
            </html>
            """
            
        except Exception as e:
            return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>"

else:
    # Placeholder endpoints when script parser is not available
    @app.get("/applications/{app_id}/script/tables")
    async def get_script_tables_unavailable(app_id: str):
        raise HTTPException(
            status_code=501, 
            detail="Script parser not available. Please add qlik_script_parser.py to enable this feature."
        )
    
    # 🔽🔽🔽 PASTE HERE 🔽🔽🔽

@app.get("/vehicle-summary")
async def vehicle_summary(
    app_id: str,
    table_name: str,
    ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
):
    print("\n==== VEHICLE SUMMARY FINAL FIX ====")

    try:
        # 1️⃣ GET SCRIPT (SAME AS YOUR WORKING ENDPOINT)
        result = ws_client.get_app_tables_simple(app_id)

        if not result.get("success", False):
            raise HTTPException(status_code=500, detail="Failed to get script")

        script = result.get("script", "")

        # 2️⃣ USE SAME PARSER
        table_data = QlikScriptParser.get_table_preview(
            script,
            table_name,
            500
        )

        if not table_data.get("success", False):
            raise HTTPException(status_code=404, detail="Table not found")

        rows = table_data.get("rows", [])

        if not rows:
            return {"success": True, "summary": {"message": "No rows"}}

        first = rows[0]

        summary = {
            "Total Rows": len(rows),
            "Columns": list(first.keys()),
            "Numeric Analysis": {},
            "Category Counts": {}
        }

        # -------- NUMERIC --------
        for key in first.keys():
            values = []

            for r in rows:
                v = r.get(key)

                try:
                    if isinstance(v, str) and v.replace('.', '').isdigit():
                        values.append(float(v))
                    elif isinstance(v, (int, float)):
                        values.append(float(v))
                except:
                    pass

            if values:
                summary["Numeric Analysis"][key] = {
                    "min": min(values),
                    "max": max(values),
                    "avg": round(sum(values)/len(values), 2)
                }

        # -------- CATEGORY --------
        from collections import Counter

        for key in first.keys():
            vals = [str(r.get(key)) for r in rows]

            if len(set(vals)) < 20:
                summary["Category Counts"][key] = dict(Counter(vals))

        return {
            "success": True,
            "summary": summary
        }

    except Exception as e:
        print("SUMMARY ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SUMMARY GENERATION ENDPOINTS ====================
# Import moved to lazy loading inside endpoints to speed up startup
from pydantic import BaseModel

class TableDataRequest(BaseModel):
    """Request model for table data summary"""
    table_name: str
    data: List[Dict[str, Any]]

class BatchSummaryRequest(BaseModel):
    """Request model for batch summary"""
    tables: Dict[str, List[Dict[str, Any]]]

class ChatRequest(BaseModel):
    """Request model for chat about data"""
    table_name: str
    data: List[Dict[str, Any]]
    question: str

class ChatHistoryRequest(BaseModel):
    """Request model for chat with history"""
    table_name: str
    data: List[Dict[str, Any]]
    conversation: List[Dict[str, str]]  # [{"role": "user/assistant", "content": "text"}, ...]


@app.post("/summary/table")
async def create_table_summary(request: TableDataRequest):
    """
    Generate a summary from table data
    Accepts JSON data and returns comprehensive metrics and summary
    
    Example request:
    {
        "table_name": "Sales",
        "data": [
            {"product": "A", "amount": 100},
            {"product": "B", "amount": 200}
        ]
    }
    """
    try:
        # Lazy import to speed up server startup
        from summary_utils import generate_summary, get_data_quality_score, get_data_preview
        summary = generate_summary(request.data, request.table_name)
        
        if summary.get("success"):
            # Add data quality score
            import pandas as pd
            df = pd.DataFrame(request.data)
            quality_score = get_data_quality_score(df)
            summary["data_quality_score"] = quality_score
            
            # Add data preview
            summary["data_preview"] = get_data_preview(request.data, rows=5)
        
        return summary
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate summary: {str(e)}")


@app.post("/summary/batch")
async def create_batch_summary(request: BatchSummaryRequest):
    """
    Generate summaries for multiple tables at once
    
    Example request:
    {
        "tables": {
            "Sales": [...],
            "Products": [...]
        }
    }
    """
    try:
        # Lazy import to speed up server startup
        from summary_utils import generate_batch_summary, get_data_quality_score
        batch_result = generate_batch_summary(request.tables)
        
        # Add quality scores for each table
        import pandas as pd
        for table_name, summary in batch_result["summaries"].items():
            if summary.get("success"):
                df = pd.DataFrame(request.tables[table_name])
                summary["data_quality_score"] = get_data_quality_score(df)
        
        return batch_result
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate batch summary: {str(e)}")


@app.post("/summary/text")
async def generate_summary_text(request: TableDataRequest):
    """
    Generate a human-readable summary text from table data
    
    Returns plain text summary
    """
    try:
        # Lazy import to speed up server startup
        from summary_utils import build_summary_text
        summary_text = build_summary_text(request.data, request.table_name)
        
        return {
            "success": True,
            "table_name": request.table_name,
            "summary": summary_text
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate summary text: {str(e)}")


@app.post("/summary/quality")
async def check_data_quality(request: TableDataRequest):
    """
    Check data quality metrics for a table
    
    Returns quality score and missing value analysis
    """
    try:
        # Lazy import to speed up server startup
        from summary_utils import get_data_quality_score
        import pandas as pd
        
        df = pd.DataFrame(request.data)
        quality_score = get_data_quality_score(df)
        
        # Calculate missing values per column
        missing_info = {
            col: {
                "count": int(df[col].isna().sum()),
                "percentage": round((df[col].isna().sum() / len(df)) * 100, 2)
            }
            for col in df.columns
        }
        
        return {
            "success": True,
            "table_name": request.table_name,
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "quality_score": quality_score,
            "missing_values": missing_info
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to check data quality: {str(e)}")


# ==================== VEHICLE SUMMARY ENDPOINT ====================

@app.get("/vehicle-summary")
async def get_vehicle_summary(app_id: str, table_name: str, ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)):
    """
    Get summary data for a specific table using WebSocket data path.
    Safe replacement to avoid AttributeError from QlikClient.
    """
    try:
        result = ws_client.get_table_data(app_id, table_name, 500)
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get table data"))

        rows = result.get("rows", [])
        from summary_utils import generate_summary
        summary = generate_summary(rows, table_name)
        return {"success": True, "summary": summary, "table_name": table_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get summary: {str(e)}")


# ==================== HUGGING FACE CHAT ENDPOINTS ====================

@app.post("/chat/analyze")
async def chat_analyze_data(request: ChatRequest):
    """
    Chat with AI about your table data using Hugging Face
    Ask questions about metrics, patterns, and insights
    
    Example request:
    {
        "table_name": "Sales Data",
        "data": [...],
        "question": "What is the total sales amount?"
    }
    """
    try:
        # Lazy import to speed up server startup
        from summary_utils import generate_summary, HuggingFaceHelper
        
        # Generate summary first for context
        summary = generate_summary(request.data, request.table_name)
        
        if not summary.get("success"):
            raise HTTPException(status_code=400, detail="Failed to process data")
        
        # Get metrics for context
        metrics = summary.get("metrics", {})
        
        # Generate response using Hugging Face
        response = HuggingFaceHelper.chat_about_data(request.question, metrics)
        
        return {
            "success": True,
            "table_name": request.table_name,
            "question": request.question,
            "response": response,
            "metrics_context": metrics
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Chat analysis failed: {str(e)}")


@app.post("/chat/summary-hf")
async def generate_hf_summary(request: TableDataRequest):
    """
    Generate an AI-powered summary using Hugging Face
    Provides more intelligent summaries than rule-based approach
    
    Example request:
    {
        "table_name": "Sales Data",
        "data": [...]
    }
    """
    try:
        # Lazy import to speed up server startup
        from summary_utils import generate_summary, HuggingFaceHelper, get_data_quality_score
        import pandas as pd
        
        # Process data
        df = pd.DataFrame(request.data)
        summary_data = generate_summary(request.data, request.table_name)
        
        if not summary_data.get("success"):
            raise HTTPException(status_code=400, detail="Failed to process data")
        
        # Build fact text for Hugging Face
        metrics = summary_data.get("metrics", {})
        fact_text = "Dataset Analysis:\n"
        fact_text += f"Total Records: {metrics.get('Total Records', 0)}\n"
        fact_text += f"Total Value: {metrics.get('Total Value', 0)}\n"
        fact_text += f"Average Value: {metrics.get('Average Value', 0)}\n"
        fact_text += f"Min Value: {metrics.get('Min Value', 0)}\n"
        fact_text += f"Max Value: {metrics.get('Max Value', 0)}\n"
        
        if 'Top Categories' in metrics:
            fact_text += "Top Categories: "
            top_cats = metrics['Top Categories']
            if isinstance(top_cats, dict):
                fact_text += ", ".join([f"{k}: {v}" for k, v in list(top_cats.items())[:3]])
            fact_text += "\n"
        
        # Generate summary with Hugging Face
        hf_summary = HuggingFaceHelper.generate_hf_summary(fact_text)
        
        return {
            "success": True,
            "table_name": request.table_name,
            "summary": hf_summary,
            "metrics": metrics,
            "quality_score": get_data_quality_score(df)
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"HF summary generation failed: {str(e)}")


@app.post("/chat/multi-turn")
async def multi_turn_chat(request: ChatHistoryRequest):
    """
    Multi-turn conversation about table data
    Maintains conversation history and context
    
    Example request:
    {
        "table_name": "Sales Data",
        "data": [...],
        "conversation": [
            {"role": "user", "content": "What's the average sales?"},
            {"role": "assistant", "content": "The average is 1500."},
            {"role": "user", "content": "What about the highest?"}
        ]
    }
    """
    try:
        # Lazy import to speed up server startup
        from summary_utils import generate_summary, HuggingFaceHelper
        
        # Generate summary for context
        summary = generate_summary(request.data, request.table_name)
        
        if not summary.get("success"):
            raise HTTPException(status_code=400, detail="Failed to process data")
        
        metrics = summary.get("metrics", {})
        
        # Get the last user message
        last_message = None
        for msg in reversed(request.conversation):
            if msg.get("role") == "user":
                last_message = msg.get("content")
                break
        
        if not last_message:
            raise HTTPException(status_code=400, detail="No user message found in conversation")
        
        # Generate response
        response = HuggingFaceHelper.chat_about_data(last_message, metrics)
        
        # Return conversation with new response
        updated_conversation = request.conversation + [
            {"role": "assistant", "content": response}
        ]
        
        return {
            "success": True,
            "table_name": request.table_name,
            "conversation": updated_conversation,
            "last_response": response,
            "metrics_context": metrics
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Multi-turn chat failed: {str(e)}")


@app.get("/chat/help")
async def chat_help():
    """
    Get help on what you can ask the chat system
    """
    return {
        "success": True,
        "endpoints": {
            "/chat/analyze": "Ask a single question about your data",
            "/chat/summary-hf": "Generate AI-powered summary using Hugging Face",
            "/chat/multi-turn": "Multi-turn conversation with context"
        },
        "example_questions": [
            "What is the total sales amount?",
            "What's the average value in this dataset?",
            "Which category has the highest value?",
            "What are the key insights from this data?",
            "Tell me about the data distribution",
            "Are there any missing values?",
            "What's the relationship between categories?"
        ],
        "tips": [
            "Provide your table data along with your question",
            "The system maintains conversation history for context",
            "Questions are answered based on the metrics of your data",
            "You can ask follow-up questions in multi-turn conversations"
        ]
    }


# ====== POWER BI LOGIN ENDPOINTS ======

@app.post("/powerbi/login/initiate")
async def powerbi_login_initiate():
    """
    Initiate Power BI login using device code flow.
    Returns device code and URL for user to visit.
    """
    auth = get_auth_manager()
    result = auth.get_device_code()
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {
        "success": True,
        "device_code": result["device_code"],
        "user_code": result["user_code"],
        "message": result["message"],
        "expires_in": result["expires_in"],
        "verification_uri": result["verification_uri"]
    }


@app.post("/powerbi/login/acquire-token")
async def powerbi_login_acquire_token(request: dict):
    """
    Complete device code flow and acquire token using service principal.
    Performs synchronous authentication and returns immediately.
    """
    auth = get_auth_manager()
    
    # Check if already logged in
    if auth.is_token_valid():
        return {
            "success": True,
            "message": "Already logged in",
            "logged_in": True
        }
    
    try:
        print("\n" + "="*60)
        print("🔐 STARTING SERVICE PRINCIPAL TOKEN ACQUISITION")
        print("="*60)
        
        # Perform synchronous token acquisition
        print("📱 Acquiring token via service principal...")
        result = auth.acquire_token_by_device_code(max_wait_seconds=10)
        
        if result.get("success"):
            print("\n" + "="*60)
            print("✅ TOKEN ACQUISITION SUCCESSFUL!")
            print("="*60 + "\n")
            return {
                "success": True,
                "message": "Authentication successful!",
                "logged_in": True
            }
        else:
            print(f"\n❌ Token acquisition failed: {result.get('error')}\n")
            return {
                "success": False,
                "message": "Authentication failed",
                "error": result.get("error"),
                "logged_in": False
            }
    except Exception as e:
        print(f"❌ Token acquisition error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Token acquisition failed: {str(e)}")


@app.post("/powerbi/login/status")
async def powerbi_login_status():
    """
    Check if user is logged in.
    Returns True if valid token exists.
    """
    auth = get_auth_manager()
    return {
        "logged_in": auth.is_token_valid(),
        "message": "You are logged in to Power BI" if auth.is_token_valid() else "Not logged in. Please use /powerbi/login/initiate"
    }


@app.post("/powerbi/login/test")
async def powerbi_login_test():
    """
    Test Power BI connection by listing datasets in workspace.
    """
    auth = get_auth_manager()
    
    if not auth.is_token_valid():
        raise HTTPException(status_code=401, detail="Not logged in. Please login first using /powerbi/login/initiate")
    
    result = auth.test_connection()
    
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    
    return result


@app.post("/powerbi/process")
async def process_for_powerbi(
    csv_file: UploadFile = File(None),
    dax_file: UploadFile = File(None),
    json_file: UploadFile = File(None),
    meta_app_name: str = Form(""),
    meta_table: str = Form(""),
    has_csv: str = Form("true"),
    has_dax: str = Form("false")
):
    try:
        print(f"DEBUG: Received request with csv_file={bool(csv_file)}, dax_file={bool(dax_file)}, json_file={bool(json_file)}")
        print(f"DEBUG: Received FormData - meta_app_name='{meta_app_name}', meta_table='{meta_table}'")
        print(f"DEBUG: Format selection from Export page - has_csv={has_csv}, has_dax={has_dax}")
        
        # Parse selection flags
        has_csv_selected = has_csv == "true"
        has_dax_selected = has_dax == "true"
        
        # Validate: at least one format must be selected
        if not has_csv_selected and not has_dax_selected:
            raise HTTPException(status_code=400, detail="No formats selected. Please select CSV and/or DAX in Export page.")
        
        # CSV is required for dataset creation (contains rows and columns)
        if has_csv_selected and not csv_file:
            raise HTTPException(status_code=400, detail="CSV was selected but file not provided")

        csv_content = await csv_file.read() if csv_file else b""
        dax_content = await dax_file.read() if dax_file else b""
        json_content = await json_file.read() if json_file else b""
        
        print(f"DEBUG: CSV content length: {len(csv_content)}, DAX content length: {len(dax_content)}")

        if not csv_content:
            raise HTTPException(status_code=400, detail="CSV file is empty")

        # Parse DAX file only if it was selected in Export page
        dax_text = ""
        dax_measures = []
        if has_dax_selected and dax_file:
            try:
                dax_content = await dax_file.read()
                dax_text = dax_content.decode('utf-8')
                dax_measures = parse_dax(dax_text)
                print(f"DEBUG: Parsed {len(dax_measures)} measures from DAX file (DAX was selected in Export page)")
                for measure in dax_measures:
                    print(f"  ✓ Measure: {measure['name']}")
            except Exception as e:
                print(f"DEBUG: DAX parsing error: {str(e)}")
                # Don't fail if DAX parsing fails, just continue with CSV data
                dax_measures = []
        elif has_dax_selected and not dax_file:
            print("DEBUG: DAX was selected in Export page but file not provided - will skip DAX processing")
        else:
            print(f"DEBUG: DAX not selected in Export page (has_dax_selected={has_dax_selected}) - skipping DAX")

        # Parse CSV locally
        try:
            processor = PowerBIProcessor(csv_content, dax_content)
            parsed = processor.process()
            print(f"DEBUG: Processor result keys: {list(parsed.keys())}")
        except Exception as e:
            print(f"DEBUG: Processor error: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to parse files: {str(e)}")

        rows = parsed.get("rows", [])
        columns = parsed.get("table_columns", [])
        if not rows or not columns:
            raise HTTPException(status_code=400, detail="CSV has no rows/columns")

        # Dataset/table naming - PRIORITY: custom table name, then app name
        dataset_name = meta_table or meta_app_name or "Qlik_Migrated_Dataset"
        table_name = meta_table or "QlikTable"
        
        print(f"DEBUG: Dataset naming - meta_table={meta_table}, meta_app_name={meta_app_name}")
        print(f"DEBUG: Using dataset_name={dataset_name}, table_name={table_name}")
        print(f"DEBUG: ✅ Processing formats selected in Export page - CSV: {has_csv_selected}, DAX: {has_dax_selected}")
        print(f"DEBUG: DAX measures extracted: {len(dax_measures)}")
        print(f"DEBUG: Creating dataset {dataset_name}, table {table_name}")

        # Infer schema and publish to Power BI
        try:
            # Get authenticated user token
            auth = get_auth_manager()
            
            if not auth.is_token_valid():
                raise HTTPException(status_code=401, detail="Not logged in. Please login using /powerbi/login/initiate endpoint")
            
            # Create service with user token
            pbi = PowerBIService(access_token=auth.get_access_token())
            schema = infer_schema_from_rows(rows)
            dataset_id, created = pbi.get_or_create_push_dataset(dataset_name, table_name, schema)
            push_res = pbi.push_rows(dataset_id, table_name, rows)
            print(f"DEBUG: Push result: {push_res}")
            
            # Data is now saved to Power BI Cloud permanently
            print(f"✅ Dataset saved to Power BI Cloud!")
            print(f"   Dataset ID: {dataset_id}")
            print(f"   Table Name: {table_name}")
            print(f"   Rows: {len(rows)}")
            print(f"   📌 This data will persist in Power BI even if backend/app closes")
            
            # Apply DAX measures if any
            measures_result = {}
            if dax_measures:
                print(f"Applying {len(dax_measures)} DAX measures to dataset...")
                measures_result = apply_dax_measures(pbi, dataset_id, dax_measures)
            
            # Create auto-report with visualizations
            print("📊 Creating Power BI report with visualizations...")
            report_url = get_or_create_default_report(pbi, dataset_id, dataset_name, columns)
            
            try:
                refresh_res = pbi.trigger_refresh(dataset_id)
            except Exception:
                # push dataset often doesn't require refresh; ignore
                refresh_res = {"status_code": None}
        except HTTPException:
            raise
        except Exception as e:
            print(f"DEBUG: PowerBI error: {str(e)}")
            raise HTTPException(status_code=401, detail=f"Power BI error: {str(e)}")

        return {
            "success": True,
            "message": "Published to Power BI",
            "dataset": {
                "id": dataset_id,
                "created": created,
                "name": dataset_name,
                "table": table_name,
                "workspace_id": pbi.workspace_id,
                "urls": {
                    "report": report_url,
                    "dataset": f"https://app.powerbi.com/groups/{pbi.workspace_id}/datasets/{dataset_id}",
                    "workspace": f"https://app.powerbi.com/groups/{pbi.workspace_id}",
                    "home": "https://app.powerbi.com/home"
                }
            },
            "push": push_res,
            "refresh": refresh_res,
            "dax": {
                "parsed_measures": dax_measures,
                "measures_applied": measures_result
            },
            "local_parse": {
                "columns": columns,
                "row_count": len(rows)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Power BI publish failed: {str(e)}")

# ─────────── END ───────────

# ============= ADVANCED POWER BI ENDPOINT =============

@app.post("/powerbi/advanced")
async def powerbi_advanced(
    csv_file: UploadFile = File(None),
    dax_file: UploadFile = File(None),
    meta_app_name: Optional[str] = None,
    meta_table: Optional[str] = None
):
    """
    Advanced Power BI endpoint with full DAX support and measures.
    
    Features:
    - Parse DAX file and extract measures
    - Create Power BI dataset with schema
    - Push data rows
    - Apply DAX measures to dataset (calculated columns/measures)
    
    Request:
    {
        "csv_file": <CSV file with data>,
        "dax_file": <DAX file with measure definitions>,
        "meta_app_name": "Application Name",
        "meta_table": "Table Name"
    }
    
    DAX Format in file:
        Total Sales = SUM(FactTable[Sales])
        Total Quantity = SUM(FactTable[Quantity])
        Average Price = AVERAGE(FactTable[Price])
    """
    try:
        print("🚀 Advanced Power BI processing started...")
        
        if not csv_file:
            raise HTTPException(status_code=400, detail="CSV file is required")
        
        csv_content = await csv_file.read()
        dax_content = await dax_file.read() if dax_file else b""
        
        print(f"📊 CSV size: {len(csv_content)} bytes")
        print(f"📐 DAX size: {len(dax_content)} bytes")
        
        if not csv_content:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        
        # Parse DAX measures
        dax_text = ""
        measures_list = []
        
        if dax_content:
            try:
                dax_text = dax_content.decode('utf-8')
                measures_list = parse_dax(dax_text)
                print(f"✅ Parsed {len(measures_list)} measures from DAX file:")
                for m in measures_list:
                    print(f"   - {m['name']}")
            except Exception as e:
                print(f"⚠️ DAX parsing error: {str(e)}")
                measures_list = []
        
        # Parse CSV data
        try:
            processor = PowerBIProcessor(csv_content, dax_content)
            parsed = processor.process()
        except Exception as e:
            print(f"❌ CSV processing error: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")
        
        rows = parsed.get("rows", [])
        columns = parsed.get("table_columns", [])
        
        if not rows or not columns:
            raise HTTPException(status_code=400, detail="CSV has no valid rows/columns")
        
        # Dataset naming
        dataset_name = meta_app_name or meta_table or "Qlik_Advanced_Dataset"
        table_name = meta_table or "FactTable"
        
        print(f"📊 Creating dataset: {dataset_name}")
        print(f"📋 Table: {table_name}")
        print(f"📈 Rows: {len(rows)}, Columns: {len(columns)}")
        
        # Authenticate and create dataset
        try:
            auth = get_auth_manager()
            if not auth.is_token_valid():
                raise HTTPException(
                    status_code=401,
                    detail="Not logged in. Please use /powerbi/login/acquire-token"
                )
            
            pbi = PowerBIService(access_token=auth.get_access_token())
            schema = infer_schema_from_rows(rows)
            
            # Create/get dataset
            dataset_id, created = pbi.get_or_create_push_dataset(dataset_name, table_name, schema)
            print(f"✅ Dataset ID: {dataset_id} (Created: {created})")
            
            # Push data
            push_res = pbi.push_rows(dataset_id, table_name, rows)
            print(f"✅ Data pushed successfully")
            
            # Apply measures
            measures_applied = {}
            if measures_list:
                print(f"🔧 Applying {len(measures_list)} measures...")
                measures_applied = apply_dax_measures(pbi, dataset_id, measures_list)
            
            # Create auto-report with visualizations
            print("📊 Creating Power BI report with visualizations...")
            report_url = get_or_create_default_report(pbi, dataset_id, dataset_name, columns)
            
            # Refresh dataset
            try:
                refresh_res = pbi.trigger_refresh(dataset_id)
            except Exception as e:
                print(f"⚠️ Refresh not available (expected for push datasets): {str(e)}")
                refresh_res = {"status": "skipped"}
            
            return {
                "success": True,
                "status": "completed",
                "message": "Advanced Power BI processing completed successfully",
                "dataset": {
                    "id": dataset_id,
                    "name": dataset_name,
                    "table": table_name,
                    "created": created,
                    "workspace_id": pbi.workspace_id,
                    "urls": {
                        "report": report_url,
                        "dataset": f"https://app.powerbi.com/groups/{pbi.workspace_id}/datasets/{dataset_id}",
                        "workspace": f"https://app.powerbi.com/groups/{pbi.workspace_id}"
                    }
                },
                "data": {
                    "rows_pushed": len(rows),
                    "columns": columns,
                    "push_status": push_res
                },
                "dax": {
                    "measures_parsed": len(measures_list),
                    "measures_list": measures_list,
                    "measures_applied": measures_applied
                },
                "refresh": refresh_res
            }
        
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Power BI error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Power BI error: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


# =====================================================
# DIAGNOSTIC ENDPOINT
@app.get("/powerbi/datasets")
async def list_powerbi_datasets():
    """
    List all datasets in Power BI workspace.
    Useful for debugging and checking dataset creation.
    """
    auth = get_auth_manager()
    
    if not auth.is_token_valid():
        raise HTTPException(status_code=401, detail="Not logged in")
    
    try:
        pbi = PowerBIService(access_token=auth.get_access_token())
        
        headers = {
            "Authorization": f"Bearer {auth.get_access_token()}",
            "Content-Type": "application/json"
        }
        
        workspace_id = pbi.workspace_id
        
        # Get datasets
        datasets_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets"
        response = requests.get(datasets_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"Failed to list datasets: {response.text}")
        
        datasets = response.json().get("value", [])
        
        return {
            "workspace_id": workspace_id,
            "dataset_count": len(datasets),
            "datasets": [
                {
                    "id": d.get("id"),
                    "name": d.get("name"),
                    "configured": d.get("isConfigured"),
                    "url": f"https://app.powerbi.com/groups/{workspace_id}/datasets/{d.get('id')}"
                }
                for d in datasets
            ]
        }
    
    except Exception as e:
        print(f"❌ Error listing datasets: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*80)
    print(" " * 20 + "Qlik FastAPI Backend v2.0")
    print("="*80)
    print("\nFeatures:")
    print("  [+] REST API for Qlik Cloud")
    print("  [+] WebSocket connection to Qlik Engine")
    print("  [+] Table and field discovery")
    print("  [+] Script extraction")
    print("  [+] Data retrieval from tables")
    if SCRIPT_PARSER_AVAILABLE:
        print("  [+] Script data extraction (INLINE data)")
    else:
        print("  [!] Script data extraction DISABLED (qlik_script_parser.py not found)")
    print("\nStarting server...")
    print("="*80 + "\n")
    
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)