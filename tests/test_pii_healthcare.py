"""
Tests for Healthcare/HIPAA PII Detection
Part 1.6 of Comprehensive Test Plan
Covers: Patient ID, MRN, NPI, DEA Number, ICD Codes, CPT Codes, Health Plan ID
"""

import pytest
from tork_governance.detectors.pii_patterns import (
    PIIDetector, PIIType, detect_pii, redact_pii
)


# ============================================================================
# PATIENT ID TESTS
# ============================================================================

class TestPatientID:
    """Test Patient ID detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['healthcare'])

    @pytest.mark.parametrize("patient_id,should_detect,description", [
        # With prefix (required)
        ("Patient ID: ABC12345", True, "Alphanumeric"),
        ("Patient ID: 12345678", True, "Numeric only"),
        ("Patient #: P-123456", True, "With dash"),
        ("Patient: PAT00001234", True, "Patient prefix"),
        ("PID: 1234567890", True, "PID prefix"),
        ("Patient ID: A1B2C3D4E5", True, "Mixed alphanumeric"),
        # Different lengths (5-15 chars)
        ("Patient ID: 12345", True, "5 chars"),
        ("Patient ID: 123456789012345", True, "15 chars"),
        # Without prefix
        ("ABC12345", False, "No prefix"),
        # Too short/long
        ("Patient ID: 1234", False, "4 chars - too short"),
        ("Patient ID: 1234567890123456", False, "16 chars - too long"),
    ])
    def test_patient_id_detection(self, detector, patient_id, should_detect, description):
        text = patient_id
        matches = detector.detect(text)
        pid_matches = [m for m in matches if m.pii_type == PIIType.PATIENT_ID]

        if should_detect:
            assert len(pid_matches) >= 1, f"Should detect patient ID ({description}): {patient_id}"
        else:
            assert len(pid_matches) == 0, f"Should NOT detect ({description}): {patient_id}"


# ============================================================================
# MEDICAL RECORD NUMBER (MRN) TESTS
# ============================================================================

class TestMRN:
    """Test Medical Record Number detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['healthcare'])

    @pytest.mark.parametrize("mrn,should_detect,description", [
        # With prefix
        ("MRN: 123456", True, "6 digits"),
        ("MRN: 1234567890", True, "10 digits"),
        ("MRN #1234567", True, "Hash prefix"),
        ("Medical Record: 12345678", True, "Full phrase"),
        ("Medical Record Number: 123456789", True, "Full phrase"),
        # Without prefix
        ("123456789", False, "No prefix"),
        # Too short/long
        ("MRN: 12345", False, "5 digits - too short"),
        ("MRN: 12345678901", False, "11 digits - too long"),
    ])
    def test_mrn_detection(self, detector, mrn, should_detect, description):
        text = mrn
        matches = detector.detect(text)
        mrn_matches = [m for m in matches if m.pii_type == PIIType.MRN]

        if should_detect:
            assert len(mrn_matches) >= 1, f"Should detect MRN ({description}): {mrn}"
        else:
            assert len(mrn_matches) == 0, f"Should NOT detect ({description}): {mrn}"


# ============================================================================
# NPI (National Provider Identifier) TESTS
# ============================================================================

class TestNPI:
    """Test NPI detection with Luhn validation"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['healthcare'])

    @pytest.mark.parametrize("npi,should_detect,description", [
        # Valid NPIs (10-digit, Luhn valid with 80840 prefix)
        ("NPI: 1234567893", True, "Valid NPI"),
        ("NPI: 1245319599", True, "Valid NPI 2"),
        ("NPI: 1497758544", True, "Valid NPI 3"),
        ("NPI #: 1120000009", True, "Hash prefix"),
        ("NPI Number: 1340000003", True, "Full phrase"),
        # Different prefixes
        ("Provider NPI: 1234567893", True, "Provider prefix"),
        # Invalid (wrong checksum)
        ("NPI: 1234567890", False, "Invalid checksum"),
        ("NPI: 0000000000", False, "All zeros"),
        # Without prefix
        ("1234567893", False, "No prefix"),
        # Wrong length
        ("NPI: 123456789", False, "9 digits"),
        ("NPI: 12345678901", False, "11 digits"),
    ])
    def test_npi_detection(self, detector, npi, should_detect, description):
        text = npi
        matches = detector.detect(text)
        npi_matches = [m for m in matches if m.pii_type == PIIType.NPI]

        if should_detect:
            assert len(npi_matches) >= 1, f"Should detect NPI ({description}): {npi}"
        else:
            assert len(npi_matches) == 0, f"Should NOT detect ({description}): {npi}"


# ============================================================================
# DEA NUMBER TESTS
# ============================================================================

class TestDEA:
    """Test DEA Number detection with checksum validation"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['healthcare'])

    @pytest.mark.parametrize("dea,should_detect,description", [
        # Valid DEA numbers (2 letters + 7 digits, checksum valid)
        # Format: AB1234563 where check digit = (1+3+5 + 2*(2+4+6)) mod 10 = last digit
        ("DEA: AB1234563", True, "Valid DEA"),
        ("DEA: MJ1234563", True, "Valid with M prefix"),
        ("DEA #: AB1234563", True, "Hash prefix"),
        ("DEA Number: AB1234563", True, "Full phrase"),
        # Different valid registrant types
        ("DEA: AB1234563", True, "Type A"),
        ("DEA: BB1234563", True, "Type B"),
        ("DEA: FB1234563", True, "Type F"),
        ("DEA: MB1234563", True, "Type M"),
        # Invalid checksum
        ("DEA: AB1234560", False, "Invalid checksum"),
        ("DEA: AB0000000", False, "All zeros"),
        # Without prefix
        ("AB1234563", False, "No prefix"),
        # Wrong format
        ("DEA: 123456789", False, "No letters"),
        ("DEA: ABCDEFGHI", False, "No numbers"),
    ])
    def test_dea_detection(self, detector, dea, should_detect, description):
        text = dea
        matches = detector.detect(text)
        dea_matches = [m for m in matches if m.pii_type == PIIType.DEA_NUMBER]

        if should_detect:
            assert len(dea_matches) >= 1, f"Should detect DEA ({description}): {dea}"
        else:
            assert len(dea_matches) == 0, f"Should NOT detect ({description}): {dea}"


