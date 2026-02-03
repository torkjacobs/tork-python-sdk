"""Tests for core Tork governance functionality."""

import pytest
from tork_governance.core import (
    Tork,
    PIIType,
    GovernanceAction,
    GovernanceResult,
    PIIResult,
)


class TestTork:
    """Tests for Tork class."""

    def test_create_default(self):
        """Test creating Tork with default settings."""
        tork = Tork()
        assert tork.policy_version == "1.0.0"
        assert tork.default_action == GovernanceAction.REDACT

    def test_create_with_config(self):
        """Test creating Tork with custom config."""
        tork = Tork(api_key="test_key", policy_version="2.0.0")
        assert tork.policy_version == "2.0.0"
        assert tork.api_key == "test_key"


class TestPIIDetection:
    """Tests for PII detection."""

    def test_detect_ssn(self):
        """Test detecting SSN."""
        tork = Tork()
        result = tork.govern("My SSN is 123-45-6789")
        assert result.pii.has_pii
        assert PIIType.SSN in result.pii.types
        assert "[SSN_REDACTED]" in result.output

    def test_detect_email(self):
        """Test detecting email."""
        tork = Tork()
        result = tork.govern("Contact me at test@example.com")
        assert result.pii.has_pii
        assert PIIType.EMAIL in result.pii.types
        assert "[EMAIL_REDACTED]" in result.output

    def test_detect_credit_card(self):
        """Test detecting credit card."""
        tork = Tork()
        result = tork.govern("Card: 4111-1111-1111-1111")
        assert result.pii.has_pii
        assert PIIType.CREDIT_CARD in result.pii.types
        assert "[CARD_REDACTED]" in result.output

    def test_detect_phone(self):
        """Test detecting phone number."""
        tork = Tork()
        result = tork.govern("Call 555-123-4567")
        assert result.pii.has_pii
        assert PIIType.PHONE in result.pii.types
        assert "[PHONE_REDACTED]" in result.output

    def test_no_pii(self):
        """Test text without PII."""
        tork = Tork()
        result = tork.govern("Hello, this is a safe message.")
        assert not result.pii.has_pii
        assert result.action == GovernanceAction.ALLOW
        assert result.output == "Hello, this is a safe message."

    def test_multiple_pii_types(self):
        """Test detecting multiple PII types."""
        tork = Tork()
        result = tork.govern("SSN: 123-45-6789, Email: test@test.com")
        assert result.pii.has_pii
        assert PIIType.SSN in result.pii.types
        assert PIIType.EMAIL in result.pii.types
        assert result.pii.count == 2


class TestGovernanceResult:
    """Tests for GovernanceResult."""

    def test_receipt_generation(self):
        """Test receipt is generated."""
        tork = Tork()
        result = tork.govern("Test input")
        assert result.receipt.receipt_id.startswith("rcpt_")
        assert result.receipt.input_hash.startswith("sha256:")
        assert result.receipt.output_hash.startswith("sha256:")
        assert result.receipt.timestamp is not None

    def test_action_redact(self):
        """Test redact action with PII."""
        tork = Tork()
        result = tork.govern("SSN: 123-45-6789")
        assert result.action == GovernanceAction.REDACT
        assert "[SSN_REDACTED]" in result.output

    def test_action_allow(self):
        """Test allow action without PII."""
        tork = Tork()
        result = tork.govern("Safe text")
        assert result.action == GovernanceAction.ALLOW


class TestStatistics:
    """Tests for statistics tracking."""

    def test_stats_tracking(self):
        """Test statistics are tracked."""
        tork = Tork()
        tork.govern("Text 1")
        tork.govern("SSN: 123-45-6789")
        tork.govern("Text 3")

        stats = tork.stats
        assert stats["total_calls"] == 3
        assert stats["total_pii_detected"] == 1

    def test_stats_reset(self):
        """Test statistics can be reset."""
        tork = Tork()
        tork.govern("Test")
        tork.reset_stats()

        stats = tork.stats
        assert stats["total_calls"] == 0
