"""
Load Testing Script for Customer Success FTE

Uses Locust to simulate realistic load across all channels.

Installation:
    pip install locust

Usage:
    # Start Locust server
    locust -f tests/load_test.py --host=http://localhost:8000
    
    # Or run headless (no web UI)
    locust -f tests/load_test.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 300s
    
    Parameters:
    -u 100    : 100 concurrent users
    -r 10     : Spawn 10 users per second
    -t 300s   : Run for 300 seconds (5 minutes)

Results:
    - Web UI at http://localhost:8089
    - CSV reports in ./load_test_results/
    - HTML report with --html=report.html
"""

from locust import HttpUser, task, between, events
import random
import json
import time
from datetime import datetime


class WebFormUser(HttpUser):
    """
    Simulate users submitting support forms.
    
    This is the most common user type - customers visiting the website
    and submitting support requests via the web form.
    """
    
    wait_time = between(2, 10)  # Wait 2-10 seconds between tasks
    weight = 3  # 3x more common than other user types
    
    # Test data templates
    subjects = [
        "Help with API authentication",
        "Question about pricing",
        "Bug report: Login not working",
        "Feature request: Dark mode",
        "How to export data",
        "Integration with Slack",
        "Password reset not working",
        "Billing inquiry",
        "Account deletion request",
        "Performance issues"
    ]
    
    categories = ['general', 'technical', 'billing', 'feedback', 'bug_report']
    
    messages = [
        "I'm having trouble authenticating with the API. I've tried using my API key but keep getting 401 errors. Can you help?",
        "Your product is amazing! But I noticed the mobile app could use some improvements. Any plans for updates?",
        "The dashboard is loading very slowly for me. It takes about 30 seconds to show any data. Is this a known issue?",
        "How do I export my data to CSV? I've looked through the documentation but couldn't find this feature.",
        "I'd like to request a feature: it would be great if you could add integration with Slack for notifications.",
        "I've been charged twice for my subscription this month. Can you please look into this billing issue?",
        "The password reset email never arrived. I've checked my spam folder. Can you help me reset my password?",
        "Your customer support is terrible! I've been waiting 3 days for a response. This is unacceptable!",
        "Is there a way to bulk update records? I have hundreds of entries to update and doing it one by one is tedious.",
        "I love the new features! Especially the dark mode. But I noticed a few bugs in the mobile app."
    ]
    
    @task
    def submit_support_form(self):
        """Submit a support form with realistic data."""
        
        # Generate unique email for each submission
        timestamp = datetime.now().timestamp()
        test_email = f"loadtest_{int(timestamp) % 100000}@example.com"
        
        payload = {
            "customer_email": test_email,
            "subject": random.choice(self.subjects),
            "message": random.choice(self.messages),
            "channel": "web_form",
            "category": random.choice(self.categories),
            "priority": random.choice(["low", "medium", "high"])
        }
        
        with self.client.post(
            "/api/v1/messages/submit",
            json=payload,
            headers={"X-API-Key": "dev-api-key-12345"},
            catch_response=True
        ) as response:
            if response.status_code == 202:
                response.success()
                
                # Optionally check status after submission
                request_id = response.json().get("request_id")
                if request_id:
                    # Wait a bit then check status
                    time.sleep(2)
                    self.client.get(
                        f"/api/v1/messages/status/{request_id}",
                        headers={"X-API-Key": "dev-api-key-12345"},
                        name="/api/v1/messages/status/[request_id]"
                    )
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(2)
    def check_ticket_status(self):
        """Check status of existing tickets."""
        
        # Use a random request ID (in real scenario, would be from previous submission)
        fake_request_id = f"test-{random.randint(10000, 99999)}"
        
        self.client.get(
            f"/api/v1/messages/status/{fake_request_id}",
            headers={"X-API-Key": "dev-api-key-12345"},
            name="/api/v1/messages/status/[request_id]"
        )


class HealthCheckUser(HttpUser):
    """
    Monitor system health during load test.
    
    This simulates monitoring systems and health check endpoints
    being polled regularly.
    """
    
    wait_time = between(5, 15)  # Check every 5-15 seconds
    weight = 1
    
    @task(3)
    def check_health(self):
        """Check basic health endpoint."""
        self.client.get("/health/live", name="/health/live")
    
    @task(2)
    def check_ready(self):
        """Check readiness endpoint."""
        self.client.get("/health/ready", name="/health/ready")
    
    @task(1)
    def check_metrics(self):
        """Check metrics endpoint."""
        self.client.get("/api/v1/metrics", name="/api/v1/metrics")


