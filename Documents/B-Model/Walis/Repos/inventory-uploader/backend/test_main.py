import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import pandas as pd
import io

# Import the FastAPI app instance
from main import app

# Create a client for testing
client = TestClient(app)

@pytest.fixture
def mock_bigquery_client():
    """Mocks the BigQuery client."""
    with patch('main.bigquery.Client') as mock:
        yield mock

def test_upload_success(mock_bigquery_client):
    """Tests a successful file upload."""
    # Mock the BigQuery client instance and its methods
    mock_instance = MagicMock()
    mock_bigquery_client.return_value = mock_instance
    mock_instance.load_table_from_dataframe.return_value.result.return_value = None  # Simulate successful job

    # Create a dummy CSV file in memory
    csv_data = "sku_id,name,stock,last_updated\n1,test_item,10,2023-01-01\n"
    file_content = io.BytesIO(csv_data.encode('utf-8'))
    
    files = {'file': ('test.csv', file_content, 'text/csv')}
    
    response = client.post("/upload", files=files)
    
    assert response.status_code == 200
    assert response.json() == {"message": "File 'test.csv' uploaded and data ingested successfully."}
    
    # Verify that the BigQuery client was called correctly
    mock_instance.load_table_from_dataframe.assert_called_once()

def test_upload_wrong_file_type():
    """Tests uploading a non-CSV file."""
    file_content = io.BytesIO(b"this is not a csv")
    files = {'file': ('test.txt', file_content, 'text/plain')}
    
    response = client.post("/upload", files=files)
    
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]

def test_upload_missing_columns():
    """Tests a CSV missing required columns."""
    csv_data = "sku_id,name\n1,test_item\n" # Missing 'stock' and 'last_updated'
    file_content = io.BytesIO(csv_data.encode('utf-8'))
    
    files = {'file': ('test.csv', file_content, 'text/csv')}
    
    response = client.post("/upload", files=files)
    
    assert response.status_code == 400
    assert "must contain columns" in response.json()["detail"]

@patch('main.bigquery.Client')
def test_upload_bigquery_error(mock_bigquery_client):
    """Tests a failure during BigQuery ingestion."""
    # Configure the mock to raise an exception
    mock_instance = MagicMock()
    mock_bigquery_client.return_value = mock_instance
    mock_instance.load_table_from_dataframe.side_effect = Exception("BigQuery is down")

    csv_data = "sku_id,name,stock,last_updated\n1,test_item,10,2023-01-01\n"
    file_content = io.BytesIO(csv_data.encode('utf-8'))
    
    files = {'file': ('test.csv', file_content, 'text/csv')}
    
    response = client.post("/upload", files=files)
    
    assert response.status_code == 500
    assert "Failed to ingest data to BigQuery: BigQuery is down" in response.json()["detail"] 