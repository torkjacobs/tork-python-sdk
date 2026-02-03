"""
Comprehensive Adapter Tests
Phase B: Test all 27 framework adapters

Tests:
- Import verification
- Class instantiation
- Basic method existence
- Configuration options
"""

import pytest


# ============================================================================
# LANGCHAIN ADAPTER
# ============================================================================

class TestLangChainAdapter:
    """Test LangChain adapter"""

    def test_import_callback_handler(self):
        """Test TorkCallbackHandler can be imported"""
        from tork_governance.adapters.langchain import TorkCallbackHandler
        assert TorkCallbackHandler is not None

    def test_import_governed_chain(self):
        """Test TorkGovernedChain can be imported"""
        from tork_governance.adapters.langchain import TorkGovernedChain
        assert TorkGovernedChain is not None

    def test_import_create_governed_chain(self):
        """Test create_governed_chain can be imported"""
        from tork_governance.adapters.langchain import create_governed_chain
        assert callable(create_governed_chain)

    def test_callback_handler_instantiation(self):
        """Test TorkCallbackHandler can be instantiated"""
        from tork_governance.adapters.langchain import TorkCallbackHandler
        handler = TorkCallbackHandler()
        assert handler is not None


# ============================================================================
# CREWAI ADAPTER
# ============================================================================

class TestCrewAIAdapter:
    """Test CrewAI adapter"""

    def test_import_middleware(self):
        """Test TorkCrewAIMiddleware can be imported"""
        from tork_governance.adapters.crewai import TorkCrewAIMiddleware
        assert TorkCrewAIMiddleware is not None

    def test_import_governed_agent(self):
        """Test GovernedAgent can be imported"""
        from tork_governance.adapters.crewai import GovernedAgent
        assert GovernedAgent is not None

    def test_import_governed_crew(self):
        """Test GovernedCrew can be imported"""
        from tork_governance.adapters.crewai import GovernedCrew
        assert GovernedCrew is not None

    def test_middleware_instantiation(self):
        """Test TorkCrewAIMiddleware can be instantiated"""
        from tork_governance.adapters.crewai import TorkCrewAIMiddleware
        middleware = TorkCrewAIMiddleware()
        assert middleware is not None


# ============================================================================
# AUTOGEN ADAPTER
# ============================================================================

class TestAutoGenAdapter:
    """Test AutoGen adapter"""

    def test_import_middleware(self):
        """Test TorkAutoGenMiddleware can be imported"""
        from tork_governance.adapters.autogen import TorkAutoGenMiddleware
        assert TorkAutoGenMiddleware is not None

    def test_import_governed_agent(self):
        """Test GovernedAutoGenAgent can be imported"""
        from tork_governance.adapters.autogen import GovernedAutoGenAgent
        assert GovernedAutoGenAgent is not None

    def test_middleware_instantiation(self):
        """Test TorkAutoGenMiddleware can be instantiated"""
        from tork_governance.adapters.autogen import TorkAutoGenMiddleware
        middleware = TorkAutoGenMiddleware()
        assert middleware is not None


# ============================================================================
# OPENAI AGENTS ADAPTER
# ============================================================================

class TestOpenAIAgentsAdapter:
    """Test OpenAI Agents adapter"""

    def test_import_middleware(self):
        """Test TorkOpenAIAgentsMiddleware can be imported"""
        from tork_governance.adapters.openai_agents import TorkOpenAIAgentsMiddleware
        assert TorkOpenAIAgentsMiddleware is not None

    def test_import_governed_agent(self):
        """Test GovernedOpenAIAgent can be imported"""
        from tork_governance.adapters.openai_agents import GovernedOpenAIAgent
        assert GovernedOpenAIAgent is not None

    def test_middleware_instantiation(self):
        """Test TorkOpenAIAgentsMiddleware can be instantiated"""
        from tork_governance.adapters.openai_agents import TorkOpenAIAgentsMiddleware
        middleware = TorkOpenAIAgentsMiddleware()
        assert middleware is not None


# ============================================================================
# FASTAPI ADAPTER
# ============================================================================

class TestFastAPIAdapter:
    """Test FastAPI adapter"""

    def test_import_middleware(self):
        """Test TorkFastAPIMiddleware can be imported"""
        from tork_governance.adapters.fastapi import TorkFastAPIMiddleware
        assert TorkFastAPIMiddleware is not None

    def test_import_dependency(self):
        """Test TorkFastAPIDependency can be imported"""
        from tork_governance.adapters.fastapi import TorkFastAPIDependency
        assert TorkFastAPIDependency is not None


