#!/usr/bin/env python3
"""
Test script for stockout calculation functionality
"""

import requests
import json
import time

# API base URL
BASE_URL = "http://localhost:8000"

def test_ping():
    """Test if the API is running"""
    try:
        response = requests.get(f"{BASE_URL}/ping")
        if response.status_code == 200:
            print("✅ API is running")
            return True
        else:
            print(f"❌ API ping failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Make sure the backend is running on port 8000")
        return False

def test_calculate_stockouts():
    """Test the stockout calculation endpoint"""
    try:
        print("\n🔄 Calculating stockouts...")
        response = requests.post(f"{BASE_URL}/calculate-stockouts")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Stockout calculation successful!")
            print(f"📊 Stockout count: {data.get('stockout_count', 0)}")
            print(f"💾 Table updated: {data.get('table_updated', 'N/A')}")
            
            if data.get('stockouts'):
                print("\n📋 Stockout Details:")
                for i, stockout in enumerate(data['stockouts'][:5], 1):  # Show first 5
                    print(f"  {i}. SKU: {stockout['sku_id']} - {stockout['name']}")
                    print(f"     Inventory: {stockout['quantity_on_hand']}, Orders: {stockout['total_ordered_quantity']}")
                    print(f"     Remaining: {stockout['remaining_quantity']}")
            else:
                print("✅ No stockouts found - all inventory levels are sufficient!")
            
            return True
        else:
            print(f"❌ Stockout calculation failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing stockout calculation: {e}")
        return False

def test_get_stockouts():
    """Test retrieving stockout data"""
    try:
        print("\n🔄 Retrieving stockout data...")
        response = requests.get(f"{BASE_URL}/stockouts")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Stockout retrieval successful!")
            print(f"📊 Stockout count: {data.get('stockout_count', 0)}")
            
            if data.get('stockouts'):
                print("\n📋 Current Stockouts:")
                for i, stockout in enumerate(data['stockouts'][:5], 1):  # Show first 5
                    print(f"  {i}. SKU: {stockout['sku_id']} - {stockout['name']}")
                    print(f"     Inventory: {stockout['quantity_on_hand']}, Orders: {stockout['total_ordered_quantity']}")
                    print(f"     Remaining: {stockout['remaining_quantity']}")
                    print(f"     Calculated: {stockout['calculation_timestamp']}")
            else:
                print("✅ No stockouts in database")
            
            return True
        else:
            print(f"❌ Stockout retrieval failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing stockout retrieval: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Stockout Calculation Functionality")
    print("=" * 50)
    
    # Test 1: Check if API is running
    if not test_ping():
        print("\n❌ API is not running. Please start the backend first.")
        return
    
    # Test 2: Calculate stockouts
    if test_calculate_stockouts():
        # Test 3: Retrieve stockouts
        test_get_stockouts()
    else:
        print("\n❌ Stockout calculation failed. Check the backend logs for errors.")
    
    print("\n" + "=" * 50)
    print("🏁 Testing completed!")

if __name__ == "__main__":
    main() 