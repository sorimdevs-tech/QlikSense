# """
# BULK RELATIONSHIP API ENDPOINTS
# Extract relationships from ALL Qlik apps and publish to Power BI in bulk
# """

# from fastapi import APIRouter, HTTPException, BackgroundTasks
# from pydantic import BaseModel
# from typing import List, Dict, Optional, Any
# import logging
# from datetime import datetime
# from bulk_relationship_extractor import BulkRelationshipExtractor

# logger = logging.getLogger(__name__)

# router = APIRouter(prefix="/api/bulk", tags=["bulk-relationships"])

# # ============================================================================
# # PYDANTIC MODELS
# # ============================================================================

# class BulkExtractionRequest(BaseModel):
#     """Request to extract relationships from all apps"""
#     appIds: Optional[List[str]] = None  # If None, extract from ALL apps
#     includeCSVData: bool = True
#     dataSource: str = "inline"  # inline, csv, sql

# class BulkPublishRequest(BaseModel):
#     """Request to publish all apps to Power BI"""
#     extractionResult: Dict[str, Any]  # Result from bulk extraction
#     accessToken: str
#     workspaceId: Optional[str] = None
#     publishMode: str = "xmla_semantic"  # xmla_semantic or push_dataset

# class RelationshipSummary(BaseModel):
#     """Summary of relationships in an app"""
#     appId: str
#     appName: str
#     tableCount: int
#     relationshipCount: int
#     relatedTables: List[str]

# # ============================================================================
# # ENDPOINT 1: SCAN ALL APPS FOR RELATIONSHIPS
# # ============================================================================

# @router.post("/extract-all-relationships")
# async def extract_all_relationships(request: BulkExtractionRequest):
#     """
#     Scan ALL Qlik apps and extract ALL relationships automatically
    
#     This is the main entry point - no need to click individual tables.
#     Returns complete relationship graph for all apps ready for Power BI
#     """
    
#     try:
#         logger.info("🔗 Starting bulk relationship extraction...")
        
#         # Step 1: Get all apps from Qlik
#         all_apps = await _fetch_all_qlik_apps(request.appIds)
        
#         logger.info(f"📊 Found {len(all_apps)} apps to process")
        
#         # Step 2: Get tables for each app
#         apps_with_tables = {}
        
#         for app in all_apps:
#             app_id = app["id"]
#             app_name = app["name"]
            
#             logger.info(f"  Loading tables for: {app_name}")
            
#             tables = await _fetch_app_tables(app_id)
            
#             apps_with_tables[app_id] = {
#                 "appName": app_name,
#                 "appId": app_id,
#                 "tables": tables
#             }
        
#         # Step 3: Extract relationships using bulk extractor
#         logger.info("🔗 Extracting relationships from all apps...")
        
#         extractor = BulkRelationshipExtractor(apps_with_tables)
#         extraction_result = extractor.extract_all_relationships()
        
#         # Step 4: Optionally generate CSV data
#         if request.includeCSVData:
#             logger.info("💾 Generating CSV data for all tables...")
            
#             for app_id, app_result in extraction_result["apps"].items():
#                 app_tables = apps_with_tables[app_id]["tables"]
#                 csv_payloads = extractor._generate_all_csv_data(app_tables)
                
#                 extraction_result["apps"][app_id]["csvPayloads"] = csv_payloads
#                 extraction_result["apps"][app_id]["csvSize"] = sum(len(csv) for csv in csv_payloads.values())
        
#         # Add metadata
#         extraction_result["extractionRequest"] = {
#             "timestamp": datetime.now().isoformat(),
#             "appIds": request.appIds or "all",
#             "includeCSVData": request.includeCSVData,
#             "dataSource": request.dataSource
#         }
        
#         logger.info("✅ Bulk extraction complete")
        
#         return {
#             "success": True,
#             "message": f"Extracted relationships from {len(all_apps)} apps",
#             "extractionResult": extraction_result
#         }
    
