# 24-Hour Stability Test Plan

## Overview

This document outlines the 24-hour stability test for the Customer Success FTE system. The test validates that the system can operate continuously under realistic load conditions.

---

## Test Objectives

1. **Validate 24/7 Operation:** System must run continuously for 24 hours without manual intervention
2. **Measure Performance:** Track response times, success rates, and resource utilization
3. **Test Auto-Scaling:** Verify pods scale up/down based on load
4. **Validate Fallback Modes:** Test Kafka/database failure recovery
5. **Monitor Memory Leaks:** Detect memory growth over time
6. **Test Cross-Channel Continuity:** Ensure conversations persist across channels

---

## Test Environment

### Infrastructure
- **Kubernetes Cluster:** Minikube or Cloud (GKE/AKS/EKS)
- **Nodes:** Minimum 3 nodes
- **CPU:** 4 cores per node minimum
- **Memory:** 8GB RAM per node minimum
- **Storage:** 50GB SSD per node

### Deployments
```yaml
API Pods:        3 replicas (auto-scale 3-20)
Worker Pods:     3 replicas (auto-scale 3-30)
PostgreSQL:      1 pod (StatefulSet)
Kafka:           3 pods (StatefulSet)
Zookeeper:       3 pods (StatefulSet)
```

---

## Test Phases

### Phase 1: Pre-Test Checklist (30 minutes)

- [ ] All pods healthy and ready
- [ ] Database migrations complete
- [ ] Kafka topics created
- [ ] Gmail credentials valid
- [ ] Twilio sandbox active
- [ ] Monitoring dashboards configured
- [ ] Alert rules active
- [ ] Backup system tested
- [ ] Log aggregation working

### Phase 2: Ramp-Up (1 hour)

**Goal:** Gradually increase load to normal operating levels

**Load Profile:**
- Start: 10 concurrent users
- End: 100 concurrent users
- Ramp-up: Linear over 1 hour

**Metrics to Track:**
- Pod CPU/memory usage
- Response times (P50, P95, P99)
- Success rate
- Auto-scaling triggers

### Phase 3: Steady State (20 hours)

**Goal:** Maintain normal operating load for 20 hours

**Load Profile:**
- Concurrent users: 100 (constant)
- Requests/minute: ~600
- Mix: 60% web form, 25% email, 15% WhatsApp

**Metrics to Track:**
- All Phase 2 metrics
- Memory growth rate
- Garbage collection frequency
- Database connection pool usage
- Kafka lag

**Scheduled Events:**
- Hour 6: Chaos test - kill 1 API pod
- Hour 12: Chaos test - kill 1 worker pod
- Hour 18: Chaos test - restart Kafka leader

### Phase 4: Stress Test (2 hours)

**Goal:** Push system beyond normal operating conditions

**Load Profile:**
- Start: 100 concurrent users
- Peak: 500 concurrent users
- Duration: 2 hours

**Metrics to Track:**
- Auto-scaling response time
- Max replicas reached
- Degraded performance thresholds
- Error rate under load

### Phase 5: Cool-Down (1 hour)

**Goal:** Gradually reduce load and observe recovery

**Load Profile:**
- Start: 500 concurrent users
- End: 10 concurrent users
- Ramp-down: Linear over 1 hour

**Metrics to Track:**
- Auto-scaling down response
- Resource release
- System stability at low load

---

## Success Criteria

### Availability
- [ ] Uptime > 99.9% (< 2.6 minutes downtime allowed)
- [ ] No data loss
- [ ] All messages delivered

### Performance
- [ ] P95 response time < 3 seconds
- [ ] P99 response time < 5 seconds
- [ ] Success rate > 99%

### Scalability
- [ ] Auto-scaling triggered correctly
- [ ] Pods scaled up within 2 minutes
- [ ] Pods scaled down within 5 minutes

### Reliability
- [ ] System recovered from chaos tests
- [ ] No memory leaks detected
- [ ] Database connections stable

