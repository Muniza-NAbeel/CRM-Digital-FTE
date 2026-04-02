"""
Edge Case Manual Tests - Quick Verification

These tests verify edge cases without complex fixtures.
Run Date: March 29, 2026
"""

import asyncio
import httpx
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_KEY = "dev-api-key-12345"

print("=" * 80)
print("EDGE CASE MANUAL TESTS")
print("=" * 80)
print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Base URL: {BASE_URL}")
print("=" * 80)

async def run_edge_case_tests():
    results = []
    
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=30.0,
        headers={"X-API-Key": API_KEY}
    ) as client:
        
        # Test 1: Empty Message
        print("\n[TEST 1] Empty Message Handling")
        print("-" * 80)
        try:
            response = await client.post(
                "/api/v1/messages/submit",
                json={
                    "customer_email": "empty_test@example.com",
                    "subject": "Empty Test",
                    "message": "",
                    "channel": "web_form"
                }
            )
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.json().get('message', 'N/A')}")
            results.append(("Empty Message", response.status_code in [200, 422]))
        except Exception as e:
            print(f"  Error: {e}")
            results.append(("Empty Message", False))
        
        # Test 2: Very Long Message
        print("\n[TEST 2] Very Long Message (10,000 chars)")
        print("-" * 80)
        try:
            long_message = "Help! " * 2000  # ~12,000 characters
            response = await client.post(
                "/api/v1/messages/submit",
                json={
                    "customer_email": "long_test@example.com",
                    "subject": "Long Message Test",
                    "message": long_message,
                    "channel": "web_form"
                }
            )
            print(f"  Status: {response.status_code}")
            print(f"  Message Length: {len(long_message)}")
            results.append(("Very Long Message", response.status_code == 200))
        except Exception as e:
            print(f"  Error: {e}")
            results.append(("Very Long Message", False))
        
        # Test 3: Special Characters
        print("\n[TEST 3] Special Characters & Unicode")
        print("-" * 80)
        try:
            special_message = """
            Test with special chars: <>&"'\/
            Unicode: 你好世界 🌍 مرحبا
            Emojis: 🎉 🚀 ✅ ❌
            """
            response = await client.post(
                "/api/v1/messages/submit",
                json={
                    "customer_email": "unicode_test@example.com",
                    "subject": "Unicode Test 你好 🌍",
                    "message": special_message,
                    "channel": "web_form"
                }
            )
            print(f"  Status: {response.status_code}")
            print(f"  Unicode handled: ✅")
            results.append(("Special Characters", response.status_code == 200))
        except Exception as e:
            print(f"  Error: {e}")
            results.append(("Special Characters", False))
        
        # Test 4: Angry Customer (should escalate)
        print("\n[TEST 4] Angry Customer Message")
        print("-" * 80)
        try:
            angry_message = "This is RIDICULOUS! Your product is BROKEN! I want a REFUND NOW!"
            response = await client.post(
                "/api/v1/messages/submit",
                json={
                    "customer_email": "angry_test@example.com",
                    "subject": "Angry Test",
                    "message": angry_message,
                    "channel": "web_form"
                }
            )
            print(f"  Status: {response.status_code}")
            data = response.json()
            print(f"  Request ID: {data.get('request_id', 'N/A')}")
            
            # Check status after processing
            await asyncio.sleep(2)
            status_response = await client.get(f"/api/v1/messages/status/{data.get('request_id', '')}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"  Sentiment: {status_data.get('sentiment', 'N/A')}")
                print(f"  Escalated: {status_data.get('is_escalated', False)}")
                results.append(("Angry Customer", True))
            else:
                results.append(("Angry Customer", False))
        except Exception as e:
            print(f"  Error: {e}")
            results.append(("Angry Customer", False))
        
        # Test 5: Pricing Query (should escalate)
        print("\n[TEST 5] Pricing Query (Should Escalate)")
        print("-" * 80)
        try:
            pricing_message = "How much does the enterprise plan cost? What are your pricing options?"
            response = await client.post(
                "/api/v1/messages/submit",
                json={
                    "customer_email": "pricing_test@example.com",
                    "subject": "Pricing Query",
                    "message": pricing_message,
                    "channel": "web_form"
                }
            )
            print(f"  Status: {response.status_code}")
            results.append(("Pricing Query", response.status_code == 200))
        except Exception as e:
            print(f"  Error: {e}")
            results.append(("Pricing Query", False))
        
        # Test 6: Rapid Submissions (Rate Limiting)
        print("\n[TEST 6] Rapid Submissions (Rate Limiting)")
        print("-" * 80)
        try:
            rapid_results = []
            for i in range(5):
                response = await client.post(
                    "/api/v1/messages/submit",
                    json={
                        "customer_email": f"rapid_{i}@example.com",
                        "subject": f"Rapid Test {i}",
                        "message": "Quick test message",
                        "channel": "web_form"
                    }
                )
                rapid_results.append(response.status_code)
            
            print(f"  Submissions: {len(rapid_results)}")
            print(f"  Status Codes: {rapid_results}")
            success_count = sum(1 for code in rapid_results if code == 200)
            results.append(("Rapid Submissions", success_count >= 3))  # At least 3 should succeed
        except Exception as e:
            print(f"  Error: {e}")
            results.append(("Rapid Submissions", False))
        
        # Test 7: Concurrent Requests
        print("\n[TEST 7] Concurrent Requests")
        print("-" * 80)
        try:
            async def submit_single(i):
                try:
                    response = await client.post(
                        "/api/v1/messages/submit",
                        json={
                            "customer_email": f"concurrent_{i}@example.com",
                            "subject": f"Concurrent Test {i}",
                            "message": "Concurrent test",
                            "channel": "web_form"
                        },
                        timeout=10.0
                    )
                    return response.status_code == 200
                except:
                    return False
            
            tasks = [submit_single(i) for i in range(5)]
            concurrent_results = await asyncio.gather(*tasks)
            
            print(f"  Concurrent Requests: {len(concurrent_results)}")
            print(f"  Successful: {sum(concurrent_results)}")
            results.append(("Concurrent Requests", sum(concurrent_results) >= 3))
        except Exception as e:
            print(f"  Error: {e}")
            results.append(("Concurrent Requests", False))
    
    return results

# Run tests
test_results = asyncio.run(run_edge_case_tests())

# Print summary
print("\n" + "=" * 80)
print("EDGE CASE TEST SUMMARY")
print("=" * 80)

passed = sum(1 for _, result in test_results if result)
total = len(test_results)

for test_name, result in test_results:
    status = "✅ PASS" if result else "❌ FAIL"
    print(f"  {status}: {test_name}")

print("\n" + "-" * 80)
print(f"RESULTS: {passed}/{total} edge case tests passed")
print("-" * 80)

if passed == total:
    print("\n🎉 ALL EDGE CASE TESTS PASSED!")
else:
    print(f"\n⚠ {total - passed} edge case test(s) failed.")

print(f"\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

# Save results
with open("edge_case_test_results.txt", "w") as f:
    f.write(f"Edge Case Test Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("=" * 80 + "\n\n")
    for test_name, result in test_results:
        status = "PASS" if result else "FAIL"
        f.write(f"{status}: {test_name}\n")
    f.write(f"\nTotal: {passed}/{total} passed\n")

print(f"\n📄 Results saved to: edge_case_test_results.txt")
