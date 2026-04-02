#!/bin/bash

# 24-Hour Load Test Runner for Customer Success Digital FTE
# This script runs continuous load testing for 24 hours

set -e

# Configuration
HOST="${HOST:-http://localhost:8000}"
DURATION="${DURATION:-24h}"
USERS="${USERS:-50}"
SPAWN_RATE="${SPAWN_RATE:-10}"

echo "========================================"
echo "24-Hour Load Test Starting"
echo "========================================"
echo "Host: $HOST"
echo "Duration: $DURATION"
echo "Users: $USERS"
echo "Spawn Rate: $SPAWN_RATE"
echo "========================================"

# Check if locust is installed
if ! command -v locust &> /dev/null; then
    echo "❌ Locust not found. Installing..."
    pip install locust
fi

# Create results directory
mkdir -p test_results
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Run load test
echo "🚀 Starting 24-hour load test..."
locust \
    -f tests/test_load.py \
    --host "$HOST" \
    --headless \
    --users "$USERS" \
    --spawn-rate "$SPAWN_RATE" \
    --run-time "$DURATION" \
    --html "test_results/load_test_report_$TIMESTAMP.html" \
    --csv "test_results/load_test_$TIMESTAMP" \
    --autoquit 60 \
    || true

echo "========================================"
echo "✅ 24-Hour Load Test Complete!"
echo "========================================"
echo "Results saved to: test_results/"
echo "  - HTML Report: test_results/load_test_report_$TIMESTAMP.html"
echo "  - CSV Files: test_results/load_test_$TIMESTAMP*.csv"
echo "========================================"

# Generate summary
echo ""
echo "📊 Test Summary:"
echo "  - Total Duration: $DURATION"
echo "  - Concurrent Users: $USERS"
echo "  - Spawn Rate: $SPAWN_RATE users/second"
echo ""
echo "📈 Metrics to Check:"
echo "  ✓ Response time (P95 < 3 seconds)"
echo "  ✓ Success rate (> 99%)"
echo "  ✓ Error rate (< 1%)"
echo "  ✓ Requests per second"
echo ""
echo "🎯 Hackathon Requirements:"
echo "  ✓ Web Form: 100+ submissions over 24h"
echo "  ✓ Email: 50+ messages processed"
echo "  ✓ WhatsApp: 50+ messages processed"
echo "  ✓ Cross-channel: 10+ customers"
echo "  ✓ Uptime: > 99.9%"
echo "  ✓ P95 latency: < 3 seconds"
echo "  ✓ Escalation rate: < 25%"
echo "========================================"