### Business Metrics
- [ ] Escalation rate < 25%
- [ ] Cross-channel ID accuracy > 95%
- [ ] Customer sentiment stable/positive

---

## Monitoring Setup

### Prometheus Metrics

```promql
# API Performance
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job="fte-api"}[5m]))

# Worker Performance
rate(fte_messages_processed_total[5m])

# Error Rates
rate(http_requests_total{status=~"5.."}[5m])

# Resource Usage
container_memory_usage_bytes{namespace="customer-success-fte"}

# Kafka Lag
kafka_consumer_lag{topic="fte.tickets.incoming"}

# Database Connections
pg_stat_activity_count{datname="customer_success_fte"}
```

### Grafana Dashboards

1. **System Overview**
   - Pod status and health
   - CPU/Memory usage
   - Network I/O
   
2. **Application Performance**
   - Request rates by channel
   - Response time percentiles
   - Error rates
   
3. **Business Metrics**
   - Tickets processed per hour
   - Escalation rate
   - Sentiment distribution
   
4. **Database Health**
   - Connection pool usage
   - Query performance
   - Replication lag

### Alert Rules

```yaml
groups:
- name: fte-alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      
  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 3
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "P95 response time > 3s"
      
  - alert: PodCrashLooping
    expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Pod is crash looping"
      
  - alert: LowDiskSpace
    expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.1
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Disk space running low"
```

---

## Chaos Engineering Tests

### Test 1: API Pod Failure (Hour 6)

**Action:**
```bash
kubectl delete pod -l app=customer-success-fte,component=api -n customer-success-fte
```

**Expected:**
- Remaining pods handle load
- New pod starts within 30 seconds
- No request failures (or < 1%)
- Auto-scaling maintains replica count

### Test 2: Worker Pod Failure (Hour 12)

**Action:**
```bash
kubectl delete pod -l app=customer-success-fte,component=message-processor -n customer-success-fte
```

**Expected:**
- Messages queue without processing
- New worker starts within 30 seconds
- Backlog processed within 5 minutes
- No message loss

### Test 3: Kafka Leader Restart (Hour 18)

**Action:**
```bash
kubectl delete pod -l app=kafka,component=controller -n customer-success-fte
```

**Expected:**
- New leader elected within 30 seconds
- Producers/consumers reconnect
- No message loss
- Lag returns to normal within 2 minutes

---

## Execution Guide

### Pre-Test Setup (Day Before)

```bash
# 1. Deploy application
cd backend/k8s
kubectl apply -f .

# 2. Wait for all pods ready
kubectl wait --for=condition=ready pod --all -n customer-success-fte --timeout=300s

# 3. Verify health
curl http://<load-balancer-ip>/health

# 4. Setup monitoring
kubectl apply -f monitoring.yaml

# 5. Port-forward for testing
kubectl port-forward svc/customer-success-fte 8000:80 -n customer-success-fte
```

### Test Execution (Test Day)

```bash
# 1. Start monitoring (Terminal 1)
kubectl top pods -n customer-success-fte --watch

# 2. Start load test (Terminal 2)
locust -f tests/load_test.py \
  --host=http://localhost:8000 \
  --headless \
  -u 100 \
  -r 10 \
  -t 86400s \
  --csv=load_test_results/

# 3. Monitor logs (Terminal 3)
kubectl logs -f -l app=customer-success-fte -n customer-success-fte

# 4. Monitor metrics (Browser)
# Open Grafana at http://localhost:3000
```

### Chaos Tests (During Test)

```bash
# Hour 6: Kill API pod
kubectl delete pod -l app=customer-success-fte,component=api -n customer-success-fte

# Hour 12: Kill worker pod
kubectl delete pod -l app=customer-success-fte,component=message-processor -n customer-success-fte

# Hour 18: Restart Kafka
kubectl delete pod -l app=kafka -n customer-success-fte
```

### Post-Test Analysis

