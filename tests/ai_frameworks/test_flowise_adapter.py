"""
Tests for Flowise adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Flow input governance
- Chatflow governance
- Node output governance
- Tool call governance
- API request governance
"""

import pytest
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.flowise import (
    TorkFlowiseNode,
    TorkFlowiseFlow,
    TorkFlowiseAPI,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestFlowiseImportInstantiation:
    """Test import and instantiation of Flowise adapter."""

    def test_import_node(self):
        """Test TorkFlowiseNode can be imported."""
        assert TorkFlowiseNode is not None

    def test_import_flow(self):
        """Test TorkFlowiseFlow can be imported."""
        assert TorkFlowiseFlow is not None

    def test_import_api(self):
        """Test TorkFlowiseAPI can be imported."""
        assert TorkFlowiseAPI is not None

    def test_instantiate_node_default(self):
        """Test node instantiation with defaults."""
        node = TorkFlowiseNode()
        assert node is not None
        assert node.tork is not None
        assert node.receipts == []

    def test_instantiate_flow_default(self):
        """Test flow instantiation with defaults."""
        flow = TorkFlowiseFlow()
        assert flow is not None
        assert flow.tork is not None


class TestFlowiseConfiguration:
    """Test configuration of Flowise adapter."""

    def test_node_with_tork_instance(self, tork_instance):
        """Test node with existing Tork instance."""
        node = TorkFlowiseNode(tork=tork_instance)
        assert node.tork is tork_instance

    def test_flow_with_tork_instance(self, tork_instance):
        """Test flow with existing Tork instance."""
        flow = TorkFlowiseFlow(tork=tork_instance)
        assert flow.tork is tork_instance

    def test_api_with_tork_instance(self, tork_instance):
        """Test API with existing Tork instance."""
        api = TorkFlowiseAPI(tork=tork_instance)
        assert api.tork is tork_instance

    def test_node_with_api_key(self):
        """Test node with API key."""
        node = TorkFlowiseNode(api_key="test-key")
        assert node.tork is not None


class TestFlowisePIIDetection:
    """Test PII detection and redaction in Flowise adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        node = TorkFlowiseNode()
        result = node.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        node = TorkFlowiseNode()
        result = node.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        node = TorkFlowiseNode()
        result = node.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        node = TorkFlowiseNode()
        result = node.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        node = TorkFlowiseNode()
        clean_text = "What is machine learning?"
        result = node.govern(clean_text)
        assert result == clean_text


class TestFlowiseErrorHandling:
    """Test error handling in Flowise adapter."""

    def test_node_empty_string(self):
        """Test node handles empty string."""
        node = TorkFlowiseNode()
        result = node.govern("")
        assert result == ""

    def test_node_whitespace(self):
        """Test node handles whitespace."""
        node = TorkFlowiseNode()
        result = node.govern("   ")
        assert result == "   "

    def test_flow_empty_string(self):
        """Test flow handles empty string."""
        flow = TorkFlowiseFlow()
        result = flow.govern("")
        assert result == ""

    def test_node_empty_receipts(self):
        """Test node starts with empty receipts."""
        node = TorkFlowiseNode()
        assert node.get_receipts() == []


class TestFlowiseComplianceReceipts:
    """Test compliance receipt generation in Flowise adapter."""

    def test_node_process_generates_receipt(self):
        """Test node process generates receipt."""
        node = TorkFlowiseNode()
        node.process({"text": "Test input"})
        assert len(node.receipts) >= 1
        assert node.receipts[0]["type"] == "node_input"
        assert "receipt_id" in node.receipts[0]

    def test_flow_get_receipts(self):
        """Test flow get_receipts method."""
        flow = TorkFlowiseFlow()
        receipts = flow.get_receipts()
        assert isinstance(receipts, list)


class TestFlowiseFlowInputGovernance:
    """Test flow input governance."""

    def test_node_process_governs_input(self):
        """Test node process governs input."""
        node = TorkFlowiseNode()
        result = node.process({"question": PII_MESSAGES["email_message"]})
        assert PII_SAMPLES["email"] not in result["question"]

    def test_node_process_multiple_inputs(self):
        """Test node process governs multiple inputs."""
        node = TorkFlowiseNode()
        result = node.process({
            "question": PII_MESSAGES["email_message"],
            "context": PII_MESSAGES["phone_message"]
        })
        assert PII_SAMPLES["email"] not in result["question"]
        assert PII_SAMPLES["phone_us"] not in result["context"]

    def test_node_process_receipt_has_field(self):
        """Test node receipt includes field name."""
        node = TorkFlowiseNode()
        node.process({"query": "test"})
        assert node.receipts[0]["field"] == "query"


class TestFlowiseChatflowGovernance:
    """Test chatflow governance."""

    def test_flow_execute_governs_input(self):
        """Test flow execute governs input."""
        class MockFlow:
            def execute(self, inputs):
                return {"answer": inputs.get("question", "")}

        flow = TorkFlowiseFlow(MockFlow())
        result = flow.execute({"question": PII_MESSAGES["email_message"]})
        # Input is governed
        assert len(flow.receipts) >= 1

    def test_flow_execute_governs_output(self):
        """Test flow execute governs output."""
        class MockFlow:
            def execute(self, inputs):
                return {"answer": PII_MESSAGES["ssn_message"]}

        flow = TorkFlowiseFlow(MockFlow())
        result = flow.execute({"question": "get ssn"})
        assert PII_SAMPLES["ssn"] not in result["answer"]

    def test_flow_govern_method(self):
        """Test flow govern method."""
        flow = TorkFlowiseFlow()
        result = flow.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result


class TestFlowiseNodeOutputGovernance:
    """Test node output governance."""

    def test_node_process_output(self):
        """Test node process_output governs output."""
        node = TorkFlowiseNode()
        result = node.process_output({"result": PII_MESSAGES["credit_card_message"]})
        assert PII_SAMPLES["credit_card"] not in result["result"]

    def test_node_process_output_receipt(self):
        """Test node process_output generates receipt."""
        node = TorkFlowiseNode()
        node.process_output({"data": "test output"})
        assert any(r["type"] == "node_output" for r in node.receipts)


class TestFlowiseToolCallGovernance:
    """Test tool call governance."""

    def test_node_nested_dict(self):
        """Test node processes nested dict."""
        node = TorkFlowiseNode()
        result = node.process({
            "nested": {"email": PII_MESSAGES["email_message"]}
        })
        assert PII_SAMPLES["email"] not in result["nested"]["email"]

    def test_node_list_values(self):
        """Test node processes list values."""
        node = TorkFlowiseNode()
        result = node.process({
            "items": [PII_MESSAGES["phone_message"], "clean"]
        })
        assert PII_SAMPLES["phone_us"] not in result["items"][0]
        assert result["items"][1] == "clean"


class TestFlowiseAPIRequestGovernance:
    """Test API request governance."""

    def test_api_govern_method(self):
        """Test API govern method."""
        api = TorkFlowiseAPI()
        result = api.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result

    def test_api_get_receipts(self):
        """Test API get_receipts method."""
        api = TorkFlowiseAPI()
        receipts = api.get_receipts()
        assert isinstance(receipts, list)