#     except Exception as e:
#         logger.error(f"❌ Bulk extraction failed: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# # ============================================================================
# # ENDPOINT 2: GET RELATIONSHIP SUMMARY FOR ALL APPS
# # ============================================================================

# @router.get("/relationship-summary")
# async def get_relationship_summary():
#     """
#     Get quick summary of relationships in all apps
#     Useful for dashboard showing migration readiness
#     """
    
#     try:
#         logger.info("📊 Generating relationship summary...")
        
#         # Get all apps
#         all_apps = await _fetch_all_qlik_apps()
        
#         apps_with_tables = {}
#         for app in all_apps:
#             tables = await _fetch_app_tables(app["id"])
#             apps_with_tables[app["id"]] = {
#                 "appName": app["name"],
#                 "tables": tables
#             }
        
#         # Extract relationships
#         extractor = BulkRelationshipExtractor(apps_with_tables)
#         extraction_result = extractor.extract_all_relationships()
        
#         # Build summary
#         summaries = []
        
#         for app_id, app_result in extraction_result["apps"].items():
#             summaries.append({
#                 "appId": app_id,
#                 "appName": app_result["appName"],
#                 "tableCount": app_result["tableCount"],
#                 "relationshipCount": len(app_result["relationships"]),
#                 "relatedTables": app_result["relatedTables"],
#                 "readyForPowerBI": len(app_result["relationships"]) > 0,
#                 "detectionMethods": list(set(
#                     rel.get("detectionMethod", "UNKNOWN") 
#                     for rel in app_result["relationships"]
#                 ))
#             })
        
#         return {
#             "success": True,
#             "timestamp": datetime.now().isoformat(),
#             "totalApps": len(summaries),
#             "totalRelationships": extraction_result["stats"]["totalRelationships"],
#             "appsWithRelationships": extraction_result["stats"]["appsWithRelationships"],
#             "appSummaries": summaries
#         }
    
#     except Exception as e:
#         logger.error(f"Failed to generate summary: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# # ============================================================================
# # ENDPOINT 3: PUBLISH ALL APPS TO POWER BI
# # ============================================================================

# @router.post("/publish-all-to-powerbi")
# async def publish_all_to_powerbi(request: BulkPublishRequest, background_tasks: BackgroundTasks):
#     """
#     Publish ALL extracted apps to Power BI at once
    
#     Uses extraction result from extract-all-relationships endpoint
#     Each app becomes a separate dataset in Power BI with relationships
#     """
    
#     try:
#         logger.info("📤 Starting bulk publish to Power BI...")
        
#         extraction_result = request.extractionResult
#         apps = extraction_result.get("apps", {})
        
#         logger.info(f"📦 Publishing {len(apps)} apps to Power BI...")
        
#         # Validate access token
#         if not request.accessToken:
#             raise HTTPException(status_code=400, detail="Access token required")
        
#         # Publish each app in background
#         publish_tasks = []
        
#         for app_id, app_result in apps.items():
#             app_name = app_result.get("appName", app_id)
            
#             # Prepare publish payload
#             publish_payload = {
#                 "appId": app_id,
#                 "appName": app_name,
#                 "datasetName": f"Qlik_{app_name.replace(' ', '_')}",
#                 "tables": app_result.get("csvTables", []),
#                 "relationships": app_result.get("relationships", []),
#                 "csvPayloads": app_result.get("csvPayloads", {}),
#                 "dataSource": extraction_result.get("extractionRequest", {}).get("dataSource", "inline"),
#                 "accessToken": request.accessToken,
#                 "workspaceId": request.workspaceId,
#                 "publishMode": request.publishMode
#             }
            
#             # Queue for background processing
#             background_tasks.add_task(
#                 _publish_app_to_powerbi,
#                 publish_payload
#             )
            
#             publish_tasks.append({
#                 "appId": app_id,
#                 "appName": app_name,
#                 "status": "queued"
#             })
        
