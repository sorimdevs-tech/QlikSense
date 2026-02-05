#!/usr/bin/env python3
"""
Test script for Qlik WebSocket Client
This script tests the connection and data retrieval from Qlik Sense Cloud
"""

import os
import sys
import json
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def test_websocket_connection():
    """Test WebSocket connection and data retrieval"""
    
    # Import the improved client
    try:
        from qlik_websocket_client import QlikWebSocketClient
        print("✓ Successfully imported QlikWebSocketClient")
    except ImportError as e:
        print(f"✗ Failed to import QlikWebSocketClient: {e}")
        return
    
    # Check environment variables
    print_section("Checking Environment Variables")
    api_key = os.getenv('QLIK_API_KEY')
    tenant_url = os.getenv('QLIK_TENANT_URL')
    
    if not api_key:
        print("✗ QLIK_API_KEY not found in environment")
        return
    else:
        print(f"✓ QLIK_API_KEY found (length: {len(api_key)})")
    
    if not tenant_url:
        print("✗ QLIK_TENANT_URL not found in environment")
        return
    else:
        print(f"✓ QLIK_TENANT_URL found: {tenant_url}")
    
    # Get app ID from user or use default
    print_section("Application Selection")
    print("\nEnter the Qlik app ID to test (or press Enter to use first available app):")
    app_id_input = input("> ").strip()
    
    if not app_id_input:
        # Try to get apps list
        try:
            from qlik_client import QlikClient
            client = QlikClient()
            apps = client.get_applications()
            
            if apps and len(apps) > 0:
                # Find first app with data
                for app in apps:
                    if isinstance(app, dict):
                        attributes = app.get('attributes', {})
                        if attributes.get('lastReloadTime'):
                            app_id_input = attributes.get('id')
                            print(f"\n✓ Using app: {attributes.get('name')} (ID: {app_id_input})")
                            break
                
                if not app_id_input and isinstance(apps[0], dict):
                    attributes = apps[0].get('attributes', {})
                    app_id_input = attributes.get('id')
                    print(f"\n✓ Using first app: {attributes.get('name')} (ID: {app_id_input})")
            
            if not app_id_input:
                print("\n✗ No apps found. Please enter an app ID manually.")
                return
                
        except Exception as e:
            print(f"\n✗ Could not retrieve apps: {e}")
            print("Please enter an app ID manually.")
            return
    
    # Test WebSocket client
    print_section("Testing WebSocket Connection")
    
    try:
        ws_client = QlikWebSocketClient()
        print("✓ QlikWebSocketClient initialized")
    except Exception as e:
        print(f"✗ Failed to initialize client: {e}")
        return
    
    # Test 1: Get tables and fields
    print_section("Test 1: Getting Tables and Fields")
    try:
        result = ws_client.get_app_tables_simple(app_id_input)
        
        if result.get("success"):
            print("\n✓ Successfully retrieved app information!")
            print(f"\nApp Title: {result.get('app_title')}")
            print(f"\nSummary:")
            summary = result.get('summary', {})
            print(f"  - Tables: {summary.get('table_count', 0)}")
            print(f"  - Fields: {summary.get('total_fields', 0)}")
            print(f"  - Sheets: {summary.get('sheet_count', 0)}")
            print(f"  - Has Script: {summary.get('has_script', False)}")
            
            # Show tables
            tables = result.get('tables', [])
            if tables:
                print(f"\nTables found ({len(tables)}):")
                for i, table in enumerate(tables[:5], 1):  # Show first 5
                    print(f"\n  {i}. {table.get('name')}")
                    print(f"     - Fields: {table.get('field_count', 0)}")
                    print(f"     - Rows: {table.get('no_of_rows', 'N/A')}")
                    
                    # Show some fields
                    fields = table.get('fields', [])
                    if fields:
                        field_names = [f.get('name') for f in fields[:3]]
                        print(f"     - Sample fields: {', '.join(field_names)}")
                        if len(fields) > 3:
                            print(f"       ... and {len(fields) - 3} more")
                
                if len(tables) > 5:
                    print(f"\n  ... and {len(tables) - 5} more tables")
            
            # Show script info
            if summary.get('has_script'):
                script = result.get('script', '')
                print(f"\n\nScript Information:")
                print(f"  - Script length: {len(script)} characters")
                script_tables = result.get('script_tables', [])
                if script_tables:
                    print(f"  - Tables in script: {', '.join(script_tables[:5])}")
            
            # Show sheets
            sheets = result.get('sheets', [])
            if sheets:
                print(f"\n\nSheets found ({len(sheets)}):")
                for i, sheet in enumerate(sheets[:3], 1):  # Show first 3
                    print(f"  {i}. {sheet.get('title')}")
                    if sheet.get('description'):
                        print(f"     {sheet.get('description')}")
                
                if len(sheets) > 3:
                    print(f"  ... and {len(sheets) - 3} more sheets")
            
            # Save full result to file
            output_file = f"qlik_app_info_{app_id_input}.json"
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n✓ Full result saved to: {output_file}")
            
            # Ask if user wants to test field values
            print("\n" + "-"*80)
            fields = result.get('all_fields', [])
            if fields:
                print(f"\nFound {len(fields)} fields. Would you like to test field value retrieval? (y/n)")
                test_fields = input("> ").strip().lower()
                
                if test_fields == 'y':
                    # Show first few fields
                    print("\nAvailable fields:")
                    for i, field in enumerate(fields[:10], 1):
                        print(f"  {i}. {field.get('name')}")
                    
                    print("\nEnter field number to test (1-10) or field name:")
                    field_choice = input("> ").strip()
                    
                    field_name = None
                    if field_choice.isdigit() and 1 <= int(field_choice) <= min(10, len(fields)):
                        field_name = fields[int(field_choice) - 1].get('name')
                    else:
                        field_name = field_choice
                    
                    if field_name:
                        print_section(f"Test 2: Getting Values for Field '{field_name}'")
                        
                        try:
                            field_result = ws_client.get_field_values(app_id_input, field_name, limit=20)
                            
                            if field_result.get("success"):
                                print(f"\n✓ Successfully retrieved field values!")
                                values = field_result.get('values', [])
                                print(f"\nTotal values: {field_result.get('value_count', 0)}")
                                
                                if values:
                                    print(f"\nFirst {min(10, len(values))} values:")
                                    for i, value in enumerate(values[:10], 1):
                                        text = value.get('text', '')
                                        freq = value.get('frequency', '')
                                        print(f"  {i}. {text}" + (f" (frequency: {freq})" if freq else ""))
                                
                                # Save to file
                                field_file = f"qlik_field_{field_name.replace(' ', '_')}_{app_id_input}.json"
                                with open(field_file, 'w') as f:
                                    json.dump(field_result, f, indent=2)
                                print(f"\n✓ Field data saved to: {field_file}")
                            else:
                                print(f"\n✗ Failed: {field_result.get('error')}")
                        
                        except Exception as e:
                            print(f"\n✗ Error getting field values: {e}")
                            import traceback
                            traceback.print_exc()
        
        else:
            print(f"\n✗ Failed to retrieve app information")
            print(f"Error: {result.get('error')}")
            
    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    print_section("Testing Complete")
    print("\nResults summary:")
    print("  - Connection test: Completed")
    print("  - Data retrieval: Check output above")
    print("\nCheck the generated JSON files for complete results.")

if __name__ == "__main__":
    print("\n" + "="*80)
    print(" " * 25 + "Qlik WebSocket Test Script")
    print("="*80)
    
    test_websocket_connection()
    
    print("\n")