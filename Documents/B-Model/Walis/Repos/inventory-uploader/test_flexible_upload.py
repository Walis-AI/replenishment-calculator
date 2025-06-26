#!/usr/bin/env python3
"""
Test script to demonstrate flexible inventory upload with different column structures
"""

import requests
import json
import os

def test_upload_with_different_structure():
    """Test uploading inventory with different column structure"""
    
    # Test 1: Upload with auto-detection (should work)
    print("🧪 Test 1: Auto-detection with different column names")
    
    files = {
        'file': ('sample_inventory_different_structure.csv', 
                open('sample_inventory_different_structure.csv', 'rb'), 
                'text/csv')
    }
    
    try:
        response = requests.post('http://localhost:8000/upload', files=files)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print("✅ Auto-detection should work for this file\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")
    
    # Test 2: Upload with explicit column mapping
    print("🧪 Test 2: Explicit column mapping")
    
    # Create a CSV with completely different column names
    custom_csv_content = """item_code,product_title,available_qty,modified_date,extra_field
ITEM001,Test Product 1,100,2024-06-19,extra_data
ITEM002,Test Product 2,50,2024-06-18,extra_data
ITEM003,Test Product 3,75,2024-06-17,extra_data"""
    
    with open('custom_structure.csv', 'w') as f:
        f.write(custom_csv_content)
    
    files = {
        'file': ('custom_structure.csv', 
                open('custom_structure.csv', 'rb'), 
                'text/csv')
    }
    
    # Define explicit column mapping
    column_mapping = {
        'item_code': 'sku_id',
        'product_title': 'name', 
        'available_qty': 'stock',
        'modified_date': 'last_updated'
    }
    
    data = {
        'column_mapping': json.dumps(column_mapping)
    }
    
    try:
        response = requests.post('http://localhost:8000/upload', files=files, data=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print("✅ Explicit mapping should work\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")
    
    # Test 3: Upload with missing required columns (should fail gracefully)
    print("🧪 Test 3: Missing required columns")
    
    incomplete_csv_content = """product_id,product_name
PROD001,Product A
PROD002,Product B"""
    
    with open('incomplete_structure.csv', 'w') as f:
        f.write(incomplete_csv_content)
    
    files = {
        'file': ('incomplete_structure.csv', 
                open('incomplete_structure.csv', 'rb'), 
                'text/csv')
    }
    
    try:
        response = requests.post('http://localhost:8000/upload', files=files)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print("✅ Should return available columns for mapping\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")
    
    # Cleanup
    for filename in ['custom_structure.csv', 'incomplete_structure.csv']:
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    print("🚀 Testing Flexible Inventory Upload")
    print("=" * 50)
    test_upload_with_different_structure()
    print("✅ Testing completed!") 