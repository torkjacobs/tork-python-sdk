"""Tests for Groq SDK adapter."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from tork_governance.core import Tork, GovernanceAction


class TestTorkGroqClient:
    """Tests for TorkGroqClient."""

    def setup_method(self):
        self.tork = Tork()

    def test_govern_input_messages(self):
        """Test that governance is applied to input user messages."""
        from tork_governance.adapters.groq_sdk import TorkGroqClient

        client = TorkGroqClient(api_key="test", tork=self.tork)

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "My SSN is 123-45-6789"},
        ]

        mock_groq = MagicMock()
        mock_response = MagicMock()
        mock_response.id = "test-id"
        mock_response.model = "llama-3.1-70b-versatile"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_choice = MagicMock()
        mock_choice.index = 0
        mock_choice.message.role = "assistant"
        mock_choice.message.content = "I can help you."
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_groq.chat.completions.create.return_value = mock_response
        client._client = mock_groq

        result = client.chat(messages)

        # Verify governance was applied
        call_args = mock_groq.chat.completions.create.call_args
        called_messages = call_args.kwargs.get("messages") or call_args[1].get("messages", [])
        assert result is not None
        assert len(result["_tork_receipts"]) > 0

    def test_govern_output_content(self):
        """Test that governance is applied to output content."""
        from tork_governance.adapters.groq_sdk import TorkGroqClient

        client = TorkGroqClient(api_key="test", tork=self.tork)

        mock_groq = MagicMock()
        mock_response = MagicMock()
        mock_response.id = "test-id"
        mock_response.model = "llama-3.1-70b-versatile"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 15
        mock_response.usage.total_tokens = 25
        mock_choice = MagicMock()
        mock_choice.index = 0
        mock_choice.message.role = "assistant"
        mock_choice.message.content = "Contact john@example.com for details."
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_groq.chat.completions.create.return_value = mock_response
        client._client = mock_groq

        result = client.chat([{"role": "user", "content": "Hello"}])

        assert "[EMAIL_REDACTED]" in result["choices"][0]["message"]["content"]

    def test_pii_redaction_in_messages(self):
        """Test PII redaction works for multiple PII types in messages."""
        from tork_governance.adapters.groq_sdk import TorkGroqClient

        client = TorkGroqClient(api_key="test", tork=self.tork)

        messages = [
            {"role": "user", "content": "Card 4111-1111-1111-1111 and email test@example.com"},
        ]

        mock_groq = MagicMock()
        mock_response = MagicMock()
        mock_response.id = "test-id"
        mock_response.model = "llama-3.1-70b-versatile"
        mock_response.usage.prompt_tokens = 20
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 25
        mock_choice = MagicMock()
        mock_choice.index = 0
        mock_choice.message.role = "assistant"
        mock_choice.message.content = "Noted."
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_groq.chat.completions.create.return_value = mock_response
        client._client = mock_groq

        result = client.chat(messages)

        assert len(result["_tork_receipts"]) > 0

    def test_transcribe_governs_output(self):
        """Test that transcribe governs output text."""
        from tork_governance.adapters.groq_sdk import TorkGroqClient

        client = TorkGroqClient(api_key="test", tork=self.tork)

        mock_groq = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.text = "My SSN is 123-45-6789"
        mock_groq.audio.transcriptions.create.return_value = mock_transcription
        client._client = mock_groq

        result = client.transcribe(file=b"fake-audio")

        assert "[SSN_REDACTED]" in result["text"]
        assert "123-45-6789" not in result["text"]


class TestGroqGoverned:
    """Tests for groq_governed decorator."""

    def test_decorator_governs_messages(self):
        """Test that the decorator governs messages."""
        from tork_governance.adapters.groq_sdk import groq_governed

        tork = Tork()

        @groq_governed(tork)
        def fake_chat(**kwargs):
            return kwargs

        result = fake_chat(
            messages=[{"role": "user", "content": "My email is test@example.com"}]
        )

        user_msg = result["messages"][0]
        assert "test@example.com" not in user_msg["content"]
        assert "[EMAIL_REDACTED]" in user_msg["content"]
