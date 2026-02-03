"""
Comprehensive tests for tork_governance/core.py
Phase A: Increase coverage from 55% to 80%+
"""

import pytest
import re
from tork_governance.core import (
    Tork,
    TorkConfig,
    PIIType,
    GovernanceAction,
    GovernanceResult,
    PIIResult,
    PIIMatch,
    Receipt,
    detect_pii,
    redact_pii,
    hash_text,
    generate_receipt_id,
    PII_PATTERNS,
)


# ============================================================================
# TEST ENUMS
# ============================================================================

class TestPIITypeEnum:
    """Test PIIType enum"""

    def test_pii_type_values(self):
        """Test all PIIType enum values exist"""
        assert PIIType.SSN.value == "ssn"
        assert PIIType.CREDIT_CARD.value == "credit_card"
        assert PIIType.EMAIL.value == "email"
        assert PIIType.PHONE.value == "phone"
        assert PIIType.ADDRESS.value == "address"
        assert PIIType.IP_ADDRESS.value == "ip_address"
        assert PIIType.DATE_OF_BIRTH.value == "date_of_birth"
        assert PIIType.PASSPORT.value == "passport"
        assert PIIType.DRIVERS_LICENSE.value == "drivers_license"
        assert PIIType.BANK_ACCOUNT.value == "bank_account"

    def test_pii_type_is_string_enum(self):
        """Test PIIType inherits from str"""
        assert isinstance(PIIType.SSN, str)
        assert PIIType.SSN == "ssn"


class TestGovernanceActionEnum:
    """Test GovernanceAction enum"""

    def test_governance_action_values(self):
        """Test all GovernanceAction values"""
        assert GovernanceAction.ALLOW.value == "allow"
        assert GovernanceAction.DENY.value == "deny"
        assert GovernanceAction.REDACT.value == "redact"
        assert GovernanceAction.ESCALATE.value == "escalate"

    def test_governance_action_is_string_enum(self):
        """Test GovernanceAction inherits from str"""
        assert isinstance(GovernanceAction.ALLOW, str)


# ============================================================================
# TEST DATACLASSES
# ============================================================================

class TestPIIMatch:
    """Test PIIMatch dataclass"""

    def test_pii_match_creation(self):
        """Test creating PIIMatch"""
        match = PIIMatch(
            type=PIIType.SSN,
            value="123-45-6789",
            start_index=10,
            end_index=21
        )
        assert match.type == PIIType.SSN
        assert match.value == "123-45-6789"
        assert match.start_index == 10
        assert match.end_index == 21

    def test_pii_match_with_email(self):
        """Test PIIMatch with email type"""
        match = PIIMatch(
            type=PIIType.EMAIL,
            value="test@example.com",
            start_index=0,
            end_index=16
        )
        assert match.type == PIIType.EMAIL


class TestPIIResult:
    """Test PIIResult dataclass"""

    def test_pii_result_with_matches(self):
        """Test PIIResult with PII found"""
        result = PIIResult(
            has_pii=True,
            types=[PIIType.SSN, PIIType.EMAIL],
            count=2,
            matches=[
                PIIMatch(PIIType.SSN, "123-45-6789", 0, 11),
                PIIMatch(PIIType.EMAIL, "test@test.com", 15, 28)
            ],
            redacted_text="[SSN_REDACTED] [EMAIL_REDACTED]"
        )
        assert result.has_pii == True
        assert len(result.types) == 2
        assert result.count == 2

    def test_pii_result_no_matches(self):
        """Test PIIResult with no PII"""
        result = PIIResult(
            has_pii=False,
            types=[],
            count=0,
            matches=[],
            redacted_text="Clean text"
        )
        assert result.has_pii == False
        assert result.count == 0


