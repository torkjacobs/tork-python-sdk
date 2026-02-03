"""
Tests for US-Specific PII Detection
Part 1.1 of Comprehensive Test Plan
"""

import pytest
from tork_governance.detectors.pii_patterns import (
    PIIDetector, PIIType, detect_pii, redact_pii
)


class TestUSSSN:
    """Test US Social Security Number detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['us'])

    # Valid SSN formats
    @pytest.mark.parametrize("ssn,should_detect", [
        ("123-45-6789", True),
        ("123 45 6789", True),
        ("123456789", True),
        # Invalid patterns
        ("000-00-0000", False),  # All zeros
        ("666-00-0000", False),  # 666 area
        ("900-00-0000", False),  # 9XX area (ITIN range)
        ("123-00-6789", False),  # 00 group
        ("123-45-0000", False),  # 0000 serial
        # Edge cases
        ("111-11-1111", False),  # All same
        ("078-05-1120", True),   # Famous Woolworth SSN (valid format)
    ])
    def test_ssn_detection(self, detector, ssn, should_detect):
        text = f"SSN is {ssn}"
        matches = detector.detect(text)
        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]

        if should_detect:
            assert len(ssn_matches) >= 1, f"Should detect SSN: {ssn}"
        else:
            assert len(ssn_matches) == 0, f"Should NOT detect invalid SSN: {ssn}"

    def test_ssn_redaction(self, detector):
        text = "My SSN is 123-45-6789 and spouse SSN is 987-65-4321"
        redacted, matches = detector.redact(text)

        assert "123-45-6789" not in redacted
        assert "987-65-4321" not in redacted
        assert "[SSN_REDACTED]" in redacted
        assert len(matches) >= 2

    def test_ssn_in_context(self, detector):
        """Test SSN detection in realistic contexts"""
        contexts = [
            "Employee SSN: 123-45-6789",
            "Social Security Number: 123 45 6789",
            "Tax ID 123456789 for John Smith",
            "W2 shows SSN 123-45-6789 with wages $50,000",
        ]

        for text in contexts:
            matches = detector.detect(text)
            ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]
            assert len(ssn_matches) >= 1, f"Should detect SSN in: {text}"


class TestUSPhone:
    """Test US Phone Number detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['us'])

    @pytest.mark.parametrize("phone,should_detect", [
        ("(555) 123-4567", True),
        ("555-123-4567", True),
        ("555.123.4567", True),
        ("5551234567", True),
        ("+1 555-123-4567", True),
        ("+1-555-123-4567", True),
        ("1-555-123-4567", True),
        # Area codes must start with 2-9
        ("(123) 456-7890", False),   # Invalid: area code starts with 1
        ("(234) 567-8901", True),    # Valid: area code starts with 2
    ])
    def test_phone_detection(self, detector, phone, should_detect):
        text = f"Call me at {phone}"
        matches = detector.detect(text)
        phone_matches = [m for m in matches if m.pii_type == PIIType.PHONE_US]

        if should_detect:
            assert len(phone_matches) >= 1, f"Should detect phone: {phone}"
        else:
            assert len(phone_matches) == 0, f"Should NOT detect invalid phone: {phone}"

    def test_phone_redaction(self, detector):
        text = "Contact: (555) 123-4567 or +1 800-555-1234"
        redacted, matches = detector.redact(text)

        assert "(555) 123-4567" not in redacted
        assert "[PHONE_US_REDACTED]" in redacted


class TestUSDriverLicense:
    """Test US Driver License detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['us'])

    @pytest.mark.parametrize("dl,should_detect", [
        ("DL: A1234567", True),
        ("Driver License 123456789", True),
        ("D.L. #12345678", True),
        ("Driver's License: B9876543", True),
    ])
    def test_dl_detection(self, detector, dl, should_detect):
        matches = detector.detect(dl)
        dl_matches = [m for m in matches if m.pii_type == PIIType.DRIVER_LICENSE_US]

        if should_detect:
            assert len(dl_matches) >= 1, f"Should detect DL: {dl}"


class TestUSPassport:
    """Test US Passport detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['us'])

    @pytest.mark.parametrize("passport,should_detect", [
        ("Passport: 123456789", True),
        ("Passport #A12345678", True),
    ])
    def test_passport_detection(self, detector, passport, should_detect):
        matches = detector.detect(passport)
        passport_matches = [m for m in matches if m.pii_type == PIIType.PASSPORT_US]

        if should_detect:
            assert len(passport_matches) >= 1, f"Should detect passport: {passport}"


class TestUSEIN:
    """Test US Employer Identification Number detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['us'])

    @pytest.mark.parametrize("ein,should_detect", [
        ("EIN: 12-3456789", True),
        ("EIN 123456789", True),
        ("EIN# 12-3456789", True),
    ])
    def test_ein_detection(self, detector, ein, should_detect):
        matches = detector.detect(ein)
        ein_matches = [m for m in matches if m.pii_type == PIIType.EIN]

        if should_detect:
            assert len(ein_matches) >= 1, f"Should detect EIN: {ein}"


class TestUSITIN:
    """Test US Individual Taxpayer Identification Number detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['us'])

    @pytest.mark.parametrize("itin,should_detect", [
        ("912-34-5678", True),
        ("900-12-3456", True),
        ("988-76-5432", True),
        # Non-ITIN (regular SSN range)
        ("123-45-6789", False),  # Not in 9XX range
    ])
    def test_itin_detection(self, detector, itin, should_detect):
        text = f"ITIN: {itin}"
        matches = detector.detect(text)
        itin_matches = [m for m in matches if m.pii_type == PIIType.ITIN]

        if should_detect:
            assert len(itin_matches) >= 1, f"Should detect ITIN: {itin}"


class TestUSCombined:
    """Test combined US PII detection scenarios"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['us'])

    def test_multiple_pii_types(self, detector):
        """Test detecting multiple PII types in one text"""
        text = """
        Employee Record:
        Name: John Smith
        SSN: 123-45-6789
        Phone: (555) 123-4567
        Driver License: A1234567
        EIN: 12-3456789
        """

        matches = detector.detect(text)
        types_found = {m.pii_type for m in matches}

        assert PIIType.SSN in types_found
        assert PIIType.PHONE_US in types_found

    def test_full_redaction(self, detector):
        """Test full redaction of realistic document"""
        text = """
        CONFIDENTIAL EMPLOYEE INFORMATION

        Name: John Doe
        SSN: 123-45-6789
        Phone: (555) 123-4567
        Emergency Contact: (555) 987-6543
        Driver License: CA A1234567
        """

        redacted, matches = detector.redact(text)

        # Verify all PII is redacted
        assert "123-45-6789" not in redacted
        assert "(555) 123-4567" not in redacted
        assert "(555) 987-6543" not in redacted

        # Verify redaction markers are present
        assert "[SSN_REDACTED]" in redacted
        assert "[PHONE_US_REDACTED]" in redacted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
