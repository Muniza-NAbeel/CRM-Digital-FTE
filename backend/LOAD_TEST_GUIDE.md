# 24-Hour Load Test Guide

## Overview

This guide explains how to run the 24-hour continuous load test for the Customer Success Digital FTE.

## Prerequisites

- Python 3.10+ installed
- Backend server running on `http://localhost:8000`
- Locust installed: `pip install locust`

## Quick Start

### Windows

```bash
cd D:\assignments\hackathon_five\backend
run_24h_test.bat
```

### Linux/Mac

```bash
cd /path/to/hackathon_five/backend
chmod +x run_24h_test.sh
./run_24h_test.sh
```

## Configuration

Environment variables you can set:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `http://localhost:8000` | Backend server URL |
| `DURATION` | `24h` | Test duration |
| `USERS` | `50` | Concurrent users |
| `SPAWN_RATE` | `10` | Users spawned per second |

### Example (Custom Configuration)

```bash
# Windows
set HOST=http://localhost:8000
set DURATION=1h
set USERS=100
set SPAWN_RATE=20
run_24h_test.bat

# Linux/Mac
export HOST=http://localhost:8000
export DURATION=1h
export USERS=100
export SPAWN_RATE=20
./run_24h_test.sh
```

## Running Shorter Tests

For development/testing, you can run shorter tests:

```bash
# 1 hour test
locust -f tests/test_load.py --host http://localhost:8000 --headless -u 50 -r 10 --run-time 1h

# 5 minute quick test
locust -f tests/test_load.py --host http://localhost:8000 --headless -u 20 -r 5 --run-time 5m
```

## Test Scenarios

The load test includes 5 user types:

1. **WebFormUser** - Submits support forms via web
2. **AngryCustomerUser** - Tests escalation handling
3. **APIPollerUser** - Polls ticket status endpoints
4. **MixedChannelUser** - Uses multiple channels
5. **StressTestUser** - High-volume submissions

## Metrics to Monitor

### Performance Metrics

- **Response Time (P95)**: Should be < 3 seconds
- **Success Rate**: Should be > 99%
- **Error Rate**: Should be < 1%
- **Requests/Second**: Varies based on load

### Hackathon Requirements

| Metric | Target | How to Check |
|--------|--------|--------------|
| Web Form Submissions | 100+ over 24h | CSV report |
| Email Messages | 50+ processed | Backend logs |
| WhatsApp Messages | 50+ processed | Backend logs |
| Cross-Channel Customers | 10+ | Database query |
| Uptime | > 99.9% | Locust report |
| P95 Latency | < 3 seconds | Locust report |
| Escalation Rate | < 25% | Database query |

## Results

After the test completes, you'll find:

- **HTML Report**: `test_results/load_test_report_YYYYMMDD_HHMMSS.html`
- **CSV Files**: `test_results/load_test_YYYYMMDD_HHMMSS*.csv`

### Viewing Results

1. Open the HTML report in your browser
2. Check key metrics:
   - Total requests
   - Failures
   - Response time distribution
   - Requests per second

## Troubleshooting

### Backend Not Responding

```bash
# Check if backend is running
curl http://localhost:8000/health

# Restart backend if needed
cd backend
python -m uvicorn src.api.main:app --reload
```

### Locust Installation Issues

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install locust
pip install locust

# Verify installation
locust --version
```

### High Error Rate

If error rate > 5%:

1. Check backend logs for errors
2. Reduce number of concurrent users
3. Verify database connection pool size
4. Check Kafka is running

## Database Queries for Validation

After test completion, run these queries:

```sql
-- Total tickets created
SELECT COUNT(*) FROM tickets 
WHERE created_at > NOW() - INTERVAL '24 hours';

-- Cross-channel customers
SELECT c.email, COUNT(DISTINCT t.source_channel) as channels
FROM customers c
JOIN tickets t ON c.id = t.customer_id
WHERE t.created_at > NOW() - INTERVAL '24 hours'
GROUP BY c.email
HAVING COUNT(DISTINCT t.source_channel) > 1;

-- Escalation rate
SELECT 
    COUNT(*) FILTER (WHERE status = 'escalated')::float / 
    COUNT(*) * 100 as escalation_rate
FROM tickets 
WHERE created_at > NOW() - INTERVAL '24 hours';
```

## Chaos Testing (Optional)

To test resilience, run these commands during the load test:

```bash
# Kill random worker pod (Kubernetes)
kubectl delete pod -l app=customer-success-fte,component=worker --random

# Restart Kafka
docker-compose restart kafka

# Simulate network latency
tc qdisc add dev lo root netem delay 100ms
```

## Success Criteria

Test is considered successful if:

- ✅ Uptime > 99.9%
- ✅ P95 latency < 3 seconds
- ✅ Error rate < 1%
- ✅ No data loss
- ✅ All channels functional
- ✅ Cross-channel tracking works
- ✅ Escalation rate < 25%

## Next Steps

After successful 24-hour test:

1. Review HTML report
2. Check backend logs for any warnings
3. Verify all tickets were created
4. Check sentiment analysis accuracy
5. Validate escalation triggers
6. Document any issues found
7. Optimize if needed

## Support

For issues or questions:
- Check Locust documentation: https://docs.locust.io/
- Review backend logs: `backend/logs/`
- Check test results: `test_results/`
