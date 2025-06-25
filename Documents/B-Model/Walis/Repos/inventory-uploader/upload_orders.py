#!/usr/bin/env python3
"""
Script to upload sample orders data to BigQuery for testing stockout calculations
"""

import pandas as pd
from google.cloud import bigquery
import os

def upload_orders_to_bigquery():
    """Upload sample orders data to BigQuery"""
    try:
        # Read the sample orders CSV
        orders_df = pd.read_csv('sample_orders.csv')
        print(f"📊 Loaded {len(orders_df)} orders from sample_orders.csv")
        
        # Initialize BigQuery client
        client = bigquery.Client(project="walis-inventory-mvp")
        
        # Define the orders table
        orders_table_id = "walis-inventory-mvp.warehouse_data.orders"
        
        # Configure job to append data
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            autodetect=True,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )
        
        print("🔄 Uploading orders data to BigQuery...")
        
        # Upload the DataFrame to BigQuery
        job = client.load_table_from_dataframe(orders_df, orders_table_id, job_config=job_config)
        job.result()  # Wait for the job to complete
        
        print(f"✅ Orders data uploaded successfully to {orders_table_id}")
        print(f"📈 Total orders uploaded: {len(orders_df)}")
        
        # Show summary of orders by SKU
        print("\n📋 Orders Summary by SKU:")
        sku_summary = orders_df.groupby('sku_id')['quantity'].sum().sort_values(ascending=False)
        for sku_id, total_quantity in sku_summary.items():
            print(f"  {sku_id}: {total_quantity} units ordered")
        
        return True
        
    except Exception as e:
        print(f"❌ Error uploading orders data: {e}")
        return False

def main():
    """Main function"""
    print("📦 Uploading Sample Orders Data to BigQuery")
    print("=" * 50)
    
    if upload_orders_to_bigquery():
        print("\n✅ Orders upload completed successfully!")
        print("\n💡 Next steps:")
        print("  1. Make sure your inventory data is also in BigQuery")
        print("  2. Run the stockout calculation: python test_stockout.py")
    else:
        print("\n❌ Orders upload failed. Check the error message above.")

if __name__ == "__main__":
    main() 