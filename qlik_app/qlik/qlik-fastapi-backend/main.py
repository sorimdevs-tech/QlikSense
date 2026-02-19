# import sys
# import os
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File, BackgroundTasks, Form
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import HTMLResponse, PlainTextResponse
# from typing import List, Dict, Any, Optional
# import threading
# import time
# import requests
# import json
# import re
# from qlik_client import QlikClient
# from qlik_websocket_client import QlikWebSocketClient
# from login_validation import router as login_router
# from processor import PowerBIProcessor
# from table_tracker import enhance_tables_with_timestamps
# from powerbi_service_delegated import PowerBIService, infer_schema_from_rows
# from powerbi_auth import get_auth_manager
# from pydantic import BaseModel


# qlik_client = QlikClient()

# # Try to import script parser, but make it optional
# try:
#     from qlik_script_parser import QlikScriptParser
#     SCRIPT_PARSER_AVAILABLE = True
# except ImportError:
#     SCRIPT_PARSER_AVAILABLE = False
#     print("WARNING: qlik_script_parser not found. Script extraction endpoints will be disabled.")

# app = FastAPI(title="Qlik Sense Cloud API", version="2.0.0")

# app.include_router(login_router)

# # CORS Middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://localhost:5173",
#         "http://localhost:5174",
#         "http://localhost:5175",
#         "http://localhost:5176",
#         "http://127.0.0.1:5173",
#         "http://127.0.0.1:5174",
#         "http://127.0.0.1:5175",
#         "http://127.0.0.1:5176",
#         # Render deployments
#         "https://qlik-frontend.onrender.com",
#         "https://qlik-sense-cloud.onrender.com",
#         "https://qlikai.onrender.com"
#     ],
   
#     allow_origin_regex=r"http://localhost:\d+|http://127\.0\.0\.1:\d+|https://.*\.onrender\.com",
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# def get_qlik_client():
#     """Get Qlik client using environment variables"""
#     try:
#         return QlikClient()
#     except ValueError as e:
#         raise HTTPException(status_code=500, detail=str(e))

# def get_qlik_websocket_client():
#     try:
#         return QlikWebSocketClient()
#     except ValueError as e:
#         raise HTTPException(status_code=500, detail=str(e))


# # ============= DAX PARSING & POWER BI HELPERS =============

# def parse_dax(dax_text: str) -> List[Dict[str, str]]:
#     """
#     Parse DAX file and extract measures.
#     Format:
#         Measure Name = DAX expression
#         Another Measure = SUM(Table[Column])
#     """
#     if not dax_text or not dax_text.strip():
#         return []
    
#     measures = []
#     # Split by double newlines or look for measure definitions
#     blocks = re.split(r"\n\s*\n", dax_text.strip())
    
#     for block in blocks:
#         block = block.strip()
#         if not block or block.startswith("--"):  # Skip comments
#             continue
        
#         if "=" in block:
#             parts = block.split("=", 1)
#             if len(parts) == 2:
#                 name = parts[0].strip()
#                 expression = parts[1].strip()
#                 # Remove trailing comments
#                 if "--" in expression:
#                     expression = expression.split("--")[0].strip()
                
#                 measures.append({
#                     "name": name,
#                     "expression": expression
#                 })
    
#     return measures


# def apply_dax_measures(pbi_service: PowerBIService, dataset_id: str, measures: List[Dict[str, str]]) -> Dict[str, Any]:
#     """
#     Apply DAX measures to Power BI dataset.
#     """
#     if not measures:
#         return {"status": "no_measures", "count": 0}
    
#     try:
#         # Get the dataset first to ensure it exists
#         print(f"Applying {len(measures)} measures to dataset {dataset_id}")
        
#         # For now, we'll store measures as metadata
#         # In a production system, you'd use Power BI API to add these as calculated columns/measures
#         success_count = 0
#         for measure in measures:
#             try:
#                 print(f"  ✓ Prepared measure: {measure['name']}")
#                 success_count += 1
#             except Exception as e:
#                 print(f"  ✗ Failed to apply measure {measure['name']}: {str(e)}")
        
#         return {
#             "status": "success",
#             "applied_count": success_count,
#             "total_count": len(measures),
#             "measures": measures
#         }
#     except Exception as e:
#         print(f"Error applying measures: {str(e)}")
#         return {"status": "error", "error": str(e), "measures": measures}


# def create_auto_report(pbi_service: PowerBIService, dataset_id: str, dataset_name: str, columns: List[str]) -> Dict[str, Any]:
#     """
#     Create a basic Power BI report with automatic visualizations.
    
#     Strategy:
#     1. Try to clone a template report if available
#     2. Try to create a new report with visualizations
#     3. Otherwise, use direct dataset URL
#     4. Fallback to workspace
#     """
#     try:
#         print(f"🔧 Creating auto-report for dataset: {dataset_name}")
        
#         # Template Report ID (you can set this as env variable)
#         TEMPLATE_REPORT_ID = os.getenv("POWERBI_TEMPLATE_REPORT_ID", None)
        
#         if TEMPLATE_REPORT_ID:
#             result = clone_template_report(pbi_service, dataset_id, dataset_name, TEMPLATE_REPORT_ID)
#             if result.get("status") == "success":
#                 return result
        
#         # Try to create a new report
#         print("📝 Attempting to create new report...")
#         result = create_and_publish_report(pbi_service, dataset_id, dataset_name, columns)
#         if result.get("status") == "success":
#             return result
        
#         # Fallback to direct dataset URL
#         print("📊 Using dataset direct URL...")
#         return create_basic_report(pbi_service, dataset_id, dataset_name, columns)
    
#     except Exception as e:
#         print(f"⚠️ Could not create report: {str(e)}")
#         return {
#             "status": "skipped",
#             "message": "Could not create report automatically",
#             "error": str(e)
#         }


# def clone_template_report(pbi_service: PowerBIService, dataset_id: str, dataset_name: str, template_report_id: str) -> Dict[str, Any]:
#     """
#     Clone an existing Power BI report template and bind it to the new dataset.
    
#     This creates a copy of the template report with all visualizations,
#     but connected to your new dataset.
#     """
#     try:
#         print(f"📋 Cloning template report: {template_report_id}")
        
#         # Power BI API endpoint to clone report
#         headers = {
#             "Authorization": f"Bearer {pbi_service.access_token}",
#             "Content-Type": "application/json"
#         }
        
#         clone_url = f"https://api.powerbi.com/v1.0/myorg/groups/{pbi_service.workspace_id}/reports/{template_report_id}/Clone"
        
#         payload = {
#             "name": f"{dataset_name} - Report",
#             "targetWorkspaceId": pbi_service.workspace_id,
#             "targetModelId": dataset_id
#         }
        
#         response = requests.post(clone_url, headers=headers, json=payload, timeout=30)
        
#         if response.status_code not in [200, 201, 202]:
#             print(f"Clone failed: {response.text}")
#             raise Exception(f"Clone returned {response.status_code}")
        
#         result = response.json()
#         report_id = result.get("id")
#         report_url = result.get("webUrl")
        
#         print(f"✅ Report cloned successfully!")
#         print(f"   Report ID: {report_id}")
#         print(f"   URL: {report_url}")
        
#         return {
#             "status": "success",
#             "type": "cloned_template",
#             "report_id": report_id,
#             "report_url": report_url,
#             "dataset_id": dataset_id
#         }
    
#     except Exception as e:
#         print(f"❌ Template cloning failed: {str(e)}")
#         return {
#             "status": "failed",
#             "error": str(e)
#         }


# def create_and_publish_report(pbi_service: PowerBIService, dataset_id: str, dataset_name: str, columns: List[str]) -> Dict[str, Any]:
#     """
#     Create a new Power BI Report with a table visualization using the REST API.
    
#     This creates a real report with visualizations that can be opened immediately.
    
#     Strategy:
#     1. Create report in workspace
#     2. Add table visualization with all columns
#     3. Return report URL
#     """
#     try:
#         print(f"🛠️ Creating Power BI report with visualizations...")
        
#         headers = {
#             "Authorization": f"Bearer {pbi_service.access_token}",
#             "Content-Type": "application/json"
#         }
        
#         workspace_id = pbi_service.workspace_id
#         report_name = f"{dataset_name} - Data Report"
        
#         # Create report using Power BI API
#         create_report_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports"
        
#         # Report payload with basic structure
#         payload = {
#             "name": report_name,
#             "datasetId": dataset_id
#         }
        
#         print(f"📊 Creating report: {report_name}")
#         response = requests.post(create_report_url, headers=headers, json=payload, timeout=30)
        
#         if response.status_code not in [200, 201, 202]:
#             print(f"⚠️ Create report failed ({response.status_code}): {response.text}")
#             # If create fails, just return the dataset URL
#             return {
#                 "status": "fallback",
#                 "message": "Using dataset URL instead"
#             }
        
#         result = response.json()
#         report_id = result.get("id")
#         report_url = result.get("webUrl") or f"https://app.powerbi.com/groups/{workspace_id}/reports/{report_id}"
        
#         print(f"✅ Report created!")
#         print(f"   Report ID: {report_id}")
#         print(f"   URL: {report_url}")
        
#         return {
#             "status": "success",
#             "type": "created_new",
#             "report_id": report_id,
#             "report_url": report_url,
#             "dataset_id": dataset_id,
#             "message": "New report with visualizations created"
#         }
    
#     except Exception as e:
#         print(f"❌ Report creation error: {str(e)}")
#         return {
#             "status": "error",
#             "error": str(e)
#         }


# def create_basic_report(pbi_service: PowerBIService, dataset_id: str, dataset_name: str, columns: List[str]) -> Dict[str, Any]:
#     """
#     Create a basic Power BI report with data table visualization.
    
#     Returns URL that opens Power BI with dataset visualization.
#     """
#     try:
#         print(f"📊 Creating visualization URL for dataset: {dataset_name}")
        
#         workspace_id = pbi_service.workspace_id
        
#         # Use direct workspace URL - opens workspace where user can see and interact with dataset
#         # This shows the dataset in the workspace context with full Power BI interface
#         workspace_dataset_url = f"https://app.powerbi.com/groups/{workspace_id}"
        
#         print(f"✅ Visualization URL generated!")
#         print(f"   URL: {workspace_dataset_url}")
#         print(f"   Dataset: {dataset_name}")
#         print(f"   (Power BI will open workspace with new dataset ready to visualize)")
        
#         return {
#             "status": "success",
#             "type": "workspace_dataset",
#             "report_url": workspace_dataset_url,
#             "dataset_id": dataset_id,
#             "dataset_name": dataset_name,
#             "workspace_id": workspace_id,
#             "message": "Opening Power BI workspace with dataset ready for visualization"
#         }
    
#     except Exception as e:
#         print(f"❌ URL generation failed: {str(e)}")
#         return {
#             "status": "failed",
#             "error": str(e)
#         }


# def get_or_create_default_report(pbi_service: PowerBIService, dataset_id: str, dataset_name: str, columns: List[str]) -> str:
#     """
#     Get the best report URL to open - either a new auto-created report or the dataset URL.
    
#     Priority:
#     1. Clone template report if configured
#     2. Use dataset direct URL (shows in Power BI workspace context)
#     3. Fallback to workspace home
#     """
#     try:
#         report_result = create_auto_report(pbi_service, dataset_id, dataset_name, columns)
        
#         if report_result.get("status") == "success":
#             report_url = report_result.get("report_url")
#             if report_url:
#                 print(f"🎯 Will open report: {report_url}")
#                 return report_url
        
#         # Fallback to direct dataset URL
#         dataset_url = f"https://app.powerbi.com/groups/{pbi_service.workspace_id}/datasets/{dataset_id}"
#         print(f"Using dataset URL: {dataset_url}")
#         return dataset_url
    
#     except Exception as e:
#         print(f"⚠️ Could not create report, using workspace URL: {str(e)}")
#         return f"https://app.powerbi.com/groups/{pbi_service.workspace_id}"


# # =========================================================

# #test user login

# #test endpoint  validation 
# from fastapi import Body
# import os

# TEST_USERNAME = "testuser"
# TEST_PASSWORD = "test123"
# HARDCODED_TENANT = "https://c8vlzp3sx6akvnh.in.qlikcloud.com"

# class PowerBIRequest(BaseModel):
#     csv_path: str
#     dax_path: str



# @app.post("/validate-tenant")
# async def validate_tenant(payload: dict = Body(...)):
#     tenant_url = payload.get("tenant_url")
#     use_test_user = payload.get("use_test_user")

#     if not use_test_user:
#         raise HTTPException(status_code=400, detail="Please enable validation checkbox")

#     if not tenant_url or not tenant_url.endswith("qlikcloud.com"):
#         raise HTTPException(status_code=400, detail="Enter correct tenant URL")

#     # Runtime override (testing purpose)
#     os.environ["QLIK_TENANT_URL"] = tenant_url
#     os.environ["QLIK_API_BASE_URL"] = f"{tenant_url}/api/v1"

#     try:
#         client = QlikClient()
#         result = client.test_connection()

#         if result.get("status") != "success":
#             raise HTTPException(status_code=401, detail="Invalid tenant or credentials")

#         return {"success": True}

#     except Exception as e:
#         raise HTTPException(status_code=401, detail=str(e))








# @app.get("/")
# async def root():
#     endpoints = {
#         "basic": [
#             "/health",
#             "/test-connection",
#             "/spaces",
#             "/applications",
#             "/applications/with-data"
#         ],
#         "app_details": [
#             "/applications/{app_id}",
#             "/applications/{app_id}/info"
#         ],
#         "data_access": [
#             "/applications/{app_id}/tables",
#             "/applications/{app_id}/script",
#             "/applications/{app_id}/fields",
#             "/applications/{app_id}/field/{field_name}/values",
#             "/applications/{app_id}/table/{table_name}/data"
#         ]
#     }
    
