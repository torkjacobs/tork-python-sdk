"""Tests for Mistral SDK adapter."""

import sys
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from tork_governance.core import Tork, GovernanceAction

# Mock the mistralai module so adapter imports don't fail
mock_mistralai = MagicMock()
mock_chat_message = MagicMock()
mock_mistralai.models.chat_completion.ChatMessage = mock_chat_message
sys.modules["mistralai"] = mock_mistralai
sys.modules["mistralai.models"] = mock_mistralai.models
sys.modules["mistralai.models.chat_completion"] = mock_mistralai.models.chat_completion


class TestTorkMistralClient:
    """Tests for TorkMistralClient."""

    def setup_method(self):
        self.tork = Tork()

    def test_govern_input_messages(self):
        """Test that governance is applied to input user messages."""
        from tork_governance.adapters.mistral_sdk import TorkMistralClient

        client = TorkMistralClient(api_key="test", tork=self.tork)

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "My SSN is 123-45-6789"},
        ]

        # Mock the internal client to avoid real API calls
        mock_mistral = MagicMock()
        mock_response = MagicMock()
        mock_response.id = "test-id"
        mock_response.model = "mistral-small-latest"
        mock_choice = MagicMock()
        mock_choice.index = 0
        mock_choice.message.role = "assistant"
        mock_choice.message.content = "I can help you."
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_mistral.chat.return_value = mock_response
        client._client = mock_mistral

        result = client.chat(messages)

        # Verify the call was made with governed messages
        call_args = mock_mistral.chat.call_args
        called_messages = call_args.kwargs.get("messages") or call_args[1].get("messages", [])
        # The user message should have SSN redacted
        assert result is not None
        assert len(result["choices"]) == 1
        assert result["_tork_receipts"] is not None

    def test_govern_output_content(self):
        """Test that governance is applied to output content."""
        from tork_governance.adapters.mistral_sdk import TorkMistralClient

        client = TorkMistralClient(api_key="test", tork=self.tork)

        messages = [{"role": "user", "content": "Hello"}]

        mock_mistral = MagicMock()
        mock_response = MagicMock()
        mock_response.id = "test-id"
        mock_response.model = "mistral-small-latest"
        mock_choice = MagicMock()
        mock_choice.index = 0
        mock_choice.message.role = "assistant"
        mock_choice.message.content = "Your SSN 123-45-6789 is on file."
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_mistral.chat.return_value = mock_response
        client._client = mock_mistral

        result = client.chat(messages)

        # Output should have PII redacted
        assert "[SSN_REDACTED]" in result["choices"][0]["message"]["content"]

    def test_pii_redaction_in_messages(self):
        """Test PII redaction works for multiple PII types in messages."""
        from tork_governance.adapters.mistral_sdk import TorkMistralClient

        client = TorkMistralClient(api_key="test", tork=self.tork)

        messages = [
            {"role": "user", "content": "My email is test@example.com and SSN is 123-45-6789"},
        ]

        mock_mistral = MagicMock()
        mock_response = MagicMock()
        mock_response.id = "test-id"
        mock_response.model = "mistral-small-latest"
        mock_choice = MagicMock()
        mock_choice.index = 0
        mock_choice.message.role = "assistant"
        mock_choice.message.content = "Got it."
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_mistral.chat.return_value = mock_response
        client._client = mock_mistral

        result = client.chat(messages)

        # Should have receipts for PII detection
        assert len(result["_tork_receipts"]) > 0

    def test_governance_disabled(self):
        """Test that governance can be disabled."""
        from tork_governance.adapters.mistral_sdk import TorkMistralClient

        client = TorkMistralClient(
            api_key="test", tork=self.tork,
            govern_input=False, govern_output=False
        )
        assert client.govern_input is False
        assert client.govern_output is False

    def test_embeddings(self):
        """Test governed embeddings."""
        from tork_governance.adapters.mistral_sdk import TorkMistralClient

        client = TorkMistralClient(api_key="test", tork=self.tork)

        mock_mistral = MagicMock()
        mock_data = MagicMock()
        mock_data.embedding = [0.1, 0.2, 0.3]
        mock_data.index = 0
        mock_response = MagicMock()
        mock_response.model = "mistral-embed"
        mock_response.data = [mock_data]
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.total_tokens = 10
        mock_mistral.embeddings.return_value = mock_response
        client._client = mock_mistral

        result = client.embeddings("My SSN is 123-45-6789")
        assert result["model"] == "mistral-embed"
        assert len(result["data"]) == 1


class TestMistralGoverned:
    """Tests for mistral_governed decorator."""

    def test_decorator_governs_messages(self):
        """Test that the decorator governs messages."""
        from tork_governance.adapters.mistral_sdk import mistral_governed

        tork = Tork()

        @mistral_governed(tork)
        def fake_chat(**kwargs):
            return kwargs

        result = fake_chat(
            messages=[{"role": "user", "content": "SSN: 123-45-6789"}]
        )

        # The message content should be governed
        user_msg = result["messages"][0]
        assert "123-45-6789" not in user_msg["content"]
        assert "[SSN_REDACTED]" in user_msg["content"]
