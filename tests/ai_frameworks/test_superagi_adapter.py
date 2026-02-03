"""
Tests for SuperAGI adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Agent action governance
- Tool execution governance
- Resource governance
- Memory governance
- Goal governance
"""

import pytest
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.superagi import (
    TorkSuperAGIAgent,
    TorkSuperAGITool,
    TorkSuperAGIWorkflow,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestSuperAGIImportInstantiation:
    """Test import and instantiation of SuperAGI adapter."""

    def test_import_agent(self):
        """Test TorkSuperAGIAgent can be imported."""
        assert TorkSuperAGIAgent is not None

    def test_import_tool(self):
        """Test TorkSuperAGITool can be imported."""
        assert TorkSuperAGITool is not None

    def test_import_workflow(self):
        """Test TorkSuperAGIWorkflow can be imported."""
        assert TorkSuperAGIWorkflow is not None

    def test_instantiate_agent_default(self):
        """Test agent instantiation with defaults."""
        agent = TorkSuperAGIAgent()
        assert agent is not None
        assert agent.tork is not None
        assert agent.receipts == []

    def test_instantiate_tool_default(self):
        """Test tool instantiation with defaults."""
        tool = TorkSuperAGITool()
        assert tool is not None
        assert tool.tork is not None


class TestSuperAGIConfiguration:
    """Test configuration of SuperAGI adapter."""

    def test_agent_with_tork_instance(self, tork_instance):
        """Test agent with existing Tork instance."""
        agent = TorkSuperAGIAgent(tork=tork_instance)
        assert agent.tork is tork_instance

    def test_tool_with_tork_instance(self, tork_instance):
        """Test tool with existing Tork instance."""
        tool = TorkSuperAGITool(tork=tork_instance)
        assert tool.tork is tork_instance

    def test_workflow_with_tork_instance(self, tork_instance):
        """Test workflow with existing Tork instance."""
        workflow = TorkSuperAGIWorkflow(tork=tork_instance)
        assert workflow.tork is tork_instance

    def test_agent_with_api_key(self):
        """Test agent with API key."""
        agent = TorkSuperAGIAgent(api_key="test-key")
        assert agent.tork is not None


class TestSuperAGIPIIDetection:
    """Test PII detection and redaction in SuperAGI adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        agent = TorkSuperAGIAgent()
        result = agent.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        agent = TorkSuperAGIAgent()
        result = agent.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        agent = TorkSuperAGIAgent()
        result = agent.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        agent = TorkSuperAGIAgent()
        result = agent.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        agent = TorkSuperAGIAgent()
        clean_text = "Research market trends"
        result = agent.govern(clean_text)
        assert result == clean_text


class TestSuperAGIErrorHandling:
    """Test error handling in SuperAGI adapter."""

    def test_agent_empty_string(self):
        """Test agent handles empty string."""
        agent = TorkSuperAGIAgent()
        result = agent.govern("")
        assert result == ""

    def test_agent_whitespace(self):
        """Test agent handles whitespace."""
        agent = TorkSuperAGIAgent()
        result = agent.govern("   ")
        assert result == "   "

    def test_tool_empty_string(self):
        """Test tool handles empty string."""
        tool = TorkSuperAGITool()
        result = tool.govern("")
        assert result == ""

    def test_agent_empty_receipts(self):
        """Test agent starts with empty receipts."""
        agent = TorkSuperAGIAgent()
        assert agent.get_receipts() == []


class TestSuperAGIComplianceReceipts:
    """Test compliance receipt generation in SuperAGI adapter."""

    def test_agent_run_generates_receipt(self):
        """Test agent run generates receipt."""
        class MockAgent:
            def run(self, task, **kwargs):
                return f"Completed: {task}"

        agent = TorkSuperAGIAgent(MockAgent())
        agent.run("Test task")
        assert len(agent.receipts) >= 1
        assert agent.receipts[0]["type"] == "agent_task"
        assert "receipt_id" in agent.receipts[0]

    def test_agent_get_receipts(self):
        """Test agent get_receipts method."""
        agent = TorkSuperAGIAgent()
        receipts = agent.get_receipts()
        assert isinstance(receipts, list)


class TestSuperAGIAgentActionGovernance:
    """Test agent action governance."""

    def test_agent_run_governs_task(self):
        """Test agent run governs task input."""
        class MockAgent:
            def run(self, task, **kwargs):
                return task

        agent = TorkSuperAGIAgent(MockAgent())
        result = agent.run(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_agent_run_governs_output(self):
        """Test agent run governs output."""
        class MockAgent:
            def run(self, task, **kwargs):
                return PII_MESSAGES["ssn_message"]

        agent = TorkSuperAGIAgent(MockAgent())
        result = agent.run("get ssn")
        assert PII_SAMPLES["ssn"] not in result

    def test_agent_run_dict_output(self):
        """Test agent run governs dict output."""
        class MockAgent:
            def run(self, task, **kwargs):
                return {"result": PII_MESSAGES["phone_message"]}

        agent = TorkSuperAGIAgent(MockAgent())
        result = agent.run("get phone")
        assert PII_SAMPLES["phone_us"] not in result["result"]

    def test_govern_task_alias(self):
        """Test govern_task is alias for govern."""
        agent = TorkSuperAGIAgent()
        result1 = agent.govern("test")
        result2 = agent.govern_task("test")
        assert result1 == result2


class TestSuperAGIToolExecutionGovernance:
    """Test tool execution governance."""

    def test_tool_decorator(self):
        """Test governed_tool decorator."""
        tool = TorkSuperAGITool()

        @tool.governed_tool
        def search(query: str) -> str:
            return f"Results for: {query}"

        result = search("test query")
        assert result == "Results for: test query"

    def test_tool_governs_input(self):
        """Test tool governs input arguments."""
        tool = TorkSuperAGITool()

        @tool.governed_tool
        def process(data: str) -> str:
            return data

        result = process(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_tool_governs_output(self):
        """Test tool governs output."""
        tool = TorkSuperAGITool()

        @tool.governed_tool
        def get_data() -> str:
            return PII_MESSAGES["credit_card_message"]

        result = get_data()
        assert PII_SAMPLES["credit_card"] not in result

    def test_tool_generates_receipts(self):
        """Test tool generates receipts."""
        tool = TorkSuperAGITool()

        @tool.governed_tool
        def process(text: str) -> str:
            return text

        process("test")
        assert len(tool.receipts) >= 1


class TestSuperAGIResourceGovernance:
    """Test resource/workflow governance."""

    def test_workflow_govern_method(self):
        """Test workflow govern method."""
        workflow = TorkSuperAGIWorkflow()
        result = workflow.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result

    def test_workflow_execute_governs_input(self):
        """Test workflow execute governs input."""
        class MockWorkflow:
            def execute(self, input_data, **kwargs):
                return f"Executed: {input_data}"

        workflow = TorkSuperAGIWorkflow(MockWorkflow())
        result = workflow.execute(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_workflow_execute_governs_output(self):
        """Test workflow execute governs output."""
        class MockWorkflow:
            def execute(self, input_data, **kwargs):
                return PII_MESSAGES["phone_message"]

        workflow = TorkSuperAGIWorkflow(MockWorkflow())
        result = workflow.execute("test")
        assert PII_SAMPLES["phone_us"] not in result


class TestSuperAGIMemoryGovernance:
    """Test memory governance (via dict governance)."""

    def test_agent_governs_dict_values(self):
        """Test agent governs dictionary values."""
        class MockAgent:
            def run(self, task, **kwargs):
                return {
                    "memory": PII_MESSAGES["email_message"],
                    "context": "clean context"
                }

        agent = TorkSuperAGIAgent(MockAgent())
        result = agent.run("test")
        assert PII_SAMPLES["email"] not in result["memory"]
        assert result["context"] == "clean context"

    def test_agent_dict_value_receipts(self):
        """Test agent generates receipts for dict values."""
        class MockAgent:
            def run(self, task, **kwargs):
                return {"data": "value"}

        agent = TorkSuperAGIAgent(MockAgent())
        agent.run("test")
        assert any(r.get("type") == "agent_dict_value" for r in agent.receipts)


class TestSuperAGIGoalGovernance:
    """Test goal governance."""

    def test_agent_set_goals(self):
        """Test agent set_goals governs goals."""
        class MockAgent:
            def __init__(self):
                self.goals = []

            def set_goals(self, goals):
                self.goals = goals

            def run(self, task, **kwargs):
                return task

        mock_agent = MockAgent()
        agent = TorkSuperAGIAgent(mock_agent)
        agent.set_goals([
            PII_MESSAGES["email_message"],
            "Clean goal"
        ])
        assert PII_SAMPLES["email"] not in mock_agent.goals[0]
        assert mock_agent.goals[1] == "Clean goal"

    def test_agent_goal_receipts(self):
        """Test agent generates goal receipts."""
        class MockAgent:
            def set_goals(self, goals):
                pass

            def run(self, task, **kwargs):
                return task

        agent = TorkSuperAGIAgent(MockAgent())
        agent.set_goals(["Goal 1", "Goal 2"])
        goal_receipts = [r for r in agent.receipts if r["type"] == "agent_goal"]
        assert len(goal_receipts) == 2
