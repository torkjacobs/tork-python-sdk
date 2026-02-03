"""
Tests for European and UK-Specific PII Detection
Part 1.3 of Comprehensive Test Plan
"""

import pytest
from tork_governance.detectors.pii_patterns import (
    PIIDetector, PIIType, detect_pii, redact_pii
)


# ============================================================================
# IBAN TESTS (International Bank Account Number)
# ============================================================================

class TestIBAN:
    """Test IBAN detection across European countries"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['eu'])

    @pytest.mark.parametrize("iban,should_detect,country", [
        # Valid IBANs (real checksum-valid examples)
        ("DE89370400440532013000", True, "Germany"),
        ("GB29NWBK60161331926819", True, "UK"),
        ("FR7630006000011234567890189", True, "France"),
        ("ES9121000418450200051332", True, "Spain"),
        ("IT60X0542811101000000123456", True, "Italy"),
        ("NL91ABNA0417164300", True, "Netherlands"),
        ("BE68539007547034", True, "Belgium"),
        ("CH9300762011623852957", True, "Switzerland"),
        ("AT611904300234573201", True, "Austria"),
        # With spaces (common format)
        ("DE89 3704 0044 0532 0130 00", True, "Germany spaced"),
        ("GB29 NWBK 6016 1331 9268 19", True, "UK spaced"),
        # Invalid IBANs
        ("DE00000000000000000000", False, "Invalid checksum"),
        ("XX00000000000000", False, "Invalid country code"),
        ("DE8", False, "Too short"),
    ])
    def test_iban_detection(self, detector, iban, should_detect, country):
        text = f"Bank Account: {iban}"
        matches = detector.detect(text)
        iban_matches = [m for m in matches if m.pii_type == PIIType.IBAN]

        if should_detect:
            assert len(iban_matches) >= 1, f"Should detect IBAN ({country}): {iban}"
        else:
            assert len(iban_matches) == 0, f"Should NOT detect invalid IBAN ({country}): {iban}"

    def test_iban_redaction(self, detector):
        text = "Transfer to IBAN DE89370400440532013000 for invoice payment"
        redacted, matches = detector.redact(text)

        assert "DE89370400440532013000" not in redacted
        assert "[IBAN_REDACTED]" in redacted


# ============================================================================
# UK NATIONAL INSURANCE NUMBER (NINO)
# ============================================================================

class TestUKNINO:
    """Test UK National Insurance Number detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['uk'])

    @pytest.mark.parametrize("nino,should_detect,description", [
        # Valid formats
        ("AB 12 34 56 C", True, "Standard spaced format"),
        ("AB123456C", True, "No spaces"),
        ("AB-12-34-56-C", True, "Dashed format"),
        ("JG 10 20 30 A", True, "Another valid NINO"),
        ("SP 00 00 00 D", True, "Valid prefix SP"),
        # Different valid suffixes (A, B, C, D)
        ("AB 12 34 56 A", True, "Suffix A"),
        ("AB 12 34 56 B", True, "Suffix B"),
        ("AB 12 34 56 D", True, "Suffix D"),
        # Invalid prefixes (BG, GB, KN, NK, NT, TN, ZZ)
        ("BG 12 34 56 A", False, "Invalid prefix BG"),
        ("GB 12 34 56 A", False, "Invalid prefix GB"),
        ("NK 12 34 56 A", False, "Invalid prefix NK"),
        ("TN 12 34 56 A", False, "Invalid prefix TN"),
        # Invalid format
        ("AB 12 34 56", False, "Missing suffix"),
        ("AB 12 34 56 E", False, "Invalid suffix E"),
    ])
    def test_nino_detection(self, detector, nino, should_detect, description):
        text = f"NI Number: {nino}"
        matches = detector.detect(text)
        nino_matches = [m for m in matches if m.pii_type == PIIType.NINO_UK]

        if should_detect:
            assert len(nino_matches) >= 1, f"Should detect NINO ({description}): {nino}"
        else:
            assert len(nino_matches) == 0, f"Should NOT detect invalid NINO ({description}): {nino}"

    def test_nino_in_payroll_context(self, detector):
        """Test NINO in payroll document"""
        text = """
        PAYSLIP
        Employee: John Smith
        NI Number: AB 12 34 56 C
        Tax Code: 1257L
        """
        matches = detector.detect(text)
        nino_matches = [m for m in matches if m.pii_type == PIIType.NINO_UK]
        assert len(nino_matches) >= 1, "Should detect NINO in payslip"


