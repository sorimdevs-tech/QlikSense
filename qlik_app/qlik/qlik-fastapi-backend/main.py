from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from typing import List, Dict, Any, Optional
from qlik_client import QlikClient
from qlik_websocket_client import QlikWebSocketClient
from login_validation import router as login_router
from qlik_client import QlikClient

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
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
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



#test user login

#test endpoint  validation 
from fastapi import Body
import os

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
@app.get("/applications/{app_id}/tables")
async def get_app_tables(
    app_id: str, 
    include_script: bool = Query(default=False, description="Include script analysis"),
    ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
):
    """
    Get tables and fields from app using WebSocket.
    Returns table structure, field information, and optionally script analysis.
    """
    try:
        result = ws_client.get_app_tables_simple(app_id)
        
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get tables"))
        
        # Format response
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
from summary_utils import (
    generate_summary, generate_batch_summary, build_summary_text, 
    get_data_quality_score, get_data_preview, HuggingFaceHelper,
    create_data_chat_context
)
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
async def get_vehicle_summary(app_id: str, table_name: str):
    """
    Get summary data for a specific table
    Used for pie chart visualization in frontend
    
    Returns: { summary: { metrics... } }
    """
    try:
        from summary_utils import generate_summary
        
        # Get all table data
        qlik = QlikClient()
        table_data = qlik.get_table_data(app_id, table_name)
        
        if not table_data:
            return {
                "success": False,
                "summary": {},
                "error": "No data found"
            }
        
        # Generate summary using utility function
        summary = generate_summary(table_data, table_name)
        
        return {
            "success": True,
            "summary": summary,
            "table_name": table_name
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
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


    

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*80)
    print(" " * 20 + "Qlik FastAPI Backend v2.0")
    print("="*80)
    print("\nFeatures:")
    print("  ✓ REST API for Qlik Cloud")
    print("  ✓ WebSocket connection to Qlik Engine")
    print("  ✓ Table and field discovery")
    print("  ✓ Script extraction")
    print("  ✓ Data retrieval from tables")
    if SCRIPT_PARSER_AVAILABLE:
        print("  ✓ Script data extraction (INLINE data)")
    else:
        print("  ⚠ Script data extraction DISABLED (qlik_script_parser.py not found)")
    print("\nStarting server...")
    print("="*80 + "\n")
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)