```bash
# 1. Generate report
python tests/analyze_load_test.py --input=load_test_results/ --output=test_report.html

# 2. Review metrics
# - Check Grafana dashboards
# - Review Prometheus queries
# - Analyze error logs

# 3. Document findings
# - Update TEST_RESULTS.md
# - Note any issues found
# - List improvements needed
```

---

## Results Template

### Executive Summary

```
Test Duration:     24 hours (2026-04-XX 00:00 to 2026-04-XX 00:00)
Total Requests:    XXX,XXX
Success Rate:      XX.XX%
P95 Response Time: X,XXX ms
P99 Response Time: X,XXX ms
Downtime:          X minutes
Auto-Scale Events: XX
```

### Performance Summary

| Metric | Target | Actual | Pass/Fail |
|--------|--------|--------|-----------|
| Uptime | >99.9% | XX.X% | ✅/❌ |
| P95 Response Time | <3s | X.XXs | ✅/❌ |
| P99 Response Time | <5s | X.XXs | ✅/❌ |
| Success Rate | >99% | XX.X% | ✅/❌ |
| Escalation Rate | <25% | XX% | ✅/❌ |

### Resource Utilization

| Component | Avg CPU | Peak CPU | Avg Memory | Peak Memory |
|-----------|---------|----------|------------|-------------|
| API Pod 1 | XX% | XX% | XXX MB | XXX MB |
| API Pod 2 | XX% | XX% | XXX MB | XXX MB |
| Worker 1 | XX% | XX% | XXX MB | XXX MB |
| Worker 2 | XX% | XX% | XXX MB | XXX MB |
| PostgreSQL | XX% | XX% | XXX MB | XXX MB |
| Kafka | XX% | XX% | XXX MB | XXX MB |

### Issues Found

| # | Issue | Severity | Resolution |
|---|-------|----------|------------|
| 1 | Description | High/Med/Low | Fixed/Investigating |

### Recommendations

1. **Immediate Actions:** List critical fixes needed
2. **Short-term Improvements:** List improvements for next sprint
3. **Long-term Optimizations:** List architectural improvements

---

## Troubleshooting Guide

### High Memory Usage

```bash
# Check for memory leaks
kubectl top pods -n customer-success-fte

# Review heap dumps
kubectl exec -it <pod-name> -n customer-success-fte -- jmap -heap <pid>

# Solution: Increase memory limits or fix leak
```

### High Response Times

```bash
# Check slow queries
kubectl logs -l app=customer-success-fte -n customer-success-fte | grep "slow"

# Check database locks
kubectl exec -it postgres-0 -n customer-success-fte -- psql -c "SELECT * FROM pg_locks;"

# Solution: Optimize queries or scale resources
```

### Message Backlog

```bash
# Check Kafka lag
kubectl exec -it kafka-0 -n customer-success-fte -- kafka-consumer-groups --bootstrap-server localhost:9092 --describe

# Scale workers
kubectl scale deployment fte-message-processor --replicas=10 -n customer-success-fte

# Solution: Increase worker count or optimize processing
```

---

## Local Development Test (Alternative to Kubernetes)

For students without access to Kubernetes cluster, here's a simplified local test:

### Prerequisites

```bash
# Ensure you have:
- Python 3.11+
- Node.js 18+
- Docker Desktop (for PostgreSQL and Kafka)
- Locust installed (pip install locust)
```

### Step 1: Start Infrastructure (Docker)

```bash
# Start PostgreSQL and Kafka in Docker
cd D:\assignments\hackathon_five
docker-compose up -d postgres kafka zookeeper

# Wait for services to be ready
docker-compose ps

# All services should show "healthy" status
```

### Step 2: Start Backend Services

```bash
# Terminal 1 - Start API and Worker
cd D:\assignments\hackathon_five\backend
python run_both.py
```

### Step 3: Start Frontend

```bash
# Terminal 2 - Start Web Form
cd D:\assignments\hackathon_five\frontend\web-form
npm run dev
```

