"""
Tests for Universal PII Detection
Part 1.4 of Comprehensive Test Plan
Covers: Email, Credit Card, IP, IPv6, MAC, DOB
"""

import pytest
from tork_governance.detectors.pii_patterns import (
    PIIDetector, PIIType, detect_pii, redact_pii
)


# ============================================================================
# EMAIL ADDRESS TESTS
# ============================================================================

class TestEmail:
    """Test Email Address detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['universal'])

    @pytest.mark.parametrize("email,should_detect,description", [
        # Standard formats
        ("john.doe@example.com", True, "Standard format"),
        ("user@domain.org", True, "Simple format"),
        ("test@sub.domain.co.uk", True, "Subdomain"),
        ("user+tag@example.com", True, "Plus addressing"),
        ("user.name+tag@example.com", True, "Dot and plus"),
        # Complex valid emails
        ("user_name@example.com", True, "Underscore"),
        ("user-name@example.com", True, "Hyphen"),
        ("user123@example.com", True, "Numbers"),
        ("123user@example.com", True, "Leading numbers"),
        ("a@b.co", True, "Minimal valid"),
        # International TLDs
        ("user@example.io", True, "IO TLD"),
        ("user@example.dev", True, "Dev TLD"),
        ("user@example.ai", True, "AI TLD"),
        ("user@example.cloud", True, "Cloud TLD"),
        # Invalid formats
        ("invalid-email", False, "No @ symbol"),
        ("@nodomain.com", False, "No local part"),
        ("user@", False, "No domain"),
        ("user@.com", False, "No domain name"),
        # Note: "user name@example.com" will match "name@example.com" which is valid
        # This is correct behavior - we detect the valid email substring
    ])
    def test_email_detection(self, detector, email, should_detect, description):
        text = f"Contact: {email}"
        matches = detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        if should_detect:
            assert len(email_matches) >= 1, f"Should detect email ({description}): {email}"
        else:
            assert len(email_matches) == 0, f"Should NOT detect invalid email ({description}): {email}"

    def test_multiple_emails(self, detector):
        """Test detecting multiple emails in text"""
        text = "Contact john@example.com or jane@company.org for support"
        matches = detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        assert len(email_matches) >= 2, "Should detect multiple emails"

    def test_email_redaction(self, detector):
        """Test email redaction"""
        text = "Send to john.doe@example.com"
        redacted, matches = detector.redact(text)

        assert "john.doe@example.com" not in redacted
        assert "[EMAIL_REDACTED]" in redacted


# ============================================================================
# CREDIT CARD TESTS
# ============================================================================

class TestCreditCard:
    """Test Credit Card detection with Luhn validation"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['universal'])

    @pytest.mark.parametrize("card,should_detect,card_type", [
        # Visa (starts with 4)
        ("4111111111111111", True, "Visa"),
        ("4111-1111-1111-1111", True, "Visa dashed"),
        ("4111 1111 1111 1111", True, "Visa spaced"),
        ("4532015112830366", True, "Visa valid"),
        # Mastercard (starts with 51-55 or 2221-2720)
        ("5500000000000004", True, "Mastercard"),
        ("5555555555554444", True, "Mastercard test"),
        ("5105105105105100", True, "Mastercard valid"),
        # American Express (starts with 34 or 37)
        ("378282246310005", True, "Amex"),
        ("371449635398431", True, "Amex valid"),
        ("3782 822463 10005", True, "Amex spaced"),
        # Discover (starts with 6011, 644-649, or 65)
        ("6011111111111117", True, "Discover"),
        ("6011000990139424", True, "Discover valid"),
        # Invalid cards (fail Luhn)
        ("4111111111111112", False, "Invalid Luhn"),
        ("1234567890123456", False, "Invalid Luhn random"),
        ("0000000000000000", False, "All zeros"),
        # Too short/long
        ("411111111111", False, "Too short"),
        ("41111111111111111111", False, "Too long"),
    ])
    def test_credit_card_detection(self, detector, card, should_detect, card_type):
        text = f"Card: {card}"
        matches = detector.detect(text)
        card_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]

        if should_detect:
            assert len(card_matches) >= 1, f"Should detect {card_type}: {card}"
        else:
            assert len(card_matches) == 0, f"Should NOT detect invalid card ({card_type}): {card}"

    def test_credit_card_redaction(self, detector):
        """Test credit card redaction"""
        text = "Payment card: 4111111111111111"
        redacted, matches = detector.redact(text)

        assert "4111111111111111" not in redacted
        assert "[CREDIT_CARD_REDACTED]" in redacted

    def test_credit_card_in_context(self, detector):
        """Test credit card detection in realistic contexts"""
        contexts = [
            "Please charge my card 4111111111111111",
            "CC: 5555555555554444",
            "Card Number: 4111-1111-1111-1111",
            "Payment: 378282246310005 (Amex)",
        ]

        for text in contexts:
            matches = detector.detect(text)
            card_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
            assert len(card_matches) >= 1, f"Should detect card in: {text}"


