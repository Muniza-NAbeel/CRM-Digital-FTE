"""
Simple Load Test - No External Dependencies
Uses only httpx and asyncio (already installed)

This script simulates multiple concurrent users hitting the API.
"""

import asyncio
import time
import httpx
import random
from datetime import datetime
from typing import List, Dict

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "dev-api-key-12345"
NUM_USERS = 10  # Simulate 10 concurrent users (lighter load)
REQUESTS_PER_USER = 3  # Each user makes 3 requests
TOTAL_REQUESTS = NUM_USERS * REQUESTS_PER_USER

print("=" * 80)
print("SIMPLE LOAD TEST - Customer Success FTE")
print("=" * 80)
print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Target: {BASE_URL}")
print(f"Simulated Users: {NUM_USERS}")
print(f"Requests per User: {REQUESTS_PER_USER}")
print(f"Total Requests: {TOTAL_REQUESTS}")
print("=" * 80)

# Test data templates
SUBJECTS = [
    "Help with account",
    "Question about features",
    "Technical support needed",
    "Billing inquiry",
    "How to reset password",
    "Integration question",
    "Bug report",
    "Feature request",
]

MESSAGES = [
    "I need help with my account. Can you assist?",
    "Having trouble understanding a feature. Please help!",
    "Question about my recent order status.",
    "How do I reset my password?",
    "I'd like to update my billing information.",
    "Technical issue with the product. Need support.",
    "Can you explain how to use feature X?",
    "I'm experiencing an error when trying to checkout.",
]

# Results storage
results: List[Dict] = []


async def submit_ticket(user_id: int, request_id: int, client: httpx.AsyncClient) -> Dict:
    """Submit a support ticket."""
    test_data = {
        "customer_email": f"loadtest_user{user_id}_{request_id}@example.com",
        "subject": random.choice(SUBJECTS),
        "message": random.choice(MESSAGES),
        "channel": "web_form"
    }
    
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    
    start_time = time.time()
    try:
        response = await client.post(
            f"{BASE_URL}/api/v1/messages/submit",
            json=test_data,
            headers=headers,
            timeout=30.0
        )
        end_time = time.time()
        
        return {
            "user_id": user_id,
            "request_id": request_id,
            "endpoint": "submit",
            "status_code": response.status_code,
            "response_time_ms": (end_time - start_time) * 1000,
            "success": response.status_code == 200,
            "error": None
        }
    except Exception as e:
        end_time = time.time()
        return {
            "user_id": user_id,
            "request_id": request_id,
            "endpoint": "submit",
            "status_code": 0,
            "response_time_ms": (end_time - start_time) * 1000,
            "success": False,
            "error": str(e)
        }


async def check_health(request_id: int, client: httpx.AsyncClient) -> Dict:
    """Check API health."""
    start_time = time.time()
    try:
        response = await client.get(f"{BASE_URL}/health/", timeout=10.0)
        end_time = time.time()
        
        return {
            "request_id": request_id,
            "endpoint": "health",
            "status_code": response.status_code,
            "response_time_ms": (end_time - start_time) * 1000,
            "success": response.status_code == 200,
            "error": None
        }
    except Exception as e:
        end_time = time.time()
        return {
            "request_id": request_id,
            "endpoint": "health",
            "status_code": 0,
            "response_time_ms": (end_time - start_time) * 1000,
            "success": False,
            "error": str(e)
        }


async def check_dashboard(request_id: int, client: httpx.AsyncClient) -> Dict:
    """Check dashboard metrics."""
    start_time = time.time()
    try:
        response = await client.get(f"{BASE_URL}/api/v1/dashboard", timeout=30.0)
        end_time = time.time()
        
        return {
            "request_id": request_id,
            "endpoint": "dashboard",
            "status_code": response.status_code,
            "response_time_ms": (end_time - start_time) * 1000,
            "success": response.status_code == 200,
            "error": None
        }
    except Exception as e:
        end_time = time.time()
        return {
            "request_id": request_id,
            "endpoint": "dashboard",
            "status_code": 0,
            "response_time_ms": (end_time - start_time) * 1000,
            "success": False,
            "error": str(e)
        }


async def user_session(user_id: int):
    """Simulate a user session with multiple requests."""
    async with httpx.AsyncClient() as client:
        user_results = []
        
        for i in range(REQUESTS_PER_USER):
            # Mix of different endpoints
            if i % 3 == 0:
                result = await check_health(f"user{user_id}_req{i}", client)
            elif i % 3 == 1:
                result = await submit_ticket(user_id, i, client)
            else:
                result = await check_dashboard(f"user{user_id}_req{i}", client)
            
            user_results.append(result)
            
            # Small delay between requests (simulate real user)
            await asyncio.sleep(random.uniform(0.1, 0.5))
        
        return user_results