class TestReceipt:
    """Test Receipt dataclass"""

    def test_receipt_creation(self):
        """Test creating Receipt"""
        receipt = Receipt(
            receipt_id="rcpt_abc123",
            timestamp="2026-01-31T10:00:00Z",
            input_hash="sha256:abc",
            output_hash="sha256:def",
            action=GovernanceAction.REDACT,
            policy_version="1.0.0",
            processing_time_ns=1000000,
            pii_types=[PIIType.SSN],
            pii_count=1
        )
        assert receipt.receipt_id == "rcpt_abc123"
        assert receipt.action == GovernanceAction.REDACT
        assert receipt.pii_count == 1

    def test_receipt_verify_success(self):
        """Test receipt verification success"""
        input_text = "Test input"
        output_text = "Test output"
        receipt = Receipt(
            receipt_id="rcpt_test",
            timestamp="2026-01-31T10:00:00Z",
            input_hash=hash_text(input_text),
            output_hash=hash_text(output_text),
            action=GovernanceAction.ALLOW,
            policy_version="1.0.0",
            processing_time_ns=1000
        )
        assert receipt.verify(input_text, output_text) == True

    def test_receipt_verify_failure(self):
        """Test receipt verification failure"""
        receipt = Receipt(
            receipt_id="rcpt_test",
            timestamp="2026-01-31T10:00:00Z",
            input_hash="sha256:original",
            output_hash="sha256:original_out",
            action=GovernanceAction.ALLOW,
            policy_version="1.0.0",
            processing_time_ns=1000
        )
        assert receipt.verify("different input", "different output") == False

    def test_receipt_default_pii_fields(self):
        """Test receipt default pii_types and pii_count"""
        receipt = Receipt(
            receipt_id="rcpt_test",
            timestamp="2026-01-31T10:00:00Z",
            input_hash="sha256:abc",
            output_hash="sha256:def",
            action=GovernanceAction.ALLOW,
            policy_version="1.0.0",
            processing_time_ns=1000
        )
        assert receipt.pii_types == []
        assert receipt.pii_count == 0


class TestGovernanceResult:
    """Test GovernanceResult dataclass"""

    def test_governance_result_creation(self):
        """Test creating GovernanceResult"""
        pii = PIIResult(False, [], 0, [], "Clean")
        receipt = Receipt(
            "rcpt_test", "2026-01-31T10:00:00Z",
            "sha256:a", "sha256:b",
            GovernanceAction.ALLOW, "1.0.0", 1000
        )
        result = GovernanceResult(
            action=GovernanceAction.ALLOW,
            output="Clean",
            pii=pii,
            receipt=receipt
        )
        assert result.action == GovernanceAction.ALLOW
        assert result.output == "Clean"


class TestTorkConfig:
    """Test TorkConfig dataclass"""

    def test_default_config(self):
        """Test default TorkConfig values"""
        config = TorkConfig()
        assert config.policy_version == "1.0.0"
        assert config.default_action == GovernanceAction.REDACT
        assert config.custom_patterns is None
        assert config.api_key is None

    def test_custom_config(self):
        """Test custom TorkConfig values"""
        patterns = {"custom": re.compile(r"CUSTOM-\d+")}
        config = TorkConfig(
            policy_version="2.0.0",
            default_action=GovernanceAction.DENY,
            custom_patterns=patterns,
            api_key="test_key"
        )
        assert config.policy_version == "2.0.0"
        assert config.default_action == GovernanceAction.DENY
        assert config.api_key == "test_key"


# ============================================================================
# TEST UTILITY FUNCTIONS
# ============================================================================

class TestHashText:
    """Test hash_text function"""

    def test_hash_text_format(self):
        """Test hash_text returns correct format"""
        result = hash_text("test")
        assert result.startswith("sha256:")
        assert len(result) == 71  # "sha256:" + 64 hex chars

    def test_hash_text_deterministic(self):
        """Test hash_text is deterministic"""
        assert hash_text("hello") == hash_text("hello")

    def test_hash_text_different_inputs(self):
        """Test different inputs produce different hashes"""
        assert hash_text("hello") != hash_text("world")

    def test_hash_text_empty(self):
        """Test hash of empty string"""
        result = hash_text("")
        assert result.startswith("sha256:")

    def test_hash_text_unicode(self):
        """Test hash with unicode characters"""
        result = hash_text("日本語テスト")
        assert result.startswith("sha256:")


class TestGenerateReceiptId:
    """Test generate_receipt_id function"""

    def test_receipt_id_format(self):
        """Test receipt ID format"""
        receipt_id = generate_receipt_id()
        assert receipt_id.startswith("rcpt_")
        assert len(receipt_id) == 37  # "rcpt_" + 32 hex chars

    def test_receipt_id_unique(self):
        """Test receipt IDs are unique"""
        ids = [generate_receipt_id() for _ in range(100)]
        assert len(set(ids)) == 100


