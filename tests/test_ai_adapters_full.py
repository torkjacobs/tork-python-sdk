"""
Comprehensive test suite for ALL AI framework adapters.
Tests import, functionality (PII detection/redaction), and simulated integration.
"""

import pytest
import json
from datetime import datetime
from typing import Dict, List, Any

# ============================================================
# TEST DATA
# ============================================================

TEST_INPUTS = {
    "clean": "Hello, how can I help you today?",
    "ssn": "My SSN is 123-45-6789, please process my request.",
    "email": "Contact me at john.doe@example.com for more info.",
    "phone": "Call me at 555-123-4567 tomorrow.",
    "credit_card": "My card number is 4111-1111-1111-1111",
    "mixed": "I'm John, SSN 123-45-6789, email john@test.com, phone 555-999-8888",
}

EXPECTED_REDACTIONS = {
    "ssn": "[SSN_REDACTED]",
    "email": "[EMAIL_REDACTED]",
    "phone": "[PHONE_REDACTED]",
    "credit_card": "[CARD_REDACTED]",
}


# ============================================================
# LANGCHAIN ADAPTER TESTS
# ============================================================

class TestLangChainAdapter:
    """Full test suite for LangChain adapter."""

    def test_import_callback_handler(self):
        """Test TorkCallbackHandler import."""
        from tork_governance.adapters.langchain import TorkCallbackHandler
        assert TorkCallbackHandler is not None

    def test_import_governed_chain(self):
        """Test TorkGovernedChain import."""
        from tork_governance.adapters.langchain import TorkGovernedChain
        assert TorkGovernedChain is not None

    def test_import_create_governed_chain(self):
        """Test create_governed_chain import."""
        from tork_governance.adapters.langchain import create_governed_chain
        assert create_governed_chain is not None

    def test_callback_handler_instantiation(self):
        """Test TorkCallbackHandler can be instantiated."""
        from tork_governance.adapters.langchain import TorkCallbackHandler
        handler = TorkCallbackHandler()
        assert handler is not None

    def test_callback_handler_ssn_redaction(self):
        """Test SSN is redacted in prompts."""
        from tork_governance.adapters.langchain import TorkCallbackHandler
        handler = TorkCallbackHandler()
        prompts = [TEST_INPUTS["ssn"]]
        handler.on_llm_start({}, prompts)
        assert "[SSN_REDACTED]" in prompts[0]

    def test_callback_handler_email_redaction(self):
        """Test email is redacted in prompts."""
        from tork_governance.adapters.langchain import TorkCallbackHandler
        handler = TorkCallbackHandler()
        prompts = [TEST_INPUTS["email"]]
        handler.on_llm_start({}, prompts)
        assert "[EMAIL_REDACTED]" in prompts[0]

    def test_callback_handler_clean_passthrough(self):
        """Test clean input passes through unchanged."""
        from tork_governance.adapters.langchain import TorkCallbackHandler
        handler = TorkCallbackHandler()
        prompts = [TEST_INPUTS["clean"]]
        original = prompts[0]
        handler.on_llm_start({}, prompts)
        assert prompts[0] == original

    def test_governed_chain_instantiation(self):
        """Test TorkGovernedChain can be instantiated."""
        from tork_governance.adapters.langchain import TorkGovernedChain
        chain = TorkGovernedChain()
        assert chain is not None

    def test_governed_chain_govern_input(self):
        """Test TorkGovernedChain governs input."""
        from tork_governance.adapters.langchain import TorkGovernedChain
        chain = TorkGovernedChain()
        result = chain.govern_input(TEST_INPUTS["ssn"])
        assert "[SSN_REDACTED]" in result


# ============================================================
# CREWAI ADAPTER TESTS
# ============================================================

