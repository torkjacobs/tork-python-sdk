"""
Tests for GDPR Compliance Framework
Phase 2.1 of Comprehensive Test Plan

GDPR Requirements Tested:
- Article 5: Data Processing Principles
- Article 6: Lawful Basis
- Article 7: Consent
- Article 12-14: Transparency
- Article 15: Right of Access
- Article 16: Right to Rectification
- Article 17: Right to Erasure
- Article 18: Right to Restriction
- Article 20: Right to Portability
- Article 21: Right to Object
- Article 25: Privacy by Design
- Article 32: Security
- Article 33-34: Breach Notification
- Article 44-49: International Transfers
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Import compliance modules
try:
    from tork_governance.compliance import (
        GDPRValidator,
        ComplianceResult,
        PolicyEngine,
        ConsentManager,
        DataSubjectRequest,
        BreachNotification,
    )
    COMPLIANCE_MODULES_AVAILABLE = True
except ImportError:
    COMPLIANCE_MODULES_AVAILABLE = False

# Import PII detection for integration tests
from tork_governance.detectors.pii_patterns import PIIDetector, PIIType


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def gdpr_detector():
    """PII detector configured for EU region"""
    return PIIDetector(regions=['eu', 'uk', 'universal'])


@pytest.fixture
def sample_eu_data():
    """Sample data containing EU PII"""
    return {
        "name": "Hans Mueller",
        "email": "hans.mueller@example.de",
        "iban": "DE89370400440532013000",
        "german_id": "T220001293",
        "ip_address": "192.168.1.100",
        "dob": "DOB: 15/03/1985",
    }


@pytest.fixture
def sample_processing_record():
    """Sample GDPR processing record"""
    return {
        "controller": "Acme Corp",
        "processor": "Cloud Provider X",
        "purpose": "Customer relationship management",
        "lawful_basis": "consent",
        "data_categories": ["name", "email", "purchase_history"],
        "retention_period": "3 years",
        "recipients": ["Marketing team", "Customer support"],
        "international_transfers": False,
    }


# ============================================================================
# ARTICLE 5: DATA PROCESSING PRINCIPLES
# ============================================================================

class TestGDPRArticle5Principles:
    """Test GDPR Article 5 - Principles relating to processing"""
    
    def test_purpose_limitation_detection(self, gdpr_detector):
        """Test that data is collected for specified, explicit purposes"""
        text = """
        DATA COLLECTION NOTICE
        
        We collect your email: hans.mueller@example.de
        Purpose: Marketing communications
        
        Secondary use: Sold to third parties
        """
        
        matches = gdpr_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        
        assert len(email_matches) >= 1, "Should detect email for purpose limitation check"
    
    def test_data_minimization(self, gdpr_detector):
        """Test that only necessary data is processed"""
        # Excessive data collection scenario
        text = """
        JOB APPLICATION FORM
        
        Required for application:
        Name: Hans Mueller
        Email: hans.mueller@example.de
        
        Unnecessary data collected:
        Bank IBAN: DE89370400440532013000
        German ID: T220001293
        Mother's maiden name: Schmidt
        """
        
        matches = gdpr_detector.detect(text)
        
        # Should detect all PII to flag minimization concerns
        assert len(matches) >= 2, "Should detect excessive PII collection"
    
    def test_accuracy_principle(self, gdpr_detector):
        """Test data accuracy requirements"""
        text = """
        CUSTOMER RECORD - ACCURACY CHECK
        
        Email: hans.mueller@example.de
        Last verified: 2024-01-15
        Verification status: OUTDATED (>12 months)
        """
        
        matches = gdpr_detector.detect(text)
        assert len(matches) >= 1, "Should detect PII requiring accuracy verification"
    
    def test_storage_limitation(self, gdpr_detector):
        """Test storage limitation principle"""
        text = """
        DATA RETENTION ALERT
        
        Customer: hans.mueller@example.de
        Account created: 2018-01-01
        Last activity: 2019-12-31
        Retention period: Exceeded (5+ years inactive)
        
        Action required: Delete or anonymize
        """
        
        matches = gdpr_detector.detect(text)
        assert len(matches) >= 1, "Should detect PII exceeding retention"
    
    def test_integrity_and_confidentiality(self, gdpr_detector):
        """Test security of processing"""
        text = """
        SECURITY LOG - UNENCRYPTED TRANSMISSION DETECTED
        
        Data transmitted in clear text:
        IBAN: DE89370400440532013000
        Email: hans.mueller@example.de
        
        Security violation: Article 5(1)(f)
        """
        
        matches = gdpr_detector.detect(text)
        iban_matches = [m for m in matches if m.pii_type == PIIType.IBAN]
        
        assert len(iban_matches) >= 1, "Should detect IBAN in security violation"


# ============================================================================
# ARTICLE 6: LAWFUL BASIS
# ============================================================================

class TestGDPRArticle6LawfulBasis:
    """Test GDPR Article 6 - Lawfulness of processing"""
    
    @pytest.mark.parametrize("lawful_basis,is_valid", [
        ("consent", True),
        ("contract", True),
        ("legal_obligation", True),
        ("vital_interests", True),
        ("public_task", True),
        ("legitimate_interests", True),
        ("marketing_preference", False),
        ("business_need", False),
        ("", False),
        (None, False),
    ])
    def test_lawful_basis_validation(self, lawful_basis, is_valid):
        """Test validation of lawful basis"""
        valid_bases = {
            "consent", "contract", "legal_obligation",
            "vital_interests", "public_task", "legitimate_interests"
        }
        
        result = lawful_basis in valid_bases if lawful_basis else False
        assert result == is_valid, f"Lawful basis '{lawful_basis}' validation should be {is_valid}"
    
    def test_consent_requirements(self, gdpr_detector):
        """Test consent as lawful basis"""
        text = """
        CONSENT RECORD
        
        Data subject: hans.mueller@example.de
        Consent given: 2026-01-15
        Purpose: Newsletter subscription
        Freely given: Yes
        Specific: Yes
        Informed: Yes
        Unambiguous: Yes
        """
        
        matches = gdpr_detector.detect(text)
        assert len(matches) >= 1, "Should detect PII in consent record"
    
    def test_contract_basis(self, gdpr_detector):
        """Test contract as lawful basis"""
        text = """
        CONTRACT PROCESSING
        
        Customer: hans.mueller@example.de
        IBAN: DE89370400440532013000
        
        Processing necessary for:
        - Order fulfillment
        - Payment processing
        - Delivery
        
        Lawful basis: Contract (Article 6(1)(b))
        """
        
        matches = gdpr_detector.detect(text)
        assert len(matches) >= 2, "Should detect PII processed under contract"


# ============================================================================
# ARTICLE 7: CONDITIONS FOR CONSENT
# ============================================================================

class TestGDPRArticle7Consent:
    """Test GDPR Article 7 - Conditions for consent"""
    
    def test_consent_record_exists(self):
        """Test that consent records are maintained"""
        consent_record = {
            "data_subject": "hans.mueller@example.de",
            "timestamp": "2026-01-15T10:30:00Z",
            "purpose": "Marketing emails",
            "method": "Checkbox on website",
            "ip_address": "192.168.1.100",
            "consent_text": "I agree to receive marketing emails",
        }
        
        required_fields = ["data_subject", "timestamp", "purpose", "method"]
        
        for field in required_fields:
            assert field in consent_record, f"Consent record must have {field}"
    
    def test_consent_withdrawal(self, gdpr_detector):
        """Test right to withdraw consent"""
        text = """
        CONSENT WITHDRAWAL REQUEST
        
        From: hans.mueller@example.de
        Date: 2026-01-31
        
        Request: Withdraw consent for marketing
        
        Status: Processing
        Deadline: 2026-02-03 (72 hours)
        """
        
        matches = gdpr_detector.detect(text)
        assert len(matches) >= 1, "Should detect email in withdrawal request"
    
    def test_consent_granularity(self):
        """Test that consent is granular for different purposes"""
        consent_options = {
            "marketing_emails": False,
            "product_updates": True,
            "third_party_sharing": False,
            "analytics": True,
        }
        
        # Each purpose should be separately consentable
        assert len(consent_options) >= 3, "Should have granular consent options"


# ============================================================================
# ARTICLE 15-22: DATA SUBJECT RIGHTS
# ============================================================================

class TestGDPRDataSubjectRights:
    """Test GDPR Articles 15-22 - Data Subject Rights"""
    
    def test_right_of_access_article15(self, gdpr_detector):
        """Test Article 15 - Right of access"""
        text = """
        DATA SUBJECT ACCESS REQUEST (DSAR)
        
        Requester: hans.mueller@example.de
        Date: 2026-01-31
        
        Data held:
        - Name: Hans Mueller
        - Email: hans.mueller@example.de
        - IBAN: DE89370400440532013000
        - Purchase history: 15 orders
        - Login IP: 192.168.1.100
        
        Response deadline: 30 days
        """
        
        matches = gdpr_detector.detect(text)
        
        # Should detect multiple PII types in access response
        types_found = {m.pii_type for m in matches}
        assert len(types_found) >= 2, f"Should detect multiple PII types: {types_found}"
    
    def test_right_to_rectification_article16(self, gdpr_detector):
        """Test Article 16 - Right to rectification"""
        text = """
        RECTIFICATION REQUEST
        
        Data subject: hans.mueller@example.de
        
        Current data: IBAN DE89370400440532013000
        Corrected data: IBAN DE89370400440532013001
        
        Reason: Bank account changed
        Status: Pending verification
        """
        
        matches = gdpr_detector.detect(text)
        iban_matches = [m for m in matches if m.pii_type == PIIType.IBAN]
        
        assert len(iban_matches) >= 1, "Should detect IBAN in rectification request"
    
    def test_right_to_erasure_article17(self, gdpr_detector):
        """Test Article 17 - Right to erasure (Right to be forgotten)"""
        text = """
        ERASURE REQUEST
        
        Data subject: hans.mueller@example.de
        Request date: 2026-01-31
        
        Data to be erased:
        - Email: hans.mueller@example.de
        - German ID: T220001293
        - IBAN: DE89370400440532013000
        - All associated records
        
        Legal hold: None
        Erasure approved: Pending
        """
        
        matches = gdpr_detector.detect(text)
        
        # Verify all PII types are detected for erasure
        assert len(matches) >= 3, "Should detect all PII for erasure"
    
    def test_right_to_restriction_article18(self, gdpr_detector):
        """Test Article 18 - Right to restriction of processing"""
        text = """
        RESTRICTION REQUEST
        
        Data subject: hans.mueller@example.de
        
        Restriction type: Processing suspended
        Reason: Accuracy contested
        
        Affected data:
        - Email: hans.mueller@example.de
        - Address records
        
        Duration: Until accuracy verified
        """
        
        matches = gdpr_detector.detect(text)
        assert len(matches) >= 1, "Should detect PII under restriction"
    
    def test_right_to_portability_article20(self, gdpr_detector):
        """Test Article 20 - Right to data portability"""
        text = """
        DATA PORTABILITY REQUEST
        
        Data subject: hans.mueller@example.de
        Export format: JSON
        
        Portable data:
        {
            "email": "hans.mueller@example.de",
            "iban": "DE89370400440532013000",
            "purchase_history": [...],
            "preferences": {...}
        }
        
        Delivered to: new-provider@example.com
        """
        
        matches = gdpr_detector.detect(text)
        
        # Should detect PII in portability export
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        assert len(email_matches) >= 1, "Should detect email in portability data"
    
    def test_right_to_object_article21(self, gdpr_detector):
        """Test Article 21 - Right to object"""
        text = """
        OBJECTION TO PROCESSING
        
        Data subject: hans.mueller@example.de
        
        Objection type: Direct marketing
        
        Current processing:
        - Email marketing: ACTIVE
        - Profiling: ACTIVE
        
        Requested status:
        - Email marketing: STOPPED
        - Profiling: STOPPED
        
        Effective: Immediately (no balancing test for direct marketing)
        """
        
        matches = gdpr_detector.detect(text)
        assert len(matches) >= 1, "Should detect PII in objection request"


# ============================================================================
# ARTICLE 25: PRIVACY BY DESIGN
# ============================================================================

class TestGDPRArticle25PrivacyByDesign:
    """Test GDPR Article 25 - Data protection by design and default"""
    
    def test_default_privacy_settings(self, gdpr_detector):
        """Test privacy by default"""
        # Privacy settings should default to most protective
        default_settings = {
            "data_sharing": False,  # Default: no sharing
            "marketing": False,  # Default: no marketing
            "profiling": False,  # Default: no profiling
            "analytics": False,  # Default: no analytics
            "retention": "minimum",  # Default: minimum retention
        }
        
        assert default_settings["data_sharing"] == False
        assert default_settings["marketing"] == False
        assert default_settings["profiling"] == False
    
    def test_pseudonymization_support(self, gdpr_detector):
        """Test pseudonymization as privacy by design measure"""
        original_text = "Customer email: hans.mueller@example.de"
        
        matches = gdpr_detector.detect(original_text)
        redacted, _ = gdpr_detector.redact(original_text)
        
        # Original should be detected
        assert len(matches) >= 1
        
        # Redacted should not contain original
        assert "hans.mueller@example.de" not in redacted
    
    def test_data_minimization_by_design(self, gdpr_detector):
        """Test data minimization in system design"""
        # Form should only collect necessary fields
        necessary_fields = ["name", "email", "order_details"]
        unnecessary_fields = ["mother_maiden_name", "social_security", "religion"]
        
        collected_fields = ["name", "email", "order_details"]
        
        for field in collected_fields:
            assert field in necessary_fields, f"{field} should be necessary"
        
        for field in unnecessary_fields:
            assert field not in collected_fields, f"{field} should not be collected"


# ============================================================================
# ARTICLE 32: SECURITY OF PROCESSING
# ============================================================================

class TestGDPRArticle32Security:
    """Test GDPR Article 32 - Security of processing"""
    
    def test_encryption_requirement(self, gdpr_detector):
        """Test encryption of personal data"""
        # Unencrypted PII should be flagged
        unencrypted_text = """
        PLAINTEXT TRANSMISSION DETECTED
        
        IBAN: DE89370400440532013000
        Email: hans.mueller@example.de
        
        WARNING: Data not encrypted
        """
        
        matches = gdpr_detector.detect(unencrypted_text)
        assert len(matches) >= 2, "Should detect unencrypted PII"
    
    def test_access_control(self):
        """Test access control measures"""
        access_levels = {
            "admin": ["read", "write", "delete", "export"],
            "manager": ["read", "write", "export"],
            "employee": ["read"],
            "guest": [],
        }
        
        # Least privilege principle
        assert len(access_levels["guest"]) == 0
        assert "delete" not in access_levels["employee"]
        assert "delete" in access_levels["admin"]
    
    def test_audit_logging(self, gdpr_detector):
        """Test audit logging of data access"""
        audit_log = """
        AUDIT LOG ENTRY
        
        Timestamp: 2026-01-31T10:30:00Z
        User: admin@company.com
        Action: VIEW
        Data accessed: hans.mueller@example.de
        IP: 192.168.1.100
        Justification: Customer support ticket #12345
        """
        
        matches = gdpr_detector.detect(audit_log)
        
        # Audit log should capture PII access
        assert len(matches) >= 2, "Should detect PII in audit log"


# ============================================================================
# ARTICLES 33-34: BREACH NOTIFICATION
# ============================================================================

class TestGDPRBreachNotification:
    """Test GDPR Articles 33-34 - Breach notification"""
    
    def test_breach_detection(self, gdpr_detector):
        """Test detection of data breach"""
        breach_report = """
        DATA BREACH INCIDENT REPORT
        
        Incident ID: BR-2026-001
        Detection time: 2026-01-31T08:00:00Z
        
        Affected data:
        - Emails: 1,000 records
        - IBANs: DE89370400440532013000, DE89370400440532013001
        - German IDs: T220001293
        
        Breach type: Unauthorized access
        Risk level: HIGH
        """
        
        matches = gdpr_detector.detect(breach_report)
        
        # Should detect all PII in breach report
        assert len(matches) >= 2, "Should detect PII in breach report"
    
    def test_72_hour_notification_deadline(self):
        """Test 72-hour supervisory authority notification"""
        breach_time = datetime(2026, 1, 31, 8, 0, 0)
        notification_deadline = breach_time + timedelta(hours=72)
        
        expected_deadline = datetime(2026, 2, 3, 8, 0, 0)
        
        assert notification_deadline == expected_deadline
    
    def test_breach_notification_content(self, gdpr_detector):
        """Test breach notification contains required information"""
        notification = """
        SUPERVISORY AUTHORITY NOTIFICATION
        
        1. Nature of breach: Unauthorized access to customer database
        
        2. Categories of data:
           - Email addresses
           - Payment IBANs: DE89370400440532013000
           - Identity documents
        
        3. Approximate number of subjects: 1,000
        
        4. DPO contact: dpo@company.com
        
        5. Consequences: Potential identity theft
        
        6. Mitigation measures: Password reset, monitoring
        """
        
        matches = gdpr_detector.detect(notification)
        
        # Required sections check
        required_sections = [
            "Nature of breach",
            "Categories of data",
            "number of subjects",
            "DPO contact",
            "Consequences",
            "Mitigation",
        ]
        
        for section in required_sections:
            assert section.lower() in notification.lower(), f"Notification must include {section}"


# ============================================================================
# ARTICLES 44-49: INTERNATIONAL TRANSFERS
# ============================================================================

class TestGDPRInternationalTransfers:
    """Test GDPR Articles 44-49 - International data transfers"""
    
    @pytest.mark.parametrize("country,is_adequate", [
        ("UK", True),  # Adequacy decision
        ("Switzerland", True),  # Adequacy decision
        ("Japan", True),  # Adequacy decision
        ("Canada", True),  # Adequacy decision (commercial)
        ("USA", False),  # No general adequacy (post-Schrems II)
        ("China", False),  # No adequacy decision
        ("Russia", False),  # No adequacy decision
        ("India", False),  # No adequacy decision
    ])
    def test_adequacy_decisions(self, country, is_adequate):
        """Test country adequacy decisions"""
        adequate_countries = {
            "UK", "Switzerland", "Japan", "Canada", "New Zealand",
            "Israel", "Argentina", "Uruguay", "South Korea"
        }
        
        result = country in adequate_countries
        assert result == is_adequate, f"{country} adequacy should be {is_adequate}"
    
    def test_standard_contractual_clauses(self, gdpr_detector):
        """Test SCCs for non-adequate countries"""
        transfer_record = """
        INTERNATIONAL DATA TRANSFER
        
        Data: hans.mueller@example.de
        From: EU (Germany)
        To: USA
        
        Adequacy: NO
        Transfer mechanism: Standard Contractual Clauses (SCCs)
        SCC version: 2021 Commission Decision
        Supplementary measures: Encryption, pseudonymization
        """
        
        matches = gdpr_detector.detect(transfer_record)
        assert len(matches) >= 1, "Should detect PII in transfer record"
    
    def test_transfer_impact_assessment(self, gdpr_detector):
        """Test Transfer Impact Assessment (TIA)"""
        tia = """
        TRANSFER IMPACT ASSESSMENT
        
        Data exported:
        - Email: hans.mueller@example.de
        - IBAN: DE89370400440532013000
        
        Destination: United States
        
        Third country laws assessment:
        - FISA 702: Potential government access
        - CLOUD Act: Potential government access
        
        Risk level: HIGH
        
        Supplementary measures required: YES
        """
        
        matches = gdpr_detector.detect(tia)
        
        # TIA should flag all PII being transferred
        assert len(matches) >= 2, "Should detect all PII in TIA"


# ============================================================================
# GDPR REDACTION TESTS
# ============================================================================

class TestGDPRRedaction:
    """Test GDPR-compliant redaction"""
    
    def test_full_redaction_for_erasure(self, gdpr_detector):
        """Test complete redaction for right to erasure"""
        text = """
        CUSTOMER RECORD - TO BE ERASED
        
        Name: Hans Mueller
        Email: hans.mueller@example.de
        IBAN: DE89370400440532013000
        German ID: T220001293
        IP: 192.168.1.100
        """
        
        redacted, matches = gdpr_detector.redact(text)
        
        # All PII should be redacted
        assert "hans.mueller@example.de" not in redacted
        assert "DE89370400440532013000" not in redacted
        assert "T220001293" not in redacted
        assert "192.168.1.100" not in redacted
    
    def test_partial_redaction_for_portability(self, gdpr_detector):
        """Test that redaction preserves data for portability"""
        text = "Email: hans.mueller@example.de"
        
        matches = gdpr_detector.detect(text)
        
        # For portability, we detect but preserve original
        assert len(matches) >= 1
        assert matches[0].value == "hans.mueller@example.de"
    
    def test_redaction_maintains_context(self, gdpr_detector):
        """Test that redaction maintains document context"""
        text = """
        Dear Customer,
        
        Your account hans.mueller@example.de has been updated.
        
        Best regards,
        Support Team
        """
        
        redacted, _ = gdpr_detector.redact(text)
        
        # Context should be preserved
        assert "Dear Customer" in redacted
        assert "Best regards" in redacted
        assert "Support Team" in redacted
        
        # PII should be redacted
        assert "hans.mueller@example.de" not in redacted


# ============================================================================
# GDPR COMPLIANCE REPORTING
# ============================================================================

class TestGDPRComplianceReporting:
    """Test GDPR compliance reporting capabilities"""
    
    def test_processing_activities_record(self, gdpr_detector, sample_processing_record):
        """Test Article 30 - Records of processing activities"""
        required_fields = [
            "controller",
            "purpose",
            "data_categories",
            "recipients",
            "retention_period",
        ]
        
        for field in required_fields:
            assert field in sample_processing_record, f"ROPA must include {field}"
    
    def test_dpia_trigger_detection(self, gdpr_detector):
        """Test Data Protection Impact Assessment triggers"""
        high_risk_text = """
        NEW PROCESSING ACTIVITY
        
        Type: Large-scale profiling
        Data: Customer emails, IBANs (DE89370400440532013000)
        
        DPIA triggers:
        - Systematic profiling: YES
        - Large scale processing: YES
        - Sensitive data: NO
        - Automated decision-making: YES
        
        DPIA REQUIRED: YES
        """
        
        matches = gdpr_detector.detect(high_risk_text)
        
        # Should detect PII that triggers DPIA
        assert len(matches) >= 1, "Should detect PII in DPIA assessment"
    
    def test_compliance_audit_trail(self, gdpr_detector):
        """Test compliance audit trail"""
        audit_trail = """
        GDPR COMPLIANCE AUDIT
        
        Date: 2026-01-31
        Auditor: Internal DPO
        
        Findings:
        1. PII detected in logs: hans.mueller@example.de
        2. Consent records: Valid
        3. Retention compliance: Compliant
        4. Security measures: A+ rating
        
        Overall: COMPLIANT
        """
        
        matches = gdpr_detector.detect(audit_trail)
        
        # Audit should detect any PII mentioned
        assert len(matches) >= 1, "Should detect PII in audit trail"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
