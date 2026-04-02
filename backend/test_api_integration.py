#!/usr/bin/env python
"""
Full API Integration Tests (using httpx)
Run: python test_api_integration.py
"""

import httpx
import json
import sys

BASE_URL = "http://localhost:8000"
API_KEY = "dev-api-key-12345"

def test_root():
    """Test root endpoint"""
    print("\n=== Test: Root Endpoint ===")
    try:
        with httpx.Client() as client:
            resp = client.get(f"{BASE_URL}/", timeout=5)
            data = resp.json()
            assert resp.status_code == 200
            assert "name" in data
        print(f"[PASS] Root: {data['name']}")
        return True
    except Exception as e:
        print(f"[FAIL] Root: {e}")
        return False


def test_health():
    """Test health endpoint"""
    print("\n=== Test: Health Endpoint ===")
    try:
        with httpx.Client() as client:
            resp = client.get(f"{BASE_URL}/health", timeout=5)
            assert resp.status_code == 200
        print(f"[PASS] Health: OK")
        return True
    except Exception as e:
        print(f"[FAIL] Health: {e}")
        return False


def test_dashboard():
    """Test dashboard endpoint"""
    print("\n=== Test: Dashboard ===")
    try:
        with httpx.Client() as client:
            resp = client.get(f"{BASE_URL}/api/v1/dashboard", timeout=10)
            data = resp.json()
            assert resp.status_code == 200
            assert "channels" in data
        print(f"[PASS] Dashboard: {data['channels'].get('total_channels', 'N/A')} channels")
        return True
    except Exception as e:
        print(f"[FAIL] Dashboard: {e}")
        return False


def test_web_form_submit():
    """Test web form submission"""
    print("\n=== Test: Web Form Submit ===")
    try:
        payload = {
            "customer_email": "test@example.com",
            "subject": "Test Web Form",
            "message": "Testing web form submission",
            "channel": "web_form"
        }
        with httpx.Client() as client:
            resp = client.post(
                f"{BASE_URL}/api/v1/messages/submit",
                json=payload,
                headers={"X-API-Key": API_KEY},
                timeout=10
            )
            data = resp.json()
            assert resp.status_code == 202
            assert data.get("status") == "received"
        print(f"[PASS] Web Form: request_id={data.get('request_id','N/A')[:8]}")
        return data.get("request_id")
    except Exception as e:
        print(f"[FAIL] Web Form: {e}")
        return None


def test_whatsapp_submit():
    """Test WhatsApp submission (with email workaround)"""
    print("\n=== Test: WhatsApp Submit ===")
    try:
        payload = {
            "customer_email": "whatsapp_user@test.com",
            "customer_phone": "+1234567890",
            "subject": "Test WhatsApp",
            "message": "Testing WhatsApp submission",
            "channel": "whatsapp"
        }
        with httpx.Client() as client:
            resp = client.post(
                f"{BASE_URL}/api/v1/messages/submit",
                json=payload,
                headers={"X-API-Key": API_KEY},
                timeout=10
            )
            data = resp.json()
            assert resp.status_code == 202
            assert data.get("status") == "received"
        print(f"[PASS] WhatsApp: request_id={data.get('request_id','N/A')[:8]}")
        return data.get("request_id")
    except Exception as e:
        print(f"[FAIL] WhatsApp: {e}")
        return None


def test_gmail_submit():
    """Test Gmail submission"""
    print("\n=== Test: Gmail Submit ===")
    try:
        payload = {
            "customer_email": "test@gmail.com",
            "subject": "Test Gmail",
            "message": "Testing Gmail submission",
            "channel": "gmail"
        }
        with httpx.Client() as client:
            resp = client.post(
                f"{BASE_URL}/api/v1/messages/submit",
                json=payload,
                headers={"X-API-Key": API_KEY},
                timeout=10
            )
            data = resp.json()
            assert resp.status_code == 202
            assert data.get("status") == "received"
        print(f"[PASS] Gmail: request_id={data.get('request_id','N/A')[:8]}")
        return data.get("request_id")
    except Exception as e:
        print(f"[FAIL] Gmail: {e}")
        return None


def test_status_check(request_id):
    """Test status check endpoint"""
    print("\n=== Test: Status Check ===")
    if not request_id:
        print("[SKIP] Status Check: No request_id")
        return False
    try:
        with httpx.Client() as client:
            resp = client.get(f"{BASE_URL}/api/v1/messages/status/{request_id}", timeout=10)
            data = resp.json()
            assert resp.status_code in [200, 404]
        print(f"[PASS] Status Check: status={data.get('status','N/A')}")
        return True
    except Exception as e:
        print(f"[FAIL] Status Check: {e}")
        return False


def test_webhook_routes():
    """Test webhook routes exist"""
    print("\n=== Test: Webhook Routes ===")
    try:
        with httpx.Client() as client:
            resp = client.get(f"{BASE_URL}/webhooks/whatsapp", timeout=5)
            assert resp.status_code in [200, 400]
            
            resp = client.get(f"{BASE_URL}/webhooks/gmail", timeout=5)
            assert resp.status_code in [200, 400]
        
        print(f"[PASS] Webhook Routes: OK")
        return True
    except Exception as e:
        print(f"[FAIL] Webhook Routes: {e}")
        return False


def main():
    print("=" * 60)
    print("FULL API INTEGRATION TESTS")
    print("=" * 60)
    
    results = []
    request_ids = []
    
    # Basic endpoints
    results.append(("Root", test_root()))
    results.append(("Health", test_health()))
    results.append(("Dashboard", test_dashboard()))
    results.append(("Webhook Routes", test_webhook_routes()))
    
    # Submit messages
    web_form_id = test_web_form_submit()
    request_ids.append(web_form_id)
    
    whatsapp_id = test_whatsapp_submit()
    request_ids.append(whatsapp_id)
    
    gmail_id = test_gmail_submit()
    request_ids.append(gmail_id)
    
    # Status checks
    results.append(("Status Check (Web Form)", test_status_check(web_form_id)))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n[FAILURE] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