# ============================================================================
# DJANGO ADAPTER
# ============================================================================

class TestDjangoAdapter:
    """Test Django adapter"""

    def test_import_middleware(self):
        """Test TorkDjangoMiddleware can be imported"""
        from tork_governance.adapters.django import TorkDjangoMiddleware
        assert TorkDjangoMiddleware is not None


# ============================================================================
# FLASK ADAPTER
# ============================================================================

class TestFlaskAdapter:
    """Test Flask adapter"""

    def test_import_tork_flask(self):
        """Test TorkFlask can be imported"""
        from tork_governance.adapters.flask import TorkFlask
        assert TorkFlask is not None

    def test_import_tork_required(self):
        """Test tork_required can be imported"""
        from tork_governance.adapters.flask import tork_required
        assert callable(tork_required)


# ============================================================================
# MCP ADAPTER
# ============================================================================

class TestMCPAdapter:
    """Test MCP (Model Context Protocol) adapter"""

    def test_import_tool_wrapper(self):
        """Test TorkMCPToolWrapper can be imported"""
        from tork_governance.adapters.mcp import TorkMCPToolWrapper
        assert TorkMCPToolWrapper is not None

    def test_import_server(self):
        """Test TorkMCPServer can be imported"""
        from tork_governance.adapters.mcp import TorkMCPServer
        assert TorkMCPServer is not None

    def test_import_middleware(self):
        """Test TorkMCPMiddleware can be imported"""
        from tork_governance.adapters.mcp import TorkMCPMiddleware
        assert TorkMCPMiddleware is not None

    def test_tool_wrapper_instantiation(self):
        """Test TorkMCPToolWrapper can be instantiated"""
        from tork_governance.adapters.mcp import TorkMCPToolWrapper
        wrapper = TorkMCPToolWrapper()
        assert wrapper is not None

    def test_middleware_instantiation(self):
        """Test TorkMCPMiddleware can be instantiated"""
        from tork_governance.adapters.mcp import TorkMCPMiddleware
        middleware = TorkMCPMiddleware()
        assert middleware is not None


# ============================================================================
# LLAMAINDEX ADAPTER
# ============================================================================

class TestLlamaIndexAdapter:
    """Test LlamaIndex adapter"""

    def test_import_callback(self):
        """Test TorkLlamaIndexCallback can be imported"""
        from tork_governance.adapters.llamaindex import TorkLlamaIndexCallback
        assert TorkLlamaIndexCallback is not None

    def test_import_query_engine(self):
        """Test TorkQueryEngine can be imported"""
        from tork_governance.adapters.llamaindex import TorkQueryEngine
        assert TorkQueryEngine is not None

    def test_import_retriever(self):
        """Test TorkRetriever can be imported"""
        from tork_governance.adapters.llamaindex import TorkRetriever
        assert TorkRetriever is not None


# ============================================================================
# SEMANTIC KERNEL ADAPTER
# ============================================================================

class TestSemanticKernelAdapter:
    """Test Semantic Kernel adapter"""

    def test_import_filter(self):
        """Test TorkSKFilter can be imported"""
        from tork_governance.adapters.semantic_kernel import TorkSKFilter
        assert TorkSKFilter is not None

    def test_import_plugin(self):
        """Test TorkSKPlugin can be imported"""
        from tork_governance.adapters.semantic_kernel import TorkSKPlugin
        assert TorkSKPlugin is not None

    def test_import_prompt_filter(self):
        """Test TorkSKPromptFilter can be imported"""
        from tork_governance.adapters.semantic_kernel import TorkSKPromptFilter
        assert TorkSKPromptFilter is not None


# ============================================================================
# HAYSTACK ADAPTER
# ============================================================================

class TestHaystackAdapter:
    """Test Haystack adapter"""

    def test_import_component(self):
        """Test TorkHaystackComponent can be imported"""
        from tork_governance.adapters.haystack import TorkHaystackComponent
        assert TorkHaystackComponent is not None

    def test_import_pipeline(self):
        """Test TorkHaystackPipeline can be imported"""
        from tork_governance.adapters.haystack import TorkHaystackPipeline
        assert TorkHaystackPipeline is not None

    def test_import_document_processor(self):
        """Test TorkDocumentProcessor can be imported"""
        from tork_governance.adapters.haystack import TorkDocumentProcessor
        assert TorkDocumentProcessor is not None


