"""
Tests for LMQL adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Query governance
- Runtime governance
- Query decorator governance
- Output governance
- Async governance
"""

import pytest
import asyncio
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.lmql import (
    TorkLMQLQuery,
    TorkLMQLRuntime,
    governed_query,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestLMQLImportInstantiation:
    """Test import and instantiation of LMQL adapter."""

    def test_import_query(self):
        """Test TorkLMQLQuery can be imported."""
        assert TorkLMQLQuery is not None

    def test_import_runtime(self):
        """Test TorkLMQLRuntime can be imported."""
        assert TorkLMQLRuntime is not None

    def test_import_governed_query(self):
        """Test governed_query can be imported."""
        assert governed_query is not None

    def test_instantiate_query_default(self):
        """Test query instantiation with defaults."""
        query = TorkLMQLQuery()
        assert query is not None
        assert query.tork is not None
        assert query.receipts == []

    def test_instantiate_runtime_default(self):
        """Test runtime instantiation with defaults."""
        runtime = TorkLMQLRuntime()
        assert runtime is not None
        assert runtime.tork is not None


class TestLMQLConfiguration:
    """Test configuration of LMQL adapter."""

    def test_query_with_tork_instance(self, tork_instance):
        """Test query with existing Tork instance."""
        query = TorkLMQLQuery(tork=tork_instance)
        assert query.tork is tork_instance

    def test_runtime_with_tork_instance(self, tork_instance):
        """Test runtime with existing Tork instance."""
        runtime = TorkLMQLRuntime(tork=tork_instance)
        assert runtime.tork is tork_instance

    def test_query_with_api_key(self):
        """Test query with API key."""
        query = TorkLMQLQuery(api_key="test-key")
        assert query.tork is not None

    def test_runtime_with_api_key(self):
        """Test runtime with API key."""
        runtime = TorkLMQLRuntime(api_key="test-key")
        assert runtime.tork is not None


class TestLMQLPIIDetection:
    """Test PII detection and redaction in LMQL adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        query = TorkLMQLQuery()
        result = query.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        query = TorkLMQLQuery()
        result = query.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        query = TorkLMQLQuery()
        result = query.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        query = TorkLMQLQuery()
        result = query.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        query = TorkLMQLQuery()
        clean_text = "What is the capital of France?"
        result = query.govern(clean_text)
        assert result == clean_text


class TestLMQLErrorHandling:
    """Test error handling in LMQL adapter."""

    def test_query_empty_string(self):
        """Test query handles empty string."""
        query = TorkLMQLQuery()
        result = query.govern("")
        assert result == ""

    def test_query_whitespace(self):
        """Test query handles whitespace."""
        query = TorkLMQLQuery()
        result = query.govern("   ")
        assert result == "   "

    def test_runtime_empty_string(self):
        """Test runtime handles empty string."""
        runtime = TorkLMQLRuntime()
        result = runtime.govern("")
        assert result == ""

    def test_query_empty_receipts(self):
        """Test query starts with empty receipts."""
        query = TorkLMQLQuery()
        assert query.get_receipts() == []


class TestLMQLComplianceReceipts:
    """Test compliance receipt generation in LMQL adapter."""

    def test_query_call_generates_receipt(self):
        """Test query call generates receipt."""
        def mock_query(**kwargs):
            return kwargs.get("text", "")

        query = TorkLMQLQuery(mock_query)
        query(text="Test input")
        assert len(query.receipts) >= 1
        assert query.receipts[0]["type"] == "query_input"
        assert "receipt_id" in query.receipts[0]

    def test_query_receipt_includes_variable(self):
        """Test receipt includes variable name."""
        def mock_query(**kwargs):
            return kwargs.get("user_input", "")

        query = TorkLMQLQuery(mock_query)
        query(user_input="test")
        assert query.receipts[0]["variable"] == "user_input"

    def test_query_get_receipts(self):
        """Test query get_receipts method."""
        query = TorkLMQLQuery()
        receipts = query.get_receipts()
        assert isinstance(receipts, list)


class TestLMQLQueryGovernance:
    """Test query governance."""

    def test_query_governs_input_kwargs(self):
        """Test query governs input keyword arguments."""
        def mock_query(**kwargs):
            return kwargs

        query = TorkLMQLQuery(mock_query)
        result = query(text=PII_MESSAGES["email_message"])
        # The governed text is passed to mock_query
        assert len(query.receipts) >= 1

    def test_query_multiple_inputs(self):
        """Test query governs multiple inputs."""
        def mock_query(**kwargs):
            return kwargs

        query = TorkLMQLQuery(mock_query)
        query(
            input1=PII_MESSAGES["email_message"],
            input2=PII_MESSAGES["phone_message"],
            clean="Clean text"
        )
        # Each string input gets a receipt (+ possible output receipts)
        assert len(query.receipts) >= 3

    def test_query_non_string_inputs(self):
        """Test query passes through non-string inputs."""
        def mock_query(**kwargs):
            return kwargs

        query = TorkLMQLQuery(mock_query)
        result = query(text="test", count=42, active=True)
        assert result["count"] == 42
        assert result["active"] is True

    def test_govern_query_alias(self):
        """Test govern_query is alias for govern."""
        query = TorkLMQLQuery()
        result1 = query.govern("test")
        result2 = query.govern_query("test")
        assert result1 == result2

    def test_query_receipt_has_action(self):
        """Test query receipt includes action."""
        def mock_query(**kwargs):
            return kwargs

        query = TorkLMQLQuery(mock_query)
        query(text=PII_MESSAGES["email_message"])
        assert "action" in query.receipts[0]


class TestLMQLOutputGovernance:
    """Test output governance."""

    def test_query_governs_string_output(self):
        """Test query governs string output."""
        def mock_query(**kwargs):
            return PII_MESSAGES["ssn_message"]

        query = TorkLMQLQuery(mock_query)
        result = query(text="get ssn")
        assert PII_SAMPLES["ssn"] not in result

    def test_query_governs_dict_output(self):
        """Test query governs dict output."""
        def mock_query(**kwargs):
            return {
                "response": PII_MESSAGES["email_message"],
                "count": 42
            }

        query = TorkLMQLQuery(mock_query)
        result = query(text="get info")
        assert PII_SAMPLES["email"] not in result["response"]
        assert result["count"] == 42

    def test_query_governs_object_output(self):
        """Test query governs object output fields."""
        class MockOutput:
            def __init__(self):
                self.email = PII_MESSAGES["email_message"]
                self.name = "John"

        def mock_query(**kwargs):
            return MockOutput()

        query = TorkLMQLQuery(mock_query)
        result = query(text="get user")
        assert PII_SAMPLES["email"] not in result.email

    def test_query_output_receipt(self):
        """Test query generates output receipt."""
        def mock_query(**kwargs):
            return "response with data"

        query = TorkLMQLQuery(mock_query)
        query(text="test")
        assert any(r["type"] == "query_output" for r in query.receipts)


class TestLMQLRuntimeGovernance:
    """Test runtime governance."""

    def test_runtime_govern_method(self):
        """Test runtime govern method."""
        runtime = TorkLMQLRuntime()
        result = runtime.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result

    def test_runtime_get_receipts(self):
        """Test runtime get_receipts method."""
        runtime = TorkLMQLRuntime()
        receipts = runtime.get_receipts()
        assert isinstance(receipts, list)

    def test_runtime_has_run_method(self):
        """Test runtime has run method."""
        runtime = TorkLMQLRuntime()
        assert hasattr(runtime, "run")

    def test_runtime_has_arun_method(self):
        """Test runtime has async run method."""
        runtime = TorkLMQLRuntime()
        assert hasattr(runtime, "arun")


class TestLMQLQueryDecoratorGovernance:
    """Test query decorator governance."""

    def test_governed_query_decorator(self):
        """Test governed_query decorator."""
        @governed_query()
        def my_query(**kwargs):
            return kwargs.get("text", "")

        result = my_query(text="test input")
        assert result == "test input"

    def test_governed_query_governs_input(self):
        """Test governed_query governs input."""
        @governed_query()
        def process(**kwargs):
            return kwargs.get("text", "")

        result = process(text=PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_governed_query_generates_receipt(self):
        """Test governed_query generates receipts."""
        @governed_query()
        def my_query(**kwargs):
            return kwargs

        my_query(input1="test1", input2="test2")
        receipts = my_query.get_receipts()
        assert len(receipts) == 2

    def test_governed_query_receipt_type(self):
        """Test governed_query receipt type."""
        @governed_query()
        def my_query(**kwargs):
            return kwargs.get("text", "")

        my_query(text="test")
        receipts = my_query.get_receipts()
        assert receipts[0]["type"] == "decorated_query_input"
        assert receipts[0]["variable"] == "text"

    def test_governed_query_governs_output(self):
        """Test governed_query governs output."""
        @governed_query()
        def my_query(**kwargs):
            return PII_MESSAGES["ssn_message"]

        result = my_query(text="test")
        assert PII_SAMPLES["ssn"] not in result

    def test_governed_query_output_receipt(self):
        """Test governed_query generates output receipt."""
        @governed_query()
        def my_query(**kwargs):
            return "response"

        my_query(text="test")
        receipts = my_query.get_receipts()
        assert any(r["type"] == "decorated_query_output" for r in receipts)

    def test_governed_query_with_tork(self, tork_instance):
        """Test governed_query with Tork instance."""
        @governed_query(tork=tork_instance)
        def my_query(**kwargs):
            return kwargs.get("text", "")

        result = my_query(text="test")
        assert result == "test"


class TestLMQLAsyncGovernance:
    """Test async governance."""

    @pytest.mark.asyncio
    async def test_query_has_acall_method(self):
        """Test query has async call method."""
        query = TorkLMQLQuery()
        assert hasattr(query, "__acall__")

    @pytest.mark.asyncio
    async def test_decorated_query_async_compatible(self):
        """Test decorated query works with async patterns."""
        @governed_query()
        def sync_query(**kwargs):
            return kwargs.get("text", "")

        async def async_wrapper():
            return sync_query(text="test")

        result = await async_wrapper()
        assert result == "test"

    def test_multiple_query_calls(self):
        """Test multiple query calls accumulate receipts."""
        def mock_query(**kwargs):
            return kwargs

        query = TorkLMQLQuery(mock_query)
        query(text="first")
        query(text="second")
        assert len(query.receipts) >= 2