### Step 4: Run Load Test

```bash
# Terminal 3 - Run Locust load test
cd D:\assignments\hackathon_five\backend

# Option A: Web UI (Interactive)
locust -f tests/load_test.py --host=http://localhost:8000

# Open browser: http://localhost:8089
# Set users: 100, Spawn rate: 10, Run time: 24h

# Option B: Headless (Automated)
locust -f tests/load_test.py \
  --host=http://localhost:8000 \
  --headless \
  -u 100 \
  -r 10 \
  -t 86400s \
  --csv=load_test_results/ \
  --html=load_test_report.html
```

### Step 5: Monitor Test

```bash
# Terminal 4 - Monitor system resources
# Windows: Task Manager or Resource Monitor
# Check: CPU, Memory, Disk I/O

# Terminal 5 - Monitor application logs
cd D:\assignments\hackathon_five\backend
Get-Content -Path "logs\*.log" -Wait -Tail 50

# Or use Python script to monitor
python -c "
import time
while True:
    time.sleep(60)
    print(f'[{time.strftime(\"%Y-%m-%d %H:%M\")}] Test running...')
"
```

### Step 6: Mid-Test Chaos (Optional)

```bash
# Hour 6: Restart backend
# Press Ctrl+C in Terminal 1, then restart:
python run_both.py

# Hour 12: Restart frontend
# Press Ctrl+C in Terminal 2, then restart:
npm run dev

# Hour 18: Restart Docker services
docker-compose restart postgres kafka
```

### Step 7: Post-Test Analysis

```bash
# Generate report from CSV results
cd D:\assignments\hackathon_five\backend
python tests/analyze_load_test.py --input=load_test_results/ --output=load_test_report.html

# Open report in browser
start load_test_report.html
```

---

## Automated Test Script

Save this as `run_24h_test.bat` (Windows) or `run_24h_test.sh` (Linux/Mac):

### Windows Batch File (run_24h_test.bat)

```batch
@echo off
echo ============================================================
echo Customer Success FTE - 24 Hour Stability Test
echo ============================================================
echo.
echo Starting test at: %date% %time%
echo.

REM Create results directory
mkdir load_test_results 2>nul

REM Start load test
echo Starting Locust load test...
locust -f tests/load_test.py ^
  --host=http://localhost:8000 ^
  --headless ^
  -u 100 ^
  -r 10 ^
  -t 86400s ^
  --csv=load_test_results/ ^
  --html=load_test_report.html

echo.
echo Test completed at: %date% %time%
echo.
echo Generating report...
python tests/analyze_load_test.py --input=load_test_results/ --output=load_test_report.html

echo.
echo ============================================================
echo Test Complete! Report saved to: load_test_report.html
echo ============================================================
pause
```

### Linux/Mac Shell Script (run_24h_test.sh)

```bash
#!/bin/bash

echo "============================================================"
echo "Customer Success FTE - 24 Hour Stability Test"
echo "============================================================"
echo
echo "Starting test at: $(date)"
echo

# Create results directory
mkdir -p load_test_results

# Start load test
echo "Starting Locust load test..."
locust -f tests/load_test.py \
  --host=http://localhost:8000 \
  --headless \
  -u 100 \
  -r 10 \
  -t 86400s \
  --csv=load_test_results/ \
  --html=load_test_report.html

echo
echo "Test completed at: $(date)"
echo

# Generate report
echo "Generating report..."
python tests/analyze_load_test.py --input=load_test_results/ --output=load_test_report.html

echo
echo "============================================================"
echo "Test Complete! Report saved to: load_test_report.html"
echo "============================================================"
```

### Make Test Executable (Linux/Mac)

```bash
chmod +x run_24h_test.sh
```

---

## Test Analysis Script

Save this as `tests/analyze_load_test.py`:

