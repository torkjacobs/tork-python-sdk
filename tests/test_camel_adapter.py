"""Tests for CAMEL adapter."""

import pytest
from unittest.mock import MagicMock
from tork_governance.core import Tork


class TestTorkCamelAgent:
    """Tests for TorkCamelAgent."""

    def setup_method(self):
        self.tork = Tork()

    def test_govern_step_input(self):
        """Test that governance is applied to step input."""
        from tork_governance.adapters.camel_adapter import TorkCamelAgent

        agent = TorkCamelAgent(tork=self.tork, role="assistant")

        mock_agent = MagicMock()
        mock_response = MagicMock()
        mock_response.msg.content = "I can help."
        mock_agent.step.return_value = mock_response
        agent._agent = mock_agent

        result = agent.step("My SSN is 123-45-6789")

        call_args = mock_agent.step.call_args[0][0]
        assert "[SSN_REDACTED]" in call_args
        assert "123-45-6789" not in call_args
        assert len(result["_tork_receipts"]) > 0

    def test_govern_step_output(self):
        """Test that governance is applied to step output."""
        from tork_governance.adapters.camel_adapter import TorkCamelAgent

        agent = TorkCamelAgent(tork=self.tork)

        mock_agent = MagicMock()
        mock_response = MagicMock()
        mock_response.msg.content = "Contact john@example.com"
        mock_agent.step.return_value = mock_response
        agent._agent = mock_agent

        result = agent.step("Hello")

        assert "[EMAIL_REDACTED]" in result["content"]

    def test_skip_governance_when_disabled(self):
        """Test that governance can be disabled."""
        from tork_governance.adapters.camel_adapter import TorkCamelAgent

        agent = TorkCamelAgent(tork=self.tork, govern_input=False, govern_output=False)

        mock_agent = MagicMock()
        mock_response = MagicMock()
        mock_response.msg.content = "SSN: 123-45-6789"
        mock_agent.step.return_value = mock_response
        agent._agent = mock_agent

        result = agent.step("My SSN is 123-45-6789")

        assert len(result["_tork_receipts"]) == 0


class TestTorkCamelRolePlaying:
    """Tests for TorkCamelRolePlaying."""

    def setup_method(self):
        self.tork = Tork()

    def test_govern_init_chat(self):
        """Test that governance is applied to init_chat task."""
        from tork_governance.adapters.camel_adapter import TorkCamelRolePlaying

        rp = TorkCamelRolePlaying(tork=self.tork)

        result = rp.init_chat("Build app with SSN 123-45-6789")

        assert "[SSN_REDACTED]" in result["task"]
        assert "123-45-6789" not in result["task"]
        assert len(result["_tork_receipts"]) > 0

    def test_govern_step_messages(self):
        """Test that governance is applied to step messages."""
        from tork_governance.adapters.camel_adapter import TorkCamelRolePlaying

        rp = TorkCamelRolePlaying(tork=self.tork)

        messages = [
            {"role": "assistant", "content": "Email: admin@secret.com"},
            {"role": "user", "content": "Got it"},
        ]

        result = rp.step(messages)

        assert "[EMAIL_REDACTED]" in result["messages"][0]["content"]
        assert len(result["_tork_receipts"]) == 2


class TestCamelGoverned:
    """Tests for camel_governed decorator."""

    def test_decorator_governs_message(self):
        """Test that the decorator governs message kwarg."""
        from tork_governance.adapters.camel_adapter import camel_governed

        tork = Tork()

        @camel_governed(tork)
        def fake_step(**kwargs):
            return kwargs

        result = fake_step(message="My email is test@example.com")

        assert "test@example.com" not in result["message"]
        assert "[EMAIL_REDACTED]" in result["message"]
