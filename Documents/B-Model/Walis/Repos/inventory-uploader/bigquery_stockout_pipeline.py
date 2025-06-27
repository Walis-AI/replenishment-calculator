#!/usr/bin/env python3
"""
BigQuery Stockout and Shorted Orders Pipeline

This script:
1. Fetches inventory and order data from BigQuery
2. Calculates current stockouts and shorted orders
3. Uploads results back to BigQuery for UI consumption
"""

import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
import logging
from datetime import datetime
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BigQueryStockoutPipeline:
    def __init__(self, project_id, dataset_id):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = bigquery.Client(project=project_id)
        
    def fetch_inventory_data(self):
        """Fetch inventory data from BigQuery"""
        try:
            query = f"""
            SELECT 
                `Snapshot Date`,
                SKU,
                Site,
                `Qty On Hand`,
                UOM
            FROM `{self.project_id}.{self.dataset_id}.inventory_data`
            ORDER BY SKU, Site
            """
            
            logger.info("Fetching inventory data from BigQuery...")
            df = self.client.query(query).to_dataframe()
            logger.info(f"Retrieved {len(df)} inventory records")
            return df
            
        except GoogleCloudError as e:
            logger.error(f"Error fetching inventory data: {e}")
            raise
    
    def fetch_order_data(self):
        """Fetch order data from BigQuery"""
        try:
            query = f"""
            SELECT 
                `Order Date`,
                SKU,
                `Order ID`,
                `Qty Ordered`,
                Site,
                UOM,
                `Late Ship Date`
            FROM `{self.project_id}.{self.dataset_id}.open_order_data`
            ORDER BY `Late Ship Date`, `Order Date`, SKU
            """
            
            logger.info("Fetching order data from BigQuery...")
            df = self.client.query(query).to_dataframe()
            logger.info(f"Retrieved {len(df)} order records")
            return df
            
        except GoogleCloudError as e:
            logger.error(f"Error fetching order data: {e}")
            raise
    
    def calculate_stockouts_and_shorted_orders(self, inventory_df, orders_df):
        """Calculate stockouts and shorted orders"""
        logger.info("Calculating stockouts and shorted orders...")
        
        # Create a copy of inventory for tracking
        current_inventory = inventory_df.copy()
        current_inventory = current_inventory.set_index(['SKU', 'Site'])
        
        # Sort orders by late ship date (earliest first)
        orders_sorted = orders_df.sort_values('Late Ship Date').copy()
        
        stockouts = []
        shorted_orders = []
        
        # Process each order
        for _, order in orders_sorted.iterrows():
            sku = order['SKU']
            site = order['Site']
            qty_ordered = order['Qty Ordered']
            order_id = order['Order ID']
            
            # Check if we have inventory for this SKU/Site
            if (sku, site) in current_inventory.index:
                available_qty = current_inventory.loc[(sku, site), 'Qty On Hand']
                
                if available_qty >= qty_ordered:
                    # Full fulfillment
                    current_inventory.loc[(sku, site), 'Qty On Hand'] -= qty_ordered
                else:
                    # Partial fulfillment - record stockout
                    fulfilled_qty = available_qty
                    shorted_qty = qty_ordered - available_qty
                    
                    # Record stockout
                    stockouts.append({
                        'SKU': sku,
                        'Site': site,
                        'Stockout_Date': order['Late Ship Date'],
                        'Qty_Short': shorted_qty,
                        'UOM': order['UOM'],
                        'Triggering_Order_ID': order_id
                    })
                    
                    # Record shorted order
                    shorted_orders.append({
                        'Order_ID': order_id,
                        'SKU': sku,
                        'Site': site,
                        'Qty_Ordered': qty_ordered,
                        'Qty_Fulfilled': fulfilled_qty,
                        'Qty_Shorted': shorted_qty,
                        'UOM': order['UOM'],
                        'Order_Date': order['Order Date'],
                        'Late_Ship_Date': order['Late Ship Date']
                    })
                    
                    # Set inventory to 0
                    current_inventory.loc[(sku, site), 'Qty On Hand'] = 0
            else:
                # No inventory for this SKU/Site - complete stockout
                stockouts.append({
                    'SKU': sku,
                    'Site': site,
                    'Stockout_Date': order['Late Ship Date'],
                    'Qty_Short': qty_ordered,
                    'UOM': order['UOM'],
                    'Triggering_Order_ID': order_id
                })
                
                shorted_orders.append({
                    'Order_ID': order_id,
                    'SKU': sku,
                    'Site': site,
                    'Qty_Ordered': qty_ordered,
                    'Qty_Fulfilled': 0,
                    'Qty_Shorted': qty_ordered,
                    'UOM': order['UOM'],
                    'Order_Date': order['Order Date'],
                    'Late_Ship_Date': order['Late Ship Date']
                })
        
        # Convert to DataFrames
        stockouts_df = pd.DataFrame(stockouts)
        shorted_orders_df = pd.DataFrame(shorted_orders)
        
        logger.info(f"Calculated {len(stockouts_df)} stockouts and {len(shorted_orders_df)} shorted orders")
        
        return stockouts_df, shorted_orders_df
    
    def upload_results_to_bigquery(self, stockouts_df, shorted_orders_df):
        """Upload results back to BigQuery"""
        try:
            # Upload stockouts
            if not stockouts_df.empty:
                table_id = f"{self.project_id}.{self.dataset_id}.calculated_stockouts"
                job_config = bigquery.LoadJobConfig(
                    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                    schema=[
                        bigquery.SchemaField("SKU", "STRING"),
                        bigquery.SchemaField("Site", "STRING"),
                        bigquery.SchemaField("Stockout_Date", "DATE"),
                        bigquery.SchemaField("Qty_Short", "INTEGER"),
                        bigquery.SchemaField("UOM", "STRING"),
                        bigquery.SchemaField("Triggering_Order_ID", "STRING")
                    ]
                )
                
                logger.info("Uploading stockouts to BigQuery...")
                job = self.client.load_table_from_dataframe(
                    stockouts_df, table_id, job_config=job_config
                )
                job.result()
                logger.info(f"Uploaded {len(stockouts_df)} stockout records")
            
            # Upload shorted orders
            if not shorted_orders_df.empty:
                table_id = f"{self.project_id}.{self.dataset_id}.calculated_shorted_orders"
                job_config = bigquery.LoadJobConfig(
                    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                    schema=[
                        bigquery.SchemaField("Order_ID", "STRING"),
                        bigquery.SchemaField("SKU", "STRING"),
                        bigquery.SchemaField("Site", "STRING"),
                        bigquery.SchemaField("Qty_Ordered", "INTEGER"),
                        bigquery.SchemaField("Qty_Fulfilled", "INTEGER"),
                        bigquery.SchemaField("Qty_Shorted", "INTEGER"),
                        bigquery.SchemaField("UOM", "STRING"),
                        bigquery.SchemaField("Order_Date", "DATE"),
                        bigquery.SchemaField("Late_Ship_Date", "DATE")
                    ]
                )
                
                logger.info("Uploading shorted orders to BigQuery...")
                job = self.client.load_table_from_dataframe(
                    shorted_orders_df, table_id, job_config=job_config
                )
                job.result()
                logger.info(f"Uploaded {len(shorted_orders_df)} shorted order records")
                
        except GoogleCloudError as e:
            logger.error(f"Error uploading results to BigQuery: {e}")
            raise
    
    def run_pipeline(self):
        """Run the complete pipeline"""
        try:
            logger.info("Starting BigQuery Stockout Pipeline...")
            
            # Step 1: Fetch data
            inventory_df = self.fetch_inventory_data()
            orders_df = self.fetch_order_data()
            
            # Step 2: Calculate results
            stockouts_df, shorted_orders_df = self.calculate_stockouts_and_shorted_orders(
                inventory_df, orders_df
            )
            
            # Step 3: Upload results
            self.upload_results_to_bigquery(stockouts_df, shorted_orders_df)
            
            logger.info("Pipeline completed successfully!")
            
            # Print summary
            print(f"\n📊 Pipeline Summary:")
            print(f"   • Inventory records processed: {len(inventory_df)}")
            print(f"   • Order records processed: {len(orders_df)}")
            print(f"   • Stockouts calculated: {len(stockouts_df)}")
            print(f"   • Shorted orders calculated: {len(shorted_orders_df)}")
            print(f"   • Results uploaded to BigQuery dataset: {self.dataset_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            return False

def main():
    """Main function"""
    # Configuration
    PROJECT_ID = "walis-inventory-mvp"
    DATASET_ID = "Sample_inventory_management_dataset"
    
    # Create and run pipeline
    pipeline = BigQueryStockoutPipeline(PROJECT_ID, DATASET_ID)
    success = pipeline.run_pipeline()
    
    if success:
        print("\n✅ Pipeline completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Pipeline failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 