class TestCrewAIAdapter:
    """Full test suite for CrewAI adapter."""

    def test_import_middleware(self):
        """Test TorkCrewAIMiddleware import."""
        from tork_governance.adapters.crewai import TorkCrewAIMiddleware
        assert TorkCrewAIMiddleware is not None

    def test_import_governed_agent(self):
        """Test GovernedAgent import."""
        from tork_governance.adapters.crewai import GovernedAgent
        assert GovernedAgent is not None

    def test_import_governed_crew(self):
        """Test GovernedCrew import."""
        from tork_governance.adapters.crewai import GovernedCrew
        assert GovernedCrew is not None

    def test_middleware_instantiation(self):
        """Test middleware can be instantiated."""
        from tork_governance.adapters.crewai import TorkCrewAIMiddleware
        middleware = TorkCrewAIMiddleware()
        assert middleware is not None

    def test_middleware_ssn_redaction(self):
        """Test SSN is redacted."""
        from tork_governance.adapters.crewai import TorkCrewAIMiddleware
        middleware = TorkCrewAIMiddleware()
        result = middleware.govern_input(TEST_INPUTS["ssn"])
        assert "[SSN_REDACTED]" in result

    def test_middleware_email_redaction(self):
        """Test email is redacted."""
        from tork_governance.adapters.crewai import TorkCrewAIMiddleware
        middleware = TorkCrewAIMiddleware()
        result = middleware.govern_input(TEST_INPUTS["email"])
        assert "[EMAIL_REDACTED]" in result

    def test_middleware_clean_passthrough(self):
        """Test clean input passes through."""
        from tork_governance.adapters.crewai import TorkCrewAIMiddleware
        middleware = TorkCrewAIMiddleware()
        result = middleware.govern_input(TEST_INPUTS["clean"])
        assert result == TEST_INPUTS["clean"]


# ============================================================
# AUTOGEN ADAPTER TESTS
# ============================================================

class TestAutoGenAdapter:
    """Full test suite for AutoGen adapter."""

    def test_import_middleware(self):
        """Test TorkAutoGenMiddleware import."""
        from tork_governance.adapters.autogen import TorkAutoGenMiddleware
        assert TorkAutoGenMiddleware is not None

    def test_import_governed_agent(self):
        """Test GovernedAutoGenAgent import."""
        from tork_governance.adapters.autogen import GovernedAutoGenAgent
        assert GovernedAutoGenAgent is not None

    def test_middleware_instantiation(self):
        """Test middleware can be instantiated."""
        from tork_governance.adapters.autogen import TorkAutoGenMiddleware
        middleware = TorkAutoGenMiddleware()
        assert middleware is not None

    def test_middleware_ssn_redaction(self):
        """Test SSN is redacted."""
        from tork_governance.adapters.autogen import TorkAutoGenMiddleware
        middleware = TorkAutoGenMiddleware()
        result = middleware.govern_message(TEST_INPUTS["ssn"])
        assert "[SSN_REDACTED]" in result

    def test_middleware_email_redaction(self):
        """Test email is redacted."""
        from tork_governance.adapters.autogen import TorkAutoGenMiddleware
        middleware = TorkAutoGenMiddleware()
        result = middleware.govern_message(TEST_INPUTS["email"])
        assert "[EMAIL_REDACTED]" in result


# ============================================================
# OPENAI AGENTS ADAPTER TESTS
# ============================================================

class TestOpenAIAgentsAdapter:
    """Full test suite for OpenAI Agents adapter."""

    def test_import_middleware(self):
        """Test TorkOpenAIAgentsMiddleware import."""
        from tork_governance.adapters.openai_agents import TorkOpenAIAgentsMiddleware
        assert TorkOpenAIAgentsMiddleware is not None

    def test_import_governed_agent(self):
        """Test GovernedOpenAIAgent import."""
        from tork_governance.adapters.openai_agents import GovernedOpenAIAgent
        assert GovernedOpenAIAgent is not None

    def test_middleware_instantiation(self):
        """Test middleware can be instantiated."""
        from tork_governance.adapters.openai_agents import TorkOpenAIAgentsMiddleware
        middleware = TorkOpenAIAgentsMiddleware()
        assert middleware is not None


# ============================================================
# MCP ADAPTER TESTS
# ============================================================

