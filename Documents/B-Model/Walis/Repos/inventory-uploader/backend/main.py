import io
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery
import pandas as pd
from datetime import datetime

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React app's address
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to the Inventory Uploader API"}

@app.get("/ping")
async def ping():
    return {"ping": "pong"}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV file.")

    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        expected_cols = {"sku_id", "name", "stock", "last_updated"}
        if not expected_cols.issubset(df.columns):
            raise HTTPException(status_code=400, detail=f"CSV must contain columns: {expected_cols}")

        client = bigquery.Client(project="walis-inventory-mvp")
        table_id = "walis-inventory-mvp.warehouse_data.inventory"

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            autodetect=True,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )

        # Ingest the DataFrame into BigQuery
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()  # Wait for the job to complete

        return {"message": f"File '{file.filename}' uploaded and data ingested successfully."}

    except HTTPException as e:
        # Re-raise HTTP exceptions to let FastAPI handle them
        raise e
    except Exception as e:
        # Catch all other exceptions and return a 500 internal server error
        raise HTTPException(status_code=500, detail=f"Failed to ingest data to BigQuery: {e}")

@app.post("/calculate-stockouts")
async def calculate_stockouts():
    """
    Calculate stockouts by comparing inventory quantity_on_hand with sum of orders quantity.
    For every inventory.quantity_on_hand < sum(orders.quantity), it's a stockout.
    Store results in 'current_stockouts' table.
    """
    try:
        client = bigquery.Client(project="walis-inventory-mvp")
        
        # SQL query to calculate stockouts
        stockout_query = """
        WITH inventory_data AS (
            SELECT 
                sku_id,
                name,
                quantity_on_hand,
                last_updated
            FROM `walis-inventory-mvp.warehouse_data.inventory`
        ),
        orders_summary AS (
            SELECT 
                sku_id,
                SUM(quantity) as total_ordered_quantity
            FROM `walis-inventory-mvp.warehouse_data.orders`
            GROUP BY sku_id
        ),
        stockout_calculation AS (
            SELECT 
                i.sku_id,
                i.name,
                i.quantity_on_hand,
                COALESCE(o.total_ordered_quantity, 0) as total_ordered_quantity,
                (i.quantity_on_hand - COALESCE(o.total_ordered_quantity, 0)) as remaining_quantity,
                CASE 
                    WHEN i.quantity_on_hand < COALESCE(o.total_ordered_quantity, 0) THEN TRUE
                    ELSE FALSE
                END as is_stockout,
                i.last_updated,
                CURRENT_TIMESTAMP() as calculation_timestamp
            FROM inventory_data i
            LEFT JOIN orders_summary o ON i.sku_id = o.sku_id
        )
        SELECT 
            sku_id,
            name,
            quantity_on_hand,
            total_ordered_quantity,
            remaining_quantity,
            is_stockout,
            last_updated,
            calculation_timestamp
        FROM stockout_calculation
        WHERE is_stockout = TRUE
        ORDER BY remaining_quantity ASC
        """
        
        # Execute the query
        query_job = client.query(stockout_query)
        results = query_job.result()
        
        # Convert results to DataFrame
        stockout_data = []
        for row in results:
            stockout_data.append({
                'sku_id': row.sku_id,
                'name': row.name,
                'quantity_on_hand': row.quantity_on_hand,
                'total_ordered_quantity': row.total_ordered_quantity,
                'remaining_quantity': row.remaining_quantity,
                'is_stockout': row.is_stockout,
                'last_updated': row.last_updated,
                'calculation_timestamp': row.calculation_timestamp
            })
        
        if not stockout_data:
            return {
                "message": "No stockouts found. All inventory levels are sufficient for current orders.",
                "stockout_count": 0,
                "stockouts": []
            }
        
        # Create DataFrame and upload to BigQuery
        df = pd.DataFrame(stockout_data)
        
        # Define the stockout table
        stockout_table_id = "walis-inventory-mvp.warehouse_data.current_stockouts"
        
        # Configure job to overwrite the table (replace existing data)
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            autodetect=True,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # Replace existing data
        )
        
        # Upload stockout data to BigQuery
        job = client.load_table_from_dataframe(df, stockout_table_id, job_config=job_config)
        job.result()  # Wait for the job to complete
        
        return {
            "message": f"Stockout calculation completed successfully. {len(stockout_data)} items found to be out of stock.",
            "stockout_count": len(stockout_data),
            "stockouts": stockout_data,
            "table_updated": stockout_table_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate stockouts: {e}")

@app.get("/stockouts")
async def get_stockouts():
    """
    Retrieve current stockout data from the current_stockouts table.
    """
    try:
        client = bigquery.Client(project="walis-inventory-mvp")
        
        query = """
        SELECT 
            sku_id,
            name,
            quantity_on_hand,
            total_ordered_quantity,
            remaining_quantity,
            is_stockout,
            last_updated,
            calculation_timestamp
        FROM `walis-inventory-mvp.warehouse_data.current_stockouts`
        ORDER BY remaining_quantity ASC
        """
        
        query_job = client.query(query)
        results = query_job.result()
        
        stockouts = []
        for row in results:
            stockouts.append({
                'sku_id': row.sku_id,
                'name': row.name,
                'quantity_on_hand': row.quantity_on_hand,
                'total_ordered_quantity': row.total_ordered_quantity,
                'remaining_quantity': row.remaining_quantity,
                'is_stockout': row.is_stockout,
                'last_updated': row.last_updated,
                'calculation_timestamp': row.calculation_timestamp
            })
        
        return {
            "stockout_count": len(stockouts),
            "stockouts": stockouts
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stockouts: {e}") 