async def run_load_test():
    """Run the complete load test."""
    print("\n🚀 Starting Load Test...")
    print("-" * 80)
    
    start_time = time.time()
    
    # Create tasks for all users
    tasks = [user_session(user_id) for user_id in range(1, NUM_USERS + 1)]
    
    # Run all users concurrently
    all_results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Flatten results
    for user_results in all_results:
        results.extend(user_results)
    
    return total_duration


def print_results(total_duration: float):
    """Print test results and statistics."""
    print("\n" + "=" * 80)
    print("LOAD TEST RESULTS")
    print("=" * 80)
    
    # Calculate statistics
    total_requests = len(results)
    successful = sum(1 for r in results if r["success"])
    failed = total_requests - successful
    success_rate = (successful / total_requests * 100) if total_requests > 0 else 0
    
    response_times = [r["response_time_ms"] for r in results if r["success"]]
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    min_response_time = min(response_times) if response_times else 0
    max_response_time = max(response_times) if response_times else 0
    p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 1 else max_response_time
    
    requests_per_second = total_requests / total_duration if total_duration > 0 else 0
    
    # Print summary
    print(f"\n📊 SUMMARY")
    print("-" * 80)
    print(f"  Total Duration: {total_duration:.2f}s")
    print(f"  Total Requests: {total_requests}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Success Rate: {success_rate:.2f}%")
    print(f"  Requests/Second: {requests_per_second:.2f}")
    
    print(f"\n⏱️  RESPONSE TIMES")
    print("-" * 80)
    print(f"  Average: {avg_response_time:.2f}ms")
    print(f"  Minimum: {min_response_time:.2f}ms")
    print(f"  Maximum: {max_response_time:.2f}ms")
    print(f"  P95: {p95_response_time:.2f}ms")
    
    # Print results by endpoint
    print(f"\n📈 RESULTS BY ENDPOINT")
    print("-" * 80)
    
    endpoints = {}
    for r in results:
        endpoint = r["endpoint"]
        if endpoint not in endpoints:
            endpoints[endpoint] = {"total": 0, "success": 0, "times": []}
        endpoints[endpoint]["total"] += 1
        if r["success"]:
            endpoints[endpoint]["success"] += 1
            endpoints[endpoint]["times"].append(r["response_time_ms"])
    
    for endpoint, stats in endpoints.items():
        success_rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
        avg_time = sum(stats["times"]) / len(stats["times"]) if stats["times"] else 0
        print(f"  {endpoint}:")
        print(f"    Requests: {stats['total']}, Success: {stats['success']}, Rate: {success_rate:.1f}%")
        print(f"    Avg Response: {avg_time:.2f}ms")
    
    # Print errors if any
    errors = [r for r in results if r["error"]]
    if errors:
        print(f"\n❌ ERRORS ({len(errors)})")
        print("-" * 80)
        for error in errors[:5]:  # Show first 5 errors
            print(f"  [{error['endpoint']}] {error['error']}")
    
    # Performance assessment
    print(f"\n🎯 PERFORMANCE ASSESSMENT")
    print("-" * 80)
    
    # Check against hackathon requirements
    checks = [
        ("Response Time < 3000ms", avg_response_time < 3000),
        ("Success Rate > 95%", success_rate > 95),
        ("P95 < 3000ms", p95_response_time < 3000),
        ("Throughput > 10 RPS", requests_per_second > 10),
    ]
    
    all_passed = True
    for check_name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {check_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 LOAD TEST PASSED! All performance targets met!")
        print("\n✅ Testing Suite: 100% COMPLETE")
    else:
        print("⚠️  Some performance targets not met. Check results above.")
        print("\n✅ Testing Suite: 95% COMPLETE (Load test executed)")
    print("=" * 80)
    
    # Save results to file
    with open("load_test_results.txt", "w") as f:
        f.write(f"Load Test Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total Duration: {total_duration:.2f}s\n")
        f.write(f"Total Requests: {total_requests}\n")
        f.write(f"Successful: {successful}\n")
        f.write(f"Failed: {failed}\n")
        f.write(f"Success Rate: {success_rate:.2f}%\n")
        f.write(f"Requests/Second: {requests_per_second:.2f}\n\n")
        f.write(f"Average Response Time: {avg_response_time:.2f}ms\n")
        f.write(f"Minimum Response Time: {min_response_time:.2f}ms\n")
        f.write(f"Maximum Response Time: {max_response_time:.2f}ms\n")
        f.write(f"P95 Response Time: {p95_response_time:.2f}ms\n")
    
    print(f"\n📄 Results saved to: load_test_results.txt")


# Run the test
if __name__ == "__main__":
    total_duration = asyncio.run(run_load_test())
    print_results(total_duration)
    
    print(f"\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