class TestMCPAdapter:
    """Full test suite for MCP adapter."""

    def test_import_tool_wrapper(self):
        """Test TorkMCPToolWrapper import."""
        from tork_governance.adapters.mcp import TorkMCPToolWrapper
        assert TorkMCPToolWrapper is not None

    def test_import_server(self):
        """Test TorkMCPServer import."""
        from tork_governance.adapters.mcp import TorkMCPServer
        assert TorkMCPServer is not None

    def test_import_middleware(self):
        """Test TorkMCPMiddleware import."""
        from tork_governance.adapters.mcp import TorkMCPMiddleware
        assert TorkMCPMiddleware is not None

    def test_tool_wrapper_instantiation(self):
        """Test TorkMCPToolWrapper can be instantiated."""
        from tork_governance.adapters.mcp import TorkMCPToolWrapper
        wrapper = TorkMCPToolWrapper()
        assert wrapper is not None

    def test_tool_wrapper_ssn_redaction(self):
        """Test SSN is redacted in tool calls."""
        from tork_governance.adapters.mcp import TorkMCPToolWrapper
        wrapper = TorkMCPToolWrapper()
        result = wrapper.govern_tool_input({"text": TEST_INPUTS["ssn"]})
        assert "[SSN_REDACTED]" in str(result)


# ============================================================
# LLAMAINDEX ADAPTER TESTS
# ============================================================

class TestLlamaIndexAdapter:
    """Full test suite for LlamaIndex adapter."""

    def test_import_callback(self):
        """Test TorkLlamaIndexCallback import."""
        from tork_governance.adapters.llamaindex import TorkLlamaIndexCallback
        assert TorkLlamaIndexCallback is not None

    def test_import_query_engine(self):
        """Test TorkQueryEngine import."""
        from tork_governance.adapters.llamaindex import TorkQueryEngine
        assert TorkQueryEngine is not None

    def test_import_retriever(self):
        """Test TorkRetriever import."""
        from tork_governance.adapters.llamaindex import TorkRetriever
        assert TorkRetriever is not None

    def test_callback_instantiation(self):
        """Test callback can be instantiated."""
        from tork_governance.adapters.llamaindex import TorkLlamaIndexCallback
        callback = TorkLlamaIndexCallback()
        assert callback is not None

    def test_callback_query_governance(self):
        """Test query is governed."""
        from tork_governance.adapters.llamaindex import TorkLlamaIndexCallback
        callback = TorkLlamaIndexCallback()
        result = callback.govern_query(TEST_INPUTS["ssn"])
        assert "[SSN_REDACTED]" in result


# ============================================================
# SEMANTIC KERNEL ADAPTER TESTS
# ============================================================

class TestSemanticKernelAdapter:
    """Full test suite for Semantic Kernel adapter."""

    def test_import_filter(self):
        """Test TorkSKFilter import."""
        from tork_governance.adapters.semantic_kernel import TorkSKFilter
        assert TorkSKFilter is not None

    def test_import_plugin(self):
        """Test TorkSKPlugin import."""
        from tork_governance.adapters.semantic_kernel import TorkSKPlugin
        assert TorkSKPlugin is not None

    def test_import_prompt_filter(self):
        """Test TorkSKPromptFilter import."""
        from tork_governance.adapters.semantic_kernel import TorkSKPromptFilter
        assert TorkSKPromptFilter is not None

    def test_filter_instantiation(self):
        """Test filter can be instantiated."""
        from tork_governance.adapters.semantic_kernel import TorkSKFilter
        filter_obj = TorkSKFilter()
        assert filter_obj is not None


# ============================================================
# HAYSTACK ADAPTER TESTS
# ============================================================