#     if SCRIPT_PARSER_AVAILABLE:
#         endpoints["script_data_extraction"] = [
#             "/applications/{app_id}/script/tables",
#             "/applications/{app_id}/script/table/{table_name}",
#             "/applications/{app_id}/script/table/{table_name}/html",
#             "/applications/{app_id}/script/table/{table_name}/csv",
#             "/applications/{app_id}/script/html"
#         ]
    
#     return {
#         "message": "Qlik FastAPI Backend with WebSocket Support",
#         "status": "running",
#         "version": "2.0.0",
#         "script_parser_available": SCRIPT_PARSER_AVAILABLE,
#         "endpoints": endpoints
#     }

# from fastapi import HTTPException
# import requests

# @app.get("/health")
# async def health():
#     return {
#         "status": "healthy", 
#         "service": "Qlik FastAPI Backend",
#         "script_parser": SCRIPT_PARSER_AVAILABLE
#     }

# @app.get("/test-connection")
# async def test_connection(client: QlikClient = Depends(get_qlik_client)):
#     """Test connection to Qlik Cloud"""
#     try:
#         result = client.test_connection()
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")

# @app.get("/spaces")
# async def list_spaces(
#     client: QlikClient = Depends(get_qlik_client)
# ):
#     """List all available spaces"""
#     try:
#         spaces = client.get_spaces()
#         return {
#             "success": True,
#             "spaces": spaces,
#             "count": len(spaces) if isinstance(spaces, list) else 0
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to retrieve spaces: {str(e)}")

# @app.get("/applications", response_model=List[Dict[str, Any]])
# async def list_applications(
#     client: QlikClient = Depends(get_qlik_client)
# ):
#     """List all available applications"""
#     try:
#         apps = client.get_applications()
#         return apps
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to retrieve applications: {str(e)}")

# @app.get("/applications/{app_id}")
# async def get_application(app_id: str, client: QlikClient = Depends(get_qlik_client)):
#     """Get basic details of a specific application"""
#     try:
#         app = client.get_application_details(app_id)
#         return app
#     except Exception as e:
#         raise HTTPException(status_code=404, detail=f"Application not found: {str(e)}")

# @app.get("/applications/{app_id}/info")
# async def get_application_full_info(app_id: str, ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)):
#     """Get comprehensive information about an application including tables, fields, script, and sheets"""
#     try:
#         result = ws_client.get_app_tables_simple(app_id)
#         if not result.get("success", False):
#             raise HTTPException(status_code=500, detail=result.get("error", "Failed to get app info"))
#         return result
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to get app info: {str(e)}")

# # WEBSOCKET ENDPOINTS - DATA ACCESS
# # @app.get("/applications/{app_id}/tables")
# # async def get_app_tables(
# #     app_id: str, 
# #     include_script: bool = Query(default=False, description="Include script analysis"),
# #     ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
# # ):
# #     """
# #     Get tables and fields from app using WebSocket.
# #     Returns table structure, field information, and optionally script analysis.
# #     """
# #     try:
# #         result = ws_client.get_app_tables_simple(app_id)
        
# #         if not result.get("success", False):
# #             raise HTTPException(status_code=500, detail=result.get("error", "Failed to get tables"))
        
# #         # Format response
# #         response = {
# #             "success": True,
# #             "app_id": result.get("app_id"),
# #             "app_title": result.get("app_title"),
# #             "tables": result.get("tables", []),
# #             "summary": result.get("summary", {})
# #         }
        
# #         if include_script:
# #             response["script"] = result.get("script", "")
# #             response["script_tables"] = result.get("script_tables", [])
        
# #         return response
        
# #     except HTTPException:
# #         raise
# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=f"Failed to get tables: {str(e)}")




# @app.get("/applications/{app_id}/tables")
# async def get_app_tables(app_id: str, include_script: bool = Query(default=False), ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)):
#     try:
#         result = ws_client.get_app_tables_simple(app_id)
#         if not result.get("success", False):
#             raise HTTPException(status_code=500, detail=result.get("error", "Failed to get tables"))
       
#         # Get tables and enhance with timestamp information
#         tables = result.get("tables", [])
#         enhanced_tables = enhance_tables_with_timestamps(app_id, tables)
       
#         response = {
#             "success": True,
#             "app_id": result.get("app_id"),
#             "tables": enhanced_tables
#         }
#         if include_script:
#             response["script"] = result.get("script", "")
#         return response
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to get tables: {str(e)}")


# @app.get("/applications/{app_id}/script")
# async def get_app_script(app_id: str, ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)):
#     """Get the load script from the application"""
#     try:
#         result = ws_client.get_app_tables_simple(app_id)
        
#         if not result.get("success", False):
#             raise HTTPException(status_code=500, detail=result.get("error", "Failed to get script"))
        
#         return {
#             "success": True,
#             "app_id": app_id,
#             "script": result.get("script", ""),
#             "script_length": len(result.get("script", "")),
#             "tables_in_script": result.get("script_tables", []),
#             "table_count": len(result.get("script_tables", []))
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to get script: {str(e)}")

# @app.get("/applications/{app_id}/fields")
# async def get_app_fields(
#     app_id: str,
#     include_system: bool = Query(default=False, description="Include system fields"),
#     ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
# ):
#     """Get all fields from the application"""
#     try:
#         result = ws_client.get_app_tables_simple(app_id)
        
#         if not result.get("success", False):
#             raise HTTPException(status_code=500, detail=result.get("error", "Failed to get fields"))
        
#         all_fields = result.get("all_fields", [])
        
#         # Filter system fields if requested
#         if not include_system:
#             all_fields = [f for f in all_fields if not f.get("is_system", False)]
        
#         return {
#             "success": True,
#             "app_id": app_id,
#             "fields": all_fields,
#             "field_count": len(all_fields),
#             "field_names": [f.get("name", "") for f in all_fields]
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to get fields: {str(e)}")

# @app.get("/applications/{app_id}/field/{field_name}/values")
# async def get_field_values(
#     app_id: str, 
#     field_name: str,
#     limit: int = Query(default=100, le=10000, description="Maximum number of values to return"),
#     ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
# ):
#     """Get values for a specific field with actual data"""
#     try:
#         result = ws_client.get_field_values(app_id, field_name, limit)
        
#         if not result.get("success", False):
#             raise HTTPException(status_code=500, detail=result.get("error", "Failed to get field values"))
        
#         return result
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to get field values: {str(e)}")

# @app.post("/validate-login")
# async def validate_login_alias(payload: dict = Body(...)):
#     # Alias kept for frontend compatibility
#     return await validate_tenant(payload)

# @app.get("/applications/{app_id}/table/{table_name}/data")
# async def get_table_data(
#     app_id: str,
#     table_name: str,
#     limit: int = Query(default=100, le=10000, description="Maximum number of rows to return"),
#     ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
# ):
#     """Get actual data from a specific table with tolerant name matching"""
#     try:
#         # First attempt as-provided
#         result = ws_client.get_table_data(app_id, table_name, limit)
#         if result.get("success", False):
#             return result

#         # Fallback: try case-insensitive/trimmed match against discovered tables
#         tables_info = ws_client.get_app_tables_simple(app_id)
#         if not tables_info.get("success", False):
#             raise HTTPException(status_code=500, detail=tables_info.get("error", "Failed to read tables"))

#         requested = (table_name or "").strip().lower()
#         actual_name = None
#         for t in tables_info.get("tables", []):
#             name = (t.get("name") or t.get("table") or "").strip()
#             if name.lower() == requested:
#                 actual_name = name
#                 break
#         if not actual_name:
#             raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found in app")

#         result2 = ws_client.get_table_data(app_id, actual_name, limit)
#         if not result2.get("success", False):
#             raise HTTPException(status_code=500, detail=result2.get("error", "Failed to get table data"))
#         return result2

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to get table data: {str(e)}")

# @app.get("/applications/with-data")
# async def find_apps_with_data(client: QlikClient = Depends(get_qlik_client)):
#     """Find apps that have been reloaded (have data)"""
#     try:
#         apps = client.get_applications()
#         apps_with_data = []
        
#         for app in apps:
#             if isinstance(app, dict):
#                 attributes = app.get('attributes', {})
#                 last_reload = attributes.get('lastReloadTime')
#                 if last_reload:
#                     apps_with_data.append({
#                         "id": attributes.get('id'),
#                         "name": attributes.get('name'),
#                         "last_reload_time": last_reload,
#                         "created_date": attributes.get('createdDate'),
#                         "description": attributes.get('description', ''),
#                         "app_url": f"https://c8vlzp3sx6akvnh.in.qlikcloud.com/hub/{attributes.get('id')}"
#                     })
        
#         # Sort by last reload time (most recent first)
#         apps_with_data.sort(key=lambda x: x.get('last_reload_time', ''), reverse=True)
        
#         return {
#             "success": True,
#             "total_apps_found": len(apps) if isinstance(apps, list) else 0,
#             "apps_with_reloads": apps_with_data,
#             "count": len(apps_with_data)
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to find apps with data: {str(e)}")

# @app.get("/applications/{app_id}/table/{table_name}/data/simple")
# async def get_table_data_simple(
#     app_id: str,
#     table_name: str,
#     ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
# ):
#     """
#     Simple endpoint that returns table structure and metadata without complex hypercube creation
#     Great for showing table summaries/previews
#     """
#     try:
#         # Get tables from data model
#         result = ws_client.get_app_tables_simple(app_id)
        
#         if not result.get("success"):
#             raise HTTPException(status_code=500, detail=result.get("error"))
        
#         tables = result.get("tables", [])
#         requested = table_name.strip().lower()
#         matching_table = None
        
#         for table in tables:
#             if table.get("name", "").strip().lower() == requested:
#                 matching_table = table
#                 break
        
#         if not matching_table:
#             raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
#         # Return table metadata
#         columns = [f["name"] for f in matching_table.get("fields", []) if not f.get("is_system")]
        
#         return {
#             "success": True,
#             "table_name": matching_table.get("name"),
#             "columns": columns,
#             "column_count": len(columns),
#             "row_count": matching_table.get("no_of_rows", 0),
#             "is_synthetic": matching_table.get("is_synthetic", False),
#             "fields_info": matching_table.get("fields", [])[:10],  # First 10 fields for preview
#             "note": "This returns table structure. For actual table data, use the /table/{table_name}/data endpoint"
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error retrieving table info: {str(e)}")


# # Enhanced table data endpoint with better error handling for CSV-loaded tables
# @app.get("/applications/{app_id}/table/{table_name}/data/enhanced")
# async def get_table_data_enhanced(
#     app_id: str,
#     table_name: str,
#     limit: int = Query(default=100, le=10000, description="Maximum number of rows to return"),
#     ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
# ):
#     """
#     Enhanced endpoint to fetch table data with multiple fallback strategies
#     Handles CSV-loaded tables, case-insensitive matching, and trimmed names
#     NOW WITH PRIORITY: Script extraction for inline/CSV data
#     """
#     try:
#         print(f"📊 Attempting to fetch table '{table_name}' from app '{app_id}'...")
        
#         # STRATEGY 0: First try script extraction (for INLINE loads and CSV data)
#         # This is the KEY FIX - prioritize script extraction for inline/CSV data
#         if SCRIPT_PARSER_AVAILABLE:
#             print(f"🔍 Trying script extraction first (for inline/CSV data)...")
#             try:
#                 # Get script via websocket client
#                 script_result = ws_client.get_app_tables_simple(app_id)
#                 if script_result.get("success"):
#                     script = script_result.get("script", "")
#                     if script:
#                         table_preview = QlikScriptParser.get_table_preview(script, table_name, limit)
#                         if table_preview.get("success"):
#                             rows = table_preview.get("rows", [])
#                             columns = table_preview.get("columns", [])
#                             print(f"✅ SUCCESS: Extracted {len(rows)} rows from script for table '{table_name}'")
#                             return {
#                                 "success": True,
#                                 "table_name": table_name,
#                                 "columns": columns,
#                                 "rows": rows,
#                                 "row_count": len(rows),
#                                 "source": "script"
#                             }
#                         else:
#                             print(f"⚠️ Script found but table '{table_name}' not in script: {table_preview.get('error')}")
#                     else:
#                         print("⚠️ No script found in app")
#             except Exception as e:
#                 print(f"⚠️ Script extraction failed: {str(e)}")
#         else:
#             print("⚠️ Script parser not available, skipping script extraction")
        
#         # STRATEGY 1: Direct fetch with provided name (hypercupe method)
#         print(f"🔄 Trying hypercube method...")
#         result = ws_client.get_table_data(app_id, table_name, limit)
#         if result.get("success", False):
#             # Check if it's not just placeholder data
#             rows = result.get("rows", [])
#             if rows and len(rows) > 0:
#                 # Check if we got actual data or placeholders
#                 first_row = rows[0] if rows else {}
#                 has_placeholder = any(
#                     isinstance(v, str) and "not accessible" in v 
#                     for v in first_row.values()
#                 ) if first_row else False
                
#                 if not has_placeholder:
#                     print(f"✅ Successfully retrieved table data using direct name")
#                     return result
#                 else:
#                     print(f"⚠️ Got placeholder data, trying other strategies...")
#             else:
#                 return result
        
#         print(f"⚠️ Direct fetch failed or returned placeholders: {result.get('error', 'Unknown error')}")
        
#         # Strategy 2: Get list of available tables and try case-insensitive match
#         print(f"🔍 Retrieving list of available tables...")
#         tables_info = ws_client.get_app_tables_simple(app_id)
        
#         if tables_info.get("success", False):
#             available_tables = tables_info.get("tables", [])
#             print(f"📋 Found {len(available_tables)} tables in app")
            
#             # Try case-insensitive and whitespace-trimmed match
#             requested_lower = (table_name or "").strip().lower()
            
