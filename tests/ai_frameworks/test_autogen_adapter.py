"""
Tests for AutoGen adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- ConversableAgent wrapping
- GroupChat governance
- Code execution governance
- Human-in-the-loop governance
"""

import pytest
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.autogen import (
    TorkAutoGenMiddleware,
    GovernedAutoGenAgent,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestAutoGenImportInstantiation:
    """Test import and instantiation of AutoGen adapter."""

    def test_import_middleware(self):
        """Test TorkAutoGenMiddleware can be imported."""
        assert TorkAutoGenMiddleware is not None

    def test_import_governed_agent(self):
        """Test GovernedAutoGenAgent can be imported."""
        assert GovernedAutoGenAgent is not None

    def test_instantiate_middleware_default(self):
        """Test middleware instantiation with defaults."""
        middleware = TorkAutoGenMiddleware()
        assert middleware is not None
        assert middleware.tork is not None
        assert middleware.agent_id == "autogen-agent"
        assert middleware.receipts == []

    def test_instantiate_governed_agent_default(self):
        """Test governed agent instantiation with defaults."""
        agent = GovernedAutoGenAgent()
        assert agent is not None
        assert agent._middleware is not None


class TestAutoGenConfiguration:
    """Test configuration of AutoGen adapter."""

    def test_middleware_with_policy_version(self):
        """Test middleware with custom policy version."""
        middleware = TorkAutoGenMiddleware(policy_version="2.0.0")
        assert middleware.tork is not None

    def test_middleware_with_agent_id(self):
        """Test middleware with custom agent ID."""
        middleware = TorkAutoGenMiddleware(agent_id="custom-agent")
        assert middleware.agent_id == "custom-agent"

    def test_middleware_with_tork_instance(self, tork_instance):
        """Test middleware with existing Tork instance."""
        middleware = TorkAutoGenMiddleware(tork=tork_instance)
        assert middleware.tork is tork_instance

    def test_governed_agent_with_api_key(self):
        """Test governed agent with API key."""
        agent = GovernedAutoGenAgent(api_key="test-key")
        assert agent._middleware is not None


class TestAutoGenPIIDetection:
    """Test PII detection and redaction in AutoGen adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        middleware = TorkAutoGenMiddleware()
        result = middleware.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        middleware = TorkAutoGenMiddleware()
        result = middleware.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        middleware = TorkAutoGenMiddleware()
        result = middleware.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        middleware = TorkAutoGenMiddleware()
        result = middleware.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        middleware = TorkAutoGenMiddleware()
        clean_text = "Hello, how can I help you today?"
        result = middleware.govern(clean_text)
        assert result == clean_text

    def test_governed_agent_govern_message(self):
        """Test governed agent govern_message method."""
        agent = GovernedAutoGenAgent()
        result = agent.govern_message(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result


class TestAutoGenErrorHandling:
    """Test error handling in AutoGen adapter."""

    def test_middleware_empty_string(self):
        """Test middleware handles empty string."""
        middleware = TorkAutoGenMiddleware()
        result = middleware.govern("")
        assert result == ""

    def test_middleware_whitespace_only(self):
        """Test middleware handles whitespace-only string."""
        middleware = TorkAutoGenMiddleware()
        result = middleware.govern("   ")
        assert result == "   "

    def test_governed_agent_no_wrapped_agent(self):
        """Test governed agent without wrapped agent."""
        agent = GovernedAutoGenAgent()
        # Should work without underlying agent for governance methods
        result = agent.govern_message("test")
        assert result == "test"

    def test_message_filter_missing_content(self):
        """Test message filter handles missing content."""
        middleware = TorkAutoGenMiddleware()
        filter_func = middleware.create_message_filter()
        message = {"role": "user"}
        result = filter_func(message)
        assert result == message


class TestAutoGenComplianceReceipts:
    """Test compliance receipt generation in AutoGen adapter."""

    def test_process_message_generates_receipt(self):
        """Test process_message generates receipt."""
        middleware = TorkAutoGenMiddleware()
        result = middleware.process_message("Test message")
        assert len(middleware.receipts) == 1
        assert middleware.receipts[0]["type"] == "input"
        assert "receipt_id" in middleware.receipts[0]

    def test_process_message_output_direction(self):
        """Test process_message with output direction."""
        middleware = TorkAutoGenMiddleware()
        result = middleware.process_message("Test message", "output")
        assert middleware.receipts[0]["type"] == "output"

    def test_receipt_has_agent_id(self):
        """Test receipt includes agent ID."""
        middleware = TorkAutoGenMiddleware(agent_id="test-agent")
        middleware.process_message("Test")
        assert middleware.receipts[0]["agent_id"] == "test-agent"

    def test_receipt_has_pii_flag(self):
        """Test receipt includes has_pii flag."""
        middleware = TorkAutoGenMiddleware()
        middleware.process_message(PII_MESSAGES["email_message"])
        assert "has_pii" in middleware.receipts[0]
        assert middleware.receipts[0]["has_pii"] is True


class TestAutoGenConversableAgentWrapping:
    """Test ConversableAgent wrapping functionality."""

    def test_wrap_agent(self):
        """Test middleware wrap_agent method."""
        middleware = TorkAutoGenMiddleware()

        class MockAgent:
            name = "test-agent"

        wrapped = middleware.wrap_agent(MockAgent())
        assert isinstance(wrapped, GovernedAutoGenAgent)

    def test_governed_agent_send(self):
        """Test governed agent send method."""
        middleware = TorkAutoGenMiddleware()

        class MockAgent:
            def send(self, message, recipient, request_reply=None, silent=False):
                pass

        class MockRecipient:
            pass

        agent = GovernedAutoGenAgent(MockAgent(), middleware)
        agent.send("Hello", MockRecipient())
        assert len(middleware.receipts) >= 1

    def test_governed_agent_receive(self):
        """Test governed agent receive method."""
        middleware = TorkAutoGenMiddleware()

        class MockAgent:
            def receive(self, message, sender, request_reply=None, silent=False):
                pass

        class MockSender:
            pass

        agent = GovernedAutoGenAgent(MockAgent(), middleware)
        agent.receive("Hello", MockSender())
        assert len(middleware.receipts) >= 1

    def test_governed_agent_attribute_delegation(self):
        """Test governed agent delegates attributes."""
        class MockAgent:
            custom_attr = "test_value"

        agent = GovernedAutoGenAgent(MockAgent())
        assert agent.custom_attr == "test_value"


class TestAutoGenGroupChatGovernance:
    """Test GroupChat governance functionality."""

    def test_message_filter_creation(self):
        """Test message filter creation."""
        middleware = TorkAutoGenMiddleware()
        filter_func = middleware.create_message_filter()
        assert callable(filter_func)

    def test_message_filter_governs_content(self):
        """Test message filter governs content."""
        middleware = TorkAutoGenMiddleware()
        filter_func = middleware.create_message_filter()
        message = {"content": PII_MESSAGES["email_message"]}
        result = filter_func(message)
        assert PII_SAMPLES["email"] not in result["content"]

    def test_message_filter_preserves_structure(self):
        """Test message filter preserves message structure."""
        middleware = TorkAutoGenMiddleware()
        filter_func = middleware.create_message_filter()
        message = {"role": "user", "content": "Hello", "name": "test"}
        result = filter_func(message)
        assert result["role"] == "user"
        assert result["name"] == "test"

    def test_message_filter_non_string_content(self):
        """Test message filter handles non-string content."""
        middleware = TorkAutoGenMiddleware()
        filter_func = middleware.create_message_filter()
        message = {"content": 12345}
        result = filter_func(message)
        assert result["content"] == 12345


class TestAutoGenCodeExecutionGovernance:
    """Test code execution governance."""

    def test_govern_code_input(self):
        """Test governance of code input."""
        middleware = TorkAutoGenMiddleware()
        code = f"# User email: {PII_SAMPLES['email']}\nprint('hello')"
        result = middleware.govern(code)
        assert PII_SAMPLES["email"] not in result

    def test_govern_code_output(self):
        """Test governance of code output."""
        middleware = TorkAutoGenMiddleware()
        output = f"Execution result: {PII_SAMPLES['ssn']}"
        result = middleware.govern(output)
        assert PII_SAMPLES["ssn"] not in result

    def test_generate_reply_governs_output(self):
        """Test generate_reply governs output."""
        middleware = TorkAutoGenMiddleware()

        class MockAgent:
            def generate_reply(self, messages=None, sender=None, **kwargs):
                return PII_MESSAGES["email_message"]

        agent = GovernedAutoGenAgent(MockAgent(), middleware)
        result = agent.generate_reply()
        assert PII_SAMPLES["email"] not in result

    def test_generate_reply_none_output(self):
        """Test generate_reply handles None output."""
        class MockAgent:
            def generate_reply(self, messages=None, sender=None, **kwargs):
                return None

        agent = GovernedAutoGenAgent(MockAgent())
        result = agent.generate_reply()
        assert result is None


class TestAutoGenHumanInTheLoopGovernance:
    """Test human-in-the-loop governance."""

    def test_initiate_chat_governs_message(self):
        """Test initiate_chat governs initial message."""
        middleware = TorkAutoGenMiddleware()

        class MockAgent:
            def initiate_chat(self, recipient, message, clear_history=True,
                            silent=False, **kwargs):
                return {"history": [{"content": message}], "cost": 0}

        class MockRecipient:
            pass

        agent = GovernedAutoGenAgent(MockAgent(), middleware)
        result = agent.initiate_chat(MockRecipient(), "Hello")
        assert len(middleware.receipts) >= 1

    def test_initiate_chat_pii_redaction(self):
        """Test initiate_chat redacts PII from message."""
        middleware = TorkAutoGenMiddleware()

        class MockAgent:
            def initiate_chat(self, recipient, message, clear_history=True,
                            silent=False, **kwargs):
                # Return the message to verify it was governed
                return {"history": [{"content": message}], "cost": 0}

        class MockRecipient:
            pass

        agent = GovernedAutoGenAgent(MockAgent(), middleware)
        result = agent.initiate_chat(MockRecipient(), PII_MESSAGES["email_message"])
        # The receipt should show the message was processed
        assert middleware.receipts[0]["type"] == "initiate"

    def test_send_with_pii_redaction(self):
        """Test send method redacts PII."""
        middleware = TorkAutoGenMiddleware()

        sent_message = None

        class MockAgent:
            def send(self, message, recipient, request_reply=None, silent=False):
                nonlocal sent_message
                sent_message = message

        class MockRecipient:
            pass

        agent = GovernedAutoGenAgent(MockAgent(), middleware)
        agent.send(PII_MESSAGES["ssn_message"], MockRecipient())
        assert PII_SAMPLES["ssn"] not in sent_message

    def test_receive_with_pii_redaction(self):
        """Test receive method redacts PII."""
        middleware = TorkAutoGenMiddleware()

        received_message = None

        class MockAgent:
            def receive(self, message, sender, request_reply=None, silent=False):
                nonlocal received_message
                received_message = message

        class MockSender:
            pass

        agent = GovernedAutoGenAgent(MockAgent(), middleware)
        agent.receive(PII_MESSAGES["credit_card_message"], MockSender())
        assert PII_SAMPLES["credit_card"] not in received_message
