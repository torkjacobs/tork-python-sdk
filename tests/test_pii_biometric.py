"""
Tests for Biometric PII Detection
Part 1.7 of Comprehensive Test Plan (FINAL)
Covers: Biometric ID, Face ID, Fingerprint ID
"""

import pytest
from tork_governance.detectors.pii_patterns import (
    PIIDetector, PIIType, detect_pii, redact_pii
)


# ============================================================================
# BIOMETRIC ID TESTS
# ============================================================================

class TestBiometricID:
    """Test generic Biometric ID detection"""
    
    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['biometric'])
    
    @pytest.mark.parametrize("bio_id,should_detect,description", [
        # With prefix
        ("Biometric ID: BIO123456789", True, "Biometric ID prefix"),
        ("Biometric: BIO-2024-001234", True, "Biometric prefix"),
        ("Bio ID: BIOID00001234", True, "Bio ID prefix"),
        ("Biometric Identifier: B1234567890", True, "Full phrase"),
        ("Biometric Data ID: BD-2026-00001", True, "Data ID format"),
        # Different formats
        ("Biometric ID: 123456789012", True, "Numeric only"),
        ("Biometric ID: ABC-123-DEF-456", True, "Alphanumeric dashed"),
        # Without prefix
        ("BIO123456789", False, "No prefix"),
        ("123456789012", False, "Numeric no prefix"),
    ])
    def test_biometric_id_detection(self, detector, bio_id, should_detect, description):
        text = bio_id
        matches = detector.detect(text)
        bio_matches = [m for m in matches if m.pii_type == PIIType.BIOMETRIC_ID]
        
        if should_detect:
            assert len(bio_matches) >= 1, f"Should detect biometric ID ({description}): {bio_id}"
        else:
            assert len(bio_matches) == 0, f"Should NOT detect ({description}): {bio_id}"
    
    def test_biometric_id_redaction(self, detector):
        """Test biometric ID redaction"""
        text = "Subject Biometric ID: BIO123456789"
        redacted, matches = detector.redact(text)
        
        assert "BIO123456789" not in redacted
        assert "[BIOMETRIC_REDACTED]" in redacted


# ============================================================================
# FACE ID TESTS
# ============================================================================

class TestFaceID:
    """Test Face ID / Facial Recognition ID detection"""
    
    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['biometric'])
    
    @pytest.mark.parametrize("face_id,should_detect,description", [
        # With prefix
        ("Face ID: FACE123456789", True, "Face ID prefix"),
        ("Facial ID: FAC-2024-001234", True, "Facial ID prefix"),
        ("Face Recognition ID: FR00001234", True, "Face Recognition prefix"),
        ("FaceID: FID-2026-ABCD1234", True, "FaceID prefix"),
        ("Facial Recognition: FACEREC123456", True, "Facial Recognition"),
        # Different formats
        ("Face ID: 123456789012", True, "Numeric"),
        ("Face ID: ABC-123-456-DEF", True, "Alphanumeric dashed"),
        ("Face Template ID: FT-001-2026", True, "Template ID"),
        # Without prefix
        ("FACE123456789", False, "No prefix"),
        ("FR00001234", False, "No prefix FR"),
    ])
    def test_face_id_detection(self, detector, face_id, should_detect, description):
        text = face_id
        matches = detector.detect(text)
        face_matches = [m for m in matches if m.pii_type == PIIType.FACE_ID]
        
        if should_detect:
            assert len(face_matches) >= 1, f"Should detect face ID ({description}): {face_id}"
        else:
            assert len(face_matches) == 0, f"Should NOT detect ({description}): {face_id}"
    
    def test_face_id_redaction(self, detector):
        """Test face ID redaction"""
        text = "Subject Face ID: FACE123456789"
        redacted, matches = detector.redact(text)
        
        assert "FACE123456789" not in redacted


# ============================================================================
# FINGERPRINT ID TESTS
# ============================================================================

class TestFingerprintID:
    """Test Fingerprint ID detection"""
    
    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['biometric'])
    
    @pytest.mark.parametrize("fp_id,should_detect,description", [
        # With prefix
        ("Fingerprint ID: FP123456789", True, "Fingerprint ID prefix"),
        ("Fingerprint: FPRINT-2024-001", True, "Fingerprint prefix"),
        ("FP ID: FPID00001234", True, "FP ID prefix"),
        ("Fingerprint Record: FPR-2026-ABCD", True, "Fingerprint Record"),
        ("Print ID: PRINT123456789", True, "Print ID prefix"),
        # Different formats
        ("Fingerprint ID: 123456789012", True, "Numeric"),
        ("Fingerprint ID: ABC-123-456-DEF", True, "Alphanumeric dashed"),
        ("Fingerprint Template: FPT-001-2026", True, "Template format"),
        # Without prefix
        ("FP123456789", False, "No prefix"),
        ("FPRINT-2024-001", False, "No prefix FPRINT"),
    ])
    def test_fingerprint_id_detection(self, detector, fp_id, should_detect, description):
        text = fp_id
        matches = detector.detect(text)
        fp_matches = [m for m in matches if m.pii_type == PIIType.FINGERPRINT_ID]
        
        if should_detect:
            assert len(fp_matches) >= 1, f"Should detect fingerprint ID ({description}): {fp_id}"
        else:
            assert len(fp_matches) == 0, f"Should NOT detect ({description}): {fp_id}"
    
    def test_fingerprint_id_redaction(self, detector):
        """Test fingerprint ID redaction"""
        text = "Subject Fingerprint ID: FP123456789"
        redacted, matches = detector.redact(text)
        
        assert "FP123456789" not in redacted


