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

# Function to check if a service is running
check_service() {
    local url=$1
    local service_name=$2
    
    if curl -s "$url" >/dev/null 2>&1; then
        print_success "$service_name is running at $url"
        return 0
    else
        print_error "$service_name is not responding at $url"
        return 1
    fi
}

# Main test function
main() {
    print_status "Testing Inventory Uploader Services..."
    echo
    
    # Check if sample file exists
    if [ ! -f "sample_inventory.csv" ]; then
        print_error "sample_inventory.csv not found!"
        exit 1
    fi
    
    print_success "Sample file found: sample_inventory.csv"
    echo
    
    # Test each service
    print_status "Testing service connectivity..."
    
    local all_services_ok=true
    
    if ! check_service "http://localhost:8000/ping" "Backend"; then
        all_services_ok=false
    fi
    
    if ! check_service "http://localhost:4000/api/ping" "Proxy"; then
        all_services_ok=false
    fi
    
    if ! check_service "http://localhost:3000" "Frontend"; then
        all_services_ok=false
    fi
    
    echo
    
    if [ "$all_services_ok" = false ]; then
        print_error "Some services are not running. Please start them first with: ./start_services.sh"
        exit 1
    fi
    
    print_success "All services are running!"
    echo
    
    # Test the upload functionality
    print_status "Testing CSV upload functionality..."
    echo
    
    print_status "Uploading sample_inventory.csv to http://localhost:4000/api/upload"
    
    # Perform the upload
    response=$(curl -s -w "\n%{http_code}" -X POST -F "file=@sample_inventory.csv" http://localhost:4000/api/upload)
    
    # Extract the response body and status code
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | head -n -1)
    
    echo "HTTP Status Code: $http_code"
    echo "Response: $response_body"
    echo
    
    if [ "$http_code" = "200" ]; then
        print_success "Upload successful! 🎉"
        print_status "Check your BigQuery table 'walis-inventory-mvp.warehouse_data.inventory' for the uploaded data."
    elif [ "$http_code" = "500" ]; then
        print_error "Upload failed with 500 Internal Server Error"
        print_status "This might be due to:"
        print_status "  - Google Cloud authentication issues"
        print_status "  - Missing BigQuery permissions"
        print_status "  - Billing account issues"
        print_status "Check the backend.log file for detailed error messages."
    else
        print_error "Upload failed with HTTP status $http_code"
        print_status "Response: $response_body"
    fi
    
    echo
    print_status "Test completed!"
}

# Run main function
main "$@" 