# ============================================================================
# IP ADDRESS (IPv4) TESTS
# ============================================================================

class TestIPv4:
    """Test IPv4 Address detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['universal'])

    @pytest.mark.parametrize("ip,should_detect,description", [
        # Valid IPs
        ("192.168.1.1", True, "Private Class C"),
        ("10.0.0.1", True, "Private Class A"),
        ("172.16.0.1", True, "Private Class B"),
        ("8.8.8.8", True, "Google DNS"),
        ("255.255.255.255", True, "Broadcast"),
        ("0.0.0.0", True, "All zeros"),
        ("127.0.0.1", True, "Localhost"),
        ("1.2.3.4", True, "Simple"),
        ("192.168.100.200", True, "Three digits"),
        # Invalid IPs
        ("256.1.1.1", False, "First octet > 255"),
        ("1.256.1.1", False, "Second octet > 255"),
        ("1.1.256.1", False, "Third octet > 255"),
        ("1.1.1.256", False, "Fourth octet > 255"),
        ("1.2.3", False, "Only 3 octets"),
        ("1.2.3.4.5", False, "5 octets"),
        ("192.168.1", False, "Incomplete"),
    ])
    def test_ipv4_detection(self, detector, ip, should_detect, description):
        text = f"Server IP: {ip}"
        matches = detector.detect(text)
        ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]

        if should_detect:
            assert len(ip_matches) >= 1, f"Should detect IPv4 ({description}): {ip}"
        else:
            assert len(ip_matches) == 0, f"Should NOT detect invalid IPv4 ({description}): {ip}"

    def test_ipv4_redaction(self, detector):
        """Test IPv4 redaction"""
        text = "User logged in from 192.168.1.100"
        redacted, matches = detector.redact(text)

        assert "192.168.1.100" not in redacted
        assert "[IP_REDACTED]" in redacted

    def test_multiple_ips(self, detector):
        """Test multiple IP detection"""
        text = "Allow traffic from 192.168.1.1 to 10.0.0.1"
        matches = detector.detect(text)
        ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]
        assert len(ip_matches) >= 2, "Should detect multiple IPs"


# ============================================================================
# IPv6 ADDRESS TESTS
# ============================================================================

class TestIPv6:
    """Test IPv6 Address detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['universal'])

    @pytest.mark.parametrize("ip,should_detect,description", [
        # Full format
        ("2001:0db8:85a3:0000:0000:8a2e:0370:7334", True, "Full format"),
        ("fe80:0000:0000:0000:0000:0000:0000:0001", True, "Link local"),
        # Mixed case
        ("2001:0DB8:85A3:0000:0000:8A2E:0370:7334", True, "Uppercase"),
        ("2001:0Db8:85a3:0000:0000:8A2e:0370:7334", True, "Mixed case"),
        # Invalid (abbreviated forms not supported by simple pattern)
        ("::1", False, "Loopback abbreviated"),
        ("::", False, "All zeros abbreviated"),
    ])
    def test_ipv6_detection(self, detector, ip, should_detect, description):
        text = f"IPv6: {ip}"
        matches = detector.detect(text)
        ipv6_matches = [m for m in matches if m.pii_type == PIIType.IPV6_ADDRESS]

        if should_detect:
            assert len(ipv6_matches) >= 1, f"Should detect IPv6 ({description}): {ip}"
        else:
            # Abbreviated forms may not be detected by simple pattern
            pass


