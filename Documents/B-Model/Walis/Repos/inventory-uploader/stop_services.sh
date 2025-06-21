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

# Function to kill processes on a port
kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pids" ]; then
        print_status "Killing processes on port $port: $pids"
        echo $pids | xargs kill -9 2>/dev/null || true
    else
        print_status "No processes found on port $port"
    fi
}

# Function to kill process by PID file
kill_pid_file() {
    local pid_file=$1
    local service_name=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if [ ! -z "$pid" ]; then
            print_status "Killing $service_name (PID: $pid)"
            kill $pid 2>/dev/null || true
            rm -f "$pid_file"
        fi
    else
        print_status "No PID file found for $service_name"
    fi
}

# Main script
main() {
    print_status "Stopping Inventory Uploader Services..."
    
    # Kill processes by PID files first
    kill_pid_file "backend.pid" "Backend"
    kill_pid_file "proxy.pid" "Proxy"
    kill_pid_file "frontend.pid" "Frontend"
    
    # Kill any remaining processes by name
    print_status "Killing any remaining service processes..."
    pkill -f "uvicorn.*main:app" 2>/dev/null || true
    pkill -f "node.*proxy-server" 2>/dev/null || true
    pkill -f "npm.*start" 2>/dev/null || true
    pkill -f "react-scripts.*start" 2>/dev/null || true
    
    # Kill processes on specific ports
    print_status "Killing processes on service ports..."
    kill_port 3000
    kill_port 4000
    kill_port 8000
    
    # Wait a moment for processes to terminate
    sleep 2
    
    # Double-check that ports are free
    print_status "Verifying ports are free..."
    for port in 3000 4000 8000; do
        if lsof -ti:$port >/dev/null 2>&1; then
            print_warning "Port $port is still in use, force killing..."
            lsof -ti:$port | xargs kill -9 2>/dev/null || true
        else
            print_success "Port $port is free"
        fi
    done
    
    # Clean up log files if requested
    if [ "$1" = "--clean-logs" ]; then
        print_status "Cleaning up log files..."
        rm -f backend.log proxy.log frontend.log
        print_success "Log files cleaned"
    fi
    
    print_success "All services stopped!"
}

# Run main function
main "$@" 