class TestHaystackAdapter:
    """Full test suite for Haystack adapter."""

    def test_import_component(self):
        """Test TorkHaystackComponent import."""
        from tork_governance.adapters.haystack import TorkHaystackComponent
        assert TorkHaystackComponent is not None

    def test_import_pipeline(self):
        """Test TorkHaystackPipeline import."""
        from tork_governance.adapters.haystack import TorkHaystackPipeline
        assert TorkHaystackPipeline is not None

    def test_import_document_processor(self):
        """Test TorkDocumentProcessor import."""
        from tork_governance.adapters.haystack import TorkDocumentProcessor
        assert TorkDocumentProcessor is not None

    def test_component_instantiation(self):
        """Test component can be instantiated."""
        from tork_governance.adapters.haystack import TorkHaystackComponent
        component = TorkHaystackComponent()
        assert component is not None

    def test_component_run(self):
        """Test component run method."""
        from tork_governance.adapters.haystack import TorkHaystackComponent
        component = TorkHaystackComponent()
        result = component.run(query=TEST_INPUTS["ssn"])
        assert "[SSN_REDACTED]" in result.get("governed_query", "")


# ============================================================
# PYDANTIC AI ADAPTER TESTS
# ============================================================

class TestPydanticAIAdapter:
    """Full test suite for Pydantic AI adapter."""

    def test_import_middleware(self):
        """Test TorkPydanticAIMiddleware import."""
        from tork_governance.adapters.pydantic_ai import TorkPydanticAIMiddleware
        assert TorkPydanticAIMiddleware is not None

    def test_import_tool(self):
        """Test TorkPydanticAITool import."""
        from tork_governance.adapters.pydantic_ai import TorkPydanticAITool
        assert TorkPydanticAITool is not None

    def test_import_dependency(self):
        """Test TorkAgentDependency import."""
        from tork_governance.adapters.pydantic_ai import TorkAgentDependency
        assert TorkAgentDependency is not None

    def test_middleware_instantiation(self):
        """Test middleware can be instantiated."""
        from tork_governance.adapters.pydantic_ai import TorkPydanticAIMiddleware
        middleware = TorkPydanticAIMiddleware()
        assert middleware is not None


# ============================================================
# DSPY ADAPTER TESTS
# ============================================================

class TestDSPyAdapter:
    """Full test suite for DSPy adapter."""

    def test_import_module(self):
        """Test TorkDSPyModule import."""
        from tork_governance.adapters.dspy import TorkDSPyModule
        assert TorkDSPyModule is not None

    def test_import_signature(self):
        """Test TorkDSPySignature import."""
        from tork_governance.adapters.dspy import TorkDSPySignature
        assert TorkDSPySignature is not None

    def test_import_decorator(self):
        """Test governed_predict import."""
        from tork_governance.adapters.dspy import governed_predict
        assert governed_predict is not None

    def test_module_instantiation(self):
        """Test module can be instantiated."""
        from tork_governance.adapters.dspy import TorkDSPyModule
        module = TorkDSPyModule()
        assert module is not None


# ============================================================
# INSTRUCTOR ADAPTER TESTS
# ============================================================

class TestInstructorAdapter:
    """Full test suite for Instructor adapter."""

    def test_import_client(self):
        """Test TorkInstructorClient import."""
        from tork_governance.adapters.instructor import TorkInstructorClient
        assert TorkInstructorClient is not None

    def test_import_patch(self):
        """Test TorkInstructorPatch import."""
        from tork_governance.adapters.instructor import TorkInstructorPatch
        assert TorkInstructorPatch is not None

    def test_import_decorator(self):
        """Test governed_response import."""
        from tork_governance.adapters.instructor import governed_response
        assert governed_response is not None

    def test_client_instantiation(self):
        """Test client can be instantiated."""
        from tork_governance.adapters.instructor import TorkInstructorClient
        client = TorkInstructorClient()
        assert client is not None


# ============================================================
# GUIDANCE ADAPTER TESTS
# ============================================================

class TestGuidanceAdapter:
    """Full test suite for Guidance adapter."""

    def test_import_program(self):
        """Test TorkGuidanceProgram import."""
        from tork_governance.adapters.guidance import TorkGuidanceProgram
        assert TorkGuidanceProgram is not None

    def test_import_gen(self):
        """Test TorkGuidanceGen import."""
        from tork_governance.adapters.guidance import TorkGuidanceGen
        assert TorkGuidanceGen is not None

    def test_import_decorator(self):
        """Test governed_block import."""
        from tork_governance.adapters.guidance import governed_block
        assert governed_block is not None

    def test_program_instantiation(self):
        """Test program can be instantiated."""
        from tork_governance.adapters.guidance import TorkGuidanceProgram
        program = TorkGuidanceProgram()
        assert program is not None