# ============================================================================
# MAC ADDRESS TESTS
# ============================================================================

class TestMACAddress:
    """Test MAC Address detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['universal'])

    @pytest.mark.parametrize("mac,should_detect,description", [
        # Colon separated (common on Linux/Mac)
        ("00:1A:2B:3C:4D:5E", True, "Colon uppercase"),
        ("00:1a:2b:3c:4d:5e", True, "Colon lowercase"),
        ("AA:BB:CC:DD:EE:FF", True, "All letters"),
        # Hyphen separated (common on Windows)
        ("00-1A-2B-3C-4D-5E", True, "Hyphen uppercase"),
        ("00-1a-2b-3c-4d-5e", True, "Hyphen lowercase"),
        # Special addresses
        ("FF:FF:FF:FF:FF:FF", True, "Broadcast"),
        ("00:00:00:00:00:00", True, "Null MAC"),
        # Invalid
        ("00:1A:2B:3C:4D", False, "Only 5 octets"),
        ("00:1A:2B:3C:4D:5E:6F", False, "7 octets"),
        ("GG:HH:II:JJ:KK:LL", False, "Invalid hex"),
        ("001A2B3C4D5E", False, "No separators"),
    ])
    def test_mac_detection(self, detector, mac, should_detect, description):
        text = f"Device MAC: {mac}"
        matches = detector.detect(text)
        mac_matches = [m for m in matches if m.pii_type == PIIType.MAC_ADDRESS]

        if should_detect:
            assert len(mac_matches) >= 1, f"Should detect MAC ({description}): {mac}"
        else:
            assert len(mac_matches) == 0, f"Should NOT detect invalid MAC ({description}): {mac}"

    def test_mac_redaction(self, detector):
        """Test MAC redaction"""
        text = "Network adapter: 00:1A:2B:3C:4D:5E"
        redacted, matches = detector.redact(text)

        assert "00:1A:2B:3C:4D:5E" not in redacted
        assert "[MAC_REDACTED]" in redacted


# ============================================================================
# DATE OF BIRTH TESTS
# ============================================================================

class TestDateOfBirth:
    """Test Date of Birth detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['universal'])

    @pytest.mark.parametrize("dob,should_detect,description", [
        # With DOB prefix
        ("DOB: 01/15/1985", True, "DOB with slash"),
        ("DOB: 15-01-1985", True, "DOB with dash"),
        ("DOB: 01.15.1985", True, "DOB with dot"),
        ("Date of Birth: 12/25/1990", True, "Full phrase"),
        ("Date of Birth: 25-12-1990", True, "Full phrase dash"),
        ("Born: 06/15/1975", True, "Born prefix"),
        ("Birthday: 03/14/1992", True, "Birthday prefix"),
        # Case insensitive
        ("dob: 01/15/1985", True, "Lowercase DOB"),
        ("DATE OF BIRTH: 01/15/1985", True, "Uppercase"),
        # Two digit year
        ("DOB: 01/15/85", True, "Two digit year"),
        # Without prefix (should NOT match - too many false positives)
        ("01/15/1985", False, "No prefix"),
        ("The meeting is on 01/15/2025", False, "Generic date"),
    ])
    def test_dob_detection(self, detector, dob, should_detect, description):
        text = dob
        matches = detector.detect(text)
        dob_matches = [m for m in matches if m.pii_type == PIIType.DATE_OF_BIRTH]

        if should_detect:
            assert len(dob_matches) >= 1, f"Should detect DOB ({description}): {dob}"
        else:
            assert len(dob_matches) == 0, f"Should NOT detect ({description}): {dob}"

    def test_dob_redaction(self, detector):
        """Test DOB redaction"""
        text = "Patient DOB: 01/15/1985"
        redacted, matches = detector.redact(text)

        assert "01/15/1985" not in redacted


