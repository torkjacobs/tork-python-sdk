"""
Tests for DSPy adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Signature governance
- Module governance
- Optimizer governance
- Retriever governance
- Teleprompter governance
"""

import pytest
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.dspy import (
    TorkDSPyModule,
    TorkDSPySignature,
    TorkDSPyOptimizer,
    governed_predict,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestDSPyImportInstantiation:
    """Test import and instantiation of DSPy adapter."""

    def test_import_module(self):
        """Test TorkDSPyModule can be imported."""
        assert TorkDSPyModule is not None

    def test_import_signature(self):
        """Test TorkDSPySignature can be imported."""
        assert TorkDSPySignature is not None

    def test_import_optimizer(self):
        """Test TorkDSPyOptimizer can be imported."""
        assert TorkDSPyOptimizer is not None

    def test_import_governed_predict(self):
        """Test governed_predict can be imported."""
        assert governed_predict is not None

    def test_instantiate_module_default(self):
        """Test module instantiation with defaults."""
        module = TorkDSPyModule()
        assert module is not None
        assert module.tork is not None
        assert module.receipts == []

    def test_instantiate_signature_default(self):
        """Test signature instantiation with defaults."""
        sig = TorkDSPySignature()
        assert sig is not None
        assert sig.tork is not None


class TestDSPyConfiguration:
    """Test configuration of DSPy adapter."""

    def test_module_with_tork_instance(self, tork_instance):
        """Test module with existing Tork instance."""
        module = TorkDSPyModule(tork=tork_instance)
        assert module.tork is tork_instance

    def test_signature_with_tork_instance(self, tork_instance):
        """Test signature with existing Tork instance."""
        sig = TorkDSPySignature(tork=tork_instance)
        assert sig.tork is tork_instance

    def test_optimizer_with_tork_instance(self, tork_instance):
        """Test optimizer with existing Tork instance."""
        opt = TorkDSPyOptimizer(tork=tork_instance)
        assert opt.tork is tork_instance

    def test_module_with_api_key(self):
        """Test module with API key."""
        module = TorkDSPyModule(api_key="test-key")
        assert module.tork is not None


class TestDSPyPIIDetection:
    """Test PII detection and redaction in DSPy adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        module = TorkDSPyModule()
        result = module.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        module = TorkDSPyModule()
        result = module.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        module = TorkDSPyModule()
        result = module.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        module = TorkDSPyModule()
        result = module.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        module = TorkDSPyModule()
        clean_text = "What is machine learning?"
        result = module.govern(clean_text)
        assert result == clean_text


class TestDSPyErrorHandling:
    """Test error handling in DSPy adapter."""

    def test_module_empty_string(self):
        """Test module handles empty string."""
        module = TorkDSPyModule()
        result = module.govern("")
        assert result == ""

    def test_module_whitespace(self):
        """Test module handles whitespace."""
        module = TorkDSPyModule()
        result = module.govern("   ")
        assert result == "   "

    def test_signature_empty_receipts(self):
        """Test signature starts with empty receipts."""
        sig = TorkDSPySignature()
        assert sig.get_receipts() == []

    def test_optimizer_empty_string(self):
        """Test optimizer handles empty string."""
        opt = TorkDSPyOptimizer()
        result = opt.govern("")
        assert result == ""


class TestDSPyComplianceReceipts:
    """Test compliance receipt generation in DSPy adapter."""

    def test_signature_govern_input_generates_receipt(self):
        """Test signature govern_input generates receipt."""
        sig = TorkDSPySignature()
        sig.govern_input(question="Test question")
        assert len(sig.receipts) == 1
        assert sig.receipts[0]["type"] == "signature_input"
        assert "receipt_id" in sig.receipts[0]

    def test_module_get_receipts(self):
        """Test module get_receipts method."""
        module = TorkDSPyModule()
        receipts = module.get_receipts()
        assert isinstance(receipts, list)

    def test_signature_get_receipts(self):
        """Test signature get_receipts method."""
        sig = TorkDSPySignature()
        receipts = sig.get_receipts()
        assert isinstance(receipts, list)


class TestDSPySignatureGovernance:
    """Test signature governance."""

    def test_signature_govern_input(self):
        """Test signature govern_input method."""
        sig = TorkDSPySignature()
        result = sig.govern_input(question=PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result["question"]

    def test_signature_govern_multiple_fields(self):
        """Test signature governs multiple input fields."""
        sig = TorkDSPySignature()
        result = sig.govern_input(
            question=PII_MESSAGES["email_message"],
            context=PII_MESSAGES["phone_message"]
        )
        assert PII_SAMPLES["email"] not in result["question"]
        assert PII_SAMPLES["phone_us"] not in result["context"]
        assert len(sig.receipts) == 2

    def test_signature_govern_output(self):
        """Test signature govern_output method."""
        sig = TorkDSPySignature()

        class MockOutput:
            def __init__(self):
                self.answer = PII_MESSAGES["ssn_message"]

        governed = sig.govern_output(MockOutput())
        assert PII_SAMPLES["ssn"] not in governed.answer

    def test_signature_non_string_field(self):
        """Test signature handles non-string fields."""
        sig = TorkDSPySignature()
        result = sig.govern_input(question="test", count=42)
        assert result["question"] == "test"
        assert result["count"] == 42


class TestDSPyModuleGovernance:
    """Test module governance."""

    def test_module_forward_governs_input(self):
        """Test module forward governs input."""
        class MockModule:
            def forward(self, **kwargs):
                class Output:
                    answer = kwargs.get("question", "")
                return Output()

        module = TorkDSPyModule(MockModule())
        result = module.forward(question=PII_MESSAGES["email_message"])
        assert len(module.receipts) >= 1

    def test_module_forward_governs_output(self):
        """Test module forward governs output."""
        class MockModule:
            def forward(self, **kwargs):
                class Output:
                    def __init__(self):
                        self.answer = PII_MESSAGES["ssn_message"]
                return Output()

        module = TorkDSPyModule(MockModule())
        result = module.forward(question="What is your SSN?")
        assert PII_SAMPLES["ssn"] not in result.answer

    def test_module_callable(self):
        """Test module is callable."""
        class MockModule:
            def forward(self, **kwargs):
                class Output:
                    answer = "test"
                return Output()

        module = TorkDSPyModule(MockModule())
        result = module(question="test")
        assert result.answer == "test"

    def test_module_govern_input_alias(self):
        """Test govern_input is alias for govern."""
        module = TorkDSPyModule()
        result1 = module.govern("test")
        result2 = module.govern_input("test")
        assert result1 == result2


class TestDSPyOptimizerGovernance:
    """Test optimizer governance."""

    def test_optimizer_govern_method(self):
        """Test optimizer govern method."""
        opt = TorkDSPyOptimizer()
        result = opt.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_optimizer_compile_governs_trainset(self):
        """Test optimizer compile governs training data."""
        class MockOptimizer:
            def compile(self, module, trainset):
                return module

        class MockModule:
            pass

        class MockExample:
            question = PII_MESSAGES["email_message"]
            answer = "Test answer"

        opt = TorkDSPyOptimizer(MockOptimizer())
        result = opt.compile(MockModule(), [MockExample()])
        # Should have governed the trainset
        assert result is not None

    def test_optimizer_with_api_key(self):
        """Test optimizer with API key."""
        opt = TorkDSPyOptimizer(api_key="test-key")
        assert opt.tork is not None


class TestDSPyRetrieverGovernance:
    """Test retriever governance (via module)."""

    def test_module_governs_retrieval_query(self):
        """Test module governs retrieval query."""
        class MockRetrieverModule:
            def forward(self, query):
                class Output:
                    passages = [f"Result for: {query}"]
                return Output()

        module = TorkDSPyModule(MockRetrieverModule())
        result = module.forward(query=PII_MESSAGES["email_message"])
        assert len(module.receipts) >= 1
        assert module.receipts[0]["type"] == "module_input"

    def test_module_governs_retrieved_passages(self):
        """Test module governs retrieved passages."""
        class MockRetrieverModule:
            def forward(self, query):
                class Output:
                    def __init__(self):
                        self.passages = PII_MESSAGES["ssn_message"]
                return Output()

        module = TorkDSPyModule(MockRetrieverModule())
        result = module.forward(query="Find SSN")
        # Output field should be governed
        assert PII_SAMPLES["ssn"] not in result.passages

    def test_signature_retriever_input(self):
        """Test signature for retriever input."""
        sig = TorkDSPySignature("query -> passages")
        result = sig.govern_input(query=PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result["query"]


class TestDSPyTeleprompterGovernance:
    """Test teleprompter/prompt optimization governance."""

    def test_governed_predict_decorator(self):
        """Test governed_predict decorator."""
        @governed_predict()
        def predictor(question: str) -> str:
            return f"Answer to: {question}"

        result = predictor(question="test")
        assert result == "Answer to: test"

    def test_governed_predict_governs_input(self):
        """Test governed_predict governs input."""
        @governed_predict()
        def predictor(question: str) -> str:
            return question

        result = predictor(question=PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_governed_predict_governs_output(self):
        """Test governed_predict governs output."""
        @governed_predict()
        def predictor() -> str:
            return PII_MESSAGES["ssn_message"]

        result = predictor()
        assert PII_SAMPLES["ssn"] not in result

    def test_governed_predict_get_receipts(self):
        """Test governed_predict provides get_receipts."""
        @governed_predict()
        def predictor(q: str) -> str:
            return q

        predictor(q="test")
        receipts = predictor.get_receipts()
        assert len(receipts) >= 1

    def test_governed_predict_with_tork(self, tork_instance):
        """Test governed_predict with Tork instance."""
        @governed_predict(tork=tork_instance)
        def predictor(q: str) -> str:
            return q

        result = predictor(q="test")
        assert result == "test"


class TestDSPyEdgeCases:
    """Test edge cases for DSPy adapter."""

    def test_module_receipt_has_field_name(self):
        """Test module receipt includes field name."""
        class MockModule:
            def forward(self, **kwargs):
                class Output:
                    pass
                return Output()

        module = TorkDSPyModule(MockModule())
        module.forward(question="test")
        assert module.receipts[0]["field"] == "question"

    def test_signature_receipt_has_field_name(self):
        """Test signature receipt includes field name."""
        sig = TorkDSPySignature()
        sig.govern_input(query="test")
        assert sig.receipts[0]["field"] == "query"

    def test_module_multiple_input_fields(self):
        """Test module handles multiple input fields."""
        class MockModule:
            def forward(self, **kwargs):
                class Output:
                    pass
                return Output()

        module = TorkDSPyModule(MockModule())
        module.forward(
            question=PII_MESSAGES["email_message"],
            context=PII_MESSAGES["phone_message"],
            hint="Clean hint"
        )
        assert len(module.receipts) == 3

    def test_module_output_multiple_fields(self):
        """Test module governs multiple output fields."""
        class MockModule:
            def forward(self, **kwargs):
                class Output:
                    def __init__(self):
                        self.answer = PII_MESSAGES["ssn_message"]
                        self.reasoning = PII_MESSAGES["credit_card_message"]
                return Output()

        module = TorkDSPyModule(MockModule())
        result = module.forward(question="test")
        assert PII_SAMPLES["ssn"] not in result.answer
        assert PII_SAMPLES["credit_card"] not in result.reasoning