# ============================================================================
# COMBINED BIOMETRIC TESTS
# ============================================================================

class TestBiometricCombined:
    """Test combined Biometric PII detection scenarios"""
    
    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['biometric'])
    
    def test_biometric_enrollment(self, detector):
        """Test biometric enrollment form"""
        text = """
        BIOMETRIC ENROLLMENT FORM
        
        Subject: John Doe
        Biometric ID: BIO123456789
        Face ID: FACE987654321
        Fingerprint ID: FP-2026-00001
        """
        
        matches = detector.detect(text)
        types_found = {m.pii_type for m in matches}
        
        assert len(matches) >= 2, f"Should find multiple biometric IDs, found: {types_found}"
    
    def test_access_control_record(self, detector):
        """Test access control record"""
        text = """
        ACCESS CONTROL LOG
        
        Entry Time: 2026-01-31 10:30:00
        Biometric ID: BIO123456789
        Face Recognition ID: FR-2026-ABCD
        Status: GRANTED
        """
        
        matches = detector.detect(text)
        assert len(matches) >= 1, "Should detect biometric data in access log"
    
    def test_identity_verification(self, detector):
        """Test identity verification document"""
        text = """
        IDENTITY VERIFICATION
        
        Method: Multi-factor Biometric
        
        Biometric ID: BIO-2026-001234
        Face ID: FACE-2026-001234
        Fingerprint ID: FP-2026-001234
        
        Verification Status: CONFIRMED
        """
        
        matches = detector.detect(text)
        assert len(matches) >= 2, "Should detect multiple biometric identifiers"


# ============================================================================
# GDPR/PRIVACY COMPLIANCE SCENARIOS
# ============================================================================

class TestBiometricPrivacy:
    """Test biometric privacy compliance scenarios"""
    
    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['biometric'])
    
    def test_gdpr_biometric_data(self, detector):
        """Test GDPR Article 9 special category data"""
        text = """
        GDPR DATA SUBJECT REQUEST
        
        Category: Biometric Data (Article 9)
        
        Biometric ID: BIO123456789
        Facial Recognition Data ID: FACE-EU-2026-001
        Fingerprint Data ID: FP-EU-2026-001
        
        Processing Basis: Explicit Consent
        """
        
        matches = detector.detect(text)
        assert len(matches) >= 2, "Should detect biometric data under GDPR"
        
        # Verify full redaction
        redacted, _ = detector.redact(text)
        assert "BIO123456789" not in redacted
    
    def test_ccpa_biometric_data(self, detector):
        """Test CCPA biometric information"""
        text = """
        CCPA CONSUMER REQUEST
        
        Category: Biometric Information
        
        Biometric ID: BIO-CA-2026-001234
        Face ID: FACEID-CA-001234
        
        Consumer Rights: Right to Delete
        """
        
        matches = detector.detect(text)
        assert len(matches) >= 1, "Should detect biometric data under CCPA"
    
    def test_bipa_compliance(self, detector):
        """Test Illinois BIPA compliance"""
        text = """
        BIPA CONSENT FORM
        
        Biometric Identifier Type: Fingerprint
        Fingerprint ID: FP-IL-2026-001234
        
        Biometric Identifier Type: Face Geometry
        Face ID: FACE-IL-2026-001234
        
        Purpose: Employee Time Tracking
        Retention: 3 years
        """
        
        matches = detector.detect(text)
        assert len(matches) >= 1, "Should detect biometric data under BIPA"


# ============================================================================
# REAL WORLD SCENARIOS
# ============================================================================

class TestBiometricRealWorld:
    """Test real-world biometric scenarios"""
    
    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['biometric'])
    
    def test_employee_badge_system(self, detector):
        """Test employee badge biometric system"""
        text = """
        EMPLOYEE BADGE ENROLLMENT
        
        Employee ID: EMP001234
        Biometric ID: BIO-EMP-001234
        Fingerprint ID: FP-EMP-001234
        Face ID: FACE-EMP-001234
        
        Enrolled: 2026-01-31
        """
        
        matches = detector.detect(text)
        bio_matches = [m for m in matches if 'BIOMETRIC' in str(m.pii_type) or 'FACE' in str(m.pii_type) or 'FINGER' in str(m.pii_type)]
        assert len(bio_matches) >= 2, "Should detect biometric employee data"
    
    def test_border_control(self, detector):
        """Test border control biometric data"""
        text = """
        BORDER CONTROL RECORD
        
        Traveler: Jane Smith
        Passport: ABC123456
        
        Biometric Verification:
        Face ID: FACE-BORDER-2026-001
        Fingerprint ID: FP-BORDER-2026-001
        
        Entry Granted: Yes
        """
        
        matches = detector.detect(text)
        assert len(matches) >= 1, "Should detect border control biometric data"
    
    def test_healthcare_biometric(self, detector):
        """Test healthcare biometric identification"""
        text = """
        PATIENT BIOMETRIC IDENTIFICATION
        
        Patient ID: PAT001234
        
        Biometric Enrollment:
        Biometric ID: BIO-HC-001234
        Face ID: FACE-HC-001234
        
        Purpose: Positive Patient Identification
        """
        
        matches = detector.detect(text)
        assert len(matches) >= 1, "Should detect healthcare biometric data"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