# ============================================================================
# TEST DETECT_PII FUNCTION
# ============================================================================

class TestDetectPII:
    """Test detect_pii function"""

    def test_detect_ssn(self):
        """Test SSN detection"""
        result = detect_pii("My SSN is 123-45-6789")
        assert result.has_pii == True
        assert PIIType.SSN in result.types
        assert result.count >= 1
        assert "[SSN_REDACTED]" in result.redacted_text

    def test_detect_email(self):
        """Test email detection"""
        result = detect_pii("Contact: test@example.com")
        assert result.has_pii == True
        assert PIIType.EMAIL in result.types
        assert "[EMAIL_REDACTED]" in result.redacted_text

    def test_detect_credit_card(self):
        """Test credit card detection"""
        result = detect_pii("Card: 4111-1111-1111-1111")
        assert result.has_pii == True
        assert PIIType.CREDIT_CARD in result.types
        assert "[CARD_REDACTED]" in result.redacted_text

    def test_detect_phone(self):
        """Test phone detection"""
        result = detect_pii("Call 555-123-4567")
        assert result.has_pii == True
        assert PIIType.PHONE in result.types
        assert "[PHONE_REDACTED]" in result.redacted_text

    def test_detect_ip_address(self):
        """Test IP address detection"""
        result = detect_pii("IP: 192.168.1.100")
        assert result.has_pii == True
        assert PIIType.IP_ADDRESS in result.types
        assert "[IP_REDACTED]" in result.redacted_text

    def test_detect_dob(self):
        """Test date of birth detection"""
        result = detect_pii("DOB: 01/15/1990")
        assert result.has_pii == True
        assert PIIType.DATE_OF_BIRTH in result.types
        assert "[DOB_REDACTED]" in result.redacted_text

    def test_detect_address(self):
        """Test address detection"""
        result = detect_pii("Address: 123 Main Street")
        assert result.has_pii == True
        assert PIIType.ADDRESS in result.types
        assert "[ADDRESS_REDACTED]" in result.redacted_text

    def test_no_pii(self):
        """Test text without PII"""
        result = detect_pii("Hello, this is a safe message.")
        assert result.has_pii == False
        assert result.count == 0
        assert result.redacted_text == "Hello, this is a safe message."

    def test_multiple_pii_types(self):
        """Test detecting multiple PII types"""
        result = detect_pii("SSN: 123-45-6789, Email: test@test.com, Phone: 555-123-4567")
        assert result.has_pii == True
        assert PIIType.SSN in result.types
        assert PIIType.EMAIL in result.types
        assert PIIType.PHONE in result.types
        assert result.count >= 3

    def test_custom_patterns(self):
        """Test with custom patterns"""
        custom = {"employee_id": re.compile(r"EMP-\d{6}")}
        result = detect_pii("Employee: EMP-123456", custom_patterns=custom)
        assert "[EMPLOYEE_ID_REDACTED]" in result.redacted_text

    def test_empty_text(self):
        """Test empty text"""
        result = detect_pii("")
        assert result.has_pii == False
        assert result.count == 0

    def test_match_indices(self):
        """Test match indices are correct"""
        result = detect_pii("SSN: 123-45-6789")
        assert len(result.matches) >= 1
        match = result.matches[0]
        assert match.start_index >= 0
        assert match.end_index > match.start_index


class TestRedactPII:
    """Test redact_pii convenience function"""

    def test_redact_ssn(self):
        """Test SSN redaction"""
        result = redact_pii("My SSN is 123-45-6789")
        assert "123-45-6789" not in result
        assert "[SSN_REDACTED]" in result

    def test_redact_email(self):
        """Test email redaction"""
        result = redact_pii("Contact: test@example.com")
        assert "test@example.com" not in result

    def test_redact_clean_text(self):
        """Test clean text unchanged"""
        original = "Hello world"
        result = redact_pii(original)
        assert result == original


# ============================================================================
# TEST TORK CLASS
# ============================================================================

