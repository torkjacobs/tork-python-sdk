"""Tests for txtai adapter."""

import pytest
from unittest.mock import MagicMock
from tork_governance.core import Tork


class TestTorkTxtaiEmbeddings:
    """Tests for TorkTxtaiEmbeddings."""

    def setup_method(self):
        self.tork = Tork()

    def test_govern_index_documents(self):
        """Test that governance is applied when indexing documents."""
        from tork_governance.adapters.txtai_adapter import TorkTxtaiEmbeddings

        client = TorkTxtaiEmbeddings(tork=self.tork)

        mock_embeddings = MagicMock()
        client._client = mock_embeddings

        result = client.index(["My SSN is 123-45-6789", "Clean text"])

        call_args = mock_embeddings.index.call_args[0][0]
        assert "[SSN_REDACTED]" in call_args[0]
        assert "123-45-6789" not in call_args[0]
        assert result["indexed"] == 2
        assert len(result["_tork_receipts"]) == 2

    def test_govern_search_query(self):
        """Test that governance is applied to search queries."""
        from tork_governance.adapters.txtai_adapter import TorkTxtaiEmbeddings

        client = TorkTxtaiEmbeddings(tork=self.tork)

        mock_embeddings = MagicMock()
        mock_embeddings.search.return_value = [("doc1", 0.9)]
        client._client = mock_embeddings

        result = client.search("Find SSN 123-45-6789")

        call_args = mock_embeddings.search.call_args
        assert "[SSN_REDACTED]" in call_args[0][0]
        assert len(result["_tork_receipts"]) > 0

    def test_skip_governance_when_disabled(self):
        """Test that governance can be disabled."""
        from tork_governance.adapters.txtai_adapter import TorkTxtaiEmbeddings

        client = TorkTxtaiEmbeddings(tork=self.tork, govern_input=False)

        mock_embeddings = MagicMock()
        client._client = mock_embeddings

        result = client.index(["My SSN is 123-45-6789"])

        call_args = mock_embeddings.index.call_args[0][0]
        assert call_args[0] == "My SSN is 123-45-6789"
        assert len(result["_tork_receipts"]) == 0


class TestTorkTxtaiPipeline:
    """Tests for TorkTxtaiPipeline."""

    def test_govern_pipeline_input(self):
        """Test that governance is applied to pipeline input."""
        from tork_governance.adapters.txtai_adapter import TorkTxtaiPipeline

        tork = Tork()
        pipeline = TorkTxtaiPipeline(tork=tork)

        mock_pipeline = MagicMock()
        mock_pipeline.return_value = "Summary output"
        pipeline._pipeline = mock_pipeline

        result = pipeline.run("My SSN is 123-45-6789")

        call_args = mock_pipeline.call_args[0][0]
        assert "[SSN_REDACTED]" in call_args
        assert len(result["_tork_receipts"]) > 0


class TestTxtaiGoverned:
    """Tests for txtai_governed decorator."""

    def test_decorator_governs_string_input(self):
        """Test that the decorator governs string arguments."""
        from tork_governance.adapters.txtai_adapter import txtai_governed

        tork = Tork()

        @txtai_governed(tork)
        def fake_index(text):
            return text

        result = fake_index("My email is test@example.com")

        assert "test@example.com" not in result
        assert "[EMAIL_REDACTED]" in result

    def test_decorator_governs_list_input(self):
        """Test that the decorator governs list arguments."""
        from tork_governance.adapters.txtai_adapter import txtai_governed

        tork = Tork()

        @txtai_governed(tork)
        def fake_index(docs):
            return docs

        result = fake_index(["My SSN is 123-45-6789", "Clean text"])

        assert "[SSN_REDACTED]" in result[0]
        assert "123-45-6789" not in result[0]
