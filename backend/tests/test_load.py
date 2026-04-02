"""
Load Testing for Customer Success Digital FTE

Uses Locust for load testing.
Install: pip install locust

Run:
    locust -f tests/test_load.py --host=http://localhost:8000

Or headless:
    locust -f tests/test_load.py --host=http://localhost:8000 --headless -u 100 -r 10 --run-time 5m
"""

import random
import time
import json
from uuid import uuid4
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner


# ============================================================================
# Test Data Generators
# ============================================================================

def generate_email() -> str:
    """Generate random email."""
    return f"loadtest_{uuid4().hex[:8]}@example.com"


def generate_message() -> str:
    """Generate random support message."""
    templates = [
        "I need help with my account. Can you assist?",
        "Having trouble logging in. Please help!",
        "Question about my recent order status.",
        "How do I reset my password?",
        "I'd like to update my billing information.",
        "Technical issue with the product. Need support.",
        "Can you explain how to use feature X?",
        "I'm experiencing an error when trying to checkout.",
        "Need help setting up my profile.",
        "Question about your service pricing.",
    ]
    return random.choice(templates)


def generate_angry_message() -> str:
    """Generate angry customer message."""
    templates = [
        "This is unacceptable! Fix it now!",
        "I'm very disappointed with your service!",
        "Your product is terrible! I want a refund!",
        "This is the worst experience ever!",
        "I've been waiting for days! No response!",
    ]
    return random.choice(templates)


# ============================================================================
# Load Test User Classes
# ============================================================================

class WebFormUser(HttpUser):
    """
    Simulates users submitting web forms.
    """
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    @task(3)
    def submit_support_form(self):
        """Submit a support form."""
        self.client.post(
            "/api/v1/tickets",
            json={
                "customer_email": generate_email(),
                "subject": f"Support Request {uuid4().hex[:6]}",
                "description": generate_message(),
                "channel": "web_form",
            },
            name="/api/v1/tickets",
        )
    
    @task(1)
    def check_health(self):
        """Check API health."""
        self.client.get("/health/ready", name="/health/ready")
    
    @task(1)
    def get_tickets(self):
        """List tickets (paginated)."""
        self.client.get(
            "/api/v1/tickets",
            params={"page": 1, "page_size": 10},
            name="/api/v1/tickets [GET]",
        )


class AngryCustomerUser(HttpUser):
    """
    Simulates angry customers (tests escalation).
    """
    
    wait_time = between(2, 5)
    
    @task
    def submit_angry_message(self):
        """Submit angry message."""
        self.client.post(
            "/api/v1/tickets",
            json={
                "customer_email": generate_email(),
                "subject": "COMPLAINT",
                "description": generate_angry_message(),
                "channel": "web_form",
            },
            name="/api/v1/tickets (angry)",
        )


class APIPollerUser(HttpUser):
    """
    Simulates users polling for ticket status.
    """
    
    wait_time = between(0.5, 2)
    
    @task(2)
    def poll_ticket_status(self):
        """Poll ticket status."""
        ticket_id = getattr(self, "_ticket_id", None)
        
        if not ticket_id:
            # Create a ticket first
            response = self.client.post(
                "/api/v1/tickets",
                json={
                    "customer_email": generate_email(),
                    "subject": "Poll Test",
                    "description": "Testing polling",
                    "channel": "web_form",
                },
                name="/api/v1/tickets [CREATE]",
            )
            if response.status_code == 201:
                self._ticket_id = response.json().get("id")
        else:
            # Check status
            self.client.get(
                f"/api/v1/tickets/{ticket_id}",
                name="/api/v1/tickets/{id} [GET]",
            )
    
    @task(1)
    def check_health(self):
        """Health check."""
        self.client.get("/health/live", name="/health/live")


class MixedChannelUser(HttpUser):
    """
    Simulates users across different channels.
    """
    
    wait_time = between(1, 4)
    
    @task(2)
    def web_form_submission(self):
        """Web form submission."""
        self.client.post(
            "/api/v1/tickets",
            json={
                "customer_email": generate_email(),
                "subject": f"Mixed Test {uuid4().hex[:6]}",
                "description": generate_message(),
                "channel": "web_form",
            },
            name="/api/v1/tickets (web)",
        )
    
    @task(1)
    def whatsapp_webhook(self):
        """Simulate WhatsApp webhook."""
        self.client.post(
            "/webhooks/whatsapp",
            data={
                "MessageSid": f"SM{uuid4().hex[:10]}",
                "ConversationSid": f"CH{uuid4().hex[:10]}",
                "AccountSid": "AC_TEST",
                "Body": generate_message(),
                "From": f"whatsapp:+1415555{random.randint(1000, 9999)}",
                "To": "whatsapp:+14155558886",
            },
            name="/webhooks/whatsapp",
        )


