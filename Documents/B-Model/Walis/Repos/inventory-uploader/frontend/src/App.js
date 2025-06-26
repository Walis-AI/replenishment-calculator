import React, { useState, useEffect } from 'react';

function App() {
  const [file, setFile] = useState(null);
  const [fileType, setFileType] = useState('inventory');
  const [uploadStatus, setUploadStatus] = useState('');
  const [columnMapping, setColumnMapping] = useState({});
  const [availableColumns, setAvailableColumns] = useState([]);
  const [showMapping, setShowMapping] = useState(false);
  const [previewData, setPreviewData] = useState(null);

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    setFile(selectedFile);
    
    if (selectedFile && selectedFile.name.endsWith('.csv')) {
      // Preview the CSV to show available columns
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target.result;
        const lines = text.split('\n');
        if (lines.length > 0) {
          const columns = lines[0].split(',').map(col => col.trim());
          setAvailableColumns(columns);
          
          // Show first few rows as preview
          const previewRows = lines.slice(1, 4).map(line => {
            const values = line.split(',').map(val => val.trim());
            const row = {};
            columns.forEach((col, index) => {
              row[col] = values[index] || '';
            });
            return row;
          });
          setPreviewData(previewRows);
        }
      };
      reader.readAsText(selectedFile);
    }
  };

  const handleColumnMappingChange = (sourceColumn, targetColumn) => {
    setColumnMapping(prev => ({
      ...prev,
      [sourceColumn]: targetColumn
    }));
  };

  const handleUpload = async () => {
    if (!file) {
      alert('Please select a file first.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('file_type', fileType);
    
    // Add column mapping if provided
    if (Object.keys(columnMapping).length > 0) {
      formData.append('column_mapping', JSON.stringify(columnMapping));
    }

    // Choose endpoint based on fileType
    let endpoint = '/api/upload_inventory';
    if (fileType === 'orders') {
      endpoint = '/api/upload_orders';
    }

    try {
      const response = await fetch(`http://localhost:4000${endpoint}`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      
      if (response.ok) {
        setUploadStatus(`✅ File uploaded successfully! Rows processed: ${data.rows_processed}`);
        if (data.column_mapping_used) {
          setUploadStatus(prev => prev + ` | Column mapping: ${JSON.stringify(data.column_mapping_used)}`);
        }
      } else {
        // Handle column mapping requirement
        if (data.available_columns) {
          setShowMapping(true);
          setUploadStatus(`📋 Column mapping required. Available columns: ${data.available_columns.join(', ')}`);
        } else {
          setUploadStatus(`❌ Upload failed: ${data.detail || 'Unknown error'}`);
        }
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      setUploadStatus('❌ Error uploading file.');
    }
  };

  const handleRetryWithMapping = async () => {
    if (Object.keys(columnMapping).length === 0) {
      alert('Please provide column mapping first.');
      return;
    }
    await handleUpload();
  };

  useEffect(() => {
    fetch("http://localhost:4000/api/ping")
      .then((res) => res.json())
      .then((data) => console.log("✅ Backend Response:", data))
      .catch((err) => console.error("❌ Backend Error:", err));
  }, []);

  const requiredColumns = ['sku_id', 'name', 'stock', 'last_updated'];

  return (
    <div style={{ padding: '2rem', fontFamily: 'Arial, sans-serif', maxWidth: '800px' }}>
      <h2>📦 Upload Inventory / Orders File</h2>

      <div style={{ marginBottom: '1rem' }}>
        <input type="file" accept=".csv,.xlsx,.xls" onChange={handleFileChange} />
      </div>

      <div style={{ marginBottom: '1rem' }}>
        <label>Select File Type: </label>
        <select value={fileType} onChange={(e) => setFileType(e.target.value)}>
          <option value="inventory">Inventory</option>
          <option value="orders">Orders</option>
        </select>
      </div>

      {/* Column Mapping Section */}
      {showMapping && availableColumns.length > 0 && (
        <div style={{ 
          border: '1px solid #ccc', 
          padding: '1rem', 
          marginBottom: '1rem',
          borderRadius: '5px',
          backgroundColor: '#f9f9f9'
        }}>
          <h3>📋 Column Mapping Required</h3>
          <p>Map your CSV columns to the required format:</p>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            {requiredColumns.map(requiredCol => (
              <div key={requiredCol} style={{ display: 'flex', flexDirection: 'column' }}>
                <label style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>
                  {requiredCol}:
                </label>
                <select 
                  value={columnMapping[Object.keys(columnMapping).find(key => columnMapping[key] === requiredCol)] || ''}
                  onChange={(e) => {
                    const sourceCol = e.target.value;
                    if (sourceCol) {
                      handleColumnMappingChange(sourceCol, requiredCol);
                    }
                  }}
                  style={{ padding: '0.5rem' }}
                >
                  <option value="">Select column...</option>
                  {availableColumns.map(col => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
          
          <button 
            onClick={handleRetryWithMapping}
            style={{ 
              marginTop: '1rem',
              padding: '0.5rem 1rem',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '3px',
              cursor: 'pointer'
            }}
          >
            🔄 Retry Upload with Mapping
          </button>
        </div>
      )}

      {/* Preview Section */}
      {previewData && (
        <div style={{ 
          border: '1px solid #ddd', 
          padding: '1rem', 
          marginBottom: '1rem',
          borderRadius: '5px',
          backgroundColor: '#fafafa'
        }}>
          <h4>📊 File Preview (First 3 rows):</h4>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ borderCollapse: 'collapse', width: '100%' }}>
              <thead>
                <tr>
                  {availableColumns.map(col => (
                    <th key={col} style={{ border: '1px solid #ddd', padding: '8px', backgroundColor: '#f2f2f2' }}>
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewData.map((row, index) => (
                  <tr key={index}>
                    {availableColumns.map(col => (
                      <td key={col} style={{ border: '1px solid #ddd', padding: '8px' }}>
                        {row[col]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <button 
        onClick={handleUpload}
        style={{ 
          padding: '0.75rem 1.5rem',
          backgroundColor: '#28a745',
          color: 'white',
          border: 'none',
          borderRadius: '5px',
          cursor: 'pointer',
          fontSize: '16px'
        }}
      >
        📤 Upload
      </button>

      <div style={{ marginTop: '1rem' }}>
        {uploadStatus && (
          <div style={{ 
            padding: '1rem', 
            borderRadius: '5px',
            backgroundColor: uploadStatus.includes('✅') ? '#d4edda' : '#f8d7da',
            border: `1px solid ${uploadStatus.includes('✅') ? '#c3e6cb' : '#f5c6cb'}`
          }}>
            <p style={{ margin: 0 }}>{uploadStatus}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
