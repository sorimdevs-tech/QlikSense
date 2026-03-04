# """
# ROBUST M QUERY CONVERTER WITH RELATIONSHIPS
# Handles Fabric API token limits by chunking large deployments
# Prevents timeout and token overflow errors
# """

# import re
# import logging
# import json
# from typing import Dict, List, Any, Optional, Tuple
# from datetime import datetime

# logger = logging.getLogger(__name__)

# # ============================================================================
# # TOKEN MANAGEMENT
# # ============================================================================

# class TokenManager:
#     """
#     Manages API token usage and prevents overflows
#     Implements token pooling and rotation
#     """
    
#     # Approximate token costs
#     TOKEN_COSTS = {
#         "table_definition": 500,      # Per table
#         "relationship_definition": 200,  # Per relationship
#         "csv_data": 2,                # Per byte of CSV
#         "api_call": 1000,             # Base API call overhead
#         "deployment": 5000,           # Deployment overhead
#     }
    
#     MAX_TOKEN_PER_REQUEST = 120000  # Safe limit (150k actual limit)
    
#     def __init__(self, access_tokens: List[str]):
#         """
#         Initialize with multiple access tokens
#         Allows rotating tokens to prevent exhaustion
#         """
#         self.tokens = access_tokens
#         self.current_token_index = 0
#         self.token_usage = {token: 0 for token in access_tokens}
    
#     def get_next_token(self) -> str:
#         """Get next available token (round-robin)"""
#         token = self.tokens[self.current_token_index]
#         self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
#         return token
    
#     def estimate_deployment_cost(
#         self,
#         tables: List[Dict],
#         relationships: List[Dict],
#         csv_payloads: Dict[str, str]
#     ) -> int:
#         """Estimate tokens needed for deployment"""
        
#         cost = 0
        
#         # Table definitions
#         cost += len(tables) * self.TOKEN_COSTS["table_definition"]
        
#         # Relationships
#         cost += len(relationships) * self.TOKEN_COSTS["relationship_definition"]
        
#         # CSV data
#         for csv in csv_payloads.values():
#             cost += len(csv) * self.TOKEN_COSTS["csv_data"]
        
#         # API overhead
#         cost += self.TOKEN_COSTS["api_call"]
#         cost += self.TOKEN_COSTS["deployment"]
        
#         return cost
    
#     def can_fit_in_token_limit(
#         self,
#         tables: List[Dict],
#         relationships: List[Dict],
#         csv_payloads: Dict[str, str]
#     ) -> bool:
#         """Check if deployment fits within token limit"""
#         cost = self.estimate_deployment_cost(tables, relationships, csv_payloads)
#         return cost < self.MAX_TOKEN_PER_REQUEST
    
#     def split_for_chunking(
#         self,
#         tables: List[Dict],
#         relationships: List[Dict],
#         csv_payloads: Dict[str, str]
#     ) -> List[Tuple[List[Dict], List[Dict], Dict[str, str]]]:
#         """
#         Split large deployment into chunks to fit token limits
#         Returns list of (tables, relationships, csvs) tuples
#         """
        
#         # Calculate size
#         cost = self.estimate_deployment_cost(tables, relationships, csv_payloads)
        
#         if cost < self.MAX_TOKEN_PER_REQUEST:
#             # Fits in one chunk
#             return [(tables, relationships, csv_payloads)]
        
#         # Need to chunk
#         chunks = []
#         tables_per_chunk = max(1, len(tables) // 2)
        
#         for i in range(0, len(tables), tables_per_chunk):
#             chunk_tables = tables[i:i+tables_per_chunk]
#             chunk_table_names = {t.get("name") for t in chunk_tables}
            
#             # Filter relationships to only those within this chunk
#             chunk_rels = [
#                 r for r in relationships
#                 if r.get("fromTable") in chunk_table_names and 
#                    r.get("toTable") in chunk_table_names
#             ]
            
#             # Filter CSV payloads
#             chunk_csvs = {
#                 name: csv for name, csv in csv_payloads.items()
#                 if name in chunk_table_names
#             }
            
#             chunks.append((chunk_tables, chunk_rels, chunk_csvs))
        
#         return chunks


# # ============================================================================
# # ROBUST M QUERY CONVERTER WITH RELATIONSHIPS
# # ============================================================================

