"""
Tests for Guidance adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Program governance
- Generation block governance
- Model governance
- Block decorator governance
- Template governance
"""

import pytest
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.guidance import (
    TorkGuidanceProgram,
    TorkGuidanceGen,
    TorkGuidanceModel,
    governed_block,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestGuidanceImportInstantiation:
    """Test import and instantiation of Guidance adapter."""

    def test_import_program(self):
        """Test TorkGuidanceProgram can be imported."""
        assert TorkGuidanceProgram is not None

    def test_import_gen(self):
        """Test TorkGuidanceGen can be imported."""
        assert TorkGuidanceGen is not None

    def test_import_model(self):
        """Test TorkGuidanceModel can be imported."""
        assert TorkGuidanceModel is not None

    def test_import_governed_block(self):
        """Test governed_block can be imported."""
        assert governed_block is not None

    def test_instantiate_program_default(self):
        """Test program instantiation with defaults."""
        program = TorkGuidanceProgram()
        assert program is not None
        assert program.tork is not None
        assert program.receipts == []

    def test_instantiate_gen_default(self):
        """Test gen instantiation with defaults."""
        gen = TorkGuidanceGen()
        assert gen is not None
        assert gen.tork is not None


class TestGuidanceConfiguration:
    """Test configuration of Guidance adapter."""

    def test_program_with_tork_instance(self, tork_instance):
        """Test program with existing Tork instance."""
        program = TorkGuidanceProgram(tork=tork_instance)
        assert program.tork is tork_instance

    def test_gen_with_tork_instance(self, tork_instance):
        """Test gen with existing Tork instance."""
        gen = TorkGuidanceGen(tork=tork_instance)
        assert gen.tork is tork_instance

    def test_model_with_tork_instance(self, tork_instance):
        """Test model with existing Tork instance."""
        model = TorkGuidanceModel(tork=tork_instance)
        assert model.tork is tork_instance

    def test_program_with_api_key(self):
        """Test program with API key."""
        program = TorkGuidanceProgram(api_key="test-key")
        assert program.tork is not None


class TestGuidancePIIDetection:
    """Test PII detection and redaction in Guidance adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        program = TorkGuidanceProgram()
        result = program.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        program = TorkGuidanceProgram()
        result = program.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        program = TorkGuidanceProgram()
        result = program.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        program = TorkGuidanceProgram()
        result = program.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        program = TorkGuidanceProgram()
        clean_text = "Generate a poem about nature"
        result = program.govern(clean_text)
        assert result == clean_text


class TestGuidanceErrorHandling:
    """Test error handling in Guidance adapter."""

    def test_program_empty_string(self):
        """Test program handles empty string."""
        program = TorkGuidanceProgram()
        result = program.govern("")
        assert result == ""

    def test_program_whitespace(self):
        """Test program handles whitespace."""
        program = TorkGuidanceProgram()
        result = program.govern("   ")
        assert result == "   "

    def test_gen_empty_string(self):
        """Test gen handles empty string."""
        gen = TorkGuidanceGen()
        result = gen.govern("")
        assert result == ""

    def test_program_empty_receipts(self):
        """Test program starts with empty receipts."""
        program = TorkGuidanceProgram()
        assert program.get_receipts() == []


class TestGuidanceComplianceReceipts:
    """Test compliance receipt generation in Guidance adapter."""

    def test_program_call_generates_receipt(self):
        """Test program call generates receipt."""
        def mock_program(**kwargs):
            return kwargs

        program = TorkGuidanceProgram(mock_program)
        program(text="Test input")
        assert len(program.receipts) >= 1
        assert program.receipts[0]["type"] == "program_input"
        assert "receipt_id" in program.receipts[0]

    def test_program_receipt_includes_variable(self):
        """Test receipt includes variable name."""
        def mock_program(**kwargs):
            return kwargs

        program = TorkGuidanceProgram(mock_program)
        program(user_input="test")
        assert program.receipts[0]["variable"] == "user_input"

    def test_program_get_receipts(self):
        """Test program get_receipts method."""
        program = TorkGuidanceProgram()
        receipts = program.get_receipts()
        assert isinstance(receipts, list)


class TestGuidanceProgramGovernance:
    """Test program governance."""

    def test_program_governs_input_kwargs(self):
        """Test program governs input keyword arguments."""
        def mock_program(**kwargs):
            return kwargs

        program = TorkGuidanceProgram(mock_program)
        result = program(text=PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result.get("text", "")

    def test_program_multiple_inputs(self):
        """Test program governs multiple inputs."""
        def mock_program(**kwargs):
            return kwargs

        program = TorkGuidanceProgram(mock_program)
        program(
            input1=PII_MESSAGES["email_message"],
            input2=PII_MESSAGES["phone_message"],
            clean="Clean text"
        )
        # 3 inputs + possible output receipts
        assert len(program.receipts) >= 3

    def test_program_non_string_inputs(self):
        """Test program passes through non-string inputs."""
        def mock_program(**kwargs):
            return kwargs

        program = TorkGuidanceProgram(mock_program)
        result = program(text="test", count=42, active=True)
        assert result["count"] == 42
        assert result["active"] is True

    def test_program_with_lm(self):
        """Test program with language model."""
        def mock_program(lm, **kwargs):
            return {"lm": lm, **kwargs}

        program = TorkGuidanceProgram(mock_program)
        mock_lm = "mock_language_model"
        result = program(lm=mock_lm, text="test")
        assert result["lm"] == mock_lm

    def test_govern_input_alias(self):
        """Test govern_input is alias for govern."""
        program = TorkGuidanceProgram()
        result1 = program.govern("test")
        result2 = program.govern_input("test")
        assert result1 == result2


class TestGuidanceGenGovernance:
    """Test generation block governance."""

    def test_gen_govern_method(self):
        """Test gen govern method."""
        gen = TorkGuidanceGen()
        result = gen.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_gen_has_governed_gen_method(self):
        """Test gen has governed_gen method."""
        gen = TorkGuidanceGen()
        assert hasattr(gen, "governed_gen")

    def test_gen_get_receipts(self):
        """Test gen get_receipts method."""
        gen = TorkGuidanceGen()
        receipts = gen.get_receipts()
        assert isinstance(receipts, list)


class TestGuidanceModelGovernance:
    """Test model governance."""

    def test_model_govern_method(self):
        """Test model govern method."""
        model = TorkGuidanceModel()
        result = model.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result

    def test_model_add_governs_string(self):
        """Test model __add__ governs string content."""
        class MockModel:
            def __add__(self, content):
                return content

        model = TorkGuidanceModel(MockModel())
        result = model + PII_MESSAGES["email_message"]
        # Note: Result depends on mock behavior
        assert len(model.receipts) == 1
        assert model.receipts[0]["type"] == "model_content"

    def test_model_get_receipts(self):
        """Test model get_receipts method."""
        model = TorkGuidanceModel()
        receipts = model.get_receipts()
        assert isinstance(receipts, list)

    def test_model_getitem_governs_string(self):
        """Test model __getitem__ governs string values."""
        class MockModel:
            def __getitem__(self, key):
                if key == "output":
                    return PII_MESSAGES["phone_message"]
                return None

        model = TorkGuidanceModel(MockModel())
        result = model["output"]
        assert PII_SAMPLES["phone_us"] not in result


class TestGuidanceBlockDecoratorGovernance:
    """Test block decorator governance."""

    def test_governed_block_decorator(self):
        """Test governed_block decorator."""
        @governed_block()
        def my_block(lm=None, **kwargs):
            return kwargs

        result = my_block(text="test input")
        assert result["text"] == "test input"

    def test_governed_block_governs_input(self):
        """Test governed_block governs input."""
        @governed_block()
        def process(lm=None, text=None):
            return {"text": text}

        result = process(text=PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result["text"]

    def test_governed_block_generates_receipt(self):
        """Test governed_block generates receipts."""
        @governed_block()
        def my_block(lm=None, **kwargs):
            return kwargs

        my_block(input1="test1", input2="test2")
        receipts = my_block.get_receipts()
        assert len(receipts) == 2

    def test_governed_block_receipt_type(self):
        """Test governed_block receipt type."""
        @governed_block()
        def my_block(lm=None, text=None):
            return text

        my_block(text="test")
        receipts = my_block.get_receipts()
        assert receipts[0]["type"] == "block_input"
        assert receipts[0]["variable"] == "text"

    def test_governed_block_with_tork(self, tork_instance):
        """Test governed_block with Tork instance."""
        @governed_block(tork=tork_instance)
        def my_block(lm=None, text=None):
            return text

        result = my_block(text="test")
        assert result == "test"

    def test_governed_block_with_lm(self):
        """Test governed_block passes through lm."""
        @governed_block()
        def my_block(lm=None, text=None):
            return {"lm": lm, "text": text}

        mock_lm = "mock_language_model"
        result = my_block(lm=mock_lm, text="test")
        assert result["lm"] == mock_lm


class TestGuidanceTemplateGovernance:
    """Test template-related functionality."""

    def test_program_receipt_has_action(self):
        """Test program receipt includes action."""
        def mock_program(**kwargs):
            return kwargs

        program = TorkGuidanceProgram(mock_program)
        program(text=PII_MESSAGES["email_message"])
        assert "action" in program.receipts[0]

    def test_multiple_program_calls(self):
        """Test multiple program calls accumulate receipts."""
        def mock_program(**kwargs):
            return kwargs

        program = TorkGuidanceProgram(mock_program)
        program(text="first")
        program(text="second")
        # 2 inputs + possible output receipts
        assert len(program.receipts) >= 2

    def test_program_mixed_inputs(self):
        """Test program with mixed string and non-string inputs."""
        def mock_program(**kwargs):
            return kwargs

        program = TorkGuidanceProgram(mock_program)
        program(
            text=PII_MESSAGES["credit_card_message"],
            count=10,
            items=["a", "b", "c"]
        )
        # Only string inputs generate receipts (+ possible output receipts)
        assert len(program.receipts) >= 1
        # Verify input receipt exists
        assert any(r["type"] == "program_input" for r in program.receipts)