#         return {
#             "success": True,
#             "message": f"Queued {len(apps)} apps for publishing to Power BI",
#             "appsQueued": len(apps),
#             "publishTasks": publish_tasks,
#             "note": "Publishing happens in background. Check status with /api/bulk/publish-status endpoint"
#         }
    
#     except Exception as e:
#         logger.error(f"❌ Bulk publish failed: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# # ============================================================================
# # ENDPOINT 4: GET PUBLISH STATUS
# # ============================================================================

# @router.get("/publish-status")
# async def get_publish_status():
#     """
#     Get status of bulk publish operation
#     Returns status for each app being published
#     """
    
#     # Note: In production, this would track actual publish jobs
#     # For now, return mock status
    
#     return {
#         "success": True,
#         "bulkPublishStatus": {
#             "totalApps": 3,
#             "completed": 2,
#             "inProgress": 1,
#             "failed": 0,
#             "appStatus": [
#                 {
#                     "appId": "app-sales-001",
#                     "appName": "Sales Analytics",
#                     "status": "completed",
#                     "datasetId": "4b48e046-8b41-49d5-be5f-f28a97ce8e1b",
#                     "tablesDeployed": 6,
#                     "relationshipsApplied": 5,
#                     "datasetUrl": "https://app.powerbi.com/groups/me/datasets/4b48e046.../details"
#                 },
#                 {
#                     "appId": "app-customer-002",
#                     "appName": "Customer Insights",
#                     "status": "completed",
#                     "datasetId": "7c92f15d-1234-5678-abcd-ef1234567890",
#                     "tablesDeployed": 3,
#                     "relationshipsApplied": 2,
#                     "datasetUrl": "https://app.powerbi.com/groups/me/datasets/7c92f15d.../details"
#                 },
#                 {
#                     "appId": "app-inventory-003",
#                     "appName": "Inventory Management",
#                     "status": "inProgress",
#                     "progress": 75,
#                     "currentStep": "Deploying relationships"
#                 }
#             ]
#         }
#     }

# # ============================================================================
# # ENDPOINT 5: EXPORT RELATIONSHIPS AS JSON/CSV
# # ============================================================================

# @router.post("/export-relationships")
# async def export_relationships(extractionResult: Dict[str, Any]):
#     """
#     Export all extracted relationships as JSON or CSV for review
#     Useful for validation and audit
#     """
    
#     try:
#         apps = extractionResult.get("apps", {})
        
#         # Build export data
#         export_data = {
#             "exportDate": datetime.now().isoformat(),
#             "totalApps": len(apps),
#             "relationships": []
#         }
        
#         for app_id, app_result in apps.items():
#             for rel in app_result.get("relationships", []):
#                 export_data["relationships"].append({
#                     "appId": app_id,
#                     "appName": app_result.get("appName"),
#                     "fromTable": rel.get("fromTable"),
#                     "fromColumn": rel.get("fromColumn"),
#                     "toTable": rel.get("toTable"),
#                     "toColumn": rel.get("toColumn"),
#                     "cardinality": rel.get("cardinality"),
#                     "detectionMethod": rel.get("detectionMethod"),
#                     "confidence": rel.get("confidence")
#                 })
        
#         return {
#             "success": True,
#             "exportData": export_data,
#             "totalRelationships": len(export_data["relationships"])
#         }
    
#     except Exception as e:
#         logger.error(f"Export failed: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# # ============================================================================
# # HELPER FUNCTIONS (Mock implementations)
# # ============================================================================

# async def _fetch_all_qlik_apps(app_ids: Optional[List[str]] = None) -> List[Dict]:
#     """Fetch all Qlik apps (or specific ones if app_ids provided)"""
    
#     # Mock data - replace with actual Qlik API calls
#     all_apps = [
#         {
#             "id": "app-sales-001",
#             "name": "Sales Analytics"
#         },
#         {
#             "id": "app-customer-002",
#             "name": "Customer Insights"
#         },
#         {
#             "id": "app-inventory-003",
#             "name": "Inventory Management"
#         }
#     ]
    
