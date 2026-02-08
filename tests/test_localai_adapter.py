"""Tests for LocalAI adapter."""

import pytest
from unittest.mock import MagicMock
from tork_governance.core import Tork


class TestTorkLocalAIClient:
    """Tests for TorkLocalAIClient."""

    def setup_method(self):
        self.tork = Tork()

    def test_govern_input_messages(self):
        """Test that governance is applied to input messages."""
        from tork_governance.adapters.localai_adapter import TorkLocalAIClient

        client = TorkLocalAIClient(tork=self.tork)

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "My SSN is 123-45-6789"},
        ]

        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.id = "test-id"
        mock_response.model = "gpt-3.5-turbo"
        mock_choice = MagicMock()
        mock_choice.index = 0
        mock_choice.message.role = "assistant"
        mock_choice.message.content = "I can help."
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_openai.chat.completions.create.return_value = mock_response
        client._client = mock_openai

        result = client.chat(messages)

        assert len(result["_tork_receipts"]) > 0

    def test_govern_output_content(self):
        """Test that governance is applied to output content."""
        from tork_governance.adapters.localai_adapter import TorkLocalAIClient

        client = TorkLocalAIClient(tork=self.tork)

        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.id = "test-id"
        mock_response.model = "gpt-3.5-turbo"
        mock_choice = MagicMock()
        mock_choice.index = 0
        mock_choice.message.role = "assistant"
        mock_choice.message.content = "Contact john@example.com"
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_openai.chat.completions.create.return_value = mock_response
        client._client = mock_openai

        result = client.chat([{"role": "user", "content": "Hello"}])

        assert "[EMAIL_REDACTED]" in result["choices"][0]["message"]["content"]

    def test_govern_generate(self):
        """Test that governance is applied to generate."""
        from tork_governance.adapters.localai_adapter import TorkLocalAIClient

        client = TorkLocalAIClient(tork=self.tork)

        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.text = "SSN: 123-45-6789"
        mock_response.choices = [mock_choice]
        mock_openai.completions.create.return_value = mock_response
        client._client = mock_openai

        result = client.generate("Tell me something")

        assert "[SSN_REDACTED]" in result["text"]

    def test_skip_governance_when_disabled(self):
        """Test that governance can be disabled."""
        from tork_governance.adapters.localai_adapter import TorkLocalAIClient

        client = TorkLocalAIClient(tork=self.tork, govern_input=False, govern_output=False)

        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.id = "test-id"
        mock_response.model = "gpt-3.5-turbo"
        mock_choice = MagicMock()
        mock_choice.index = 0
        mock_choice.message.role = "assistant"
        mock_choice.message.content = "SSN: 123-45-6789"
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_openai.chat.completions.create.return_value = mock_response
        client._client = mock_openai

        result = client.chat([{"role": "user", "content": "Hello"}])

        assert result["choices"][0]["message"]["content"] == "SSN: 123-45-6789"
        assert len(result["_tork_receipts"]) == 0


class TestLocalAIGoverned:
    """Tests for localai_governed decorator."""

    def test_decorator_governs_messages(self):
        """Test that the decorator governs messages kwarg."""
        from tork_governance.adapters.localai_adapter import localai_governed

        tork = Tork()

        @localai_governed(tork)
        def fake_chat(**kwargs):
            return kwargs

        result = fake_chat(
            messages=[{"role": "user", "content": "My email is test@example.com"}]
        )

        assert "test@example.com" not in result["messages"][0]["content"]
        assert "[EMAIL_REDACTED]" in result["messages"][0]["content"]
