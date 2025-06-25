import React, { useState, useEffect } from 'react';

function App() {
  const [file, setFile] = useState(null);
  const [fileType, setFileType] = useState('inventory');
  const [uploadStatus, setUploadStatus] = useState('');

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) {
      alert('Please select a file first.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('file_type', fileType);

    try {
      const response = await fetch('http://localhost:4000/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        setUploadStatus(`✅ File uploaded: ${data.filename}`);
      } else {
        setUploadStatus('❌ Upload failed.');
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      setUploadStatus('❌ Error uploading file.');
    }
  };

  useEffect(() => {
    fetch("http://localhost:4000/api/ping")
      .then((res) => res.json())
      .then((data) => console.log("✅ Backend Response:", data))
      .catch((err) => console.error("❌ Backend Error:", err));
  }, []);

  return (
    <div style={{ padding: '2rem', fontFamily: 'Arial, sans-serif' }}>
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

      <button onClick={handleUpload}>📤 Upload</button>

      <div style={{ marginTop: '1rem' }}>
        {uploadStatus && <p>{uploadStatus}</p>}
      </div>
    </div>
  );
}

export default App;
