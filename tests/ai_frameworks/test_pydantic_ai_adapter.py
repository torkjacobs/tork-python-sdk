"""
Tests for Pydantic AI adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Model input governance
- Model output governance
- Validation governance
- Structured output governance
- Async governance
"""

import pytest
import asyncio
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.pydantic_ai import (
    TorkPydanticAIMiddleware,
    TorkPydanticAITool,
    TorkAgentDependency,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestPydanticAIImportInstantiation:
    """Test import and instantiation of Pydantic AI adapter."""

    def test_import_middleware(self):
        """Test TorkPydanticAIMiddleware can be imported."""
        assert TorkPydanticAIMiddleware is not None

    def test_import_tool(self):
        """Test TorkPydanticAITool can be imported."""
        assert TorkPydanticAITool is not None

    def test_import_dependency(self):
        """Test TorkAgentDependency can be imported."""
        assert TorkAgentDependency is not None

    def test_instantiate_middleware_default(self):
        """Test middleware instantiation with defaults."""
        middleware = TorkPydanticAIMiddleware()
        assert middleware is not None
        assert middleware.tork is not None
        assert middleware.receipts == []

    def test_instantiate_tool_default(self):
        """Test tool instantiation with defaults."""
        tool = TorkPydanticAITool()
        assert tool is not None
        assert tool.tork is not None


class TestPydanticAIConfiguration:
    """Test configuration of Pydantic AI adapter."""

    def test_middleware_with_tork_instance(self, tork_instance):
        """Test middleware with existing Tork instance."""
        middleware = TorkPydanticAIMiddleware(tork=tork_instance)
        assert middleware.tork is tork_instance

    def test_tool_with_tork_instance(self, tork_instance):
        """Test tool with existing Tork instance."""
        tool = TorkPydanticAITool(tork=tork_instance)
        assert tool.tork is tork_instance

    def test_dependency_with_tork_instance(self, tork_instance):
        """Test dependency with existing Tork instance."""
        dep = TorkAgentDependency(tork=tork_instance)
        assert dep.tork is tork_instance

    def test_middleware_with_api_key(self):
        """Test middleware with API key."""
        middleware = TorkPydanticAIMiddleware(api_key="test-key")
        assert middleware.tork is not None


class TestPydanticAIPIIDetection:
    """Test PII detection and redaction in Pydantic AI adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        dep = TorkAgentDependency()
        result = dep.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        dep = TorkAgentDependency()
        result = dep.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        dep = TorkAgentDependency()
        result = dep.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        dep = TorkAgentDependency()
        result = dep.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        dep = TorkAgentDependency()
        clean_text = "What is the weather?"
        result = dep.govern(clean_text)
        assert result == clean_text


class TestPydanticAIErrorHandling:
    """Test error handling in Pydantic AI adapter."""

    def test_dependency_empty_string(self):
        """Test dependency handles empty string."""
        dep = TorkAgentDependency()
        result = dep.govern("")
        assert result == ""

    def test_dependency_whitespace(self):
        """Test dependency handles whitespace."""
        dep = TorkAgentDependency()
        result = dep.govern("   ")
        assert result == "   "

    def test_tool_empty_receipts(self):
        """Test tool starts with empty receipts."""
        tool = TorkPydanticAITool()
        assert tool.get_receipts() == []

    def test_dependency_check_pii_false(self):
        """Test check_pii returns False for clean text."""
        dep = TorkAgentDependency()
        assert dep.check_pii("Hello world") is False


class TestPydanticAIComplianceReceipts:
    """Test compliance receipt generation in Pydantic AI adapter."""

    def test_dependency_govern_generates_receipt(self):
        """Test dependency govern generates receipt."""
        dep = TorkAgentDependency()
        dep.govern("Test message")
        assert len(dep.receipts) == 1
        assert dep.receipts[0]["type"] == "dependency_govern"
        assert "receipt_id" in dep.receipts[0]

    def test_middleware_get_receipts(self):
        """Test middleware get_receipts method."""
        middleware = TorkPydanticAIMiddleware()
        receipts = middleware.get_receipts()
        assert isinstance(receipts, list)

    def test_tool_get_receipts(self):
        """Test tool get_receipts method."""
        tool = TorkPydanticAITool()
        receipts = tool.get_receipts()
        assert isinstance(receipts, list)


class TestPydanticAIModelInputGovernance:
    """Test model input governance."""

    def test_tool_governs_input_kwargs(self):
        """Test tool governs input keyword arguments."""
        tool = TorkPydanticAITool()

        @tool.governed_tool
        def process(data: str) -> str:
            return f"Processed: {data}"

        result = process(data=PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert len(tool.receipts) >= 1

    def test_tool_receipt_has_argument_name(self):
        """Test tool receipt includes argument name."""
        tool = TorkPydanticAITool()

        @tool.governed_tool
        def search(query: str) -> str:
            return query

        search(query="test")
        assert tool.receipts[0]["argument"] == "query"

    def test_dependency_check_pii_true(self):
        """Test check_pii returns True for PII text."""
        dep = TorkAgentDependency()
        assert dep.check_pii(PII_MESSAGES["email_message"]) is True

    def test_dependency_get_result(self):
        """Test get_result returns full governance result."""
        dep = TorkAgentDependency()
        result = dep.get_result("test")
        assert hasattr(result, "action")
        assert hasattr(result, "output")
        assert hasattr(result, "pii")
        assert hasattr(result, "receipt")


class TestPydanticAIModelOutputGovernance:
    """Test model output governance."""

    def test_tool_governs_output(self):
        """Test tool governs output."""
        tool = TorkPydanticAITool()

        @tool.governed_tool
        def get_email() -> str:
            return PII_MESSAGES["email_message"]

        result = get_email()
        assert PII_SAMPLES["email"] not in result

    def test_tool_non_string_output(self):
        """Test tool handles non-string output."""
        tool = TorkPydanticAITool()

        @tool.governed_tool
        def get_count() -> int:
            return 42

        result = get_count()
        assert result == 42

    def test_tool_output_receipt(self):
        """Test tool generates output receipt."""
        tool = TorkPydanticAITool()

        @tool.governed_tool
        def respond() -> str:
            return "Response with SSN"

        respond()
        # Should have input (none) and output receipts
        assert any(r["type"] == "tool_output" for r in tool.receipts)

    def test_dependency_govern_for_output(self):
        """Test dependency can govern output."""
        dep = TorkAgentDependency()
        output = dep.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in output


class TestPydanticAIValidationGovernance:
    """Test validation governance."""

    def test_dependency_receipt_has_pii_flag(self):
        """Test dependency receipt includes has_pii flag."""
        dep = TorkAgentDependency()
        dep.govern(PII_MESSAGES["email_message"])
        assert dep.receipts[0]["has_pii"] is True

    def test_dependency_clean_text_no_pii(self):
        """Test dependency marks clean text correctly."""
        dep = TorkAgentDependency()
        dep.govern("Clean text")
        assert dep.receipts[0]["has_pii"] is False

    def test_tool_validates_multiple_args(self):
        """Test tool validates multiple arguments."""
        tool = TorkPydanticAITool()

        @tool.governed_tool
        def process(name: str, email: str) -> str:
            return f"{name}: {email}"

        result = process(
            name="John",
            email=PII_MESSAGES["email_message"]
        )
        # Should have receipts for both args
        assert len(tool.receipts) >= 2

    def test_tool_non_string_args_passed_through(self):
        """Test tool passes through non-string args."""
        tool = TorkPydanticAITool()

        @tool.governed_tool
        def calc(x: int, y: int) -> int:
            return x + y

        result = calc(x=5, y=3)
        assert result == 8


class TestPydanticAIStructuredOutputGovernance:
    """Test structured output governance."""

    def test_tool_dict_output_not_governed(self):
        """Test tool doesn't modify dict output (not string)."""
        tool = TorkPydanticAITool()

        @tool.governed_tool
        def get_data() -> dict:
            return {"key": "value"}

        result = get_data()
        assert result == {"key": "value"}

    def test_dependency_govern_structured_field(self):
        """Test dependency can govern structured output fields."""
        dep = TorkAgentDependency()

        # Simulate governing a structured output field
        data = {
            "name": dep.govern("John Doe"),
            "email": dep.govern(PII_SAMPLES["email"]),
            "bio": dep.govern("Clean bio text")
        }

        assert data["name"] == "John Doe"
        assert PII_SAMPLES["email"] not in data["email"]
        assert data["bio"] == "Clean bio text"

    def test_tool_list_output_not_governed(self):
        """Test tool doesn't modify list output."""
        tool = TorkPydanticAITool()

        @tool.governed_tool
        def get_items() -> list:
            return ["a", "b", "c"]

        result = get_items()
        assert result == ["a", "b", "c"]

    def test_dependency_multiple_fields(self):
        """Test dependency governs multiple fields."""
        dep = TorkAgentDependency()
        fields = [
            PII_MESSAGES["email_message"],
            PII_MESSAGES["phone_message"],
            "Clean field"
        ]
        governed = [dep.govern(f) for f in fields]

        assert PII_SAMPLES["email"] not in governed[0]
        assert PII_SAMPLES["phone_us"] not in governed[1]
        assert governed[2] == "Clean field"
        assert len(dep.receipts) == 3


class TestPydanticAIAsyncGovernance:
    """Test async governance."""

    @pytest.mark.asyncio
    async def test_middleware_wrap_agent(self):
        """Test middleware can wrap agent."""
        middleware = TorkPydanticAIMiddleware()

        class MockResult:
            data = "test response"

        class MockAgent:
            async def run(self, prompt, *args, **kwargs):
                return MockResult()

        agent = MockAgent()
        wrapped = middleware.wrap_agent(agent)
        result = await wrapped.run("test prompt")
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_middleware_governs_async_input(self):
        """Test middleware governs async input."""
        middleware = TorkPydanticAIMiddleware()

        class MockResult:
            data = "response"

        class MockAgent:
            async def run(self, prompt, *args, **kwargs):
                return MockResult()

        agent = MockAgent()
        wrapped = middleware.wrap_agent(agent)
        await wrapped.run(PII_MESSAGES["email_message"])

        assert len(middleware.receipts) >= 1
        assert middleware.receipts[0]["type"] == "agent_input"

    @pytest.mark.asyncio
    async def test_middleware_governs_async_output(self):
        """Test middleware governs async output."""
        middleware = TorkPydanticAIMiddleware()

        class MockResult:
            data = PII_MESSAGES["ssn_message"]

        class MockAgent:
            async def run(self, prompt, *args, **kwargs):
                return MockResult()

        agent = MockAgent()
        wrapped = middleware.wrap_agent(agent)
        result = await wrapped.run("Get SSN info")

        assert PII_SAMPLES["ssn"] not in result.data

    @pytest.mark.asyncio
    async def test_middleware_receipt_has_action(self):
        """Test middleware receipt includes action."""
        middleware = TorkPydanticAIMiddleware()

        class MockResult:
            data = "response"

        class MockAgent:
            async def run(self, prompt, *args, **kwargs):
                return MockResult()

        agent = MockAgent()
        wrapped = middleware.wrap_agent(agent)
        await wrapped.run(PII_MESSAGES["email_message"])

        assert "action" in middleware.receipts[0]
        assert "has_pii" in middleware.receipts[0]
