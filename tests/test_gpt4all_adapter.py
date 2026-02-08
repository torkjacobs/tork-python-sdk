"""Tests for GPT4All adapter."""

import pytest
from unittest.mock import MagicMock, patch
from tork_governance.core import Tork


class TestTorkGPT4All:
    """Tests for TorkGPT4All."""

    def setup_method(self):
        self.tork = Tork()

    def test_govern_generate_input(self):
        """Test that governance is applied to generate input."""
        from tork_governance.adapters.gpt4all_adapter import TorkGPT4All

        client = TorkGPT4All(tork=self.tork)

        mock_model = MagicMock()
        mock_model.generate.return_value = "I can help."
        client._model = mock_model

        result = client.generate("My SSN is 123-45-6789")

        call_args = mock_model.generate.call_args[0][0]
        assert "[SSN_REDACTED]" in call_args
        assert "123-45-6789" not in call_args
        assert len(result["_tork_receipts"]) > 0

    def test_govern_generate_output(self):
        """Test that governance is applied to generate output."""
        from tork_governance.adapters.gpt4all_adapter import TorkGPT4All

        client = TorkGPT4All(tork=self.tork)

        mock_model = MagicMock()
        mock_model.generate.return_value = "Contact john@example.com"
        client._model = mock_model

        result = client.generate("Hello")

        assert "[EMAIL_REDACTED]" in result["content"]

    def test_govern_chat_messages(self):
        """Test that governance is applied to chat messages."""
        from tork_governance.adapters.gpt4all_adapter import TorkGPT4All

        client = TorkGPT4All(tork=self.tork)

        mock_model = MagicMock()
        mock_model.generate.return_value = "Noted."
        client._model = mock_model

        messages = [
            {"role": "user", "content": "My SSN is 123-45-6789"},
        ]

        result = client.chat(messages)

        assert len(result["_tork_receipts"]) > 0

    def test_chat_completion_format(self):
        """Test that chat_completion returns OpenAI-compatible format."""
        from tork_governance.adapters.gpt4all_adapter import TorkGPT4All

        client = TorkGPT4All(tork=self.tork)

        mock_model = MagicMock()
        mock_model.generate.return_value = "Hello there"
        client._model = mock_model

        result = client.chat_completion([{"role": "user", "content": "Hi"}])

        assert "choices" in result
        assert result["choices"][0]["message"]["role"] == "assistant"

    def test_skip_governance_when_disabled(self):
        """Test that governance can be disabled."""
        from tork_governance.adapters.gpt4all_adapter import TorkGPT4All

        client = TorkGPT4All(tork=self.tork, govern_input=False, govern_output=False)

        mock_model = MagicMock()
        mock_model.generate.return_value = "SSN: 123-45-6789"
        client._model = mock_model

        result = client.generate("My SSN is 123-45-6789")

        assert len(result["_tork_receipts"]) == 0


class TestGPT4AllGoverned:
    """Tests for gpt4all_governed decorator."""

    def test_decorator_governs_prompt(self):
        """Test that the decorator governs prompt kwarg."""
        from tork_governance.adapters.gpt4all_adapter import gpt4all_governed

        tork = Tork()

        @gpt4all_governed(tork)
        def fake_generate(**kwargs):
            return kwargs

        result = fake_generate(prompt="My email is test@example.com")

        assert "test@example.com" not in result["prompt"]
        assert "[EMAIL_REDACTED]" in result["prompt"]

    def test_decorator_governs_messages(self):
        """Test that the decorator governs messages kwarg."""
        from tork_governance.adapters.gpt4all_adapter import gpt4all_governed

        tork = Tork()

        @gpt4all_governed(tork)
        def fake_chat(**kwargs):
            return kwargs

        result = fake_chat(
            messages=[{"role": "user", "content": "SSN: 123-45-6789"}]
        )

        assert "[SSN_REDACTED]" in result["messages"][0]["content"]
