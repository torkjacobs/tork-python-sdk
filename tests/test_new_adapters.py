"""
Tests for new AI framework adapters.

Tests MCP, LlamaIndex, Semantic Kernel, Haystack, and Pydantic AI adapters.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
import asyncio

from tork_governance.core import Tork, GovernanceAction


class TestMCPAdapter:
    """Tests for MCP (Model Context Protocol) adapter."""

    def test_mcp_tool_wrapper_init(self):
        """Test TorkMCPToolWrapper initialization."""
        from tork_governance.adapters.mcp import TorkMCPToolWrapper

        wrapper = TorkMCPToolWrapper()
        assert wrapper.tork is not None
        assert wrapper.receipts == []

    def test_mcp_tool_wrapper_govern_tool(self):
        """Test tool wrapping with governance."""
        from tork_governance.adapters.mcp import TorkMCPToolWrapper

        wrapper = TorkMCPToolWrapper()

        @wrapper.govern_tool
        def search_tool(query: str) -> str:
            return f"Results for: {query}"

        # Test with clean input
        result = search_tool(query="hello world")
        assert "Results for: hello world" in result

        # Test with PII input
        result = search_tool(query="Contact john@example.com")
        assert "[EMAIL_REDACTED]" in result
        assert len(wrapper.get_receipts()) >= 1

    def test_mcp_server_init(self):
        """Test TorkMCPServer initialization."""
        from tork_governance.adapters.mcp import TorkMCPServer

        server = TorkMCPServer(server_name="test-server")
        assert server.server_name == "test-server"
        assert len(server.tools) == 0

    def test_mcp_server_register_tool(self):
        """Test tool registration."""
        from tork_governance.adapters.mcp import TorkMCPServer

        server = TorkMCPServer(server_name="test-server")

        def my_tool(text: str) -> str:
            return text.upper()

        server.register_tool(my_tool)
        assert "my_tool" in server.tools

    def test_mcp_middleware(self):
        """Test TorkMCPMiddleware."""
        from tork_governance.adapters.mcp import TorkMCPMiddleware

        middleware = TorkMCPMiddleware()

        # Test request governance
        request = {"arguments": {"query": "test@email.com"}}
        governed = middleware.govern_request(request)
        assert "[EMAIL_REDACTED]" in governed["arguments"]["query"]


class TestLlamaIndexAdapter:
    """Tests for LlamaIndex adapter."""

    def test_callback_init(self):
        """Test TorkLlamaIndexCallback initialization."""
        from tork_governance.adapters.llamaindex import TorkLlamaIndexCallback

        callback = TorkLlamaIndexCallback()
        assert callback.tork is not None
        assert callback.receipts == []

    def test_callback_on_query_start(self):
        """Test query start governance."""
        from tork_governance.adapters.llamaindex import TorkLlamaIndexCallback

        callback = TorkLlamaIndexCallback()

        # Clean query
        result = callback.on_query_start("Find documents about AI")
        assert result == "Find documents about AI"

        # Query with PII
        result = callback.on_query_start("Find data for 123-45-6789")
        assert "[SSN_REDACTED]" in result
        assert len(callback.get_receipts()) == 2

    def test_callback_on_query_end(self):
        """Test query end governance."""
        from tork_governance.adapters.llamaindex import TorkLlamaIndexCallback

        callback = TorkLlamaIndexCallback()
        result = callback.on_query_end("User email is test@example.com")
        assert "[EMAIL_REDACTED]" in result

    def test_query_engine_init(self):
        """Test TorkQueryEngine initialization."""
        from tork_governance.adapters.llamaindex import TorkQueryEngine

        mock_engine = MagicMock()
        governed_engine = TorkQueryEngine(mock_engine)
        assert governed_engine.engine == mock_engine

    def test_query_engine_query(self):
        """Test governed query execution."""
        from tork_governance.adapters.llamaindex import TorkQueryEngine

        mock_response = MagicMock()
        mock_response.response = "Contact: admin@company.com"

        mock_engine = MagicMock()
        mock_engine.query.return_value = mock_response

        governed_engine = TorkQueryEngine(mock_engine)
        result = governed_engine.query("Find contact info")

        assert "[EMAIL_REDACTED]" in result.response
        assert len(governed_engine.get_receipts()) >= 1

    def test_retriever_init(self):
        """Test TorkRetriever initialization."""
        from tork_governance.adapters.llamaindex import TorkRetriever

        mock_retriever = MagicMock()
        governed_retriever = TorkRetriever(mock_retriever)
        assert governed_retriever.retriever == mock_retriever


class TestSemanticKernelAdapter:
    """Tests for Microsoft Semantic Kernel adapter."""

    def test_sk_filter_init(self):
        """Test TorkSKFilter initialization."""
        from tork_governance.adapters.semantic_kernel import TorkSKFilter

        sk_filter = TorkSKFilter()
        assert sk_filter.tork is not None
        assert sk_filter.receipts == []

    @pytest.mark.asyncio
    async def test_sk_filter_function_invocation(self):
        """Test function invocation filter."""
        from tork_governance.adapters.semantic_kernel import TorkSKFilter

        sk_filter = TorkSKFilter()

        context = MagicMock()
        context.arguments = {"text": "Email: user@domain.com"}

        result = await sk_filter.on_function_invocation(context)
        assert "[EMAIL_REDACTED]" in result.arguments["text"]

    @pytest.mark.asyncio
    async def test_sk_filter_function_result(self):
        """Test function result filter."""
        from tork_governance.adapters.semantic_kernel import TorkSKFilter

        sk_filter = TorkSKFilter()

        context = MagicMock()
        result = await sk_filter.on_function_result(context, "SSN: 123-45-6789")
        assert "[SSN_REDACTED]" in result

    def test_sk_plugin_init(self):
        """Test TorkSKPlugin initialization."""
        from tork_governance.adapters.semantic_kernel import TorkSKPlugin

        plugin = TorkSKPlugin()
        assert plugin.tork is not None

    @pytest.mark.asyncio
    async def test_sk_plugin_governed_function(self):
        """Test governed function decorator."""
        from tork_governance.adapters.semantic_kernel import TorkSKPlugin

        plugin = TorkSKPlugin()

        @plugin.governed_function
        async def process(text: str) -> str:
            return f"Processed: {text}"

        result = await process(text="test@email.com")
        assert "[EMAIL_REDACTED]" in result

    def test_sk_plugin_check_pii(self):
        """Test PII checking."""
        from tork_governance.adapters.semantic_kernel import TorkSKPlugin

        plugin = TorkSKPlugin()

        assert plugin.check_pii("test@example.com") is True
        assert plugin.check_pii("hello world") is False


class TestHaystackAdapter:
    """Tests for deepset Haystack adapter."""

    def test_component_init(self):
        """Test TorkHaystackComponent initialization."""
        from tork_governance.adapters.haystack import TorkHaystackComponent

        component = TorkHaystackComponent()
        assert component.tork is not None
        assert component.receipts == []

    def test_component_run_query(self):
        """Test component run with query."""
        from tork_governance.adapters.haystack import TorkHaystackComponent

        component = TorkHaystackComponent()
        result = component.run(query="Find user@example.com")

        assert "query" in result
        assert "[EMAIL_REDACTED]" in result["query"]
        assert "query_receipt" in result

    def test_component_run_text(self):
        """Test component run with text."""
        from tork_governance.adapters.haystack import TorkHaystackComponent

        component = TorkHaystackComponent()
        result = component.run(text="SSN is 123-45-6789")

        assert "text" in result
        assert "[SSN_REDACTED]" in result["text"]

    def test_component_run_documents(self):
        """Test component run with documents."""
        from tork_governance.adapters.haystack import TorkHaystackComponent

        component = TorkHaystackComponent()

        doc = MagicMock()
        doc.content = "Contact: admin@test.com"

        result = component.run(documents=[doc])
        assert "documents" in result
        assert "[EMAIL_REDACTED]" in result["documents"][0].content

    def test_pipeline_init(self):
        """Test TorkHaystackPipeline initialization."""
        from tork_governance.adapters.haystack import TorkHaystackPipeline

        mock_pipeline = MagicMock()
        governed = TorkHaystackPipeline(mock_pipeline)
        assert governed.pipeline == mock_pipeline

    def test_pipeline_run(self):
        """Test governed pipeline run."""
        from tork_governance.adapters.haystack import TorkHaystackPipeline

        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = {"output": "Result: test@email.com"}

        governed = TorkHaystackPipeline(mock_pipeline)
        result = governed.run({"query": "user@domain.com"})

        # Input should be governed
        call_args = mock_pipeline.run.call_args[0][0]
        assert "[EMAIL_REDACTED]" in call_args["query"]

        # Output should be governed
        assert "[EMAIL_REDACTED]" in result["output"]

    def test_document_processor(self):
        """Test TorkDocumentProcessor."""
        from tork_governance.adapters.haystack import TorkDocumentProcessor

        processor = TorkDocumentProcessor()

        doc = MagicMock()
        doc.content = "Phone: 555-123-4567"
        doc.meta = {}

        processed = processor.process([doc])
        assert "[PHONE_REDACTED]" in processed[0].content
        assert "tork_receipt_id" in processed[0].meta


class TestPydanticAIAdapter:
    """Tests for Pydantic AI adapter."""

    def test_middleware_init(self):
        """Test TorkPydanticAIMiddleware initialization."""
        from tork_governance.adapters.pydantic_ai import TorkPydanticAIMiddleware

        middleware = TorkPydanticAIMiddleware()
        assert middleware.tork is not None
        assert middleware.receipts == []

    def test_middleware_wrap_agent(self):
        """Test agent wrapping."""
        from tork_governance.adapters.pydantic_ai import TorkPydanticAIMiddleware

        middleware = TorkPydanticAIMiddleware()

        mock_agent = MagicMock()
        original_run = mock_agent.run

        wrapped = middleware.wrap_agent(mock_agent)
        assert wrapped.run != original_run

    def test_tool_wrapper_init(self):
        """Test TorkPydanticAITool initialization."""
        from tork_governance.adapters.pydantic_ai import TorkPydanticAITool

        wrapper = TorkPydanticAITool()
        assert wrapper.tork is not None

    def test_tool_wrapper_governed_tool(self):
        """Test governed tool decorator."""
        from tork_governance.adapters.pydantic_ai import TorkPydanticAITool

        wrapper = TorkPydanticAITool()

        @wrapper.governed_tool
        def process(text: str) -> str:
            return f"Output: {text}"

        result = process(text="email@test.com")
        assert "[EMAIL_REDACTED]" in result

    def test_agent_dependency_init(self):
        """Test TorkAgentDependency initialization."""
        from tork_governance.adapters.pydantic_ai import TorkAgentDependency

        dep = TorkAgentDependency()
        assert dep.tork is not None

    def test_agent_dependency_govern(self):
        """Test dependency govern method."""
        from tork_governance.adapters.pydantic_ai import TorkAgentDependency

        dep = TorkAgentDependency()
        result = dep.govern("SSN: 123-45-6789")
        assert "[SSN_REDACTED]" in result
        assert len(dep.receipts) == 1

    def test_agent_dependency_check_pii(self):
        """Test dependency PII checking."""
        from tork_governance.adapters.pydantic_ai import TorkAgentDependency

        dep = TorkAgentDependency()
        assert dep.check_pii("user@email.com") is True
        assert dep.check_pii("hello") is False

    def test_agent_dependency_get_result(self):
        """Test dependency get_result method."""
        from tork_governance.adapters.pydantic_ai import TorkAgentDependency

        dep = TorkAgentDependency()
        result = dep.get_result("test@example.com")

        assert result.action == GovernanceAction.REDACT
        assert result.pii.has_pii is True
        assert "email" in result.pii.types


class TestAdapterExports:
    """Test that all adapters are properly exported."""

    def test_all_adapters_importable(self):
        """Test all adapters can be imported from adapters module."""
        from tork_governance.adapters import (
            # MCP
            TorkMCPToolWrapper,
            TorkMCPServer,
            TorkMCPMiddleware,
            # LlamaIndex
            TorkLlamaIndexCallback,
            TorkQueryEngine,
            TorkRetriever,
            # Semantic Kernel
            TorkSKFilter,
            TorkSKPlugin,
            TorkSKPromptFilter,
            # Haystack
            TorkHaystackComponent,
            TorkHaystackPipeline,
            TorkDocumentProcessor,
            # Pydantic AI
            TorkPydanticAIMiddleware,
            TorkPydanticAITool,
            TorkAgentDependency,
        )

        # All imports should succeed
        assert TorkMCPToolWrapper is not None
        assert TorkMCPServer is not None
        assert TorkMCPMiddleware is not None
        assert TorkLlamaIndexCallback is not None
        assert TorkQueryEngine is not None
        assert TorkRetriever is not None
        assert TorkSKFilter is not None
        assert TorkSKPlugin is not None
        assert TorkSKPromptFilter is not None
        assert TorkHaystackComponent is not None
        assert TorkHaystackPipeline is not None
        assert TorkDocumentProcessor is not None
        assert TorkPydanticAIMiddleware is not None
        assert TorkPydanticAITool is not None
        assert TorkAgentDependency is not None
