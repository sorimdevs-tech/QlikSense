# # qlik_websocket_client.py - IMPROVED VERSION
# import websocket
# import json
# import ssl
# import jwt
# import os
# import time
# from typing import Dict, Any, List, Optional
# from dotenv import load_dotenv

# load_dotenv()

# class QlikWebSocketClient:
#     def __init__(self):
#         self.api_key = os.getenv('QLIK_API_KEY')
#         self.tenant_url = os.getenv('QLIK_TENANT_URL')
        
#         if not self.api_key or not self.tenant_url:
#             raise ValueError("QLIK_API_KEY and QLIK_TENANT_URL must be set in environment variables")
        
#         # Decode JWT to get user info
#         try:
#             decoded = jwt.decode(self.api_key, options={"verify_signature": False})
#             self.user_id = decoded.get('sub', '')
#             self.user_directory = "QLIK"
#         except Exception as e:
#             print(f"Warning: Could not decode JWT: {e}")
#             self.user_id = ""
#             self.user_directory = "QLIK"
        
#         self.ws = None
#         self.connected = False
#         self.app_handle = None
#         self.request_id = 1
        
#     def _get_next_id(self) -> int:
#         """Get next request ID"""
#         current_id = self.request_id
#         self.request_id += 1
#         return current_id
    
#     def connect_to_app(self, app_id: str) -> bool:
#         """Connect to a specific app via WebSocket"""
#         try:
#             # Clean up tenant URL
#             tenant_host = self.tenant_url.replace('https://', '').replace('http://', '')
#             ws_url = f"wss://{tenant_host}/app/{app_id}"
            
#             print(f"\n{'='*60}")
#             print(f"Connecting to Qlik app via WebSocket")
#             print(f"URL: {ws_url}")
#             print(f"{'='*60}")
            
#             # Create WebSocket connection
#             self.ws = websocket.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE})
            
#             # Connect with headers
#             headers = {
#                 "Authorization": f"Bearer {self.api_key}",
#             }
            
#             if self.user_id:
#                 headers["X-Qlik-User"] = f"UserDirectory={self.user_directory};UserId={self.user_id}"
            
#             self.ws.connect(ws_url, header=headers)
#             self.connected = True
#             print("✓ WebSocket connected successfully")
            
#             # Open the app
#             return self._open_app(app_id)
            
#         except Exception as e:
#             print(f"✗ Connection error: {str(e)}")
#             import traceback
#             traceback.print_exc()
#             return False
    
#     def _open_app(self, app_id: str) -> bool:
#         """Open the app and get its handle"""
#         try:
#             # Open app message
#             open_msg = {
#                 "jsonrpc": "2.0",
#                 "id": self._get_next_id(),
#                 "method": "OpenDoc",
#                 "handle": -1,
#                 "params": {
#                     "qDocName": app_id,
#                     "qNoData": False
#                 }
#             }
            
#             print(f"\nSending OpenDoc request...")
#             self.ws.send(json.dumps(open_msg))
            
#             response = self.ws.recv()
#             response_data = json.loads(response)
            
#             print(f"OpenDoc response: {json.dumps(response_data, indent=2)}")
            
#             if 'result' in response_data and 'qReturn' in response_data['result']:
#                 self.app_handle = response_data['result']['qReturn']['qHandle']
#                 print(f"✓ App opened successfully with handle: {self.app_handle}")
#                 return True
#             else:
#                 print(f"✗ Failed to open app. Response: {response_data}")
#                 return False
                
#         except Exception as e:
#             print(f"✗ Error opening app: {str(e)}")
#             import traceback
#             traceback.print_exc()
#             return False
    
#     def send_request(self, method: str, params: Dict = None, handle: int = None) -> Dict[str, Any]:
#         """Send a request to Qlik Engine"""
#         if not self.connected:
#             raise ConnectionError("Not connected to Qlik")
        
#         if handle is None:
#             handle = self.app_handle
        
#         request_id = self._get_next_id()
#         request = {
#             "jsonrpc": "2.0",
#             "id": request_id,
#             "method": method,
#             "handle": handle,
#             "params": params or {}
#         }
        
#         print(f"\nSending request: {method}")
#         self.ws.send(json.dumps(request))
        
#         response = self.ws.recv()
        
#         try:
#             return json.loads(response)
#         except:
#             return {"error": "Failed to parse response", "raw_response": response}
    
#     def get_app_tables_simple(self, app_id: str) -> Dict[str, Any]:
#         """Get comprehensive table information from app"""
#         try:
#             # Connect to app
#             if not self.connect_to_app(app_id):
#                 return {"success": False, "error": "Failed to connect to app"}
            
#             # Method 1: Get data model metadata
#             print("\n" + "="*60)
#             print("Getting data model information...")
#             print("="*60)
            
#             tables_info = self._get_tables_from_data_model()
            
#             # Method 2: Get all fields
#             print("\nGetting field list...")
#             fields_info = self._get_all_fields()
            
#             # Method 3: Get app layout for metadata
#             print("\nGetting app layout...")
#             layout_info = self._get_app_layout()
            
#             # Method 4: Get script
#             print("\nGetting app script...")
#             script_info = self._get_app_script()
            
#             # Method 5: Get sheets
#             print("\nGetting sheets...")
#             sheets_info = self._get_sheets()
            
#             # Close connection
#             self.close()
            
