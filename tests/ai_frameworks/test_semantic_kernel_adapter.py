"""
Tests for Semantic Kernel adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Function governance
- Plugin governance
- Planner governance
- Memory governance
- Connector governance
"""

import pytest
import asyncio
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.semantic_kernel import (
    TorkSKFilter,
    TorkSKPlugin,
    TorkSKPromptFilter,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestSemanticKernelImportInstantiation:
    """Test import and instantiation of Semantic Kernel adapter."""

    def test_import_filter(self):
        """Test TorkSKFilter can be imported."""
        assert TorkSKFilter is not None

    def test_import_plugin(self):
        """Test TorkSKPlugin can be imported."""
        assert TorkSKPlugin is not None

    def test_import_prompt_filter(self):
        """Test TorkSKPromptFilter can be imported."""
        assert TorkSKPromptFilter is not None

    def test_instantiate_filter_default(self):
        """Test filter instantiation with defaults."""
        filter = TorkSKFilter()
        assert filter is not None
        assert filter.tork is not None
        assert filter.receipts == []

    def test_instantiate_plugin_default(self):
        """Test plugin instantiation with defaults."""
        plugin = TorkSKPlugin()
        assert plugin is not None
        assert plugin.tork is not None


class TestSemanticKernelConfiguration:
    """Test configuration of Semantic Kernel adapter."""

    def test_filter_with_tork_instance(self, tork_instance):
        """Test filter with existing Tork instance."""
        filter = TorkSKFilter(tork=tork_instance)
        assert filter.tork is tork_instance

    def test_plugin_with_tork_instance(self, tork_instance):
        """Test plugin with existing Tork instance."""
        plugin = TorkSKPlugin(tork=tork_instance)
        assert plugin.tork is tork_instance

    def test_filter_with_api_key(self):
        """Test filter with API key."""
        filter = TorkSKFilter(api_key="test-key")
        assert filter.tork is not None

    def test_prompt_filter_with_tork(self, tork_instance):
        """Test prompt filter with Tork instance."""
        filter = TorkSKPromptFilter(tork=tork_instance)
        assert filter.tork is tork_instance


class TestSemanticKernelPIIDetection:
    """Test PII detection and redaction in Semantic Kernel adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        plugin = TorkSKPlugin()
        result = plugin.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        plugin = TorkSKPlugin()
        result = plugin.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        plugin = TorkSKPlugin()
        result = plugin.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        plugin = TorkSKPlugin()
        result = plugin.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        plugin = TorkSKPlugin()
        clean_text = "What is the capital of France?"
        result = plugin.govern(clean_text)
        assert result == clean_text


class TestSemanticKernelErrorHandling:
    """Test error handling in Semantic Kernel adapter."""

    def test_plugin_empty_string(self):
        """Test plugin handles empty string."""
        plugin = TorkSKPlugin()
        result = plugin.govern("")
        assert result == ""

    def test_plugin_whitespace(self):
        """Test plugin handles whitespace."""
        plugin = TorkSKPlugin()
        result = plugin.govern("   ")
        assert result == "   "

    def test_filter_empty_receipts(self):
        """Test filter starts with empty receipts."""
        filter = TorkSKFilter()
        assert filter.get_receipts() == []

    def test_plugin_check_pii_false(self):
        """Test check_pii returns False for clean text."""
        plugin = TorkSKPlugin()
        assert plugin.check_pii("Hello world") is False


class TestSemanticKernelComplianceReceipts:
    """Test compliance receipt generation in Semantic Kernel adapter."""

    def test_plugin_govern_generates_receipt(self):
        """Test plugin govern generates receipt."""
        plugin = TorkSKPlugin()
        plugin.govern("Test message")
        assert len(plugin.receipts) == 1
        assert plugin.receipts[0]["type"] == "direct_govern"
        assert "receipt_id" in plugin.receipts[0]

    def test_filter_get_receipts(self):
        """Test filter get_receipts method."""
        filter = TorkSKFilter()
        receipts = filter.get_receipts()
        assert isinstance(receipts, list)

    def test_prompt_filter_get_receipts(self):
        """Test prompt filter get_receipts method."""
        filter = TorkSKPromptFilter()
        receipts = filter.receipts
        assert isinstance(receipts, list)


class TestSemanticKernelFunctionGovernance:
    """Test function governance."""

    @pytest.mark.asyncio
    async def test_filter_on_function_invocation(self):
        """Test filter governs function invocation."""
        filter = TorkSKFilter()

        class MockContext:
            arguments = {"input": PII_MESSAGES["email_message"]}

        context = await filter.on_function_invocation(MockContext())
        assert PII_SAMPLES["email"] not in context.arguments["input"]
        assert len(filter.receipts) == 1

    @pytest.mark.asyncio
    async def test_filter_on_function_result(self):
        """Test filter governs function result."""
        filter = TorkSKFilter()

        class MockContext:
            pass

        result = await filter.on_function_result(
            MockContext(),
            PII_MESSAGES["ssn_message"]
        )
        assert PII_SAMPLES["ssn"] not in result

    @pytest.mark.asyncio
    async def test_filter_non_string_arguments(self):
        """Test filter handles non-string arguments."""
        filter = TorkSKFilter()

        class MockContext:
            arguments = {"count": 42, "flag": True}

        context = await filter.on_function_invocation(MockContext())
        assert context.arguments["count"] == 42
        assert context.arguments["flag"] is True

    @pytest.mark.asyncio
    async def test_filter_non_string_result(self):
        """Test filter handles non-string result."""
        filter = TorkSKFilter()

        class MockContext:
            pass

        result = await filter.on_function_result(MockContext(), {"key": "value"})
        assert result == {"key": "value"}


class TestSemanticKernelPluginGovernance:
    """Test plugin governance."""

    @pytest.mark.asyncio
    async def test_governed_function_decorator(self):
        """Test governed_function decorator."""
        plugin = TorkSKPlugin()

        @plugin.governed_function
        async def my_function(input: str) -> str:
            return f"Processed: {input}"

        result = await my_function(input="test")
        assert result == "Processed: test"

    @pytest.mark.asyncio
    async def test_governed_function_governs_input(self):
        """Test governed_function governs input."""
        plugin = TorkSKPlugin()

        @plugin.governed_function
        async def process_email(email: str) -> str:
            return f"Got: {email}"

        result = await process_email(email=PII_MESSAGES["email_message"])
        # The input should be governed
        assert len(plugin.receipts) >= 1

    @pytest.mark.asyncio
    async def test_governed_function_governs_output(self):
        """Test governed_function governs output."""
        plugin = TorkSKPlugin()

        @plugin.governed_function
        async def get_ssn() -> str:
            return PII_MESSAGES["ssn_message"]

        result = await get_ssn()
        assert PII_SAMPLES["ssn"] not in result

    def test_plugin_check_pii(self):
        """Test check_pii method."""
        plugin = TorkSKPlugin()
        assert plugin.check_pii(PII_MESSAGES["email_message"]) is True
        assert plugin.check_pii("Hello world") is False


class TestSemanticKernelPlannerGovernance:
    """Test planner governance."""

    @pytest.mark.asyncio
    async def test_prompt_filter_on_prompt_render(self):
        """Test prompt filter governs rendered prompt."""
        filter = TorkSKPromptFilter()
        result = await filter.on_prompt_render(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert len(filter.receipts) == 1

    @pytest.mark.asyncio
    async def test_prompt_filter_clean_prompt(self):
        """Test prompt filter allows clean prompts."""
        filter = TorkSKPromptFilter()
        clean_prompt = "Create a plan to write a poem"
        result = await filter.on_prompt_render(clean_prompt)
        assert result == clean_prompt

    @pytest.mark.asyncio
    async def test_prompt_filter_receipt_type(self):
        """Test prompt filter receipt type."""
        filter = TorkSKPromptFilter()
        await filter.on_prompt_render("Test prompt")
        assert filter.receipts[0]["type"] == "prompt_render"


class TestSemanticKernelMemoryGovernance:
    """Test memory governance (using plugin govern method)."""

    def test_govern_memory_content(self):
        """Test governing memory content."""
        plugin = TorkSKPlugin()
        memory_content = f"User said: {PII_MESSAGES['phone_message']}"
        result = plugin.govern(memory_content)
        assert PII_SAMPLES["phone_us"] not in result

    def test_govern_memory_key_value(self):
        """Test governing memory key-value pairs."""
        plugin = TorkSKPlugin()
        governed_key = plugin.govern("user_email")
        governed_value = plugin.govern(PII_MESSAGES["email_message"])
        assert governed_key == "user_email"
        assert PII_SAMPLES["email"] not in governed_value

    def test_multiple_memory_items(self):
        """Test governing multiple memory items."""
        plugin = TorkSKPlugin()
        items = [
            PII_MESSAGES["email_message"],
            PII_MESSAGES["phone_message"],
            "Clean memory item"
        ]
        governed = [plugin.govern(item) for item in items]
        assert PII_SAMPLES["email"] not in governed[0]
        assert PII_SAMPLES["phone_us"] not in governed[1]
        assert governed[2] == "Clean memory item"


class TestSemanticKernelConnectorGovernance:
    """Test connector governance."""

    @pytest.mark.asyncio
    async def test_filter_governs_connector_input(self):
        """Test filter governs connector input."""
        filter = TorkSKFilter()

        class MockContext:
            arguments = {"prompt": PII_MESSAGES["credit_card_message"]}

        context = await filter.on_function_invocation(MockContext())
        assert PII_SAMPLES["credit_card"] not in context.arguments["prompt"]

    @pytest.mark.asyncio
    async def test_filter_governs_connector_output(self):
        """Test filter governs connector output."""
        filter = TorkSKFilter()

        class MockContext:
            pass

        result = await filter.on_function_result(
            MockContext(),
            PII_MESSAGES["ssn_message"]
        )
        assert PII_SAMPLES["ssn"] not in result

    def test_plugin_govern_connector_data(self):
        """Test plugin governs connector data."""
        plugin = TorkSKPlugin()
        connector_data = f"Retrieved: {PII_MESSAGES['mixed_message']}"
        result = plugin.govern(connector_data)
        assert PII_SAMPLES["email"] not in result
        assert PII_SAMPLES["phone_us"] not in result

    def test_filter_receipt_action(self):
        """Test filter receipt includes action."""
        async def run_test():
            filter = TorkSKFilter()

            class MockContext:
                arguments = {"data": PII_MESSAGES["email_message"]}

            await filter.on_function_invocation(MockContext())
            assert "action" in filter.receipts[0]

        asyncio.run(run_test())
