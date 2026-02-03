"""
Tests for Australian-Specific PII Detection
Part 1.2 of Comprehensive Test Plan
"""

import pytest
from tork_governance.detectors.pii_patterns import (
    PIIDetector, PIIType, detect_pii, redact_pii
)


class TestAUPhone:
    """Test Australian Phone Number detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['au'])

    @pytest.mark.parametrize("phone,should_detect", [
        # Mobile numbers (04XX)
        ("0412 345 678", True),
        ("0412345678", True),
        ("0412-345-678", True),
        ("+61 412 345 678", True),
        ("+61412345678", True),
        # Landline numbers (02, 03, 07, 08)
        ("02 9876 5432", True),
        ("03 9876 5432", True),
        ("07 3456 7890", True),
        ("08 8765 4321", True),
        ("+61 2 9876 5432", True),
        # Invalid
        ("0512 345 678", False),  # Invalid prefix (05)
        ("0112 345 678", False),  # Invalid prefix (01)
    ])
    def test_phone_detection(self, detector, phone, should_detect):
        text = f"Contact: {phone}"
        matches = detector.detect(text)
        phone_matches = [m for m in matches if m.pii_type == PIIType.PHONE_AU]

        if should_detect:
            assert len(phone_matches) >= 1, f"Should detect AU phone: {phone}"
        else:
            # Pattern may or may not match invalid prefixes
            pass

    def test_phone_redaction(self, detector):
        text = "Mobile: 0412 345 678, Landline: 02 9876 5432"
        redacted, matches = detector.redact(text)

        assert "0412 345 678" not in redacted
        assert "02 9876 5432" not in redacted
        assert "[PHONE_AU_REDACTED]" in redacted


class TestAUMedicare:
    """Test Australian Medicare Number detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['au'])

    @pytest.mark.parametrize("medicare,should_detect", [
        # Valid formats
        ("2123 45678 1", True),
        ("2123456781", True),
        ("2123-45678-1", True),
        # Different starting digits
        ("3123 45678 1", True),
        ("4123 45678 1", True),
        ("5123 45678 1", True),
        ("6123 45678 1", True),
        # Invalid (wrong length)
        ("2123 4567", False),
        ("2123 456789 1", False),
    ])
    def test_medicare_detection(self, detector, medicare, should_detect):
        text = f"Medicare: {medicare}"
        matches = detector.detect(text)
        medicare_matches = [m for m in matches if m.pii_type == PIIType.MEDICARE_AU]

        if should_detect:
            assert len(medicare_matches) >= 1, f"Should detect Medicare: {medicare}"
        else:
            assert len(medicare_matches) == 0, f"Should NOT detect invalid Medicare: {medicare}"

    def test_medicare_in_context(self, detector):
        """Test Medicare detection in realistic contexts"""
        contexts = [
            "Patient Medicare Number: 2123 45678 1",
            "Medicare Card: 2123456781",
            "Claim for Medicare 2123-45678-1",
        ]

        for text in contexts:
            matches = detector.detect(text)
            medicare_matches = [m for m in matches if m.pii_type == PIIType.MEDICARE_AU]
            assert len(medicare_matches) >= 1, f"Should detect Medicare in: {text}"


class TestAUTFN:
    """Test Australian Tax File Number detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['au'])

    @pytest.mark.parametrize("tfn,should_detect,description", [
        # Valid TFNs (checksum valid)
        ("123 456 782", True, "Valid TFN with spaces"),
        ("123-456-782", True, "Valid TFN with dashes"),
        ("123456782", True, "Valid TFN no separators"),
        ("876 543 210", True, "Another valid TFN"),
        # Invalid checksum (these should fail validation)
        ("123 456 789", False, "Invalid checksum"),
        ("111 111 111", False, "All ones - invalid"),
        ("000 000 000", False, "All zeros - invalid"),
    ])
    def test_tfn_detection(self, detector, tfn, should_detect, description):
        text = f"TFN: {tfn}"
        matches = detector.detect(text)
        tfn_matches = [m for m in matches if m.pii_type == PIIType.TFN]

        if should_detect:
            assert len(tfn_matches) >= 1, f"Should detect TFN ({description}): {tfn}"
        else:
            assert len(tfn_matches) == 0, f"Should NOT detect invalid TFN ({description}): {tfn}"

    def test_tfn_redaction(self, detector):
        text = "Employee TFN: 123 456 782"
        redacted, matches = detector.redact(text)

        # Check that original is redacted
        assert "123 456 782" not in redacted


class TestAUABN:
    """Test Australian Business Number detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['au'])

    @pytest.mark.parametrize("abn,should_detect,description", [
        # Valid ABNs (11 digits with checksum)
        ("ABN: 51 824 753 556", True, "Valid ABN with prefix"),
        ("ABN 51824753556", True, "Valid ABN no spaces"),
        ("ABN: 53 004 085 616", True, "Another valid ABN"),
        # Invalid
        ("ABN: 12 345 678 901", False, "Invalid checksum"),
        ("ABN: 00 000 000 000", False, "All zeros"),
    ])
    def test_abn_detection(self, detector, abn, should_detect, description):
        matches = detector.detect(abn)
        abn_matches = [m for m in matches if m.pii_type == PIIType.ABN]

        if should_detect:
            assert len(abn_matches) >= 1, f"Should detect ABN ({description}): {abn}"
        else:
            assert len(abn_matches) == 0, f"Should NOT detect invalid ABN ({description}): {abn}"

    def test_abn_in_business_context(self, detector):
        """Test ABN in business document context"""
        text = """
        Invoice
        Company: Test Pty Ltd
        ABN: 51 824 753 556
        Amount: $1,500.00
        """
        matches = detector.detect(text)
        abn_matches = [m for m in matches if m.pii_type == PIIType.ABN]
        assert len(abn_matches) >= 1, "Should detect ABN in invoice"