# class RobustMQueryConverter:
#     """
#     Converts Qlik tables to M Query with relationships
#     Handles:
#     - Embedded CSV data
#     - Relationship definitions (as comments)
#     - Multiple data sources (inline, file, SQL)
#     - Large datasets with chunking
#     - Token limit management
#     """
    
#     def __init__(self, access_tokens: Optional[List[str]] = None):
#         """
#         Initialize converter with optional token management
        
#         Args:
#             access_tokens: List of Fabric API tokens for rotation
#         """
#         self.token_manager = TokenManager(access_tokens or ["default-token"])
#         self.deployments = []
    
#     def convert_with_relationships(
#         self,
#         app_id: str,
#         app_name: str,
#         tables: List[Dict[str, Any]],
#         relationships: List[Dict[str, Any]],
#         csv_payloads: Dict[str, str],
#         data_source: str = "inline"
#     ) -> Dict[str, Any]:
#         """
#         Convert tables to M Query with relationships
#         Handles token limits by chunking if needed
        
#         Args:
#             app_id: Qlik app ID
#             app_name: Qlik app name
#             tables: List of table definitions
#             relationships: List of relationship definitions
#             csv_payloads: CSV data for each table
#             data_source: 'inline', 'csv', or 'sql'
        
#         Returns:
#             Deployment plan with M queries and chunking info
#         """
        
#         logger.info(f"Converting {len(tables)} tables with {len(relationships)} relationships")
        
#         # Check if fits in token limit
#         fits_in_one = self.token_manager.can_fit_in_token_limit(
#             tables, relationships, csv_payloads
#         )
        
#         if not fits_in_one:
#             logger.warning(f"⚠️ Deployment exceeds token limit - will chunk into multiple deployments")
#             chunks = self.token_manager.split_for_chunking(
#                 tables, relationships, csv_payloads
#             )
#         else:
#             chunks = [(tables, relationships, csv_payloads)]
        
#         # Build deployment plan
#         deployment_plan = {
#             "appId": app_id,
#             "appName": app_name,
#             "dataSource": data_source,
#             "timestamp": datetime.now().isoformat(),
#             "totalTables": len(tables),
#             "totalRelationships": len(relationships),
#             "chunksNeeded": len(chunks),
#             "deployments": []
#         }
        
#         # Create M Query for each chunk
#         for chunk_idx, (chunk_tables, chunk_rels, chunk_csvs) in enumerate(chunks):
#             logger.info(f"Creating M Query for chunk {chunk_idx + 1}/{len(chunks)}")
            
#             # Get token for this deployment
#             token = self.token_manager.get_next_token()
            
#             # Build M Query
#             m_query = self._build_m_query_with_relationships(
#                 chunk_tables,
#                 chunk_rels,
#                 chunk_csvs,
#                 data_source,
#                 app_name,
#                 chunk_idx
#             )
            
#             # Build semantic model
#             semantic_model = self._build_semantic_model(
#                 app_name,
#                 chunk_tables,
#                 chunk_rels,
#                 data_source,
#                 chunk_idx
#             )
            
#             # Record deployment
#             deployment = {
#                 "chunkIndex": chunk_idx,
#                 "token": token[:20] + "..." if token != "default-token" else token,
#                 "datasetName": self._get_dataset_name(app_name, chunk_idx),
#                 "tableCount": len(chunk_tables),
#                 "relationshipCount": len(chunk_rels),
#                 "mQuery": m_query,
#                 "semanticModel": semantic_model,
#                 "csvPayloadSize": sum(len(csv) for csv in chunk_csvs.values()),
#                 "estimatedTokenCost": self.token_manager.estimate_deployment_cost(
#                     chunk_tables, chunk_rels, chunk_csvs
#                 )
#             }
            
#             deployment_plan["deployments"].append(deployment)
#             logger.info(
#                 f"  Chunk {chunk_idx + 1}: {len(chunk_tables)} tables, "
#                 f"{len(chunk_rels)} relationships, "
#                 f"~{deployment['estimatedTokenCost']} tokens"
#             )
        
#         return deployment_plan
    
#     def _build_m_query_with_relationships(
#         self,
#         tables: List[Dict],
#         relationships: List[Dict],
#         csv_payloads: Dict[str, str],
#         data_source: str,
#         app_name: str,
#         chunk_idx: int
#     ) -> str:
#         """Build M Query with relationship comments"""
        
#         m_query = f"""// QLIK → POWER BI M QUERY
# // Application: {app_name}
# // Generated: {datetime.now().isoformat()}
# // Data Source: {data_source}
# // Chunk: {chunk_idx + 1}