```python
"""
Analyze Locust load test results and generate HTML report.

Usage:
    python analyze_load_test.py --input=load_test_results/ --output=report.html
"""

import argparse
import pandas as pd
import os
from datetime import datetime
from pathlib import Path


def load_results(input_dir: str):
    """Load CSV results from Locust."""
    results_path = Path(input_dir)
    
    # Load requests CSV
    requests_file = results_path / "requests.csv"
    if requests_file.exists():
        requests_df = pd.read_csv(requests_file)
    else:
        requests_df = pd.DataFrame()
    
    # Load stats CSV
    stats_file = results_path / "stats.csv"
    if stats_file.exists():
        stats_df = pd.read_csv(stats_file)
    else:
        stats_df = pd.DataFrame()
    
    # Load failures CSV
    failures_file = results_path / "failures.csv"
    if failures_file.exists():
        failures_df = pd.read_csv(failures_file)
    else:
        failures_df = pd.DataFrame()
    
    return requests_df, stats_df, failures_df


def generate_report(requests_df, stats_df, failures_df, output_file: str):
    """Generate HTML report from results."""
    
    # Calculate summary statistics
    total_requests = len(requests_df) if not requests_df.empty else 0
    total_failures = len(failures_df) if not failures_df.empty else 0
    success_rate = ((total_requests - total_failures) / total_requests * 100) if total_requests > 0 else 0
    
    # Get P95 and P99 from stats
    if not stats_df.empty:
        total_row = stats_df[stats_df['Method'] == 'Total']
        if not total_row.empty:
            p95 = total_row['response_time_95_percentile'].values[0]
            p99 = total_row['response_time_99_percentile'].values[0]
            avg_response_time = total_row['avg_response_time'].values[0]
        else:
            p95 = p99 = avg_response_time = 0
    else:
        p95 = p99 = avg_response_time = 0
    
    # Generate HTML
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>24-Hour Load Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }}
        .metric {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .metric.pass {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
        .metric.fail {{ background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }}
        .metric-value {{ font-size: 36px; font-weight: bold; margin: 10px 0; }}
        .metric-label {{ font-size: 14px; opacity: 0.9; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; font-weight: 600; }}
        tr:hover {{ background: #f8f9fa; }}
        .status-pass {{ color: #28a745; font-weight: bold; }}
        .status-fail {{ color: #dc3545; font-weight: bold; }}
        .timestamp {{ color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 24-Hour Load Test Report</h1>
        <p class="timestamp">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        
        <h2>Executive Summary</h2>
        <div class="summary">
            <div class="metric {'pass' if success_rate > 99 else 'fail'}">
                <div class="metric-value">{success_rate:.2f}%</div>
                <div class="metric-label">Success Rate</div>
            </div>
            <div class="metric {'pass' if p95 < 3000 else 'fail'}">
                <div class="metric-value">{p95:.0f}ms</div>
                <div class="metric-label">P95 Response Time</div>
            </div>
            <div class="metric {'pass' if p99 < 5000 else 'fail'}">
                <div class="metric-value">{p99:.0f}ms</div>
                <div class="metric-label">P99 Response Time</div>
            </div>
            <div class="metric">
                <div class="metric-value">{total_requests:,}</div>
                <div class="metric-label">Total Requests</div>
            </div>
            <div class="metric {'pass' if total_failures < 100 else 'fail'}">
                <div class="metric-value">{total_failures:,}</div>
                <div class="metric-label">Total Failures</div>
            </div>
        </div>
        
        <h2>Performance Metrics</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Target</th>
                <th>Status</th>
            </tr>
            <tr>
                <td>Success Rate</td>
                <td>{success_rate:.2f}%</td>
                <td>>99%</td>
                <td class="{'status-pass' if success_rate > 99 else 'status-fail'}">{'✅ PASS' if success_rate > 99 else '❌ FAIL'}</td>
            </tr>
            <tr>
                <td>P95 Response Time</td>
                <td>{p95:.0f}ms</td>
                <td><3000ms</td>
                <td class="{'status-pass' if p95 < 3000 else 'status-fail'}">{'✅ PASS' if p95 < 3000 else '❌ FAIL'}</td>
            </tr>
            <tr>
                <td>P99 Response Time</td>
                <td>{p99:.0f}ms</td>
                <td><5000ms</td>
                <td class="{'status-pass' if p99 < 5000 else 'status-fail'}">{'✅ PASS' if p99 < 5000 else '❌ FAIL'}</td>
            </tr>
            <tr>
                <td>Average Response Time</td>
                <td>{avg_response_time:.0f}ms</td>
                <td><2000ms</td>
                <td class="{'status-pass' if avg_response_time < 2000 else 'status-fail'}">{'✅ PASS' if avg_response_time < 2000 else '❌ FAIL'}</td>
            </tr>
        </table>
        
        <h2>Request Statistics by Endpoint</h2>
        {stats_df.to_html(index=False, classes='stats-table', border=0) if not stats_df.empty else '<p>No statistics available</p>'}
        
        <h2>Failure Analysis</h2>
        {failures_df.to_html(index=False, classes='failures-table', border=0) if not failures_df.empty else '<p>No failures recorded - Excellent! ✅</p>'}
        
        <h2>Recommendations</h2>
        <ul>
            {'<li>✅ System performed well under load - Ready for production!</li>' if success_rate > 99 and p95 < 3000 else '<li>⚠️ Review failing endpoints and optimize response times</li>'}
            {'<li>✅ Response times within acceptable range</li>' if p95 < 3000 else '<li>⚠️ Consider optimizing slow endpoints or scaling resources</li>'}
            {'<li>✅ No significant failures detected</li>' if total_failures < 100 else '<li>⚠️ Investigate root cause of failures</li>'}
        </ul>
        
        <h2>Next Steps</h2>
        <ol>
            <li>Review this report with the team</li>
            <li>Address any failing metrics</li>
            <li>Update TEST_RESULTS.md with findings</li>
            <li>Schedule production deployment if all tests pass</li>
        </ol>
    </div>
</body>
</html>
"""
    
    # Write HTML
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Report generated: {output_file}")
    
    # Print summary to console
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total Requests:    {total_requests:,}")
    print(f"Total Failures:    {total_failures:,}")
    print(f"Success Rate:      {success_rate:.2f}%")
    print(f"P95 Response Time: {p95:.0f}ms")
    print(f"P99 Response Time: {p99:.0f}ms")
    print(f"Avg Response Time: {avg_response_time:.0f}ms")
    print("="*60)
    
    if success_rate > 99 and p95 < 3000:
        print("✅ TEST PASSED - System ready for production!")
    else:
        print("❌ TEST FAILED - Review metrics and optimize")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Analyze load test results')
    parser.add_argument('--input', required=True, help='Input directory with CSV files')
    parser.add_argument('--output', default='load_test_report.html', help='Output HTML file')
    
    args = parser.parse_args()
    
    print(f"Loading results from: {args.input}")
    requests_df, stats_df, failures_df = load_results(args.input)
    
    print(f"Generating report: {args.output}")
    generate_report(requests_df, stats_df, failures_df, args.output)


if __name__ == '__main__':
    main()
```

---

## Sign-Off

**Test Executed By:** ________________  
**Date:** ________________  
**Result:** PASS / FAIL  

**Test Duration:** _____ hours _____ minutes  

**Total Requests:** ________________  
**Success Rate:** _____%  
**P95 Response Time:** _____ms  
**P99 Response Time:** _____ms  

**Issues Found:**
1. ________________
2. ________________
3. ________________

**Approved By:** ________________  
**Date:** ________________  

---

## Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | Apr 2, 2026 | Initial version | [Your Name] |
| 1.1 | Apr 2, 2026 | Added local test guide | [Your Name] |

---

**Document Status:** ✅ Complete  
**Last Updated:** April 2, 2026  
**Version:** 1.1
