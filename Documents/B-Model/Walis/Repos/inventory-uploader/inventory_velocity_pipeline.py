#!/usr/bin/env python3
"""
Inventory Velocity and Forecasting Pipeline

This script calculates:
1. velocity_value: Average velocity of consumption per day
2. velocity_category: High, Medium, Low velocity categories
3. predicted_stockout_date: Predicted date when inventory will be depleted
4. urgency: High, Medium, Low urgency levels
5. recommended_reorder_quantity: Recommended reorder quantity
6. optimal_reorder_date: Optimal date to place purchase order

Assumptions:
- Lead_Time_Days: 5 days (PO approval to stock arrival)
- Safety_Stock_Days: 2 days (buffer for variability)
- Forecast_Horizon_Days: 14 days (how far ahead to be stocked)
"""

import pandas as pd
import numpy as np
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
import logging
from datetime import datetime, timedelta
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InventoryVelocityPipeline:
    def __init__(self, project_id, dataset_id):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = bigquery.Client(project=project_id)
        
        # Configuration parameters
        self.lead_time_days = 5
        self.safety_stock_days = 2
        self.forecast_horizon_days = 14
        self.velocity_window_days = 7  # For moving average calculation
        
    def fetch_historic_fulfillment_data(self):
        """Fetch historic order fulfillment data from BigQuery"""
        try:
            query = f"""
            SELECT 
                Date,
                SKU as Sku_Id,
                Customer,
                `Qty Ordered` as Quantity_ordered,
                `Qty Picked` as Quantity_fulfilled,
                `Order ID` as Order_Id,
                Carrier as carrier,
                Site,
                UOM
            FROM `{self.project_id}.{self.dataset_id}.historic_fulfillment_data`
            ORDER BY SKU, Date
            """
            
            logger.info("Fetching historic fulfillment data from BigQuery...")
            job_config = bigquery.QueryJobConfig(use_legacy_sql=False)
            df = self.client.query(query, job_config=job_config).to_dataframe()
            logger.info(f"Retrieved {len(df)} historic fulfillment records")
            return df
            
        except GoogleCloudError as e:
            logger.error(f"Error fetching historic fulfillment data: {e}")
            raise
    
    def fetch_inventory_data(self):
        """Fetch current inventory data from BigQuery"""
        try:
            query = f"""
            SELECT 
                `Snapshot Date`,
                SKU as Sku_Id,
                Site,
                `Qty On Hand` as Quantity_On_Hand,
                UOM
            FROM `{self.project_id}.{self.dataset_id}.inventory_data`
            ORDER BY SKU, Site
            """
            
            logger.info("Fetching inventory data from BigQuery...")
            job_config = bigquery.QueryJobConfig(use_legacy_sql=False)
            df = self.client.query(query, job_config=job_config).to_dataframe()
            logger.info(f"Retrieved {len(df)} inventory records")
            return df
            
        except GoogleCloudError as e:
            logger.error(f"Error fetching inventory data: {e}")
            raise
    
    def calculate_velocity_values(self, historic_df):
        """Calculate velocity values using weighted moving average"""
        logger.info("Calculating velocity values...")
        
        # Group by Date and Sku_Id, sum Quantity_fulfilled
        daily_consumption = (
            historic_df.groupby(['Date', 'Sku_Id'])['Quantity_fulfilled']
            .sum()
            .reset_index()
            .sort_values(['Sku_Id', 'Date'])
        )
        
        # Calculate moving average per SKU
        daily_consumption['avg_7d'] = (
            daily_consumption.groupby('Sku_Id')['Quantity_fulfilled']
            .transform(lambda x: x.rolling(window=self.velocity_window_days, min_periods=1).mean())
        )
        
        # Calculate average velocity per SKU (latest moving average)
        velocity_values = (
            daily_consumption.groupby('Sku_Id')['avg_7d']
            .last()
            .reset_index()
            .rename(columns={'avg_7d': 'velocity_value'})
        )
        
        logger.info(f"Calculated velocity values for {len(velocity_values)} SKUs")
        return velocity_values, daily_consumption
    
    def categorize_velocity(self, velocity_values):
        """Categorize velocity into High, Medium, Low based on velocity value ranges"""
        logger.info("Categorizing velocity values...")
        
        # Get min and max velocity values
        min_velocity = velocity_values['velocity_value'].min()
        max_velocity = velocity_values['velocity_value'].max()
        velocity_range = max_velocity - min_velocity
        
        # Calculate range boundaries
        low_max = min_velocity + (0.3 * velocity_range)  # Bottom 30% of range
        medium_max = min_velocity + (0.8 * velocity_range)  # Bottom 80% of range (30% + 50%)
        
        logger.info(f"Velocity range: {min_velocity:.2f} to {max_velocity:.2f}")
        logger.info(f"LOW range: {min_velocity:.2f} to {low_max:.2f}")
        logger.info(f"MEDIUM range: {low_max:.2f} to {medium_max:.2f}")
        logger.info(f"HIGH range: {medium_max:.2f} to {max_velocity:.2f}")
        
        # Create velocity categories based on velocity value ranges
        velocity_categories = []
        for _, row in velocity_values.iterrows():
            velocity_value = row['velocity_value']
            
            if velocity_value <= low_max:
                category = 'LOW'
            elif velocity_value <= medium_max:
                category = 'MEDIUM'
            else:
                category = 'HIGH'
            
            velocity_categories.append({
                'Sku_Id': row['Sku_Id'],
                'velocity_value': velocity_value,
                'velocity_category': category
            })
        
        return pd.DataFrame(velocity_categories)
    
    def predict_stockout_dates(self, inventory_df, daily_consumption):
        """Predict stockout dates based on current inventory and consumption patterns"""
        logger.info("Predicting stockout dates...")
        
        predicted_stockouts = []
        
        for _, inventory_row in inventory_df.iterrows():
            sku = inventory_row['Sku_Id']
            current_inventory = inventory_row['Quantity_On_Hand']
            
            # Get consumption forecast for this SKU
            sku_consumption = daily_consumption[daily_consumption['Sku_Id'] == sku].copy()
            
            if sku_consumption.empty:
                # No historic data, skip
                continue
            
            # Sort by date and get latest forecast
            sku_consumption = sku_consumption.sort_values('Date')
            latest_forecast = sku_consumption['avg_7d'].iloc[-1]
            
            if latest_forecast <= 0:
                # No consumption, no stockout predicted
                continue
            
            # Calculate days until stockout
            days_to_stockout = current_inventory / latest_forecast
            
            # Calculate predicted stockout date
            latest_date = sku_consumption['Date'].max()
            predicted_stockout_date = latest_date + timedelta(days=days_to_stockout)
            
            predicted_stockouts.append({
                'Sku_Id': sku,
                'current_inventory': current_inventory,
                'daily_consumption_rate': latest_forecast,
                'days_to_stockout': days_to_stockout,
                'predicted_stockout_date': predicted_stockout_date
            })
        
        return pd.DataFrame(predicted_stockouts)
    
    def calculate_urgency(self, predicted_stockouts):
        """Calculate urgency levels based on predicted stockout date and lead time"""
        logger.info("Calculating urgency levels...")
        
        urgency_levels = []
        
        for _, row in predicted_stockouts.iterrows():
            stockout_date = row['predicted_stockout_date']
            today = datetime.now().date()
            
            # Calculate days until stockout
            days_until_stockout = (stockout_date - today).days
            
            # Calculate days available after lead time
            days_after_lead_time = days_until_stockout - self.lead_time_days
            
            # Determine urgency
            if days_after_lead_time < 4:
                urgency = 'HIGH'
            elif days_after_lead_time < 10:
                urgency = 'MEDIUM'
            elif days_after_lead_time < 30:
                urgency = 'LOW'
            else:
                urgency = 'LOW'  # More than 30 days
            
            urgency_levels.append({
                'Sku_Id': row['Sku_Id'],
                'days_until_stockout': days_until_stockout,
                'days_after_lead_time': days_after_lead_time,
                'urgency': urgency
            })
        
        return pd.DataFrame(urgency_levels)
    
    def calculate_reorder_recommendations(self, predicted_stockouts, velocity_categories):
        """Calculate reorder recommendations"""
        logger.info("Calculating reorder recommendations...")
        
        reorder_recommendations = []
        
        for _, row in predicted_stockouts.iterrows():
            sku = row['Sku_Id']
            stockout_date = row['predicted_stockout_date']
            current_inventory = row['current_inventory']
            daily_consumption_rate = row['daily_consumption_rate']
            
            # Get velocity category
            velocity_info = velocity_categories[velocity_categories['Sku_Id'] == sku]
            velocity_category = velocity_info['velocity_category'].iloc[0] if not velocity_info.empty else 'MEDIUM'
            
            # Calculate optimal reorder date
            optimal_reorder_date = stockout_date - timedelta(
                days=self.lead_time_days + self.safety_stock_days
            )
            
            # Calculate recommended reorder quantity
            recommended_qty = max(0, int(
                (daily_consumption_rate * self.forecast_horizon_days) - current_inventory
            ))
            
            reorder_recommendations.append({
                'Sku_Id': sku,
                'velocity_category': velocity_category,
                'predicted_stockout_date': stockout_date,
                'optimal_reorder_date': optimal_reorder_date,
                'recommended_reorder_quantity': recommended_qty,
                'current_inventory': current_inventory,
                'daily_consumption_rate': daily_consumption_rate
            })
        
        return pd.DataFrame(reorder_recommendations)
    
    def merge_all_results(self, velocity_categories, predicted_stockouts, urgency_levels, reorder_recommendations):
        """Merge all results into a comprehensive output"""
        logger.info("Merging all results...")
        
        # Start with velocity categories
        final_results = velocity_categories.copy()
        
        # Add predicted stockout information
        final_results = final_results.merge(
            predicted_stockouts[['Sku_Id', 'predicted_stockout_date', 'current_inventory', 'daily_consumption_rate']],
            on='Sku_Id',
            how='left'
        )
        
        # Add urgency levels
        final_results = final_results.merge(
            urgency_levels[['Sku_Id', 'urgency']],
            on='Sku_Id',
            how='left'
        )
        
        # Add reorder recommendations
        final_results = final_results.merge(
            reorder_recommendations[['Sku_Id', 'optimal_reorder_date', 'recommended_reorder_quantity']],
            on='Sku_Id',
            how='left'
        )
        
        return final_results
    
    def upload_results_to_bigquery(self, final_results):
        """Upload results back to BigQuery"""
        try:
            table_id = f"{self.project_id}.{self.dataset_id}.inventory_velocity_analysis"
            job_config = bigquery.LoadJobConfig(
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                schema=[
                    bigquery.SchemaField("Sku_Id", "STRING"),
                    bigquery.SchemaField("velocity_value", "FLOAT"),
                    bigquery.SchemaField("velocity_category", "STRING"),
                    bigquery.SchemaField("predicted_stockout_date", "DATE"),
                    bigquery.SchemaField("urgency", "STRING"),
                    bigquery.SchemaField("optimal_reorder_date", "DATE"),
                    bigquery.SchemaField("recommended_reorder_quantity", "INTEGER"),
                    bigquery.SchemaField("current_inventory", "INTEGER"),
                    bigquery.SchemaField("daily_consumption_rate", "FLOAT")
                ]
            )
            
            logger.info("Uploading inventory velocity analysis to BigQuery...")
            job = self.client.load_table_from_dataframe(
                final_results, table_id, job_config=job_config
            )
            job.result()
            logger.info(f"Uploaded {len(final_results)} inventory velocity records")
                
        except GoogleCloudError as e:
            logger.error(f"Error uploading results to BigQuery: {e}")
            raise
    
    def run_pipeline(self):
        """Run the complete inventory velocity pipeline"""
        try:
            logger.info("Starting Inventory Velocity Pipeline...")
            
            # Step 1: Fetch data
            historic_df = self.fetch_historic_fulfillment_data()
            inventory_df = self.fetch_inventory_data()
            
            # Step 2: Calculate velocity values
            velocity_values, daily_consumption = self.calculate_velocity_values(historic_df)
            
            # Step 3: Categorize velocity
            velocity_categories = self.categorize_velocity(velocity_values)
            
            # Step 4: Predict stockout dates
            predicted_stockouts = self.predict_stockout_dates(inventory_df, daily_consumption)
            
            # Step 5: Calculate urgency levels
            urgency_levels = self.calculate_urgency(predicted_stockouts)
            
            # Step 6: Calculate reorder recommendations
            reorder_recommendations = self.calculate_reorder_recommendations(
                predicted_stockouts, velocity_categories
            )
            
            # Step 7: Merge all results
            final_results = self.merge_all_results(
                velocity_categories, predicted_stockouts, urgency_levels, reorder_recommendations
            )
            
            # Step 8: Upload results
            self.upload_results_to_bigquery(final_results)
            
            logger.info("Pipeline completed successfully!")
            
            # Print summary
            print(f"\n📊 Inventory Velocity Pipeline Summary:")
            print(f"   • Historic fulfillment records processed: {len(historic_df)}")
            print(f"   • Inventory records processed: {len(inventory_df)}")
            print(f"   • SKUs analyzed: {len(final_results)}")
            print(f"   • High velocity SKUs: {len(final_results[final_results['velocity_category'] == 'HIGH'])}")
            print(f"   • Medium velocity SKUs: {len(final_results[final_results['velocity_category'] == 'MEDIUM'])}")
            print(f"   • Low velocity SKUs: {len(final_results[final_results['velocity_category'] == 'LOW'])}")
            print(f"   • High urgency SKUs: {len(final_results[final_results['urgency'] == 'HIGH'])}")
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
    pipeline = InventoryVelocityPipeline(PROJECT_ID, DATASET_ID)
    success = pipeline.run_pipeline()
    
    if success:
        print("\n✅ Inventory Velocity Pipeline completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Inventory Velocity Pipeline failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 