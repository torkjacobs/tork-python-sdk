"""Tests for Mirascope adapter."""

import pytest
from unittest.mock import MagicMock
from tork_governance.core import Tork


class TestTorkMirascopeCall:
    """Tests for TorkMirascopeCall."""

    def setup_method(self):
        self.tork = Tork()

    def test_govern_input_prompt(self):
        """Test that governance is applied to input prompt."""
        from tork_governance.adapters.mirascope_adapter import TorkMirascopeCall

        client = TorkMirascopeCall(tork=self.tork)

        mock_mirascope = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "I can help you."
        mock_mirascope.chat.return_value = mock_response
        client._client = mock_mirascope

        result = client.call("My SSN is 123-45-6789")

        call_args = mock_mirascope.chat.call_args
        sent_messages = call_args.kwargs.get("messages") or call_args[1].get("messages", [])
        assert "[SSN_REDACTED]" in sent_messages[0]["content"]
        assert "123-45-6789" not in sent_messages[0]["content"]
        assert len(result["_tork_receipts"]) > 0

    def test_govern_output_content(self):
        """Test that governance is applied to output content."""
        from tork_governance.adapters.mirascope_adapter import TorkMirascopeCall

        client = TorkMirascopeCall(tork=self.tork)

        mock_mirascope = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Contact john@example.com for details."
        mock_mirascope.chat.return_value = mock_response
        client._client = mock_mirascope

        result = client.call("Hello")

        assert "[EMAIL_REDACTED]" in result["content"]

    def test_skip_governance_when_disabled(self):
        """Test that governance can be disabled."""
        from tork_governance.adapters.mirascope_adapter import TorkMirascopeCall

        client = TorkMirascopeCall(tork=self.tork, govern_input=False, govern_output=False)

        mock_mirascope = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "SSN: 123-45-6789"
        mock_mirascope.chat.return_value = mock_response
        client._client = mock_mirascope

        result = client.call("My SSN is 123-45-6789")

        assert len(result["_tork_receipts"]) == 0

    def test_receipts_generated(self):
        """Test that governance receipts are generated."""
        from tork_governance.adapters.mirascope_adapter import TorkMirascopeCall

        client = TorkMirascopeCall(tork=self.tork)

        mock_mirascope = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "OK"
        mock_mirascope.chat.return_value = mock_response
        client._client = mock_mirascope

        result = client.call("My email is test@example.com")

        assert len(result["_tork_receipts"]) == 1
        assert result["_tork_receipts"][0] is not None


class TestMirascopeGoverned:
    """Tests for mirascope_governed decorator."""

    def test_decorator_governs_prompt(self):
        """Test that the decorator governs prompt arguments."""
        from tork_governance.adapters.mirascope_adapter import mirascope_governed

        tork = Tork()

        @mirascope_governed(tork)
        def fake_call(prompt):
            return prompt

        result = fake_call(prompt="My email is test@example.com")

        assert "test@example.com" not in result
        assert "[EMAIL_REDACTED]" in result