class TestTorkInit:
    """Test Tork initialization"""

    def test_default_init(self):
        """Test default initialization"""
        tork = Tork()
        assert tork.config.policy_version == "1.0.0"
        assert tork.config.default_action == GovernanceAction.REDACT

    def test_init_with_api_key(self):
        """Test initialization with API key"""
        tork = Tork(api_key="test_key_123")
        assert tork.config.api_key == "test_key_123"

    def test_init_with_policy_version(self):
        """Test initialization with policy version"""
        tork = Tork(policy_version="2.0.0")
        assert tork.config.policy_version == "2.0.0"

    def test_init_with_default_action(self):
        """Test initialization with default action"""
        tork = Tork(default_action=GovernanceAction.DENY)
        assert tork.config.default_action == GovernanceAction.DENY

    def test_init_with_config(self):
        """Test initialization with TorkConfig"""
        config = TorkConfig(
            policy_version="3.0.0",
            default_action=GovernanceAction.ESCALATE,
            api_key="config_key"
        )
        tork = Tork(config=config)
        assert tork.config.policy_version == "3.0.0"
        assert tork.config.default_action == GovernanceAction.ESCALATE
        assert tork.config.api_key == "config_key"

    def test_init_stats(self):
        """Test initial stats are zero"""
        tork = Tork()
        stats = tork.get_stats()
        assert stats['total_calls'] == 0
        assert stats['total_pii_detected'] == 0


class TestTorkGovern:
    """Test Tork.govern method"""

    def test_govern_clean_text(self):
        """Test governing clean text"""
        tork = Tork()
        result = tork.govern("Hello, this is a safe message.")
        assert result.action == GovernanceAction.ALLOW
        assert result.output == "Hello, this is a safe message."
        assert result.pii.has_pii == False

    def test_govern_with_ssn(self):
        """Test governing text with SSN"""
        tork = Tork()
        result = tork.govern("My SSN is 123-45-6789")
        assert result.action == GovernanceAction.REDACT
        assert "[SSN_REDACTED]" in result.output
        assert result.pii.has_pii == True
        assert PIIType.SSN in result.pii.types

    def test_govern_with_email(self):
        """Test governing text with email"""
        tork = Tork()
        result = tork.govern("Contact: test@example.com")
        assert result.action == GovernanceAction.REDACT
        assert "[EMAIL_REDACTED]" in result.output

    def test_govern_with_credit_card(self):
        """Test governing text with credit card"""
        tork = Tork()
        result = tork.govern("Card: 4111-1111-1111-1111")
        assert result.action == GovernanceAction.REDACT
        assert "[CARD_REDACTED]" in result.output

    def test_govern_receipt_generated(self):
        """Test receipt is generated"""
        tork = Tork()
        result = tork.govern("Test input")
        assert result.receipt.receipt_id.startswith("rcpt_")
        assert result.receipt.input_hash.startswith("sha256:")
        assert result.receipt.output_hash.startswith("sha256:")
        assert result.receipt.timestamp is not None
        assert result.receipt.policy_version == "1.0.0"

    def test_govern_processing_time(self):
        """Test processing time is recorded"""
        tork = Tork()
        result = tork.govern("Test input")
        assert result.receipt.processing_time_ns > 0

    def test_govern_with_deny_action(self):
        """Test govern with DENY default action"""
        tork = Tork(default_action=GovernanceAction.DENY)
        result = tork.govern("SSN: 123-45-6789")
        assert result.action == GovernanceAction.DENY
        # With DENY, original text is kept (not redacted)
        assert "123-45-6789" in result.output

    def test_govern_multiple_pii(self):
        """Test governing multiple PII types"""
        tork = Tork()
        result = tork.govern("SSN: 123-45-6789, Email: test@test.com")
        assert result.pii.count >= 2
        assert "[SSN_REDACTED]" in result.output
        assert "[EMAIL_REDACTED]" in result.output

    def test_govern_empty_string(self):
        """Test governing empty string"""
        tork = Tork()
        result = tork.govern("")
        assert result.action == GovernanceAction.ALLOW
        assert result.output == ""

    def test_govern_whitespace(self):
        """Test governing whitespace"""
        tork = Tork()
        result = tork.govern("   \n\t  ")
        assert result.action == GovernanceAction.ALLOW

    def test_govern_unicode(self):
        """Test governing unicode text"""
        tork = Tork()
        result = tork.govern("日本語テスト 🎉")
        assert result.action == GovernanceAction.ALLOW

    def test_govern_with_custom_patterns(self):
        """Test govern with custom patterns in config"""
        config = TorkConfig(
            custom_patterns={"order_id": re.compile(r"ORD-\d{8}")}
        )
        tork = Tork(config=config)
        result = tork.govern("Order: ORD-12345678")
        # Custom patterns are applied in detect_pii, check redacted_text
        assert "[ORDER_ID_REDACTED]" in result.pii.redacted_text


