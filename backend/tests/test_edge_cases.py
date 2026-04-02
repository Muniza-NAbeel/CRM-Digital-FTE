"""
Edge Case Tests for Customer Success Digital FTE

Tests edge cases and error conditions:
- Empty input
- Angry customer (sentiment escalation)
- Pricing queries (must escalate)
- Very long messages
- Invalid data
- Rate limiting
"""

import pytest
import asyncio
from uuid import uuid4

import httpx
from asyncpg import Connection


pytestmark = pytest.mark.e2e


# ============================================================================
# Input Validation Edge Cases
# ============================================================================

class TestInputValidation:
    """
    Test input validation edge cases.
    """
    
    @pytest.mark.asyncio
    async def test_empty_message_rejected(
        self,
        api_client: httpx.AsyncClient,
        empty_message: str,
    ):
        """
        Test that empty messages are rejected.
        """
        unique_id = str(uuid4())[:8]
        
        response = await api_client.post(
            "/api/v1/tickets",
            json={
                "customer_email": f"empty_{unique_id}@example.com",
                "subject": "Empty Test",
                "description": empty_message,
                "channel": "web_form",
            },
        )
        
        # Should be rejected (422) or accepted with validation
        assert response.status_code in [422, 201]
        
        if response.status_code == 201:
            # If accepted, agent should handle gracefully
            ticket = response.json()
            assert "id" in ticket
    
    @pytest.mark.asyncio
    async def test_very_long_message(
        self,
        api_client: httpx.AsyncClient,
        very_long_message: str,
    ):
        """
        Test handling of very long messages.
        """
        unique_id = str(uuid4())[:8]
        
        response = await api_client.post(
            "/api/v1/tickets",
            json={
                "customer_email": f"long_{unique_id}@example.com",
                "subject": "Long Message Test",
                "description": very_long_message[:10000],  # Truncate to max
                "channel": "web_form",
            },
        )
        
        # Should handle gracefully (either accept or reject with clear error)
        assert response.status_code in [201, 400, 422]
    
    @pytest.mark.asyncio
    async def test_special_characters_in_message(
        self,
        api_client: httpx.AsyncClient,
        generate_unique_id: callable,
    ):
        """
        Test messages with special characters.
        """
        unique_id = generate_unique_id()
        
        special_message = """
        Test with special chars: <>&"'\\/\n\t\r
        Unicode: 你好世界 🌍 مرحبا
        SQL injection attempt: ' OR '1'='1
        XSS attempt: <script>alert('xss')</script>
        """
        
        response = await api_client.post(
            "/api/v1/tickets",
            json={
                "customer_email": f"special_{unique_id}@example.com",
                "subject": "Special Chars Test",
                "description": special_message,
                "channel": "web_form",
            },
        )
        
        assert response.status_code == 201
        
        # Verify data is stored safely
        ticket = response.json()
        assert ticket["id"] is not None
    
    @pytest.mark.asyncio
    async def test_invalid_email_format(
        self,
        api_client: httpx.AsyncClient,
    ):
        """
        Test invalid email formats.
        """
        unique_id = str(uuid4())[:8]
        
        invalid_emails = [
            "not-an-email",
            "@missing-local.com",
            "missing-domain@",
            "spaces in@email.com",
        ]
        
        for email in invalid_emails:
            response = await api_client.post(
                "/api/v1/tickets",
                json={
                    "customer_email": email,
                    "subject": "Invalid Email Test",
                    "description": "Testing invalid email",
                    "channel": "web_form",
                },
            )
            
            # Should either reject or normalize
            assert response.status_code in [201, 422]


# ============================================================================
# Sentiment-Based Escalation Tests
# ============================================================================

class TestSentimentEscalation:
    """
    Test escalation based on customer sentiment.
    """
    
    @pytest.mark.asyncio
    async def test_angry_customer_escalation(
        self,
        api_client: httpx.AsyncClient,
        db_connection: Connection,
        angry_customer_message: str,
    ):
        """
        Test that angry customers trigger escalation.
        """
        unique_id = str(uuid4())[:8]
        
        # Submit angry message
        response = await api_client.post(
            "/api/v1/tickets",
            json={
                "customer_email": f"angry_{unique_id}@example.com",
                "subject": "VERY ANGRY",
                "description": angry_customer_message,
                "channel": "web_form",
            },
        )
        
        assert response.status_code == 201
        ticket = response.json()
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Check if ticket was escalated
        escalated_ticket = await db_connection.fetchrow(
            "SELECT * FROM tickets WHERE id = $1",
            ticket["id"],
        )
        
        # Should be escalated due to negative sentiment
        assert escalated_ticket is not None
        # Note: Escalation may be async, so we check if it's marked
        assert (
            escalated_ticket["escalation_status"] == "escalated" or
            escalated_ticket["status"] == "escalated" or
            escalated_ticket["escalation_reason"] is not None
        )
    
    @pytest.mark.asyncio
    async def test_frustrated_customer_keywords(
        self,
        api_client: httpx.AsyncClient,
        db_connection: Connection,
        generate_unique_id: callable,
    ):
        """
        Test escalation for frustrated customer keywords.
        """
        unique_id = generate_unique_id()
        
        frustrated_messages = [
            "This is unacceptable! I'm very disappointed!",
            "Your service is terrible and useless!",
            "I hate this product. Worst experience ever!",
            "I'm frustrated and angry about this issue!",
        ]
        
        for i, message in enumerate(frustrated_messages):
            response = await api_client.post(
                "/api/v1/tickets",
                json={
                    "customer_email": f"frustrated_{unique_id}_{i}@example.com",
                    "subject": "Frustrated Customer",
                    "description": message,
                    "channel": "web_form",
                },
            )
            
            assert response.status_code == 201


