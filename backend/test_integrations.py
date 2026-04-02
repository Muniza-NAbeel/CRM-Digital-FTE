#!/usr/bin/env python
"""
Integration Tests for WhatsApp & Gmail
Run: python test_integrations.py
"""

import sys

def test_whatsapp_handler():
    """Test WhatsApp handler"""
    print('\n=== Testing WhatsApp Handler ===')
    try:
        from src.channels.whatsapp_handler import WhatsAppHandler, WhatsAppWebhookHandler, WhatsAppResponseSender
        
        # Test initialization
        handler = WhatsAppHandler(twilio_auth_token='test_token')
        print(f'[PASS] WhatsAppHandler initialized: {handler.channel_type}')
        
        # Test phone cleaning
        clean = handler._clean_phone_number('whatsapp:+14155238886')
        assert clean == '+14155238886', f'Expected +14155238886, got {clean}'
        print(f'[PASS] Phone cleaning: {clean}')
        
        # Test message splitting
        chunks = handler.split_long_message('A' * 2000)
        assert len(chunks) > 1, f'Expected multiple chunks, got {len(chunks)}'
        print(f'[PASS] Message splitting: {len(chunks)} chunks')
        
        # Test webhook handler
        webhook = WhatsAppWebhookHandler(handler)
        print(f'[PASS] WhatsAppWebhookHandler initialized')
        
        print('[OK] WhatsApp Handler: ALL TESTS PASSED\n')
        return True
    except Exception as e:
        print(f'[FAIL] WhatsApp Handler: {e}\n')
        import traceback
        traceback.print_exc()
        return False


def test_gmail_handler():
    """Test Gmail handler"""
    print('=== Testing Gmail Handler ===')
    try:
        from src.channels.gmail_handler import GmailHandler, GmailWebhookHandler, GmailResponseSender
        
        # Test initialization
        handler = GmailHandler()
        print(f'[PASS] GmailHandler initialized: {handler.channel_type}')
        
        # Test header extraction
        test_payload = {
            'headers': [
                {'name': 'From', 'value': 'Test User <test@example.com>'},
                {'name': 'To', 'value': 'support@techcorp.com'},
                {'name': 'Subject', 'value': 'Test Subject'},
            ],
            'mimeType': 'text/plain',
            'body': {'data': ''}
        }
        headers = handler._extract_headers(test_payload)
        assert 'from' in headers, 'From header not found'
        print(f'[PASS] Header extraction: {list(headers.keys())}')
        
        # Test email extraction
        email = handler._extract_email('Test User <test@example.com>')
        assert email == 'test@example.com', f'Expected test@example.com, got {email}'
        print(f'[PASS] Email extraction: {email}')
        
        # Test name extraction
        name = handler._extract_name('Test User <test@example.com>')
        assert name == 'Test User', f'Expected Test User, got {name}'
        print(f'[PASS] Name extraction: {name}')
        
        # Test webhook handler
        webhook = GmailWebhookHandler(handler)
        print(f'[PASS] GmailWebhookHandler initialized')
        
        print('[OK] Gmail Handler: ALL TESTS PASSED\n')
        return True
    except Exception as e:
        print(f'[FAIL] Gmail Handler: {e}\n')
        import traceback
        traceback.print_exc()
        return False


def test_intake_service():
    """Test intake service"""
    print('=== Testing Intake Service ===')
    try:
        from src.channels.intake_service import ChannelIntakeService, CustomerIdentificationService, MultiChannelMessageRouter
        from src.channels.base import ChannelType
        
        # Test intake service
        intake = ChannelIntakeService(twilio_auth_token='test')
        print(f'[PASS] ChannelIntakeService initialized')
        
        # Test handlers dict
        assert ChannelType.WHATSAPP in intake.handlers
        assert ChannelType.GMAIL in intake.handlers
        assert ChannelType.WEB_FORM in intake.handlers
        print(f'[PASS] All channel handlers registered')
        
        # Test customer ID service
        customer_service = CustomerIdentificationService()
        result = customer_service.identify_customer(email='test@example.com')
        assert result['is_identified'] == True
        print(f'[PASS] CustomerIdentificationService: {result}')
        
        print('[OK] Intake Service: ALL TESTS PASSED\n')
        return True
    except Exception as e:
        print(f'[FAIL] Intake Service: {e}\n')
        import traceback
        traceback.print_exc()
        return False


