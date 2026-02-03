"""
Tests for BabyAGI adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Task governance
- Execution governance
- Context governance
- Objective governance
- Task list governance
"""

import pytest
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.babyagi import (
    TorkBabyAGIAgent,
    TorkBabyAGITaskManager,
    TorkBabyAGIMemory,
    governed_task,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestBabyAGIImportInstantiation:
    """Test import and instantiation of BabyAGI adapter."""

    def test_import_agent(self):
        """Test TorkBabyAGIAgent can be imported."""
        assert TorkBabyAGIAgent is not None

    def test_import_task_manager(self):
        """Test TorkBabyAGITaskManager can be imported."""
        assert TorkBabyAGITaskManager is not None

    def test_import_memory(self):
        """Test TorkBabyAGIMemory can be imported."""
        assert TorkBabyAGIMemory is not None

    def test_instantiate_agent_default(self):
        """Test agent instantiation with defaults."""
        agent = TorkBabyAGIAgent()
        assert agent is not None
        assert agent.tork is not None
        assert agent.receipts == []

    def test_instantiate_task_manager_default(self):
        """Test task manager instantiation with defaults."""
        tm = TorkBabyAGITaskManager()
        assert tm is not None
        assert tm.tork is not None


class TestBabyAGIConfiguration:
    """Test configuration of BabyAGI adapter."""

    def test_agent_with_tork_instance(self, tork_instance):
        """Test agent with existing Tork instance."""
        agent = TorkBabyAGIAgent(tork=tork_instance)
        assert agent.tork is tork_instance

    def test_task_manager_with_tork_instance(self, tork_instance):
        """Test task manager with existing Tork instance."""
        tm = TorkBabyAGITaskManager(tork=tork_instance)
        assert tm.tork is tork_instance

    def test_memory_with_tork_instance(self, tork_instance):
        """Test memory with existing Tork instance."""
        memory = TorkBabyAGIMemory(tork=tork_instance)
        assert memory.tork is tork_instance

    def test_agent_with_api_key(self):
        """Test agent with API key."""
        agent = TorkBabyAGIAgent(api_key="test-key")
        assert agent.tork is not None


class TestBabyAGIPIIDetection:
    """Test PII detection and redaction in BabyAGI adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        agent = TorkBabyAGIAgent()
        result = agent.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        agent = TorkBabyAGIAgent()
        result = agent.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        agent = TorkBabyAGIAgent()
        result = agent.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        agent = TorkBabyAGIAgent()
        result = agent.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        agent = TorkBabyAGIAgent()
        clean_text = "Research AI technology"
        result = agent.govern(clean_text)
        assert result == clean_text


class TestBabyAGIErrorHandling:
    """Test error handling in BabyAGI adapter."""

    def test_agent_empty_string(self):
        """Test agent handles empty string."""
        agent = TorkBabyAGIAgent()
        result = agent.govern("")
        assert result == ""

    def test_agent_whitespace(self):
        """Test agent handles whitespace."""
        agent = TorkBabyAGIAgent()
        result = agent.govern("   ")
        assert result == "   "

    def test_task_manager_empty_string(self):
        """Test task manager handles empty string."""
        tm = TorkBabyAGITaskManager()
        result = tm.govern("")
        assert result == ""

    def test_agent_empty_receipts(self):
        """Test agent starts with empty receipts."""
        agent = TorkBabyAGIAgent()
        assert agent.get_receipts() == []


class TestBabyAGIComplianceReceipts:
    """Test compliance receipt generation in BabyAGI adapter."""

    def test_agent_run_generates_receipt(self):
        """Test agent run generates receipt."""
        class MockAgent:
            def run(self, objective=None, **kwargs):
                return f"Completed: {objective}"

        agent = TorkBabyAGIAgent(MockAgent())
        agent.run(objective="Test objective")
        assert len(agent.receipts) >= 1
        assert agent.receipts[0]["type"] == "agent_objective"
        assert "receipt_id" in agent.receipts[0]

    def test_task_manager_get_receipts(self):
        """Test task manager get_receipts method."""
        tm = TorkBabyAGITaskManager()
        receipts = tm.get_receipts()
        assert isinstance(receipts, list)


class TestBabyAGITaskGovernance:
    """Test task governance."""

    def test_task_manager_create_task(self):
        """Test task manager create_task governs description."""
        tm = TorkBabyAGITaskManager()
        task = tm.create_task(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in task["description"]

    def test_task_manager_create_receipt(self):
        """Test task manager create generates receipt."""
        tm = TorkBabyAGITaskManager()
        tm.create_task("Test task")
        assert len(tm.receipts) >= 1
        assert tm.receipts[0]["type"] == "task_create"

    def test_task_manager_complete_task(self):
        """Test task manager complete_task governs result."""
        tm = TorkBabyAGITaskManager()
        task = tm.create_task("Test task")
        completed = tm.complete_task(task["id"], PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in completed["result"]


class TestBabyAGIExecutionGovernance:
    """Test execution governance."""

    def test_agent_run_governs_objective(self):
        """Test agent run governs objective input."""
        class MockAgent:
            def run(self, objective=None, **kwargs):
                return objective

        agent = TorkBabyAGIAgent(MockAgent())
        result = agent.run(objective=PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_agent_run_governs_output(self):
        """Test agent run governs output."""
        class MockAgent:
            def run(self, objective=None, **kwargs):
                return PII_MESSAGES["phone_message"]

        agent = TorkBabyAGIAgent(MockAgent())
        result = agent.run(objective="test")
        assert PII_SAMPLES["phone_us"] not in result

    def test_governed_task_decorator(self):
        """Test governed_task decorator."""
        @governed_task()
        def research(query: str) -> str:
            return f"Results: {query}"

        result = research("test query")
        assert result == "Results: test query"


class TestBabyAGIContextGovernance:
    """Test context/memory governance."""

    def test_memory_add_memory(self):
        """Test memory add_memory governs content."""
        memory = TorkBabyAGIMemory()
        mem = memory.add_memory(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in mem["content"]

    def test_memory_add_generates_receipt(self):
        """Test memory add generates receipt."""
        memory = TorkBabyAGIMemory()
        memory.add_memory("Test content")
        assert len(memory.receipts) >= 1
        assert memory.receipts[0]["type"] == "memory_add"


class TestBabyAGIObjectiveGovernance:
    """Test objective governance."""

    def test_agent_set_objective(self):
        """Test agent set_objective governs objective."""
        class MockAgent:
            objective = None

            def set_objective(self, obj):
                self.objective = obj

            def run(self, objective=None, **kwargs):
                return objective

        mock_agent = MockAgent()
        agent = TorkBabyAGIAgent(mock_agent)
        agent.set_objective(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in mock_agent.objective

    def test_govern_objective_alias(self):
        """Test govern_objective is alias for govern."""
        agent = TorkBabyAGIAgent()
        result1 = agent.govern("test")
        result2 = agent.govern_objective("test")
        assert result1 == result2


class TestBabyAGITaskListGovernance:
    """Test task list governance."""

    def test_task_manager_get_tasks(self):
        """Test task manager get_tasks returns governed tasks."""
        tm = TorkBabyAGITaskManager()
        tm.create_task(PII_MESSAGES["email_message"])
        tm.create_task("Clean task")
        tasks = tm.get_tasks()
        assert len(tasks) == 2
        assert PII_SAMPLES["email"] not in tasks[0]["description"]

    def test_task_manager_prioritize(self):
        """Test task manager prioritize_tasks governs objective."""
        tm = TorkBabyAGITaskManager()
        tm.create_task("Task 1", priority=1)
        tm.create_task("Task 2", priority=2)
        prioritized = tm.prioritize_tasks(PII_MESSAGES["phone_message"])
        assert len(tm.receipts) >= 3  # 2 creates + 1 prioritize