# ============================================================================
# ICD CODE TESTS
# ============================================================================

class TestICDCode:
    """Test ICD-10 Diagnosis Code detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['healthcare'])

    @pytest.mark.parametrize("icd,should_detect,description", [
        # Valid ICD-10 codes
        ("ICD: A00.0", True, "Simple code"),
        ("ICD-10: Z99.89", True, "ICD-10 prefix"),
        ("Diagnosis: J06.9", True, "Diagnosis prefix"),
        ("Dx: M54.5", True, "Dx prefix"),
        # Different categories
        ("ICD: A00.0", True, "Infectious disease"),
        ("ICD: C34.90", True, "Neoplasm"),
        ("ICD: E11.9", True, "Endocrine"),
        ("ICD: F32.9", True, "Mental health"),
        ("ICD: I10", True, "Circulatory (no decimal)"),
        ("ICD: J18.9", True, "Respiratory"),
        ("ICD: K21.0", True, "Digestive"),
        ("ICD: M54.5", True, "Musculoskeletal"),
        ("ICD: S72.001A", True, "Injury with extension"),
        ("ICD: Z00.00", True, "Health status"),
        # Without prefix
        ("A00.0", False, "No prefix"),
    ])
    def test_icd_detection(self, detector, icd, should_detect, description):
        text = icd
        matches = detector.detect(text)
        icd_matches = [m for m in matches if m.pii_type == PIIType.ICD_CODE]

        if should_detect:
            assert len(icd_matches) >= 1, f"Should detect ICD ({description}): {icd}"
        else:
            assert len(icd_matches) == 0, f"Should NOT detect ({description}): {icd}"


# ============================================================================
# CPT CODE TESTS
# ============================================================================

class TestCPTCode:
    """Test CPT Procedure Code detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['healthcare'])

    @pytest.mark.parametrize("cpt,should_detect,description", [
        # Valid CPT codes (5 digits)
        ("CPT: 99213", True, "Office visit"),
        ("CPT: 99214", True, "Office visit extended"),
        ("CPT Code: 36415", True, "Blood draw"),
        ("Procedure: 99385", True, "Procedure prefix"),
        ("CPT #: 71046", True, "Chest X-ray"),
        # Category ranges
        ("CPT: 00100", True, "Anesthesia"),
        ("CPT: 10021", True, "Surgery"),
        ("CPT: 70010", True, "Radiology"),
        ("CPT: 80047", True, "Lab"),
        ("CPT: 90281", True, "Medicine"),
        ("CPT: 99201", True, "E&M"),
        # Without prefix
        ("99213", False, "No prefix"),
        # Wrong length
        ("CPT: 9921", False, "4 digits"),
        ("CPT: 992130", False, "6 digits"),
    ])
    def test_cpt_detection(self, detector, cpt, should_detect, description):
        text = cpt
        matches = detector.detect(text)
        cpt_matches = [m for m in matches if m.pii_type == PIIType.CPT_CODE]

        if should_detect:
            assert len(cpt_matches) >= 1, f"Should detect CPT ({description}): {cpt}"
        else:
            assert len(cpt_matches) == 0, f"Should NOT detect ({description}): {cpt}"


# ============================================================================
# HEALTH PLAN ID TESTS
# ============================================================================

