"""
Tests for Marvin adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- AI function governance
- Classifier governance
- Extractor governance
- Image governance
- Decorator governance
"""

import pytest
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.marvin import (
    TorkMarvinAI,
    TorkMarvinImage,
    governed_fn,
    governed_classifier,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestMarvinImportInstantiation:
    """Test import and instantiation of Marvin adapter."""

    def test_import_ai(self):
        """Test TorkMarvinAI can be imported."""
        assert TorkMarvinAI is not None

    def test_import_image(self):
        """Test TorkMarvinImage can be imported."""
        assert TorkMarvinImage is not None

    def test_import_governed_fn(self):
        """Test governed_fn can be imported."""
        assert governed_fn is not None

    def test_import_governed_classifier(self):
        """Test governed_classifier can be imported."""
        assert governed_classifier is not None

    def test_instantiate_ai_default(self):
        """Test AI instantiation with defaults."""
        ai = TorkMarvinAI()
        assert ai is not None
        assert ai.tork is not None
        assert ai.receipts == []

    def test_instantiate_image_default(self):
        """Test image instantiation with defaults."""
        image = TorkMarvinImage()
        assert image is not None
        assert image.tork is not None


class TestMarvinConfiguration:
    """Test configuration of Marvin adapter."""

    def test_ai_with_tork_instance(self, tork_instance):
        """Test AI with existing Tork instance."""
        ai = TorkMarvinAI(tork=tork_instance)
        assert ai.tork is tork_instance

    def test_image_with_tork_instance(self, tork_instance):
        """Test image with existing Tork instance."""
        image = TorkMarvinImage(tork=tork_instance)
        assert image.tork is tork_instance

    def test_ai_with_api_key(self):
        """Test AI with API key."""
        ai = TorkMarvinAI(api_key="test-key")
        assert ai.tork is not None


class TestMarvinPIIDetection:
    """Test PII detection and redaction in Marvin adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected via tork."""
        ai = TorkMarvinAI()
        result = ai.tork.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result.output
        assert "[EMAIL_REDACTED]" in result.output

    def test_govern_phone_pii(self):
        """Test phone PII is detected via tork."""
        ai = TorkMarvinAI()
        result = ai.tork.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result.output
        assert "[PHONE_REDACTED]" in result.output

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected via tork."""
        ai = TorkMarvinAI()
        result = ai.tork.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result.output
        assert "[SSN_REDACTED]" in result.output

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected via tork."""
        ai = TorkMarvinAI()
        result = ai.tork.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result.output
        assert "[CARD_REDACTED]" in result.output

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        ai = TorkMarvinAI()
        clean_text = "Classify this sentiment"
        result = ai.tork.govern(clean_text)
        assert result.output == clean_text


class TestMarvinErrorHandling:
    """Test error handling in Marvin adapter."""

    def test_ai_empty_string(self):
        """Test AI handles empty string."""
        ai = TorkMarvinAI()
        result = ai.tork.govern("")
        assert result.output == ""

    def test_ai_whitespace(self):
        """Test AI handles whitespace."""
        ai = TorkMarvinAI()
        result = ai.tork.govern("   ")
        assert result.output == "   "

    def test_ai_empty_receipts(self):
        """Test AI starts with empty receipts."""
        ai = TorkMarvinAI()
        assert ai.get_receipts() == []

    def test_image_empty_receipts(self):
        """Test image starts with empty receipts."""
        image = TorkMarvinImage()
        assert image.get_receipts() == []


class TestMarvinComplianceReceipts:
    """Test compliance receipt generation in Marvin adapter."""

    def test_ai_get_receipts(self):
        """Test AI get_receipts method."""
        ai = TorkMarvinAI()
        receipts = ai.get_receipts()
        assert isinstance(receipts, list)

    def test_image_get_receipts(self):
        """Test image get_receipts method."""
        image = TorkMarvinImage()
        receipts = image.get_receipts()
        assert isinstance(receipts, list)


class TestMarvinFnDecoratorGovernance:
    """Test governed_fn decorator governance."""

    def test_governed_fn_decorator(self):
        """Test governed_fn decorator."""
        @governed_fn()
        def my_func(text: str) -> str:
            return f"Processed: {text}"

        result = my_func("test input")
        assert result == "Processed: test input"

    def test_governed_fn_governs_args(self):
        """Test governed_fn governs positional args."""
        @governed_fn()
        def process(text: str) -> str:
            return text

        result = process(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_governed_fn_governs_kwargs(self):
        """Test governed_fn governs keyword args."""
        @governed_fn()
        def process(text: str = "") -> str:
            return text

        result = process(text=PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result

    def test_governed_fn_generates_receipt(self):
        """Test governed_fn generates receipts."""
        @governed_fn()
        def my_func(text: str) -> str:
            return text

        my_func("test")
        receipts = my_func.get_receipts()
        assert len(receipts) >= 1

    def test_governed_fn_arg_receipt_type(self):
        """Test governed_fn arg receipt type."""
        @governed_fn()
        def my_func(text: str) -> str:
            return text

        my_func("test")
        receipts = my_func.get_receipts()
        assert receipts[0]["type"] == "fn_input_arg"

    def test_governed_fn_kwarg_receipt_type(self):
        """Test governed_fn kwarg receipt type."""
        @governed_fn()
        def my_func(text: str = "") -> str:
            return text

        my_func(text="test")
        receipts = my_func.get_receipts()
        assert receipts[0]["type"] == "fn_input_kwarg"
        assert receipts[0]["key"] == "text"

    def test_governed_fn_governs_output(self):
        """Test governed_fn governs output."""
        @governed_fn()
        def my_func() -> str:
            return PII_MESSAGES["ssn_message"]

        result = my_func()
        assert PII_SAMPLES["ssn"] not in result

    def test_governed_fn_output_receipt(self):
        """Test governed_fn generates output receipt."""
        @governed_fn()
        def my_func() -> str:
            return "output"

        my_func()
        receipts = my_func.get_receipts()
        assert any(r["type"] == "fn_output" for r in receipts)

    def test_governed_fn_with_tork(self, tork_instance):
        """Test governed_fn with Tork instance."""
        @governed_fn(tork=tork_instance)
        def my_func(text: str) -> str:
            return text

        result = my_func("test")
        assert result == "test"

    def test_governed_fn_non_string_output(self):
        """Test governed_fn handles non-string output."""
        @governed_fn()
        def my_func() -> dict:
            return {"result": "value"}

        result = my_func()
        assert result == {"result": "value"}

    def test_governed_fn_non_string_args(self):
        """Test governed_fn passes through non-string args."""
        @governed_fn()
        def my_func(count: int, active: bool) -> str:
            return f"{count}-{active}"

        result = my_func(42, True)
        assert result == "42-True"


class TestMarvinClassifierDecoratorGovernance:
    """Test governed_classifier decorator governance."""

    def test_governed_classifier_decorator(self):
        """Test governed_classifier decorator."""
        @governed_classifier()
        def classify(text: str) -> str:
            return "positive"

        result = classify("test text")
        assert result == "positive"

    def test_governed_classifier_governs_input(self):
        """Test governed_classifier governs input."""
        texts_received = []

        @governed_classifier()
        def classify(text: str) -> str:
            texts_received.append(text)
            return "pii"

        classify(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in texts_received[0]

    def test_governed_classifier_generates_receipt(self):
        """Test governed_classifier generates receipts."""
        @governed_classifier()
        def classify(text: str) -> str:
            return "category"

        classify("test")
        receipts = classify.get_receipts()
        assert len(receipts) == 1
        assert receipts[0]["type"] == "classifier_input"

    def test_governed_classifier_with_tork(self, tork_instance):
        """Test governed_classifier with Tork instance."""
        @governed_classifier(tork=tork_instance)
        def classify(text: str) -> str:
            return "result"

        result = classify("test")
        assert result == "result"

    def test_governed_classifier_with_labels(self):
        """Test governed_classifier with additional args."""
        @governed_classifier()
        def classify(text: str, labels=None) -> str:
            return labels[0] if labels else "unknown"

        result = classify("test", labels=["positive", "negative"])
        assert result == "positive"


class TestMarvinAIMethods:
    """Test TorkMarvinAI method signatures."""

    def test_ai_has_classify_method(self):
        """Test AI has classify method."""
        ai = TorkMarvinAI()
        assert hasattr(ai, "classify")

    def test_ai_has_extract_method(self):
        """Test AI has extract method."""
        ai = TorkMarvinAI()
        assert hasattr(ai, "extract")

    def test_ai_has_cast_method(self):
        """Test AI has cast method."""
        ai = TorkMarvinAI()
        assert hasattr(ai, "cast")

    def test_ai_has_generate_method(self):
        """Test AI has generate method."""
        ai = TorkMarvinAI()
        assert hasattr(ai, "generate")


class TestMarvinImageGovernance:
    """Test image governance."""

    def test_image_has_caption_method(self):
        """Test image has caption method."""
        image = TorkMarvinImage()
        assert hasattr(image, "caption")


class TestMarvinEdgeCases:
    """Test edge cases for Marvin adapter."""

    def test_fn_multiple_string_args(self):
        """Test governed_fn with multiple string args."""
        @governed_fn()
        def process(a: str, b: str) -> str:
            return f"{a}-{b}"

        result = process(
            PII_MESSAGES["email_message"],
            PII_MESSAGES["phone_message"]
        )
        assert PII_SAMPLES["email"] not in result
        assert PII_SAMPLES["phone_us"] not in result

    def test_fn_multiple_calls_accumulate_receipts(self):
        """Test multiple calls accumulate receipts."""
        @governed_fn()
        def my_func(text: str) -> str:
            return text

        my_func("first")
        my_func("second")
        receipts = my_func.get_receipts()
        assert len(receipts) >= 2

    def test_classifier_multiple_calls(self):
        """Test classifier multiple calls."""
        @governed_classifier()
        def classify(text: str) -> str:
            return "result"

        classify("first")
        classify("second")
        receipts = classify.get_receipts()
        assert len(receipts) == 2

    def test_fn_mixed_args_kwargs(self):
        """Test governed_fn with mixed args and kwargs."""
        @governed_fn()
        def process(text: str, prefix: str = "") -> str:
            return f"{prefix}{text}"

        result = process(
            PII_MESSAGES["email_message"],
            prefix=PII_MESSAGES["phone_message"]
        )
        assert PII_SAMPLES["email"] not in result
        assert PII_SAMPLES["phone_us"] not in result
