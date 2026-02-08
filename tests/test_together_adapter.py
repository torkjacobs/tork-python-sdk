"""Tests for Together AI SDK adapter."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from tork_governance.core import Tork, GovernanceAction


class TestTorkTogetherClient:
    """Tests for TorkTogetherClient."""

    def setup_method(self):
        self.tork = Tork()

    def test_govern_input_messages(self):
        """Test that governance is applied to input user messages."""
        from tork_governance.adapters.together_sdk import TorkTogetherClient

        client = TorkTogetherClient(api_key="test", tork=self.tork)

        messages = [
            {"role": "user", "content": "My SSN is 123-45-6789"},
        ]

        mock_together = MagicMock()
        mock_response = MagicMock()
        mock_response.id = "test-id"
        mock_response.model = "meta-llama/Llama-3-70b-chat-hf"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_choice = MagicMock()
        mock_choice.index = 0
        mock_choice.message.role = "assistant"
        mock_choice.message.content = "Understood."
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_together.chat.completions.create.return_value = mock_response
        client._client = mock_together

        result = client.chat(messages)

        assert len(result["_tork_receipts"]) > 0
        assert result["choices"][0]["message"]["content"] == "Understood."

    def test_govern_output_content(self):
        """Test that governance is applied to output content."""
        from tork_governance.adapters.together_sdk import TorkTogetherClient

        client = TorkTogetherClient(api_key="test", tork=self.tork)

        mock_together = MagicMock()
        mock_response = MagicMock()
        mock_response.id = "test-id"
        mock_response.model = "meta-llama/Llama-3-70b-chat-hf"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 15
        mock_response.usage.total_tokens = 25
        mock_choice = MagicMock()
        mock_choice.index = 0
        mock_choice.message.role = "assistant"
        mock_choice.message.content = "Call me at 555-123-4567"
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_together.chat.completions.create.return_value = mock_response
        client._client = mock_together

        result = client.chat([{"role": "user", "content": "Hello"}])

        assert "[PHONE_REDACTED]" in result["choices"][0]["message"]["content"]

    def test_pii_redaction_in_messages(self):
        """Test PII redaction for email in messages."""
        from tork_governance.adapters.together_sdk import TorkTogetherClient

        client = TorkTogetherClient(api_key="test", tork=self.tork)

        messages = [
            {"role": "user", "content": "Email me at admin@secret.com"},
        ]

        mock_together = MagicMock()
        mock_response = MagicMock()
        mock_response.id = "test-id"
        mock_response.model = "meta-llama/Llama-3-70b-chat-hf"
        mock_response.usage = None
        mock_choice = MagicMock()
        mock_choice.index = 0
        mock_choice.message.role = "assistant"
        mock_choice.message.content = "OK."
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_together.chat.completions.create.return_value = mock_response
        client._client = mock_together

        result = client.chat(messages)

        assert len(result["_tork_receipts"]) > 0

    def test_complete_governs_prompt(self):
        """Test that the complete method governs the prompt."""
        from tork_governance.adapters.together_sdk import TorkTogetherClient

        client = TorkTogetherClient(api_key="test", tork=self.tork)

        mock_together = MagicMock()
        mock_response = MagicMock()
        mock_response.id = "test-id"
        mock_response.model = "meta-llama/Llama-3-70b-chat-hf"
        mock_response.usage = None
        mock_text_choice = MagicMock()
        mock_text_choice.text = "Response text"
        mock_response.choices = [mock_text_choice]
        mock_together.completions.create.return_value = mock_response
        client._client = mock_together

        result = client.complete("My SSN is 123-45-6789")

        # Prompt should have been governed before API call
        call_args = mock_together.completions.create.call_args
        called_prompt = call_args.kwargs.get("prompt", "")
        assert "123-45-6789" not in called_prompt
        assert result["_tork_receipt"] is not None


class TestTogetherGoverned:
    """Tests for together_governed decorator."""

    def test_decorator_governs_messages(self):
        """Test that the decorator governs messages."""
        from tork_governance.adapters.together_sdk import together_governed

        tork = Tork()

        @together_governed(tork)
        def fake_chat(**kwargs):
            return kwargs

        result = fake_chat(
            messages=[{"role": "user", "content": "SSN: 123-45-6789"}]
        )

        user_msg = result["messages"][0]
        assert "123-45-6789" not in user_msg["content"]

    def test_decorator_governs_prompt(self):
        """Test that the decorator governs prompt."""
        from tork_governance.adapters.together_sdk import together_governed

        tork = Tork()

        @together_governed(tork)
        def fake_complete(**kwargs):
            return kwargs

        result = fake_complete(prompt="My email is test@example.com")

        assert "test@example.com" not in result["prompt"]
        assert "[EMAIL_REDACTED]" in result["prompt"]