# // =============================================================================
# // RELATIONSHIPS
# // =============================================================================
# """
        
#         if relationships:
#             for rel in relationships:
#                 m_query += (
#                     f"\n// {rel['fromTable']}.{rel['fromColumn']} → "
#                     f"{rel['toTable']}.{rel['toColumn']} ({rel.get('cardinality', 'ManyToOne')})"
#                 )
#         else:
#             m_query += "\n// No relationships"
        
#         m_query += f"""

# // =============================================================================
# // TABLE DEFINITIONS
# // =============================================================================

# """
        
#         # Build queries for each table
#         for table in tables:
#             table_name = table.get("name", "")
#             fields = table.get("fields", [])
            
#             m_query += f"""// Table: {table_name}
# let
#     {table_name}_Source = {self._get_data_source_expression(table, data_source, csv_payloads)},
#     {table_name}_Headers = Table.PromoteHeaders({table_name}_Source),
#     {table_name}_Typed = Table.TransformColumnTypes(
#         {table_name}_Headers,
#         {self._build_type_definitions(fields)}
#     ),
#     {table_name}_Final = {table_name}_Typed
# in
#     {table_name}_Final

# """
        
#         return m_query
    
#     def _get_data_source_expression(
#         self,
#         table: Dict,
#         data_source: str,
#         csv_payloads: Dict[str, str]
#     ) -> str:
#         """Get M expression for data source"""
        
#         table_name = table.get("name", "")
        
#         if data_source == "inline" and table_name in csv_payloads:
#             csv_content = csv_payloads[table_name]
#             # Build inline CSV as #table()
#             return self._csv_to_m_table(csv_content)
        
#         elif data_source == "csv":
#             # Reference to CSV file
#             return f'Csv.Document(File.Contents("[DataSourcePath]/{table_name}.csv"))'
        
#         elif data_source == "sql":
#             # SQL Server connection
#             return f'Sql.Database("[SQLServer]", "[Database]", "SELECT * FROM {table_name}")'
        
#         else:
#             # Default placeholder
#             return f'#table(type table [], {{}})'
    
#     def _csv_to_m_table(self, csv_content: str) -> str:
#         """Convert CSV to M #table() expression"""
        
#         lines = csv_content.strip().split('\n')
#         if not lines:
#             return '#table({}, {})'
        
#         headers = lines[0].split(',')
#         rows = [line.split(',') for line in lines[1:]]
        
#         # Build column types
#         col_types = ", ".join([f'"{col}"=type text' for col in headers])
        
#         # Build rows (limit to avoid token overflow)
#         max_rows = min(len(rows), 100)  # Max 100 rows per table to save tokens
#         row_values = []
        
#         for row in rows[:max_rows]:
#             row_values.append("{" + ", ".join([f'"{val}"' for val in row]) + "}")
        
#         if len(rows) > max_rows:
#             logger.warning(f"⚠️ Table {headers[0]}: truncated from {len(rows)} to {max_rows} rows to fit token limit")
        
#         return f'#table(type table[{col_types}], {{{", ".join(row_values)}}})'
    
#     def _build_type_definitions(self, fields: List[Dict]) -> str:
#         """Build M column type definitions"""
        
#         types = []
        
#         for field in fields:
#             name = field.get("name", "")
#             field_type = field.get("type", "text").lower()
            
#             # Map Qlik types to M types
#             m_type_map = {
#                 "integer": "Int64.Type",
#                 "int": "Int64.Type",
#                 "numeric": "type number",
#                 "number": "type number",
#                 "decimal": "type number",
#                 "date": "type date",
#                 "datetime": "type datetime",
#                 "timestamp": "type datetime",
#                 "text": "type text",
#                 "string": "type text",
#                 "boolean": "type logical",
#                 "bool": "type logical",
#             }
            
#             m_type = m_type_map.get(field_type, "type text")
#             types.append(f'{{"{name}", {m_type}}}')
        
#         return "{\n            " + ",\n            ".join(types) + "\n        }"
    
#     def _build_semantic_model(
#         self,
#         app_name: str,
#         tables: List[Dict],
#         relationships: List[Dict],
#         data_source: str,
#         chunk_idx: int
#     ) -> Dict[str, Any]:
#         """Build Power BI Tabular semantic model definition"""
        
#         # Build table definitions
#         model_tables = []
        