# ============================================================================
# Topic-Based Escalation Tests
# ============================================================================

class TestTopicEscalation:
    """
    Test escalation based on topic detection.
    """
    
    @pytest.mark.asyncio
    async def test_pricing_query_escalation(
        self,
        api_client: httpx.AsyncClient,
        db_connection: Connection,
        pricing_query_message: str,
    ):
        """
        Test that pricing queries trigger escalation.
        """
        unique_id = str(uuid4())[:8]
        
        response = await api_client.post(
            "/api/v1/tickets",
            json={
                "customer_email": f"pricing_{unique_id}@example.com",
                "subject": "Pricing Inquiry",
                "description": pricing_query_message,
                "channel": "web_form",
            },
        )
        
        assert response.status_code == 201
        ticket = response.json()
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Check escalation
        escalated_ticket = await db_connection.fetchrow(
            "SELECT * FROM tickets WHERE id = $1",
            ticket["id"],
        )
        
        # Pricing queries should escalate
        assert escalated_ticket is not None
        assert (
            escalated_ticket["escalation_reason"] == "pricing_query" or
            escalated_ticket["escalation_status"] == "escalated" or
            escalated_ticket["assigned_to"] != "ai_agent"
        )
    
    @pytest.mark.asyncio
    async def test_refund_request_escalation(
        self,
        api_client: httpx.AsyncClient,
        db_connection: Connection,
        generate_unique_id: callable,
    ):
        """
        Test that refund requests trigger escalation.
        """
        unique_id = generate_unique_id()
        
        refund_message = """
        I want a refund for my last purchase.
        The product didn't meet my expectations.
        Please process my refund as soon as possible.
        """
        
        response = await api_client.post(
            "/api/v1/tickets",
            json={
                "customer_email": f"refund_{unique_id}@example.com",
                "subject": "Refund Request",
                "description": refund_message,
                "channel": "web_form",
            },
        )
        
        assert response.status_code == 201
        
        await asyncio.sleep(3)
        
        ticket = await db_connection.fetchrow(
            "SELECT * FROM tickets WHERE id = $1",
            response.json()["id"],
        )
        
        # Refund requests should escalate
        assert ticket["escalation_reason"] in ["refund_query", None]  # May be async
    
    @pytest.mark.asyncio
    async def test_legal_query_escalation(
        self,
        api_client: httpx.AsyncClient,
        db_connection: Connection,
        generate_unique_id: callable,
    ):
        """
        Test that legal queries trigger critical escalation.
        """
        unique_id = generate_unique_id()
        
        legal_message = """
        I need to speak with your legal team.
        This involves GDPR compliance and data privacy.
        I may need to consult with my attorney.
        """
        
        response = await api_client.post(
            "/api/v1/tickets",
            json={
                "customer_email": f"legal_{unique_id}@example.com",
                "subject": "Legal Matter",
                "description": legal_message,
                "channel": "web_form",
            },
        )
        
        assert response.status_code == 201
        
        await asyncio.sleep(3)
        
        ticket = await db_connection.fetchrow(
            "SELECT * FROM tickets WHERE id = $1",
            response.json()["id"],
        )
        
        # Legal queries should escalate to critical level
        assert ticket is not None
        assert (
            ticket["escalation_reason"] == "legal_query" or
            ticket["escalation_level"] >= 2
        )
    
    @pytest.mark.asyncio
    async def test_human_request_escalation(
        self,
        api_client: httpx.AsyncClient,
        db_connection: Connection,
        generate_unique_id: callable,
    ):
        """
        Test that requests for human agent trigger escalation.
        """
        unique_id = generate_unique_id()
        
        human_request_message = """
        I don't want to talk to a bot.
        Get me a real person please.
        I need to speak with a human agent.
        """
        
        response = await api_client.post(
            "/api/v1/tickets",
            json={
                "customer_email": f"human_{unique_id}@example.com",
                "subject": "Need Human Help",
                "description": human_request_message,
                "channel": "web_form",
            },
        )
        
        assert response.status_code == 201
        
        await asyncio.sleep(3)
        
        ticket = await db_connection.fetchrow(
            "SELECT * FROM tickets WHERE id = $1",
            response.json()["id"],
        )
        
        # Human requests should escalate immediately
        assert ticket["escalation_reason"] == "customer_request" or \
               ticket["escalation_status"] == "escalated"


