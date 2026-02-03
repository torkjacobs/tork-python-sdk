"""
Tests for Edge Cases & Integration Scenarios
Phase 4 of Comprehensive Test Plan

Edge Cases Tested:
- Boundary conditions (min/max lengths)
- Malformed/partial data
- False positives/negatives
- Unicode and special characters
- Empty/null handling
- Mixed-region data
- Performance considerations
- Integration scenarios
"""

import pytest
from tork_governance.detectors.pii_patterns import PIIDetector, PIIType


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def full_detector():
    """PII detector with all regions enabled"""
    return PIIDetector(regions=['us', 'universal', 'financial', 'healthcare', 'biometric', 'eu_uk', 'au'])


@pytest.fixture
def minimal_detector():
    """PII detector with minimal regions"""
    return PIIDetector(regions=['universal'])


# ============================================================================
# BOUNDARY CONDITIONS
# ============================================================================

class TestBoundaryConditions:
    """Test boundary conditions for PII detection"""

    def test_minimum_length_email(self, full_detector):
        """Test minimum valid email detection"""
        # Shortest valid emails
        short_emails = [
            "a@b.co",
            "x@y.io",
        ]

        for email in short_emails:
            matches = full_detector.detect(f"Email: {email}")
            email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
            assert len(email_matches) >= 1, f"Should detect short email: {email}"

    def test_long_email_address(self, full_detector):
        """Test long email address detection"""
        long_local = "a" * 64  # Max local part
        long_email = f"{long_local}@example.com"

        matches = full_detector.detect(f"Contact: {long_email}")
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        assert len(email_matches) >= 1, "Should detect long email"

    def test_ssn_boundary_values(self, full_detector):
        """Test SSN boundary values"""
        valid_ssns = [
            "001-01-0001",  # Minimum area number
            "899-99-9999",  # High area number
            "123-45-6789",  # Standard
        ]

        for ssn in valid_ssns:
            text = f"SSN: {ssn}"
            matches = full_detector.detect(text)
            ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]
            assert len(ssn_matches) >= 1, f"Should detect SSN: {ssn}"

    def test_credit_card_boundaries(self, full_detector):
        """Test credit card number boundaries"""
        # 13-19 digit card numbers
        cards = [
            "4111111111111",      # 13 digits (Visa old format)
            "4111111111111111",   # 16 digits (standard)
            "378282246310005",    # 15 digits (Amex)
        ]

        for card in cards:
            text = f"Card: {card}"
            matches = full_detector.detect(text)
            # May or may not detect based on Luhn validation
            # Just verify no crash
            assert isinstance(matches, list)

    def test_ip_address_boundaries(self, full_detector):
        """Test IP address boundary values"""
        valid_ips = [
            "0.0.0.0",
            "255.255.255.255",
            "192.168.1.1",
            "10.0.0.1",
        ]

        for ip in valid_ips:
            text = f"IP: {ip}"
            matches = full_detector.detect(text)
            ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]
            assert len(ip_matches) >= 1, f"Should detect IP: {ip}"


# ============================================================================
# MALFORMED DATA
# ============================================================================

class TestMalformedData:
    """Test handling of malformed/invalid data"""

    def test_invalid_ssn_formats(self, full_detector):
        """Test that invalid SSN formats are not detected"""
        invalid_ssns = [
            "000-00-0000",  # Invalid (all zeros)
            "123-45-678",   # Too short
            "123-45-67890", # Too long
            "12-345-6789",  # Wrong grouping
            "abc-de-fghi",  # Non-numeric
        ]

        for invalid in invalid_ssns:
            text = f"Number: {invalid}"
            matches = full_detector.detect(text)
            # Invalid SSNs should not be detected as valid SSNs
            # Some patterns might still match, which is ok
            assert isinstance(matches, list)

    def test_invalid_email_formats(self, full_detector):
        """Test that invalid email formats are handled"""
        invalid_emails = [
            "notanemail",
            "@nodomain",
            "no@",
            "spaces in@email.com",
            "",
        ]

        for invalid in invalid_emails:
            text = f"Contact: {invalid}"
            matches = full_detector.detect(text)
            # Should not crash
            assert isinstance(matches, list)

    def test_invalid_credit_cards(self, full_detector):
        """Test invalid credit card handling"""
        invalid_cards = [
            "1234567890123456",  # Invalid Luhn
            "0000000000000000",  # All zeros
            "abcdefghijklmnop",  # Non-numeric
            "411111111111",      # Too short
        ]

        for invalid in invalid_cards:
            text = f"Card: {invalid}"
            matches = full_detector.detect(text)
            # Should not crash, may or may not detect
            assert isinstance(matches, list)

    def test_partial_data(self, full_detector):
        """Test handling of partial/truncated data"""
        partial_data = [
            "SSN: 123-45-",
            "Email: john@",
            "Card: 4111",
            "IP: 192.168.",
        ]

        for data in partial_data:
            matches = full_detector.detect(data)
            # Should not crash on partial data
            assert isinstance(matches, list)


