"""
Tests for LlamaIndex adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Query engine governance
- Document indexing governance
- Retrieved nodes governance
- Response synthesis governance
- Chat engine governance
"""

import pytest
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.llamaindex import (
    TorkLlamaIndexCallback,
    TorkQueryEngine,
    TorkRetriever,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestLlamaIndexImportInstantiation:
    """Test import and instantiation of LlamaIndex adapter."""

    def test_import_callback(self):
        """Test TorkLlamaIndexCallback can be imported."""
        assert TorkLlamaIndexCallback is not None

    def test_import_query_engine(self):
        """Test TorkQueryEngine can be imported."""
        assert TorkQueryEngine is not None

    def test_import_retriever(self):
        """Test TorkRetriever can be imported."""
        assert TorkRetriever is not None

    def test_instantiate_callback_default(self):
        """Test callback instantiation with defaults."""
        callback = TorkLlamaIndexCallback()
        assert callback is not None
        assert callback.tork is not None
        assert callback.receipts == []

    def test_instantiate_query_engine_default(self):
        """Test query engine instantiation with defaults."""
        engine = TorkQueryEngine()
        assert engine is not None
        assert engine.tork is not None


class TestLlamaIndexConfiguration:
    """Test configuration of LlamaIndex adapter."""

    def test_callback_with_tork_instance(self, tork_instance):
        """Test callback with existing Tork instance."""
        callback = TorkLlamaIndexCallback(tork=tork_instance)
        assert callback.tork is tork_instance

    def test_query_engine_with_tork_instance(self, tork_instance):
        """Test query engine with existing Tork instance."""
        engine = TorkQueryEngine(tork=tork_instance)
        assert engine.tork is tork_instance

    def test_retriever_with_tork_instance(self, tork_instance):
        """Test retriever with existing Tork instance."""
        retriever = TorkRetriever(tork=tork_instance)
        assert retriever.tork is tork_instance

    def test_callback_with_api_key(self):
        """Test callback with API key."""
        callback = TorkLlamaIndexCallback(api_key="test-key")
        assert callback.tork is not None


class TestLlamaIndexPIIDetection:
    """Test PII detection and redaction in LlamaIndex adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        callback = TorkLlamaIndexCallback()
        result = callback.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        callback = TorkLlamaIndexCallback()
        result = callback.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        callback = TorkLlamaIndexCallback()
        result = callback.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        callback = TorkLlamaIndexCallback()
        result = callback.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        callback = TorkLlamaIndexCallback()
        clean_text = "What is the weather today?"
        result = callback.govern(clean_text)
        assert result == clean_text


class TestLlamaIndexErrorHandling:
    """Test error handling in LlamaIndex adapter."""

    def test_callback_empty_string(self):
        """Test callback handles empty string."""
        callback = TorkLlamaIndexCallback()
        result = callback.govern("")
        assert result == ""

    def test_callback_whitespace(self):
        """Test callback handles whitespace."""
        callback = TorkLlamaIndexCallback()
        result = callback.govern("   ")
        assert result == "   "

    def test_query_engine_empty_string(self):
        """Test query engine handles empty string."""
        engine = TorkQueryEngine()
        result = engine.govern("")
        assert result == ""

    def test_retriever_empty_string(self):
        """Test retriever handles empty string."""
        retriever = TorkRetriever()
        result = retriever.govern("")
        assert result == ""


class TestLlamaIndexComplianceReceipts:
    """Test compliance receipt generation in LlamaIndex adapter."""

    def test_on_query_start_generates_receipt(self):
        """Test on_query_start generates receipt."""
        callback = TorkLlamaIndexCallback()
        callback.on_query_start("Test query")
        assert len(callback.receipts) == 1
        assert callback.receipts[0]["type"] == "query_start"
        assert "receipt_id" in callback.receipts[0]
        assert "has_pii" in callback.receipts[0]

    def test_on_query_end_generates_receipt(self):
        """Test on_query_end generates receipt."""
        callback = TorkLlamaIndexCallback()
        callback.on_query_end("Test response")
        assert len(callback.receipts) == 1
        assert callback.receipts[0]["type"] == "query_end"

    def test_get_receipts(self):
        """Test get_receipts method."""
        callback = TorkLlamaIndexCallback()
        callback.on_query_start("Query 1")
        callback.on_query_end("Response 1")
        receipts = callback.get_receipts()
        assert len(receipts) == 2


class TestLlamaIndexQueryEngineGovernance:
    """Test query engine governance."""

    def test_govern_query_method(self):
        """Test govern_query method."""
        engine = TorkQueryEngine()
        result = engine.govern_query(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_query_governs_input(self):
        """Test query method governs input."""
        class MockEngine:
            def query(self, query_str):
                class Response:
                    response = f"Result for: {query_str}"
                return Response()

        engine = TorkQueryEngine(MockEngine())
        response = engine.query("Find data")
        assert len(engine.receipts) >= 1
        assert engine.receipts[0]["type"] == "query_input"

    def test_query_governs_output(self):
        """Test query method governs output."""
        class MockEngine:
            def query(self, query_str):
                class Response:
                    response = PII_MESSAGES["ssn_message"]
                return Response()

        engine = TorkQueryEngine(MockEngine())
        response = engine.query("Find SSN")
        assert PII_SAMPLES["ssn"] not in response.response

    def test_query_engine_receipts(self):
        """Test query engine generates receipts."""
        class MockEngine:
            def query(self, query_str):
                class Response:
                    response = "Clean response"
                return Response()

        engine = TorkQueryEngine(MockEngine())
        engine.query("Test")
        receipts = engine.get_receipts()
        assert len(receipts) >= 1


class TestLlamaIndexDocumentIndexingGovernance:
    """Test document indexing governance."""

    def test_callback_on_llm_start(self):
        """Test on_llm_start governs prompts."""
        callback = TorkLlamaIndexCallback()
        result = callback.on_llm_start(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert len(callback.receipts) == 1

    def test_callback_on_llm_end(self):
        """Test on_llm_end governs responses."""
        callback = TorkLlamaIndexCallback()
        result = callback.on_llm_end(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert len(callback.receipts) == 1


class TestLlamaIndexRetrievedNodesGovernance:
    """Test retrieved nodes governance."""

    def test_on_retrieve_start(self):
        """Test on_retrieve_start governs query."""
        callback = TorkLlamaIndexCallback()
        result = callback.on_retrieve_start(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    def test_on_retrieve_end_governs_nodes(self):
        """Test on_retrieve_end governs node content."""
        callback = TorkLlamaIndexCallback()

        class MockNode:
            text = PII_MESSAGES["ssn_message"]

        nodes = [MockNode()]
        governed_nodes = callback.on_retrieve_end(nodes)
        assert PII_SAMPLES["ssn"] not in governed_nodes[0].text

    def test_retriever_retrieve_governs_query(self):
        """Test retriever governs query."""
        class MockRetriever:
            def retrieve(self, query_str):
                return []

        retriever = TorkRetriever(MockRetriever())
        result = retriever.retrieve("Test query")
        assert len(retriever.receipts) >= 1

    def test_retriever_retrieve_governs_nodes(self):
        """Test retriever governs retrieved node content."""
        class MockNode:
            text = PII_MESSAGES["email_message"]

        class MockRetriever:
            def retrieve(self, query_str):
                return [MockNode()]

        retriever = TorkRetriever(MockRetriever())
        nodes = retriever.retrieve("Find emails")
        assert PII_SAMPLES["email"] not in nodes[0].text


class TestLlamaIndexResponseSynthesisGovernance:
    """Test response synthesis governance."""

    def test_query_engine_governs_synthesized_response(self):
        """Test query engine governs synthesized response."""
        class MockEngine:
            def query(self, query_str):
                class Response:
                    response = f"Synthesized: {PII_MESSAGES['credit_card_message']}"
                return Response()

        engine = TorkQueryEngine(MockEngine())
        response = engine.query("Get card info")
        assert PII_SAMPLES["credit_card"] not in response.response

    def test_multiple_query_receipts(self):
        """Test multiple queries generate multiple receipts."""
        class MockEngine:
            def query(self, query_str):
                class Response:
                    response = "Result"
                return Response()

        engine = TorkQueryEngine(MockEngine())
        engine.query("Query 1")
        engine.query("Query 2")
        assert len(engine.get_receipts()) >= 2


class TestLlamaIndexChatEngineGovernance:
    """Test chat engine governance (using callback)."""

    def test_callback_govern_query_alias(self):
        """Test govern_query is alias for on_query_start."""
        callback = TorkLlamaIndexCallback()
        result1 = callback.govern_query("test")
        callback2 = TorkLlamaIndexCallback()
        result2 = callback2.on_query_start("test")
        assert result1 == result2

    def test_callback_chain_governance(self):
        """Test chaining multiple governance calls."""
        callback = TorkLlamaIndexCallback()
        # Simulate chat flow
        governed_input = callback.on_query_start(PII_MESSAGES["email_message"])
        governed_output = callback.on_query_end(PII_MESSAGES["phone_message"])

        assert PII_SAMPLES["email"] not in governed_input
        assert PII_SAMPLES["phone_us"] not in governed_output
        assert len(callback.receipts) == 2

    def test_receipt_has_pii_flag(self):
        """Test receipt includes has_pii flag."""
        callback = TorkLlamaIndexCallback()
        callback.on_query_start(PII_MESSAGES["email_message"])
        assert callback.receipts[0]["has_pii"] is True

        callback2 = TorkLlamaIndexCallback()
        callback2.on_query_start("Clean query")
        assert callback2.receipts[0]["has_pii"] is False
