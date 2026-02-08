"""Tests for Magentic adapter."""

import pytest
from unittest.mock import MagicMock
from tork_governance.core import Tork


class TestTorkMagenticPrompt:
    """Tests for TorkMagenticPrompt."""

    def setup_method(self):
        self.tork = Tork()

    def test_govern_input_prompt(self):
        """Test that governance is applied to input prompt."""
        from tork_governance.adapters.magentic_adapter import TorkMagenticPrompt

        client = TorkMagenticPrompt(tork=self.tork)

        mock_magentic = MagicMock()
        mock_magentic.prompt.return_value = "I can help."
        client._client = mock_magentic

        result = client.call("My SSN is 123-45-6789")

        call_args = mock_magentic.prompt.call_args
        sent_prompt = call_args[0][0]
        assert "[SSN_REDACTED]" in sent_prompt
        assert "123-45-6789" not in sent_prompt
        assert len(result["_tork_receipts"]) > 0

    def test_govern_output_content(self):
        """Test that governance is applied to output content."""
        from tork_governance.adapters.magentic_adapter import TorkMagenticPrompt

        client = TorkMagenticPrompt(tork=self.tork)

        mock_magentic = MagicMock()
        mock_magentic.prompt.return_value = "Contact john@example.com"
        client._client = mock_magentic

        result = client.call("Hello")

        assert "[EMAIL_REDACTED]" in result["content"]

    def test_skip_governance_when_disabled(self):
        """Test that governance can be disabled."""
        from tork_governance.adapters.magentic_adapter import TorkMagenticPrompt

        client = TorkMagenticPrompt(tork=self.tork, govern_input=False, govern_output=False)

        mock_magentic = MagicMock()
        mock_magentic.prompt.return_value = "OK"
        client._client = mock_magentic

        result = client.call("My SSN is 123-45-6789")

        assert len(result["_tork_receipts"]) == 0

    def test_wrap_prompt_function(self):
        """Test that wrap_prompt_function applies governance."""
        from tork_governance.adapters.magentic_adapter import TorkMagenticPrompt

        client = TorkMagenticPrompt(tork=self.tork)

        def my_prompt(text: str) -> str:
            return text

        wrapped = client.wrap_prompt_function(my_prompt)
        result = wrapped("My SSN is 123-45-6789")

        assert "[SSN_REDACTED]" in result
        assert "123-45-6789" not in result


class TestMagenticGoverned:
    """Tests for magentic_governed decorator."""

    def test_decorator_governs_input(self):
        """Test that the decorator governs input arguments."""
        from tork_governance.adapters.magentic_adapter import magentic_governed

        tork = Tork()

        @magentic_governed(tork)
        def fake_prompt(text):
            return text

        result = fake_prompt("My email is test@example.com")

        assert "test@example.com" not in result
        assert "[EMAIL_REDACTED]" in result

    def test_decorator_governs_output(self):
        """Test that the decorator governs output."""
        from tork_governance.adapters.magentic_adapter import magentic_governed

        tork = Tork()

        @magentic_governed(tork, govern_input=False)
        def fake_prompt():
            return "Contact john@example.com"

        result = fake_prompt()

        assert "[EMAIL_REDACTED]" in result
