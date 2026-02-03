"""
Tests for Dify adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Workflow node governance
- API hook governance
- App governance
- Chat governance
- Decorator governance
"""

import pytest
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.dify import (
    TorkDifyNode,
    TorkDifyHook,
    TorkDifyApp,
    dify_governed,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestDifyImportInstantiation:
    """Test import and instantiation of Dify adapter."""

    def test_import_node(self):
        """Test TorkDifyNode can be imported."""
        assert TorkDifyNode is not None

    def test_import_hook(self):
        """Test TorkDifyHook can be imported."""
        assert TorkDifyHook is not None

    def test_import_app(self):
        """Test TorkDifyApp can be imported."""
        assert TorkDifyApp is not None

    def test_import_decorator(self):
        """Test dify_governed decorator can be imported."""
        assert dify_governed is not None

    def test_instantiate_node_default(self):
        """Test node instantiation with defaults."""
        node = TorkDifyNode()
        assert node is not None
        assert node.tork is not None
        assert node.input_field == "query"
        assert node.output_field == "governed_text"

    def test_instantiate_hook_default(self):
        """Test hook instantiation with defaults."""
        hook = TorkDifyHook()
        assert hook is not None
        assert hook.tork is not None
        assert hook.govern_request is True
        assert hook.govern_response is True

    def test_instantiate_app(self):
        """Test app instantiation."""
        app = TorkDifyApp(app_id="test-app")
        assert app is not None
        assert app.tork is not None
        assert app.app_id == "test-app"


class TestDifyConfiguration:
    """Test configuration of Dify adapter."""

    def test_node_with_api_key(self):
        """Test node with API key."""
        node = TorkDifyNode(api_key="test-key")
        assert node.tork is not None

    def test_node_custom_fields(self):
        """Test node with custom input/output fields."""
        node = TorkDifyNode(input_field="text", output_field="result")
        assert node.input_field == "text"
        assert node.output_field == "result"

    def test_hook_with_webhook_url(self):
        """Test hook with webhook URL."""
        hook = TorkDifyHook(webhook_url="https://api.dify.ai/webhook")
        assert hook.webhook_url == "https://api.dify.ai/webhook"

    def test_hook_govern_options(self):
        """Test hook govern options."""
        hook = TorkDifyHook(govern_request=False, govern_response=True)
        assert hook.govern_request is False
        assert hook.govern_response is True

    def test_app_with_dify_config(self):
        """Test app with Dify configuration."""
        app = TorkDifyApp(
            app_id="test-app",
            dify_api_key="dify-key",
            dify_base_url="https://custom.dify.ai/v1"
        )
        assert app.dify_api_key == "dify-key"
        assert app.dify_base_url == "https://custom.dify.ai/v1"


class TestDifyPIIDetection:
    """Test PII detection and redaction in Dify adapter."""

    def test_node_govern_email_pii(self):
        """Test node detects and redacts email PII."""
        node = TorkDifyNode()
        result = node.process({"query": PII_MESSAGES["email_message"]})
        assert PII_SAMPLES["email"] not in result["governed_text"]
        assert "[EMAIL_REDACTED]" in result["governed_text"]

    def test_node_govern_phone_pii(self):
        """Test node detects and redacts phone PII."""
        node = TorkDifyNode()
        result = node.process({"query": PII_MESSAGES["phone_message"]})
        assert PII_SAMPLES["phone_us"] not in result["governed_text"]
        assert "[PHONE_REDACTED]" in result["governed_text"]

    def test_node_govern_ssn_pii(self):
        """Test node detects and redacts SSN PII."""
        node = TorkDifyNode()
        result = node.process({"query": PII_MESSAGES["ssn_message"]})
        assert PII_SAMPLES["ssn"] not in result["governed_text"]
        assert "[SSN_REDACTED]" in result["governed_text"]

    def test_node_govern_credit_card_pii(self):
        """Test node detects and redacts credit card PII."""
        node = TorkDifyNode()
        result = node.process({"query": PII_MESSAGES["credit_card_message"]})
        assert PII_SAMPLES["credit_card"] not in result["governed_text"]
        assert "[CARD_REDACTED]" in result["governed_text"]

    def test_node_govern_clean_text(self):
        """Test node passes through clean text unchanged."""
        node = TorkDifyNode()
        clean_text = "What is the weather today?"
        result = node.process({"query": clean_text})
        assert result["governed_text"] == clean_text


class TestDifyErrorHandling:
    """Test error handling in Dify adapter."""

    def test_node_empty_string(self):
        """Test node handles empty string."""
        node = TorkDifyNode()
        result = node.process({"query": ""})
        assert result["governed_text"] == ""
        assert result["tork_action"] == "skip"

    def test_node_missing_input(self):
        """Test node handles missing input field."""
        node = TorkDifyNode()
        result = node.process({})
        assert result["governed_text"] == ""
        assert result["tork_action"] == "skip"

    def test_node_non_string_input(self):
        """Test node handles non-string input."""
        node = TorkDifyNode()
        result = node.process({"query": 123})
        assert result["tork_action"] == "skip"

    def test_hook_empty_message(self):
        """Test hook handles empty message."""
        hook = TorkDifyHook()
        result = hook.govern_chat_message({})
        assert result == {}

    def test_hook_missing_content(self):
        """Test hook handles message without content."""
        hook = TorkDifyHook()
        message = {"role": "user"}
        result = hook.govern_chat_message(message)
        assert "role" in result


class TestDifyComplianceReceipts:
    """Test compliance receipt generation in Dify adapter."""

    def test_node_includes_receipt(self):
        """Test node includes receipt in output."""
        node = TorkDifyNode(include_receipt=True)
        result = node.process({"query": "Test message"})
        assert "tork_receipt_id" in result
        assert "tork_timestamp" in result

    def test_node_receipt_disabled(self):
        """Test node can disable receipts."""
        node = TorkDifyNode(include_receipt=False)
        result = node.process({"query": "Test message"})
        assert "tork_receipt_id" not in result

    def test_app_tracks_receipts(self):
        """Test app tracks receipt IDs."""
        app = TorkDifyApp(app_id="test-app")
        app.chat(query="Test query")
        assert len(app.receipts) >= 1


class TestDifyWorkflowNodeGovernance:
    """Test workflow node governance."""

    def test_node_process_returns_governed_text(self):
        """Test node process returns governed text."""
        node = TorkDifyNode()
        result = node.process({"query": PII_MESSAGES["email_message"]})
        assert "governed_text" in result
        assert PII_SAMPLES["email"] not in result["governed_text"]

    def test_node_process_includes_action(self):
        """Test node process includes action taken."""
        node = TorkDifyNode()
        result = node.process({"query": PII_MESSAGES["ssn_message"]})
        assert "tork_action" in result
        assert result["tork_action"] == "redact"

    def test_node_process_includes_pii_types(self):
        """Test node process includes PII types found."""
        node = TorkDifyNode()
        result = node.process({"query": PII_MESSAGES["phone_message"]})
        assert "tork_pii_types" in result
        assert len(result["tork_pii_types"]) >= 1

    def test_node_get_schema(self):
        """Test node schema generation."""
        node = TorkDifyNode()
        schema = node.get_schema()
        assert schema["type"] == "tork-governance"
        assert "inputs" in schema
        assert "outputs" in schema

    def test_node_custom_field_names(self):
        """Test node with custom field names."""
        node = TorkDifyNode(input_field="text", output_field="clean_text")
        result = node.process({"text": PII_MESSAGES["email_message"]})
        assert "clean_text" in result
        assert PII_SAMPLES["email"] not in result["clean_text"]


class TestDifyAPIHookGovernance:
    """Test API hook governance."""

    def test_hook_govern_chat_message(self):
        """Test hook governs chat message content."""
        hook = TorkDifyHook()
        message = {"content": PII_MESSAGES["email_message"]}
        result = hook.govern_chat_message(message)
        assert PII_SAMPLES["email"] not in result["content"]
        assert "_tork" in result

    def test_hook_govern_chat_query(self):
        """Test hook governs chat query field."""
        hook = TorkDifyHook()
        message = {"query": PII_MESSAGES["phone_message"]}
        result = hook.govern_chat_message(message)
        assert PII_SAMPLES["phone_us"] not in result["query"]

    def test_hook_govern_completion_request(self):
        """Test hook governs completion request."""
        hook = TorkDifyHook()
        request = {
            "query": PII_MESSAGES["ssn_message"],
            "inputs": {"context": PII_MESSAGES["email_message"]}
        }
        result = hook.govern_completion_request(request)
        assert PII_SAMPLES["ssn"] not in result["query"]
        assert PII_SAMPLES["email"] not in result["inputs"]["context"]

    def test_hook_govern_completion_response(self):
        """Test hook governs completion response."""
        hook = TorkDifyHook()
        response = {"answer": PII_MESSAGES["credit_card_message"]}
        result = hook.govern_completion_response(response)
        assert PII_SAMPLES["credit_card"] not in result["answer"]
        assert "_tork_receipt_id" in result

    def test_hook_preserves_non_string_inputs(self):
        """Test hook preserves non-string inputs."""
        hook = TorkDifyHook()
        request = {
            "query": "test",
            "inputs": {"count": 5, "active": True}
        }
        result = hook.govern_completion_request(request)
        assert result["inputs"]["count"] == 5
        assert result["inputs"]["active"] is True


class TestDifyAppGovernance:
    """Test Dify app wrapper governance."""

    def test_app_chat_governs_query(self):
        """Test app chat governs query."""
        app = TorkDifyApp(app_id="test-app")
        result = app.chat(query=PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result["query"]

    def test_app_chat_governs_inputs(self):
        """Test app chat governs inputs."""
        app = TorkDifyApp(app_id="test-app")
        result = app.chat(
            query="test",
            inputs={"context": PII_MESSAGES["ssn_message"]}
        )
        assert PII_SAMPLES["ssn"] not in result["inputs"]["context"]

    def test_app_chat_includes_governance_metadata(self):
        """Test app chat includes governance metadata."""
        app = TorkDifyApp(app_id="test-app")
        result = app.chat(query="test")
        assert "_tork_governance" in result
        assert "query_action" in result["_tork_governance"]

    def test_app_receipts_accumulate(self):
        """Test app receipts accumulate across calls."""
        app = TorkDifyApp(app_id="test-app")
        app.chat(query="First query")
        app.chat(query="Second query")
        assert len(app.receipts) >= 2

    def test_app_preserves_user_and_conversation(self):
        """Test app preserves user and conversation ID."""
        app = TorkDifyApp(app_id="test-app")
        result = app.chat(
            query="test",
            user="user123",
            conversation_id="conv456"
        )
        assert result["user"] == "user123"
        assert result["conversation_id"] == "conv456"


class TestDifyDecoratorGovernance:
    """Test dify_governed decorator."""

    def test_decorator_governs_input(self):
        """Test decorator governs function input."""
        @dify_governed()
        def process(text: str) -> str:
            return text

        result = process(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_decorator_governs_output(self):
        """Test decorator governs function output."""
        @dify_governed()
        def generate() -> str:
            return PII_MESSAGES["phone_message"]

        result = generate()
        assert PII_SAMPLES["phone_us"] not in result

    def test_decorator_input_only(self):
        """Test decorator with input governance only."""
        @dify_governed(govern_inputs=True, govern_outputs=False)
        def process(text: str) -> str:
            return PII_MESSAGES["ssn_message"]

        result = process("clean input")
        # Output should NOT be governed
        assert PII_SAMPLES["ssn"] in result

    def test_decorator_output_only(self):
        """Test decorator with output governance only."""
        @dify_governed(govern_inputs=False, govern_outputs=True)
        def process(text: str) -> str:
            return text

        # Input should pass through, but if returned it gets governed
        result = process("clean text")
        assert result == "clean text"

    def test_decorator_preserves_function_name(self):
        """Test decorator preserves function name."""
        @dify_governed()
        def my_function(text: str) -> str:
            return text

        assert my_function.__name__ == "my_function"

    def test_decorator_with_kwargs(self):
        """Test decorator with keyword arguments."""
        @dify_governed()
        def process(text: str, prefix: str = "") -> str:
            return f"{prefix}{text}"

        result = process(text="clean", prefix=PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