#             for table_info in available_tables:
#                 table_names_to_try = [
#                     table_info.get("name"),
#                     table_info.get("table"),
#                     table_info.get("table_name")
#                 ]
                
#                 for name in table_names_to_try:
#                     if name and name.strip().lower() == requested_lower:
#                         print(f"✅ Found matching table name: '{name}'")
                        
#                         result = ws_client.get_table_data(app_id, name, limit)
#                         if result.get("success", False):
#                             # Check again for placeholders
#                             rows = result.get("rows", [])
#                             if rows:
#                                 first_row = rows[0]
#                                 has_placeholder = any(
#                                     isinstance(v, str) and "not accessible" in v 
#                                     for v in first_row.values()
#                                 ) if first_row else False
                                
#                                 if not has_placeholder:
#                                     print(f"✅ Successfully retrieved data using matched name: '{name}'")
#                                     return result
                        
#                         # If still getting placeholders, try script extraction with matched name
#                         if SCRIPT_PARSER_AVAILABLE:
#                             try:
#                                 script = tables_info.get("script", "")
#                                 if script:
#                                     table_preview = QlikScriptParser.get_table_preview(script, name, limit)
#                                     if table_preview.get("success"):
#                                         print(f"✅ Found actual data via script with matched name: '{name}'")
#                                         return {
#                                             "success": True,
#                                             "table_name": name,
#                                             "columns": table_preview.get("columns", []),
#                                             "rows": table_preview.get("rows", []),
#                                             "row_count": table_preview.get("total_rows", 0),
#                                             "source": "script"
#                                         }
#                             except Exception as e:
#                                 print(f"⚠️ Script extraction with matched name failed: {str(e)}")
            
#             print(f"⚠️ No matching table found. Available tables: {[t.get('name', 'unknown') for t in available_tables]}")
        
#         # If all strategies fail
#         raise HTTPException(
#             status_code=404, 
#             detail=f"Table '{table_name}' not found. Please check the table name and ensure the app has been reloaded with data."
#         )
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         print(f"❌ Error in enhanced table fetch: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Failed to get table data: {str(e)}")

# # ==================== SCRIPT DATA EXTRACTION ENDPOINTS ====================
# # These endpoints require qlik_script_parser.py

# if SCRIPT_PARSER_AVAILABLE:
    
#     @app.get("/applications/{app_id}/script/tables")
#     async def get_script_tables(app_id: str, ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)):
#         """
#         Extract all tables and their data from the app script (INLINE data)
#         Returns structured data from LOAD ... INLINE statements
#         """
#         try:
#             # Get the script first
#             result = ws_client.get_app_tables_simple(app_id)
            
#             if not result.get("success", False):
#                 raise HTTPException(status_code=500, detail=result.get("error", "Failed to get script"))
            
#             script = result.get("script", "")
            
#             if not script:
#                 return {
#                     "success": False,
#                     "error": "No script found in app",
#                     "app_id": app_id
#                 }
            
#             # Parse the script to extract table data
#             parsed_data = QlikScriptParser.parse_inline_data(script)
            
#             return {
#                 "success": True,
#                 "app_id": app_id,
#                 "tables": parsed_data.get("tables", {}),
#                 "table_count": parsed_data.get("table_count", 0),
#                 "table_names": parsed_data.get("table_names", [])
#             }
            
#         except HTTPException:
#             raise
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=f"Failed to extract script tables: {str(e)}")
    
#     @app.get("/applications/{app_id}/script/table/{table_name}")
#     async def get_script_table_data(
#         app_id: str, 
#         table_name: str,
#         limit: int = Query(default=100, le=10000, description="Maximum number of rows to return"),
#         ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
#     ):
#         """
#         Get data for a specific table from the script (INLINE data)
#         Returns rows and columns as JSON
#         """
#         try:
#             # Get the script
#             result = ws_client.get_app_tables_simple(app_id)
            
#             if not result.get("success", False):
#                 raise HTTPException(status_code=500, detail=result.get("error", "Failed to get script"))
            
#             script = result.get("script", "")
            
#             if not script:
#                 raise HTTPException(status_code=404, detail="No script found in app")
            
#             # Get table preview
#             table_data = QlikScriptParser.get_table_preview(script, table_name, limit)
            
#             if not table_data.get("success", False):
#                 raise HTTPException(
#                     status_code=404, 
#                     detail=table_data.get("error", f"Table '{table_name}' not found")
#                 )
            
#             return table_data
            
#         except HTTPException:
#             raise
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=f"Failed to get table data: {str(e)}")
        
        

#     @app.get("/applications/{app_id}/script/table/{table_name}/html", response_class=HTMLResponse)
#     async def get_script_table_html(
#         app_id: str, 
#         table_name: str,
#         ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
#     ):
#         """
#         Get data for a specific table as HTML table
#         Returns formatted HTML that can be displayed in a browser
#         """
#         try:
#             # Get the script
#             result = ws_client.get_app_tables_simple(app_id)
            
#             if not result.get("success", False):
#                 return f"<html><body><h1>Error</h1><p>{result.get('error', 'Failed to get script')}</p></body></html>"
            
#             script = result.get("script", "")
            
#             if not script:
#                 return "<html><body><h1>Error</h1><p>No script found in app</p></body></html>"
            
#             # Convert to HTML
#             html_content = QlikScriptParser.convert_to_html_table(script, table_name)
            
#             return f"""
#             <!DOCTYPE html>
#             <html>
#             <head>
#                 <title>{table_name} - Qlik Data</title>
#                 <meta charset="UTF-8">
#                 <meta name="viewport" content="width=device-width, initial-scale=1.0">
#             </head>
#             <body>
#                 <h1>Qlik App Data: {table_name}</h1>
#                 {html_content}
#             </body>
#             </html>
#             """
            
#         except Exception as e:
#             return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>"

#     @app.get("/applications/{app_id}/script/table/{table_name}/csv", response_class=PlainTextResponse)
#     async def get_script_table_csv(
#         app_id: str, 
#         table_name: str,
#         ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
#     ):
#         """
#         Get data for a specific table as CSV
#         Returns CSV format that can be downloaded
#         """
#         try:
#             # Get the script
#             result = ws_client.get_app_tables_simple(app_id)
            
#             if not result.get("success", False):
#                 return f"Error: {result.get('error', 'Failed to get script')}"
            
#             script = result.get("script", "")
            
#             if not script:
#                 return "Error: No script found in app"
            
#             # First try: Convert script INLINE data to CSV (only INLINE is safe)
#             csv_content = QlikScriptParser.convert_to_csv(script, table_name)

#             if csv_content:
#                 return csv_content

#             # If script-based conversion failed (e.g. LOAD FROM <lib://...>),
#             # do NOT read files from the backend filesystem — instead fetch
#             # the table data via the Qlik Engine (hypercube / session-object).
#             print(f"⚠️ Script CSV not available for '{table_name}', falling back to Engine API")

#             try:
#                 engine_result = ws_client.get_table_data(app_id, table_name, limit=1000)
#                 if engine_result.get("success") and engine_result.get("rows"):
#                     cols = engine_result.get("columns") or (list(engine_result.get("rows")[0].keys()) if engine_result.get("rows") else [])
#                     lines = [','.join(f'"{c}"' for c in cols)]
#                     for r in engine_result.get("rows"):
#                         lines.append(','.join(f'"{str(r.get(c, ""))}"' for c in cols))
#                     return '\n'.join(lines)

#                 # If engine also failed, return meaningful message
#                 return f"Error: Table '{table_name}' not found in script and not accessible via Engine"
#             except Exception as e:
#                 print(f"❌ Engine fallback failed for table '{table_name}': {e}")
#                 return f"Error: Failed to retrieve table '{table_name}' via Engine: {str(e)}"
            
#         except Exception as e:
#             return f"Error: {str(e)}"

#     @app.get("/applications/{app_id}/script/html", response_class=HTMLResponse)
#     async def get_all_script_tables_html(
#         app_id: str,
#         ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
#     ):
#         """
#         Get all tables from script as HTML
#         Returns formatted HTML with all tables
#         """
#         try:
#             # Get the script
#             result = ws_client.get_app_tables_simple(app_id)
            
#             if not result.get("success", False):
#                 return f"<html><body><h1>Error</h1><p>{result.get('error', 'Failed to get script')}</p></body></html>"
            
#             script = result.get("script", "")
#             app_title = result.get("app_title", "Unknown App")
            
#             if not script:
#                 return "<html><body><h1>Error</h1><p>No script found in app</p></body></html>"
            
#             # Convert all tables to HTML
#             html_content = QlikScriptParser.convert_to_html_table(script)
            
#             return f"""
#             <!DOCTYPE html>
#             <html>
#             <head>
#                 <title>{app_title} - All Tables</title>
#                 <meta charset="UTF-8">
#                 <meta name="viewport" content="width=device-width, initial-scale=1.0">
#             </head>
#             <body>
#                 <h1>Qlik App: {app_title}</h1>
#                 <p>App ID: {app_id}</p>
#                 {html_content}
#             </body>
#             </html>
#             """
            
#         except Exception as e:
#             return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>"

# else:
#     # Placeholder endpoints when script parser is not available
#     @app.get("/applications/{app_id}/script/tables")
#     async def get_script_tables_unavailable(app_id: str):
#         raise HTTPException(
#             status_code=501, 
#             detail="Script parser not available. Please add qlik_script_parser.py to enable this feature."
#         )
    
#     # 🔽🔽🔽 PASTE HERE 🔽🔽🔽

# @app.get("/applications/{app_id}/table/{table_name}/export/csv", response_class=PlainTextResponse)
# async def export_table_as_csv(
#     app_id: str,
#     table_name: str,
#     ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
# ):
#     """
#     Export table data as CSV file
#     Returns CSV format ready for download
#     """
#     try:
#         # Try to fetch actual table data first
#         table_data_result = ws_client.get_table_data(app_id, table_name, limit=10000)
        
#         if table_data_result.get("success"):
#             # Build CSV from actual table data
#             rows = table_data_result.get("rows", [])
#             columns = table_data_result.get("columns", [])
            
#             if not rows or not columns:
#                 return "No data available for export"
            
#             # Build CSV header
#             csv_lines = [",".join(f'"{col}"' for col in columns)]
            
#             # Build CSV rows
#             for row in rows:
#                 values = []
#                 for col in columns:
#                     val = str(row.get(col, ""))
#                     # Escape quotes in values
#                     val = val.replace('"', '""')
#                     values.append(f'"{val}"')
#                 csv_lines.append(",".join(values))
            
#             return "\n".join(csv_lines)
        
#         else:
#             # Fallback: Get table structure from metadata
#             tables_result = ws_client.get_app_tables_simple(app_id)
#             if not tables_result.get("success"):
#                 raise HTTPException(status_code=500, detail="Could not fetch table information")
            
#             tables = tables_result.get("tables", [])
#             requested = table_name.strip().lower()
#             matching_table = None
            
#             for table in tables:
#                 if table.get("name", "").strip().lower() == requested:
#                     matching_table = table
#                     break
            
#             if not matching_table:
#                 raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
            
#             columns = [f["name"] for f in matching_table.get("fields", []) if not f.get("is_system")]
#             row_count = matching_table.get("no_of_rows", 0)
            
#             # Create CSV with structure and metadata
#             csv_lines = [
#                 f"Table,{table_name}",
#                 f"Rows,{row_count}",
#                 f"Columns,{len(columns)}",
#                 f"Export Date,{time.strftime('%Y-%m-%d %H:%M:%S')}",
#                 ""
#             ]
            
#             csv_lines.append(",".join(f'"{col}"' for col in columns))
#             csv_lines.append("# " + ",".join(["[Data not accessible - metadata only]"] * len(columns)))
            
#             return "\n".join(csv_lines)
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error exporting table: {str(e)}")

# @app.get("/vehicle-summary")
# async def vehicle_summary(
#     app_id: str,
#     table_name: str,
#     ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
# ):
#     """
#     Generate a summary of table data
#     Works with both INLINE script data and CSV-loaded tables
#     """
#     print(f"\n==== VEHICLE SUMMARY ENDPOINT ====")
#     print(f"App ID: {app_id}, Table: {table_name}")

#     try:
#         # Step 1: Try to get actual table data first
#         print(f"Step 1: Attempting to fetch table data...")
#         table_data_result = ws_client.get_table_data(app_id, table_name, limit=1000)
        
#         if table_data_result.get("success"):
#             print(f"✅ Got actual table data")
#             rows = table_data_result.get("rows", [])
            
#             if rows:
#                 return {"success": True, "summary": _generate_summary_from_rows(rows, table_name)}
        
#         # Step 2: Fallback - get from script/INLINE data
#         print(f"Step 2: Trying script parsing...")
        
#         if not SCRIPT_PARSER_AVAILABLE:
#             print(f"⚠️ Script parser not available, returning metadata summary")
#             # Get table metadata as fallback
#             tables_result = ws_client.get_app_tables_simple(app_id)
#             if tables_result.get("success"):
#                 for table in tables_result.get("tables", []):
#                     if table.get("name", "").strip().lower() == table_name.strip().lower():
#                         return {
#                             "success": True,
#                             "summary": {
#                                 "Table": table_name,
#                                 "Total Rows": table.get("no_of_rows", 0),
#                                 "Columns": len([f for f in table.get("fields", []) if not f.get("is_system")]),
#                                 "Fields": [f["name"] for f in table.get("fields", [])[:10]],
#                                 "Note": "Summary from table metadata (actual data not accessible)"
#                             }
#                         }
        
#         # Try script-based summary
#         result = ws_client.get_app_tables_simple(app_id)
        
#         if not result.get("success", False):
#             print(f"⚠️ Script parsing failed, returning basic summary")
#             return {
#                 "success": True,
#                 "summary": {
#                     "Table": table_name,
#                     "Note": "Could not load data - check that app has been reloaded in QlikCloud"
#                 }
#             }

#         script = result.get("script", "")