class APIPowerUser(HttpUser):
    """
    Simulate power users making multiple API calls.
    
    This represents enterprise customers or integrations
    that make frequent API calls.
    """
    
    wait_time = between(1, 5)  # Very active users
    weight = 1
    
    @task
    def submit_and_track(self):
        """Submit a ticket and track it through completion."""
        
        timestamp = datetime.now().timestamp()
        test_email = f"poweruser_{int(timestamp) % 10000}@example.com"
        
        # Submit ticket
        submit_response = self.client.post(
            "/api/v1/messages/submit",
            json={
                "customer_email": test_email,
                "subject": "Load Test - Power User",
                "message": "This is a test submission from a power user during load testing.",
                "channel": "web_form"
            },
            headers={"X-API-Key": "dev-api-key-12345"},
            name="/api/v1/messages/submit"
        )
        
        if submit_response.status_code == 202:
            request_id = submit_response.json().get("request_id")
            
            # Poll status multiple times
            for i in range(5):
                time.sleep(1)
                self.client.get(
                    f"/api/v1/messages/status/{request_id}",
                    headers={"X-API-Key": "dev-api-key-12345"},
                    name="/api/v1/messages/status/[request_id]"
                )


class BatchSubmitterUser(HttpUser):
    """
    Simulate batch submissions (bulk imports, integrations).
    
    This represents scenarios where multiple tickets are submitted
    in quick succession.
    """
    
    wait_time = between(10, 30)
    weight = 1
    
    @task
    def batch_submit(self):
        """Submit multiple tickets in a batch."""
        
        batch_size = random.randint(5, 20)
        
        for i in range(batch_size):
            timestamp = datetime.now().timestamp()
            test_email = f"batch_{int(timestamp) % 10000}_{i}@example.com"
            
            self.client.post(
                "/api/v1/messages/submit",
                json={
                    "customer_email": test_email,
                    "subject": f"Batch Test - Item {i+1}/{batch_size}",
                    "message": "This is a batch submission test.",
                    "channel": "web_form"
                },
                headers={"X-API-Key": "dev-api-key-12345"},
                name="/api/v1/messages/submit (batch)"
            )
            
            # Small delay between submissions
            time.sleep(0.5)


# ============================================================================
# Event Hooks
# ============================================================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("\n" + "="*60)
    print("🚀 Load Test Starting")
    print("="*60)
    print(f"Target Host: {environment.host}")
    print(f"Start Time: {datetime.now().isoformat()}")
    print("="*60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    print("\n" + "="*60)
    print("✅ Load Test Complete")
    print("="*60)
    print(f"End Time: {datetime.now().isoformat()}")
    
    # Print statistics
    stats = environment.stats
    print(f"\nTotal Requests: {stats.total.num_requests}")
    print(f"Failed Requests: {stats.total.num_failures}")
    print(f"Success Rate: {(1 - stats.total.fail_ratio) * 100:.2f}%")
    print(f"Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"P95 Response Time: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"P99 Response Time: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print("="*60 + "\n")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Called on each request - can be used for custom logging."""
    if exception:
        print(f"❌ Request failed: {name} - {exception}")


# ============================================================================
# Performance Requirements
# ============================================================================

"""
Target Performance Metrics:

┌─────────────────────────────────┬──────────────┬──────────────┐
│ Metric                          │ Target       │ Critical     │
├─────────────────────────────────┼──────────────┼──────────────┤
│ P95 Response Time               │ < 2000ms     │ > 5000ms     │
│ P99 Response Time               │ < 3000ms     │ > 8000ms     │
│ Success Rate                    │ > 99%        │ < 95%        │
│ Requests/sec (sustained)        │ > 100        │ < 50         │
│ Concurrent Users                │ > 200        │ < 100        │
└─────────────────────────────────┴──────────────┴──────────────┘

Test Scenarios:

1. Smoke Test (2 minutes)
   - 10 users, spawn 2/sec
   - Verify basic functionality
   
2. Load Test (10 minutes)
   - 100 users, spawn 10/sec
   - Test normal operating conditions
   
3. Stress Test (15 minutes)
   - 500 users, spawn 50/sec
   - Find breaking point
   
4. Endurance Test (4 hours)
   - 50 users, spawn 5/sec
   - Test for memory leaks, stability
   
5. Spike Test (5 minutes)
   - Suddenly increase from 10 to 200 users
   - Test auto-scaling response
"""


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import os
    
    print("\n" + "="*60)
    print("📊 Customer Success FTE - Load Test Suite")
    print("="*60)
    print("\nAvailable test commands:")
    print("\n1. Start Locust Web UI:")
    print("   locust -f tests/load_test.py --host=http://localhost:8000")
    print("\n2. Run Headless Load Test (100 users, 10 min):")
    print("   locust -f tests/load_test.py --host=http://localhost:8000 \\")
    print("     --headless -u 100 -r 10 -t 600s")
    print("\n3. Run Stress Test (500 users):")
    print("   locust -f tests/load_test.py --host=http://localhost:8000 \\")
    print("     --headless -u 500 -r 50 -t 900s")
    print("\n4. Run Endurance Test (4 hours):")
    print("   locust -f tests/load_test.py --host=http://localhost:8000 \\")
    print("     --headless -u 50 -r 5 -t 14400s")
    print("\n" + "="*60)
    print("\nOpen http://localhost:8089 in browser to view real-time metrics")
    print("="*60 + "\n")