#         for table in tables:
#             columns = []
#             for field in table.get("fields", []):
#                 columns.append({
#                     "name": field.get("name", ""),
#                     "dataType": self._map_qlik_to_tabular_type(field.get("type", "text"))
#                 })
            
#             model_tables.append({
#                 "name": table.get("name", ""),
#                 "columns": columns,
#                 "partitions": [
#                     {
#                         "name": f"{table.get('name')}_Partition",
#                         "source": {
#                             "type": "m",
#                             "expression": f"{table.get('name')}_Query"
#                         }
#                     }
#                 ]
#             })
        
#         # Build relationship definitions
#         model_relationships = []
        
#         for rel in relationships:
#             model_relationships.append({
#                 "name": (
#                     f"{rel['fromTable']}_{rel['fromColumn']}_to_"
#                     f"{rel['toTable']}_{rel['toColumn']}"
#                 ),
#                 "fromTable": rel["fromTable"],
#                 "fromColumn": rel["fromColumn"],
#                 "toTable": rel["toTable"],
#                 "toColumn": rel["toColumn"],
#                 "fromCardinality": "Many",
#                 "toCardinality": "One",
#                 "isActive": True
#             })
        
#         return {
#             "name": self._get_dataset_name(app_name, chunk_idx),
#             "compatibilityLevel": 1565,
#             "tables": model_tables,
#             "relationships": model_relationships,
#             "defaultLanguage": "en-US",
#             "culture": "en-US"
#         }
    
#     def _get_dataset_name(self, app_name: str, chunk_idx: int) -> str:
#         """Generate dataset name"""
#         safe_name = re.sub(r'[^\w\-]', '_', app_name)
#         if chunk_idx > 0:
#             return f"Qlik_{safe_name}_Part{chunk_idx + 1}"
#         return f"Qlik_{safe_name}"
    
#     def _map_qlik_to_tabular_type(self, qlik_type: str) -> str:
#         """Map Qlik type to Tabular Model type"""
        
#         type_map = {
#             "integer": "Int64",
#             "int": "Int64",
#             "numeric": "Double",
#             "number": "Double",
#             "decimal": "Decimal",
#             "date": "DateTime",
#             "datetime": "DateTime",
#             "timestamp": "DateTime",
#             "text": "String",
#             "string": "String",
#             "boolean": "Boolean",
#             "bool": "Boolean",
#         }
        
#         return type_map.get(qlik_type.lower(), "String")


# # ============================================================================
# # DEPLOYMENT EXECUTOR
# # ============================================================================

# class RobustDeploymentExecutor:
#     """
#     Execute deployments with token management
#     Handles retries and fallbacks for token failures
#     """
    
#     def __init__(self, max_retries: int = 3):
#         self.max_retries = max_retries
#         self.deployment_results = []
    
#     def deploy_with_retry(
#         self,
#         deployment_plan: Dict[str, Any],
#         deploy_function
#     ) -> Dict[str, Any]:
#         """
#         Deploy with automatic retry on token failures
        
#         Args:
#             deployment_plan: Deployment plan from converter
#             deploy_function: Function to call for actual deployment
        
#         Returns:
#             Deployment results
#         """
        
#         results = {
#             "appName": deployment_plan["appName"],
#             "totalChunks": deployment_plan["chunksNeeded"],
#             "successfulDeployments": 0,
#             "failedDeployments": 0,
#             "chunkResults": []
#         }
        
#         for deployment in deployment_plan["deployments"]:
#             chunk_idx = deployment["chunkIndex"]
            
#             logger.info(f"Deploying chunk {chunk_idx + 1}/{deployment_plan['chunksNeeded']}")
            
#             # Try deployment with retries
#             chunk_result = self._deploy_with_retry(
#                 deployment,
#                 deploy_function,
#                 chunk_idx
#             )
            
#             if chunk_result["success"]:
#                 results["successfulDeployments"] += 1
#             else:
#                 results["failedDeployments"] += 1
            
#             results["chunkResults"].append(chunk_result)
        
#         return results
    
#     def _deploy_with_retry(
#         self,
#         deployment: Dict,
#         deploy_function,
#         chunk_idx: int
#     ) -> Dict[str, Any]:
#         """Deploy single chunk with retries"""
        
#         for attempt in range(self.max_retries):
#             try:
#                 logger.info(f"Attempt {attempt + 1}/{self.max_retries} for chunk {chunk_idx}")
                
#                 # Call deployment function
#                 result = deploy_function(deployment)
                
