"""
Tests for AgentGPT adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Goal governance
- Task output governance
- Loop governance
- Analysis governance
- Action governance
"""

import pytest
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.agentgpt import (
    TorkAgentGPTAgent,
    TorkAgentGPTTask,
    TorkAgentGPTGoal,
    TorkAgentGPTBrowser,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestAgentGPTImportInstantiation:
    """Test import and instantiation of AgentGPT adapter."""

    def test_import_agent(self):
        """Test TorkAgentGPTAgent can be imported."""
        assert TorkAgentGPTAgent is not None

    def test_import_task(self):
        """Test TorkAgentGPTTask can be imported."""
        assert TorkAgentGPTTask is not None

    def test_import_goal(self):
        """Test TorkAgentGPTGoal can be imported."""
        assert TorkAgentGPTGoal is not None

    def test_instantiate_agent_default(self):
        """Test agent instantiation with defaults."""
        agent = TorkAgentGPTAgent()
        assert agent is not None
        assert agent.tork is not None
        assert agent.receipts == []

    def test_instantiate_task_default(self):
        """Test task instantiation with defaults."""
        task = TorkAgentGPTTask()
        assert task is not None
        assert task.tork is not None


class TestAgentGPTConfiguration:
    """Test configuration of AgentGPT adapter."""

    def test_agent_with_tork_instance(self, tork_instance):
        """Test agent with existing Tork instance."""
        agent = TorkAgentGPTAgent(tork=tork_instance)
        assert agent.tork is tork_instance

    def test_task_with_tork_instance(self, tork_instance):
        """Test task with existing Tork instance."""
        task = TorkAgentGPTTask(tork=tork_instance)
        assert task.tork is tork_instance

    def test_goal_with_tork_instance(self, tork_instance):
        """Test goal with existing Tork instance."""
        goal = TorkAgentGPTGoal(tork=tork_instance)
        assert goal.tork is tork_instance

    def test_agent_with_api_key(self):
        """Test agent with API key."""
        agent = TorkAgentGPTAgent(api_key="test-key")
        assert agent.tork is not None


class TestAgentGPTPIIDetection:
    """Test PII detection and redaction in AgentGPT adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        agent = TorkAgentGPTAgent()
        result = agent.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        agent = TorkAgentGPTAgent()
        result = agent.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        agent = TorkAgentGPTAgent()
        result = agent.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        agent = TorkAgentGPTAgent()
        result = agent.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        agent = TorkAgentGPTAgent()
        clean_text = "Build a web scraper"
        result = agent.govern(clean_text)
        assert result == clean_text


class TestAgentGPTErrorHandling:
    """Test error handling in AgentGPT adapter."""

    def test_agent_empty_string(self):
        """Test agent handles empty string."""
        agent = TorkAgentGPTAgent()
        result = agent.govern("")
        assert result == ""

    def test_agent_whitespace(self):
        """Test agent handles whitespace."""
        agent = TorkAgentGPTAgent()
        result = agent.govern("   ")
        assert result == "   "

    def test_task_empty_string(self):
        """Test task handles empty string."""
        task = TorkAgentGPTTask()
        result = task.govern("")
        assert result == ""

    def test_agent_empty_receipts(self):
        """Test agent starts with empty receipts."""
        agent = TorkAgentGPTAgent()
        assert agent.get_receipts() == []


class TestAgentGPTComplianceReceipts:
    """Test compliance receipt generation in AgentGPT adapter."""

    def test_agent_run_generates_receipt(self):
        """Test agent run generates receipt."""
        class MockAgent:
            def run(self, goal, **kwargs):
                return f"Completed: {goal}"

        agent = TorkAgentGPTAgent(MockAgent())
        agent.run("Test goal")
        assert len(agent.receipts) >= 1
        assert agent.receipts[0]["type"] == "agent_goal"
        assert "receipt_id" in agent.receipts[0]

    def test_task_get_receipts(self):
        """Test task get_receipts method."""
        task = TorkAgentGPTTask()
        receipts = task.get_receipts()
        assert isinstance(receipts, list)


class TestAgentGPTGoalGovernance:
    """Test goal governance."""

    def test_agent_run_governs_goal(self):
        """Test agent run governs goal input."""
        class MockAgent:
            def run(self, goal, **kwargs):
                return goal

        agent = TorkAgentGPTAgent(MockAgent())
        result = agent.run(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_goal_manager_set_goal(self):
        """Test goal manager set_goal governs goal."""
        goal_manager = TorkAgentGPTGoal()
        goal = goal_manager.set_goal(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in goal["description"]

    def test_govern_goal_alias(self):
        """Test govern_goal is alias for govern."""
        agent = TorkAgentGPTAgent()
        result1 = agent.govern("test")
        result2 = agent.govern_goal("test")
        assert result1 == result2


class TestAgentGPTTaskOutputGovernance:
    """Test task output governance."""

    def test_agent_run_governs_output(self):
        """Test agent run governs output."""
        class MockAgent:
            def run(self, goal, **kwargs):
                return PII_MESSAGES["ssn_message"]

        agent = TorkAgentGPTAgent(MockAgent())
        result = agent.run("get ssn")
        assert PII_SAMPLES["ssn"] not in result

    def test_task_create_governs_description(self):
        """Test task create governs description."""
        task = TorkAgentGPTTask()
        created = task.create(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in created["description"]

    def test_task_complete_governs_result(self):
        """Test task complete governs result."""
        task = TorkAgentGPTTask()
        created = task.create("Test task")
        completed = task.complete(created["id"], PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in completed["result"]


class TestAgentGPTLoopGovernance:
    """Test loop/iteration governance."""

    def test_agent_run_dict_output(self):
        """Test agent run governs dict output."""
        class MockAgent:
            def run(self, goal, **kwargs):
                return {"result": PII_MESSAGES["phone_message"]}

        agent = TorkAgentGPTAgent(MockAgent())
        result = agent.run("test")
        assert PII_SAMPLES["phone_us"] not in result["result"]

    def test_agent_run_list_output(self):
        """Test agent run governs list output."""
        class MockAgent:
            def run(self, goal, **kwargs):
                return [PII_MESSAGES["email_message"], "clean"]

        agent = TorkAgentGPTAgent(MockAgent())
        result = agent.run("test")
        assert PII_SAMPLES["email"] not in result[0]
        assert result[1] == "clean"


class TestAgentGPTAnalysisGovernance:
    """Test analysis governance."""

    def test_goal_complete_governs_summary(self):
        """Test goal complete governs summary."""
        goal_manager = TorkAgentGPTGoal()
        goal_manager.set_goal("Test goal")
        completed = goal_manager.complete_goal(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in completed["summary"]

    def test_browser_extract_governs_text(self):
        """Test browser extract governs text."""
        browser = TorkAgentGPTBrowser()
        # Without actual browser, it returns empty string
        result = browser.extract_text()
        assert isinstance(result, str)


class TestAgentGPTActionGovernance:
    """Test action governance."""

    def test_agent_add_task(self):
        """Test agent add_task governs task."""
        class MockAgent:
            tasks = []

            def add_task(self, task):
                self.tasks.append(task)

            def run(self, goal, **kwargs):
                return goal

        mock_agent = MockAgent()
        agent = TorkAgentGPTAgent(mock_agent)
        agent.add_task(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in mock_agent.tasks[0]

    def test_task_add_subtask(self):
        """Test task add_subtask governs description."""
        task = TorkAgentGPTTask()
        parent = task.create("Parent task")
        subtask = task.add_subtask(parent["id"], PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in subtask["description"]