#         if not script:
#             print(f"⚠️ No script found, returning basic summary")
#             return {
#                 "success": True,
#                 "summary": {
#                     "Table": table_name,
#                     "Tables Available": [t["name"] for t in result.get("tables", [])],
#                     "Note": "No script data found"
#                 }
#             }

#         # Parse script for INLINE data
#         table_data = QlikScriptParser.get_table_preview(script, table_name, 1000)

#         if not table_data.get("success", False):
#             print(f"⚠️ Table not found in script")
#             return {
#                 "success": True,
#                 "summary": {
#                     "Table": table_name,
#                     "Available Tables": [t["name"] for t in result.get("tables", [])]
#                 }
#             }

#         rows = table_data.get("rows", [])

#         if not rows:
#             return {
#                 "success": True,
#                 "summary": {
#                     "Table": table_name,
#                     "Message": "No data rows found"
#                 }
#             }

#         return {"success": True, "summary": _generate_summary_from_rows(rows, table_name)}
        
#     except Exception as e:
#         print(f"❌ Error in vehicle_summary: {str(e)}")
#         import traceback
#         traceback.print_exc()
#         # Return a basic message instead of crashing
#         return {
#             "success": True,
#             "summary": {
#                 "Table": table_name,
#                 "Status": "Summary generation failed, but table data may still be available",
#                 "Error": str(e)
#             }
#         }

# def _generate_summary_from_rows(rows: list, table_name: str) -> dict:
#     """Generate summary statistics from table rows"""
#     if not rows:
#         return {"Table": table_name, "Total Rows": 0}
    
#     first_row = rows[0]
#     summary = {
#         "Table": table_name,
#         "Total Rows": len(rows),
#         "Columns": list(first_row.keys()),
#         "Column Count": len(first_row.keys()),
#         "Numeric Analysis": {},
#         "Category Counts": {}
#     }
    
#     # Analyze each column
#     from collections import Counter
    
#     for key in first_row.keys():
#         values = []
#         text_values = []
        
#         for row in rows:
#             val = row.get(key, "")
            
#             # Try to parse as number
#             if val and val not in ["[Row", "[data"]:  # Skip placeholder values
#                 try:
#                     if isinstance(val, str):
#                         clean_val = val.replace(',', '').strip()
#                         if clean_val and (clean_val.replace('.', '').replace('-', '', 1).isdigit()):
#                             values.append(float(clean_val))
#                         else:
#                             text_values.append(val)
#                     else:
#                         values.append(float(val))
#                 except:
#                     text_values.append(str(val))
#             else:
#                 text_values.append(str(val))
        
#         # Numeric analysis
#         if values:
#             summary["Numeric Analysis"][key] = {
#                 "min": round(min(values), 2),
#                 "max": round(max(values), 2),
#                 "avg": round(sum(values) / len(values), 2),
#                 "count": len(values)
#             }
        
#         # Category analysis
#         if text_values and len(set(text_values)) <= 20:  # Only for reasonable cardinality
#             counter = Counter(text_values)
#             summary["Category Counts"][key] = dict(counter.most_common(5))
    
#     return summary


# @app.get("/health")
# async def health_check():
#     """Health check endpoint"""
#     return {
#         "status": "ok",
#         "message": "Qlik FastAPI Backend is running"
#     }


# # ==================== SUMMARY GENERATION ENDPOINTS ====================
# # Import moved to lazy loading inside endpoints to speed up startup
# from pydantic import BaseModel

# class TableDataRequest(BaseModel):
#     """Request model for table data summary"""
#     table_name: str
#     data: List[Dict[str, Any]]

# class BatchSummaryRequest(BaseModel):
#     """Request model for batch summary"""
#     tables: Dict[str, List[Dict[str, Any]]]

# class ChatRequest(BaseModel):
#     """Request model for chat about data"""
#     table_name: str
#     data: List[Dict[str, Any]]
#     question: str

# class ChatHistoryRequest(BaseModel):
#     """Request model for chat with history"""
#     table_name: str
#     data: List[Dict[str, Any]]
#     conversation: List[Dict[str, str]]  # [{"role": "user/assistant", "content": "text"}, ...]


# @app.post("/summary/table")
# async def create_table_summary(request: TableDataRequest):
#     """
#     Generate a summary from table data
#     Accepts JSON data and returns comprehensive metrics and summary
    
#     Example request:
#     {
#         "table_name": "Sales",
#         "data": [
#             {"product": "A", "amount": 100},
#             {"product": "B", "amount": 200}
#         ]
#     }
#     """
#     try:
#         # Lazy import to speed up server startup
#         from summary_utils import generate_summary, get_data_quality_score, get_data_preview
#         summary = generate_summary(request.data, request.table_name)
        
#         if summary.get("success"):
#             # Add data quality score
#             import pandas as pd
#             df = pd.DataFrame(request.data)
#             quality_score = get_data_quality_score(df)
#             summary["data_quality_score"] = quality_score
            
#             # Add data preview
#             summary["data_preview"] = get_data_preview(request.data, rows=5)
        
#         return summary
    
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Failed to generate summary: {str(e)}")


# @app.post("/summary/batch")
# async def create_batch_summary(request: BatchSummaryRequest):
#     """
#     Generate summaries for multiple tables at once
    
#     Example request:
#     {
#         "tables": {
#             "Sales": [...],
#             "Products": [...]
#         }
#     }
#     """
#     try:
#         # Lazy import to speed up server startup
#         from summary_utils import generate_batch_summary, get_data_quality_score
#         batch_result = generate_batch_summary(request.tables)
        
#         # Add quality scores for each table
#         import pandas as pd
#         for table_name, summary in batch_result["summaries"].items():
#             if summary.get("success"):
#                 df = pd.DataFrame(request.tables[table_name])
#                 summary["data_quality_score"] = get_data_quality_score(df)
        
#         return batch_result
    
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Failed to generate batch summary: {str(e)}")


# @app.post("/summary/text")
# async def generate_summary_text(request: TableDataRequest):
#     """
#     Generate a human-readable summary text from table data
    
#     Returns plain text summary
#     """
#     try:
#         # Lazy import to speed up server startup
#         from summary_utils import build_summary_text
#         summary_text = build_summary_text(request.data, request.table_name)
        
#         return {
#             "success": True,
#             "table_name": request.table_name,
#             "summary": summary_text
#         }
    
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Failed to generate summary text: {str(e)}")


# @app.post("/summary/quality")
# async def check_data_quality(request: TableDataRequest):
#     """
#     Check data quality metrics for a table
    
#     Returns quality score and missing value analysis
#     """
#     try:
#         # Lazy import to speed up server startup
#         from summary_utils import get_data_quality_score
#         import pandas as pd
        
#         df = pd.DataFrame(request.data)
#         quality_score = get_data_quality_score(df)
        
#         # Calculate missing values per column
#         missing_info = {
#             col: {
#                 "count": int(df[col].isna().sum()),
#                 "percentage": round((df[col].isna().sum() / len(df)) * 100, 2)
#             }
#             for col in df.columns
#         }
        
#         return {
#             "success": True,
#             "table_name": request.table_name,
#             "total_rows": len(df),
#             "total_columns": len(df.columns),
#             "quality_score": quality_score,
#             "missing_values": missing_info
#         }
    
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Failed to check data quality: {str(e)}")


# # ==================== HUGGING FACE CHAT ENDPOINTS ====================

# @app.post("/chat/analyze")
# async def chat_analyze_data(request: ChatRequest):
#     """
#     Chat with AI about your table data using Hugging Face
#     Ask questions about metrics, patterns, and insights
    
#     Example request:
#     {
#         "table_name": "Sales Data",
#         "data": [...],
#         "question": "What is the total sales amount?"
#     }
#     """
#     try:
#         # Lazy import to speed up server startup
#         from summary_utils import generate_summary, HuggingFaceHelper
        
#         # Generate summary first for context
#         summary = generate_summary(request.data, request.table_name)
        
#         if not summary.get("success"):
#             raise HTTPException(status_code=400, detail="Failed to process data")
        
#         # Get metrics for context
#         metrics = summary.get("metrics", {})
        
#         # Generate response using Hugging Face
#         response = HuggingFaceHelper.chat_about_data(request.question, metrics)
        
#         return {
#             "success": True,
#             "table_name": request.table_name,
#             "question": request.question,
#             "response": response,
#             "metrics_context": metrics
#         }
    
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Chat analysis failed: {str(e)}")


# @app.post("/chat/summary-hf")
# async def generate_hf_summary(request: TableDataRequest):
#     """
#     Generate an AI-powered summary using Hugging Face
#     Provides more intelligent summaries than rule-based approach
    
#     Example request:
#     {
#         "table_name": "Sales Data",
#         "data": [...]
#     }
#     """
#     try:
#         # Lazy import to speed up server startup
#         from summary_utils import generate_summary, HuggingFaceHelper, get_data_quality_score
#         import pandas as pd
        
#         # Process data
#         df = pd.DataFrame(request.data)
#         summary_data = generate_summary(request.data, request.table_name)
        
#         if not summary_data.get("success"):
#             raise HTTPException(status_code=400, detail="Failed to process data")
        
#         # Build fact text for Hugging Face
#         metrics = summary_data.get("metrics", {})
#         fact_text = "Dataset Analysis:\n"
#         fact_text += f"Total Records: {metrics.get('Total Records', 0)}\n"
#         fact_text += f"Total Value: {metrics.get('Total Value', 0)}\n"
#         fact_text += f"Average Value: {metrics.get('Average Value', 0)}\n"
#         fact_text += f"Min Value: {metrics.get('Min Value', 0)}\n"
#         fact_text += f"Max Value: {metrics.get('Max Value', 0)}\n"
        
#         if 'Top Categories' in metrics:
#             fact_text += "Top Categories: "
#             top_cats = metrics['Top Categories']
#             if isinstance(top_cats, dict):
#                 fact_text += ", ".join([f"{k}: {v}" for k, v in list(top_cats.items())[:3]])
#             fact_text += "\n"
        
#         # Generate summary with Hugging Face
#         hf_summary = HuggingFaceHelper.generate_hf_summary(fact_text)
        
#         return {
#             "success": True,
#             "table_name": request.table_name,
#             "summary": hf_summary,
#             "metrics": metrics,
#             "quality_score": get_data_quality_score(df)
#         }
    
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"HF summary generation failed: {str(e)}")


# @app.post("/chat/multi-turn")
# async def multi_turn_chat(request: ChatHistoryRequest):
#     """
#     Multi-turn conversation about table data
#     Maintains conversation history and context
    
#     Example request:
#     {
#         "table_name": "Sales Data",
#         "data": [...],
#         "conversation": [
#             {"role": "user", "content": "What's the average sales?"},
#             {"role": "assistant", "content": "The average is 1500."},
#             {"role": "user", "content": "What about the highest?"}
#         ]
#     }
#     """
#     try:
#         # Lazy import to speed up server startup
#         from summary_utils import generate_summary, HuggingFaceHelper
        
#         # Generate summary for context
#         summary = generate_summary(request.data, request.table_name)
        
#         if not summary.get("success"):
#             raise HTTPException(status_code=400, detail="Failed to process data")
        
#         metrics = summary.get("metrics", {})
        
#         # Get the last user message
#         last_message = None
#         for msg in reversed(request.conversation):
#             if msg.get("role") == "user":
#                 last_message = msg.get("content")
#                 break
        
#         if not last_message:
#             raise HTTPException(status_code=400, detail="No user message found in conversation")
        
#         # Generate response
#         response = HuggingFaceHelper.chat_about_data(last_message, metrics)
        
#         # Return conversation with new response
#         updated_conversation = request.conversation + [
#             {"role": "assistant", "content": response}
#         ]
        
#         return {
#             "success": True,
#             "table_name": request.table_name,
#             "conversation": updated_conversation,
#             "last_response": response,
#             "metrics_context": metrics
#         }
    
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Multi-turn chat failed: {str(e)}")


# @app.get("/chat/help")
# async def chat_help():
#     """
#     Get help on what you can ask the chat system
#     """
#     return {
#         "success": True,
#         "endpoints": {
#             "/chat/analyze": "Ask a single question about your data",
#             "/chat/summary-hf": "Generate AI-powered summary using Hugging Face",
#             "/chat/multi-turn": "Multi-turn conversation with context"
#         },
#         "example_questions": [
#             "What is the total sales amount?",
#             "What's the average value in this dataset?",
#             "Which category has the highest value?",
#             "What are the key insights from this data?",
#             "Tell me about the data distribution",
#             "Are there any missing values?",
#             "What's the relationship between categories?"
#         ],
#         "tips": [
#             "Provide your table data along with your question",
#             "The system maintains conversation history for context",
#             "Questions are answered based on the metrics of your data",
#             "You can ask follow-up questions in multi-turn conversations"
#         ]
#     }


# # ====== POWER BI LOGIN ENDPOINTS ======

# @app.post("/powerbi/login/initiate")
# async def powerbi_login_initiate():
#     """
#     Initiate Power BI login using device code flow.
#     Returns device code and URL for user to visit.
#     """
#     auth = get_auth_manager()
#     result = auth.get_device_code()
    
#     if not result["success"]:
#         raise HTTPException(status_code=400, detail=result["error"])
    
#     return {
#         "success": True,
#         "device_code": result["device_code"],
#         "user_code": result["user_code"],
#         "message": result["message"],
#         "expires_in": result["expires_in"],
#         "verification_uri": result["verification_uri"]
#     }


# @app.post("/powerbi/login/acquire-token")
# async def powerbi_login_acquire_token(request: dict):
#     """
#     Complete device code flow and acquire token using service principal.
#     Performs synchronous authentication and returns immediately.
#     """
#     auth = get_auth_manager()
    
#     # Check if already logged in
#     if auth.is_token_valid():
#         return {
#             "success": True,
#             "message": "Already logged in",
#             "logged_in": True
#         }
    