def test_webhook_routes():
    """Test webhook routes import"""
    print('=== Testing Webhook Routes ===')
    try:
        from src.api.routes import webhooks
        print(f'[PASS] Webhooks router imported')
        
        # The webhooks module IS the router (FastAPI APIRouter)
        # Check it has the expected endpoints
        assert hasattr(webhooks, 'routes'), 'Webhook router should have routes'
        print(f'[PASS] Webhook router has {len(webhooks.routes)} routes')
        
        # Check route paths
        paths = [r.path for r in webhooks.routes]
        assert '/webhooks/whatsapp' in paths, 'WhatsApp webhook endpoint missing'
        print(f'[PASS] WhatsApp webhook endpoint: /webhooks/whatsapp')
        
        assert '/webhooks/gmail' in paths, 'Gmail webhook endpoint missing'
        print(f'[PASS] Gmail webhook endpoint: /webhooks/gmail')
        
        print('[OK] Webhook Routes: ALL TESTS PASSED\n')
        return True
    except Exception as e:
        print(f'[FAIL] Webhook Routes: {e}\n')
        import traceback
        traceback.print_exc()
        return False


def test_messages_api():
    """Test messages API routes"""
    print('=== Testing Messages API ===')
    try:
        from src.api.routes import messages
        print(f'[PASS] Messages router imported')
        
        print('[OK] Messages API: ALL TESTS PASSED\n')
        return True
    except Exception as e:
        print(f'[FAIL] Messages API: {e}\n')
        import traceback
        traceback.print_exc()
        return False


def test_metrics_dashboard():
    """Test metrics dashboard"""
    print('=== Testing Metrics Dashboard ===')
    try:
        from src.api.routes import metrics_dashboard
        print(f'[PASS] Metrics dashboard router imported')
        
        print('[OK] Metrics Dashboard: ALL TESTS PASSED\n')
        return True
    except Exception as e:
        print(f'[FAIL] Metrics Dashboard: {e}\n')
        import traceback
        traceback.print_exc()
        return False


def test_kafka_integration():
    """Test Kafka integration"""
    print('=== Testing Kafka Integration ===')
    try:
        from src.kafka.integration import publish_inbound_message
        print(f'[PASS] Kafka integration imported')
        
        # Test function signature with customer_phone
        import inspect
        sig = inspect.signature(publish_inbound_message)
        params = list(sig.parameters.keys())
        assert 'customer_phone' in params, 'customer_phone parameter missing'
        print(f'[PASS] publish_inbound_message has customer_phone parameter')
        
        print('[OK] Kafka Integration: ALL TESTS PASSED\n')
        return True
    except Exception as e:
        print(f'[FAIL] Kafka Integration: {e}\n')
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """Test config settings"""
    print('=== Testing Config ===')
    try:
        from src.config import settings
        
        # Check Twilio settings
        assert hasattr(settings, 'twilio_account_sid')
        assert hasattr(settings, 'twilio_auth_token')
        assert hasattr(settings, 'twilio_whatsapp_number')
        print(f'[PASS] Twilio settings available')
        
        # Check Gmail settings
        assert hasattr(settings, 'gmail_client_id')
        assert hasattr(settings, 'gmail_refresh_token')
        assert hasattr(settings, 'gmail_sender_email')
        print(f'[PASS] Gmail settings available')
        
        print('[OK] Config: ALL TESTS PASSED\n')
        return True
    except Exception as e:
        print(f'[FAIL] Config: {e}\n')
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print('=' * 60)
    print('WHATSAPP & GMAIL INTEGRATION TESTS')
    print('=' * 60)
    
    results = []
    
    results.append(('WhatsApp Handler', test_whatsapp_handler()))
    results.append(('Gmail Handler', test_gmail_handler()))
    results.append(('Intake Service', test_intake_service()))
    results.append(('Webhook Routes', test_webhook_routes()))
    results.append(('Messages API', test_messages_api()))
    results.append(('Metrics Dashboard', test_metrics_dashboard()))
    results.append(('Kafka Integration', test_kafka_integration()))
    results.append(('Config', test_config()))
    
    print('=' * 60)
    print('TEST SUMMARY')
    print('=' * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = 'PASS' if result else 'FAIL'
        print(f'  [{status}] {name}')
    
    print(f'\nTotal: {passed}/{total} tests passed')
    
    if passed == total:
        print('\n[SUCCESS] ALL TESTS PASSED!')
        return 0
    else:
        print(f'\n[FAILURE] {total - passed} test(s) failed')
        return 1


if __name__ == '__main__':
    sys.exit(main())