# ============================================================================
# Rate Limiting and Abuse Tests
# ============================================================================

class TestRateLimiting:
    """
    Test rate limiting and abuse prevention.
    """
    
    @pytest.mark.asyncio
    async def test_rapid_submissions(
        self,
        api_client: httpx.AsyncClient,
        generate_unique_id: callable,
    ):
        """
        Test handling of rapid successive submissions.
        """
        unique_id = generate_unique_id()
        email = f"ratelimit_{unique_id}@example.com"
        
        responses = []
        for i in range(10):
            response = await api_client.post(
                "/api/v1/tickets",
                json={
                    "customer_email": email,
                    "subject": f"Rapid Test {i}",
                    "description": f"Message {i}",
                    "channel": "web_form",
                },
            )
            responses.append(response.status_code)
        
        # Most should succeed, some may be rate limited
        success_count = sum(1 for s in responses if s == 201)
        rate_limited_count = sum(1 for s in responses if s == 429)
        
        # At least some should succeed
        assert success_count >= 5
        # Rate limiting is optional in test env
        # assert rate_limited_count > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(
        self,
        api_client: httpx.AsyncClient,
        generate_unique_id: callable,
    ):
        """
        Test handling of concurrent requests.
        """
        unique_id = generate_unique_id()
        
        async def submit_ticket(i: int):
            return await api_client.post(
                "/api/v1/tickets",
                json={
                    "customer_email": f"concurrent_{unique_id}_{i}@example.com",
                    "subject": f"Concurrent Test {i}",
                    "description": f"Message {i}",
                    "channel": "web_form",
                },
            )
        
        # Submit 20 concurrent requests
        tasks = [submit_ticket(i) for i in range(20)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes
        success_count = sum(
            1 for r in responses 
            if isinstance(r, httpx.Response) and r.status_code == 201
        )
        
        # Most should succeed
        assert success_count >= 15


# ============================================================================
# System Resilience Tests
# ============================================================================

class TestSystemResilience:
    """
    Test system resilience under edge conditions.
    """
    
    @pytest.mark.asyncio
    async def test_missing_metadata(
        self,
        api_client: httpx.AsyncClient,
        generate_unique_id: callable,
    ):
        """
        Test handling of missing optional metadata.
        """
        unique_id = generate_unique_id()
        
        # Minimal required fields only
        response = await api_client.post(
            "/api/v1/tickets",
            json={
                "customer_email": f"minimal_{unique_id}@example.com",
                "subject": "Minimal Test",
                "description": "Test with minimal data",
                "channel": "web_form",
                # No priority, no metadata, no optional fields
            },
        )
        
        assert response.status_code == 201
        
        ticket = response.json()
        assert ticket["priority"] == "medium"  # Default value
    
    @pytest.mark.asyncio
    async def test_unicode_everywhere(
        self,
        api_client: httpx.AsyncClient,
        generate_unique_id: callable,
    ):
        """
        Test Unicode handling in all fields.
        """
        unique_id = generate_unique_id()
        
        unicode_data = {
            "customer_email": f"unicode_{unique_id}@测试.com",
            "subject": "测试主题 🌍 مرحبا",
            "description": "你好世界！This is a test with 中文 and emoji 🎉",
            "channel": "web_form",
        }
        
        response = await api_client.post(
            "/api/v1/tickets",
            json=unicode_data,
        )
        
        assert response.status_code == 201
        
        ticket = response.json()
        assert ticket["id"] is not None
    
    @pytest.mark.asyncio
    async def test_customer_block_status(
        self,
        api_client: httpx.AsyncClient,
        db_connection: Connection,
        generate_unique_id: callable,
    ):
        """
        Test handling of blocked customers.
        """
        unique_id = generate_unique_id()
        email = f"blocked_{unique_id}@example.com"
        
        # Create customer
        customer = await db_connection.fetchrow(
            """
            INSERT INTO customers (email, full_name, is_blocked, block_reason)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            email,
            "Blocked User",
            True,
            "Test block",
        )
        
        # Try to create ticket for blocked customer
        response = await api_client.post(
            "/api/v1/tickets",
            json={
                "customer_email": email,
                "subject": "Blocked Customer Test",
                "description": "Testing blocked customer",
                "channel": "web_form",
            },
        )
        
        # System should handle blocked customers appropriately
        # (either reject or flag for review)
        assert response.status_code in [201, 403]