#             # Combine all information
#             result = {
#                 "success": True,
#                 "app_id": app_id,
#                 "app_title": layout_info.get("title", "Unknown"),
#                 "tables": tables_info.get("tables", []),
#                 "all_fields": fields_info.get("fields", []),
#                 "field_count": len(fields_info.get("fields", [])),
#                 "script": script_info.get("script", ""),
#                 "script_tables": script_info.get("tables", []),
#                 "sheets": sheets_info.get("sheets", []),
#                 "data_model": tables_info.get("raw_data"),
#                 "summary": {
#                     "table_count": len(tables_info.get("tables", [])),
#                     "total_fields": len(fields_info.get("fields", [])),
#                     "sheet_count": len(sheets_info.get("sheets", [])),
#                     "has_script": len(script_info.get("script", "")) > 0,
#                     "script_table_count": len(script_info.get("tables", []))
#                 }
#             }
            
#             return result
            
#         except Exception as e:
#             self.close()
#             print(f"\n✗ Error: {str(e)}")
#             import traceback
#             traceback.print_exc()
#             return {"success": False, "error": str(e)}
    
#     def _get_tables_from_data_model(self) -> Dict[str, Any]:
#         """Get tables from data model"""
#         try:
#             # Get table list
#             response = self.send_request("GetTablesAndKeys", {
#                 "qWindowSize": {
#                     "qcx": 100,
#                     "qcy": 100
#                 },
#                 "qNullSize": {
#                     "qcx": 0,
#                     "qcy": 0
#                 },
#                 "qCellHeight": 30,
#                 "qSyntheticMode": False,
#                 "qIncludeSysVars": True,
#                 "qIncludeProfiling": False
#             })
            
#             tables = []
            
#             if 'result' in response:
#                 result = response['result']
                
#                 # Parse table data
#                 if 'qtr' in result:
#                     for table_data in result['qtr']:
#                         table_name = table_data.get('qName', 'Unknown')
                        
#                         # Get fields for this table
#                         fields = []
#                         if 'qFields' in table_data:
#                             for field in table_data['qFields']:
#                                 fields.append({
#                                     "name": field.get('qName', ''),
#                                     "is_key": field.get('qIsKey', False),
#                                     "is_system": field.get('qIsSystem', False),
#                                     "is_hidden": field.get('qIsHidden', False),
#                                     "tags": field.get('qTags', [])
#                                 })
                        
#                         tables.append({
#                             "name": table_name,
#                             "fields": fields,
#                             "field_count": len(fields),
#                             "is_synthetic": table_data.get('qIsSynthetic', False),
#                             "no_of_rows": table_data.get('qNoOfRows', 0)
#                         })
            
#             return {
#                 "success": True,
#                 "tables": tables,
#                 "raw_data": response
#             }
            
#         except Exception as e:
#             print(f"Error getting tables: {str(e)}")
#             return {"success": False, "error": str(e), "tables": []}
    
#     def _get_all_fields(self) -> Dict[str, Any]:
#         """Get all fields from the app"""
#         try:
#             response = self.send_request("GetFieldDescription", {
#                 "qFieldName": "*"
#             })
            
#             # Also try GetAllInfos
#             all_infos_response = self.send_request("GetAllInfos", {})
            
#             fields = []
            
#             # Try to get field list
#             field_list_response = self.send_request("CreateSessionObject", {
#                 "qInfo": {
#                     "qType": "FieldList"
#                 },
#                 "qFieldListDef": {
#                     "qShowSystem": True,
#                     "qShowHidden": True,
#                     "qShowSemantic": True,
#                     "qShowSrcTables": True
#                 }
#             })
            
#             if 'result' in field_list_response and 'qReturn' in field_list_response['result']:
#                 field_obj_handle = field_list_response['result']['qReturn']['qHandle']
                
#                 # Get layout of field list
#                 layout_response = self.send_request("GetLayout", {}, handle=field_obj_handle)
                
#                 if 'result' in layout_response and 'qLayout' in layout_response['result']:
#                     field_list = layout_response['result']['qLayout'].get('qFieldList', {}).get('qItems', [])
                    
#                     for field in field_list:
#                         fields.append({
#                             "name": field.get('qName', ''),
#                             "cardinal": field.get('qCardinal', 0),
#                             "tags": field.get('qTags', []),
#                             "is_system": field.get('qIsSystem', False),
#                             "is_hidden": field.get('qIsHidden', False),
#                             "is_semantic": field.get('qIsSemantic', False),
#                             "src_tables": field.get('qSrcTables', [])
#                         })
            
#             return {
#                 "success": True,
#                 "fields": fields
#             }
            
#         except Exception as e:
#             print(f"Error getting fields: {str(e)}")
#             return {"success": False, "error": str(e), "fields": []}
    
#     def _get_app_layout(self) -> Dict[str, Any]:
#         """Get app layout"""
#         try:
#             response = self.send_request("GetAppLayout", {})
            
#             title = "Unknown"
#             if 'result' in response and 'qLayout' in response['result']:
#                 title = response['result']['qLayout'].get('qTitle', 'Unknown')
            
#             return {
#                 "success": True,
#                 "title": title,
#                 "raw_data": response
#             }
            
#         except Exception as e:
#             print(f"Error getting app layout: {str(e)}")
#             return {"success": False, "error": str(e), "title": "Unknown"}
    
