"""
Tests for CrewAI adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Crew wrapping
- Agent task governance
- Inter-agent communication governance
- Hierarchical crew governance
"""

import pytest
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.crewai import (
    TorkCrewAIMiddleware,
    GovernedAgent,
    GovernedCrew,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestCrewAIImportInstantiation:
    """Test import and instantiation of CrewAI adapter."""

    def test_import_middleware(self):
        """Test TorkCrewAIMiddleware can be imported."""
        assert TorkCrewAIMiddleware is not None

    def test_import_governed_agent(self):
        """Test GovernedAgent can be imported."""
        assert GovernedAgent is not None

    def test_import_governed_crew(self):
        """Test GovernedCrew can be imported."""
        assert GovernedCrew is not None

    def test_instantiate_middleware_default(self):
        """Test middleware instantiation with defaults."""
        middleware = TorkCrewAIMiddleware()
        assert middleware is not None
        assert middleware.tork is not None
        assert middleware.agent_id == "crewai-agent"
        assert middleware.receipts == []

    def test_instantiate_governed_agent_default(self):
        """Test governed agent instantiation with defaults."""
        agent = GovernedAgent()
        assert agent is not None
        assert agent._middleware is not None


class TestCrewAIConfiguration:
    """Test configuration of CrewAI adapter."""

    def test_middleware_with_policy_version(self):
        """Test middleware with custom policy version."""
        middleware = TorkCrewAIMiddleware(policy_version="2.0.0")
        assert middleware.tork is not None

    def test_middleware_with_agent_id(self):
        """Test middleware with custom agent ID."""
        middleware = TorkCrewAIMiddleware(agent_id="custom-agent")
        assert middleware.agent_id == "custom-agent"

    def test_middleware_with_tork_instance(self, tork_instance):
        """Test middleware with existing Tork instance."""
        middleware = TorkCrewAIMiddleware(tork=tork_instance)
        assert middleware.tork is tork_instance

    def test_governed_agent_with_api_key(self):
        """Test governed agent with API key."""
        agent = GovernedAgent(api_key="test-key")
        assert agent._middleware is not None


class TestCrewAIPIIDetection:
    """Test PII detection and redaction in CrewAI adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        middleware = TorkCrewAIMiddleware()
        result = middleware.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        middleware = TorkCrewAIMiddleware()
        result = middleware.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        middleware = TorkCrewAIMiddleware()
        result = middleware.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        middleware = TorkCrewAIMiddleware()
        result = middleware.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        middleware = TorkCrewAIMiddleware()
        clean_text = "Hello, how can I help you today?"
        result = middleware.govern(clean_text)
        assert result == clean_text

    def test_governed_agent_govern_input(self):
        """Test governed agent govern_input method."""
        agent = GovernedAgent()
        result = agent.govern_input(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result


class TestCrewAIErrorHandling:
    """Test error handling in CrewAI adapter."""

    def test_middleware_empty_string(self):
        """Test middleware handles empty string."""
        middleware = TorkCrewAIMiddleware()
        result = middleware.govern("")
        assert result == ""

    def test_middleware_whitespace_only(self):
        """Test middleware handles whitespace-only string."""
        middleware = TorkCrewAIMiddleware()
        result = middleware.govern("   ")
        assert result == "   "

    def test_governed_agent_no_wrapped_agent(self):
        """Test governed agent without wrapped agent."""
        agent = GovernedAgent()
        # Should work without underlying agent for governance methods
        result = agent.govern_input("test")
        assert result == "test"

    def test_governed_crew_no_wrapped_crew(self):
        """Test governed crew without wrapped crew."""
        crew = GovernedCrew()
        # Kickoff should handle missing crew gracefully
        result = crew.kickoff()
        assert result is not None


class TestCrewAIComplianceReceipts:
    """Test compliance receipt generation in CrewAI adapter."""

    def test_process_input_generates_receipt(self):
        """Test process_input generates receipt."""
        middleware = TorkCrewAIMiddleware()
        result = middleware.process_input("Test message")
        assert len(middleware.receipts) == 1
        assert middleware.receipts[0]["type"] == "input"
        assert "receipt_id" in middleware.receipts[0]

    def test_process_output_generates_receipt(self):
        """Test process_output generates receipt."""
        middleware = TorkCrewAIMiddleware()
        result = middleware.process_output("Test message")
        assert len(middleware.receipts) == 1
        assert middleware.receipts[0]["type"] == "output"

    def test_receipt_has_agent_id(self):
        """Test receipt includes agent ID."""
        middleware = TorkCrewAIMiddleware(agent_id="test-agent")
        middleware.process_input("Test")
        assert middleware.receipts[0]["agent_id"] == "test-agent"

    def test_check_tool_call_generates_receipt(self):
        """Test check_tool_call generates receipt."""
        middleware = TorkCrewAIMiddleware()
        result = middleware.check_tool_call("search", {"query": "test"})
        assert len(middleware.receipts) == 1
        assert middleware.receipts[0]["type"] == "tool_call"
        assert middleware.receipts[0]["tool_name"] == "search"


class TestCrewAICrewWrapping:
    """Test crew wrapping functionality."""

    def test_wrap_agent(self):
        """Test middleware wrap_agent method."""
        middleware = TorkCrewAIMiddleware()

        class MockAgent:
            role = "Researcher"

        wrapped = middleware.wrap_agent(MockAgent())
        assert isinstance(wrapped, GovernedAgent)

    def test_wrap_crew(self):
        """Test middleware wrap_crew method."""
        middleware = TorkCrewAIMiddleware()

        class MockCrew:
            agents = []
            tasks = []

        wrapped = middleware.wrap_crew(MockCrew())
        assert isinstance(wrapped, GovernedCrew)

    def test_governed_crew_kickoff(self):
        """Test governed crew kickoff."""
        class MockCrew:
            def kickoff(self, inputs=None):
                return "Crew output"

        crew = GovernedCrew(MockCrew())
        result = crew.kickoff()
        assert result == "Crew output"

    def test_governed_crew_kickoff_with_inputs(self):
        """Test governed crew kickoff with inputs."""
        class MockCrew:
            def kickoff(self, inputs=None):
                return f"Processed: {inputs}"

        crew = GovernedCrew(MockCrew())
        result = crew.kickoff({"data": "test"})
        assert "Processed" in result


class TestCrewAIAgentTaskGovernance:
    """Test agent task governance."""

    def test_execute_task_governs_description(self):
        """Test execute_task governs task description."""
        middleware = TorkCrewAIMiddleware()

        class MockAgent:
            def execute_task(self, task, context=None, tools=None):
                return "Task completed"

        class MockTask:
            description = "Test task"

        agent = GovernedAgent(MockAgent(), middleware)
        result = agent.execute_task(MockTask())
        assert result == "Task completed"
        assert len(middleware.receipts) >= 1

    def test_execute_task_governs_output(self):
        """Test execute_task governs task output."""
        middleware = TorkCrewAIMiddleware()

        class MockAgent:
            def execute_task(self, task, context=None, tools=None):
                return f"Result: {PII_SAMPLES['email']}"

        class MockTask:
            description = "Find email"

        agent = GovernedAgent(MockAgent(), middleware)
        result = agent.execute_task(MockTask())
        assert PII_SAMPLES["email"] not in result

    def test_execute_task_with_pii_description(self):
        """Test task with PII in description is governed."""
        middleware = TorkCrewAIMiddleware()

        class MockAgent:
            def execute_task(self, task, context=None, tools=None):
                return "Done"

        class MockTask:
            description = PII_MESSAGES["email_message"]

        agent = GovernedAgent(MockAgent(), middleware)
        result = agent.execute_task(MockTask())
        # Should complete without error
        assert result is not None


class TestCrewAIInterAgentCommunication:
    """Test inter-agent communication governance."""

    def test_govern_input_method(self):
        """Test govern_input method for inter-agent comms."""
        middleware = TorkCrewAIMiddleware()
        result = middleware.govern_input(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_govern_output_method(self):
        """Test govern_output method for inter-agent comms."""
        middleware = TorkCrewAIMiddleware()
        result = middleware.govern_output(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result

    def test_multiple_agents_share_middleware(self):
        """Test multiple agents can share middleware."""
        middleware = TorkCrewAIMiddleware()
        agent1 = GovernedAgent(middleware=middleware)
        agent2 = GovernedAgent(middleware=middleware)

        agent1.govern_input("Message 1")
        agent2.govern_input("Message 2")

        # Both should use same middleware receipts
        assert len(middleware.receipts) == 2

    def test_govern_alias(self):
        """Test govern method is alias for govern_input."""
        middleware = TorkCrewAIMiddleware()
        input_result = middleware.govern_input("test")
        alias_result = middleware.govern("test")
        assert input_result == alias_result


class TestCrewAIHierarchicalGovernance:
    """Test hierarchical crew governance."""

    def test_governed_crew_input_governance(self):
        """Test crew governs inputs before processing."""
        class MockCrew:
            def kickoff(self, inputs=None):
                return f"Got: {inputs.get('data', '')}"

        crew = GovernedCrew(MockCrew())
        result = crew.kickoff({"data": PII_MESSAGES["email_message"]})
        # The input should be governed
        assert result is not None

    def test_governed_crew_output_governance(self):
        """Test crew governs output after processing."""
        class MockCrew:
            def kickoff(self, inputs=None):
                return PII_MESSAGES["ssn_message"]

        crew = GovernedCrew(MockCrew())
        result = crew.kickoff()
        assert PII_SAMPLES["ssn"] not in result

    def test_governed_crew_govern_input_method(self):
        """Test governed crew has govern_input method."""
        crew = GovernedCrew()
        result = crew.govern_input(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_governed_crew_attribute_delegation(self):
        """Test governed crew delegates attributes."""
        class MockCrew:
            custom_attr = "test_value"

        crew = GovernedCrew(MockCrew())
        assert crew.custom_attr == "test_value"
