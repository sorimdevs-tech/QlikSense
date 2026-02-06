#!/usr/bin/env python
"""
Test script for Summary Generation Endpoints
Tests the integration between summary_utils.py and main.py
"""

import requests
import json
from typing import Dict, List, Any

BASE_URL = "http://localhost:8000"

# Sample test data
SALES_DATA = [
    {"product": "Laptop", "category": "Electronics", "sales": 5000, "region": "North"},
    {"product": "Mouse", "category": "Accessories", "sales": 500, "region": "North"},
    {"product": "Monitor", "category": "Electronics", "sales": 2000, "region": "South"},
    {"product": "Keyboard", "category": "Accessories", "sales": 800, "region": "South"},
    {"product": "Laptop", "category": "Electronics", "sales": 5000, "region": "East"},
]

INVENTORY_DATA = [
    {"item": "Laptop", "stock": 50, "reorder_level": 20},
    {"item": "Mouse", "stock": 200, "reorder_level": 50},
    {"item": "Monitor", "stock": 30, "reorder_level": 15},
    {"item": "Keyboard", "stock": 100, "reorder_level": 40},
]

QUALITY_TEST_DATA = [
    {"product": "A", "sales": 1000, "region": "North"},
    {"product": "B", "sales": None, "region": "South"},
    {"product": None, "sales": 1500, "region": "East"},
    {"product": "D", "sales": 2000, "region": "West"},
]


def test_single_table_summary():
    """Test POST /summary/table endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Single Table Summary")
    print("="*60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/summary/table",
            json={
                "table_name": "Sales Data",
                "data": SALES_DATA
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS")
            print(f"\nTable Name: {result['table_name']}")
            print(f"Rows: {result['row_count']}, Columns: {result['column_count']}")
            print(f"Quality Score: {result['data_quality_score']}")
            print(f"\nMetrics:")
            for key, value in result['metrics'].items():
                if isinstance(value, dict):
                    print(f"  {key}: {json.dumps(value, indent=2)}")
                else:
                    print(f"  {key}: {value}")
            print(f"\nSummary:\n{result['summary_text']}")
            return True
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False


def test_batch_summary():
    """Test POST /summary/batch endpoint"""
    print("\n" + "="*60)
    print("TEST 2: Batch Summary (Multiple Tables)")
    print("="*60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/summary/batch",
            json={
                "tables": {
                    "Sales": SALES_DATA,
                    "Inventory": INVENTORY_DATA
                }
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS")
            print(f"\nTotal Tables: {result['total_tables']}")
            
            for table_name, summary in result['summaries'].items():
                if summary['success']:
                    print(f"\n📊 {table_name}:")
                    print(f"   Rows: {summary['row_count']}, Quality: {summary['data_quality_score']}")
                else:
                    print(f"\n❌ {table_name}: {summary.get('error', 'Unknown error')}")
            
            return True
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False


def test_summary_text():
    """Test POST /summary/text endpoint"""
    print("\n" + "="*60)
    print("TEST 3: Summary Text Only")
    print("="*60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/summary/text",
            json={
                "table_name": "Sales Summary",
                "data": SALES_DATA
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS")
            print(f"\n{result['summary']}")
            return True
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False


def test_data_quality():
    """Test POST /summary/quality endpoint"""
    print("\n" + "="*60)
    print("TEST 4: Data Quality Check")
    print("="*60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/summary/quality",
            json={
                "table_name": "Quality Test Data",
                "data": QUALITY_TEST_DATA
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS")
            print(f"\nTable: {result['table_name']}")
            print(f"Total Rows: {result['total_rows']}")
            print(f"Total Columns: {result['total_columns']}")
            print(f"Quality Score: {result['quality_score']}%")
            print(f"\nMissing Values Analysis:")
            for col, info in result['missing_values'].items():
                print(f"  {col}: {info['count']} missing ({info['percentage']}%)")
            return True
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False


def run_all_tests():
    """Run all test endpoints"""
    print("\n" + "="*60)
    print("SUMMARY ENDPOINTS TEST SUITE")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    
    # Check if server is running
    try:
        requests.get(f"{BASE_URL}/health", timeout=5)
    except requests.ConnectionError:
        print("\n❌ ERROR: Cannot connect to FastAPI server")
        print("Make sure the server is running:")
        print("  cd qlik_app/qlik/qlik-fastapi-backend")
        print("  python -m uvicorn main:app --reload")
        return False
    
    print("\n✅ Server is running\n")
    
    results = []
    results.append(("Single Table Summary", test_single_table_summary()))
    results.append(("Batch Summary", test_batch_summary()))
    results.append(("Summary Text", test_summary_text()))
    results.append(("Data Quality", test_data_quality()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    import sys
    
    print("\n" + "="*60)
    print("SUMMARY GENERATION ENDPOINTS - TEST SCRIPT")
    print("="*60)
    print("\nBefore running tests, ensure the FastAPI server is running:")
    print("  cd d:\\qliksensecloud\\qlikSense-Accellarater\\qlik_app\\qlik\\qlik-fastapi-backend")
    print("  python -m uvicorn main:app --reload")
    print("\nPress Enter to continue...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\nTest cancelled.")
        sys.exit(1)
    
    success = run_all_tests()
    sys.exit(0 if success else 1)