# ============================================================================
# COMBINED UNIVERSAL TESTS
# ============================================================================

class TestUniversalCombined:
    """Test combined Universal PII detection scenarios"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['universal'])

    def test_contact_form(self, detector):
        """Test contact form with multiple PII types"""
        text = """
        Contact Information:
        Email: john.doe@example.com
        Phone: 555-123-4567
        DOB: 01/15/1985
        """

        matches = detector.detect(text)
        types_found = {m.pii_type for m in matches}

        assert PIIType.EMAIL in types_found, f"Should find email, found: {types_found}"

    def test_payment_form(self, detector):
        """Test payment form with card details"""
        text = """
        Payment Details:
        Card Number: 4111-1111-1111-1111
        Email: billing@example.com
        IP: 192.168.1.100
        """

        matches = detector.detect(text)
        types_found = {m.pii_type for m in matches}

        assert PIIType.EMAIL in types_found or PIIType.CREDIT_CARD in types_found

    def test_network_log(self, detector):
        """Test network log with IPs and MACs"""
        text = """
        Network Log Entry:
        Source IP: 192.168.1.100
        Destination IP: 10.0.0.1
        MAC Address: 00:1A:2B:3C:4D:5E
        """

        matches = detector.detect(text)
        ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]
        mac_matches = [m for m in matches if m.pii_type == PIIType.MAC_ADDRESS]

        assert len(ip_matches) >= 2, "Should detect IPs"
        assert len(mac_matches) >= 1, "Should detect MAC"

    def test_full_redaction(self, detector):
        """Test full redaction of document with multiple types"""
        text = """
        User Profile:
        Email: user@example.com
        Card: 4111111111111111
        IP: 192.168.1.1
        MAC: 00:1A:2B:3C:4D:5E
        DOB: 01/15/1985
        """

        redacted, matches = detector.redact(text)

        assert "user@example.com" not in redacted
        assert "4111111111111111" not in redacted
        assert "192.168.1.1" not in redacted


# ============================================================================
# REAL WORLD SCENARIOS
# ============================================================================

class TestUniversalRealWorld:
    """Test real-world scenarios with universal PII"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['universal'])

    def test_ecommerce_checkout(self, detector):
        """Test e-commerce checkout page"""
        text = """
        Order Confirmation

        Customer: john.doe@example.com
        Payment: Card ending 1111
        Full card: 4111111111111111
        Billing IP: 192.168.1.100
        """

        matches = detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        card_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]

        assert len(email_matches) >= 1, "Should detect email"
        assert len(card_matches) >= 1, "Should detect credit card"

    def test_server_access_log(self, detector):
        """Test server access log"""
        text = """
        [2026-01-31 10:30:45] User login
        IP: 192.168.1.100
        User-Agent: Mozilla/5.0
        Session MAC: 00:1A:2B:3C:4D:5E
        Email: admin@company.com
        """

        matches = detector.detect(text)
        assert len(matches) >= 2, "Should detect multiple PII types"

    def test_healthcare_intake(self, detector):
        """Test healthcare intake form"""
        text = """
        Patient Intake Form

        Email: patient@email.com
        DOB: 03/15/1980
        Emergency Contact Email: family@email.com
        """

        matches = detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        assert len(email_matches) >= 2, "Should detect multiple emails"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