# ============================================================
# LMQL ADAPTER TESTS
# ============================================================

class TestLMQLAdapter:
    """Full test suite for LMQL adapter."""

    def test_import_query(self):
        """Test TorkLMQLQuery import."""
        from tork_governance.adapters.lmql import TorkLMQLQuery
        assert TorkLMQLQuery is not None

    def test_import_runtime(self):
        """Test TorkLMQLRuntime import."""
        from tork_governance.adapters.lmql import TorkLMQLRuntime
        assert TorkLMQLRuntime is not None

    def test_import_decorator(self):
        """Test governed_query import."""
        from tork_governance.adapters.lmql import governed_query
        assert governed_query is not None

    def test_query_instantiation(self):
        """Test query can be instantiated."""
        from tork_governance.adapters.lmql import TorkLMQLQuery
        query = TorkLMQLQuery()
        assert query is not None


# ============================================================
# OUTLINES ADAPTER TESTS
# ============================================================

class TestOutlinesAdapter:
    """Full test suite for Outlines adapter."""

    def test_import_generator(self):
        """Test TorkOutlinesGenerator import."""
        from tork_governance.adapters.outlines import TorkOutlinesGenerator
        assert TorkOutlinesGenerator is not None

    def test_import_model(self):
        """Test TorkOutlinesModel import."""
        from tork_governance.adapters.outlines import TorkOutlinesModel
        assert TorkOutlinesModel is not None

    def test_import_decorator(self):
        """Test governed_generate import."""
        from tork_governance.adapters.outlines import governed_generate
        assert governed_generate is not None

    def test_generator_instantiation(self):
        """Test generator can be instantiated."""
        from tork_governance.adapters.outlines import TorkOutlinesGenerator
        generator = TorkOutlinesGenerator()
        assert generator is not None


# ============================================================
# MARVIN ADAPTER TESTS
# ============================================================

class TestMarvinAdapter:
    """Full test suite for Marvin adapter."""

    def test_import_ai(self):
        """Test TorkMarvinAI import."""
        from tork_governance.adapters.marvin import TorkMarvinAI
        assert TorkMarvinAI is not None

    def test_import_fn_decorator(self):
        """Test governed_fn import."""
        from tork_governance.adapters.marvin import governed_fn
        assert governed_fn is not None

    def test_import_classifier_decorator(self):
        """Test governed_classifier import."""
        from tork_governance.adapters.marvin import governed_classifier
        assert governed_classifier is not None

    def test_ai_instantiation(self):
        """Test AI can be instantiated."""
        from tork_governance.adapters.marvin import TorkMarvinAI
        ai = TorkMarvinAI()
        assert ai is not None


# ============================================================
# SUPERAGI ADAPTER TESTS
# ============================================================

class TestSuperAGIAdapter:
    """Full test suite for SuperAGI adapter."""

    def test_import_agent(self):
        """Test TorkSuperAGIAgent import."""
        from tork_governance.adapters.superagi import TorkSuperAGIAgent
        assert TorkSuperAGIAgent is not None

    def test_import_tool(self):
        """Test TorkSuperAGITool import."""
        from tork_governance.adapters.superagi import TorkSuperAGITool
        assert TorkSuperAGITool is not None

    def test_import_workflow(self):
        """Test TorkSuperAGIWorkflow import."""
        from tork_governance.adapters.superagi import TorkSuperAGIWorkflow
        assert TorkSuperAGIWorkflow is not None

    def test_agent_instantiation(self):
        """Test agent can be instantiated."""
        from tork_governance.adapters.superagi import TorkSuperAGIAgent
        agent = TorkSuperAGIAgent()
        assert agent is not None


# ============================================================
# METAGPT ADAPTER TESTS
# ============================================================