class TestTorkStats:
    """Test Tork statistics"""

    def test_stats_increment_calls(self):
        """Test total_calls increments"""
        tork = Tork()
        tork.govern("Test 1")
        tork.govern("Test 2")
        tork.govern("Test 3")
        stats = tork.get_stats()
        assert stats['total_calls'] == 3

    def test_stats_increment_pii_detected(self):
        """Test total_pii_detected increments"""
        tork = Tork()
        tork.govern("Clean text")
        tork.govern("SSN: 123-45-6789")
        tork.govern("Another clean")
        tork.govern("Email: test@test.com")
        stats = tork.get_stats()
        assert stats['total_pii_detected'] == 2

    def test_stats_avg_processing_time(self):
        """Test average processing time calculation"""
        tork = Tork()
        tork.govern("Test 1")
        tork.govern("Test 2")
        stats = tork.get_stats()
        assert stats['avg_processing_time_ns'] > 0

    def test_stats_action_counts(self):
        """Test action counts tracking"""
        tork = Tork()
        tork.govern("Clean text")  # ALLOW
        tork.govern("SSN: 123-45-6789")  # REDACT
        tork.govern("Another clean")  # ALLOW
        stats = tork.get_stats()
        assert stats['action_counts'][GovernanceAction.ALLOW] == 2
        assert stats['action_counts'][GovernanceAction.REDACT] == 1

    def test_reset_stats(self):
        """Test resetting stats"""
        tork = Tork()
        tork.govern("Test 1")
        tork.govern("SSN: 123-45-6789")
        tork.reset_stats()
        stats = tork.get_stats()
        assert stats['total_calls'] == 0
        assert stats['total_pii_detected'] == 0
        assert stats['avg_processing_time_ns'] == 0

    def test_stats_avg_when_no_calls(self):
        """Test avg is 0 when no calls"""
        tork = Tork()
        stats = tork.get_stats()
        assert stats['avg_processing_time_ns'] == 0


# ============================================================================
# TEST PII_PATTERNS
# ============================================================================

class TestPIIPatterns:
    """Test PII_PATTERNS dictionary"""

    def test_patterns_exist(self):
        """Test all expected patterns exist"""
        expected_types = [
            PIIType.SSN,
            PIIType.CREDIT_CARD,
            PIIType.EMAIL,
            PIIType.PHONE,
            PIIType.ADDRESS,
            PIIType.IP_ADDRESS,
            PIIType.DATE_OF_BIRTH,
        ]
        for pii_type in expected_types:
            assert pii_type in PII_PATTERNS, f"Missing pattern for {pii_type}"

    def test_pattern_structure(self):
        """Test each pattern is tuple of (pattern, redaction)"""
        for pii_type, value in PII_PATTERNS.items():
            assert isinstance(value, tuple)
            assert len(value) == 2
            assert hasattr(value[0], 'finditer')  # regex pattern
            assert isinstance(value[1], str)  # redaction string


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================

class TestEdgeCases:
    """Test edge cases"""

    def test_very_long_text(self):
        """Test handling very long text"""
        tork = Tork()
        long_text = "Hello world. " * 10000
        result = tork.govern(long_text)
        assert result.action == GovernanceAction.ALLOW

    def test_repeated_pii(self):
        """Test text with repeated PII"""
        tork = Tork()
        text = "SSN: 123-45-6789 " * 10
        result = tork.govern(text)
        assert result.pii.has_pii == True

    def test_special_characters(self):
        """Test text with special characters"""
        tork = Tork()
        text = "Test <script>alert('xss')</script> and SQL'; DROP TABLE--"
        result = tork.govern(text)
        assert result is not None

    def test_newlines_in_text(self):
        """Test text with newlines"""
        tork = Tork()
        text = "Line 1\nSSN: 123-45-6789\nLine 3"
        result = tork.govern(text)
        assert result.pii.has_pii == True
        assert "\n" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
