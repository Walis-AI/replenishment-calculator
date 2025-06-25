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

# Function to test stockout calculation
test_stockout_calculation() {
    print_status "Testing stockout calculation..."
    echo
    
    # Test the stockout calculation endpoint
    response=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/calculate-stockouts)
    
    # Extract the response body and status code
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | head -n -1)
    
    echo "HTTP Status Code: $http_code"
    echo "Response: $response_body"
    echo
    
    if [ "$http_code" = "200" ]; then
        print_success "Stockout calculation successful! 🎉"
        
        # Parse the response to show stockout count
        stockout_count=$(echo "$response_body" | grep -o '"stockout_count":[0-9]*' | cut -d':' -f2)
        if [ -n "$stockout_count" ]; then
            print_status "Found $stockout_count items that will stockout"
        fi
        
        print_status "Check your BigQuery table 'walis-inventory-mvp.warehouse_data.current_stockouts' for the results."
    elif [ "$http_code" = "500" ]; then
        print_error "Stockout calculation failed with 500 Internal Server Error"
        print_status "This might be due to:"
        print_status "  - Missing inventory or orders data in BigQuery"
        print_status "  - Google Cloud authentication issues"
        print_status "  - Missing BigQuery permissions"
        print_status "  - Billing account issues"
        print_status "Check the backend.log file for detailed error messages."
    else
        print_error "Stockout calculation failed with HTTP status $http_code"
        print_status "Response: $response_body"
    fi
}

# Function to test stockout retrieval
test_stockout_retrieval() {
    print_status "Testing stockout data retrieval..."
    echo
    
    # Test the stockout retrieval endpoint
    response=$(curl -s -w "\n%{http_code}" -X GET http://localhost:8000/stockouts)
    
    # Extract the response body and status code
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | head -n -1)
    
    echo "HTTP Status Code: $http_code"
    echo "Response: $response_body"
    echo
    
    if [ "$http_code" = "200" ]; then
        print_success "Stockout retrieval successful! 🎉"
        
        # Parse the response to show stockout count
        stockout_count=$(echo "$response_body" | grep -o '"stockout_count":[0-9]*' | cut -d':' -f2)
        if [ -n "$stockout_count" ]; then
            print_status "Retrieved $stockout_count stockout records"
        fi
    else
        print_error "Stockout retrieval failed with HTTP status $http_code"
        print_status "Response: $response_body"
    fi
}

# Main test function
main() {
    print_status "Testing Stockout Calculation Functionality..."
    echo
    
    # Check if backend is running
    print_status "Checking service connectivity..."
    
    if ! check_service "http://localhost:8000/ping" "Backend"; then
        print_error "Backend is not running. Please start it first with: ./start_services.sh"
        exit 1
    fi
    
    print_success "Backend is running!"
    echo
    
    # Test stockout calculation
    test_stockout_calculation
    
    echo
    
    # Test stockout retrieval
    test_stockout_retrieval
    
    echo
    print_status "Stockout testing completed!"
    echo
    print_status "💡 Tips:"
    print_status "  - Make sure you have both inventory and orders data in BigQuery"
    print_status "  - The stockout calculation compares inventory.quantity_on_hand with sum(orders.quantity)"
    print_status "  - Results are stored in 'walis-inventory-mvp.warehouse_data.current_stockouts'"
}

# Run main function
main "$@" 