# ============================================================================
# UK NHS NUMBER
# ============================================================================

class TestUKNHS:
    """Test UK NHS Number detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['uk'])

    @pytest.mark.parametrize("nhs,should_detect,description", [
        # Valid NHS numbers (checksum valid)
        ("943 476 5919", True, "Valid spaced format"),
        ("9434765919", True, "Valid no spaces"),
        ("943-476-5919", True, "Valid dashed"),
        ("450 557 7104", True, "Another valid NHS"),
        # Invalid checksums
        ("123 456 7890", False, "Invalid checksum"),
        ("000 000 0000", False, "All zeros"),
        ("111 111 1111", False, "All ones"),
        # Invalid format
        ("943 476 591", False, "Too short"),
        ("943 476 59199", False, "Too long"),
    ])
    def test_nhs_detection(self, detector, nhs, should_detect, description):
        text = f"NHS Number: {nhs}"
        matches = detector.detect(text)
        nhs_matches = [m for m in matches if m.pii_type == PIIType.NHS_UK]

        if should_detect:
            assert len(nhs_matches) >= 1, f"Should detect NHS ({description}): {nhs}"
        else:
            assert len(nhs_matches) == 0, f"Should NOT detect invalid NHS ({description}): {nhs}"

    def test_nhs_in_medical_context(self, detector):
        """Test NHS number in medical document"""
        text = """
        NHS Patient Record
        Name: Jane Doe
        NHS Number: 943 476 5919
        DOB: 15/03/1980
        """
        matches = detector.detect(text)
        nhs_matches = [m for m in matches if m.pii_type == PIIType.NHS_UK]
        assert len(nhs_matches) >= 1, "Should detect NHS in patient record"


# ============================================================================
# UK POSTCODE
# ============================================================================

class TestUKPostcode:
    """Test UK Postcode detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['uk'])

    @pytest.mark.parametrize("postcode,should_detect,description", [
        # Valid formats
        ("SW1A 1AA", True, "Westminster"),
        ("EC1A 1BB", True, "City of London"),
        ("W1A 0AX", True, "BBC"),
        ("M1 1AE", True, "Manchester"),
        ("B33 8TH", True, "Birmingham"),
        ("CR2 6XH", True, "Croydon"),
        ("DN55 1PT", True, "Doncaster"),
        ("GIR 0AA", True, "Girobank"),
        # Without space
        ("SW1A1AA", True, "No space"),
        # Invalid
        ("12345", False, "US zip code"),
        ("ABCD 123", False, "Invalid format"),
    ])
    def test_postcode_detection(self, detector, postcode, should_detect, description):
        text = f"Address: {postcode}"
        matches = detector.detect(text)
        postcode_matches = [m for m in matches if m.pii_type == PIIType.POSTCODE_UK]

        if should_detect:
            assert len(postcode_matches) >= 1, f"Should detect postcode ({description}): {postcode}"
        else:
            assert len(postcode_matches) == 0, f"Should NOT detect ({description}): {postcode}"


# ============================================================================
# UK SORT CODE
# ============================================================================