class TestHealthPlanID:
    """Test Health Plan ID detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['healthcare'])

    @pytest.mark.parametrize("plan_id,should_detect,description", [
        # With prefix
        ("Member ID: XYZ123456789", True, "Member ID prefix"),
        ("Subscriber ID: ABC987654321", True, "Subscriber prefix"),
        ("Policy: POL12345678", True, "Policy prefix"),
        ("Insurance ID: INS00001234", True, "Insurance prefix"),
        ("Group #: GRP1234567", True, "Group prefix"),
        # Common insurance formats
        ("Member ID: BCBS12345678", True, "BCBS format"),
        ("Member ID: UHC123456789", True, "UHC format"),
        ("Member ID: AETNA12345678", True, "Aetna format"),
        ("Member ID: CIGNA12345678", True, "Cigna format"),
        # Without prefix
        ("XYZ123456789", False, "No prefix"),
    ])
    def test_health_plan_id_detection(self, detector, plan_id, should_detect, description):
        text = plan_id
        matches = detector.detect(text)
        plan_matches = [m for m in matches if m.pii_type == PIIType.HEALTH_PLAN_ID]

        if should_detect:
            assert len(plan_matches) >= 1, f"Should detect health plan ID ({description}): {plan_id}"
        else:
            assert len(plan_matches) == 0, f"Should NOT detect ({description}): {plan_id}"


# ============================================================================
# COMBINED HEALTHCARE TESTS
# ============================================================================

class TestHealthcareCombined:
    """Test combined Healthcare PII detection scenarios"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['healthcare'])

    def test_patient_record(self, detector):
        """Test patient record with multiple healthcare PII"""
        text = """
        PATIENT RECORD

        Patient ID: ABC12345
        MRN: 123456789
        DOB: 01/15/1985
        Member ID: BCBS12345678
        """

        matches = detector.detect(text)
        types_found = {m.pii_type for m in matches}

        assert len(matches) >= 2, f"Should find multiple healthcare PII, found: {types_found}"

    def test_prescription(self, detector):
        """Test prescription with DEA and NPI"""
        text = """
        PRESCRIPTION

        Provider NPI: 1234567893
        DEA: AB1234563
        Diagnosis: J06.9
        """

        matches = detector.detect(text)
        npi_matches = [m for m in matches if m.pii_type == PIIType.NPI]

        assert len(npi_matches) >= 1, "Should detect NPI"

    def test_claim_form(self, detector):
        """Test insurance claim form"""
        text = """
        INSURANCE CLAIM

        Member ID: BCBS12345678
        Patient ID: PAT00001234
        ICD-10: J18.9, M54.5
        CPT: 99213, 36415
        """

        matches = detector.detect(text)
        assert len(matches) >= 2, "Should detect multiple healthcare PII"

    def test_lab_order(self, detector):
        """Test lab order form"""
        text = """
        LABORATORY ORDER

        MRN: 123456789
        Ordering Provider NPI: 1234567893
        CPT: 80047, 85025
        ICD: E11.9
        """

        matches = detector.detect(text)
        mrn_matches = [m for m in matches if m.pii_type == PIIType.MRN]
        assert len(mrn_matches) >= 1, "Should detect MRN"


# ============================================================================
# HIPAA COMPLIANCE SCENARIOS
# ============================================================================

class TestHIPAAScenarios:
    """Test HIPAA compliance scenarios"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['healthcare'])

    def test_discharge_summary(self, detector):
        """Test discharge summary redaction"""
        text = """
        DISCHARGE SUMMARY

        Patient ID: ABC12345
        MRN: 123456789
        Attending NPI: 1234567893

        Diagnoses:
        - ICD: J18.9 (Pneumonia)
        - ICD: E11.9 (Type 2 Diabetes)

        Procedures:
        - CPT: 71046 (Chest X-ray)
        - CPT: 94760 (Pulse oximetry)

        Insurance: Member ID: BCBS12345678
        """

        matches = detector.detect(text)
        assert len(matches) >= 3, "Should detect multiple HIPAA identifiers"

        # Verify redaction
        redacted, _ = detector.redact(text)
        assert "ABC12345" not in redacted
        assert "123456789" not in redacted

    def test_referral_form(self, detector):
        """Test referral form"""
        text = """
        REFERRAL REQUEST

        Referring Provider: Dr. Smith
        NPI: 1234567893
        DEA: AB1234563

        Patient: Jane Doe
        Patient ID: PAT00005678
        MRN: 987654321

        Reason: ICD: M54.5 (Low back pain)
        """

        matches = detector.detect(text)
        types_found = {m.pii_type for m in matches}

        # Should find NPI, Patient ID, MRN
        assert len(matches) >= 2, f"Found: {types_found}"

    def test_ehr_export(self, detector):
        """Test EHR data export"""
        text = """
        EHR EXPORT - CONFIDENTIAL

        Patient Demographics:
        - Patient ID: ABC12345
        - MRN: 123456789
        - Member ID: UHC123456789

        Provider Information:
        - NPI: 1234567893
        - DEA: AB1234563

        Clinical Data:
        - ICD: E11.9, I10, Z79.84
        - CPT: 99214, 36415
        """

        matches = detector.detect(text)

        # Count by type
        type_counts = {}
        for m in matches:
            type_counts[m.pii_type] = type_counts.get(m.pii_type, 0) + 1

        assert len(matches) >= 4, f"Should find many PHI elements, found: {type_counts}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
