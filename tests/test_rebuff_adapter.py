"""Tests for Rebuff adapter."""

import pytest
from unittest.mock import MagicMock
from tork_governance.core import Tork


class TestTorkRebuff:
    """Tests for TorkRebuff."""

    def setup_method(self):
        self.tork = Tork()

    def test_govern_detect_injection_input(self):
        """Test that governance is applied to detect_injection input."""
        from tork_governance.adapters.rebuff_adapter import TorkRebuff

        client = TorkRebuff(tork=self.tork)

        mock_rebuff = MagicMock()
        mock_detection = MagicMock()
        mock_detection.injection_detected = False
        mock_rebuff.detect_injection.return_value = mock_detection
        client._client = mock_rebuff

        result = client.detect_injection("My SSN is 123-45-6789")

        assert "[SSN_REDACTED]" in result["governed_prompt"]
        assert "123-45-6789" not in result["governed_prompt"]
        assert len(result["_tork_receipts"]) > 0

    def test_govern_is_injection_input(self):
        """Test that governance is applied to is_injection input."""
        from tork_governance.adapters.rebuff_adapter import TorkRebuff

        client = TorkRebuff(tork=self.tork)

        mock_rebuff = MagicMock()
        mock_rebuff.is_injection.return_value = False
        client._client = mock_rebuff

        result = client.is_injection("Email: admin@secret.com")

        assert "[EMAIL_REDACTED]" in result["governed_prompt"]
        assert len(result["_tork_receipts"]) > 0

    def test_skip_governance_when_disabled(self):
        """Test that governance can be disabled."""
        from tork_governance.adapters.rebuff_adapter import TorkRebuff

        client = TorkRebuff(tork=self.tork, govern_input=False)

        mock_rebuff = MagicMock()
        mock_detection = MagicMock()
        mock_detection.injection_detected = False
        mock_rebuff.detect_injection.return_value = mock_detection
        client._client = mock_rebuff

        result = client.detect_injection("SSN: 123-45-6789")

        assert result["governed_prompt"] == "SSN: 123-45-6789"
        assert len(result["_tork_receipts"]) == 0

    def test_receipts_generated(self):
        """Test that governance receipts are generated."""
        from tork_governance.adapters.rebuff_adapter import TorkRebuff

        client = TorkRebuff(tork=self.tork)

        mock_rebuff = MagicMock()
        mock_detection = MagicMock()
        mock_detection.injection_detected = False
        mock_rebuff.detect_injection.return_value = mock_detection
        client._client = mock_rebuff

        result = client.detect_injection("My email is test@example.com")

        assert len(result["_tork_receipts"]) == 1
        assert result["_tork_receipts"][0] is not None


class TestRebuffGoverned:
    """Tests for rebuff_governed decorator."""

    def test_decorator_governs_prompt(self):
        """Test that the decorator governs prompt kwarg."""
        from tork_governance.adapters.rebuff_adapter import rebuff_governed

        tork = Tork()

        @rebuff_governed(tork)
        def fake_detect(**kwargs):
            return kwargs

        result = fake_detect(prompt="My email is test@example.com")

        assert "test@example.com" not in result["prompt"]
        assert "[EMAIL_REDACTED]" in result["prompt"]