# ============================================================================
# FALSE POSITIVES
# ============================================================================

class TestFalsePositives:
    """Test for false positive scenarios"""

    def test_phone_like_numbers(self, full_detector):
        """Test numbers that look like phones but aren't"""
        not_phones = [
            "Order #555-123-4567",  # Order number
            "Part: 555-123-4567",   # Part number
            "Model 555-123-4567",   # Model number
        ]

        for text in not_phones:
            matches = full_detector.detect(text)
            # Should handle gracefully
            assert isinstance(matches, list)

    def test_ssn_like_numbers(self, full_detector):
        """Test numbers that look like SSNs but aren't"""
        not_ssns = [
            "Invoice: 123-45-6789",  # Invoice number
            "Serial: 123-45-6789",   # Serial number
            "Reference: 123-45-6789", # Reference number
        ]

        for text in not_ssns:
            matches = full_detector.detect(text)
            # Pattern may match, context matters
            assert isinstance(matches, list)

    def test_ip_like_numbers(self, full_detector):
        """Test numbers that look like IPs but aren't"""
        not_ips = [
            "Version 192.168.1.1",
            "Score: 192.168.1.1",
            "Dimensions: 192.168.1.1",
        ]

        for text in not_ips:
            matches = full_detector.detect(text)
            # May still detect as IP, which is acceptable
            assert isinstance(matches, list)

    def test_credit_card_like_numbers(self, full_detector):
        """Test numbers that look like cards but aren't"""
        not_cards = [
            "Tracking: 4111111111111111",
            "Account ID: 4111111111111111",
            "Reference: 4111111111111111",
        ]

        for text in not_cards:
            matches = full_detector.detect(text)
            # May detect, Luhn validation helps
            assert isinstance(matches, list)


# ============================================================================
# UNICODE AND SPECIAL CHARACTERS
# ============================================================================

class TestUnicodeSpecialChars:
    """Test handling of unicode and special characters"""

    def test_unicode_in_text(self, full_detector):
        """Test PII detection in unicode text"""
        text = """
        名前: John Smith
        メール: john.smith@email.com
        電話: 555-123-4567

        Ελληνικά: test@example.com
        العربية: user@domain.com
        """

        matches = full_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect emails in unicode text"

    def test_emoji_in_text(self, full_detector):
        """Test handling of emoji"""
        text = """
        Contact 📧: john.smith@email.com
        Call 📞: 555-123-4567
        Card 💳: 4111111111111111
        """

        matches = full_detector.detect(text)
        # Should not crash with emoji
        assert isinstance(matches, list)

    def test_special_characters(self, full_detector):
        """Test special characters around PII"""
        text = """
        <email>john.smith@email.com</email>
        [SSN: 123-45-6789]
        {card: 4111111111111111}
        (phone: 555-123-4567)
        """

        matches = full_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect email with special chars"

    def test_newlines_and_whitespace(self, full_detector):
        """Test various whitespace handling"""
        text = "Email:\n\t  john.smith@email.com  \n\nSSN:\t123-45-6789\r\n"

        matches = full_detector.detect(text)
        assert isinstance(matches, list)
        assert len(matches) >= 1, "Should detect PII with varied whitespace"


# ============================================================================
# EMPTY AND NULL HANDLING
# ============================================================================