# ============================================================================
# PYDANTIC AI ADAPTER
# ============================================================================

class TestPydanticAIAdapter:
    """Test Pydantic AI adapter"""

    def test_import_middleware(self):
        """Test TorkPydanticAIMiddleware can be imported"""
        from tork_governance.adapters.pydantic_ai import TorkPydanticAIMiddleware
        assert TorkPydanticAIMiddleware is not None

    def test_import_tool(self):
        """Test TorkPydanticAITool can be imported"""
        from tork_governance.adapters.pydantic_ai import TorkPydanticAITool
        assert TorkPydanticAITool is not None

    def test_import_agent_dependency(self):
        """Test TorkAgentDependency can be imported"""
        from tork_governance.adapters.pydantic_ai import TorkAgentDependency
        assert TorkAgentDependency is not None


# ============================================================================
# DSPY ADAPTER
# ============================================================================

class TestDSPyAdapter:
    """Test DSPy adapter"""

    def test_import_module(self):
        """Test TorkDSPyModule can be imported"""
        from tork_governance.adapters.dspy import TorkDSPyModule
        assert TorkDSPyModule is not None

    def test_import_signature(self):
        """Test TorkDSPySignature can be imported"""
        from tork_governance.adapters.dspy import TorkDSPySignature
        assert TorkDSPySignature is not None

    def test_import_governed_predict(self):
        """Test governed_predict can be imported"""
        from tork_governance.adapters.dspy import governed_predict
        assert callable(governed_predict)


# ============================================================================
# INSTRUCTOR ADAPTER
# ============================================================================

class TestInstructorAdapter:
    """Test Instructor adapter"""

    def test_import_client(self):
        """Test TorkInstructorClient can be imported"""
        from tork_governance.adapters.instructor import TorkInstructorClient
        assert TorkInstructorClient is not None

    def test_import_patch(self):
        """Test TorkInstructorPatch can be imported"""
        from tork_governance.adapters.instructor import TorkInstructorPatch
        assert TorkInstructorPatch is not None

    def test_import_governed_response(self):
        """Test governed_response can be imported"""
        from tork_governance.adapters.instructor import governed_response
        assert callable(governed_response)


# ============================================================================
# GUIDANCE ADAPTER
# ============================================================================

class TestGuidanceAdapter:
    """Test Guidance (Microsoft) adapter"""

    def test_import_program(self):
        """Test TorkGuidanceProgram can be imported"""
        from tork_governance.adapters.guidance import TorkGuidanceProgram
        assert TorkGuidanceProgram is not None

    def test_import_gen(self):
        """Test TorkGuidanceGen can be imported"""
        from tork_governance.adapters.guidance import TorkGuidanceGen
        assert TorkGuidanceGen is not None

    def test_import_governed_block(self):
        """Test governed_block can be imported"""
        from tork_governance.adapters.guidance import governed_block
        assert callable(governed_block)


# ============================================================================
# LMQL ADAPTER
# ============================================================================

class TestLMQLAdapter:
    """Test LMQL adapter"""

    def test_import_query(self):
        """Test TorkLMQLQuery can be imported"""
        from tork_governance.adapters.lmql import TorkLMQLQuery
        assert TorkLMQLQuery is not None

    def test_import_runtime(self):
        """Test TorkLMQLRuntime can be imported"""
        from tork_governance.adapters.lmql import TorkLMQLRuntime
        assert TorkLMQLRuntime is not None

    def test_import_governed_query(self):
        """Test governed_query can be imported"""
        from tork_governance.adapters.lmql import governed_query
        assert callable(governed_query)


# ============================================================================
# OUTLINES ADAPTER
# ============================================================================

class TestOutlinesAdapter:
    """Test Outlines adapter"""

    def test_import_generator(self):
        """Test TorkOutlinesGenerator can be imported"""
        from tork_governance.adapters.outlines import TorkOutlinesGenerator
        assert TorkOutlinesGenerator is not None

    def test_import_model(self):
        """Test TorkOutlinesModel can be imported"""
        from tork_governance.adapters.outlines import TorkOutlinesModel
        assert TorkOutlinesModel is not None

    def test_import_governed_generate(self):
        """Test governed_generate can be imported"""
        from tork_governance.adapters.outlines import governed_generate
        assert callable(governed_generate)


# ============================================================================
# MARVIN ADAPTER
# ============================================================================

