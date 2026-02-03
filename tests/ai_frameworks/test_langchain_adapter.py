"""
Tests for LangChain adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Chain wrapping
- Callback integration
- Streaming governance
"""

import pytest
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.langchain import (
    TorkCallbackHandler,
    TorkGovernedChain,
    create_governed_chain,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestLangChainImportInstantiation:
    """Test import and instantiation of LangChain adapter."""

    def test_import_callback_handler(self):
        """Test TorkCallbackHandler can be imported."""
        assert TorkCallbackHandler is not None

    def test_import_governed_chain(self):
        """Test TorkGovernedChain can be imported."""
        assert TorkGovernedChain is not None

    def test_instantiate_callback_handler_default(self):
        """Test callback handler instantiation with defaults."""
        handler = TorkCallbackHandler()
        assert handler is not None
        assert handler.tork is not None
        assert handler.block_on_pii is False
        assert handler.receipts == []

    def test_instantiate_governed_chain_default(self):
        """Test governed chain instantiation with defaults."""
        chain = TorkGovernedChain()
        assert chain is not None
        assert chain.tork is not None
        assert chain.last_result is None


class TestLangChainConfiguration:
    """Test configuration of LangChain adapter."""

    def test_callback_handler_with_policy_version(self):
        """Test callback handler with custom policy version."""
        handler = TorkCallbackHandler(policy_version="2.0.0")
        assert handler.tork is not None

    def test_callback_handler_block_on_pii(self):
        """Test callback handler with block_on_pii enabled."""
        handler = TorkCallbackHandler(block_on_pii=True)
        assert handler.block_on_pii is True

    def test_callback_handler_with_tork_instance(self, tork_instance):
        """Test callback handler with existing Tork instance."""
        handler = TorkCallbackHandler(tork=tork_instance)
        assert handler.tork is tork_instance

    def test_governed_chain_with_policy_version(self):
        """Test governed chain with custom policy version."""
        chain = TorkGovernedChain(policy_version="2.0.0")
        assert chain.tork is not None


class TestLangChainPIIDetection:
    """Test PII detection and redaction in LangChain adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        chain = TorkGovernedChain()
        result = chain.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        chain = TorkGovernedChain()
        result = chain.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        chain = TorkGovernedChain()
        result = chain.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        chain = TorkGovernedChain()
        result = chain.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        chain = TorkGovernedChain()
        clean_text = "Hello, how can I help you today?"
        result = chain.govern(clean_text)
        assert result == clean_text

    def test_govern_mixed_pii(self):
        """Test multiple PII types in same text."""
        chain = TorkGovernedChain()
        result = chain.govern(PII_MESSAGES["mixed_message"])
        assert PII_SAMPLES["email"] not in result
        assert PII_SAMPLES["phone_us"] not in result


class TestLangChainErrorHandling:
    """Test error handling in LangChain adapter."""

    def test_callback_handler_empty_prompts(self):
        """Test callback handler handles empty prompts."""
        handler = TorkCallbackHandler()
        prompts = []
        handler.on_llm_start({}, prompts)
        assert len(handler.receipts) == 0

    def test_callback_handler_none_serialized(self):
        """Test callback handler handles None serialized dict."""
        handler = TorkCallbackHandler()
        prompts = ["Hello"]
        # Should not raise
        handler.on_llm_start({}, prompts)
        assert len(handler.receipts) == 1

    def test_governed_chain_empty_string(self):
        """Test governed chain handles empty string."""
        chain = TorkGovernedChain()
        result = chain.govern("")
        assert result == ""

    def test_governed_chain_whitespace_only(self):
        """Test governed chain handles whitespace-only string."""
        chain = TorkGovernedChain()
        result = chain.govern("   ")
        assert result == "   "


class TestLangChainComplianceReceipts:
    """Test compliance receipt generation in LangChain adapter."""

    def test_callback_handler_generates_receipts(self):
        """Test callback handler generates receipts on LLM start."""
        handler = TorkCallbackHandler()
        prompts = ["Hello, world"]
        handler.on_llm_start({}, prompts)
        assert len(handler.receipts) == 1
        assert handler.receipts[0]["type"] == "input"
        assert "receipt" in handler.receipts[0]
        assert "action" in handler.receipts[0]

    def test_callback_handler_receipt_has_id(self):
        """Test receipt has a unique ID."""
        handler = TorkCallbackHandler()
        prompts = ["Test message"]
        handler.on_llm_start({}, prompts)
        receipt = handler.receipts[0]["receipt"]
        assert receipt.receipt_id.startswith("rcpt_")

    def test_clear_receipts(self):
        """Test clearing receipts."""
        handler = TorkCallbackHandler()
        prompts = ["Test"]
        handler.on_llm_start({}, prompts)
        assert len(handler.receipts) == 1
        handler.clear_receipts()
        assert len(handler.receipts) == 0

    def test_governed_chain_stores_last_result(self):
        """Test governed chain stores last governance result."""
        chain = TorkGovernedChain()
        chain.govern("Test message")
        assert chain.last_result is not None
        assert hasattr(chain.last_result, "receipt")


class TestLangChainChainWrapping:
    """Test chain wrapping functionality."""

    def test_create_governed_chain_factory(self):
        """Test factory function creates governed chain."""
        # Create a mock chain
        class MockChain:
            def invoke(self, inputs, **kwargs):
                return "Mock response"

        chain = create_governed_chain(MockChain())
        assert isinstance(chain, TorkGovernedChain)

    def test_governed_chain_invoke_dict_input(self):
        """Test governed chain invoke with dict input."""
        class MockChain:
            def invoke(self, inputs, **kwargs):
                return f"Response to: {inputs.get('question', '')}"

        chain = TorkGovernedChain(chain=MockChain())
        result = chain.invoke({"question": "What is AI?"})
        assert "Response to" in result

    def test_governed_chain_invoke_string_input(self):
        """Test governed chain invoke with string input."""
        class MockChain:
            def invoke(self, inputs, **kwargs):
                return f"Response: {inputs}"

        chain = TorkGovernedChain(chain=MockChain())
        result = chain.invoke("Hello")
        assert "Response" in result

    def test_governed_chain_invoke_governs_pii_input(self):
        """Test invoke governs PII in input."""
        class MockChain:
            def invoke(self, inputs, **kwargs):
                # Return the input to verify it was governed
                return f"Got: {inputs.get('data', '')}"

        chain = TorkGovernedChain(chain=MockChain())
        result = chain.invoke({"data": f"Email: {PII_SAMPLES['email']}"})
        assert PII_SAMPLES["email"] not in result


class TestLangChainCallbackIntegration:
    """Test callback handler integration."""

    def test_on_tool_start_governance(self):
        """Test tool start governance."""
        handler = TorkCallbackHandler()
        handler.on_tool_start({}, f"Search for: {PII_SAMPLES['email']}")
        assert len(handler.receipts) == 1
        assert handler.receipts[0]["type"] == "tool_input"

    def test_on_tool_end_governance(self):
        """Test tool end governance."""
        handler = TorkCallbackHandler()
        handler.on_tool_end(f"Found email: {PII_SAMPLES['email']}")
        assert len(handler.receipts) == 1
        assert handler.receipts[0]["type"] == "tool_output"

    def test_on_chain_start_called(self):
        """Test on_chain_start is callable."""
        handler = TorkCallbackHandler()
        # Should not raise
        handler.on_chain_start({}, {"input": "test"})

    def test_on_chain_end_called(self):
        """Test on_chain_end is callable."""
        handler = TorkCallbackHandler()
        # Should not raise
        handler.on_chain_end({"output": "test"})


class TestLangChainStreamingGovernance:
    """Test streaming governance functionality."""

    def test_govern_input_method(self):
        """Test standalone govern_input method."""
        chain = TorkGovernedChain()
        result = chain.govern_input(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_govern_output_method(self):
        """Test standalone govern_output method."""
        chain = TorkGovernedChain()
        result = chain.govern_output(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result

    def test_govern_alias(self):
        """Test govern method is alias for govern_input."""
        chain = TorkGovernedChain()
        input_result = chain.govern_input("test")
        alias_result = chain.govern("test")
        assert input_result == alias_result

    def test_multiple_govern_calls(self):
        """Test multiple govern calls maintain state."""
        chain = TorkGovernedChain()
        chain.govern("First message")
        first_result = chain.last_result
        chain.govern("Second message")
        second_result = chain.last_result
        assert first_result is not second_result