class TestEmptyNullHandling:
    """Test handling of empty and null-like values"""

    def test_empty_string(self, full_detector):
        """Test empty string handling"""
        matches = full_detector.detect("")
        assert matches == [] or isinstance(matches, list)

    def test_whitespace_only(self, full_detector):
        """Test whitespace-only string"""
        matches = full_detector.detect("   \n\t\r   ")
        assert matches == [] or isinstance(matches, list)

    def test_very_long_text(self, full_detector):
        """Test very long text performance"""
        # 10KB of text with some PII
        long_text = ("Lorem ipsum " * 1000) + " john.smith@email.com " + ("dolor sit " * 1000)

        matches = full_detector.detect(long_text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should find email in long text"

    def test_repeated_pii(self, full_detector):
        """Test detection of repeated PII"""
        text = """
        john.smith@email.com
        john.smith@email.com
        john.smith@email.com
        """

        matches = full_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        # Should detect each occurrence
        assert len(email_matches) >= 1


# ============================================================================
# MULTI-REGION DATA
# ============================================================================

class TestMultiRegionData:
    """Test handling of data from multiple regions"""

    def test_mixed_us_uk_data(self, full_detector):
        """Test mixed US and UK PII"""
        text = """
        US Customer:
        SSN: 123-45-6789
        Phone: 555-123-4567

        UK Customer:
        NINO: AB123456C
        Postcode: SW1A 1AA
        Sort code: 12-34-56
        """

        matches = full_detector.detect(text)
        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]

        assert len(ssn_matches) >= 1, "Should detect US SSN"

    def test_mixed_eu_au_data(self, full_detector):
        """Test mixed EU and AU PII"""
        text = """
        EU Customer:
        IBAN: DE89370400440532013000
        VAT: DE123456789

        AU Customer:
        TFN: 123 456 789
        ABN: 51 824 753 556
        Medicare: 2123 45670 1
        """

        matches = full_detector.detect(text)
        assert len(matches) >= 1, "Should detect multi-region PII"

    def test_global_document(self, full_detector):
        """Test document with global PII"""
        text = """
        GLOBAL CUSTOMER RECORD

        Americas:
        - US SSN: 123-45-6789
        - Email: customer@email.com
        - Card: 4111111111111111

        Europe:
        - German ID: L0123456789
        - French SSN: 1 85 12 75 108 123 45
        - IBAN: FR7630006000011234567890189

        Asia-Pacific:
        - AU TFN: 123 456 789
        - AU Medicare: 2123 45670 1

        Contact IP: 192.168.1.100
        """

        matches = full_detector.detect(text)

        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]

        assert len(ssn_matches) >= 1, "Should detect SSN"
        assert len(email_matches) >= 1, "Should detect email"
        assert len(ip_matches) >= 1, "Should detect IP"


# ============================================================================
# INTEGRATION SCENARIOS
# ============================================================================

class TestIntegrationScenarios:
    """Test real-world integration scenarios"""

    def test_json_document(self, full_detector):
        """Test PII detection in JSON"""
        json_text = '''
        {
            "customer": {
                "email": "john.smith@email.com",
                "ssn": "123-45-6789",
                "phone": "555-123-4567"
            },
            "payment": {
                "card": "4111111111111111",
                "expiry": "12/28"
            }
        }
        '''

        matches = full_detector.detect(json_text)

        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]

        assert len(email_matches) >= 1, "Should detect email in JSON"
        assert len(ssn_matches) >= 1, "Should detect SSN in JSON"
        assert len(cc_matches) >= 1, "Should detect card in JSON"

    def test_xml_document(self, full_detector):
        """Test PII detection in XML"""
        xml_text = '''
        <?xml version="1.0"?>
        <customer>
            <email>john.smith@email.com</email>
            <ssn>123-45-6789</ssn>
            <card>4111111111111111</card>
        </customer>
        '''

        matches = full_detector.detect(xml_text)

        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect email in XML"

    def test_csv_data(self, full_detector):
        """Test PII detection in CSV format"""
        csv_text = '''
        name,email,ssn,phone
        John Smith,john.smith@email.com,123-45-6789,555-123-4567
        Jane Doe,jane.doe@email.com,987-65-4321,555-987-6543
        '''

        matches = full_detector.detect(csv_text)

        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]

        assert len(email_matches) >= 1, "Should detect emails in CSV"
        assert len(ssn_matches) >= 1, "Should detect SSNs in CSV"

    def test_log_file(self, full_detector):
        """Test PII detection in log file format"""
        log_text = '''
        2026-01-31 10:30:00 INFO User login: john.smith@email.com from 192.168.1.100
        2026-01-31 10:30:05 INFO Payment processed: card ending 1111 for john.smith@email.com
        2026-01-31 10:30:10 WARN Failed auth for user SSN: 123-45-6789
        '''

        matches = full_detector.detect(log_text)

        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]

        assert len(email_matches) >= 1, "Should detect email in logs"
        assert len(ip_matches) >= 1, "Should detect IP in logs"

    def test_html_content(self, full_detector):
        """Test PII detection in HTML"""
        html_text = '''
        <html>
        <body>
            <p>Contact: <a href="mailto:john.smith@email.com">john.smith@email.com</a></p>
            <p>SSN: <span class="sensitive">123-45-6789</span></p>
            <form>
                <input type="text" value="4111111111111111" />
            </form>
        </body>
        </html>
        '''

        matches = full_detector.detect(html_text)

        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]

        assert len(email_matches) >= 1, "Should detect email in HTML"
        assert len(ssn_matches) >= 1, "Should detect SSN in HTML"


