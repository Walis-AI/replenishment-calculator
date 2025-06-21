#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -ti:$1 >/dev/null 2>&1
}

# Function to kill processes on a port
kill_port() {
    if port_in_use $1; then
        print_status "Killing processes on port $1..."
        lsof -ti:$1 | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

# Function to wait for a service to be ready
wait_for_service() {
    local url=$1
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for service at $url..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            print_success "Service at $url is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    
    print_error "Service at $url failed to start after $max_attempts attempts"
    return 1
}

# Main script
main() {
    print_status "Starting Inventory Uploader Services..."
    print_status "Current directory: $(pwd)"
    
    # Check if we're in the right directory
    if [ ! -f "proxy-server.js" ]; then
        print_error "proxy-server.js not found. Please run this script from the project root directory."
        exit 1
    fi
    
    # Step 1: Kill zombie processes and free ports
    print_status "Step 1: Killing zombie processes and freeing ports..."
    kill_port 3000
    kill_port 4000
    kill_port 8000
    
    # Kill any remaining uvicorn, node, or npm processes
    print_status "Killing any remaining service processes..."
    pkill -f "uvicorn\|node.*proxy-server\|npm.*start" 2>/dev/null || true
    sleep 2
    
    # Step 2: Clean up if needed
    if [ "$1" = "--clean" ]; then
        print_status "Step 2: Cleaning up (--clean flag provided)..."
        
        if [ -d "frontend/node_modules" ]; then
            print_status "Removing frontend node_modules..."
            rm -rf frontend/node_modules
        fi
        
        if [ -d "backend" ]; then
            print_status "Cleaning Python cache..."
            find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
            find backend -name "*.pyc" -delete 2>/dev/null || true
        fi
    fi
    
    # Step 3: Install frontend dependencies
    print_status "Step 3: Installing frontend dependencies..."
    if [ -d "frontend" ]; then
        cd frontend
        if [ ! -d "node_modules" ]; then
            print_status "Installing npm dependencies..."
            npm install
        else
            print_status "Node modules already exist, skipping npm install"
        fi
        cd ..
    else
        print_error "Frontend directory not found!"
        exit 1
    fi
    
    # Step 4: Setup backend
    print_status "Step 4: Setting up backend..."
    if [ -d "backend" ]; then
        cd backend
        
        # Check if virtual environment exists
        if [ ! -d "venv" ]; then
            print_status "Creating virtual environment..."
            python3 -m venv venv
        fi
        
        # Activate virtual environment
        print_status "Activating virtual environment..."
        source venv/bin/activate
        
        # Install/upgrade pip
        print_status "Upgrading pip..."
        pip install --upgrade pip
        
        # Install required packages
        print_status "Installing Python dependencies..."
        pip install fastapi uvicorn pandas google-cloud-bigquery python-multipart pandas-gbq six
        
        # Check if requirements.txt exists and install from it
        if [ -f "requirements.txt" ]; then
            print_status "Installing from requirements.txt..."
            pip install -r requirements.txt
        fi
        
        cd ..
    else
        print_error "Backend directory not found!"
        exit 1
    fi
    
    # Step 5: Start backend
    print_status "Step 5: Starting backend server..."
    cd backend
    source venv/bin/activate
    
    # Start backend in background
    print_status "Starting uvicorn server..."
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ../backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../backend.pid
    
    cd ..
    
    # Wait for backend to be ready
    if wait_for_service "http://localhost:8000/ping"; then
        print_success "Backend is running!"
    else
        print_error "Backend failed to start. Check backend.log for details."
        exit 1
    fi
    
    # Step 6: Start proxy server
    print_status "Step 6: Starting proxy server..."
    
    # Start proxy in background
    print_status "Starting proxy server..."
    node proxy-server.js > proxy.log 2>&1 &
    PROXY_PID=$!
    echo $PROXY_PID > proxy.pid
    
    # Wait for proxy to be ready
    if wait_for_service "http://localhost:4000/api/ping"; then
        print_success "Proxy is running!"
    else
        print_warning "Proxy might not be responding to /api/ping, but continuing..."
    fi
    
    # Step 7: Start frontend
    print_status "Step 7: Starting frontend..."
    cd frontend
    
    # Start frontend in background
    print_status "Starting React development server..."
    npm start > ../frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../frontend.pid
    
    cd ..
    
    # Wait for frontend to be ready
    if wait_for_service "http://localhost:3000"; then
        print_success "Frontend is running!"
    else
        print_warning "Frontend might still be starting up..."
    fi
    
    # Step 8: Final status
    print_success "All services started!"
    echo
    print_status "Service URLs:"
    echo "  Frontend: http://localhost:3000"
    echo "  Proxy:    http://localhost:4000"
    echo "  Backend:  http://localhost:8000"
    echo
    print_status "Log files:"
    echo "  Backend:  backend.log"
    echo "  Proxy:    proxy.log"
    echo "  Frontend: frontend.log"
    echo
    print_status "Process IDs saved in:"
    echo "  Backend:  backend.pid"
    echo "  Proxy:    proxy.pid"
    echo "  Frontend: frontend.pid"
    echo
    print_status "To stop all services, run: ./stop_services.sh"
    echo
    print_success "Ready to test upload functionality!"
}

# Function to handle script interruption
cleanup() {
    print_warning "Script interrupted. Cleaning up..."
    if [ -f "backend.pid" ]; then
        kill $(cat backend.pid) 2>/dev/null || true
        rm -f backend.pid
    fi
    if [ -f "proxy.pid" ]; then
        kill $(cat proxy.pid) 2>/dev/null || true
        rm -f proxy.pid
    fi
    if [ -f "frontend.pid" ]; then
        kill $(cat frontend.pid) 2>/dev/null || true
        rm -f frontend.pid
    fi
    exit 1
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check prerequisites
if ! command_exists node; then
    print_error "Node.js is not installed. Please install Node.js first."
    exit 1
fi

if ! command_exists python3; then
    print_error "Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

if ! command_exists curl; then
    print_error "curl is not installed. Please install curl first."
    exit 1
fi

# Run main function
main "$@" 