#     def _get_app_script(self) -> Dict[str, Any]:
#         """Get app script"""
#         try:
#             response = self.send_request("GetScript", {})
            
#             script = ""
#             tables = []
            
#             if 'result' in response and 'qScript' in response['result']:
#                 script = response['result']['qScript']
                
#                 # Parse script to extract table names
#                 tables = self._parse_tables_from_script(script)
            
#             return {
#                 "success": True,
#                 "script": script,
#                 "tables": tables
#             }
            
#         except Exception as e:
#             print(f"Error getting script: {str(e)}")
#             return {"success": False, "error": str(e), "script": "", "tables": []}
    
#     def _parse_tables_from_script(self, script: str) -> List[str]:
#         """Parse table names from Qlik script"""
#         tables = []
#         lines = script.split('\n')
        
#         for line in lines:
#             line = line.strip()
            
#             # Look for table load statements
#             if line.upper().startswith('LOAD') or 'LOAD' in line.upper():
#                 # Look for table name after colon
#                 for i, script_line in enumerate(lines):
#                     if script_line.strip() and ':' in script_line:
#                         # Check if next lines contain LOAD
#                         next_lines = '\n'.join(lines[i:i+5])
#                         if 'LOAD' in next_lines.upper():
#                             table_name = script_line.split(':')[0].strip()
#                             if table_name and not table_name.startswith('//') and not table_name.startswith('['):
#                                 tables.append(table_name)
        
#         return list(set(tables))  # Remove duplicates
    
#     def _get_sheets(self) -> Dict[str, Any]:
#         """Get sheets from the app"""
#         try:
#             response = self.send_request("CreateSessionObject", {
#                 "qInfo": {
#                     "qType": "SheetList"
#                 },
#                 "qAppObjectListDef": {
#                     "qType": "sheet",
#                     "qData": {
#                         "title": "/qMetaDef/title",
#                         "description": "/qMetaDef/description",
#                         "thumbnail": "/thumbnail",
#                         "cells": "/cells",
#                         "rank": "/rank",
#                         "columns": "/columns",
#                         "rows": "/rows"
#                     }
#                 }
#             })
            
#             sheets = []
            
#             if 'result' in response and 'qReturn' in response['result']:
#                 sheet_obj_handle = response['result']['qReturn']['qHandle']
                
#                 # Get layout
#                 layout_response = self.send_request("GetLayout", {}, handle=sheet_obj_handle)
                
#                 if 'result' in layout_response and 'qLayout' in layout_response['result']:
#                     app_obj_list = layout_response['result']['qLayout'].get('qAppObjectList', {})
#                     items = app_obj_list.get('qItems', [])
                    
#                     for item in items:
#                         sheets.append({
#                             "id": item.get('qInfo', {}).get('qId', ''),
#                             "title": item.get('qData', {}).get('title', 'Untitled'),
#                             "description": item.get('qData', {}).get('description', ''),
#                             "rank": item.get('qData', {}).get('rank', 0)
#                         })
            
#             return {
#                 "success": True,
#                 "sheets": sheets
#             }
            
#         except Exception as e:
#             print(f"Error getting sheets: {str(e)}")
#             return {"success": False, "error": str(e), "sheets": []}
    
#     def get_field_values(self, app_id: str, field_name: str, limit: int = 100) -> Dict[str, Any]:
#         """Get values for a specific field with actual data"""
#         try:
#             if not self.connected or not self.app_handle:
#                 if not self.connect_to_app(app_id):
#                     return {"success": False, "error": "Failed to connect to app"}
            
#             print(f"\n{'='*60}")
#             print(f"Getting values for field: {field_name}")
#             print(f"{'='*60}")
            
#             # Create a list object for the field
#             hypercube_def = {
#                 "qInfo": {
#                     "qType": "ListObject"
#                 },
#                 "qListObjectDef": {
#                     "qStateName": "$",
#                     "qLibraryId": "",
#                     "qDef": {
#                         "qFieldDefs": [field_name],
#                         "qFieldLabels": [field_name],
#                         "qSortCriterias": [{
#                             "qSortByState": 0,
#                             "qSortByFrequency": 0,
#                             "qSortByNumeric": 1,
#                             "qSortByAscii": 1,
#                             "qSortByLoadOrder": 1,
#                             "qSortByExpression": 0,
#                             "qExpression": {
#                                 "qv": ""
#                             }
#                         }]
#                     },
#                     "qAutoSort": True,
#                     "qFrequencyMode": "V",
#                     "qShowAlternatives": True,
#                     "qInitialDataFetch": [{
#                         "qTop": 0,
#                         "qLeft": 0,
#                         "qWidth": 1,
#                         "qHeight": min(limit, 10000)
#                     }]
#                 }
#             }
            
#             # Create session object
#             create_response = self.send_request("CreateSessionObject", hypercube_def)
            
#             if 'result' in create_response and 'qReturn' in create_response['result']:
#                 object_handle = create_response['result']['qReturn']['qHandle']
#                 print(f"✓ Created list object with handle: {object_handle}")
                
#                 # Get layout which includes the data
#                 layout_response = self.send_request("GetLayout", {}, handle=object_handle)
                
#                 values = []
#                 if 'result' in layout_response and 'qLayout' in layout_response['result']:
#                     list_object = layout_response['result']['qLayout'].get('qListObject', {})
#                     data_pages = list_object.get('qDataPages', [])
                    