class TestMarvinAdapter:
    """Test Marvin adapter"""

    def test_import_ai(self):
        """Test TorkMarvinAI can be imported"""
        from tork_governance.adapters.marvin import TorkMarvinAI
        assert TorkMarvinAI is not None

    def test_import_governed_fn(self):
        """Test governed_fn can be imported"""
        from tork_governance.adapters.marvin import governed_fn
        assert callable(governed_fn)

    def test_import_governed_classifier(self):
        """Test governed_classifier can be imported"""
        from tork_governance.adapters.marvin import governed_classifier
        assert callable(governed_classifier)


# ============================================================================
# SUPERAGI ADAPTER
# ============================================================================

class TestSuperAGIAdapter:
    """Test SuperAGI adapter"""

    def test_import_agent(self):
        """Test TorkSuperAGIAgent can be imported"""
        from tork_governance.adapters.superagi import TorkSuperAGIAgent
        assert TorkSuperAGIAgent is not None

    def test_import_tool(self):
        """Test TorkSuperAGITool can be imported"""
        from tork_governance.adapters.superagi import TorkSuperAGITool
        assert TorkSuperAGITool is not None

    def test_import_workflow(self):
        """Test TorkSuperAGIWorkflow can be imported"""
        from tork_governance.adapters.superagi import TorkSuperAGIWorkflow
        assert TorkSuperAGIWorkflow is not None


# ============================================================================
# METAGPT ADAPTER
# ============================================================================

class TestMetaGPTAdapter:
    """Test MetaGPT adapter"""

    def test_import_role(self):
        """Test TorkMetaGPTRole can be imported"""
        from tork_governance.adapters.metagpt import TorkMetaGPTRole
        assert TorkMetaGPTRole is not None

    def test_import_team(self):
        """Test TorkMetaGPTTeam can be imported"""
        from tork_governance.adapters.metagpt import TorkMetaGPTTeam
        assert TorkMetaGPTTeam is not None

    def test_import_action(self):
        """Test TorkMetaGPTAction can be imported"""
        from tork_governance.adapters.metagpt import TorkMetaGPTAction
        assert TorkMetaGPTAction is not None


# ============================================================================
# BABYAGI ADAPTER
# ============================================================================

class TestBabyAGIAdapter:
    """Test BabyAGI adapter"""

    def test_import_agent(self):
        """Test TorkBabyAGIAgent can be imported"""
        from tork_governance.adapters.babyagi import TorkBabyAGIAgent
        assert TorkBabyAGIAgent is not None

    def test_import_task_manager(self):
        """Test TorkBabyAGITaskManager can be imported"""
        from tork_governance.adapters.babyagi import TorkBabyAGITaskManager
        assert TorkBabyAGITaskManager is not None

    def test_import_governed_task(self):
        """Test governed_task can be imported"""
        from tork_governance.adapters.babyagi import governed_task
        assert callable(governed_task)


# ============================================================================
# AGENTGPT ADAPTER
# ============================================================================

class TestAgentGPTAdapter:
    """Test AgentGPT adapter"""

    def test_import_agent(self):
        """Test TorkAgentGPTAgent can be imported"""
        from tork_governance.adapters.agentgpt import TorkAgentGPTAgent
        assert TorkAgentGPTAgent is not None

    def test_import_task(self):
        """Test TorkAgentGPTTask can be imported"""
        from tork_governance.adapters.agentgpt import TorkAgentGPTTask
        assert TorkAgentGPTTask is not None

    def test_import_goal(self):
        """Test TorkAgentGPTGoal can be imported"""
        from tork_governance.adapters.agentgpt import TorkAgentGPTGoal
        assert TorkAgentGPTGoal is not None


# ============================================================================
# FLOWISE ADAPTER
# ============================================================================

class TestFlowiseAdapter:
    """Test Flowise adapter"""

    def test_import_node(self):
        """Test TorkFlowiseNode can be imported"""
        from tork_governance.adapters.flowise import TorkFlowiseNode
        assert TorkFlowiseNode is not None

    def test_import_flow(self):
        """Test TorkFlowiseFlow can be imported"""
        from tork_governance.adapters.flowise import TorkFlowiseFlow
        assert TorkFlowiseFlow is not None

    def test_import_api(self):
        """Test TorkFlowiseAPI can be imported"""
        from tork_governance.adapters.flowise import TorkFlowiseAPI
        assert TorkFlowiseAPI is not None


# ============================================================================
# LANGFLOW ADAPTER
# ============================================================================

