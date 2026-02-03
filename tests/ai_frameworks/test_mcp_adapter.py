"""
Tests for MCP (Model Context Protocol) adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Tool input governance
- Tool output governance
- Resource governance
- Prompt governance
- Server registration governance
"""

import pytest
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.mcp import (
    TorkMCPToolWrapper,
    TorkMCPServer,
    TorkMCPMiddleware,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestMCPImportInstantiation:
    """Test import and instantiation of MCP adapter."""

    def test_import_tool_wrapper(self):
        """Test TorkMCPToolWrapper can be imported."""
        assert TorkMCPToolWrapper is not None

    def test_import_server(self):
        """Test TorkMCPServer can be imported."""
        assert TorkMCPServer is not None

    def test_import_middleware(self):
        """Test TorkMCPMiddleware can be imported."""
        assert TorkMCPMiddleware is not None

    def test_instantiate_tool_wrapper_default(self):
        """Test tool wrapper instantiation with defaults."""
        wrapper = TorkMCPToolWrapper()
        assert wrapper is not None
        assert wrapper.tork is not None
        assert wrapper.receipts == []


class TestMCPConfiguration:
    """Test configuration of MCP adapter."""

    def test_tool_wrapper_with_tork_instance(self, tork_instance):
        """Test tool wrapper with existing Tork instance."""
        wrapper = TorkMCPToolWrapper(tork=tork_instance)
        assert wrapper.tork is tork_instance

    def test_server_with_name(self):
        """Test server with custom name."""
        server = TorkMCPServer(name="my-server")
        assert server.name == "my-server"

    def test_server_with_tork_instance(self, tork_instance):
        """Test server with existing Tork instance."""
        server = TorkMCPServer(tork=tork_instance)
        assert server.tork is tork_instance

    def test_middleware_with_api_key(self):
        """Test middleware with API key."""
        middleware = TorkMCPMiddleware(api_key="test-key")
        assert middleware.tork is not None


class TestMCPPIIDetection:
    """Test PII detection and redaction in MCP adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        wrapper = TorkMCPToolWrapper()
        result = wrapper.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        wrapper = TorkMCPToolWrapper()
        result = wrapper.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        wrapper = TorkMCPToolWrapper()
        result = wrapper.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        wrapper = TorkMCPToolWrapper()
        result = wrapper.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        wrapper = TorkMCPToolWrapper()
        clean_text = "Hello, how can I help you today?"
        result = wrapper.govern(clean_text)
        assert result == clean_text


class TestMCPErrorHandling:
    """Test error handling in MCP adapter."""

    def test_wrapper_empty_string(self):
        """Test wrapper handles empty string."""
        wrapper = TorkMCPToolWrapper()
        result = wrapper.govern("")
        assert result == ""

    def test_wrapper_whitespace_only(self):
        """Test wrapper handles whitespace-only string."""
        wrapper = TorkMCPToolWrapper()
        result = wrapper.govern("   ")
        assert result == "   "

    def test_server_unknown_tool(self):
        """Test server handles unknown tool call."""
        server = TorkMCPServer()

        import asyncio
        result = asyncio.run(
            server.call_tool("unknown_tool", {})
        )
        assert result["isError"] is True
        assert "Unknown tool" in result["content"]

    def test_govern_tool_input_non_string(self):
        """Test govern_tool_input handles non-string values."""
        wrapper = TorkMCPToolWrapper()
        result = wrapper.govern_tool_input({"count": 42, "flag": True})
        assert result["count"] == 42
        assert result["flag"] is True


class TestMCPComplianceReceipts:
    """Test compliance receipt generation in MCP adapter."""

    def test_govern_tool_input_generates_receipts(self):
        """Test govern_tool_input generates receipts."""
        wrapper = TorkMCPToolWrapper()
        wrapper.govern_tool_input({"query": "test", "limit": 10})
        assert len(wrapper.receipts) == 1  # Only string values
        assert wrapper.receipts[0]["type"] == "tool_input"
        assert wrapper.receipts[0]["argument"] == "query"

    def test_get_receipts_method(self):
        """Test get_receipts returns all receipts."""
        wrapper = TorkMCPToolWrapper()
        wrapper.govern("test1")
        wrapper.govern("test2")
        receipts = wrapper.get_receipts()
        assert len(receipts) == 0  # govern method doesn't generate receipts in wrapper
        # but govern_tool_input does
        wrapper.govern_tool_input({"a": "test"})
        receipts = wrapper.get_receipts()
        assert len(receipts) == 1

    def test_server_get_receipts(self):
        """Test server get_receipts method."""
        server = TorkMCPServer()

        @server.tool("test", "A test tool")
        def test_tool(arg: str) -> str:
            return f"Got: {arg}"

        import asyncio
        asyncio.run(
            server.call_tool("test", {"arg": "hello"})
        )
        receipts = server.get_receipts()
        assert len(receipts) >= 1

    def test_middleware_receipts(self):
        """Test middleware generates receipts."""
        middleware = TorkMCPMiddleware()
        middleware.govern_request({
            "params": {"arguments": {"query": "test"}}
        })
        assert len(middleware.receipts) == 1


class TestMCPToolInputGovernance:
    """Test tool input governance."""

    def test_govern_tool_input_basic(self):
        """Test basic tool input governance."""
        wrapper = TorkMCPToolWrapper()
        result = wrapper.govern_tool_input({"query": "search term"})
        assert result["query"] == "search term"

    def test_govern_tool_input_with_pii(self):
        """Test tool input governance with PII."""
        wrapper = TorkMCPToolWrapper()
        result = wrapper.govern_tool_input({
            "email": PII_SAMPLES["email"],
            "message": PII_MESSAGES["ssn_message"]
        })
        assert PII_SAMPLES["email"] not in result["email"]
        assert PII_SAMPLES["ssn"] not in result["message"]

    def test_wrap_tool_governs_kwargs(self):
        """Test wrapped tool governs keyword arguments."""
        wrapper = TorkMCPToolWrapper()

        @wrapper.wrap_tool
        def search(query: str) -> str:
            return f"Results for: {query}"

        result = search(query=PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_wrap_tool_preserves_name(self):
        """Test wrapped tool preserves original name."""
        wrapper = TorkMCPToolWrapper()

        @wrapper.wrap_tool
        def my_custom_tool(arg: str) -> str:
            return arg

        assert my_custom_tool.__name__ == "my_custom_tool"


class TestMCPToolOutputGovernance:
    """Test tool output governance."""

    def test_wrap_tool_governs_output(self):
        """Test wrapped tool governs output."""
        wrapper = TorkMCPToolWrapper()

        @wrapper.wrap_tool
        def get_user_info() -> str:
            return f"User email: {PII_SAMPLES['email']}"

        result = get_user_info()
        assert PII_SAMPLES["email"] not in result

    def test_wrap_tool_non_string_output(self):
        """Test wrapped tool handles non-string output."""
        wrapper = TorkMCPToolWrapper()

        @wrapper.wrap_tool
        def get_count() -> int:
            return 42

        result = get_count()
        assert result == 42

    def test_server_tool_output_governance(self):
        """Test server governs tool output."""
        server = TorkMCPServer()

        @server.tool("get_email", "Get user email")
        def get_email() -> str:
            return f"Email: {PII_SAMPLES['email']}"

        import asyncio
        result = asyncio.run(
            server.call_tool("get_email", {})
        )
        assert PII_SAMPLES["email"] not in result["content"]

    def test_server_tool_error_handling(self):
        """Test server handles tool errors."""
        server = TorkMCPServer()

        @server.tool("failing_tool", "A tool that fails")
        def failing_tool() -> str:
            raise ValueError("Something went wrong")

        import asyncio
        result = asyncio.run(
            server.call_tool("failing_tool", {})
        )
        assert result["isError"] is True


class TestMCPResourceGovernance:
    """Test resource governance via middleware."""

    def test_middleware_govern_request(self):
        """Test middleware governs request."""
        middleware = TorkMCPMiddleware()
        request = {
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": PII_MESSAGES["email_message"]}
            }
        }
        result = middleware.govern_request(request)
        assert PII_SAMPLES["email"] not in result["params"]["arguments"]["query"]

    def test_middleware_govern_response(self):
        """Test middleware governs response."""
        middleware = TorkMCPMiddleware()
        response = {
            "result": f"Found: {PII_SAMPLES['ssn']}"
        }
        result = middleware.govern_response(response)
        assert PII_SAMPLES["ssn"] not in result["result"]

    def test_middleware_govern_response_dict_content(self):
        """Test middleware governs response with dict content."""
        middleware = TorkMCPMiddleware()
        response = {
            "result": {"content": f"Data: {PII_SAMPLES['phone_us']}"}
        }
        result = middleware.govern_response(response)
        assert PII_SAMPLES["phone_us"] not in result["result"]["content"]

    def test_middleware_preserves_request_structure(self):
        """Test middleware preserves request structure."""
        middleware = TorkMCPMiddleware()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "test",
                "arguments": {"key": "value"}
            }
        }
        result = middleware.govern_request(request)
        assert result["jsonrpc"] == "2.0"
        assert result["id"] == 1
        assert result["method"] == "tools/call"


class TestMCPPromptGovernance:
    """Test prompt governance."""

    def test_govern_prompt_with_pii(self):
        """Test governance of prompts containing PII."""
        wrapper = TorkMCPToolWrapper()
        prompt = f"User asked: {PII_MESSAGES['mixed_message']}"
        result = wrapper.govern(prompt)
        assert PII_SAMPLES["email"] not in result
        assert PII_SAMPLES["phone_us"] not in result

    def test_govern_system_prompt(self):
        """Test governance of system prompts."""
        wrapper = TorkMCPToolWrapper()
        system_prompt = f"You help users. Contact: {PII_SAMPLES['email']}"
        result = wrapper.govern(system_prompt)
        assert PII_SAMPLES["email"] not in result

    def test_govern_user_prompt(self):
        """Test governance of user prompts."""
        wrapper = TorkMCPToolWrapper()
        user_prompt = f"My SSN is {PII_SAMPLES['ssn']}, help me file taxes"
        result = wrapper.govern(user_prompt)
        assert PII_SAMPLES["ssn"] not in result

    def test_govern_assistant_response(self):
        """Test governance of assistant responses."""
        wrapper = TorkMCPToolWrapper()
        response = f"I found your card ending in {PII_SAMPLES['credit_card'][-4:]}"
        # Note: partial card numbers may not trigger full redaction
        result = wrapper.govern(response)
        assert result is not None


class TestMCPServerRegistrationGovernance:
    """Test server registration and tool management."""

    def test_register_tool_via_decorator(self):
        """Test registering tool via decorator."""
        server = TorkMCPServer()

        @server.tool("my_tool", "My tool description")
        def my_tool(arg: str) -> str:
            return arg

        assert "my_tool" in server.tools
        assert server.tool_schemas["my_tool"]["name"] == "my_tool"

    def test_list_tools(self):
        """Test listing registered tools."""
        server = TorkMCPServer()

        @server.tool("tool1", "First tool")
        def tool1() -> str:
            return "1"

        @server.tool("tool2", "Second tool")
        def tool2() -> str:
            return "2"

        tools = server.list_tools()
        assert len(tools) == 2
        names = [t["name"] for t in tools]
        assert "tool1" in names
        assert "tool2" in names

    def test_tool_schema_includes_description(self):
        """Test tool schema includes description."""
        server = TorkMCPServer()

        @server.tool("documented_tool", "This is a well documented tool")
        def documented_tool() -> str:
            return "done"

        schema = server.tool_schemas["documented_tool"]
        assert schema["description"] == "This is a well documented tool"

    def test_multiple_tools_governed_independently(self):
        """Test multiple tools are governed independently."""
        server = TorkMCPServer()

        @server.tool("tool_a", "Tool A")
        def tool_a(data: str) -> str:
            return f"A: {data}"

        @server.tool("tool_b", "Tool B")
        def tool_b(data: str) -> str:
            return f"B: {data}"

        import asyncio

        async def run_tools():
            result_a = await server.call_tool("tool_a", {"data": PII_MESSAGES["email_message"]})
            result_b = await server.call_tool("tool_b", {"data": PII_MESSAGES["ssn_message"]})
            return result_a, result_b

        result_a, result_b = asyncio.run(run_tools())

        assert PII_SAMPLES["email"] not in result_a["content"]
        assert PII_SAMPLES["ssn"] not in result_b["content"]


class TestMCPEdgeCases:
    """Test edge cases for MCP adapter."""

    def test_empty_tool_arguments(self):
        """Test tool with empty arguments."""
        wrapper = TorkMCPToolWrapper()
        result = wrapper.govern_tool_input({})
        assert result == {}

    def test_nested_arguments(self):
        """Test tool with nested arguments (only top level governed)."""
        wrapper = TorkMCPToolWrapper()
        result = wrapper.govern_tool_input({
            "simple": "text",
            "nested": {"inner": "value"}  # Non-string, passed through
        })
        assert result["simple"] == "text"
        assert result["nested"]["inner"] == "value"

    def test_tool_with_none_output(self):
        """Test tool returning None."""
        wrapper = TorkMCPToolWrapper()

        @wrapper.wrap_tool
        def returns_none() -> None:
            return None

        result = returns_none()
        assert result is None

    def test_middleware_no_params(self):
        """Test middleware with request without params."""
        middleware = TorkMCPMiddleware()
        request = {"method": "ping"}
        result = middleware.govern_request(request)
        assert result == request