# ============================================================================
# Stress Test Scenarios
# ============================================================================

class StressTestUser(HttpUser):
    """
    High-intensity stress testing.
    """
    
    wait_time = between(0.1, 0.5)  # Very short wait
    
    @task
    def rapid_fire_tickets(self):
        """Rapid ticket creation."""
        self.client.post(
            "/api/v1/tickets",
            json={
                "customer_email": generate_email(),
                "subject": f"Stress {uuid4().hex[:6]}",
                "description": generate_message(),
                "channel": "web_form",
            },
            name="/api/v1/tickets [STRESS]",
        )


# ============================================================================
# Load Test Configuration
# ============================================================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("=" * 60)
    print("Customer Success Digital FTE - Load Test Starting")
    print("=" * 60)
    print(f"Target: {environment.host}")
    print(f"Users: WebForm, AngryCustomer, APIPoller, MixedChannel")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    print("=" * 60)
    print("Load Test Complete")
    print("=" * 60)
    
    # Print summary statistics
    stats = environment.stats
    print(f"Total Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Failure Rate: {stats.total.num_failures / max(stats.total.num_requests, 1) * 100:.2f}%")
    print(f"Avg Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"Requests/sec: {stats.total.current_rps:.2f}")
    print("=" * 60)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, 
               context, exception, start_time, url, **kwargs):
    """Called on each request."""
    if exception:
        print(f"Request failed: {name} - {exception}")


# ============================================================================
# Custom Load Test Scenarios
# ============================================================================

def run_load_test(
    host: str = "http://localhost:8000",
    users: int = 50,
    spawn_rate: int = 10,
    duration: str = "5m",
):
    """
    Programmatically run load test.
    
    Usage:
        from tests.test_load import run_load_test
        run_load_test(users=100, spawn_rate=20, duration="10m")
    """
    import subprocess
    import sys
    
    cmd = [
        sys.executable, "-m", "locust",
        "-f", __file__,
        "--host", host,
        "--headless",
        "-u", str(users),
        "-r", str(spawn_rate),
        "--run-time", duration,
    ]
    
    subprocess.run(cmd)


# ============================================================================
# Performance Thresholds
# ============================================================================

@events.quitting.add_listener
def check_performance_thresholds(environment, **kwargs):
    """
    Check performance thresholds and fail if not met.
    """
    stats = environment.stats.total
    
    # Thresholds
    MAX_AVG_RESPONSE_TIME = 1000  # ms
    MAX_FAILURE_RATE = 5  # percent
    MIN_RPS = 10  # requests per second
    
    issues = []
    
    if stats.avg_response_time > MAX_AVG_RESPONSE_TIME:
        issues.append(
            f"Avg response time {stats.avg_response_time:.0f}ms "
            f"exceeds threshold {MAX_AVG_RESPONSE_TIME}ms"
        )
    
    failure_rate = (stats.num_failures / max(stats.num_requests, 1)) * 100
    if failure_rate > MAX_FAILURE_RATE:
        issues.append(
            f"Failure rate {failure_rate:.1f}% "
            f"exceeds threshold {MAX_FAILURE_RATE}%"
        )
    
    if stats.current_rps < MIN_RPS:
        issues.append(
            f"RPS {stats.current_rps:.1f} "
            f"below minimum {MIN_RPS}"
        )
    
    if issues:
        print("\n⚠️  Performance Thresholds NOT Met:")
        for issue in issues:
            print(f"  - {issue}")
        # Uncomment to fail CI/CD
        # environment.process_exit_code = 1
    else:
        print("\n✅ All Performance Thresholds Met!")


# ============================================================================
# Worker/Master Configuration (for distributed load testing)
# ============================================================================

def is_master():
    """Check if running as master."""
    import os
    return os.getenv("LOCUST_MODE") == "master"


def is_worker():
    """Check if running as worker."""
    import os
    return os.getenv("LOCUST_MODE") == "worker"


if is_master():
    # Master configuration
    class MasterUser(HttpUser):
        wait_time = between(1, 2)
        
        @task
        def dummy(self):
            pass  # Master doesn't make requests

elif is_worker():
    # Worker configuration
    pass  # Workers use the defined user classes


# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    import os
    os.system("locust -f tests/test_load.py --host=http://localhost:8000")