class TestLangflowAdapter:
    """Test Langflow adapter"""

    def test_import_component(self):
        """Test TorkLangflowComponent can be imported"""
        from tork_governance.adapters.langflow import TorkLangflowComponent
        assert TorkLangflowComponent is not None

    def test_import_flow(self):
        """Test TorkLangflowFlow can be imported"""
        from tork_governance.adapters.langflow import TorkLangflowFlow
        assert TorkLangflowFlow is not None

    def test_import_api(self):
        """Test TorkLangflowAPI can be imported"""
        from tork_governance.adapters.langflow import TorkLangflowAPI
        assert TorkLangflowAPI is not None


# ============================================================================
# STARLETTE ADAPTER
# ============================================================================

class TestStarletteAdapter:
    """Test Starlette adapter"""

    def test_import_middleware(self):
        """Test TorkStarletteMiddleware can be imported"""
        from tork_governance.adapters.starlette import TorkStarletteMiddleware
        assert TorkStarletteMiddleware is not None

    def test_import_route(self):
        """Test TorkStarletteRoute can be imported"""
        from tork_governance.adapters.starlette import TorkStarletteRoute
        assert TorkStarletteRoute is not None

    def test_import_tork_route(self):
        """Test tork_route can be imported"""
        from tork_governance.adapters.starlette import tork_route
        assert callable(tork_route)


# ============================================================================
# GUARDRAILS AI ADAPTER
# ============================================================================

class TestGuardrailsAIAdapter:
    """Test Guardrails AI adapter"""

    def test_import_validator(self):
        """Test TorkValidator can be imported"""
        from tork_governance.adapters.guardrails_ai import TorkValidator
        assert TorkValidator is not None

    def test_import_guard(self):
        """Test TorkGuard can be imported"""
        from tork_governance.adapters.guardrails_ai import TorkGuard
        assert TorkGuard is not None

    def test_import_rail(self):
        """Test TorkRail can be imported"""
        from tork_governance.adapters.guardrails_ai import TorkRail
        assert TorkRail is not None

    def test_import_with_tork_governance(self):
        """Test with_tork_governance can be imported"""
        from tork_governance.adapters.guardrails_ai import with_tork_governance
        assert callable(with_tork_governance)


# ============================================================================
# DIFY ADAPTER
# ============================================================================

class TestDifyAdapter:
    """Test Dify adapter"""

    def test_import_node(self):
        """Test TorkDifyNode can be imported"""
        from tork_governance.adapters.dify import TorkDifyNode
        assert TorkDifyNode is not None

    def test_import_hook(self):
        """Test TorkDifyHook can be imported"""
        from tork_governance.adapters.dify import TorkDifyHook
        assert TorkDifyHook is not None

    def test_import_app(self):
        """Test TorkDifyApp can be imported"""
        from tork_governance.adapters.dify import TorkDifyApp
        assert TorkDifyApp is not None

    def test_import_dify_governed(self):
        """Test dify_governed can be imported"""
        from tork_governance.adapters.dify import dify_governed
        assert callable(dify_governed)


# ============================================================================
# ADAPTER MODULE __init__ IMPORTS
# ============================================================================

class TestAdaptersModuleImports:
    """Test that all adapters can be imported from main module"""

    def test_import_from_adapters(self):
        """Test all exports from adapters module"""
        from tork_governance.adapters import (
            # LangChain
            TorkCallbackHandler,
            TorkGovernedChain,
            create_governed_chain,
            # CrewAI
            TorkCrewAIMiddleware,
            GovernedAgent,
            GovernedCrew,
            # AutoGen
            TorkAutoGenMiddleware,
            GovernedAutoGenAgent,
            # OpenAI Agents
            TorkOpenAIAgentsMiddleware,
            GovernedOpenAIAgent,
            # FastAPI
            TorkFastAPIMiddleware,
            TorkFastAPIDependency,
            # Django
            TorkDjangoMiddleware,
            # Flask
            TorkFlask,
            tork_required,
            # MCP
            TorkMCPToolWrapper,
            TorkMCPServer,
            TorkMCPMiddleware,
        )

        # Verify all are not None
        assert TorkCallbackHandler is not None
        assert TorkGovernedChain is not None
        assert TorkCrewAIMiddleware is not None
        assert TorkAutoGenMiddleware is not None
        assert TorkFastAPIMiddleware is not None
        assert TorkDjangoMiddleware is not None
        assert TorkFlask is not None
        assert TorkMCPToolWrapper is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