#                     for page in data_pages:
#                         matrix = page.get('qMatrix', [])
#                         for row in matrix:
#                             if row and len(row) > 0:
#                                 cell = row[0]
#                                 values.append({
#                                     "text": cell.get('qText', ''),
#                                     "number": cell.get('qNum', None),
#                                     "element_number": cell.get('qElemNumber', -1),
#                                     "state": cell.get('qState', ''),
#                                     "frequency": cell.get('qFrequency', '')
#                                 })
                
#                 print(f"✓ Retrieved {len(values)} values")
                
#                 # Destroy the session object
#                 self.send_request("DestroySessionObject", {"qId": str(object_handle)}, handle=-1)
                
#                 self.close()
                
#                 return {
#                     "success": True,
#                     "field_name": field_name,
#                     "values": values,
#                     "value_count": len(values),
#                     "sample_values": [v["text"] for v in values[:10]]
#                 }
#             else:
#                 self.close()
#                 return {
#                     "success": False,
#                     "error": "Could not create list object",
#                     "response": create_response
#                 }
                
#         except Exception as e:
#             self.close()
#             print(f"✗ Error: {str(e)}")
#             import traceback
#             traceback.print_exc()
#             return {"success": False, "error": str(e)}
    
#     def get_table_data(self, app_id: str, table_name: str, limit: int = 100) -> Dict[str, Any]:
#         """Get actual data from a specific table"""
#         try:
#             if not self.connected or not self.app_handle:
#                 if not self.connect_to_app(app_id):
#                     return {"success": False, "error": "Failed to connect to app"}
            
#             print(f"\n{'='*60}")
#             print(f"Getting data from table: {table_name}")
#             print(f"{'='*60}")
            
#             # First, get fields for this table
#             tables_info = self._get_tables_from_data_model()
#             table_fields = []
            
#             for table in tables_info.get("tables", []):
#                 if table["name"] == table_name:
#                     table_fields = [f["name"] for f in table["fields"] if not f.get("is_system", False)]
#                     break
            
#             if not table_fields:
#                 return {"success": False, "error": f"Table '{table_name}' not found or has no fields"}
            
#             print(f"Found {len(table_fields)} fields in table")
            
#             # Create hypercube with all fields
#             dimensions = []
#             for i, field in enumerate(table_fields[:10]):  # Limit to first 10 fields
#                 dimensions.append({
#                     "qDef": {
#                         "qFieldDefs": [field],
#                         "qFieldLabels": [field]
#                     },
#                     "qNullSuppression": False
#                 })
            
#             hypercube_def = {
#                 "qInfo": {
#                     "qType": "HyperCube"
#                 },
#                 "qHyperCubeDef": {
#                     "qDimensions": dimensions,
#                     "qMeasures": [],
#                     "qInitialDataFetch": [{
#                         "qTop": 0,
#                         "qLeft": 0,
#                         "qWidth": len(dimensions),
#                         "qHeight": min(limit, 10000)
#                     }],
#                     "qSuppressZero": False,
#                     "qSuppressMissing": False
#                 }
#             }
            
#             # Create session object
#             create_response = self.send_request("CreateSessionObject", hypercube_def)
            
#             if 'result' in create_response and 'qReturn' in create_response['result']:
#                 object_handle = create_response['result']['qReturn']['qHandle']
#                 print(f"✓ Created hypercube with handle: {object_handle}")
                
#                 # Get layout
#                 layout_response = self.send_request("GetLayout", {}, handle=object_handle)
                
#                 rows = []
#                 column_names = table_fields[:10]
                
#                 if 'result' in layout_response and 'qLayout' in layout_response['result']:
#                     hypercube = layout_response['result']['qLayout'].get('qHyperCube', {})
#                     data_pages = hypercube.get('qDataPages', [])
                    
#                     for page in data_pages:
#                         matrix = page.get('qMatrix', [])
#                         for row_data in matrix:
#                             row_values = {}
#                             for i, cell in enumerate(row_data):
#                                 if i < len(column_names):
#                                     row_values[column_names[i]] = cell.get('qText', '')
#                             rows.append(row_values)
                
#                 print(f"✓ Retrieved {len(rows)} rows")
                
#                 # Destroy session object
#                 self.send_request("DestroySessionObject", {"qId": str(object_handle)}, handle=-1)
                
#                 self.close()
                
#                 return {
#                     "success": True,
#                     "table_name": table_name,
#                     "columns": column_names,
#                     "rows": rows,
#                     "row_count": len(rows)
#                 }
#             else:
#                 self.close()
#                 return {
#                     "success": False,
#                     "error": "Could not create hypercube",
#                     "response": create_response
#                 }
                
#         except Exception as e:
#             self.close()
#             print(f"✗ Error: {str(e)}")
#             import traceback
#             traceback.print_exc()
#             return {"success": False, "error": str(e)}
    
#     def close(self):
#         """Close WebSocket connection"""
#         if self.ws:
#             try:
#                 self.ws.close()
#                 print("\n✓ WebSocket connection closed")
#             except:
#                 pass
#             self.ws = None
#         self.connected = False
#         self.app_handle = None





# qlik_websocket_client.py - FIXED VERSION FOR YOUR SETUP
import websocket
import json
import ssl
import jwt
import os
import time
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