#     if app_ids:
#         return [app for app in all_apps if app["id"] in app_ids]
    
#     return all_apps

# async def _fetch_app_tables(app_id: str) -> List[Dict]:
#     """Fetch tables for a specific app"""
    
#     # Mock data - replace with actual Qlik API calls
#     app_tables_map = {
#         "app-sales-001": [
#             {
#                 "name": "Sales",
#                 "fields": [
#                     {"name": "SalesID", "type": "integer"},
#                     {"name": "CustomerID", "type": "integer"},
#                     {"name": "ProductID", "type": "integer"},
#                     {"name": "RegionID", "type": "integer"},
#                     {"name": "Amount", "type": "numeric"},
#                     {"name": "OrderDate", "type": "date"}
#                 ]
#             },
#             {
#                 "name": "Customer",
#                 "fields": [
#                     {"name": "CustomerID", "type": "integer"},
#                     {"name": "Name", "type": "text"},
#                     {"name": "CountryID", "type": "integer"}
#                 ]
#             },
#             {
#                 "name": "Product",
#                 "fields": [
#                     {"name": "ProductID", "type": "integer"},
#                     {"name": "ProductName", "type": "text"},
#                     {"name": "CategoryID", "type": "integer"}
#                 ]
#             },
#             {
#                 "name": "Region",
#                 "fields": [
#                     {"name": "RegionID", "type": "integer"},
#                     {"name": "RegionName", "type": "text"}
#                 ]
#             },
#             {
#                 "name": "Country",
#                 "fields": [
#                     {"name": "CountryID", "type": "integer"},
#                     {"name": "CountryName", "type": "text"}
#                 ]
#             },
#             {
#                 "name": "Category",
#                 "fields": [
#                     {"name": "CategoryID", "type": "integer"},
#                     {"name": "CategoryName", "type": "text"}
#                 ]
#             }
#         ],
#         "app-customer-002": [
#             {
#                 "name": "Customer",
#                 "fields": [
#                     {"name": "CustomerID", "type": "integer"},
#                     {"name": "Name", "type": "text"},
#                     {"name": "SegmentID", "type": "integer"}
#                 ]
#             },
#             {
#                 "name": "Segment",
#                 "fields": [
#                     {"name": "SegmentID", "type": "integer"},
#                     {"name": "SegmentName", "type": "text"}
#                 ]
#             },
#             {
#                 "name": "Orders",
#                 "fields": [
#                     {"name": "OrderID", "type": "integer"},
#                     {"name": "CustomerID", "type": "integer"},
#                     {"name": "OrderAmount", "type": "numeric"}
#                 ]
#             }
#         ],
#         "app-inventory-003": [
#             {
#                 "name": "Stock",
#                 "fields": [
#                     {"name": "StockID", "type": "integer"},
#                     {"name": "ProductID", "type": "integer"},
#                     {"name": "WarehouseID", "type": "integer"},
#                     {"name": "Quantity", "type": "integer"}
#                 ]
#             },
#             {
#                 "name": "Product",
#                 "fields": [
#                     {"name": "ProductID", "type": "integer"},
#                     {"name": "ProductName", "type": "text"}
#                 ]
#             },
#             {
#                 "name": "Warehouse",
#                 "fields": [
#                     {"name": "WarehouseID", "type": "integer"},
#                     {"name": "WarehouseName", "type": "text"}
#                 ]
#             }
#         ]
#     }
    
#     return app_tables_map.get(app_id, [])

# async def _publish_app_to_powerbi(publish_payload: Dict[str, Any]):
#     """Publish a single app to Power BI (background task)"""
    
#     try:
#         logger.info(f"Publishing app: {publish_payload['appName']}")
        
#         # Simulate publishing
#         import asyncio
#         await asyncio.sleep(2)  # Simulate work
        
#         logger.info(f"✅ Successfully published: {publish_payload['appName']}")
    
#     except Exception as e:
#         logger.error(f"❌ Failed to publish {publish_payload['appName']}: {str(e)}")