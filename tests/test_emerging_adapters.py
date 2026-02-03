"""
Tests for emerging AI framework adapters.

Tests DSPy, Instructor, Guidance, LMQL, Outlines, Marvin,
SuperAGI, MetaGPT, BabyAGI, AgentGPT, Flowise, and Langflow adapters.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
import asyncio

from tork_governance.core import Tork, GovernanceAction


class TestDSPyAdapter:
    """Tests for Stanford DSPy adapter."""

    def test_module_init(self):
        """Test TorkDSPyModule initialization."""
        from tork_governance.adapters.dspy import TorkDSPyModule

        mock_module = MagicMock()
        governed = TorkDSPyModule(mock_module)
        assert governed.module == mock_module
        assert governed.tork is not None

    def test_module_forward(self):
        """Test governed forward pass."""
        from tork_governance.adapters.dspy import TorkDSPyModule

        mock_module = MagicMock()
        mock_module.forward.return_value = MagicMock(answer="Contact: admin@test.com")

        governed = TorkDSPyModule(mock_module)
        result = governed.forward(question="Find user@example.com")

        # Input should be governed
        call_args = mock_module.forward.call_args[1]
        assert "[EMAIL_REDACTED]" in call_args["question"]

    def test_signature_govern_input(self):
        """Test signature input governance."""
        from tork_governance.adapters.dspy import TorkDSPySignature

        sig = TorkDSPySignature("question -> answer")
        governed = sig.govern_input(question="Email: test@email.com")

        assert "[EMAIL_REDACTED]" in governed["question"]

    def test_governed_predict_decorator(self):
        """Test governed_predict decorator."""
        from tork_governance.adapters.dspy import governed_predict

        @governed_predict()
        def my_predictor(text: str) -> str:
            return f"Processed: {text}"

        result = my_predictor(text="user@domain.com")
        assert "[EMAIL_REDACTED]" in result


class TestInstructorAdapter:
    """Tests for Instructor adapter."""

    def test_client_init(self):
        """Test TorkInstructorClient initialization."""
        from tork_governance.adapters.instructor import TorkInstructorClient

        mock_client = MagicMock()
        governed = TorkInstructorClient(mock_client)
        assert governed.client == mock_client

    def test_govern_messages(self):
        """Test message governance."""
        from tork_governance.adapters.instructor import TorkInstructorClient

        mock_client = MagicMock()
        governed = TorkInstructorClient(mock_client)

        messages = [{"role": "user", "content": "Email: test@example.com"}]
        governed_messages = governed._govern_messages(messages)

        assert "[EMAIL_REDACTED]" in governed_messages[0]["content"]

    def test_patch_init(self):
        """Test TorkInstructorPatch initialization."""
        from tork_governance.adapters.instructor import TorkInstructorPatch

        patch = TorkInstructorPatch()
        assert patch.tork is not None

    def test_governed_response_decorator(self):
        """Test governed_response decorator."""
        from tork_governance.adapters.instructor import governed_response

        @governed_response()
        def get_data(text: str) -> str:
            return text.upper()

        result = get_data("user@email.com")
        assert "[EMAIL_REDACTED]" in result


class TestGuidanceAdapter:
    """Tests for Microsoft Guidance adapter."""

    def test_program_init(self):
        """Test TorkGuidanceProgram initialization."""
        from tork_governance.adapters.guidance import TorkGuidanceProgram

        mock_program = MagicMock()
        governed = TorkGuidanceProgram(mock_program)
        assert governed.program == mock_program

    def test_program_call(self):
        """Test governed program execution."""
        from tork_governance.adapters.guidance import TorkGuidanceProgram

        mock_program = MagicMock()
        mock_program.return_value = {"output": "result"}

        governed = TorkGuidanceProgram(mock_program)
        result = governed(text="user@example.com")

        # Input should be governed
        call_args = mock_program.call_args[1]
        assert "[EMAIL_REDACTED]" in call_args["text"]

    def test_gen_init(self):
        """Test TorkGuidanceGen initialization."""
        from tork_governance.adapters.guidance import TorkGuidanceGen

        gen = TorkGuidanceGen()
        assert gen.tork is not None

    def test_governed_block_decorator(self):
        """Test governed_block decorator."""
        from tork_governance.adapters.guidance import governed_block

        @governed_block()
        def my_block(text: str) -> str:
            return f"Output: {text}"

        result = my_block(text="test@email.com")
        assert "[EMAIL_REDACTED]" in result


class TestLMQLAdapter:
    """Tests for LMQL adapter."""

    def test_query_init(self):
        """Test TorkLMQLQuery initialization."""
        from tork_governance.adapters.lmql import TorkLMQLQuery

        mock_query = MagicMock()
        governed = TorkLMQLQuery(mock_query)
        assert governed.query == mock_query

    def test_query_call(self):
        """Test governed query execution."""
        from tork_governance.adapters.lmql import TorkLMQLQuery

        mock_query = MagicMock()
        mock_query.return_value = "Response with admin@test.com"

        governed = TorkLMQLQuery(mock_query)
        result = governed(input="user@example.com")

        # Input should be governed
        call_args = mock_query.call_args[1]
        assert "[EMAIL_REDACTED]" in call_args["input"]

        # Output should be governed
        assert "[EMAIL_REDACTED]" in result

    def test_runtime_init(self):
        """Test TorkLMQLRuntime initialization."""
        from tork_governance.adapters.lmql import TorkLMQLRuntime

        runtime = TorkLMQLRuntime()
        assert runtime.tork is not None

    def test_governed_query_decorator(self):
        """Test governed_query decorator."""
        from tork_governance.adapters.lmql import governed_query

        @governed_query()
        def my_query(text: str) -> str:
            return f"Result: {text}"

        result = my_query(text="user@email.com")
        assert "[EMAIL_REDACTED]" in result


class TestOutlinesAdapter:
    """Tests for Outlines adapter."""

    def test_generator_init(self):
        """Test TorkOutlinesGenerator initialization."""
        from tork_governance.adapters.outlines import TorkOutlinesGenerator

        mock_gen = MagicMock()
        governed = TorkOutlinesGenerator(mock_gen)
        assert governed.generator == mock_gen

    def test_generator_call(self):
        """Test governed generation."""
        from tork_governance.adapters.outlines import TorkOutlinesGenerator

        mock_gen = MagicMock()
        mock_gen.return_value = "Generated: admin@test.com"

        governed = TorkOutlinesGenerator(mock_gen)
        result = governed("Prompt: user@example.com")

        # Output should be governed
        assert "[EMAIL_REDACTED]" in result

    def test_model_init(self):
        """Test TorkOutlinesModel initialization."""
        from tork_governance.adapters.outlines import TorkOutlinesModel

        mock_model = MagicMock()
        governed = TorkOutlinesModel(mock_model)
        assert governed.model == mock_model

    def test_governed_generate_decorator(self):
        """Test governed_generate decorator."""
        from tork_governance.adapters.outlines import governed_generate

        @governed_generate()
        def generate(prompt: str) -> str:
            return f"Generated: {prompt}"

        result = generate("user@email.com")
        assert "[EMAIL_REDACTED]" in result


class TestMarvinAdapter:
    """Tests for Marvin adapter."""

    def test_ai_init(self):
        """Test TorkMarvinAI initialization."""
        from tork_governance.adapters.marvin import TorkMarvinAI

        ai = TorkMarvinAI()
        assert ai.tork is not None
        assert ai.receipts == []

    def test_governed_fn_decorator(self):
        """Test governed_fn decorator."""
        from tork_governance.adapters.marvin import governed_fn

        @governed_fn()
        def process(text: str) -> str:
            return f"Processed: {text}"

        result = process("user@email.com")
        assert "[EMAIL_REDACTED]" in result

    def test_governed_classifier_decorator(self):
        """Test governed_classifier decorator."""
        from tork_governance.adapters.marvin import governed_classifier

        @governed_classifier()
        def classify(text: str) -> str:
            return "pii" if "@" in text else "safe"

        # The input is governed before classification
        result = classify("user@example.com")
        # Classification happens on redacted text


class TestSuperAGIAdapter:
    """Tests for SuperAGI adapter."""

    def test_agent_init(self):
        """Test TorkSuperAGIAgent initialization."""
        from tork_governance.adapters.superagi import TorkSuperAGIAgent

        mock_agent = MagicMock()
        governed = TorkSuperAGIAgent(mock_agent)
        assert governed.agent == mock_agent

    def test_agent_run(self):
        """Test governed agent run."""
        from tork_governance.adapters.superagi import TorkSuperAGIAgent

        mock_agent = MagicMock()
        mock_agent.run.return_value = "Found: admin@test.com"

        governed = TorkSuperAGIAgent(mock_agent)
        result = governed.run("Find user@example.com")

        # Input governed
        call_args = mock_agent.run.call_args[0]
        assert "[EMAIL_REDACTED]" in call_args[0]

        # Output governed
        assert "[EMAIL_REDACTED]" in result

    def test_tool_wrapper(self):
        """Test TorkSuperAGITool wrapper."""
        from tork_governance.adapters.superagi import TorkSuperAGITool

        wrapper = TorkSuperAGITool()

        @wrapper.governed_tool
        def search(query: str) -> str:
            return f"Results: {query}"

        result = search(query="user@email.com")
        assert "[EMAIL_REDACTED]" in result

    def test_workflow_init(self):
        """Test TorkSuperAGIWorkflow initialization."""
        from tork_governance.adapters.superagi import TorkSuperAGIWorkflow

        mock_workflow = MagicMock()
        governed = TorkSuperAGIWorkflow(mock_workflow)
        assert governed.workflow == mock_workflow


class TestMetaGPTAdapter:
    """Tests for MetaGPT adapter."""

    def test_role_init(self):
        """Test TorkMetaGPTRole initialization."""
        from tork_governance.adapters.metagpt import TorkMetaGPTRole

        mock_role = MagicMock()
        governed = TorkMetaGPTRole(mock_role)
        assert governed.role == mock_role

    @pytest.mark.asyncio
    async def test_role_run(self):
        """Test governed role run."""
        from tork_governance.adapters.metagpt import TorkMetaGPTRole

        mock_role = MagicMock()
        mock_role.run = AsyncMock(return_value="Code for admin@test.com")

        governed = TorkMetaGPTRole(mock_role)
        result = await governed.run("Implement for user@example.com")

        # Output governed
        assert "[EMAIL_REDACTED]" in result

    def test_team_init(self):
        """Test TorkMetaGPTTeam initialization."""
        from tork_governance.adapters.metagpt import TorkMetaGPTTeam

        mock_team = MagicMock()
        governed = TorkMetaGPTTeam(mock_team)
        assert governed.team == mock_team

    def test_action_init(self):
        """Test TorkMetaGPTAction initialization."""
        from tork_governance.adapters.metagpt import TorkMetaGPTAction

        mock_action = MagicMock()
        governed = TorkMetaGPTAction(mock_action)
        assert governed.action == mock_action


class TestBabyAGIAdapter:
    """Tests for BabyAGI adapter."""

    def test_agent_init(self):
        """Test TorkBabyAGIAgent initialization."""
        from tork_governance.adapters.babyagi import TorkBabyAGIAgent

        mock_agent = MagicMock()
        governed = TorkBabyAGIAgent(mock_agent)
        assert governed.agent == mock_agent

    def test_agent_run(self):
        """Test governed agent run."""
        from tork_governance.adapters.babyagi import TorkBabyAGIAgent

        mock_agent = MagicMock()
        mock_agent.run.return_value = "Found: admin@test.com"

        governed = TorkBabyAGIAgent(mock_agent)
        result = governed.run("Find user@example.com")

        assert "[EMAIL_REDACTED]" in result

    def test_task_manager_init(self):
        """Test TorkBabyAGITaskManager initialization."""
        from tork_governance.adapters.babyagi import TorkBabyAGITaskManager

        manager = TorkBabyAGITaskManager()
        assert manager.tork is not None
        assert manager.tasks == []

    def test_task_manager_create(self):
        """Test task creation with governance."""
        from tork_governance.adapters.babyagi import TorkBabyAGITaskManager

        manager = TorkBabyAGITaskManager()
        task = manager.create_task("Research user@example.com")

        assert "[EMAIL_REDACTED]" in task["description"]
        assert task["status"] == "pending"

    def test_governed_task_decorator(self):
        """Test governed_task decorator."""
        from tork_governance.adapters.babyagi import governed_task

        @governed_task()
        def research(query: str) -> str:
            return f"Found: {query}"

        result = research(query="user@email.com")
        assert "[EMAIL_REDACTED]" in result


class TestAgentGPTAdapter:
    """Tests for AgentGPT adapter."""

    def test_agent_init(self):
        """Test TorkAgentGPTAgent initialization."""
        from tork_governance.adapters.agentgpt import TorkAgentGPTAgent

        mock_agent = MagicMock()
        governed = TorkAgentGPTAgent(mock_agent)
        assert governed.agent == mock_agent

    def test_agent_run(self):
        """Test governed agent run."""
        from tork_governance.adapters.agentgpt import TorkAgentGPTAgent

        mock_agent = MagicMock()
        mock_agent.run.return_value = "Found: admin@test.com"

        governed = TorkAgentGPTAgent(mock_agent)
        result = governed.run("Find user@example.com")

        assert "[EMAIL_REDACTED]" in result

    def test_task_init(self):
        """Test TorkAgentGPTTask initialization."""
        from tork_governance.adapters.agentgpt import TorkAgentGPTTask

        task = TorkAgentGPTTask()
        assert task.tork is not None
        assert task.tasks == []

    def test_task_create(self):
        """Test task creation."""
        from tork_governance.adapters.agentgpt import TorkAgentGPTTask

        task_manager = TorkAgentGPTTask()
        task = task_manager.create("Research user@example.com")

        assert "[EMAIL_REDACTED]" in task["description"]

    def test_goal_init(self):
        """Test TorkAgentGPTGoal initialization."""
        from tork_governance.adapters.agentgpt import TorkAgentGPTGoal

        goal = TorkAgentGPTGoal()
        assert goal.tork is not None

    def test_goal_set(self):
        """Test goal setting."""
        from tork_governance.adapters.agentgpt import TorkAgentGPTGoal

        manager = TorkAgentGPTGoal()
        goal = manager.set_goal("Find user@example.com")

        assert "[EMAIL_REDACTED]" in goal["description"]
        assert goal["status"] == "active"


class TestFlowiseAdapter:
    """Tests for Flowise adapter."""

    def test_node_init(self):
        """Test TorkFlowiseNode initialization."""
        from tork_governance.adapters.flowise import TorkFlowiseNode

        node = TorkFlowiseNode(name="TestNode")
        assert node.name == "TestNode"
        assert node.tork is not None

    def test_node_process(self):
        """Test node processing."""
        from tork_governance.adapters.flowise import TorkFlowiseNode

        node = TorkFlowiseNode(name="TestNode")
        result = node.process({"text": "user@example.com"})

        assert "[EMAIL_REDACTED]" in result["text"]

    def test_flow_init(self):
        """Test TorkFlowiseFlow initialization."""
        from tork_governance.adapters.flowise import TorkFlowiseFlow

        mock_flow = MagicMock()
        governed = TorkFlowiseFlow(mock_flow)
        assert governed.flow == mock_flow

    def test_flow_execute(self):
        """Test flow execution."""
        from tork_governance.adapters.flowise import TorkFlowiseFlow

        mock_flow = MagicMock()
        mock_flow.execute.return_value = {"output": "admin@test.com"}

        governed = TorkFlowiseFlow(mock_flow)
        result = governed.execute({"input": "user@example.com"})

        assert "[EMAIL_REDACTED]" in result["output"]

    def test_api_init(self):
        """Test TorkFlowiseAPI initialization."""
        from tork_governance.adapters.flowise import TorkFlowiseAPI

        api = TorkFlowiseAPI(base_url="http://localhost:3000")
        assert api.base_url == "http://localhost:3000"


class TestLangflowAdapter:
    """Tests for Langflow adapter."""

    def test_component_init(self):
        """Test TorkLangflowComponent initialization."""
        from tork_governance.adapters.langflow import TorkLangflowComponent

        mock_component = MagicMock()
        governed = TorkLangflowComponent(mock_component)
        assert governed.component == mock_component

    def test_component_run(self):
        """Test component run."""
        from tork_governance.adapters.langflow import TorkLangflowComponent

        mock_component = MagicMock()
        mock_component.run.return_value = "Output: admin@test.com"

        governed = TorkLangflowComponent(mock_component)
        result = governed.run(text="user@example.com")

        assert "[EMAIL_REDACTED]" in result

    def test_flow_init(self):
        """Test TorkLangflowFlow initialization."""
        from tork_governance.adapters.langflow import TorkLangflowFlow

        mock_flow = MagicMock()
        governed = TorkLangflowFlow(mock_flow)
        assert governed.flow == mock_flow

    def test_flow_run(self):
        """Test flow run."""
        from tork_governance.adapters.langflow import TorkLangflowFlow

        mock_flow = MagicMock()
        mock_flow.run.return_value = {"output": "admin@test.com"}

        governed = TorkLangflowFlow(mock_flow)
        result = governed.run({"input": "user@example.com"})

        assert "[EMAIL_REDACTED]" in result["output"]

    def test_api_init(self):
        """Test TorkLangflowAPI initialization."""
        from tork_governance.adapters.langflow import TorkLangflowAPI

        api = TorkLangflowAPI(base_url="http://localhost:7860")
        assert api.base_url == "http://localhost:7860"


class TestEmergingAdapterExports:
    """Test that all emerging adapters are properly exported."""

    def test_all_adapters_importable(self):
        """Test all adapters can be imported from adapters module."""
        from tork_governance.adapters import (
            # DSPy
            TorkDSPyModule,
            TorkDSPySignature,
            governed_predict,
            # Instructor
            TorkInstructorClient,
            TorkInstructorPatch,
            governed_response,
            # Guidance
            TorkGuidanceProgram,
            TorkGuidanceGen,
            governed_block,
            # LMQL
            TorkLMQLQuery,
            TorkLMQLRuntime,
            governed_query,
            # Outlines
            TorkOutlinesGenerator,
            TorkOutlinesModel,
            governed_generate,
            # Marvin
            TorkMarvinAI,
            governed_fn,
            governed_classifier,
            # SuperAGI
            TorkSuperAGIAgent,
            TorkSuperAGITool,
            TorkSuperAGIWorkflow,
            # MetaGPT
            TorkMetaGPTRole,
            TorkMetaGPTTeam,
            TorkMetaGPTAction,
            # BabyAGI
            TorkBabyAGIAgent,
            TorkBabyAGITaskManager,
            governed_task,
            # AgentGPT
            TorkAgentGPTAgent,
            TorkAgentGPTTask,
            TorkAgentGPTGoal,
            # Flowise
            TorkFlowiseNode,
            TorkFlowiseFlow,
            TorkFlowiseAPI,
            # Langflow
            TorkLangflowComponent,
            TorkLangflowFlow,
            TorkLangflowAPI,
        )

        # All imports should succeed
        assert TorkDSPyModule is not None
        assert TorkInstructorClient is not None
        assert TorkGuidanceProgram is not None
        assert TorkLMQLQuery is not None
        assert TorkOutlinesGenerator is not None
        assert TorkMarvinAI is not None
        assert TorkSuperAGIAgent is not None
        assert TorkMetaGPTRole is not None
        assert TorkBabyAGIAgent is not None
        assert TorkAgentGPTAgent is not None
        assert TorkFlowiseNode is not None
        assert TorkLangflowComponent is not None
