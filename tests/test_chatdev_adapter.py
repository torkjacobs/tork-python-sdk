"""Tests for ChatDev adapter."""

import pytest
from unittest.mock import MagicMock
from tork_governance.core import Tork


class TestTorkChatDevPhase:
    """Tests for TorkChatDevPhase."""

    def setup_method(self):
        self.tork = Tork()

    def test_govern_task_input(self):
        """Test that governance is applied to task input."""
        from tork_governance.adapters.chatdev_adapter import TorkChatDevPhase

        phase = TorkChatDevPhase(tork=self.tork)

        result = phase.run("Build app with SSN 123-45-6789")

        assert "[SSN_REDACTED]" in result["task"]
        assert "123-45-6789" not in result["task"]
        assert len(result["_tork_receipts"]) > 0

    def test_govern_chat_messages(self):
        """Test that governance is applied to chat messages."""
        from tork_governance.adapters.chatdev_adapter import TorkChatDevPhase

        phase = TorkChatDevPhase(tork=self.tork)

        messages = [
            {"role": "CEO", "content": "Email is admin@secret.com"},
            {"role": "CTO", "content": "Noted"},
        ]

        result = phase.govern_chat_messages(messages)

        assert "[EMAIL_REDACTED]" in result["messages"][0]["content"]
        assert len(result["_tork_receipts"]) == 2

    def test_govern_code_output(self):
        """Test that governance is applied to code output."""
        from tork_governance.adapters.chatdev_adapter import TorkChatDevPhase

        phase = TorkChatDevPhase(tork=self.tork)

        result = phase.govern_code_output('password = "SSN: 123-45-6789"')

        assert "[SSN_REDACTED]" in result["code"]
        assert "123-45-6789" not in result["code"]

    def test_skip_governance_when_disabled(self):
        """Test that governance can be disabled."""
        from tork_governance.adapters.chatdev_adapter import TorkChatDevPhase

        phase = TorkChatDevPhase(tork=self.tork, govern_input=False)

        result = phase.run("SSN: 123-45-6789")

        assert result["task"] == "SSN: 123-45-6789"
        assert len(result["_tork_receipts"]) == 0


class TestChatDevGoverned:
    """Tests for chatdev_governed decorator."""

    def test_decorator_governs_task(self):
        """Test that the decorator governs task kwarg."""
        from tork_governance.adapters.chatdev_adapter import chatdev_governed

        tork = Tork()

        @chatdev_governed(tork)
        def fake_phase(**kwargs):
            return kwargs

        result = fake_phase(task="My email is test@example.com")

        assert "test@example.com" not in result["task"]
        assert "[EMAIL_REDACTED]" in result["task"]

    def test_decorator_governs_messages(self):
        """Test that the decorator governs messages kwarg."""
        from tork_governance.adapters.chatdev_adapter import chatdev_governed

        tork = Tork()

        @chatdev_governed(tork)
        def fake_phase(**kwargs):
            return kwargs

        result = fake_phase(messages=[
            {"role": "user", "content": "SSN: 123-45-6789"}
        ])

        assert "[SSN_REDACTED]" in result["messages"][0]["content"]
