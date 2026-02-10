from fastapi import FastAPI, HTTPException, Depends, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

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
    allow_origins=["*"],
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
TEST_USERNAME = "ponnuchamy.vellaikannu@sorimtechnologies.com"
TEST_PASSWORD = "qlikCloud000"
HARDCODED_TENANT = "https://c8vlzp3sx6akvnh.in.qlikcloud.com"

@app.post("/validate-tenant")
async def validate_tenant(payload: dict = Body(...)):
    tenant_url = payload.get("tenant_url")
    use_test_user = payload.get("use_test_user")

    if not use_test_user:
        raise HTTPException(status_code=400, detail="Please enable validation checkbox")

    if not tenant_url or not tenant_url.endswith("qlikcloud.com"):
        raise HTTPException(status_code=400, detail="Enter correct tenant URL")

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
        "basic": ["/health", "/test-connection", "/spaces", "/applications", "/applications/with-data"],
        "app_details": ["/applications/{app_id}", "/applications/{app_id}/info"],
        "data_access": ["/applications/{app_id}/tables", "/applications/{app_id}/script", "/applications/{app_id}/fields"]
    }
    
    if SCRIPT_PARSER_AVAILABLE:
        endpoints["script_data_extraction"] = ["/applications/{app_id}/script/tables", "/applications/{app_id}/script/table/{table_name}"]
    
    return {"message": "Qlik FastAPI Backend", "status": "running", "version": "2.0.0", "endpoints": endpoints}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "Qlik FastAPI Backend"}

@app.get("/test-connection")
async def test_connection(client: QlikClient = Depends(get_qlik_client)):
    try:
        return client.test_connection()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")

@app.get("/spaces")
async def list_spaces(client: QlikClient = Depends(get_qlik_client)):
    try:
        spaces = client.get_spaces()
        return {"success": True, "spaces": spaces, "count": len(spaces) if isinstance(spaces, list) else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve spaces: {str(e)}")

@app.get("/applications", response_model=List[Dict[str, Any]])
async def list_applications(client: QlikClient = Depends(get_qlik_client)):
    try:
        return client.get_applications()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve applications: {str(e)}")

@app.get("/applications/{app_id}")
async def get_application(app_id: str, client: QlikClient = Depends(get_qlik_client)):
    try:
        return client.get_application_details(app_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Application not found: {str(e)}")

@app.get("/applications/{app_id}/info")
async def get_application_full_info(app_id: str, ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)):
    try:
        result = ws_client.get_app_tables_simple(app_id)
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get app info"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get app info: {str(e)}")

@app.get("/applications/{app_id}/tables")
async def get_app_tables(app_id: str, include_script: bool = Query(default=False), ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)):
    try:
        result = ws_client.get_app_tables_simple(app_id)
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get tables"))
        response = {"success": True, "app_id": result.get("app_id"), "tables": result.get("tables", [])}
        if include_script:
            response["script"] = result.get("script", "")
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tables: {str(e)}")

@app.get("/applications/{app_id}/script")
async def get_app_script(app_id: str, ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)):
    try:
        result = ws_client.get_app_tables_simple(app_id)
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get script"))
        return {"success": True, "app_id": app_id, "script": result.get("script", "")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get script: {str(e)}")

@app.get("/applications/{app_id}/fields")
async def get_app_fields(app_id: str, include_system: bool = Query(default=False), ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)):
    try:
        result = ws_client.get_app_tables_simple(app_id)
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get fields"))
        all_fields = result.get("all_fields", [])
        if not include_system:
            all_fields = [f for f in all_fields if not f.get("is_system", False)]
        return {"success": True, "app_id": app_id, "fields": all_fields}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get fields: {str(e)}")

@app.get("/applications/with-data")
async def find_apps_with_data(client: QlikClient = Depends(get_qlik_client)):
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
                        "last_reload_time": last_reload
                    })
        apps_with_data.sort(key=lambda x: x.get('last_reload_time', ''), reverse=True)
        return {"success": True, "apps_with_reloads": apps_with_data, "count": len(apps_with_data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to find apps: {str(e)}")

# ==================== SCRIPT DATA EXTRACTION ENDPOINTS ====================

if SCRIPT_PARSER_AVAILABLE:
    
    @app.get("/applications/{app_id}/script/tables")
    async def get_script_tables(app_id: str, ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)):
        try:
            result = ws_client.get_app_tables_simple(app_id)
            if not result.get("success", False):
                raise HTTPException(status_code=500, detail=result.get("error", "Failed to get script"))
            script = result.get("script", "")
            if not script:
                return {"success": False, "error": "No script found in app", "app_id": app_id}
            parsed_data = QlikScriptParser.parse_inline_data(script)
            return {"success": True, "app_id": app_id, "tables": parsed_data.get("tables", {})}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to extract script tables: {str(e)}")
    
    @app.get("/applications/{app_id}/script/table/{table_name}")
    async def get_script_table_data(app_id: str, table_name: str, limit: int = Query(default=100), ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)):
        try:
            result = ws_client.get_app_tables_simple(app_id)
            if not result.get("success", False):
                raise HTTPException(status_code=500, detail=result.get("error", "Failed to get script"))
            script = result.get("script", "")
            if not script:
                raise HTTPException(status_code=404, detail="No script found in app")
            table_data = QlikScriptParser.get_table_preview(script, table_name, limit)
            if not table_data.get("success", False):
                raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
            return table_data
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get table data: {str(e)}")
    
    @app.get("/applications/{app_id}/script/table/{table_name}/html", response_class=HTMLResponse)
    async def get_script_table_html(app_id: str, table_name: str, ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)):
        try:
            result = ws_client.get_app_tables_simple(app_id)
            if not result.get("success", False):
                return f"<html><body><h1>Error</h1><p>{result.get('error', 'Failed')}</p></body></html>"
            script = result.get("script", "")
            if not script:
                return "<html><body><h1>Error</h1><p>No script found</p></body></html>"
            html_content = QlikScriptParser.convert_to_html_table(script, table_name)
            return f"<html><body><h1>{table_name}</h1>{html_content}</body></html>"
        except Exception as e:
            return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>"
    
    @app.get("/applications/{app_id}/script/table/{table_name}/csv", response_class=PlainTextResponse)
    async def get_script_table_csv(app_id: str, table_name: str, ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)):
        try:
            result = ws_client.get_app_tables_simple(app_id)
            if not result.get("success", False):
                return f"Error: {result.get('error', 'Failed')}"
            script = result.get("script", "")
            if not script:
                return "Error: No script found"
            csv_content = QlikScriptParser.convert_to_csv(script, table_name)
            return csv_content or f"Error: Table '{table_name}' not found"
        except Exception as e:
            return f"Error: {str(e)}"

else:
    @app.get("/applications/{app_id}/script/tables")
    async def get_script_tables_unavailable(app_id: str):
        raise HTTPException(status_code=501, detail="Script parser not available")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