class TestMetaGPTAdapter:
    """Full test suite for MetaGPT adapter."""

    def test_import_role(self):
        """Test TorkMetaGPTRole import."""
        from tork_governance.adapters.metagpt import TorkMetaGPTRole
        assert TorkMetaGPTRole is not None

    def test_import_team(self):
        """Test TorkMetaGPTTeam import."""
        from tork_governance.adapters.metagpt import TorkMetaGPTTeam
        assert TorkMetaGPTTeam is not None

    def test_import_action(self):
        """Test TorkMetaGPTAction import."""
        from tork_governance.adapters.metagpt import TorkMetaGPTAction
        assert TorkMetaGPTAction is not None

    def test_role_instantiation(self):
        """Test role can be instantiated."""
        from tork_governance.adapters.metagpt import TorkMetaGPTRole
        role = TorkMetaGPTRole()
        assert role is not None


# ============================================================
# BABYAGI ADAPTER TESTS
# ============================================================

class TestBabyAGIAdapter:
    """Full test suite for BabyAGI adapter."""

    def test_import_agent(self):
        """Test TorkBabyAGIAgent import."""
        from tork_governance.adapters.babyagi import TorkBabyAGIAgent
        assert TorkBabyAGIAgent is not None

    def test_import_task_manager(self):
        """Test TorkBabyAGITaskManager import."""
        from tork_governance.adapters.babyagi import TorkBabyAGITaskManager
        assert TorkBabyAGITaskManager is not None

    def test_import_decorator(self):
        """Test governed_task import."""
        from tork_governance.adapters.babyagi import governed_task
        assert governed_task is not None

    def test_agent_instantiation(self):
        """Test agent can be instantiated."""
        from tork_governance.adapters.babyagi import TorkBabyAGIAgent
        agent = TorkBabyAGIAgent()
        assert agent is not None


# ============================================================
# AGENTGPT ADAPTER TESTS
# ============================================================

class TestAgentGPTAdapter:
    """Full test suite for AgentGPT adapter."""

    def test_import_agent(self):
        """Test TorkAgentGPTAgent import."""
        from tork_governance.adapters.agentgpt import TorkAgentGPTAgent
        assert TorkAgentGPTAgent is not None

    def test_import_task(self):
        """Test TorkAgentGPTTask import."""
        from tork_governance.adapters.agentgpt import TorkAgentGPTTask
        assert TorkAgentGPTTask is not None

    def test_import_goal(self):
        """Test TorkAgentGPTGoal import."""
        from tork_governance.adapters.agentgpt import TorkAgentGPTGoal
        assert TorkAgentGPTGoal is not None

    def test_agent_instantiation(self):
        """Test agent can be instantiated."""
        from tork_governance.adapters.agentgpt import TorkAgentGPTAgent
        agent = TorkAgentGPTAgent()
        assert agent is not None


# ============================================================
# FLOWISE ADAPTER TESTS
# ============================================================

class TestFlowiseAdapter:
    """Full test suite for Flowise adapter."""

    def test_import_node(self):
        """Test TorkFlowiseNode import."""
        from tork_governance.adapters.flowise import TorkFlowiseNode
        assert TorkFlowiseNode is not None

    def test_import_flow(self):
        """Test TorkFlowiseFlow import."""
        from tork_governance.adapters.flowise import TorkFlowiseFlow
        assert TorkFlowiseFlow is not None

    def test_import_api(self):
        """Test TorkFlowiseAPI import."""
        from tork_governance.adapters.flowise import TorkFlowiseAPI
        assert TorkFlowiseAPI is not None

    def test_node_instantiation(self):
        """Test node can be instantiated."""
        from tork_governance.adapters.flowise import TorkFlowiseNode
        node = TorkFlowiseNode()
        assert node is not None


# ============================================================
# LANGFLOW ADAPTER TESTS
# ============================================================

class TestLangflowAdapter:
    """Full test suite for Langflow adapter."""

    def test_import_component(self):
        """Test TorkLangflowComponent import."""
        from tork_governance.adapters.langflow import TorkLangflowComponent
        assert TorkLangflowComponent is not None

    def test_import_flow(self):
        """Test TorkLangflowFlow import."""
        from tork_governance.adapters.langflow import TorkLangflowFlow
        assert TorkLangflowFlow is not None

    def test_import_api(self):
        """Test TorkLangflowAPI import."""
        from tork_governance.adapters.langflow import TorkLangflowAPI
        assert TorkLangflowAPI is not None

    def test_component_instantiation(self):
        """Test component can be instantiated."""
        from tork_governance.adapters.langflow import TorkLangflowComponent
        component = TorkLangflowComponent()
        assert component is not None


