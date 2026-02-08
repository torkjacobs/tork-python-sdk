"""Tests for PrivateGPT adapter."""

import pytest
from unittest.mock import MagicMock
from tork_governance.core import Tork


class TestTorkPrivateGPT:
    """Tests for TorkPrivateGPT."""

    def setup_method(self):
        self.tork = Tork()

    def test_govern_chat_input(self):
        """Test that governance is applied to chat input messages."""
        from tork_governance.adapters.privategpt_adapter import TorkPrivateGPT

        client = TorkPrivateGPT(tork=self.tork)

        mock_pgpt = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "I can help."
        mock_pgpt.contextual_completions.prompt_completion.return_value = mock_response
        client._client = mock_pgpt

        messages = [
            {"role": "user", "content": "My SSN is 123-45-6789"},
        ]

        result = client.chat(messages)

        call_args = mock_pgpt.contextual_completions.prompt_completion.call_args
        sent_prompt = call_args.kwargs.get("prompt") or call_args[1].get("prompt", "")
        assert "[SSN_REDACTED]" in sent_prompt
        assert "123-45-6789" not in sent_prompt
        assert len(result["_tork_receipts"]) > 0

    def test_govern_chat_output(self):
        """Test that governance is applied to chat output."""
        from tork_governance.adapters.privategpt_adapter import TorkPrivateGPT

        client = TorkPrivateGPT(tork=self.tork)

        mock_pgpt = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Contact john@example.com"
        mock_pgpt.contextual_completions.prompt_completion.return_value = mock_response
        client._client = mock_pgpt

        result = client.chat([{"role": "user", "content": "Hello"}])

        assert "[EMAIL_REDACTED]" in result["content"]

    def test_govern_ingest(self):
        """Test that governance is applied to ingest."""
        from tork_governance.adapters.privategpt_adapter import TorkPrivateGPT

        client = TorkPrivateGPT(tork=self.tork)

        result = client.ingest("My SSN is 123-45-6789")

        assert "[SSN_REDACTED]" in result["text"]
        assert "123-45-6789" not in result["text"]
        assert len(result["_tork_receipts"]) > 0

    def test_skip_governance_when_disabled(self):
        """Test that governance can be disabled."""
        from tork_governance.adapters.privategpt_adapter import TorkPrivateGPT

        client = TorkPrivateGPT(tork=self.tork, govern_input=False, govern_output=False)

        result = client.ingest("SSN: 123-45-6789")

        assert result["text"] == "SSN: 123-45-6789"
        assert len(result["_tork_receipts"]) == 0


class TestPrivateGPTGoverned:
    """Tests for privategpt_governed decorator."""

    def test_decorator_governs_messages(self):
        """Test that the decorator governs messages kwarg."""
        from tork_governance.adapters.privategpt_adapter import privategpt_governed

        tork = Tork()

        @privategpt_governed(tork)
        def fake_chat(**kwargs):
            return kwargs

        result = fake_chat(
            messages=[{"role": "user", "content": "My email is test@example.com"}]
        )

        assert "test@example.com" not in result["messages"][0]["content"]
        assert "[EMAIL_REDACTED]" in result["messages"][0]["content"]

    def test_decorator_governs_query(self):
        """Test that the decorator governs query kwarg."""
        from tork_governance.adapters.privategpt_adapter import privategpt_governed

        tork = Tork()

        @privategpt_governed(tork)
        def fake_query(**kwargs):
            return kwargs

        result = fake_query(query="Find SSN 123-45-6789")

        assert "[SSN_REDACTED]" in result["query"]