#                 if result.get("success"):
#                     logger.info(f"✅ Chunk {chunk_idx} deployed successfully")
#                     return {
#                         "chunkIndex": chunk_idx,
#                         "success": True,
#                         "datasetId": result.get("dataset_id"),
#                         "message": f"Deployed successfully in attempt {attempt + 1}"
#                     }
#                 else:
#                     # Non-token error
#                     raise Exception(result.get("error", "Deployment failed"))
            
#             except Exception as e:
#                 error_msg = str(e).lower()
                
#                 # Check if it's a token limit error
#                 if "token" in error_msg or "limit" in error_msg:
#                     logger.warning(f"⚠️ Token error on attempt {attempt + 1}: {str(e)}")
                    
#                     if attempt < self.max_retries - 1:
#                         logger.info(f"Retrying...")
#                         continue
#                     else:
#                         return {
#                             "chunkIndex": chunk_idx,
#                             "success": False,
#                             "error": f"Token limit exceeded after {self.max_retries} attempts",
#                             "errorType": "TOKEN_LIMIT"
#                         }
#                 else:
#                     # Other error
#                     logger.error(f"❌ Chunk {chunk_idx} failed: {str(e)}")
#                     return {
#                         "chunkIndex": chunk_idx,
#                         "success": False,
#                         "error": str(e),
#                         "errorType": "DEPLOYMENT_ERROR"
#                     }
        
#         return {
#             "chunkIndex": chunk_idx,
#             "success": False,
#             "error": "Max retries exceeded",
#             "errorType": "MAX_RETRIES"
#         }


# # ============================================================================
# # EXAMPLE USAGE
# # ============================================================================

# if __name__ == "__main__":
    
#     # Sample data
#     tables = [
#         {
#             "name": "Sales",
#             "fields": [
#                 {"name": "SalesID", "type": "integer"},
#                 {"name": "CustomerID", "type": "integer"},
#                 {"name": "Amount", "type": "numeric"},
#                 {"name": "OrderDate", "type": "date"}
#             ]
#         },
#         {
#             "name": "Customer",
#             "fields": [
#                 {"name": "CustomerID", "type": "integer"},
#                 {"name": "Name", "type": "text"},
#                 {"name": "Country", "type": "text"}
#             ]
#         }
#     ]
    
#     relationships = [
#         {
#             "fromTable": "Sales",
#             "fromColumn": "CustomerID",
#             "toTable": "Customer",
#             "toColumn": "CustomerID",
#             "cardinality": "ManyToOne"
#         }
#     ]
    
#     csv_payloads = {
#         "Sales": "SalesID,CustomerID,Amount,OrderDate\n1001,5001,15000,2024-01-15\n1002,5002,12500,2024-01-16",
#         "Customer": "CustomerID,Name,Country\n5001,John,USA\n5002,Jane,UK"
#     }
    
#     # Create converter with multiple tokens (for rotation)
#     converter = RobustMQueryConverter(access_tokens=[
#         "token_1",
#         "token_2",
#         "token_3"
#     ])
    
#     # Convert with relationships
#     deployment_plan = converter.convert_with_relationships(
#         app_id="app-001",
#         app_name="Sales Analytics",
#         tables=tables,
#         relationships=relationships,
#         csv_payloads=csv_payloads,
#         data_source="inline"
#     )
    
#     print("\n" + "="*80)
#     print("DEPLOYMENT PLAN")
#     print("="*80)
#     print(f"App: {deployment_plan['appName']}")
#     print(f"Tables: {deployment_plan['totalTables']}")
#     print(f"Relationships: {deployment_plan['totalRelationships']}")
#     print(f"Chunks: {deployment_plan['chunksNeeded']}")
#     print(f"\nDeployments:")
    
#     for deployment in deployment_plan["deployments"]:
#         print(f"\n  Chunk {deployment['chunkIndex'] + 1}:")
#         print(f"    Dataset: {deployment['datasetName']}")
#         print(f"    Tables: {deployment['tableCount']}")
#         print(f"    Relationships: {deployment['relationshipCount']}")
#         print(f"    Estimated Tokens: {deployment['estimatedTokenCost']}")
#         print(f"    Token Limit: {TokenManager.MAX_TOKEN_PER_REQUEST}")
#         print(f"    Fits in Limit: {'✅ Yes' if deployment['estimatedTokenCost'] < TokenManager.MAX_TOKEN_PER_REQUEST else '❌ No'}")
    
#     print("\n" + "="*80)