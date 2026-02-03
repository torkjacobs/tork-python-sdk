"""
Tests for Haystack adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Pipeline governance
- Document store governance
- Retriever governance
- Reader governance
- Generator governance
"""

import pytest
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.haystack import (
    TorkHaystackComponent,
    TorkHaystackPipeline,
    TorkDocumentProcessor,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestHaystackImportInstantiation:
    """Test import and instantiation of Haystack adapter."""

    def test_import_component(self):
        """Test TorkHaystackComponent can be imported."""
        assert TorkHaystackComponent is not None

    def test_import_pipeline(self):
        """Test TorkHaystackPipeline can be imported."""
        assert TorkHaystackPipeline is not None

    def test_import_document_processor(self):
        """Test TorkDocumentProcessor can be imported."""
        assert TorkDocumentProcessor is not None

    def test_instantiate_component_default(self):
        """Test component instantiation with defaults."""
        component = TorkHaystackComponent()
        assert component is not None
        assert component.tork is not None
        assert component.receipts == []

    def test_instantiate_pipeline_default(self):
        """Test pipeline instantiation with defaults."""
        pipeline = TorkHaystackPipeline()
        assert pipeline is not None
        assert pipeline.tork is not None


class TestHaystackConfiguration:
    """Test configuration of Haystack adapter."""

    def test_component_with_tork_instance(self, tork_instance):
        """Test component with existing Tork instance."""
        component = TorkHaystackComponent(tork=tork_instance)
        assert component.tork is tork_instance

    def test_pipeline_with_tork_instance(self, tork_instance):
        """Test pipeline with existing Tork instance."""
        pipeline = TorkHaystackPipeline(tork=tork_instance)
        assert pipeline.tork is tork_instance

    def test_component_with_api_key(self):
        """Test component with API key."""
        component = TorkHaystackComponent(api_key="test-key")
        assert component.tork is not None

    def test_document_processor_with_tork(self, tork_instance):
        """Test document processor with Tork instance."""
        processor = TorkDocumentProcessor(tork=tork_instance)
        assert processor.tork is tork_instance


class TestHaystackPIIDetection:
    """Test PII detection and redaction in Haystack adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        pipeline = TorkHaystackPipeline()
        result = pipeline.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        pipeline = TorkHaystackPipeline()
        result = pipeline.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        pipeline = TorkHaystackPipeline()
        result = pipeline.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        pipeline = TorkHaystackPipeline()
        result = pipeline.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        pipeline = TorkHaystackPipeline()
        clean_text = "What documents do you have?"
        result = pipeline.govern(clean_text)
        assert result == clean_text


class TestHaystackErrorHandling:
    """Test error handling in Haystack adapter."""

    def test_pipeline_empty_string(self):
        """Test pipeline handles empty string."""
        pipeline = TorkHaystackPipeline()
        result = pipeline.govern("")
        assert result == ""

    def test_pipeline_whitespace(self):
        """Test pipeline handles whitespace."""
        pipeline = TorkHaystackPipeline()
        result = pipeline.govern("   ")
        assert result == "   "

    def test_component_run_no_inputs(self):
        """Test component run with no inputs."""
        component = TorkHaystackComponent()
        result = component.run()
        assert result == {}

    def test_component_empty_receipts(self):
        """Test component starts with empty receipts."""
        component = TorkHaystackComponent()
        assert component.get_receipts() == []


class TestHaystackComplianceReceipts:
    """Test compliance receipt generation in Haystack adapter."""

    def test_component_run_query_generates_receipt(self):
        """Test component run with query generates receipt."""
        component = TorkHaystackComponent()
        result = component.run(query="Test query")
        assert len(component.receipts) == 1
        assert "receipt_id" in component.receipts[0]
        assert "has_pii" in component.receipts[0]

    def test_component_run_text_generates_receipt(self):
        """Test component run with text generates receipt."""
        component = TorkHaystackComponent()
        result = component.run(text="Test text")
        assert len(component.receipts) == 1

    def test_get_receipts(self):
        """Test get_receipts method."""
        component = TorkHaystackComponent()
        component.run(query="Query 1")
        component.run(query="Query 2")
        receipts = component.get_receipts()
        assert len(receipts) == 2


class TestHaystackPipelineGovernance:
    """Test pipeline governance."""

    def test_pipeline_run_governs_inputs(self):
        """Test pipeline run governs inputs."""
        class MockPipeline:
            def run(self, inputs):
                return {"output": inputs.get("query", "")}

        pipeline = TorkHaystackPipeline(MockPipeline())
        result = pipeline.run({"query": PII_MESSAGES["email_message"]})
        assert PII_SAMPLES["email"] not in result.get("output", "")

    def test_pipeline_run_governs_outputs(self):
        """Test pipeline run governs outputs."""
        class MockPipeline:
            def run(self, inputs):
                return {"answer": PII_MESSAGES["ssn_message"]}

        pipeline = TorkHaystackPipeline(MockPipeline())
        result = pipeline.run({"query": "test"})
        assert PII_SAMPLES["ssn"] not in result.get("answer", "")

    def test_pipeline_governs_nested_dict(self):
        """Test pipeline governs nested dictionaries."""
        class MockPipeline:
            def run(self, inputs):
                return {"nested": {"data": inputs.get("query", "")}}

        pipeline = TorkHaystackPipeline(MockPipeline())
        result = pipeline.run({"query": PII_MESSAGES["phone_message"]})
        # The nested value should be governed
        assert len(pipeline.receipts) >= 1

    def test_pipeline_governs_lists(self):
        """Test pipeline governs lists."""
        class MockPipeline:
            def run(self, inputs):
                return {"items": [inputs.get("query", "")]}

        pipeline = TorkHaystackPipeline(MockPipeline())
        result = pipeline.run({"query": "test"})
        assert "items" in result


class TestHaystackDocumentStoreGovernance:
    """Test document store governance."""

    def test_component_run_documents(self):
        """Test component governs documents."""
        component = TorkHaystackComponent()

        class MockDoc:
            content = PII_MESSAGES["email_message"]

        result = component.run(documents=[MockDoc()])
        assert PII_SAMPLES["email"] not in result["documents"][0].content

    def test_component_document_receipts(self):
        """Test component generates document receipts."""
        component = TorkHaystackComponent()

        class MockDoc:
            content = "Doc 1"

        class MockDoc2:
            content = "Doc 2"

        result = component.run(documents=[MockDoc(), MockDoc2()])
        assert len(result["document_receipts"]) == 2

    def test_document_processor_process(self):
        """Test document processor processes documents."""
        processor = TorkDocumentProcessor()

        class MockDoc:
            content = PII_MESSAGES["ssn_message"]
            meta = {}

        result = processor.process([MockDoc()])
        assert PII_SAMPLES["ssn"] not in result[0].content

    def test_document_processor_adds_metadata(self):
        """Test document processor adds governance metadata."""
        processor = TorkDocumentProcessor()

        class MockDoc:
            content = "Test content"
            meta = {}

        result = processor.process([MockDoc()])
        assert "tork_receipt_id" in result[0].meta
        assert "tork_has_pii" in result[0].meta


class TestHaystackRetrieverGovernance:
    """Test retriever governance."""

    def test_component_run_governs_query(self):
        """Test component run governs retriever query."""
        component = TorkHaystackComponent()
        result = component.run(query=PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result["query"]

    def test_component_governed_query_alias(self):
        """Test governed_query is available."""
        component = TorkHaystackComponent()
        result = component.run(query="test query")
        assert "governed_query" in result
        assert result["governed_query"] == result["query"]

    def test_component_query_receipt_has_pii_flag(self):
        """Test query receipt includes has_pii flag."""
        component = TorkHaystackComponent()
        result = component.run(query=PII_MESSAGES["email_message"])
        assert result["query_receipt"]["has_pii"] is True

    def test_component_clean_query_has_pii_false(self):
        """Test clean query has has_pii=False."""
        component = TorkHaystackComponent()
        result = component.run(query="What is machine learning?")
        assert result["query_receipt"]["has_pii"] is False


class TestHaystackReaderGovernance:
    """Test reader governance."""

    def test_pipeline_governs_reader_input(self):
        """Test pipeline governs reader input."""
        class MockPipeline:
            def run(self, inputs):
                return {"reader_input": inputs.get("context", "")}

        pipeline = TorkHaystackPipeline(MockPipeline())
        result = pipeline.run({"context": PII_MESSAGES["credit_card_message"]})
        assert PII_SAMPLES["credit_card"] not in result.get("reader_input", "")

    def test_pipeline_governs_reader_output(self):
        """Test pipeline governs reader output."""
        class MockPipeline:
            def run(self, inputs):
                return {"answer": PII_MESSAGES["phone_message"]}

        pipeline = TorkHaystackPipeline(MockPipeline())
        result = pipeline.run({"query": "test"})
        assert PII_SAMPLES["phone_us"] not in result.get("answer", "")

    def test_pipeline_receipts_for_reader(self):
        """Test pipeline generates receipts for reader operations."""
        class MockPipeline:
            def run(self, inputs):
                return {"answer": "test"}

        pipeline = TorkHaystackPipeline(MockPipeline())
        pipeline.run({"query": "test", "context": "context"})
        assert len(pipeline.get_receipts()) >= 1


class TestHaystackGeneratorGovernance:
    """Test generator governance."""

    def test_component_governs_generation_input(self):
        """Test component governs generation input."""
        component = TorkHaystackComponent()
        result = component.run(text=PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result["text"]

    def test_pipeline_governs_generation_output(self):
        """Test pipeline governs generation output."""
        class MockPipeline:
            def run(self, inputs):
                return {"generated": PII_MESSAGES["email_message"]}

        pipeline = TorkHaystackPipeline(MockPipeline())
        result = pipeline.run({"prompt": "Generate text"})
        assert PII_SAMPLES["email"] not in result.get("generated", "")

    def test_document_processor_receipts(self):
        """Test document processor generates receipts."""
        processor = TorkDocumentProcessor()

        class MockDoc:
            content = "Test"

        processor.process([MockDoc(), MockDoc()])
        assert len(processor.receipts) == 2

    def test_component_multiple_inputs(self):
        """Test component handles multiple inputs."""
        component = TorkHaystackComponent()

        class MockDoc:
            content = "Doc content"

        result = component.run(
            query=PII_MESSAGES["email_message"],
            text="Some text",
            documents=[MockDoc()]
        )

        assert "query" in result
        assert "text" in result
        assert "documents" in result
        assert len(component.receipts) == 3  # query + text + document