class TestUKSortCode:
    """Test UK Bank Sort Code detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['uk'])

    @pytest.mark.parametrize("sort_code,should_detect", [
        ("20-00-00", True),
        ("20 00 00", True),
        ("200000", True),
        ("40-47-84", True),
        ("60-83-71", True),
    ])
    def test_sort_code_detection(self, detector, sort_code, should_detect):
        text = f"Sort Code: {sort_code}"
        matches = detector.detect(text)
        sort_matches = [m for m in matches if m.pii_type == PIIType.SORT_CODE_UK]

        if should_detect:
            assert len(sort_matches) >= 1, f"Should detect sort code: {sort_code}"


# ============================================================================
# EU VAT NUMBER
# ============================================================================

class TestEUVAT:
    """Test EU VAT Number detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['eu'])

    @pytest.mark.parametrize("vat,should_detect,country", [
        # Valid VAT numbers
        ("DE123456789", True, "Germany"),
        ("FR12345678901", True, "France"),
        ("IT12345678901", True, "Italy"),
        ("ES12345678A", True, "Spain"),
        ("NL123456789B01", True, "Netherlands"),
        ("BE0123456789", True, "Belgium"),
        ("AT123456789", True, "Austria"),
        ("PL1234567890", True, "Poland"),
        # Invalid
        ("US123456789", False, "Invalid country US"),
        ("XX123456789", False, "Invalid country XX"),
    ])
    def test_vat_detection(self, detector, vat, should_detect, country):
        text = f"VAT: {vat}"
        matches = detector.detect(text)
        vat_matches = [m for m in matches if m.pii_type == PIIType.VAT_EU]

        if should_detect:
            assert len(vat_matches) >= 1, f"Should detect VAT ({country}): {vat}"
        else:
            assert len(vat_matches) == 0, f"Should NOT detect VAT ({country}): {vat}"


# ============================================================================
# EU PHONE NUMBERS
# ============================================================================

class TestEUPhone:
    """Test European Phone Number detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['eu'])

    @pytest.mark.parametrize("phone,should_detect,country", [
        # Germany (+49)
        ("+49 30 12345678", True, "Germany"),
        ("+49 170 1234567", True, "Germany mobile"),
        # France (+33)
        ("+33 1 23 45 67 89", True, "France"),
        ("+33 6 12 34 56 78", True, "France mobile"),
        # Italy (+39)
        ("+39 02 12345678", True, "Italy"),
        # Spain (+34)
        ("+34 91 123 4567", True, "Spain"),
        # Netherlands (+31)
        ("+31 20 1234567", True, "Netherlands"),
    ])
    def test_eu_phone_detection(self, detector, phone, should_detect, country):
        text = f"Contact: {phone}"
        matches = detector.detect(text)
        phone_matches = [m for m in matches if m.pii_type == PIIType.PHONE_EU]

        if should_detect:
            assert len(phone_matches) >= 1, f"Should detect EU phone ({country}): {phone}"


# ============================================================================
# GERMAN ID (PERSONALAUSWEIS)
# ============================================================================

class TestGermanID:
    """Test German ID Number detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['eu'])

    @pytest.mark.parametrize("german_id,should_detect", [
        ("T220001293", True),
        ("L01X00T471", True),
        ("C01X00T471", True),
        # Invalid - must start with specific letters
        ("A01X00T471", False),
        ("123456789", False),
    ])
    def test_german_id_detection(self, detector, german_id, should_detect):
        text = f"Personalausweis: {german_id}"
        matches = detector.detect(text)
        id_matches = [m for m in matches if m.pii_type == PIIType.GERMAN_ID]

        if should_detect:
            assert len(id_matches) >= 1, f"Should detect German ID: {german_id}"


# ============================================================================
# FRENCH SSN (NIR)
# ============================================================================