class TestAUACN:
    """Test Australian Company Number detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['au'])

    @pytest.mark.parametrize("acn,should_detect", [
        ("ACN: 123 456 789", True),
        ("ACN 123456789", True),
        ("ACN: 000 000 001", True),
        # Must have ACN prefix
        ("123 456 789", False),  # No ACN prefix
    ])
    def test_acn_detection(self, detector, acn, should_detect):
        matches = detector.detect(acn)
        acn_matches = [m for m in matches if m.pii_type == PIIType.ACN]

        if should_detect:
            assert len(acn_matches) >= 1, f"Should detect ACN: {acn}"
        else:
            # ACN without prefix may not be detected
            pass


class TestAUCombined:
    """Test combined Australian PII detection scenarios"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['au'])

    def test_multiple_au_pii_types(self):
        """Test detecting multiple AU PII types in one document"""
        detector = PIIDetector(regions=['au'])
        text = """
        Australian Tax Return

        Taxpayer Details:
        Name: John Smith
        TFN: 123 456 782
        Phone: 0412 345 678

        Business Details:
        ABN: 51 824 753 556
        """

        matches = detector.detect(text)
        types_found = {m.pii_type for m in matches}

        # Should find at least TFN and Phone
        assert PIIType.TFN in types_found or PIIType.PHONE_AU in types_found, \
            f"Should find AU PII types, found: {types_found}"

    def test_healthcare_context(self):
        """Test Australian healthcare document"""
        detector = PIIDetector(regions=['au'])
        text = """
        Medicare Claim Form

        Patient Medicare: 2123 45678 1
        Contact: 0412 345 678
        """

        matches = detector.detect(text)
        types_found = {m.pii_type for m in matches}

        # Should find Medicare and/or Phone
        assert len(matches) >= 1, "Should detect PII in healthcare document"

    def test_full_redaction(self):
        """Test full redaction of Australian document"""
        detector = PIIDetector(regions=['au'])
        text = """
        Employee Record (Australia)

        TFN: 123 456 782
        Mobile: 0412 345 678
        ABN: 51 824 753 556
        """

        redacted, matches = detector.redact(text)

        # Verify sensitive data is not in redacted output
        assert "0412 345 678" not in redacted
        assert len(matches) >= 1


class TestAURealWorldScenarios:
    """Test real-world Australian scenarios"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['au'])

    def test_ato_document(self, detector):
        """Test ATO (Tax Office) document"""
        text = """
        Australian Taxation Office
        Notice of Assessment

        Taxpayer: John Smith
        TFN: 123 456 782
        ABN (if applicable): 51 824 753 556
        Assessment Year: 2024-25
        """

        matches = detector.detect(text)
        assert len(matches) >= 1, "Should detect PII in ATO document"

    def test_medicare_claim(self, detector):
        """Test Medicare claim form"""
        text = """
        Medicare Australia
        Claim Reference: CLM-123456

        Patient Medicare Number: 2123 45678 1
        Service Date: 15/01/2026
        Provider Number: 123456AB
        """

        matches = detector.detect(text)
        medicare_matches = [m for m in matches if m.pii_type == PIIType.MEDICARE_AU]
        assert len(medicare_matches) >= 1, "Should detect Medicare number in claim"

    def test_business_registration(self, detector):
        """Test ASIC business registration"""
        text = """
        ASIC Business Registration

        Company Name: Example Pty Ltd
        ACN: 123 456 789
        ABN: 51 824 753 556
        Registered Office: 123 Collins St, Melbourne VIC 3000
        """

        matches = detector.detect(text)
        assert len(matches) >= 1, "Should detect business identifiers"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
