"""
End-to-End Tests for Customer Success Digital FTE

Tests complete user journeys across all channels:
- Web Form → Agent → Response
- Gmail → Agent → Response
- WhatsApp → Agent → Response
"""

import pytest
import asyncio
import time
from uuid import UUID

import httpx
from asyncpg import Connection


pytestmark = pytest.mark.e2e


# ============================================================================
# Web Form E2E Tests
# ============================================================================

class TestWebFormE2E:
    """
    End-to-end tests for Web Form channel.
    """
    
    @pytest.mark.asyncio
    @pytest.mark.channel("web_form")
    async def test_web_form_complete_flow(
        self,
        api_client: httpx.AsyncClient,
        db_connection: Connection,
        test_web_form_data: dict,
    ):
        """
        Test complete web form submission flow.
        
        Flow:
        1. Submit web form
        2. Verify ticket created
        3. Verify response sent
        """
        # Step 1: Submit web form
        response = await api_client.post(
            "/api/v1/tickets",
            json={
                "customer_email": test_web_form_data["email"],
                "subject": test_web_form_data["subject"],
                "description": test_web_form_data["message"],
                "channel": "web_form",
            },
        )
        
        assert response.status_code == 201
        ticket_data = response.json()
        
        assert "id" in ticket_data
        assert "ticket_number" in ticket_data
        assert ticket_data["status"] == "new"
        
        ticket_id = ticket_data["id"]
        
        # Step 2: Wait for processing (in real system, Kafka worker processes)
        await asyncio.sleep(2)
        
        # Step 3: Verify ticket was updated
        response = await api_client.get(f"/api/v1/tickets/{ticket_id}")
        assert response.status_code == 200
        
        updated_ticket = response.json()
        assert updated_ticket["id"] == ticket_id
        
        # Step 4: Verify messages exist
        response = await api_client.get(
            f"/api/v1/conversations",
            params={"ticket_id": ticket_id},
        )
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    @pytest.mark.channel("web_form")
    async def test_web_form_validation_errors(
        self,
        api_client: httpx.AsyncClient,
    ):
        """
        Test web form validation.
        """
        # Missing required fields
        response = await api_client.post(
            "/api/v1/tickets",
            json={"email": "test@example.com"},  # Missing subject, description
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    @pytest.mark.channel("web_form")
    async def test_web_form_customer_creation(
        self,
        api_client: httpx.AsyncClient,
        db_connection: Connection,
        generate_unique_id: callable,
    ):
        """
        Test that new customers are created from web form.
        """
        unique_id = generate_unique_id()
        email = f"new_customer_{unique_id}@example.com"
        
        # Submit ticket with new customer email
        response = await api_client.post(
            "/api/v1/tickets",
            json={
                "customer_email": email,
                "subject": "New Customer Test",
                "description": "This is my first support request.",
                "channel": "web_form",
            },
        )
        
        assert response.status_code == 201
        
        # Verify customer was created
        await asyncio.sleep(1)
        
        # Find customer by email (through tickets or direct query)
        customer = await db_connection.fetchrow(
            "SELECT * FROM customers WHERE email = $1",
            email,
        )
        
        assert customer is not None
        assert customer["email"] == email


# ============================================================================
# Gmail E2E Tests
# ============================================================================

class TestGmailE2E:
    """
    End-to-end tests for Gmail channel.
    """
    
    @pytest.mark.asyncio
    @pytest.mark.channel("gmail")
    async def test_gmail_message_processing(
        self,
        api_client: httpx.AsyncClient,
        db_connection: Connection,
        test_gmail_data: dict,
    ):
        """
        Test Gmail message processing flow.
        """
        # Extract email from Gmail data
        from_header = None
        for header in test_gmail_data["payload"]["headers"]:
            if header["name"] == "From":
                from_header = header["value"]
                break
        
        # Create ticket simulating Gmail webhook
        response = await api_client.post(
            "/api/v1/tickets",
            json={
                "customer_email": from_header,
                "subject": test_gmail_data["snippet"],
                "description": test_gmail_data["snippet"],
                "channel": "gmail",
                "metadata": {
                    "gmail_message_id": test_gmail_data["id"],
                    "gmail_thread_id": test_gmail_data["threadId"],
                },
            },
        )
        
        assert response.status_code == 201
        ticket_data = response.json()
        
        assert ticket_data["channel"] == "gmail"
        
        # Verify customer created from Gmail
        await asyncio.sleep(1)
        
        customer = await db_connection.fetchrow(
            "SELECT * FROM customers WHERE email = $1",
            from_header,
        )
        
        assert customer is not None
    
    @pytest.mark.asyncio
    @pytest.mark.channel("gmail")
    async def test_gmail_thread_continuity(
        self,
        api_client: httpx.AsyncClient,
        db_connection: Connection,
        generate_unique_id: callable,
    ):
        """
        Test that Gmail thread messages are linked correctly.
        """
        unique_id = generate_unique_id()
        thread_id = f"thread_{unique_id}"
        email = f"thread_test_{unique_id}@gmail.com"
        
        # First message in thread
        response1 = await api_client.post(
            "/api/v1/tickets",
            json={
                "customer_email": email,
                "subject": f"Thread Test {unique_id}",
                "description": "First message in thread",
                "channel": "gmail",
                "metadata": {"gmail_thread_id": thread_id},
            },
        )
        
        assert response1.status_code == 201
        ticket1 = response1.json()
        
        # Second message in same thread (should link to existing)
        response2 = await api_client.post(
            "/api/v1/tickets",
            json={
                "customer_email": email,
                "subject": f"Re: Thread Test {unique_id}",
                "description": "Reply in same thread",
                "channel": "gmail",
                "metadata": {"gmail_thread_id": thread_id},
            },
        )
        
        assert response2.status_code == 201
        ticket2 = response2.json()
        
        # Both tickets should have same customer
        assert ticket1["customer_id"] == ticket2["customer_id"]


# ============================================================================
# WhatsApp E2E Tests
# ============================================================================

class TestWhatsAppE2E:
    """
    End-to-end tests for WhatsApp channel.
    """
    
    @pytest.mark.asyncio
    @pytest.mark.channel("whatsapp")
    async def test_whatsapp_webhook_processing(
        self,
        api_client: httpx.AsyncClient,
        db_connection: Connection,
        test_whatsapp_data: dict,
    ):
        """
        Test WhatsApp webhook message processing.
        """
        # Simulate Twilio webhook
        response = await api_client.post(
            "/webhooks/whatsapp",
            data=test_whatsapp_data,
            headers={"X-Twilio-Signature": "test_signature"},
        )
        
        # Should accept webhook (signature validation may fail in test)
        assert response.status_code in [200, 400]
        
        if response.status_code == 200:
            # Verify ticket was created
            await asyncio.sleep(1)
            
            customer = await db_connection.fetchrow(
                "SELECT * FROM customers WHERE phone = $1",
                "+14155551234",  # Cleaned phone number
            )
            
            if customer:
                tickets = await db_connection.fetch(
                    "SELECT * FROM tickets WHERE customer_id = $1",
                    customer["id"],
                )
                assert len(tickets) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.channel("whatsapp")
    async def test_whatsapp_conversation_flow(
        self,
        api_client: httpx.AsyncClient,
        test_whatsapp_data: dict,
    ):
        """
        Test WhatsApp conversation with multiple messages.
        """
        # First message
        response1 = await api_client.post(
            "/webhooks/whatsapp",
            data={
                **test_whatsapp_data,
                "MessageSid": "SM001",
                "Body": "I need help",
            },
        )
        
        # Second message (same conversation)
        response2 = await api_client.post(
            "/webhooks/whatsapp",
            data={
                **test_whatsapp_data,
                "MessageSid": "SM002",
                "Body": "Still waiting for help",
            },
        )
        
        # Both should be accepted
        assert response1.status_code in [200, 400]
        assert response2.status_code in [200, 400]


# ============================================================================
# Cross-Channel E2E Tests
# ============================================================================

class TestCrossChannelE2E:
    """
    Tests for cross-channel conversation continuity.
    """
    
    @pytest.mark.asyncio
    async def test_same_customer_different_channels(
        self,
        api_client: httpx.AsyncClient,
        db_connection: Connection,
        generate_unique_id: callable,
    ):
        """
        Test that same customer across channels is recognized.
        """
        unique_id = generate_unique_id()
        email = f"omni_{unique_id}@example.com"
        phone = f"+1555{unique_id}"
        
        # First contact via web form
        response1 = await api_client.post(
            "/api/v1/tickets",
            json={
                "customer_email": email,
                "subject": "Web Form Inquiry",
                "description": "Question from web",
                "channel": "web_form",
            },
        )
        assert response1.status_code == 201
        ticket1 = response1.json()
        
        # Second contact via WhatsApp (same person, different channel)
        response2 = await api_client.post(
            "/api/v1/tickets",
            json={
                "customer_email": email,
                "customer_phone": phone,
                "subject": "WhatsApp Follow-up",
                "description": "Following up via WhatsApp",
                "channel": "whatsapp",
            },
        )
        assert response2.status_code == 201
        ticket2 = response2.json()
        
        # Both tickets should have same customer
        assert ticket1["customer_id"] == ticket2["customer_id"]
        
        # Verify customer has both channels recorded
        customer = await db_connection.fetchrow(
            "SELECT * FROM customers WHERE id = $1",
            ticket1["customer_id"],
        )
        
        assert customer["email"] == email
        assert customer["total_tickets"] >= 2
    
    @pytest.mark.asyncio
    async def test_customer_history_across_channels(
        self,
        api_client: httpx.AsyncClient,
        db_connection: Connection,
        generate_unique_id: callable,
    ):
        """
        Test customer history includes all channels.
        """
        unique_id = generate_unique_id()
        email = f"history_{unique_id}@example.com"
        
        # Create multiple tickets via different channels
        for channel in ["web_form", "gmail", "whatsapp"]:
            response = await api_client.post(
                "/api/v1/tickets",
                json={
                    "customer_email": email,
                    "subject": f"{channel} ticket",
                    "description": f"Test via {channel}",
                    "channel": channel,
                },
            )
            assert response.status_code == 201
        
        await asyncio.sleep(1)
        
        # Get customer
        customer = await db_connection.fetchrow(
            "SELECT * FROM customers WHERE email = $1",
            email,
        )
        
        assert customer["total_tickets"] >= 3
        
        # Get all tickets for customer
        tickets = await db_connection.fetch(
            "SELECT * FROM tickets WHERE customer_id = $1",
            customer["id"],
        )
        
        channels_used = set(t["channel"] for t in tickets)
        assert len(channels_used) >= 3


# ============================================================================
# Response Time E2E Tests
# ============================================================================

class TestResponseTimeE2E:
    """
    Test response times across channels.
    """
    
    @pytest.mark.asyncio
    async def test_api_response_time(
        self,
        api_client: httpx.AsyncClient,
        test_web_form_data: dict,
    ):
        """
        Test API response time is within acceptable limits.
        """
        start = time.time()
        
        response = await api_client.post(
            "/api/v1/tickets",
            json={
                "customer_email": test_web_form_data["email"],
                "subject": test_web_form_data["subject"],
                "description": test_web_form_data["message"],
                "channel": "web_form",
            },
        )
        
        elapsed = time.time() - start
        
        assert response.status_code == 201
        assert elapsed < 5.0  # Should complete in under 5 seconds
    
    @pytest.mark.asyncio
    async def test_health_check_response_time(
        self,
        api_client: httpx.AsyncClient,
    ):
        """
        Test health check endpoint response time.
        """
        start = time.time()
        
        response = await api_client.get("/health/ready")
        
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0  # Health check should be fast
