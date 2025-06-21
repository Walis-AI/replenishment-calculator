# Inventory Uploader - Service Management Scripts

This document explains how to use the automated scripts to manage the Inventory Uploader services.

## Quick Start

### 1. Start All Services
```bash
./start_services.sh
```

This will:
- Kill any existing processes on ports 3000, 4000, and 8000
- Install/update dependencies if needed
- Start the backend (FastAPI) on port 8000
- Start the proxy server on port 4000
- Start the frontend (React) on port 3000
- Wait for each service to be ready
- Provide status updates and URLs

### 2. Test Upload Functionality
```bash
./test_upload.sh
```

This will:
- Check that all services are running
- Upload the sample CSV file to BigQuery
- Show the upload result

### 3. Stop All Services
```bash
./stop_services.sh
```

This will:
- Kill all running services
- Free up all ports
- Clean up process ID files

## Script Options

### Start Services with Clean Install
```bash
./start_services.sh --clean
```
This removes `node_modules` and Python cache before starting, ensuring a fresh install.

### Stop Services and Clean Logs
```bash
./stop_services.sh --clean-logs
```
This removes all log files after stopping services.

## Service URLs

Once started, the services will be available at:
- **Frontend**: http://localhost:3000
- **Proxy**: http://localhost:4000
- **Backend**: http://localhost:8000

## Log Files

The scripts create log files for debugging:
- `backend.log` - Backend server logs
- `proxy.log` - Proxy server logs
- `frontend.log` - Frontend server logs

## Process Management

The scripts save process IDs in:
- `backend.pid` - Backend process ID
- `proxy.pid` - Proxy process ID
- `frontend.pid` - Frontend process ID

These are used by the stop script to properly terminate services.

## Troubleshooting

### Services Won't Start
1. Check if ports are already in use:
   ```bash
   lsof -i :3000
   lsof -i :4000
   lsof -i :8000
   ```

2. Kill any existing processes:
   ```bash
   ./stop_services.sh
   ```

3. Try a clean start:
   ```bash
   ./start_services.sh --clean
   ```

### Upload Fails with 500 Error
1. Check the backend logs:
   ```bash
   tail -f backend.log
   ```

2. Verify Google Cloud authentication:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

3. Check BigQuery permissions and billing:
   - Ensure the project `walis-inventory-mvp` has billing enabled
   - Verify you have BigQuery permissions
   - Check that the table `warehouse_data.inventory` exists

### Frontend Won't Load
1. Check if Node.js dependencies are installed:
   ```bash
   cd frontend
   npm install
   ```

2. Check the frontend logs:
   ```bash
   tail -f frontend.log
   ```

## Manual Commands (if scripts fail)

### Start Backend Manually
```bash
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Start Proxy Manually
```bash
node proxy-server.js
```

### Start Frontend Manually
```bash
cd frontend
npm start
```

## Prerequisites

The scripts require:
- **Node.js** (for frontend and proxy)
- **Python 3** (for backend)
- **curl** (for health checks)
- **lsof** (for port management)

## Project Structure

```
inventory-uploader/
├── start_services.sh      # Start all services
├── stop_services.sh       # Stop all services
├── test_upload.sh         # Test upload functionality
├── backend/               # FastAPI backend
│   ├── main.py
│   └── venv/             # Python virtual environment
├── frontend/              # React frontend
│   ├── package.json
│   └── node_modules/
├── proxy-server.js        # Node.js proxy server
└── sample_inventory.csv   # Sample data for testing
```

## BigQuery Configuration

The backend is configured to upload to:
- **Project**: `walis-inventory-mvp`
- **Dataset**: `warehouse_data`
- **Table**: `inventory`

Make sure this table exists with the correct schema:
- `sku_id` (STRING)
- `name` (STRING)
- `quantity` (INTEGER)
- `last_updated` (TIMESTAMP) 