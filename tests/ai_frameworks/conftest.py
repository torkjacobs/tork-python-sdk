"""Shared fixtures for AI framework adapter tests."""

import pytest
from tork_governance import Tork, TorkConfig, GovernanceAction
from .test_data import PII_SAMPLES, EXPECTED_REDACTIONS, CLEAN_SAMPLES, PII_MESSAGES


@pytest.fixture
def default_config():
    """Default Tork configuration."""
    return TorkConfig(
        policy_version="1.0.0",
        default_action=GovernanceAction.REDACT
    )


@pytest.fixture
def strict_config():
    """Strict Tork configuration that denies on PII."""
    return TorkConfig(
        policy_version="1.0.0",
        default_action=GovernanceAction.DENY
    )


@pytest.fixture
def allow_config():
    """Permissive Tork configuration."""
    return TorkConfig(
        policy_version="1.0.0",
        default_action=GovernanceAction.ALLOW
    )


@pytest.fixture
def tork_instance(default_config):
    """Default Tork instance."""
    return Tork(config=default_config)


@pytest.fixture
def strict_tork(strict_config):
    """Strict Tork instance."""
    return Tork(config=strict_config)


@pytest.fixture
def pii_test_data():
    """PII test data samples."""
    return {
        "samples": PII_SAMPLES,
        "expected_redactions": EXPECTED_REDACTIONS,
        "clean_samples": CLEAN_SAMPLES,
        "pii_messages": PII_MESSAGES,
    }


@pytest.fixture
def mock_governance_response():
    """Factory for mock governance responses."""
    def _create_response(action="redact", has_pii=False, output="test output"):
        class MockReceipt:
            receipt_id = "rcpt_test_123"
            timestamp = "2024-01-01T00:00:00Z"
            input_hash = "sha256:abc123"
            output_hash = "sha256:def456"
            policy_version = "1.0.0"

        class MockPII:
            has_pii = has_pii
            types = ["email"] if has_pii else []
            count = 1 if has_pii else 0

        class MockResult:
            action = GovernanceAction(action)
            output = output
            pii = MockPII()
            receipt = MockReceipt()

        return MockResult()

    return _create_response


@pytest.fixture
def email_pii():
    """Email PII sample."""
    return PII_SAMPLES["email"]


@pytest.fixture
def phone_pii():
    """Phone PII sample."""
    return PII_SAMPLES["phone_us"]


@pytest.fixture
def ssn_pii():
    """SSN PII sample."""
    return PII_SAMPLES["ssn"]


@pytest.fixture
def credit_card_pii():
    """Credit card PII sample."""
    return PII_SAMPLES["credit_card"]
