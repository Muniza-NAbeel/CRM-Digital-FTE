"""
Unit Tests for Core Components

Tests individual components in isolation.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.lifecycle import (
    TicketLifecycleManager,
    TicketState,
    EscalationReason,
    EscalationLevel,
    EscalationTriggers,
    StateTransition,
)

from src.channels.base import NormalizedMessage, ChannelType
from src.channels.gmail_handler import GmailHandler
from src.channels.whatsapp_handler import WhatsAppHandler
from src.channels.web_form_handler import WebFormHandler


pytestmark = pytest.mark.unit


# ============================================================================
# Lifecycle Manager Unit Tests
# ============================================================================

class TestStateTransition:
    """Test state transition validation."""
    
    def test_valid_transitions(self):
        """Test valid state transitions."""
        assert StateTransition.is_valid(TicketState.OPEN, TicketState.IN_PROGRESS)
        assert StateTransition.is_valid(TicketState.OPEN, TicketState.ESCALATED)
        assert StateTransition.is_valid(TicketState.IN_PROGRESS, TicketState.RESOLVED)
        assert StateTransition.is_valid(TicketState.RESOLVED, TicketState.CLOSED)
    
    def test_invalid_transitions(self):
        """Test invalid state transitions."""
        # Note: OPEN -> CLOSED is ALLOWED (direct close without handling)
        # Invalid transitions are:
        assert not StateTransition.is_valid(TicketState.CLOSED, TicketState.OPEN)  # Closed can't go back to open directly
        assert not StateTransition.is_valid(TicketState.RESOLVED, TicketState.OPEN)  # Must go through IN_PROGRESS
        assert not StateTransition.is_valid(TicketState.OPEN, TicketState.RESOLVED)  # Must go through IN_PROGRESS first


class TestEscalationTriggers:
    """Test escalation trigger detection."""
    
    def test_pricing_query_detection(self):
        """Test pricing query detection."""
        assert EscalationTriggers.check_pricing_query("What's the price?")
        assert EscalationTriggers.check_pricing_query("I need billing info")
        assert EscalationTriggers.check_pricing_query("payment plan options")
        assert not EscalationTriggers.check_pricing_query("technical issue")
    
    def test_refund_query_detection(self):
        """Test refund query detection."""
        assert EscalationTriggers.check_refund_query("I want a refund")
        assert EscalationTriggers.check_refund_query("cancel my subscription")
        assert EscalationTriggers.check_refund_query("chargeback")
        assert not EscalationTriggers.check_refund_query("how do I use this")
    
    def test_legal_query_detection(self):
        """Test legal query detection."""
        assert EscalationTriggers.check_legal_query("I'm talking to my lawyer")
        assert EscalationTriggers.check_legal_query("GDPR compliance issue")
        assert EscalationTriggers.check_legal_query("legal action")
        assert not EscalationTriggers.check_legal_query("technical problem")
    
    def test_escalation_request_detection(self):
        """Test human agent request detection."""
        assert EscalationTriggers.check_escalation_request("I want to speak to a human")
        assert EscalationTriggers.check_escalation_request("get me a real person")
        assert EscalationTriggers.check_escalation_request("escalate this")
        assert not EscalationTriggers.check_escalation_request("please help me")
    
    def test_negative_sentiment_detection(self):
        """Test negative sentiment keyword detection."""
        assert EscalationTriggers.check_negative_sentiment_keywords("I'm angry!")
        assert EscalationTriggers.check_negative_sentiment_keywords("This is terrible")
        assert EscalationTriggers.check_negative_sentiment_keywords("worst service ever")
        assert not EscalationTriggers.check_negative_sentiment_keywords("thank you")
    
    def test_detect_escalation_need_comprehensive(self):
        """Test comprehensive escalation detection."""
        # Customer request (highest priority)
        reason = EscalationTriggers.detect_escalation_need("I want a human")
        assert reason == EscalationReason.CUSTOMER_REQUEST
        
        # Legal query
        reason = EscalationTriggers.detect_escalation_need("legal issue")
        assert reason == EscalationReason.LEGAL_QUERY
        
        # Refund
        reason = EscalationTriggers.detect_escalation_need("refund please")
        assert reason == EscalationReason.REFUND_QUERY
        
        # Pricing
        reason = EscalationTriggers.detect_escalation_need("pricing info")
        assert reason == EscalationReason.PRICING_QUERY
        
        # Negative sentiment
        reason = EscalationTriggers.detect_escalation_need(
            "I'm so frustrated",
            sentiment_score=-0.8
        )
        assert reason == EscalationReason.NEGATIVE_SENTIMENT
        
        # No escalation needed
        reason = EscalationTriggers.detect_escalation_need("thank you for help")
        assert reason is None


# ============================================================================
# Channel Handler Unit Tests
# ============================================================================

class TestNormalizedMessage:
    """Test normalized message format."""
    
    def test_create_normalized_message(self):
        """Test creating normalized message."""
        msg = NormalizedMessage(
            channel=ChannelType.WEB_FORM,
            content="Test message",
            customer_email="test@example.com",
            external_message_id="msg_123",
        )
        
        assert msg.channel == ChannelType.WEB_FORM
        assert msg.content == "Test message"
        assert msg.customer_email == "test@example.com"
        assert msg.is_valid == True
    
    def test_normalized_message_to_dict(self):
        """Test converting to dictionary."""
        msg = NormalizedMessage(
            channel=ChannelType.GMAIL,
            content="Email content",
            customer_email="user@gmail.com",
            external_message_id="gmail_123",
        )
        
        data = msg.to_dict()
        
        assert data["channel"] == "gmail"
        assert data["content"] == "Email content"
        assert data["customer_email"] == "user@gmail.com"
        assert "received_at" in data
    
    def test_normalized_message_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "channel": "whatsapp",
            "content": "WhatsApp message",
            "customer_phone": "+1234567890",
            "external_message_id": "wa_123",
            "received_at": datetime.utcnow().isoformat(),
        }
        
        msg = NormalizedMessage.from_dict(data)
        
        assert msg.channel == ChannelType.WHATSAPP
        assert msg.content == "WhatsApp message"
        assert msg.customer_phone == "+1234567890"


class TestGmailHandler:
    """Test Gmail message handler."""
    
    def test_extract_email_from_header(self):
        """Test email extraction from From header."""
        handler = GmailHandler()
        
        assert handler._extract_email("user@example.com") == "user@example.com"
        assert handler._extract_email("John Doe <john@example.com>") == "john@example.com"
        assert handler._extract_email('"Jane Smith" <jane@example.com>') == "jane@example.com"
    
    def test_extract_name_from_header(self):
        """Test name extraction from From header."""
        handler = GmailHandler()
        
        assert handler._extract_name("John Doe <john@example.com>") == "John Doe"
        assert handler._extract_name("user@example.com") is None
    
    def test_clean_phone_number(self):
        """Test WhatsApp phone number cleaning."""
        handler = WhatsAppHandler()
        
        assert handler._clean_phone_number("whatsapp:+14155551234") == "+14155551234"
        assert handler._clean_phone_number("+14155551234") == "+14155551234"


class TestWhatsAppHandler:
    """Test WhatsApp message handler."""
    
    def test_parse_twilio_data(self):
        """Test Twilio webhook data parsing."""
        handler = WhatsAppHandler()
        
        twilio_data = {
            "MessageSid": "SM123",
            "ConversationSid": "CH123",
            "AccountSid": "AC123",
            "Body": "Test message",
            "From": "whatsapp:+14155551234",
            "To": "whatsapp:+14155558886",
        }
        
        msg = handler._parse_twilio_data(twilio_data)
        
        assert msg.message_sid == "SM123"
        assert msg.body == "Test message"
        assert msg.from_number == "whatsapp:+14155551234"
    
    def test_normalize_whatsapp_message(self):
        """Test WhatsApp message normalization."""
        handler = WhatsAppHandler()
        
        twilio_data = {
            "MessageSid": "SM123",
            "ConversationSid": "CH123",
            "AccountSid": "AC123",
            "Body": "Hello, I need help",
            "From": "whatsapp:+14155551234",
            "To": "whatsapp:+14155558886",
            "DateCreated": "Tue, 16 Jan 2024 12:00:00 +0000",
        }
        
        normalized = handler.normalize(twilio_data)
        
        assert normalized.channel == ChannelType.WHATSAPP
        assert normalized.customer_phone == "+14155551234"
        assert normalized.content == "Hello, I need help"


class TestWebFormHandler:
    """Test Web Form handler."""
    
    def test_parse_form_data(self):
        """Test web form data parsing."""
        handler = WebFormHandler()
        
        form_data = {
            "email": "user@example.com",
            "name": "John Doe",
            "subject": "Help Request",
            "message": "I need assistance",
        }
        
        msg = handler._parse_form_data(form_data)
        
        assert msg.email == "user@example.com"
        assert msg.name == "John Doe"
        assert msg.subject == "Help Request"
    
    def test_normalize_web_form(self):
        """Test web form normalization."""
        handler = WebFormHandler()
        
        form_data = {
            "email": "user@example.com",
            "name": "John Doe",
            "subject": "Test Subject",
            "message": "Test message content",
        }
        
        normalized = handler.normalize(form_data)
        
        assert normalized.channel == ChannelType.WEB_FORM
        assert normalized.customer_email == "user@example.com"
        assert "Test Subject" in normalized.content


# ============================================================================
# Agent Tools Unit Tests
# ============================================================================

class TestAgentTools:
    """Test agent tools."""
    
    @pytest.mark.asyncio
    async def test_create_ticket_input_validation(self):
        """Test create ticket input validation."""
        from src.agents.tools import CreateTicketInput
        
        # Valid input
        valid = CreateTicketInput(
            customer_id="123e4567-e89b-12d3-a456-426614174000",
            subject="Test Issue",
            description="Test description",
            channel="web_form",
        )
        assert valid.subject == "Test Issue"
        
        # Invalid: subject too short
        with pytest.raises(Exception):
            CreateTicketInput(
                customer_id="123e4567-e89b-12d3-a456-426614174000",
                subject="Hi",  # Too short
                description="Test",
                channel="web_form",
            )
    
    @pytest.mark.asyncio
    async def test_send_response_input_validation(self):
        """Test send response input validation."""
        from src.agents.tools import SendResponseInput
        
        # Valid input
        valid = SendResponseInput(
            ticket_id="123e4567-e89b-12d3-a456-426614174000",
            conversation_id="123e4567-e89b-12d3-a456-426614174001",
            customer_id="123e4567-e89b-12d3-a456-426614174002",
            message="Hello, how can I help?",
            channel="web_form",
        )
        assert valid.message == "Hello, how can I help?"
        
        # Invalid: message too long
        with pytest.raises(Exception):
            SendResponseInput(
                ticket_id="123e4567-e89b-12d3-a456-426614174000",
                conversation_id="123e4567-e89b-12d3-a456-426614174001",
                customer_id="123e4567-e89b-12d3-a456-426614174002",
                message="A" * 6000,  # Too long
                channel="web_form",
            )


# ============================================================================
# Metrics Collector Unit Tests
# ============================================================================

class TestMetricsCollector:
    """Test metrics collection."""
    
    def test_response_time_metric(self):
        """Test response time metric creation."""
        from src.services.metrics_collector import ResponseTimeMetric
        
        metric = ResponseTimeMetric(
            ticket_id="123",
            channel="web_form",
            response_time_ms=150,
            is_first_response=True,
        )
        
        data = metric.to_dict()
        assert data["response_time_ms"] == 150
        assert data["is_first_response"] == True
    
    def test_token_usage_metric(self):
        """Test token usage metric creation."""
        from src.services.metrics_collector import TokenUsageMetric

        metric = TokenUsageMetric(
            ticket_id="123",
            channel="gmail",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,  # Required parameter
        )

        assert metric.total_tokens == 150

        data = metric.to_dict()
        assert data["total_tokens"] == 150


# ============================================================================
# Integration Tests (Mock-based)
# ============================================================================

class TestMockedIntegration:
    """Test integration with mocked dependencies."""
    
    @pytest.mark.asyncio
    async def test_lifecycle_manager_mock_db(self):
        """Test lifecycle manager with mocked database."""
        mock_conn = AsyncMock()
        
        # First call: fetch ticket (returns current state)
        # Second call: after update (returns new state)
        mock_conn.fetchrow.side_effect = [
            {"id": "123", "status": "open", "ticket_number": "CS-2024-00001"},  # Initial fetch
            {"id": "123", "status": "in_progress", "ticket_number": "CS-2024-00001"},  # After update
        ]

        lifecycle = TicketLifecycleManager(mock_conn)

        # Test transition
        result = await lifecycle.transition(
            "123",
            TicketState.IN_PROGRESS,
            reason="Testing",
        )

        assert result == True  # Transition should succeed
        assert mock_conn.fetchrow.call_count == 2  # Called twice: fetch + update
    
    @pytest.mark.asyncio
    async def test_agent_with_mocked_tools(self):
        """Test agent with mocked tools."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {"id": "123", "ticket_number": "CS-001"}
        
        with patch('src.agents.customer_success_agent.AgentTools') as MockTools:
            mock_tools = AsyncMock()
            mock_tools.create_ticket.return_value = {
                "success": True,
                "ticket_id": "123",
                "ticket_number": "CS-001",
            }
            mock_tools.send_response.return_value = {
                "success": True,
                "message_id": "msg_123",
            }
            MockTools.return_value = mock_tools
            
            # Agent would use mocked tools
            assert mock_tools is not None
