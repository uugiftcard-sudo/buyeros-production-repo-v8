#!/bin/bash
# BuyerOS Monitoring Script

set -e

API_URL="${API_URL:-http://localhost:8000}"

echo "=== BuyerOS Health Monitor ==="

check_endpoint() {
    local name=$1
    local url=$2
    
    echo -n "Checking $name... "
    response=$(curl -s -w "%{http_code}" -o /dev/null "$url")
    if [ "$response" = "200" ]; then
        echo "OK ($response)"
    else
        echo "FAILED ($response)"
    fi
}

# Check endpoints
check_endpoint "Health" "$API_URL/health"
check_endpoint "API Health" "$API_URL/api/health"
check_endpoint "Status" "$API_URL/api/status"

# Check backend process
echo -n "Backend process... "
if pgrep -f "uvicorn.*app.main" > /dev/null; then
    echo "Running ($(pgrep -f 'uvicorn.*app.main'))"
else
    echo "Not running"
fi

# Check memory usage
echo "Memory usage:"
ps aux | grep -E "uvicorn|python" | grep -v grep | awk '{print "  PID:", $2, "CPU:", $3, "MEM:", $4}'

echo "=== Done ==="
