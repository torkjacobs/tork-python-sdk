"""Tests for LLM Guard adapter."""

import pytest
from unittest.mock import MagicMock
from tork_governance.core import Tork


class TestTorkLLMGuard:
    """Tests for TorkLLMGuard."""

    def setup_method(self):
        self.tork = Tork()

    def test_govern_scan_prompt(self):
        """Test that governance is applied to scan_prompt."""
        from tork_governance.adapters.llm_guard_adapter import TorkLLMGuard

        guard = TorkLLMGuard(tork=self.tork)

        result = guard.scan_prompt("My SSN is 123-45-6789")

        assert "[SSN_REDACTED]" in result["prompt"]
        assert "123-45-6789" not in result["prompt"]
        assert len(result["_tork_receipts"]) > 0

    def test_govern_scan_output(self):
        """Test that governance is applied to scan_output."""
        from tork_governance.adapters.llm_guard_adapter import TorkLLMGuard

        guard = TorkLLMGuard(tork=self.tork)

        result = guard.scan_output(
            prompt="Hello",
            output="Contact john@example.com for details."
        )

        assert "[EMAIL_REDACTED]" in result["output"]
        assert len(result["_tork_receipts"]) > 0

    def test_govern_scan_both(self):
        """Test that governance is applied to both prompt and output."""
        from tork_governance.adapters.llm_guard_adapter import TorkLLMGuard

        guard = TorkLLMGuard(tork=self.tork)

        result = guard.scan_prompt_and_output(
            prompt="My SSN is 123-45-6789",
            output="Email: admin@secret.com"
        )

        assert "[SSN_REDACTED]" in result["prompt"]
        assert "[EMAIL_REDACTED]" in result["output"]
        assert len(result["_tork_receipts"]) == 2

    def test_skip_governance_when_disabled(self):
        """Test that governance can be disabled."""
        from tork_governance.adapters.llm_guard_adapter import TorkLLMGuard

        guard = TorkLLMGuard(tork=self.tork, govern_input=False, govern_output=False)

        result = guard.scan_prompt("SSN: 123-45-6789")

        assert result["prompt"] == "SSN: 123-45-6789"
        assert len(result["_tork_receipts"]) == 0


class TestLLMGuardGoverned:
    """Tests for llm_guard_governed decorator."""

    def test_decorator_governs_prompt(self):
        """Test that the decorator governs prompt kwarg."""
        from tork_governance.adapters.llm_guard_adapter import llm_guard_governed

        tork = Tork()

        @llm_guard_governed(tork)
        def fake_scan(**kwargs):
            return kwargs

        result = fake_scan(prompt="My email is test@example.com")

        assert "test@example.com" not in result["prompt"]
        assert "[EMAIL_REDACTED]" in result["prompt"]

    def test_decorator_governs_output(self):
        """Test that the decorator governs output kwarg."""
        from tork_governance.adapters.llm_guard_adapter import llm_guard_governed

        tork = Tork()

        @llm_guard_governed(tork)
        def fake_scan(**kwargs):
            return kwargs

        result = fake_scan(output="SSN: 123-45-6789")

        assert "[SSN_REDACTED]" in result["output"]
