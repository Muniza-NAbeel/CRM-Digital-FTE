"""
Test Configuration and Fixtures

Provides shared fixtures for all tests.
"""

import os
import pytest
import httpx
import asyncio
from uuid import uuid4

# ============================================================================
# Configuration
# ============================================================================

TEST_API_URL = os.getenv("TEST_API_URL", "http://localhost:8000")
API_KEY = "dev-api-key-12345"


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest.fixture
async def api_client():
    """
    Create an async HTTP client for API testing.
    """
    async with httpx.AsyncClient(
        base_url=TEST_API_URL,
        timeout=30.0,
        headers={"X-API-Key": API_KEY}
    ) as client:
        yield client


@pytest.fixture
async def api_client_sync():
    """
    Create a sync HTTP client for API testing.
    """
    with httpx.Client(
        base_url=TEST_API_URL,
        timeout=30.0,
        headers={"X-API-Key": API_KEY}
    ) as client:
        yield client


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def test_customer_data():
    """Generate test customer data."""
    unique_id = str(uuid4())[:8]
    return {
        "email": f"test_{unique_id}@example.com",
        "phone": f"+1555{unique_id}",
        "full_name": f"Test User {unique_id}",
        "company_name": "Test Company",
        "customer_tier": "standard",
    }


@pytest.fixture
def test_ticket_data():
    """Generate test ticket data."""
    unique_id = str(uuid4())[:8]
    return {
        "subject": f"Test Issue {unique_id}",
        "description": f"This is a test support request. {unique_id}",
        "channel": "web_form",
        "priority": "medium",
    }


@pytest.fixture
def generate_unique_id():
    """Returns a function to generate unique IDs."""
    def _generate(prefix: str = "") -> str:
        return f"{prefix}{str(uuid4())[:8]}" if prefix else str(uuid4())[:8]
    return _generate


@pytest.fixture
def empty_message():
    """Empty message for testing."""
    return ""


@pytest.fixture
def very_long_message():
    """Very long message for testing."""
    return "Help " * 10000  # 50,000 characters


@pytest.fixture
def angry_customer_message():
    """Angry customer message for testing."""
    return "This is RIDICULOUS! Your product is BROKEN! I want a REFUND NOW! This is the WORST service ever!"


@pytest.fixture
def pricing_query_message():
    """Pricing-related query that should trigger escalation."""
    return "How much does the enterprise plan cost? What are your pricing options?"


@pytest.fixture
def legal_query_message():
    """Legal-related query that should trigger escalation."""
    return "I'm going to sue you! Where is your legal department? I want to speak to your attorney!"


@pytest.fixture
def refund_request_message():
    """Refund request that should trigger escalation."""
    return "I want a full refund! This product doesn't work and I want my money back!"


@pytest.fixture
def human_request_message():
    """Request for human agent that should trigger escalation."""
    return "I want to speak to a human agent! Get me a real person!"


@pytest.fixture
def special_characters_message():
    """Message with special characters."""
    return "Help! @#$%^&*()_+{}|:<>?~`-=[]\\;',./ 你好 🎉"


@pytest.fixture
def unicode_message():
    """Message with unicode characters."""
    return "Hello 世界 🌍 مرحبا שלום"