class TestFrenchSSN:
    """Test French Social Security Number (NIR) detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['eu'])

    @pytest.mark.parametrize("nir,should_detect,description", [
        ("1 85 05 78 006 084 36", True, "Standard format with spaces"),
        ("185057800608436", True, "No spaces"),
        ("2 91 12 75 115 005 42", True, "Female, different dept"),
        # Structure: Sex(1) Year(2) Month(2) Dept(2) Commune(3) Order(3) Key(2)
    ])
    def test_french_ssn_detection(self, detector, nir, should_detect, description):
        text = f"NIR: {nir}"
        matches = detector.detect(text)
        nir_matches = [m for m in matches if m.pii_type == PIIType.FRENCH_SSN]

        if should_detect:
            assert len(nir_matches) >= 1, f"Should detect French NIR ({description}): {nir}"


# ============================================================================
# COMBINED EU/UK TESTS
# ============================================================================

class TestEUUKCombined:
    """Test combined EU/UK PII detection scenarios"""

    def test_uk_payroll_document(self):
        """Test UK payroll with multiple PII types"""
        detector = PIIDetector(regions=['uk'])
        text = """
        UK PAYROLL DOCUMENT

        Employee: John Smith
        NI Number: AB 12 34 56 C
        Address: 10 Downing Street, London SW1A 2AA
        Bank Sort Code: 20-00-00
        """

        matches = detector.detect(text)
        types_found = {m.pii_type for m in matches}

        assert PIIType.NINO_UK in types_found or PIIType.POSTCODE_UK in types_found, \
            f"Should find UK PII, found: {types_found}"

    def test_eu_invoice(self):
        """Test EU invoice with multiple PII types"""
        detector = PIIDetector(regions=['eu'])
        text = """
        INVOICE

        Seller VAT: DE123456789
        Bank: IBAN DE89370400440532013000
        Contact: +49 30 12345678
        """

        matches = detector.detect(text)
        types_found = {m.pii_type for m in matches}

        assert len(matches) >= 1, f"Should find EU PII, found: {types_found}"

    def test_gdpr_data_subject_request(self):
        """Test GDPR data subject request with mixed PII"""
        detector = PIIDetector(regions=['eu', 'uk'])
        text = """
        GDPR Data Subject Access Request

        Requester: Hans Mueller
        German ID: T220001293
        UK NI (former): AB 12 34 56 C
        IBAN: DE89370400440532013000
        Phone: +49 170 1234567
        """

        matches = detector.detect(text)
        assert len(matches) >= 2, "Should detect multiple PII types in GDPR request"

    def test_cross_border_transaction(self):
        """Test cross-border EU transaction document"""
        detector = PIIDetector(regions=['eu', 'uk'])
        text = """
        CROSS-BORDER PAYMENT

        Sender IBAN: GB29NWBK60161331926819
        Sender Sort Code: 20-00-00

        Recipient IBAN: DE89370400440532013000
        Recipient VAT: DE123456789
        """

        matches = detector.detect(text)
        iban_matches = [m for m in matches if m.pii_type == PIIType.IBAN]
        assert len(iban_matches) >= 2, "Should detect both IBANs"


# ============================================================================
# REAL WORLD SCENARIOS
# ============================================================================

class TestEUUKRealWorld:
    """Test real-world EU/UK scenarios"""

    def test_uk_nhs_patient_record(self):
        """Test UK NHS patient record"""
        detector = PIIDetector(regions=['uk'])
        text = """
        NHS PATIENT RECORD

        Name: Jane Smith
        NHS Number: 943 476 5919
        Address: 123 High Street, London EC1A 1BB
        NI Number: AB 12 34 56 C
        """

        matches = detector.detect(text)
        nhs_matches = [m for m in matches if m.pii_type == PIIType.NHS_UK]
        assert len(nhs_matches) >= 1, "Should detect NHS number"

    def test_german_tax_document(self):
        """Test German tax document"""
        detector = PIIDetector(regions=['eu'])
        text = """
        STEUERERKLÄRUNG (Tax Return)

        Personalausweis: T220001293
        IBAN: DE89370400440532013000
        Steuernummer: DE123456789
        Telefon: +49 30 12345678
        """

        matches = detector.detect(text)
        assert len(matches) >= 2, "Should detect German PII"

    def test_french_social_security(self):
        """Test French social security document"""
        detector = PIIDetector(regions=['eu'])
        text = """
        SÉCURITÉ SOCIALE

        NIR: 1 85 05 78 006 084 36
        IBAN: FR7630006000011234567890189
        Téléphone: +33 1 23 45 67 89
        """

        matches = detector.detect(text)
        assert len(matches) >= 1, "Should detect French PII"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