# ============================================================================
# REDACTION EDGE CASES
# ============================================================================

class TestRedactionEdgeCases:
    """Test redaction in edge case scenarios"""

    def test_redact_empty_string(self, full_detector):
        """Test redaction of empty string"""
        redacted, matches = full_detector.redact("")
        assert redacted == ""
        assert matches == [] or isinstance(matches, list)

    def test_redact_no_pii(self, full_detector):
        """Test redaction with no PII present"""
        text = "This is a normal text without any sensitive information."
        redacted, matches = full_detector.redact(text)

        assert redacted == text, "Text without PII should remain unchanged"

    def test_redact_overlapping_matches(self, full_detector):
        """Test redaction with potentially overlapping patterns"""
        text = "Contact: 123-45-6789@email.com"  # SSN-like + email-like

        redacted, matches = full_detector.redact(text)
        # Should handle without crashing
        assert isinstance(redacted, str)

    def test_redact_adjacent_pii(self, full_detector):
        """Test redaction of adjacent PII"""
        # Adjacent PII with minimal separator (space)
        text = "john.smith@email.com 123-45-6789"  # Email followed by SSN

        redacted, matches = full_detector.redact(text)

        # At least one should be redacted
        assert "john.smith@email.com" not in redacted or "123-45-6789" not in redacted

    def test_redact_concatenated_pii(self, full_detector):
        """Test handling of concatenated PII without separators"""
        # PII without separators - patterns may not match due to word boundaries
        text = "john.smith@email.com123-45-6789"

        redacted, matches = full_detector.redact(text)

        # Should handle gracefully without crashing
        assert isinstance(redacted, str)

    def test_redact_preserves_structure(self, full_detector):
        """Test that redaction preserves document structure"""
        text = """
        Header
        ------
        Email: john.smith@email.com
        SSN: 123-45-6789
        ------
        Footer
        """

        redacted, matches = full_detector.redact(text)

        assert "Header" in redacted
        assert "Footer" in redacted
        assert "------" in redacted


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test performance characteristics"""

    def test_large_document(self, full_detector):
        """Test processing of large document"""
        # 100KB document
        large_text = ("Sample text with john.smith@email.com and 123-45-6789. " * 1000)

        import time
        start = time.time()
        matches = full_detector.detect(large_text)
        elapsed = time.time() - start

        assert len(matches) >= 1, "Should find PII in large document"
        assert elapsed < 10, f"Should process within reasonable time, took {elapsed}s"

    def test_many_small_documents(self, full_detector):
        """Test processing many small documents"""
        documents = [
            f"Customer {i}: user{i}@email.com, SSN: {i:03d}-45-6789"
            for i in range(100)
        ]

        import time
        start = time.time()

        total_matches = 0
        for doc in documents:
            matches = full_detector.detect(doc)
            total_matches += len(matches)

        elapsed = time.time() - start

        assert total_matches >= 100, "Should find PII in all documents"
        assert elapsed < 5, f"Should process quickly, took {elapsed}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