# ============================================================
# GUARDRAILS AI ADAPTER TESTS
# ============================================================

class TestGuardrailsAIAdapter:
    """Full test suite for Guardrails AI adapter."""

    def test_import_validator(self):
        """Test TorkValidator import."""
        from tork_governance.adapters.guardrails_ai import TorkValidator
        assert TorkValidator is not None

    def test_import_guard(self):
        """Test TorkGuard import."""
        from tork_governance.adapters.guardrails_ai import TorkGuard
        assert TorkGuard is not None

    def test_import_rail(self):
        """Test TorkRail import."""
        from tork_governance.adapters.guardrails_ai import TorkRail
        assert TorkRail is not None

    def test_validator_instantiation(self):
        """Test validator can be instantiated."""
        from tork_governance.adapters.guardrails_ai import TorkValidator
        validator = TorkValidator()
        assert validator is not None

    def test_validator_ssn_redaction(self):
        """Test SSN is redacted by validator."""
        from tork_governance.adapters.guardrails_ai import TorkValidator
        validator = TorkValidator()
        result = validator.validate(TEST_INPUTS["ssn"])
        assert "[SSN_REDACTED]" in result["value"]

    def test_validator_email_redaction(self):
        """Test email is redacted by validator."""
        from tork_governance.adapters.guardrails_ai import TorkValidator
        validator = TorkValidator()
        result = validator.validate(TEST_INPUTS["email"])
        assert "[EMAIL_REDACTED]" in result["value"]

    def test_guard_instantiation(self):
        """Test guard can be instantiated."""
        from tork_governance.adapters.guardrails_ai import TorkGuard
        guard = TorkGuard()
        assert guard is not None

    def test_guard_ssn_redaction(self):
        """Test SSN is redacted by guard."""
        from tork_governance.adapters.guardrails_ai import TorkGuard
        guard = TorkGuard()
        result = guard.validate(TEST_INPUTS["ssn"])
        assert "[SSN_REDACTED]" in result


# ============================================================
# DIFY ADAPTER TESTS
# ============================================================

class TestDifyAdapter:
    """Full test suite for Dify adapter."""

    def test_import_node(self):
        """Test TorkDifyNode import."""
        from tork_governance.adapters.dify import TorkDifyNode
        assert TorkDifyNode is not None

    def test_import_hook(self):
        """Test TorkDifyHook import."""
        from tork_governance.adapters.dify import TorkDifyHook
        assert TorkDifyHook is not None

    def test_import_app(self):
        """Test TorkDifyApp import."""
        from tork_governance.adapters.dify import TorkDifyApp
        assert TorkDifyApp is not None

    def test_node_instantiation(self):
        """Test node can be instantiated."""
        from tork_governance.adapters.dify import TorkDifyNode
        node = TorkDifyNode()
        assert node is not None

    def test_node_ssn_redaction(self):
        """Test SSN is redacted by node."""
        from tork_governance.adapters.dify import TorkDifyNode
        node = TorkDifyNode()
        result = node.process({"query": TEST_INPUTS["ssn"]})
        assert "[SSN_REDACTED]" in result["governed_text"]

    def test_node_email_redaction(self):
        """Test email is redacted by node."""
        from tork_governance.adapters.dify import TorkDifyNode
        node = TorkDifyNode()
        result = node.process({"query": TEST_INPUTS["email"]})
        assert "[EMAIL_REDACTED]" in result["governed_text"]

    def test_hook_instantiation(self):
        """Test hook can be instantiated."""
        from tork_governance.adapters.dify import TorkDifyHook
        hook = TorkDifyHook()
        assert hook is not None


# ============================================================
# TEST RUNNER AND REPORT GENERATION
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
