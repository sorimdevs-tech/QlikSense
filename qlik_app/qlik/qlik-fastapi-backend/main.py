from fastapi import FastAPI, HTTPException, Depends, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from typing import List, Dict, Any, Optional
from .qlik_client import QlikClient
from .qlik_websocket_client import QlikWebSocketClient
from .login_validation import router as login_router
import os

# Try to import script parser, but make it optional
try:
    from .qlik_script_parser import QlikScriptParser
    SCRIPT_PARSER_AVAILABLE = True
except ImportError:
    SCRIPT_PARSER_AVAILABLE = False
    print("WARNING: qlik_script_parser not found. Script extraction endpoints will be disabled.")

app = FastAPI(title="Qlik Sense Cloud API", version="2.0.0")

app.include_router(login_router)

# CORS Middleware - Configure for Render deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
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

# Constants
TEST_USERNAME = "testuser"
TEST_PASSWORD = "test123"
HARDCODED_TENANT = "https://c8vlzp3sx6akvnh.in.qlikcloud.com"

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
@app.get("/applications/{app_id}/tables")
async def get_app_tables(
    app_id: str, 
    include_script: bool = Query(default=False, description="Include script analysis"),
    ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
):
    """Get tables and fields from app using WebSocket."""
    try:
        result = ws_client.get_app_tables_simple(app_id)
        
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get tables"))
        
        response = {
            "success": True,
            "app_id": result.get("app_id"),
            "app_title": result.get("app_title"),
            "tables": result.get("tables", []),
            "summary": result.get("summary", {})
        }
        
        if include_script:
            response["script"] = result.get("script", "")
            response["script_tables"] = result.get("script_tables", [])
        
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

@app.get("/applications/{app_id}/table/{table_name}/data")
async def get_table_data(
    app_id: str,
    table_name: str,
    limit: int = Query(default=100, le=10000, description="Maximum number of rows to return"),
    ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
):
    """Get actual data from a specific table"""
    try:
        result = ws_client.get_table_data(app_id, table_name, limit)
        
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get table data"))
        
        return result
        
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

if SCRIPT_PARSER_AVAILABLE:
    
    @app.get("/applications/{app_id}/script/tables")
    async def get_script_tables(app_id: str, ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)):
        """Extract all tables from the app script (INLINE data)"""
        try:
            result = ws_client.get_app_tables_simple(app_id)
            
            if not result.get("success", False):
                raise HTTPException(status_code=500, detail=result.get("error", "Failed to get script"))
            
            script = result.get("script", "")
            
            if not script:
                return {"success": False, "error": "No script found in app", "app_id": app_id}
            
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
        """Get data for a specific table from the script (INLINE data)"""
        try:
            result = ws_client.get_app_tables_simple(app_id)
            
            if not result.get("success", False):
                raise HTTPException(status_code=500, detail=result.get("error", "Failed to get script"))
            
            script = result.get("script", "")
            
            if not script:
                raise HTTPException(status_code=404, detail="No script found in app")
            
            table_data = QlikScriptParser.get_table_preview(script, table_name, limit)
            
            if not table_data.get("success", False):
                raise HTTPException(status_code=404, detail=table_data.get("error", f"Table '{table_name}' not found"))
            
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
        """Get data for a specific table as HTML table"""
        try:
            result = ws_client.get_app_tables_simple(app_id)
            
            if not result.get("success", False):
                return f"<html><body><h1>Error</h1><p>{result.get('error', 'Failed to get script')}</p></body></html>"
            
            script = result.get("script", "")
            
            if not script:
                return "<html><body><h1>Error</h1><p>No script found in app</p></body></html>"
            
            html_content = QlikScriptParser.convert_to_html_table(script, table_name)
            
            return f"""<!DOCTYPE html><html><head><title>{table_name} - Qlik Data</title></head><body><h1>Qlik App Data: {table_name}</h1>{html_content}</body></html>"""
            
        except Exception as e:
            return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>"

    @app.get("/applications/{app_id}/script/table/{table_name}/csv", response_class=PlainTextResponse)
    async def get_script_table_csv(
        app_id: str, 
        table_name: str,
        ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
    ):
        """Get data for a specific table as CSV"""
        try:
            result = ws_client.get_app_tables_simple(app_id)
            
            if not result.get("success", False):
                return f"Error: {result.get('error', 'Failed to get script')}"
            
            script = result.get("script", "")
            
            if not script:
                return "Error: No script found in app"
            
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
        """Get all tables from script as HTML"""
        try:
            result = ws_client.get_app_tables_simple(app_id)
            
