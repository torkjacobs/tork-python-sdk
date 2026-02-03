"""
Tests for Langflow adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Flow governance
- Component governance
- Edge data governance
- Template governance
- Build governance
"""

import pytest
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.langflow import (
    TorkLangflowComponent,
    TorkLangflowFlow,
    TorkLangflowAPI,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestLangflowImportInstantiation:
    """Test import and instantiation of Langflow adapter."""

    def test_import_component(self):
        """Test TorkLangflowComponent can be imported."""
        assert TorkLangflowComponent is not None

    def test_import_flow(self):
        """Test TorkLangflowFlow can be imported."""
        assert TorkLangflowFlow is not None

    def test_import_api(self):
        """Test TorkLangflowAPI can be imported."""
        assert TorkLangflowAPI is not None

    def test_instantiate_component_default(self):
        """Test component instantiation with defaults."""
        component = TorkLangflowComponent()
        assert component is not None
        assert component.tork is not None
        assert component.receipts == []

    def test_instantiate_flow_default(self):
        """Test flow instantiation with defaults."""
        flow = TorkLangflowFlow()
        assert flow is not None
        assert flow.tork is not None


class TestLangflowConfiguration:
    """Test configuration of Langflow adapter."""

    def test_component_with_tork_instance(self, tork_instance):
        """Test component with existing Tork instance."""
        component = TorkLangflowComponent(tork=tork_instance)
        assert component.tork is tork_instance

    def test_flow_with_tork_instance(self, tork_instance):
        """Test flow with existing Tork instance."""
        flow = TorkLangflowFlow(tork=tork_instance)
        assert flow.tork is tork_instance

    def test_api_with_tork_instance(self, tork_instance):
        """Test API with existing Tork instance."""
        api = TorkLangflowAPI(tork=tork_instance)
        assert api.tork is tork_instance

    def test_component_with_api_key(self):
        """Test component with API key."""
        component = TorkLangflowComponent(api_key="test-key")
        assert component.tork is not None


class TestLangflowPIIDetection:
    """Test PII detection and redaction in Langflow adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        component = TorkLangflowComponent()
        result = component.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        component = TorkLangflowComponent()
        result = component.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        component = TorkLangflowComponent()
        result = component.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        component = TorkLangflowComponent()
        result = component.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        component = TorkLangflowComponent()
        clean_text = "Build a data pipeline"
        result = component.govern(clean_text)
        assert result == clean_text


class TestLangflowErrorHandling:
    """Test error handling in Langflow adapter."""

    def test_component_empty_string(self):
        """Test component handles empty string."""
        component = TorkLangflowComponent()
        result = component.govern("")
        assert result == ""

    def test_component_whitespace(self):
        """Test component handles whitespace."""
        component = TorkLangflowComponent()
        result = component.govern("   ")
        assert result == "   "

    def test_flow_empty_string(self):
        """Test flow handles empty string."""
        flow = TorkLangflowFlow()
        result = flow.govern("")
        assert result == ""

    def test_component_empty_receipts(self):
        """Test component starts with empty receipts."""
        component = TorkLangflowComponent()
        assert component.get_receipts() == []


class TestLangflowComplianceReceipts:
    """Test compliance receipt generation in Langflow adapter."""

    def test_component_run_generates_receipt(self):
        """Test component run generates receipt."""
        class MockComponent:
            name = "TestComponent"

            def run(self, **kwargs):
                return {"output": kwargs.get("input", "")}

        component = TorkLangflowComponent(MockComponent())
        component.run(input="Test input")
        assert len(component.receipts) >= 1
        assert component.receipts[0]["type"] == "component_input"
        assert "receipt_id" in component.receipts[0]

    def test_flow_get_receipts(self):
        """Test flow get_receipts method."""
        flow = TorkLangflowFlow()
        receipts = flow.get_receipts()
        assert isinstance(receipts, list)


class TestLangflowFlowGovernance:
    """Test flow governance."""

    def test_flow_run_governs_input(self):
        """Test flow run governs input."""
        class MockFlow:
            def run(self, inputs, **kwargs):
                return inputs

        flow = TorkLangflowFlow(MockFlow())
        result = flow.run({"query": PII_MESSAGES["email_message"]})
        assert PII_SAMPLES["email"] not in result["query"]

    def test_flow_run_governs_output(self):
        """Test flow run governs output."""
        class MockFlow:
            def run(self, inputs, **kwargs):
                return {"result": PII_MESSAGES["ssn_message"]}

        flow = TorkLangflowFlow(MockFlow())
        result = flow.run({"query": "get ssn"})
        assert PII_SAMPLES["ssn"] not in result["result"]

    def test_flow_govern_method(self):
        """Test flow govern method."""
        flow = TorkLangflowFlow()
        result = flow.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result


class TestLangflowComponentGovernance:
    """Test component governance."""

    def test_component_run_governs_input(self):
        """Test component run governs input."""
        class MockComponent:
            name = "TestComponent"

            def run(self, **kwargs):
                return {"text": kwargs.get("text", "")}

        component = TorkLangflowComponent(MockComponent())
        result = component.run(text=PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result["text"]

    def test_component_run_governs_output(self):
        """Test component run governs output."""
        class MockComponent:
            name = "TestComponent"

            def run(self, **kwargs):
                return {"output": PII_MESSAGES["credit_card_message"]}

        component = TorkLangflowComponent(MockComponent())
        result = component.run(text="get card")
        assert PII_SAMPLES["credit_card"] not in result["output"]

    def test_component_run_receipt(self):
        """Test component run generates receipt."""
        class MockComponent:
            name = "TestComponent"

            def run(self, **kwargs):
                return {"output": "result"}

        component = TorkLangflowComponent(MockComponent())
        component.run(input="test")
        assert any(r["type"] == "component_input" for r in component.receipts)


class TestLangflowEdgeDataGovernance:
    """Test edge data governance (data flowing between nodes)."""

    def test_component_nested_dict(self):
        """Test component processes nested dict."""
        component = TorkLangflowComponent()
        result = component._govern_dict({
            "nested": {"email": PII_MESSAGES["email_message"]}
        }, "input")
        assert PII_SAMPLES["email"] not in result["nested"]["email"]

    def test_component_list_values(self):
        """Test component processes list values."""
        component = TorkLangflowComponent()
        result = component._govern_list([
            PII_MESSAGES["phone_message"],
            "clean"
        ], "input")
        assert PII_SAMPLES["phone_us"] not in result[0]
        assert result[1] == "clean"


class TestLangflowTemplateGovernance:
    """Test template/prompt governance."""

    def test_component_governs_template(self):
        """Test component governs template strings."""
        component = TorkLangflowComponent()
        template = f"Process this email: {PII_MESSAGES['email_message']}"
        result = component.govern(template)
        assert PII_SAMPLES["email"] not in result

    def test_flow_governs_template_inputs(self):
        """Test flow governs template inputs."""
        class MockFlow:
            def run(self, inputs, **kwargs):
                return {"prompt": inputs.get("template", "")}

        flow = TorkLangflowFlow(MockFlow())
        result = flow.run({"template": PII_MESSAGES["ssn_message"]})
        assert PII_SAMPLES["ssn"] not in result["prompt"]


class TestLangflowBuildGovernance:
    """Test build/execution governance."""

    def test_api_govern_method(self):
        """Test API govern method."""
        api = TorkLangflowAPI()
        result = api.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result

    def test_api_get_receipts(self):
        """Test API get_receipts method."""
        api = TorkLangflowAPI()
        receipts = api.get_receipts()
        assert isinstance(receipts, list)

    def test_api_governs_dict_input(self):
        """Test API governs dict inputs."""
        api = TorkLangflowAPI()
        result = api._govern_dict({"input": PII_MESSAGES["phone_message"]}, "api_input")
        assert PII_SAMPLES["phone_us"] not in result["input"]

    def test_api_governs_dict_output(self):
        """Test API governs dict outputs."""
        api = TorkLangflowAPI()
        result = api._govern_dict({"output": PII_MESSAGES["email_message"]}, "api_output")
        assert PII_SAMPLES["email"] not in result["output"]