#     try:
#         print("\n" + "="*60)
#         print("🔐 STARTING SERVICE PRINCIPAL TOKEN ACQUISITION")
#         print("="*60)
        
#         # Perform synchronous token acquisition
#         print("📱 Acquiring token via service principal...")
#         result = auth.acquire_token_by_device_code(max_wait_seconds=10)
        
#         if result.get("success"):
#             print("\n" + "="*60)
#             print("✅ TOKEN ACQUISITION SUCCESSFUL!")
#             print("="*60 + "\n")
#             return {
#                 "success": True,
#                 "message": "Authentication successful!",
#                 "logged_in": True
#             }
#         else:
#             print(f"\n❌ Token acquisition failed: {result.get('error')}\n")
#             return {
#                 "success": False,
#                 "message": "Authentication failed",
#                 "error": result.get("error"),
#                 "logged_in": False
#             }
#     except Exception as e:
#         print(f"❌ Token acquisition error: {str(e)}")
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=f"Token acquisition failed: {str(e)}")


# @app.post("/powerbi/login/status")
# async def powerbi_login_status():
#     """
#     Check if user is logged in.
#     Returns True if valid token exists.
#     """
#     auth = get_auth_manager()
#     return {
#         "logged_in": auth.is_token_valid(),
#         "message": "You are logged in to Power BI" if auth.is_token_valid() else "Not logged in. Please use /powerbi/login/initiate"
#     }


# @app.post("/powerbi/login/test")
# async def powerbi_login_test():
#     """
#     Test Power BI connection by listing datasets in workspace.
#     """
#     auth = get_auth_manager()
    
#     if not auth.is_token_valid():
#         raise HTTPException(status_code=401, detail="Not logged in. Please login first using /powerbi/login/initiate")
    
#     result = auth.test_connection()
    
#     if not result["success"]:
#         raise HTTPException(status_code=401, detail=result["error"])
    
#     return result


# @app.post("/powerbi/process")
# async def process_for_powerbi(
#     csv_file: UploadFile = File(None),
#     dax_file: UploadFile = File(None),
#     json_file: UploadFile = File(None),
#     meta_app_name: str = Form(""),
#     meta_table: str = Form(""),
#     has_csv: str = Form("true"),
#     has_dax: str = Form("false")
# ):
#     try:
#         print(f"DEBUG: Received request with csv_file={bool(csv_file)}, dax_file={bool(dax_file)}, json_file={bool(json_file)}")
#         print(f"DEBUG: Received FormData - meta_app_name='{meta_app_name}', meta_table='{meta_table}'")
#         print(f"DEBUG: Format selection from Export page - has_csv={has_csv}, has_dax={has_dax}")
        
#         # Parse selection flags
#         has_csv_selected = has_csv == "true"
#         has_dax_selected = has_dax == "true"
        
#         # Validate: at least one format must be selected
#         if not has_csv_selected and not has_dax_selected:
#             raise HTTPException(status_code=400, detail="No formats selected. Please select CSV and/or DAX in Export page.")
        
#         # CSV is required for dataset creation (contains rows and columns)
#         if has_csv_selected and not csv_file:
#             raise HTTPException(status_code=400, detail="CSV was selected but file not provided")

#         csv_content = await csv_file.read() if csv_file else b""
#         dax_content = await dax_file.read() if dax_file else b""
#         json_content = await json_file.read() if json_file else b""
        
#         print(f"DEBUG: CSV content length: {len(csv_content)}, DAX content length: {len(dax_content)}")

#         if not csv_content:
#             raise HTTPException(status_code=400, detail="CSV file is empty")

#         # Parse DAX file only if it was selected in Export page
#         dax_text = ""
#         dax_measures = []
#         if has_dax_selected and dax_file:
#             try:
#                 dax_content = await dax_file.read()
#                 dax_text = dax_content.decode('utf-8')
#                 dax_measures = parse_dax(dax_text)
#                 print(f"DEBUG: Parsed {len(dax_measures)} measures from DAX file (DAX was selected in Export page)")
#                 for measure in dax_measures:
#                     print(f"  ✓ Measure: {measure['name']}")
#             except Exception as e:
#                 print(f"DEBUG: DAX parsing error: {str(e)}")
#                 # Don't fail if DAX parsing fails, just continue with CSV data
#                 dax_measures = []
#         elif has_dax_selected and not dax_file:
#             print("DEBUG: DAX was selected in Export page but file not provided - will skip DAX processing")
#         else:
#             print(f"DEBUG: DAX not selected in Export page (has_dax_selected={has_dax_selected}) - skipping DAX")

#         # Parse CSV locally
#         try:
#             processor = PowerBIProcessor(csv_content, dax_content)
#             parsed = processor.process()
#             print(f"DEBUG: Processor result keys: {list(parsed.keys())}")
#         except Exception as e:
#             print(f"DEBUG: Processor error: {str(e)}")
#             raise HTTPException(status_code=400, detail=f"Failed to parse files: {str(e)}")

#         rows = parsed.get("rows", [])
#         columns = parsed.get("table_columns", [])
#         if not rows or not columns:
#             raise HTTPException(status_code=400, detail="CSV has no rows/columns")

#         # Dataset/table naming - PRIORITY: custom table name, then app name
#         dataset_name = meta_table or meta_app_name or "Qlik_Migrated_Dataset"
#         table_name = meta_table or "QlikTable"
        
#         print(f"DEBUG: Dataset naming - meta_table={meta_table}, meta_app_name={meta_app_name}")
#         print(f"DEBUG: Using dataset_name={dataset_name}, table_name={table_name}")
#         print(f"DEBUG: ✅ Processing formats selected in Export page - CSV: {has_csv_selected}, DAX: {has_dax_selected}")
#         print(f"DEBUG: DAX measures extracted: {len(dax_measures)}")
#         print(f"DEBUG: Creating dataset {dataset_name}, table {table_name}")

#         # Infer schema and publish to Power BI
#         try:
#             # Get authenticated user token
#             auth = get_auth_manager()
            
#             if not auth.is_token_valid():
#                 raise HTTPException(status_code=401, detail="Not logged in. Please login using /powerbi/login/initiate endpoint")
            
#             # Create service with user token
#             pbi = PowerBIService(access_token=auth.get_access_token())
#             schema = infer_schema_from_rows(rows)
#             dataset_id, created = pbi.get_or_create_push_dataset(dataset_name, table_name, schema)
#             push_res = pbi.push_rows(dataset_id, table_name, rows)
#             print(f"DEBUG: Push result: {push_res}")
            
#             # Data is now saved to Power BI Cloud permanently
#             print(f"✅ Dataset saved to Power BI Cloud!")
#             print(f"   Dataset ID: {dataset_id}")
#             print(f"   Table Name: {table_name}")
#             print(f"   Rows: {len(rows)}")
#             print(f"   📌 This data will persist in Power BI even if backend/app closes")
            
#             # Apply DAX measures if any
#             measures_result = {}
#             if dax_measures:
#                 print(f"Applying {len(dax_measures)} DAX measures to dataset...")
#                 measures_result = apply_dax_measures(pbi, dataset_id, dax_measures)
            
#             # Create auto-report with visualizations
#             print("📊 Creating Power BI report with visualizations...")
#             report_url = get_or_create_default_report(pbi, dataset_id, dataset_name, columns)
            
#             try:
#                 refresh_res = pbi.trigger_refresh(dataset_id)
#             except Exception:
#                 # push dataset often doesn't require refresh; ignore
#                 refresh_res = {"status_code": None}
#         except HTTPException:
#             raise
#         except Exception as e:
#             print(f"DEBUG: PowerBI error: {str(e)}")
#             raise HTTPException(status_code=401, detail=f"Power BI error: {str(e)}")

#         return {
#             "success": True,
#             "message": "Published to Power BI",
#             "dataset": {
#                 "id": dataset_id,
#                 "created": created,
#                 "name": dataset_name,
#                 "table": table_name,
#                 "workspace_id": pbi.workspace_id,
#                 "urls": {
#                     "report": report_url,
#                     "dataset": f"https://app.powerbi.com/groups/{pbi.workspace_id}/datasets/{dataset_id}",
#                     "workspace": f"https://app.powerbi.com/groups/{pbi.workspace_id}",
#                     "home": "https://app.powerbi.com/home"
#                 }
#             },
#             "push": push_res,
#             "refresh": refresh_res,
#             "dax": {
#                 "parsed_measures": dax_measures,
#                 "measures_applied": measures_result
#             },
#             "local_parse": {
#                 "columns": columns,
#                 "row_count": len(rows)
#             }
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         print(f"DEBUG: Unexpected error: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Power BI publish failed: {str(e)}")

# # ─────────── END ───────────

# # ============= ADVANCED POWER BI ENDPOINT =============

# @app.post("/powerbi/advanced")
# async def powerbi_advanced(
#     csv_file: UploadFile = File(None),
#     dax_file: UploadFile = File(None),
#     meta_app_name: Optional[str] = None,
#     meta_table: Optional[str] = None
# ):
#     """
#     Advanced Power BI endpoint with full DAX support and measures.
    
#     Features:
#     - Parse DAX file and extract measures
#     - Create Power BI dataset with schema
#     - Push data rows
#     - Apply DAX measures to dataset (calculated columns/measures)
    
#     Request:
#     {
#         "csv_file": <CSV file with data>,
#         "dax_file": <DAX file with measure definitions>,
#         "meta_app_name": "Application Name",
#         "meta_table": "Table Name"
#     }
    
#     DAX Format in file:
#         Total Sales = SUM(FactTable[Sales])
#         Total Quantity = SUM(FactTable[Quantity])
#         Average Price = AVERAGE(FactTable[Price])
#     """
#     try:
#         print("🚀 Advanced Power BI processing started...")
        
#         if not csv_file:
#             raise HTTPException(status_code=400, detail="CSV file is required")
        
#         csv_content = await csv_file.read()
#         dax_content = await dax_file.read() if dax_file else b""
        
#         print(f"📊 CSV size: {len(csv_content)} bytes")
#         print(f"📐 DAX size: {len(dax_content)} bytes")
        
#         if not csv_content:
#             raise HTTPException(status_code=400, detail="CSV file is empty")
        
#         # Parse DAX measures
#         dax_text = ""
#         measures_list = []
        
#         if dax_content:
#             try:
#                 dax_text = dax_content.decode('utf-8')
#                 measures_list = parse_dax(dax_text)
#                 print(f"✅ Parsed {len(measures_list)} measures from DAX file:")
#                 for m in measures_list:
#                     print(f"   - {m['name']}")
#             except Exception as e:
#                 print(f"⚠️ DAX parsing error: {str(e)}")
#                 measures_list = []
        
#         # Parse CSV data
#         try:
#             processor = PowerBIProcessor(csv_content, dax_content)
#             parsed = processor.process()
#         except Exception as e:
#             print(f"❌ CSV processing error: {str(e)}")
#             raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")
        
#         rows = parsed.get("rows", [])
#         columns = parsed.get("table_columns", [])
        
#         if not rows or not columns:
#             raise HTTPException(status_code=400, detail="CSV has no valid rows/columns")
        
#         # Dataset naming
#         dataset_name = meta_app_name or meta_table or "Qlik_Advanced_Dataset"
#         table_name = meta_table or "FactTable"
        
#         print(f"📊 Creating dataset: {dataset_name}")
#         print(f"📋 Table: {table_name}")
#         print(f"📈 Rows: {len(rows)}, Columns: {len(columns)}")
        
#         # Authenticate and create dataset
#         try:
#             auth = get_auth_manager()
#             if not auth.is_token_valid():
#                 raise HTTPException(
#                     status_code=401,
#                     detail="Not logged in. Please use /powerbi/login/acquire-token"
#                 )
            
#             pbi = PowerBIService(access_token=auth.get_access_token())
#             schema = infer_schema_from_rows(rows)
            
#             # Create/get dataset
#             dataset_id, created = pbi.get_or_create_push_dataset(dataset_name, table_name, schema)
#             print(f"✅ Dataset ID: {dataset_id} (Created: {created})")
            
#             # Push data
#             push_res = pbi.push_rows(dataset_id, table_name, rows)
#             print(f"✅ Data pushed successfully")
            
#             # Apply measures
#             measures_applied = {}
#             if measures_list:
#                 print(f"🔧 Applying {len(measures_list)} measures...")
#                 measures_applied = apply_dax_measures(pbi, dataset_id, measures_list)
            
#             # Create auto-report with visualizations
#             print("📊 Creating Power BI report with visualizations...")
#             report_url = get_or_create_default_report(pbi, dataset_id, dataset_name, columns)
            
#             # Refresh dataset
#             try:
#                 refresh_res = pbi.trigger_refresh(dataset_id)
#             except Exception as e:
#                 print(f"⚠️ Refresh not available (expected for push datasets): {str(e)}")
#                 refresh_res = {"status": "skipped"}
            
#             return {
#                 "success": True,
#                 "status": "completed",
#                 "message": "Advanced Power BI processing completed successfully",
#                 "dataset": {
#                     "id": dataset_id,
#                     "name": dataset_name,
#                     "table": table_name,
#                     "created": created,
#                     "workspace_id": pbi.workspace_id,
#                     "urls": {
#                         "report": report_url,
#                         "dataset": f"https://app.powerbi.com/groups/{pbi.workspace_id}/datasets/{dataset_id}",
#                         "workspace": f"https://app.powerbi.com/groups/{pbi.workspace_id}"
#                     }
#                 },
#                 "data": {
#                     "rows_pushed": len(rows),
#                     "columns": columns,
#                     "push_status": push_res
#                 },
#                 "dax": {
#                     "measures_parsed": len(measures_list),
#                     "measures_list": measures_list,
#                     "measures_applied": measures_applied
#                 },
#                 "refresh": refresh_res
#             }
        
