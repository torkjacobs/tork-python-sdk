"""
Tests for OpenAI Agents adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Agent creation governance
- Tool call governance
- Run governance
- Thread message governance
"""

import pytest
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.openai_agents import (
    TorkOpenAIAgentsMiddleware,
    GovernedOpenAIAgent,
    GovernedRunner,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestOpenAIAgentsImportInstantiation:
    """Test import and instantiation of OpenAI Agents adapter."""

    def test_import_middleware(self):
        """Test TorkOpenAIAgentsMiddleware can be imported."""
        assert TorkOpenAIAgentsMiddleware is not None

    def test_import_governed_agent(self):
        """Test GovernedOpenAIAgent can be imported."""
        assert GovernedOpenAIAgent is not None

    def test_import_governed_runner(self):
        """Test GovernedRunner can be imported."""
        assert GovernedRunner is not None

    def test_instantiate_middleware_default(self):
        """Test middleware instantiation with defaults."""
        middleware = TorkOpenAIAgentsMiddleware()
        assert middleware is not None
        assert middleware.tork is not None
        assert middleware.agent_id == "openai-agent"
        assert middleware.receipts == []


class TestOpenAIAgentsConfiguration:
    """Test configuration of OpenAI Agents adapter."""

    def test_middleware_with_policy_version(self):
        """Test middleware with custom policy version."""
        middleware = TorkOpenAIAgentsMiddleware(policy_version="2.0.0")
        assert middleware.tork is not None

    def test_middleware_with_agent_id(self):
        """Test middleware with custom agent ID."""
        middleware = TorkOpenAIAgentsMiddleware(agent_id="custom-agent")
        assert middleware.agent_id == "custom-agent"

    def test_middleware_with_tork_instance(self, tork_instance):
        """Test middleware with existing Tork instance."""
        middleware = TorkOpenAIAgentsMiddleware(tork=tork_instance)
        assert middleware.tork is tork_instance

    def test_create_governed_runner(self):
        """Test creating governed runner from middleware."""
        middleware = TorkOpenAIAgentsMiddleware()
        runner = middleware.create_governed_runner()
        assert isinstance(runner, GovernedRunner)


class TestOpenAIAgentsPIIDetection:
    """Test PII detection and redaction in OpenAI Agents adapter."""

    def test_process_input_email_pii(self):
        """Test email PII is detected and redacted in input."""
        middleware = TorkOpenAIAgentsMiddleware()
        result = middleware.process_input(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result.output
        assert "[EMAIL_REDACTED]" in result.output

    def test_process_input_phone_pii(self):
        """Test phone PII is detected and redacted in input."""
        middleware = TorkOpenAIAgentsMiddleware()
        result = middleware.process_input(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result.output
        assert "[PHONE_REDACTED]" in result.output

    def test_process_output_ssn_pii(self):
        """Test SSN PII is detected and redacted in output."""
        middleware = TorkOpenAIAgentsMiddleware()
        result = middleware.process_output(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result.output
        assert "[SSN_REDACTED]" in result.output

    def test_process_output_credit_card_pii(self):
        """Test credit card PII is detected and redacted in output."""
        middleware = TorkOpenAIAgentsMiddleware()
        result = middleware.process_output(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result.output
        assert "[CARD_REDACTED]" in result.output

    def test_process_input_clean_text(self):
        """Test clean text passes through unchanged."""
        middleware = TorkOpenAIAgentsMiddleware()
        clean_text = "Hello, how can I help you today?"
        result = middleware.process_input(clean_text)
        assert result.output == clean_text

    def test_process_mixed_pii(self):
        """Test multiple PII types in same text."""
        middleware = TorkOpenAIAgentsMiddleware()
        result = middleware.process_input(PII_MESSAGES["mixed_message"])
        assert PII_SAMPLES["email"] not in result.output
        assert PII_SAMPLES["phone_us"] not in result.output


class TestOpenAIAgentsErrorHandling:
    """Test error handling in OpenAI Agents adapter."""

    def test_middleware_empty_string(self):
        """Test middleware handles empty string."""
        middleware = TorkOpenAIAgentsMiddleware()
        result = middleware.process_input("")
        assert result.output == ""

    def test_middleware_whitespace_only(self):
        """Test middleware handles whitespace-only string."""
        middleware = TorkOpenAIAgentsMiddleware()
        result = middleware.process_input("   ")
        assert result.output == "   "

    def test_governed_agent_run_fallback(self):
        """Test governed agent run with fallback (no run method)."""
        middleware = TorkOpenAIAgentsMiddleware()

        class MockAgent:
            pass  # No run method

        agent = GovernedOpenAIAgent(MockAgent(), middleware)
        result = agent.run("Test input")
        assert "Agent response" in result

    def test_governed_runner_wraps_unwrapped_agent(self):
        """Test runner wraps unwrapped agent automatically."""
        middleware = TorkOpenAIAgentsMiddleware()
        runner = GovernedRunner(middleware)

        class MockAgent:
            def run(self, user_input, **kwargs):
                return f"Response: {user_input}"

        result = runner.run(MockAgent(), "Hello")
        assert "Response" in result


class TestOpenAIAgentsComplianceReceipts:
    """Test compliance receipt generation in OpenAI Agents adapter."""

    def test_process_input_generates_receipt(self):
        """Test process_input generates receipt."""
        middleware = TorkOpenAIAgentsMiddleware()
        result = middleware.process_input("Test message")
        assert len(middleware.receipts) == 1
        assert middleware.receipts[0]["type"] == "input"
        assert "receipt_id" in middleware.receipts[0]

    def test_process_output_generates_receipt(self):
        """Test process_output generates receipt."""
        middleware = TorkOpenAIAgentsMiddleware()
        result = middleware.process_output("Test message")
        assert len(middleware.receipts) == 1
        assert middleware.receipts[0]["type"] == "output"

    def test_receipt_has_agent_id(self):
        """Test receipt includes agent ID."""
        middleware = TorkOpenAIAgentsMiddleware(agent_id="test-agent")
        middleware.process_input("Test")
        assert middleware.receipts[0]["agent_id"] == "test-agent"

    def test_check_tool_call_generates_receipt(self):
        """Test check_tool_call generates receipt."""
        middleware = TorkOpenAIAgentsMiddleware()
        result = middleware.check_tool_call("search", {"query": "test"})
        assert len(middleware.receipts) == 1
        assert middleware.receipts[0]["type"] == "tool_call"
        assert middleware.receipts[0]["tool_name"] == "search"


class TestOpenAIAgentsAgentCreationGovernance:
    """Test agent creation governance."""

    def test_wrap_agent(self):
        """Test middleware wrap_agent method."""
        middleware = TorkOpenAIAgentsMiddleware()

        class MockAgent:
            name = "test-agent"
            instructions = "Help users"

        wrapped = middleware.wrap_agent(MockAgent())
        assert isinstance(wrapped, GovernedOpenAIAgent)

    def test_wrapped_agent_property(self):
        """Test wrapped_agent property."""
        middleware = TorkOpenAIAgentsMiddleware()

        class MockAgent:
            name = "test-agent"

        mock = MockAgent()
        wrapped = GovernedOpenAIAgent(mock, middleware)
        assert wrapped.wrapped_agent is mock

    def test_governed_agent_attribute_delegation(self):
        """Test governed agent delegates attributes."""
        middleware = TorkOpenAIAgentsMiddleware()

        class MockAgent:
            name = "test-agent"
            instructions = "Help users"
            custom_attr = "test_value"

        wrapped = middleware.wrap_agent(MockAgent())
        assert wrapped.custom_attr == "test_value"
        assert wrapped.name == "test-agent"

    def test_governed_agent_run_basic(self):
        """Test governed agent run method."""
        middleware = TorkOpenAIAgentsMiddleware()

        class MockAgent:
            def run(self, user_input, **kwargs):
                return f"Response to: {user_input}"

        agent = GovernedOpenAIAgent(MockAgent(), middleware)
        result = agent.run("Hello")
        assert "Response to" in result


class TestOpenAIAgentsToolCallGovernance:
    """Test tool call governance."""

    def test_check_tool_call_basic(self):
        """Test basic tool call check."""
        middleware = TorkOpenAIAgentsMiddleware()
        result = middleware.check_tool_call("search", {"query": "AI safety"})
        assert result is not None
        assert hasattr(result, "action")

    def test_check_tool_call_with_pii(self):
        """Test tool call check with PII."""
        middleware = TorkOpenAIAgentsMiddleware()
        result = middleware.check_tool_call("send_email", {
            "to": PII_SAMPLES["email"],
            "body": "Hello"
        })
        assert len(middleware.receipts) == 1

    def test_check_tool_call_receipt_has_tool_name(self):
        """Test tool call receipt includes tool name."""
        middleware = TorkOpenAIAgentsMiddleware()
        middleware.check_tool_call("web_search", {"query": "test"})
        assert middleware.receipts[0]["tool_name"] == "web_search"

    def test_check_tool_call_action_recorded(self):
        """Test tool call action is recorded."""
        middleware = TorkOpenAIAgentsMiddleware()
        middleware.check_tool_call("function", {"arg": "value"})
        assert "action" in middleware.receipts[0]


class TestOpenAIAgentsRunGovernance:
    """Test run governance."""

    def test_governed_agent_run_governs_input(self):
        """Test agent run governs input."""
        middleware = TorkOpenAIAgentsMiddleware()

        class MockAgent:
            def run(self, user_input, **kwargs):
                return f"Got: {user_input}"

        agent = GovernedOpenAIAgent(MockAgent(), middleware)
        result = agent.run(PII_MESSAGES["email_message"])
        # Input should be governed before reaching agent
        assert len(middleware.receipts) >= 1

    def test_governed_agent_run_governs_output(self):
        """Test agent run governs output."""
        middleware = TorkOpenAIAgentsMiddleware()

        class MockAgent:
            def run(self, user_input, **kwargs):
                return PII_MESSAGES["ssn_message"]

        agent = GovernedOpenAIAgent(MockAgent(), middleware)
        result = agent.run("Get my info")
        assert PII_SAMPLES["ssn"] not in result

    def test_governed_runner_run(self):
        """Test governed runner run method."""
        middleware = TorkOpenAIAgentsMiddleware()
        runner = GovernedRunner(middleware)

        class MockAgent:
            def run(self, user_input, **kwargs):
                return "Response"

        result = runner.run(MockAgent(), "Hello")
        assert result == "Response"

    def test_governed_runner_with_wrapped_agent(self):
        """Test runner with already wrapped agent."""
        middleware = TorkOpenAIAgentsMiddleware()
        runner = GovernedRunner(middleware)

        class MockAgent:
            def run(self, user_input, **kwargs):
                return "Response"

        wrapped = GovernedOpenAIAgent(MockAgent(), middleware)
        result = runner.run(wrapped, "Hello")
        assert result == "Response"


class TestOpenAIAgentsThreadMessageGovernance:
    """Test thread message governance."""

    def test_process_input_for_thread_message(self):
        """Test processing thread message input."""
        middleware = TorkOpenAIAgentsMiddleware()
        result = middleware.process_input("User message with " + PII_SAMPLES["email"])
        assert PII_SAMPLES["email"] not in result.output

    def test_process_output_for_thread_message(self):
        """Test processing thread message output."""
        middleware = TorkOpenAIAgentsMiddleware()
        result = middleware.process_output("Assistant found " + PII_SAMPLES["phone_us"])
        assert PII_SAMPLES["phone_us"] not in result.output

    def test_multiple_thread_messages(self):
        """Test governance of multiple thread messages."""
        middleware = TorkOpenAIAgentsMiddleware()
        messages = [
            "Hello, I need help",
            f"My email is {PII_SAMPLES['email']}",
            f"And phone is {PII_SAMPLES['phone_us']}"
        ]

        for msg in messages:
            middleware.process_input(msg)

        assert len(middleware.receipts) == 3

    def test_thread_message_receipt_ordering(self):
        """Test receipt ordering matches message order."""
        middleware = TorkOpenAIAgentsMiddleware()

        middleware.process_input("First")
        middleware.process_output("Second")
        middleware.process_input("Third")

        assert middleware.receipts[0]["type"] == "input"
        assert middleware.receipts[1]["type"] == "output"
        assert middleware.receipts[2]["type"] == "input"


class TestOpenAIAgentsAsyncSupport:
    """Test async support for OpenAI Agents."""

    @pytest.mark.asyncio
    async def test_governed_runner_async(self):
        """Test governed runner async method."""
        middleware = TorkOpenAIAgentsMiddleware()
        runner = GovernedRunner(middleware)

        class MockAgent:
            def run(self, user_input, **kwargs):
                return "Async response"

        result = await runner.run_async(MockAgent(), "Hello")
        assert result == "Async response"

    @pytest.mark.asyncio
    async def test_governed_runner_async_governs_pii(self):
        """Test async runner still governs PII."""
        middleware = TorkOpenAIAgentsMiddleware()
        runner = GovernedRunner(middleware)

        class MockAgent:
            def run(self, user_input, **kwargs):
                return PII_MESSAGES["email_message"]

        result = await runner.run_async(MockAgent(), "Get email")
        assert PII_SAMPLES["email"] not in result