class QlikWebSocketClient:
    def __init__(self):
        self.api_key = os.getenv('QLIK_API_KEY')
        self.tenant_url = os.getenv('QLIK_TENANT_URL')
        
        if not self.api_key or not self.tenant_url:
            raise ValueError("QLIK_API_KEY and QLIK_TENANT_URL must be set in environment variables")
        
        # Clean tenant URL
        self.tenant_url = self.tenant_url.rstrip('/')
        
        # Decode JWT to get user info
        try:
            decoded = jwt.decode(self.api_key, options={"verify_signature": False})
            self.user_id = decoded.get('sub', '')
            self.user_directory = "QLIK"
        except Exception as e:
            print(f"Warning: Could not decode JWT: {e}")
            self.user_id = ""
            self.user_directory = "QLIK"
        
        self.ws = None
        self.connected = False
        self.app_handle = None
        self.request_id = 1
        
    def _get_next_id(self) -> int:
        """Get next request ID"""
        current_id = self.request_id
        self.request_id += 1
        return current_id
    
    def _receive_response(self, expected_id: int = None, timeout: int = 30) -> Dict[str, Any]:
        """
        Receive response from WebSocket, handling OnConnected and other system messages
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = self.ws.recv()
                response_data = json.loads(response)
                
                # Check if this is a system message (OnConnected, etc.)
                if 'method' in response_data:
                    method = response_data['method']
                    print(f"   Received system message: {method}")
                    
                    if method == "OnConnected":
                        # This is normal, continue waiting for actual response
                        continue
                    else:
                        # Other system messages, log and continue
                        print(f"   System message data: {json.dumps(response_data, indent=2)}")
                        continue
                
                # Check if this is the response we're waiting for
                if expected_id is not None and response_data.get('id') == expected_id:
                    return response_data
                elif expected_id is None:
                    return response_data
                else:
                    # Not the response we're waiting for, continue
                    print(f"   Received response with different ID: {response_data.get('id')}")
                    continue
                    
            except websocket.WebSocketTimeoutException:
                continue
            except Exception as e:
                print(f"   Error receiving response: {e}")
                raise
        
        raise TimeoutError(f"Did not receive response within {timeout} seconds")
    
    def connect_to_app(self, app_id: str) -> bool:
        """Connect to a specific app via WebSocket"""
        try:
            # Clean up tenant URL
            tenant_host = self.tenant_url.replace('https://', '').replace('http://', '')
            ws_url = f"wss://{tenant_host}/app/{app_id}"
            
            print(f"\n{'='*60}")
            print(f"Connecting to Qlik app via WebSocket")
            print(f"URL: {ws_url}")
            print(f"{'='*60}")
            
            # Create WebSocket connection with timeout
            self.ws = websocket.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE})
            self.ws.settimeout(10)  # Set timeout for receiving messages
            
            # Connect with headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }
            
            if self.user_id:
                headers["X-Qlik-User"] = f"UserDirectory={self.user_directory};UserId={self.user_id}"
            
            self.ws.connect(ws_url, header=headers)
            self.connected = True
            print("✓ WebSocket connected successfully")
            
            # Open the app
            return self._open_app(app_id)
            
        except Exception as e:
            print(f"✗ Connection error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _open_app(self, app_id: str) -> bool:
        """Open the app and get its handle"""
        try:
            # Open app message
            request_id = self._get_next_id()
            open_msg = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "OpenDoc",
                "handle": -1,
                "params": {
                    "qDocName": app_id,
                    "qNoData": False
                }
            }
            
            print(f"\nSending OpenDoc request (ID: {request_id})...")
            self.ws.send(json.dumps(open_msg))
            
            # Receive response, handling OnConnected messages
            response_data = self._receive_response(expected_id=request_id)
            
            print(f"OpenDoc response: {json.dumps(response_data, indent=2)}")
            
            if 'result' in response_data:
                if 'qReturn' in response_data['result']:
                    self.app_handle = response_data['result']['qReturn']['qHandle']
                    print(f"✓ App opened successfully with handle: {self.app_handle}")
                    return True
                elif 'qHandle' in response_data['result']:
                    # Some versions return qHandle directly
                    self.app_handle = response_data['result']['qHandle']
                    print(f"✓ App opened successfully with handle: {self.app_handle}")
                    return True
                else:
                    print(f"✗ Failed to get app handle from response")
                    return False
            elif 'error' in response_data:
                error = response_data['error']
                print(f"✗ Error opening app: {error.get('message', 'Unknown error')}")
                return False
            else:
                print(f"✗ Unexpected response format")
                return False
                
        except Exception as e:
            print(f"✗ Error opening app: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_request(self, method: str, params: Dict = None, handle: int = None) -> Dict[str, Any]:
        """Send a request to Qlik Engine"""
        if not self.connected:
            raise ConnectionError("Not connected to Qlik")
        
        if handle is None:
            handle = self.app_handle
        
        request_id = self._get_next_id()
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "handle": handle,
            "params": params or {}
        }
        
        print(f"\nSending request: {method} (ID: {request_id})")
        self.ws.send(json.dumps(request))
        
        # Receive response
        response_data = self._receive_response(expected_id=request_id)
        
        return response_data
    
    def get_app_tables_simple(self, app_id: str) -> Dict[str, Any]:
        """Get comprehensive table information from app"""
        try:
            # Connect to app
            if not self.connect_to_app(app_id):
                return {"success": False, "error": "Failed to connect to app"}
            
            # Method 1: Get data model metadata
            print("\n" + "="*60)
            print("Getting data model information...")
            print("="*60)
            
            tables_info = self._get_tables_from_data_model()
            
            # Method 2: Get all fields
            print("\nGetting field list...")
            fields_info = self._get_all_fields()
            
            # Method 3: Get app layout for metadata
            print("\nGetting app layout...")
            layout_info = self._get_app_layout()
            
            # Method 4: Get script
            print("\nGetting app script...")
            script_info = self._get_app_script()
            
            # Method 5: Get sheets
            print("\nGetting sheets...")
            sheets_info = self._get_sheets()
            
            # Close connection
            self.close()
            
            # Combine all information
            result = {
                "success": True,
                "app_id": app_id,
                "app_title": layout_info.get("title", "Unknown"),
                "tables": tables_info.get("tables", []),
                "all_fields": fields_info.get("fields", []),
                "field_count": len(fields_info.get("fields", [])),
                "script": script_info.get("script", ""),
                "script_tables": script_info.get("tables", []),
                "sheets": sheets_info.get("sheets", []),
                "data_model": tables_info.get("raw_data"),
                "summary": {
                    "table_count": len(tables_info.get("tables", [])),
                    "total_fields": len(fields_info.get("fields", [])),
                    "sheet_count": len(sheets_info.get("sheets", [])),
                    "has_script": len(script_info.get("script", "")) > 0,
                    "script_table_count": len(script_info.get("tables", []))
                }
            }
            
            return result
            
        except Exception as e:
            self.close()
            print(f"\n✗ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
        
      

    def get_script_table_details(self, app_id: str, table_name: str) -> Optional[dict]:
        """
        Fetch detailed metadata for a script-only table by name.
        Returns dict with keys: name, fields, field_count, no_of_rows, is_synthetic.
        """
        try:
            if not self.connected or not self.app_handle:
                if not self.connect_to_app(app_id):
                    return None

            # Call GetTablesAndKeys to get all tables
            tables_response = self._get_tables_from_data_model()
            if not tables_response.get("success"):
                return None

            for table in tables_response.get("tables", []):
                if table.get("name") == table_name:
                    return table

            return None  # Table not found

        except Exception as e:
            print(f"Error fetching script table details for {table_name}: {e}")
            return None

    # ... other methods below ...

    
    def _get_tables_from_data_model(self) -> Dict[str, Any]:
        """Get tables from data model"""
        try:
            # Get table list
            response = self.send_request("GetTablesAndKeys", {
                "qWindowSize": {
                    "qcx": 100,
                    "qcy": 100
                },
                "qNullSize": {
                    "qcx": 0,
                    "qcy": 0
                },
                "qCellHeight": 30,
                "qSyntheticMode": False,
                "qIncludeSysVars": True,
                "qIncludeProfiling": False
            })
            
            tables = []
            
            if 'result' in response:
                result = response['result']
                
                # Parse table data
                if 'qtr' in result:
                    for table_data in result['qtr']:
                        table_name = table_data.get('qName', 'Unknown')
                        
                        # Get fields for this table
                        fields = []
                        if 'qFields' in table_data:
                            for field in table_data['qFields']:
                                fields.append({
                                    "name": field.get('qName', ''),
                                    "is_key": field.get('qIsKey', False),
                                    "is_system": field.get('qIsSystem', False),
                                    "is_hidden": field.get('qIsHidden', False),
                                    "tags": field.get('qTags', [])
                                })
                        
                        tables.append({
                            "name": table_name,
                            "fields": fields,
                            "field_count": len(fields),
                            "is_synthetic": table_data.get('qIsSynthetic', False),
                            "no_of_rows": table_data.get('qNoOfRows', 0)
                        })
            
            print(f"✓ Found {len(tables)} tables")
            return {
                "success": True,
                "tables": tables,
                "raw_data": response
            }
            
        except Exception as e:
            print(f"Error getting tables: {str(e)}")
            return {"success": False, "error": str(e), "tables": []}
    
    def _get_all_fields(self) -> Dict[str, Any]:
        """Get all fields from the app"""
        try:
            # Create a proper FieldList session object
            field_list_response = self.send_request("CreateSessionObject", {
                "qInfo": {
                    "qType": "FieldList"
                },
                "qFieldListDef": {
                    "qShowSystem": True,
                    "qShowHidden": True,
                    "qShowSemantic": True,
                    "qShowSrcTables": True
                }
            })
            
            fields = []
            
            if 'result' in field_list_response and 'qReturn' in field_list_response['result']:
                field_obj_handle = field_list_response['result']['qReturn']['qHandle']
                
                # Get layout of field list
                layout_response = self.send_request("GetLayout", {}, handle=field_obj_handle)
                
                if 'result' in layout_response and 'qLayout' in layout_response['result']:
                    field_list = layout_response['result']['qLayout'].get('qFieldList', {}).get('qItems', [])
                    
                    for field in field_list:
                        fields.append({
                            "name": field.get('qName', ''),
                            "cardinal": field.get('qCardinal', 0),
                            "tags": field.get('qTags', []),
                            "is_system": field.get('qIsSystem', False),
                            "is_hidden": field.get('qIsHidden', False),
                            "is_semantic": field.get('qIsSemantic', False),
                            "src_tables": field.get('qSrcTables', [])
                        })
                
                # Destroy the session object
                self.send_request("DestroySessionObject", {"qId": str(field_obj_handle)}, handle=-1)
            
            print(f"✓ Found {len(fields)} fields")
            return {
                "success": True,
                "fields": fields
            }
            
        except Exception as e:
            print(f"Error getting fields: {str(e)}")
            return {"success": False, "error": str(e), "fields": []}
    
    def _get_app_layout(self) -> Dict[str, Any]:
        """Get app layout"""
        try:
            response = self.send_request("GetAppLayout", {})
            
            title = "Unknown"
            if 'result' in response and 'qLayout' in response['result']:
                title = response['result']['qLayout'].get('qTitle', 'Unknown')
            
            print(f"✓ App title: {title}")
            return {
                "success": True,
                "title": title,
                "raw_data": response
            }
            
        except Exception as e:
            print(f"Error getting app layout: {str(e)}")
            return {"success": False, "error": str(e), "title": "Unknown"}
    
    def _get_app_script(self) -> Dict[str, Any]:
        """Get app script"""
        try:
            response = self.send_request("GetScript", {})
            
            script = ""
            tables = []
            
            if 'result' in response and 'qScript' in response['result']:
                script = response['result']['qScript']
                
                # Parse script to extract table names
                tables = self._parse_tables_from_script(script)
            
            print(f"✓ Script length: {len(script)} characters")
            print(f"✓ Found {len(tables)} tables in script")
            
            return {
                "success": True,
                "script": script,
                "tables": tables
            }
            
        except Exception as e:
            print(f"Error getting script: {str(e)}")
            return {"success": False, "error": str(e), "script": "", "tables": []}
    
    def _parse_tables_from_script(self, script: str) -> List[str]:
        """Parse table names from Qlik script"""
        tables = []
        lines = script.split('\n')
        
        current_table = None
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Look for table name before colon
            if ':' in line and not line_stripped.startswith('//'):
                # Check if next few lines contain LOAD
                next_lines = '\n'.join(lines[i:i+5])
                if 'LOAD' in next_lines.upper():
                    parts = line.split(':')
                    if len(parts) >= 2:
                        table_name = parts[0].strip()
                        # Clean up table name
                        table_name = table_name.replace('[', '').replace(']', '')
                        if table_name and not table_name.startswith('//'):
                            tables.append(table_name)
        
        return list(set(tables))  # Remove duplicates
    
    def _get_sheets(self) -> Dict[str, Any]:
        """Get sheets from the app"""
        try:
            response = self.send_request("CreateSessionObject", {
                "qInfo": {
                    "qType": "SheetList"
                },
                "qAppObjectListDef": {
                    "qType": "sheet",
                    "qData": {
                        "title": "/qMetaDef/title",
                        "description": "/qMetaDef/description",
                        "thumbnail": "/thumbnail",
                        "cells": "/cells",
                        "rank": "/rank",
                        "columns": "/columns",
                        "rows": "/rows"
                    }
                }
            })
            
            sheets = []
            
            if 'result' in response and 'qReturn' in response['result']:
                sheet_obj_handle = response['result']['qReturn']['qHandle']
                
                # Get layout
                layout_response = self.send_request("GetLayout", {}, handle=sheet_obj_handle)
                
                if 'result' in layout_response and 'qLayout' in layout_response['result']:
                    app_obj_list = layout_response['result']['qLayout'].get('qAppObjectList', {})
                    items = app_obj_list.get('qItems', [])
                    
                    for item in items:
                        sheets.append({
                            "id": item.get('qInfo', {}).get('qId', ''),
                            "title": item.get('qData', {}).get('title', 'Untitled'),
                            "description": item.get('qData', {}).get('description', ''),
                            "rank": item.get('qData', {}).get('rank', 0)
                        })
                
                # Destroy the session object
                self.send_request("DestroySessionObject", {"qId": str(sheet_obj_handle)}, handle=-1)
            
            print(f"✓ Found {len(sheets)} sheets")
            return {
                "success": True,
                "sheets": sheets
            }
            
        except Exception as e:
            print(f"Error getting sheets: {str(e)}")
            return {"success": False, "error": str(e), "sheets": []}
    
    def get_field_values(self, app_id: str, field_name: str, limit: int = 100) -> Dict[str, Any]:
        """Get values for a specific field with actual data"""
        try:
            if not self.connected or not self.app_handle:
                if not self.connect_to_app(app_id):
                    return {"success": False, "error": "Failed to connect to app"}
            
            print(f"\n{'='*60}")
            print(f"Getting values for field: {field_name}")
            print(f"{'='*60}")
            
            # Create a list object for the field
            hypercube_def = {
                "qInfo": {
                    "qType": "ListObject"
                },
                "qListObjectDef": {
                    "qStateName": "$",
                    "qLibraryId": "",
                    "qDef": {
                        "qFieldDefs": [field_name],
                        "qFieldLabels": [field_name],
                        "qSortCriterias": [{
                            "qSortByState": 0,
                            "qSortByFrequency": 0,
                            "qSortByNumeric": 1,
                            "qSortByAscii": 1,
                            "qSortByLoadOrder": 1,
                            "qSortByExpression": 0,
                            "qExpression": {
                                "qv": ""
                            }
                        }]
                    },
                    "qAutoSort": True,
                    "qFrequencyMode": "V",
                    "qShowAlternatives": True,
                    "qInitialDataFetch": [{
                        "qTop": 0,
                        "qLeft": 0,
                        "qWidth": 1,
                        "qHeight": min(limit, 10000)
                    }]
                }
            }
            
            # Create session object
            create_response = self.send_request("CreateSessionObject", hypercube_def)
            
            if 'result' in create_response and 'qReturn' in create_response['result']:
                object_handle = create_response['result']['qReturn']['qHandle']
                print(f"✓ Created list object with handle: {object_handle}")
                
                # Get layout which includes the data
                layout_response = self.send_request("GetLayout", {}, handle=object_handle)
                
                values = []
                if 'result' in layout_response and 'qLayout' in layout_response['result']:
                    list_object = layout_response['result']['qLayout'].get('qListObject', {})
                    data_pages = list_object.get('qDataPages', [])
                    
                    for page in data_pages:
                        matrix = page.get('qMatrix', [])
                        for row in matrix:
                            if row and len(row) > 0:
                                cell = row[0]
                                values.append({
                                    "text": cell.get('qText', ''),
                                    "number": cell.get('qNum', None),
                                    "element_number": cell.get('qElemNumber', -1),
                                    "state": cell.get('qState', ''),
                                    "frequency": cell.get('qFrequency', '')
                                })
                
                print(f"✓ Retrieved {len(values)} values")
                
                # Destroy the session object
                self.send_request("DestroySessionObject", {"qId": str(object_handle)}, handle=-1)
                
                self.close()
                
                return {
                    "success": True,
                    "field_name": field_name,
                    "values": values,
                    "value_count": len(values),
                    "sample_values": [v["text"] for v in values[:10]]
                }
            else:
                self.close()
                return {
                    "success": False,
                    "error": "Could not create list object",
                    "response": create_response
                }
                
        except Exception as e:
            self.close()
            print(f"✗ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def get_table_data(self, app_id: str, table_name: str, limit: int = 100) -> Dict[str, Any]:
        """Get actual data from a specific table"""
        try:
            if not self.connected or not self.app_handle:
                if not self.connect_to_app(app_id):
                    return {"success": False, "error": "Failed to connect to app"}
            
            print(f"\n{'='*60}")
            print(f"Getting data from table: {table_name}")
            print(f"{'='*60}")
            
            # First, get fields for this table
            tables_info = self._get_tables_from_data_model()
            table_fields = []
            
            for table in tables_info.get("tables", []):
                if table["name"] == table_name:
                    table_fields = [f["name"] for f in table["fields"] if not f.get("is_system", False)]
                    break
            
            if not table_fields:
                return {"success": False, "error": f"Table '{table_name}' not found or has no fields"}
            
            print(f"Found {len(table_fields)} fields in table")
            
            # Create hypercube with all fields
            dimensions = []
            for i, field in enumerate(table_fields[:10]):  # Limit to first 10 fields
                dimensions.append({
                    "qDef": {
                        "qFieldDefs": [field],
                        "qFieldLabels": [field]
                    },
                    "qNullSuppression": False
                })
            
            hypercube_def = {
                "qInfo": {
                    "qType": "HyperCube"
                },
                "qHyperCubeDef": {
                    "qDimensions": dimensions,
                    "qMeasures": [],
                    "qInitialDataFetch": [{
                        "qTop": 0,
                        "qLeft": 0,
                        "qWidth": len(dimensions),
                        "qHeight": min(limit, 10000)
                    }],
                    "qSuppressZero": False,
                    "qSuppressMissing": False
                }
            }
            
            # Create session object
            create_response = self.send_request("CreateSessionObject", hypercube_def)
            
            if 'result' in create_response and 'qReturn' in create_response['result']:
                object_handle = create_response['result']['qReturn']['qHandle']
                print(f"✓ Created hypercube with handle: {object_handle}")
                
                # Get layout
                layout_response = self.send_request("GetLayout", {}, handle=object_handle)
                
                rows = []
                column_names = table_fields[:10]
                
                if 'result' in layout_response and 'qLayout' in layout_response['result']:
                    hypercube = layout_response['result']['qLayout'].get('qHyperCube', {})
                    data_pages = hypercube.get('qDataPages', [])
                    
                    for page in data_pages:
                        matrix = page.get('qMatrix', [])
                        for row_data in matrix:
                            row_values = {}
                            for i, cell in enumerate(row_data):
                                if i < len(column_names):
                                    row_values[column_names[i]] = cell.get('qText', '')
                            rows.append(row_values)
                
                print(f"✓ Retrieved {len(rows)} rows")
                
                # Destroy session object
                self.send_request("DestroySessionObject", {"qId": str(object_handle)}, handle=-1)
                
                self.close()
                
                return {
                    "success": True,
                    "table_name": table_name,
                    "columns": column_names,
                    "rows": rows,
                    "row_count": len(rows)
                }
            else:
                self.close()
                return {
                    "success": False,
                    "error": "Could not create hypercube",
                    "response": create_response
                }
                
        except Exception as e:
            self.close()
            print(f"✗ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def close(self):
        """Close WebSocket connection"""
        if self.ws:
            try:
                self.ws.close()
                print("\n✓ WebSocket connection closed")
            except:
                pass
            self.ws = None
        self.connected = False
        self.app_handle = None