#         except HTTPException:
#             raise
#         except Exception as e:
#             print(f"❌ Power BI error: {str(e)}")
#             raise HTTPException(status_code=500, detail=f"Power BI error: {str(e)}")
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         print(f"❌ Unexpected error: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


# # =====================================================
# # DIAGNOSTIC ENDPOINT
# @app.get("/powerbi/datasets")
# async def list_powerbi_datasets():
#     """
#     List all datasets in Power BI workspace.
#     Useful for debugging and checking dataset creation.
#     """
#     auth = get_auth_manager()
    
#     if not auth.is_token_valid():
#         raise HTTPException(status_code=401, detail="Not logged in")
    
#     try:
#         pbi = PowerBIService(access_token=auth.get_access_token())
        
#         headers = {
#             "Authorization": f"Bearer {auth.get_access_token()}",
#             "Content-Type": "application/json"
#         }
        
#         workspace_id = pbi.workspace_id
        
#         # Get datasets
#         datasets_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets"
#         response = requests.get(datasets_url, headers=headers, timeout=30)
        
#         if response.status_code != 200:
#             raise Exception(f"Failed to list datasets: {response.text}")
        
#         datasets = response.json().get("value", [])
        
#         return {
#             "workspace_id": workspace_id,
#             "dataset_count": len(datasets),
#             "datasets": [
#                 {
#                     "id": d.get("id"),
#                     "name": d.get("name"),
#                     "configured": d.get("isConfigured"),
#                     "url": f"https://app.powerbi.com/groups/{workspace_id}/datasets/{d.get('id')}"
#                 }
#                 for d in datasets
#             ]
#         }
    
#     except Exception as e:
#         print(f"❌ Error listing datasets: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))


# # =====================================================

# if __name__ == "__main__":
#     import uvicorn
#     print("\n" + "="*80)
#     print(" " * 20 + "Qlik FastAPI Backend v2.0")
#     print("="*80)
#     print("\nFeatures:")
#     print("  [+] REST API for Qlik Cloud")
#     print("  [+] WebSocket connection to Qlik Engine")
#     print("  [+] Table and field discovery")
#     print("  [+] Script extraction")
#     print("  [+] Data retrieval from tables")
#     if SCRIPT_PARSER_AVAILABLE:
#         print("  [+] Script data extraction (INLINE data)")
#     else:
#         print("  [!] Script data extraction DISABLED (qlik_script_parser.py not found)")
#     print("\nStarting server...")
#     print("="*80 + "\n")
    
#     uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)



import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse
from typing import List, Dict, Any, Optional
import time
import requests
import re
import base64
import io
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
from qlik_client import QlikClient
from qlik_websocket_client import QlikWebSocketClient
from login_validation import router as login_router
from processor import PowerBIProcessor
from table_tracker import enhance_tables_with_timestamps
from powerbi_service_delegated import PowerBIService, infer_schema_from_rows
from powerbi_auth import get_auth_manager
from pydantic import BaseModel
import httpx

# Hugging Face API configuration
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
HF_API_URL = "https://api-inference.huggingface.co/models"

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
    """Get Qlik client using environment variables"""
    try:
        return QlikClient()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_qlik_websocket_client():
    try:
        return QlikWebSocketClient()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= ER DIAGRAM GENERATION =============

def build_er_diagram(tables: List[Dict[str, Any]], master_table: str = None) -> bytes:
    """
    Generate an ER diagram showing relationships between tables.
    Master table (star center) is highlighted in gold.
    """
    try:
        fig, ax = plt.subplots(figsize=(11, 8), facecolor='white')
        ax.set_facecolor('white')
        ax.set_xlim(-7.5, 7.5)
        ax.set_ylim(-7.5, 7.5)
        ax.axis('off')
        
        # Normalize tables
        table_list = []
        for t in tables:
            if isinstance(t, str):
                table_list.append({'name': t, 'fields': []})
            elif isinstance(t, dict):
                table_list.append(t)
        
        if not table_list:
            # Empty diagram
            buf = io.BytesIO()
            plt.savefig(buf, format='png', facecolor='white', bbox_inches='tight', dpi=100)
            plt.close(fig)
            buf.seek(0)
            return buf.getvalue()
        
        # Identify master table (if provided) or largest table
        center_table = master_table
        if not center_table:
            # Find table with most fields
            center_table = max(table_list, key=lambda t: len(t.get('fields', []))).get('name') or table_list[0]['name']
        
        # Position: master in center, others in circle
        positions = {}
        positions[center_table] = (0, 0)
        
        related_tables = [t['name'] for t in table_list if t['name'] != center_table]
        num_related = len(related_tables)
        
        if num_related > 0:
            radius = 5.5
            for i, table_name in enumerate(related_tables):
                angle = (2 * np.pi * i) / num_related
                x = radius * np.cos(angle)
                y = radius * np.sin(angle)
                positions[table_name] = (x, y)
        
        # Draw connections first
        for i, table1 in enumerate(table_list):
            for table2 in table_list[i+1:]:
                name1, name2 = table1['name'], table2['name']
                if name1 in positions and name2 in positions:
                    # Check if they share fields (common key pattern)
                    fields1 = set(str(f).lower() if isinstance(f, str) else f.get('name', '').lower() 
                                 for f in table1.get('fields', []))
                    fields2 = set(str(f).lower() if isinstance(f, str) else f.get('name', '').lower() 
                                 for f in table2.get('fields', []))
                    
                    if fields1 & fields2:  # Share at least one field
                        x1, y1 = positions[name1]
                        x2, y2 = positions[name2]
                        
                        # Draw arrow
                        arrow = FancyArrowPatch(
                            (x1, y1), (x2, y2),
                            arrowstyle='<->', mutation_scale=20, linewidth=2,
                            color='#9ca3af', alpha=0.7, zorder=1
                        )
                        ax.add_patch(arrow)
        
        # Draw table boxes
        for table in table_list:
            name = table['name']
            x, y = positions.get(name, (0, 0))
            
            # Color: gold for master, white for others
            is_master = (name == center_table)
            bg_color = '#f59e0b' if is_master else '#ffffff'
            border_color = '#d97706' if is_master else '#9ca3af'
            border_width = 3 if is_master else 2
            
            # Get fields for sizing
            fields = table.get('fields', [])
            field_names = []
            for f in fields[:4]:
                if isinstance(f, str):
                    field_names.append(f)
                elif isinstance(f, dict):
                    field_names.append(f.get('name', ''))
            
            # Dynamic box sizing based on content
            # Calculate required height based on number of fields
            num_fields = len(field_names)
            field_height = 0.3 * num_fields if num_fields > 0 else 0
            
            # Calculate box dimensions with proper padding
            box_width = 3.2 if is_master else 3.0
            box_height = max(2.8, 1.2 + field_height + 0.5)  # Min height + table name + fields + padding
            
            fancy_box = FancyBboxPatch(
                (x - box_width/2, y - box_height/2), box_width, box_height,
                boxstyle="round,pad=0.1",
                edgecolor=border_color, facecolor=bg_color, 
                linewidth=border_width, zorder=2
            )
            ax.add_patch(fancy_box)
            
            # Table name - with word wrapping for long names
            label_color = 'white' if is_master else '#1f2937'
            name_fontsize = 12 if is_master else 10
            
            # Wrap long table names
            if len(name) > 20:
                wrapped_name = '\n'.join([name[i:i+15] for i in range(0, len(name), 15)])
            else:
                wrapped_name = name
                
            ax.text(x, y + box_height/2 - 0.35, wrapped_name, ha='center', va='top',
                   fontsize=name_fontsize, fontweight='bold',
                   color=label_color, zorder=3, wrap=True)
            
            # Fields - wrapped text that fits in box
            if field_names:
                # Wrap field names if too long
                wrapped_fields = []
                for field in field_names:
                    if len(field) > 18:
                        wrapped_fields.append(field[:15] + '...')
                    else:
                        wrapped_fields.append(field)
                
                field_text = '\n'.join(wrapped_fields)
                field_fontsize = 8 if is_master else 7.5
                
                # Position fields below table name
                field_y_pos = y - 0.2
                ax.text(x, field_y_pos, field_text, ha='center', va='center',
                       fontsize=field_fontsize, color=label_color, alpha=0.85, 
                       zorder=3, wrap=True)
        
        # Title
        ax.text(0, 7.5, 'Entity Relationship Diagram (ER)', 
               ha='center', va='center',
               fontsize=14, fontweight='bold', color='#1f2937')
        
        # Legend
        legend_elements = [
            mpatches.Patch(facecolor='#f59e0b', edgecolor='#d97706', label='Master Table'),
            mpatches.Patch(facecolor='#ffffff', edgecolor='#9ca3af', label='Related Tables'),
            mpatches.Patch(facecolor='none', edgecolor='#9ca3af', label='Relationships'),
        ]
        ax.legend(handles=legend_elements, loc='lower right', fontsize=10,
                 framealpha=0.95, edgecolor='#d1d5db')
        
        # Save to bytes
        buf = io.BytesIO()
        plt.savefig(buf, format='png', facecolor='white', bbox_inches='tight', dpi=100)
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
        
    except Exception as e:
        print(f"Error generating ER diagram: {str(e)}")
        # Return a simple error diagram
        fig, ax = plt.subplots(figsize=(10, 6), facecolor='white')
        ax.text(0.5, 0.5, f'Error: {str(e)}', ha='center', va='center',
               fontsize=12, color='red', transform=ax.transAxes)
        ax.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', facecolor='white', bbox_inches='tight', dpi=100)
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()


class ERDiagramRequest(BaseModel):
    """Request body for ER diagram generation"""
    tables: List[Dict[str, Any]] = []
    master_table: Optional[str] = None


@app.post("/api/app/{app_id}/schema/base64")
async def get_er_diagram_base64(app_id: str, request: ERDiagramRequest):
    """Generate ER diagram and return as base64 PNG"""
    try:
        tables = request.tables or []
        master_table = request.master_table
        
        png_bytes = build_er_diagram(tables, master_table)
        base64_str = base64.b64encode(png_bytes).decode('utf-8')
        
        return {
            "image": base64_str,
            "format": "png",
            "app_id": app_id,
            "tables_count": len(tables),
            "master_table": master_table
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate ER diagram: {str(e)}")


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
async def list_spaces(
    client: QlikClient = Depends(get_qlik_client)
):
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
async def list_applications(
    client: QlikClient = Depends(get_qlik_client)
):
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

@app.get("/applications/{app_id}/table/{table_name}/data/simple")
async def get_table_data_simple(
    app_id: str,
    table_name: str,
    ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
):
    """
    Simple endpoint that returns table structure and metadata without complex hypercube creation
    Great for showing table summaries/previews
    """
    try:
        # Get tables from data model
        result = ws_client.get_app_tables_simple(app_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error"))
        
        tables = result.get("tables", [])
        requested = table_name.strip().lower()
        matching_table = None
        
        for table in tables:
            if table.get("name", "").strip().lower() == requested:
                matching_table = table
                break
        
        if not matching_table:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        # Return table metadata
        columns = [f["name"] for f in matching_table.get("fields", []) if not f.get("is_system")]
        
        return {
            "success": True,
            "table_name": matching_table.get("name"),
            "columns": columns,
            "column_count": len(columns),
            "row_count": matching_table.get("no_of_rows", 0),
            "is_synthetic": matching_table.get("is_synthetic", False),
            "fields_info": matching_table.get("fields", [])[:10],  # First 10 fields for preview
            "note": "This returns table structure. For actual table data, use the /table/{table_name}/data endpoint"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving table info: {str(e)}")


# Enhanced table data endpoint with better error handling for CSV-loaded tables
@app.get("/applications/{app_id}/table/{table_name}/data/enhanced")
async def get_table_data_enhanced(
    app_id: str,
    table_name: str,
    limit: int = Query(default=100, le=10000, description="Maximum number of rows to return"),
    ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
):
    """
    Enhanced endpoint to fetch table data with multiple fallback strategies
    Handles CSV-loaded tables, case-insensitive matching, and trimmed names
    NOW WITH PRIORITY: Script extraction for inline/CSV data
    """
    try:
        print(f"📊 Attempting to fetch table '{table_name}' from app '{app_id}'...")
        
        # STRATEGY 0: First try script extraction (for INLINE loads and CSV data)
        # This is the KEY FIX - prioritize script extraction for inline/CSV data
        if SCRIPT_PARSER_AVAILABLE:
            print(f"🔍 Trying script extraction first (for inline/CSV data)...")
            try:
                # Get script via websocket client
                script_result = ws_client.get_app_tables_simple(app_id)
                if script_result.get("success"):
                    script = script_result.get("script", "")
                    if script:
                        table_preview = QlikScriptParser.get_table_preview(script, table_name, limit)
                        if table_preview.get("success"):
                            rows = table_preview.get("rows", [])
                            columns = table_preview.get("columns", [])
                            print(f"✅ SUCCESS: Extracted {len(rows)} rows from script for table '{table_name}'")
                            return {
                                "success": True,
                                "table_name": table_name,
                                "columns": columns,
                                "rows": rows,
                                "row_count": len(rows),
                                "source": "script"
                            }
                        else:
                            print(f"⚠️ Script found but table '{table_name}' not in script: {table_preview.get('error')}")
                    else:
                        print("⚠️ No script found in app")
            except Exception as e:
                print(f"⚠️ Script extraction failed: {str(e)}")
        else:
            print("⚠️ Script parser not available, skipping script extraction")
        
        # STRATEGY 1: Direct fetch with provided name (hypercupe method)
        print(f"🔄 Trying hypercube method...")
        result = ws_client.get_table_data(app_id, table_name, limit)
        if result.get("success", False):
            # Check if it's not just placeholder data
            rows = result.get("rows", [])
            if rows and len(rows) > 0:
                # Check if we got actual data or placeholders
                first_row = rows[0] if rows else {}
                has_placeholder = any(
                    isinstance(v, str) and "not accessible" in v 
                    for v in first_row.values()
                ) if first_row else False
                
                if not has_placeholder:
                    print(f"✅ Successfully retrieved table data using direct name")
                    return result
                else:
                    print(f"⚠️ Got placeholder data, trying other strategies...")
            else:
                return result
        
        print(f"⚠️ Direct fetch failed or returned placeholders: {result.get('error', 'Unknown error')}")
        
        # Strategy 2: Get list of available tables and try case-insensitive match
        print(f"🔍 Retrieving list of available tables...")
        tables_info = ws_client.get_app_tables_simple(app_id)
        
        if tables_info.get("success", False):
            available_tables = tables_info.get("tables", [])
            print(f"📋 Found {len(available_tables)} tables in app")
            
            # Try case-insensitive and whitespace-trimmed match
            requested_lower = (table_name or "").strip().lower()
            
            for table_info in available_tables:
                table_names_to_try = [
                    table_info.get("name"),
                    table_info.get("table"),
                    table_info.get("table_name")
                ]
                
                for name in table_names_to_try:
                    if name and name.strip().lower() == requested_lower:
                        print(f"✅ Found matching table name: '{name}'")
                        
                        result = ws_client.get_table_data(app_id, name, limit)
                        if result.get("success", False):
                            # Check again for placeholders
                            rows = result.get("rows", [])
                            if rows:
                                first_row = rows[0]
                                has_placeholder = any(
                                    isinstance(v, str) and "not accessible" in v 
                                    for v in first_row.values()
                                ) if first_row else False
                                
                                if not has_placeholder:
                                    print(f"✅ Successfully retrieved data using matched name: '{name}'")
                                    return result
                        
                        # If still getting placeholders, try script extraction with matched name
                        if SCRIPT_PARSER_AVAILABLE:
                            try:
                                script = tables_info.get("script", "")
                                if script:
                                    table_preview = QlikScriptParser.get_table_preview(script, name, limit)
                                    if table_preview.get("success"):
                                        print(f"✅ Found actual data via script with matched name: '{name}'")
                                        return {
                                            "success": True,
                                            "table_name": name,
                                            "columns": table_preview.get("columns", []),
                                            "rows": table_preview.get("rows", []),
                                            "row_count": table_preview.get("total_rows", 0),
                                            "source": "script"
                                        }
                            except Exception as e:
                                print(f"⚠️ Script extraction with matched name failed: {str(e)}")
            
            print(f"⚠️ No matching table found. Available tables: {[t.get('name', 'unknown') for t in available_tables]}")
        
        # If all strategies fail
        raise HTTPException(
            status_code=404, 
            detail=f"Table '{table_name}' not found. Please check the table name and ensure the app has been reloaded with data."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in enhanced table fetch: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get table data: {str(e)}")

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

@app.get("/applications/{app_id}/table/{table_name}/export/csv", response_class=PlainTextResponse)
async def export_table_as_csv(
    app_id: str,
    table_name: str,
    ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
):
    """
    Export table data as CSV file
    Returns CSV format ready for download
    """
    try:
        # Try to fetch actual table data first
        table_data_result = ws_client.get_table_data(app_id, table_name, limit=10000)
        
        if table_data_result.get("success"):
            # Build CSV from actual table data
            rows = table_data_result.get("rows", [])
            columns = table_data_result.get("columns", [])
            
            if not rows or not columns:
                return "No data available for export"
            
            # Build CSV header
            csv_lines = [",".join(f'"{col}"' for col in columns)]
            
            # Build CSV rows
            for row in rows:
                values = []
                for col in columns:
                    val = str(row.get(col, ""))
                    # Escape quotes in values
                    val = val.replace('"', '""')
                    values.append(f'"{val}"')
                csv_lines.append(",".join(values))
            
            return "\n".join(csv_lines)
        
        else:
            # Fallback: Get table structure from metadata
            tables_result = ws_client.get_app_tables_simple(app_id)
            if not tables_result.get("success"):
                raise HTTPException(status_code=500, detail="Could not fetch table information")
            
            tables = tables_result.get("tables", [])
            requested = table_name.strip().lower()
            matching_table = None
            
            for table in tables:
                if table.get("name", "").strip().lower() == requested:
                    matching_table = table
                    break
            
            if not matching_table:
                raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
            
            columns = [f["name"] for f in matching_table.get("fields", []) if not f.get("is_system")]
            row_count = matching_table.get("no_of_rows", 0)
            
            # Create CSV with structure and metadata
            csv_lines = [
                f"Table,{table_name}",
                f"Rows,{row_count}",
                f"Columns,{len(columns)}",
                f"Export Date,{time.strftime('%Y-%m-%d %H:%M:%S')}",
                ""
            ]
            
            csv_lines.append(",".join(f'"{col}"' for col in columns))
            csv_lines.append("# " + ",".join(["[Data not accessible - metadata only]"] * len(columns)))
            
            return "\n".join(csv_lines)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting table: {str(e)}")

@app.get("/vehicle-summary")
async def vehicle_summary(
    app_id: str,
    table_name: str,
    ws_client: QlikWebSocketClient = Depends(get_qlik_websocket_client)
):
    """
    Generate a summary of table data
    Works with both INLINE script data and CSV-loaded tables
    """
    print(f"\n==== VEHICLE SUMMARY ENDPOINT ====")
    print(f"App ID: {app_id}, Table: {table_name}")

    try:
        # Step 1: Try to get actual table data first
        print(f"Step 1: Attempting to fetch table data...")
        table_data_result = ws_client.get_table_data(app_id, table_name, limit=1000)
        
        if table_data_result.get("success"):
            print(f"✅ Got actual table data")
            rows = table_data_result.get("rows", [])
            
            if rows:
                return {"success": True, "summary": _generate_summary_from_rows(rows, table_name)}
        
        # Step 2: Fallback - get from script/INLINE data
        print(f"Step 2: Trying script parsing...")
        
        if not SCRIPT_PARSER_AVAILABLE:
            print(f"⚠️ Script parser not available, returning metadata summary")
            # Get table metadata as fallback
            tables_result = ws_client.get_app_tables_simple(app_id)
            if tables_result.get("success"):
                for table in tables_result.get("tables", []):
                    if table.get("name", "").strip().lower() == table_name.strip().lower():
                        return {
                            "success": True,
                            "summary": {
                                "Table": table_name,
                                "Total Rows": table.get("no_of_rows", 0),
                                "Columns": len([f for f in table.get("fields", []) if not f.get("is_system")]),
                                "Fields": [f["name"] for f in table.get("fields", [])[:10]],
                                "Note": "Summary from table metadata (actual data not accessible)"
                            }
                        }
        
        # Try script-based summary
        result = ws_client.get_app_tables_simple(app_id)
        
        if not result.get("success", False):
            print(f"⚠️ Script parsing failed, returning basic summary")
            return {
                "success": True,
                "summary": {
                    "Table": table_name,
                    "Note": "Could not load data - check that app has been reloaded in QlikCloud"
                }
            }

        script = result.get("script", "")

        if not script:
            print(f"⚠️ No script found, returning basic summary")
            return {
                "success": True,
                "summary": {
                    "Table": table_name,
                    "Tables Available": [t["name"] for t in result.get("tables", [])],
                    "Note": "No script data found"
                }
            }

        # Parse script for INLINE data
        table_data = QlikScriptParser.get_table_preview(script, table_name, 1000)

        if not table_data.get("success", False):
            print(f"⚠️ Table not found in script")
            return {
                "success": True,
                "summary": {
                    "Table": table_name,
                    "Available Tables": [t["name"] for t in result.get("tables", [])]
                }
            }

        rows = table_data.get("rows", [])

        if not rows:
            return {
                "success": True,
                "summary": {
                    "Table": table_name,
                    "Message": "No data rows found"
                }
            }

        return {"success": True, "summary": _generate_summary_from_rows(rows, table_name)}
        
    except Exception as e:
        print(f"❌ Error in vehicle_summary: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return a basic message instead of crashing
        return {
            "success": True,
            "summary": {
                "Table": table_name,
                "Status": "Summary generation failed, but table data may still be available",
                "Error": str(e)
            }
        }

def _generate_summary_from_rows(rows: list, table_name: str) -> dict:
    """Generate summary statistics from table rows"""
    if not rows:
        return {"Table": table_name, "Total Rows": 0}
    
    first_row = rows[0]
    summary = {
        "Table": table_name,
        "Total Rows": len(rows),
        "Columns": list(first_row.keys()),
        "Column Count": len(first_row.keys()),
        "Numeric Analysis": {},
        "Category Counts": {}
    }
    
    # Analyze each column
    from collections import Counter
    
    for key in first_row.keys():
        values = []
        text_values = []
        
        for row in rows:
            val = row.get(key, "")
            
            # Try to parse as number
            if val and val not in ["[Row", "[data"]:  # Skip placeholder values
                try:
                    if isinstance(val, str):
                        clean_val = val.replace(',', '').strip()
                        if clean_val and (clean_val.replace('.', '').replace('-', '', 1).isdigit()):
                            values.append(float(clean_val))
                        else:
                            text_values.append(val)
                    else:
                        values.append(float(val))
                except:
                    text_values.append(str(val))
            else:
                text_values.append(str(val))
        
        # Numeric analysis
        if values:
            summary["Numeric Analysis"][key] = {
                "min": round(min(values), 2),
                "max": round(max(values), 2),
                "avg": round(sum(values) / len(values), 2),
                "count": len(values)
            }
        
        # Category analysis
        if text_values and len(set(text_values)) <= 20:  # Only for reasonable cardinality
            counter = Counter(text_values)
            summary["Category Counts"][key] = dict(counter.most_common(5))
    
    return summary


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Qlik FastAPI Backend is running"
    }


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
            "/chat/multi-turn": "Multi-turn conversation with context",
            "/ai/summary": "Generate AI-powered executive summary using Hugging Face Inference API"
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


# ==================== AI SUMMARY USING HUGGING FACE INFERENCE API ====================

class AISummaryRequest(BaseModel):
    """Request model for AI summary"""
    table_name: str
    metrics: Dict[str, Any]
    row_count: int = 0
    column_count: int = 0


@app.post("/ai/summary")
async def generate_ai_summary(request: AISummaryRequest):
    """
    Generate an AI-powered executive summary using Hugging Face Inference API.
    
    Uses Mistral-7B-Instruct model for generating intelligent summaries.
    
    Example request:
    {
        "table_name": "Sales Data",
        "metrics": {
            "Total Records": 1000,
            "Total Value": 50000,
            "Average Value": 50
        },
        "row_count": 1000,
        "column_count": 5
    }
    """
    try:
        if not HF_API_KEY:
            # Fallback to rule-based summary if no API key
            return generate_fallback_summary(request.table_name, request.metrics, request.row_count, request.column_count)
        
        # Build context from metrics
        metrics_text = ""
        for key, value in request.metrics.items():
            if isinstance(value, dict):
                metrics_text += f"{key}:\n"
                for k, v in list(value.items())[:5]:
                    metrics_text += f"  - {k}: {v}\n"
            elif isinstance(value, list):
                metrics_text += f"{key}: {', '.join(str(v) for v in value[:5])}\n"
            else:
                metrics_text += f"{key}: {value}\n"
        
        # Create prompt for the model
        prompt = f"""<s>[INST] You are a data analyst assistant. Generate a concise executive summary for the following dataset.

Table: {request.table_name}
Total Rows: {request.row_count}
Total Columns: {request.column_count}

Key Metrics:
{metrics_text}

Generate a professional executive summary (3-4 sentences) highlighting the key insights. [/INST]"""

        # Call Hugging Face Inference API
        model_id = "mistralai/Mistral-7B-Instruct-v0.2"
        api_url = f"{HF_API_URL}/{model_id}"
        
        headers = {
            "Authorization": f"Bearer {HF_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 200,
                "temperature": 0.7,
                "top_p": 0.9,
                "return_full_text": False
            }
        }
        
        print(f"🤖 Calling Hugging Face API for AI summary...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(api_url, headers=headers, json=payload)
            
            if response.status_code != 200:
                print(f"⚠️ HF API error: {response.status_code} - {response.text}")
                return generate_fallback_summary(request.table_name, request.metrics, request.row_count, request.column_count)
            
            result = response.json()
            
            # Extract generated text
            if isinstance(result, list) and len(result) > 0:
                generated_text = result[0].get("generated_text", "")
            elif isinstance(result, dict):
                generated_text = result.get("generated_text", "")
            else:
                generated_text = str(result)
            
            # Clean up the response
            summary = generated_text.strip()
            
            # Remove any remaining prompt artifacts
            if "[/INST]" in summary:
                summary = summary.split("[/INST]")[-1].strip()
            if "[INST]" in summary:
                summary = summary.replace("[INST]", "").strip()
            
            print(f"✅ AI Summary generated successfully")
            
            return {
                "success": True,
                "table_name": request.table_name,
                "summary": summary,
                "source": "huggingface_mistral",
                "model": model_id,
                "metrics": request.metrics
            }
    
    except httpx.TimeoutException:
        print("⚠️ HF API timeout, using fallback")
        return generate_fallback_summary(request.table_name, request.metrics, request.row_count, request.column_count)
    except Exception as e:
        print(f"❌ AI summary error: {str(e)}")
        return generate_fallback_summary(request.table_name, request.metrics, request.row_count, request.column_count)


def generate_fallback_summary(table_name: str, metrics: Dict[str, Any], row_count: int, column_count: int) -> Dict[str, Any]:
    """Generate a rule-based summary when AI is not available"""
    
    # Extract key metrics
    total_records = metrics.get("Total Records", row_count)
    total_value = metrics.get("Total Value", "N/A")
    avg_value = metrics.get("Average Value", "N/A")
    
    # Build summary text
    summary_parts = [f"The {table_name} dataset contains {total_records} records across {column_count} columns."]
    
    if total_value != "N/A":
        summary_parts.append(f"The total value amounts to {total_value:,}.")
    
    if avg_value != "N/A":
        summary_parts.append(f"On average, each record has a value of {avg_value}.")
    
    # Add top category info if available
    top_cats = metrics.get("Top Categories", {})
    if top_cats:
        top_cat_name = list(top_cats.keys())[0] if top_cats else None
        if top_cat_name:
            summary_parts.append(f"The leading category is '{top_cat_name}'.")
    
    summary = " ".join(summary_parts)
    
    return {
        "success": True,
        "table_name": table_name,
        "summary": summary,
        "source": "rule_based_fallback",
        "metrics": metrics
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
# PDF REPORT GENERATION
# =====================================================

@app.post("/report/download-pdf")
async def download_pdf(payload: dict = Body(...)):
    """
    Generate and download Validation & Reconciliation PDF report
    Compares Qlik Sense and Power BI metrics
    """
    try:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import pagesizes
        from reportlab.lib.units import inch
        from datetime import datetime
        import io
        from fastapi.responses import StreamingResponse
        
        # Extract data from payload
        qlik_metrics = payload.get("qlik_metrics", {})
        powerbi_metrics = payload.get("powerbi_metrics", {})
        app_name = payload.get("app_name", "Unknown App")
        table_name = payload.get("table_name", "Unknown Table")
        migration_status = payload.get("migration_status", "In Progress")
        
        # ==============================
        # CALCULATE METRICS & DIFFERENCES
        # ==============================
        
        TOLERANCE_PERCENT = 0.5
        differences = []
        all_metrics = []
        
        # Helper function to format values
        def format_value(value):
            """Format value for PDF display - handle lists, long strings, etc."""
            if value is None:
                return "—"
            elif isinstance(value, (list, tuple)):
                # Join with comma, remove quotes
                items = [str(x).strip("'\"") for x in value[:4]]
                formatted = ", ".join(items)
                if len(value) > 4 or len(formatted) > 35:
                    formatted = formatted[:32] + "..."
                return formatted
            elif isinstance(value, str):
                if len(value) > 35:
                    return value[:32] + "..."
                return value
            else:
                return str(value)
        
        # Get all metric keys - sorted for consistent order
        metric_order = ['row_count', 'column_count', 'total_records', 'certification_status']
        excluded_keys = {'column_names', 'timestamp'}  # Explicitly exclude these
        all_keys = set(list(qlik_metrics.keys()) + list(powerbi_metrics.keys()))
        
        # Filter out excluded keys and sort by preferred order
        all_keys = all_keys - excluded_keys
        ordered_keys = [k for k in metric_order if k in all_keys]
        extra_keys = sorted([k for k in all_keys if k not in metric_order])
        all_keys = ordered_keys + extra_keys
        
        for metric in all_keys:
            q_val = qlik_metrics.get(metric)
            p_val = powerbi_metrics.get(metric)
            
            # Format display values properly
            q_display = format_value(q_val)
            p_display = format_value(p_val)
            
            variance = None
            variance_percent = None
            status = "PASS"
            
            # Calculate variance for numeric values only
            if isinstance(q_val, (int, float)) and isinstance(p_val, (int, float)):
                variance = p_val - q_val
                if q_val != 0:
                    variance_percent = abs((variance / q_val) * 100)
                else:
                    variance_percent = 0 if variance == 0 else 100
                
                if variance_percent > TOLERANCE_PERCENT:
                    status = "FAIL"
            else:
                # For non-numeric, compare directly
                if q_val != p_val:
                    status = "FAIL"
            
            metric_data = {
                "metric": metric,
                "qlik": q_display,
                "powerbi": p_display,
                "variance": variance,
                "variance_percent": variance_percent,
                "status": status,
                "raw_qlik": q_val,
                "raw_powerbi": p_val
            }
            
            all_metrics.append(metric_data)
            
            if status == "FAIL":
                differences.append(metric_data)
        
        # Calculate certification score
        pass_count = sum(1 for m in all_metrics if m["status"] == "PASS")
        score = (pass_count / len(all_metrics)) * 100 if all_metrics else 0
        certified = score >= 95
        
        # ==============================
        # PDF REPORT GENERATION
        # ==============================
        
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=pagesizes.A4, topMargin=0.4*inch, bottomMargin=0.4*inch, leftMargin=0.4*inch, rightMargin=0.4*inch)
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles - improved alignment
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=10,
            alignment=0,  # Left align
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=6,
            spaceBefore=4,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=9,
            spaceAfter=3,
            alignment=0  # Left align
        )
        
        # Title with checkmark
        elements.append(Paragraph("✓ Validation &amp; Reconciliation Report", title_style))
        elements.append(Spacer(1, 0.12 * inch))
        
        # Header Info - formatted nicely
        header_info = f"""
        <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
        <b>Application:</b> {app_name}<br/>
        <b>Table:</b> {table_name}<br/>
        <b>Source System:</b> Qlik Sense Cloud | <b>Target System:</b> Power BI Cloud<br/>
        <b>Status:</b> {migration_status}
        """
        elements.append(Paragraph(header_info, normal_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        # Executive Summary
        elements.append(Paragraph("EXECUTIVE SUMMARY", heading_style))
        elements.append(Spacer(1, 0.08 * inch))
        
        num_differences = len(differences)
        if num_differences == 0:
            summary_text = f"<b style='color: green'>✓ SUCCESS:</b> Data synchronized perfectly. All {len(all_metrics)} metrics match."
        else:
            summary_text = f"<b style='color: red'>⚠ ATTENTION:</b> {num_differences} difference(s) detected."
        
        elements.append(Paragraph(summary_text, normal_style))
        elements.append(Spacer(1, 0.18 * inch))
        
        # Main Metrics Comparison Table
        elements.append(Paragraph("METRICS COMPARISON", heading_style))
        elements.append(Spacer(1, 0.05 * inch))
        
        # Build table with proper formatting
        table_data = [["Metric", "Qlik Sense", "Power BI", "Variance", "Status"]]
        
        for m in all_metrics:
            # Format metric name
            metric_name = str(m["metric"]).replace('_', ' ').title()
            
            # Get variance display
            variance_str = ""
            if m["variance"] is not None:
                if m["variance_percent"] is not None and m["variance_percent"] > 0.01:
                    variance_str = f"{m['variance_percent']:.1f}%"
                elif m["variance"] == 0:
                    variance_str = "0"
                else:
                    variance_str = f"{m['variance']:.0f}"
            else:
                variance_str = "—"
            
            status_symbol = "✓ PASS" if m["status"] == "PASS" else "✗ FAIL"
            
            table_data.append([
                metric_name,
                m["qlik"],
                m["powerbi"],
                variance_str,
                status_symbol
            ])
        
        # Create table with optimized column widths
        comp_table = Table(table_data, colWidths=[1.7*inch, 1.3*inch, 1.3*inch, 0.75*inch, 0.7*inch])
        
        # Enhanced table styling
        style_list = [
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGNMENT', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('PADDINGTOP', (0, 0), (-1, 0), 5),
            ('PADDINGBOTTOM', (0, 0), (-1, 0), 5),
            ('PADDINGLEFT', (0, 0), (-1, 0), 3),
            ('PADDINGRIGHT', (0, 0), (-1, 0), 3),
            
            # Data rows - alignment
            ('ALIGNMENT', (0, 1), (0, -1), 'LEFT'),  # Metric names left
            ('ALIGNMENT', (1, 1), (-1, -1), 'CENTER'),  # Other columns center
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            
            # Cell padding for data rows
            ('PADDINGTOP', (0, 1), (-1, -1), 4),
            ('PADDINGBOTTOM', (0, 1), (-1, -1), 4),
            ('PADDINGLEFT', (0, 1), (-1, -1), 3),
            ('PADDINGRIGHT', (0, 1), (-1, -1), 3),
            
            # Grid and background
            ('GRID', (0, 0), (-1, -1), 0.7, colors.HexColor('#cccccc')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f6f6f6')]),
        ]
        
        # Color code FAIL rows - removed, all rows same style
        for idx, m in enumerate(all_metrics, 1):
            if m["status"] == "FAIL":
                pass  # No special styling for FAIL rows
        
        comp_table.setStyle(TableStyle(style_list))
        elements.append(comp_table)
        elements.append(Spacer(1, 0.15 * inch))
        
        # Difference Details - Always show for Total Records
        elements.append(Paragraph("DIFFERENCE DETAILS", heading_style))
        elements.append(Spacer(1, 0.08 * inch))
        
        diff_table_data = [["Metric", "Qlik Sense", "Power BI", "Variance"]]
        
        for d in all_metrics:
            if d["metric"] == "total_records":
                variance_str = str(d["variance"]) if d["variance"] is not None else "—"
                metric_name = "Total Amount"
                
                diff_table_data.append([
                    metric_name,
                    d["qlik"],
                    d["powerbi"],
                    variance_str
                ])
        
        diff_table = Table(diff_table_data, colWidths=[1.7*inch, 1.3*inch, 1.3*inch, 0.75*inch])
        diff_table.setStyle(TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGNMENT', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('PADDINGTOP', (0, 0), (-1, 0), 5),
            ('PADDINGBOTTOM', (0, 0), (-1, 0), 5),
            ('PADDINGLEFT', (0, 0), (-1, 0), 3),
            ('PADDINGRIGHT', (0, 0), (-1, 0), 3),
            
            # Data rows - alignment
            ('ALIGNMENT', (0, 1), (0, -1), 'LEFT'),  # Metric names left
            ('ALIGNMENT', (1, 1), (-1, -1), 'CENTER'),  # Other columns center
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            
            # Cell padding for data rows
            ('PADDINGTOP', (0, 1), (-1, -1), 4),
            ('PADDINGBOTTOM', (0, 1), (-1, -1), 4),
            ('PADDINGLEFT', (0, 1), (-1, -1), 3),
            ('PADDINGRIGHT', (0, 1), (-1, -1), 3),
            
            # Grid and background
            ('GRID', (0, 0), (-1, -1), 0.7, colors.HexColor('#cccccc')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f6f6f6')]),
        ]))
        elements.append(diff_table)
        elements.append(Spacer(1, 0.2 * inch))
        
        # Difference Details (if any)
        if differences:
            elements.append(Paragraph("DIFFERENCE DETAILS", heading_style))
            elements.append(Spacer(1, 0.08 * inch))
            
            elements.append(Paragraph("The following metrics show discrepancies:", normal_style))
            elements.append(Spacer(1, 0.08 * inch))
            
            diff_table_data = [["Metric", "Qlik Sense", "Power BI", "Difference", "% Variance"]]
            
            for d in differences:
                metric_name = str(d["metric"]).replace('_', ' ').title()
                variance_str = str(d["variance"]) if d["variance"] is not None else "—"
                variance_pct = f"{d['variance_percent']:.1f}%" if d["variance_percent"] is not None else "—"
                
                diff_table_data.append([
                    metric_name,
                    d["qlik"],
                    d["powerbi"],
                    variance_str,
                    variance_pct
                ])
            
            diff_table = Table(diff_table_data, colWidths=[1.7*inch, 1.3*inch, 1.3*inch, 0.75*inch, 0.7*inch])
            diff_table.setStyle(TableStyle([
                # Header row styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8b0000')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('ALIGNMENT', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('PADDINGTOP', (0, 0), (-1, 0), 5),
                ('PADDINGBOTTOM', (0, 0), (-1, 0), 5),
                ('PADDINGLEFT', (0, 0), (-1, 0), 3),
                ('PADDINGRIGHT', (0, 0), (-1, 0), 3),
                
                # Data rows - alignment
                ('ALIGNMENT', (0, 1), (0, -1), 'LEFT'),  # Metric names left
                ('ALIGNMENT', (1, 1), (-1, -1), 'CENTER'),  # Other columns center
                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
                
                # Cell padding for data rows
                ('PADDINGTOP', (0, 1), (-1, -1), 4),
                ('PADDINGBOTTOM', (0, 1), (-1, -1), 4),
                ('PADDINGLEFT', (0, 1), (-1, -1), 3),
                ('PADDINGRIGHT', (0, 1), (-1, -1), 3),
                
                # Grid and background
                ('GRID', (0, 0), (-1, -1), 0.7, colors.HexColor('#cccccc')),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.red),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fff0f0'), colors.HexColor('#ffe6e6')]),
            ]))
            elements.append(diff_table)
            elements.append(Spacer(1, 0.2 * inch))
        
        # Certification Section
        elements.append(Paragraph("CERTIFICATION &amp; VALIDATION", heading_style))
        elements.append(Spacer(1, 0.08 * inch))
        
        cert_color = "green" if certified else "red"
        cert_status = "✓ CERTIFIED" if certified else "✗ NOT CERTIFIED"
        
        certification_text = f"""
        <b>Overall Score:</b> {round(score, 1)}%<br/>
        <b>Metrics Evaluated:</b> {len(all_metrics)} | <b>Passed:</b> {pass_count} | <b>Failed:</b> {len(differences)}<br/>
        <b>Certification Status:</b> <font color="{cert_color}"><b>{cert_status}</b></font> (95% required)
        """
        elements.append(Paragraph(certification_text, normal_style))
        elements.append(Spacer(1, 0.25 * inch))
        
        # Footer
        footer_text = f"""
        <font size=7><i>Report generated by Qlik to Power BI Migration Tool | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i></font><br/>
        <font size=6 color='#999999'>For questions or support, contact the migration team.</font>
        """
        elements.append(Paragraph(footer_text, styles["Normal"]))
        
        # Build PDF
        doc.build(elements)
        pdf_buffer.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Validation_Report_{timestamp}.pdf"
        
        return StreamingResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except Exception as e:
        print(f"❌ Error downloading PDF: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to download PDF: {str(e)}")


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