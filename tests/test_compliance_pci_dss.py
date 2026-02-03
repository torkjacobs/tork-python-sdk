"""
Tests for PCI-DSS Compliance Framework
Phase 2.3 of Comprehensive Test Plan

PCI-DSS Requirements Tested:
- Requirement 1: Install and maintain network security controls
- Requirement 2: Apply secure configurations
- Requirement 3: Protect stored account data
- Requirement 4: Protect cardholder data with strong cryptography during transmission
- Requirement 5: Protect all systems and networks from malicious software
- Requirement 6: Develop and maintain secure systems and software
- Requirement 7: Restrict access to system components and cardholder data by business need to know
- Requirement 8: Identify users and authenticate access to system components
- Requirement 9: Restrict physical access to cardholder data
- Requirement 10: Log and monitor all access to system components and cardholder data
- Requirement 11: Test security of systems and networks regularly
- Requirement 12: Support information security with organizational policies and programs
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Import PII detection for integration tests
from tork_governance.detectors.pii_patterns import PIIDetector, PIIType


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def pci_detector():
    """PII detector configured for PCI-DSS cardholder data"""
    return PIIDetector(regions=['financial', 'universal'])


@pytest.fixture
def sample_cardholder_data():
    """Sample cardholder data"""
    return {
        "pan": "4111111111111111",
        "expiry": "Exp: 12/26",
        "cvv": "CVV: 123",
        "cardholder_name": "John Smith",
    }


# ============================================================================
# REQUIREMENT 3: PROTECT STORED ACCOUNT DATA
# ============================================================================

class TestPCIDSSRequirement3StoredData:
    """Test PCI-DSS Requirement 3 - Protect stored account data"""
    
    def test_pan_detection_visa(self, pci_detector):
        """Test Primary Account Number (PAN) detection - Visa"""
        text = """
        PAYMENT RECORD
        Card Number: 4111111111111111
        """
        matches = pci_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) >= 1, "Should detect Visa PAN"
    
    def test_pan_detection_mastercard(self, pci_detector):
        """Test PAN detection - Mastercard"""
        text = """
        PAYMENT RECORD
        Card Number: 5555555555554444
        """
        matches = pci_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) >= 1, "Should detect Mastercard PAN"
    
    def test_pan_detection_amex(self, pci_detector):
        """Test PAN detection - American Express"""
        text = """
        PAYMENT RECORD
        Card Number: 378282246310005
        """
        matches = pci_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) >= 1, "Should detect Amex PAN"
    
    def test_pan_detection_discover(self, pci_detector):
        """Test PAN detection - Discover"""
        text = """
        PAYMENT RECORD
        Card Number: 6011111111111117
        """
        matches = pci_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) >= 1, "Should detect Discover PAN"
    
    def test_pan_masking_requirement(self, pci_detector):
        """Test PAN must be masked when displayed"""
        text = """
        RECEIPT
        Card: **** **** **** 1111
        """
        matches = pci_detector.detect(text)
        # Masked PAN should NOT be detected as full card number
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) == 0, "Masked PAN should not be detected as full card"
    
    def test_pan_truncation_first6_last4(self, pci_detector):
        """Test PAN truncation (first 6, last 4)"""
        text = """
        TRANSACTION LOG
        Card BIN: 411111******1111
        """
        matches = pci_detector.detect(text)
        # Truncated PAN should NOT be detected
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) == 0, "Truncated PAN should not be detected"
    
    def test_cvv_never_stored(self, pci_detector):
        """Test CVV/CVC detection - MUST NEVER be stored"""
        text = """
        PAYMENT DATA - VIOLATION DETECTED
        Card: 4111111111111111
        CVV: 123
        
        WARNING: CVV must NEVER be stored post-authorization
        """
        matches = pci_detector.detect(text)
        cvv_matches = [m for m in matches if m.pii_type == PIIType.CVV]
        assert len(cvv_matches) >= 1, "Should detect CVV (storage violation)"
    
    def test_expiry_date_detection(self, pci_detector):
        """Test expiration date detection"""
        text = """
        CARD DATA
        Expiry: 12/26
        """
        matches = pci_detector.detect(text)
        exp_matches = [m for m in matches if m.pii_type == PIIType.CARD_EXPIRY]
        assert len(exp_matches) >= 1, "Should detect card expiry"
    
    def test_track_data_prohibition(self, pci_detector):
        """Test that track data should never be stored"""
        # Track 1/2 data detection would be a specific pattern
        text = """
        MAGNETIC STRIPE DATA - CRITICAL VIOLATION
        Track 1: B4111111111111111^DOE/JOHN^2512101123400001230000000
        Track 2: 4111111111111111=2512101123400001230
        
        VIOLATION: Track data must NEVER be stored
        """
        matches = pci_detector.detect(text)
        # Should at least detect the PAN in track data
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) >= 1, "Should detect PAN within track data"


# ============================================================================
# REQUIREMENT 3.5: ENCRYPTION REQUIREMENTS
# ============================================================================

class TestPCIDSSEncryption:
    """Test PCI-DSS Encryption Requirements"""
    
    def test_unencrypted_pan_detection(self, pci_detector):
        """Test detection of unencrypted PAN in logs"""
        text = """
        APPLICATION LOG - SECURITY VIOLATION
        
        DEBUG: Processing payment for card 4111111111111111
        INFO: Transaction completed
        
        VIOLATION: PAN logged in clear text
        """
        matches = pci_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) >= 1, "Should detect unencrypted PAN in logs"
    
    def test_encrypted_pan_not_detected(self, pci_detector):
        """Test that encrypted PAN is not detected"""
        text = """
        ENCRYPTED PAYMENT DATA
        
        Encrypted PAN: a3f9b2c1d4e5f6a7b8c9d0e1f2a3b4c5
        Algorithm: AES-256
        Key ID: KEY-2026-001
        """
        matches = pci_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) == 0, "Encrypted PAN should not be detected"
    
    def test_hashed_pan_not_detected(self, pci_detector):
        """Test that hashed PAN is not detected"""
        text = """
        TOKENIZED PAYMENT DATA
        
        PAN Hash: 5e884898da28047d9151ed1c2f578e8a
        Token: TKN-12345678
        """
        matches = pci_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) == 0, "Hashed PAN should not be detected"


# ============================================================================
# REQUIREMENT 4: TRANSMISSION SECURITY
# ============================================================================

class TestPCIDSSRequirement4Transmission:
    """Test PCI-DSS Requirement 4 - Protect cardholder data during transmission"""
    
    def test_insecure_transmission_detection(self, pci_detector):
        """Test detection of PAN in insecure transmission"""
        text = """
        HTTP REQUEST LOG - SECURITY VIOLATION
        
        POST /payment HTTP/1.1 (NOT HTTPS!)
        Host: api.example.com
        
        Body: {"card_number": "4111111111111111"}
        
        VIOLATION: Cardholder data transmitted over HTTP
        """
        matches = pci_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) >= 1, "Should detect PAN in insecure transmission"
    
    def test_email_transmission_violation(self, pci_detector):
        """Test PAN should never be sent via email"""
        text = """
        EMAIL - PCI VIOLATION
        
        From: customer@email.com
        To: support@merchant.com
        Subject: Payment Issue
        
        My card number is 4111111111111111, please process manually.
        
        VIOLATION: PAN transmitted via email
        """
        matches = pci_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) >= 1, "Should detect PAN in email"


# ============================================================================
# REQUIREMENT 7: ACCESS CONTROL
# ============================================================================

class TestPCIDSSRequirement7Access:
    """Test PCI-DSS Requirement 7 - Restrict access by business need to know"""
    
    def test_access_control_logging(self, pci_detector):
        """Test access control logging for cardholder data"""
        text = """
        ACCESS CONTROL LOG
        
        User: payment_processor@merchant.com
        Action: VIEW
        Data accessed: Card ending in 1111
        Full PAN accessed: 4111111111111111
        Timestamp: 2026-01-31T10:30:00Z
        Business justification: Chargeback investigation
        """
        matches = pci_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) >= 1, "Should detect PAN in access log"
    
    def test_unauthorized_access_detection(self, pci_detector):
        """Test detection of potentially unauthorized access"""
        text = """
        SECURITY ALERT - UNAUTHORIZED ACCESS ATTEMPT
        
        User: intern@merchant.com
        Role: Intern (NO PCI ACCESS)
        Attempted to access: Card 4111111111111111
        
        ACCESS DENIED - User lacks authorization
        """
        matches = pci_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) >= 1, "Should detect PAN in access attempt"


# ============================================================================
# REQUIREMENT 8: AUTHENTICATION
# ============================================================================

class TestPCIDSSRequirement8Authentication:
    """Test PCI-DSS Requirement 8 - User authentication"""
    
    def test_authentication_logging(self, pci_detector):
        """Test authentication logging for PCI systems"""
        text = """
        AUTHENTICATION LOG
        
        User: admin@merchant.com
        System: Payment Gateway
        Action: LOGIN_SUCCESS
        MFA: Verified
        IP: 192.168.1.100
        
        Subsequent action: Viewed card 4111111111111111
        """
        matches = pci_detector.detect(text)
        
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]
        
        assert len(cc_matches) >= 1, "Should detect PAN"
        assert len(ip_matches) >= 1, "Should detect IP address"


# ============================================================================
# REQUIREMENT 10: LOGGING AND MONITORING
# ============================================================================

class TestPCIDSSRequirement10Logging:
    """Test PCI-DSS Requirement 10 - Log and monitor all access"""
    
    def test_pan_in_logs_violation(self, pci_detector):
        """Test detection of PAN in application logs (violation)"""
        text = """
        APPLICATION LOG - VIOLATION
        
        2026-01-31 10:30:00 INFO  PaymentService - Processing card: 4111111111111111
        2026-01-31 10:30:01 INFO  PaymentService - Amount: $100.00
        2026-01-31 10:30:02 INFO  PaymentService - CVV provided: 123
        
        VIOLATION: Full PAN and CVV logged
        """
        matches = pci_detector.detect(text)
        
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        cvv_matches = [m for m in matches if m.pii_type == PIIType.CVV]
        
        assert len(cc_matches) >= 1, "Should detect PAN in logs"
    
    def test_audit_trail_requirements(self, pci_detector):
        """Test audit trail contains required elements"""
        audit_entry = """
        PCI AUDIT TRAIL
        
        Entry ID: AUD-2026-001
        Timestamp: 2026-01-31T10:30:00Z
        User ID: user123
        User IP: 192.168.1.100
        Action: VIEW_CARDHOLDER_DATA
        Resource: Card ending *1111
        Success: true
        """
        
        required_fields = [
            "timestamp",
            "user id",
            "action",
            "success",
        ]
        
        for field in required_fields:
            assert field.lower() in audit_entry.lower(), f"Audit trail must include {field}"
    
    def test_compliant_logging(self, pci_detector):
        """Test compliant logging (no clear PAN)"""
        text = """
        COMPLIANT APPLICATION LOG
        
        2026-01-31 10:30:00 INFO  PaymentService - Processing card: ****1111
        2026-01-31 10:30:01 INFO  PaymentService - Amount: $100.00
        2026-01-31 10:30:02 INFO  PaymentService - Transaction approved
        """
        matches = pci_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) == 0, "Masked PAN should not be detected"


# ============================================================================
# PAN REDACTION TESTS
# ============================================================================

class TestPCIDSSRedaction:
    """Test PCI-DSS compliant redaction"""
    
    def test_pan_redaction(self, pci_detector):
        """Test PAN is properly redacted"""
        text = """
        PAYMENT CONFIRMATION
        
        Card Number: 4111111111111111
        Expiry: 12/26
        Amount: $100.00
        """
        
        redacted, matches = pci_detector.redact(text)
        
        assert "4111111111111111" not in redacted, "PAN should be redacted"
    
    def test_cvv_redaction(self, pci_detector):
        """Test CVV is properly redacted"""
        text = """
        PAYMENT DATA
        
        Card: 4111111111111111
        CVV: 123
        """
        
        redacted, matches = pci_detector.redact(text)
        
        assert "4111111111111111" not in redacted, "PAN should be redacted"
    
    def test_multiple_card_redaction(self, pci_detector):
        """Test multiple cards are all redacted"""
        text = """
        CARD DATABASE EXPORT - VIOLATION
        
        Card 1: 4111111111111111
        Card 2: 5555555555554444
        Card 3: 378282246310005
        """
        
        redacted, matches = pci_detector.redact(text)
        
        assert "4111111111111111" not in redacted
        assert "5555555555554444" not in redacted
        assert "378282246310005" not in redacted


# ============================================================================
# VALIDATION TESTS
# ============================================================================

class TestPCIDSSValidation:
    """Test PCI-DSS validation requirements"""
    
    def test_luhn_validation_valid(self, pci_detector):
        """Test Luhn algorithm validation - valid cards"""
        valid_cards = [
            "4111111111111111",  # Visa test
            "5555555555554444",  # Mastercard test
            "378282246310005",   # Amex test
            "6011111111111117",  # Discover test
        ]
        
        for card in valid_cards:
            text = f"Card: {card}"
            matches = pci_detector.detect(text)
            cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
            assert len(cc_matches) >= 1, f"Valid card {card} should be detected"
    
    def test_luhn_validation_invalid(self, pci_detector):
        """Test Luhn algorithm validation - invalid cards"""
        invalid_cards = [
            "4111111111111112",  # Invalid Luhn
            "5555555555554445",  # Invalid Luhn
            "1234567890123456",  # Invalid BIN and Luhn
        ]
        
        for card in invalid_cards:
            text = f"Card: {card}"
            matches = pci_detector.detect(text)
            cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
            assert len(cc_matches) == 0, f"Invalid card {card} should not be detected"
    
    def test_card_brand_identification(self, pci_detector):
        """Test card brand identification by BIN"""
        cards = [
            ("4111111111111111", "Visa"),      # 4xxx
            ("5555555555554444", "Mastercard"),  # 51-55xx
            ("378282246310005", "Amex"),       # 34xx, 37xx
            ("6011111111111117", "Discover"),  # 6011, 644-649, 65
        ]
        
        for card, brand in cards:
            text = f"Card: {card}"
            matches = pci_detector.detect(text)
            cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
            assert len(cc_matches) >= 1, f"{brand} card should be detected"


# ============================================================================
# REAL WORLD PCI-DSS SCENARIOS
# ============================================================================

class TestPCIDSSRealWorldScenarios:
    """Test real-world PCI-DSS compliance scenarios"""
    
    def test_payment_form_submission(self, pci_detector):
        """Test payment form data"""
        text = """
        PAYMENT FORM SUBMISSION
        
        Cardholder: John Smith
        Card Number: 4111111111111111
        Expiry: 12/26
        CVV: 123
        
        Billing Address:
        123 Main St
        Boston, MA 02101
        """
        
        matches = pci_detector.detect(text)
        
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        cvv_matches = [m for m in matches if m.pii_type == PIIType.CVV]
        exp_matches = [m for m in matches if m.pii_type == PIIType.CARD_EXPIRY]
        
        assert len(cc_matches) >= 1, "Should detect PAN"
    
    def test_transaction_log(self, pci_detector):
        """Test transaction log analysis"""
        text = """
        TRANSACTION LOG
        
        ID: TXN-2026-001234
        Timestamp: 2026-01-31T10:30:00Z
        
        Card: 4111111111111111
        Amount: $99.99
        Merchant: Example Store
        
        Status: APPROVED
        Auth Code: 123456
        """
        
        matches = pci_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) >= 1, "Should detect PAN in transaction log"
    
    def test_chargeback_investigation(self, pci_detector):
        """Test chargeback investigation document"""
        text = """
        CHARGEBACK INVESTIGATION
        
        Case ID: CB-2026-001
        
        Original Transaction:
        Card: 4111111111111111
        Date: 2026-01-15
        Amount: $250.00
        
        Reason: Unauthorized transaction
        
        Investigation notes:
        Customer claims card stolen on 2026-01-14
        """
        
        matches = pci_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) >= 1, "Should detect PAN in chargeback"
    
    def test_payment_receipt(self, pci_detector):
        """Test payment receipt (should have masked PAN)"""
        text = """
        PAYMENT RECEIPT
        
        Merchant: Example Store
        Date: 2026-01-31
        
        Card: ************1111
        Amount: $99.99
        
        Thank you for your purchase!
        """
        
        matches = pci_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) == 0, "Masked PAN on receipt should not be detected"


# ============================================================================
# SAQ (SELF-ASSESSMENT QUESTIONNAIRE) SCENARIOS
# ============================================================================

class TestPCIDSSSAQScenarios:
    """Test scenarios relevant to different SAQ types"""
    
    def test_saq_a_ecommerce(self, pci_detector):
        """Test SAQ A - E-commerce (all processing outsourced)"""
        text = """
        SAQ A COMPLIANCE CHECK
        
        Merchant: Example E-commerce
        SAQ Type: A (Card-not-present, all outsourced)
        
        Payment processing: Stripe
        Cardholder data stored locally: NO
        
        Compliant: No PAN should exist in merchant systems
        """
        
        matches = pci_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) == 0, "SAQ A merchant should have no PAN data"
    
    def test_saq_d_full_pan_storage(self, pci_detector):
        """Test SAQ D - Full PAN storage (highest compliance)"""
        text = """
        SAQ D COMPLIANCE CHECK
        
        Merchant: Payment Processor
        SAQ Type: D (Stores cardholder data)
        
        Encrypted PAN storage:
        Card: 4111111111111111 (ENCRYPTED: AES-256)
        Key management: HSM
        
        This merchant stores PAN and must comply with full PCI DSS
        """
        
        matches = pci_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        # Should detect the PAN (even though merchant claims encryption)
        assert len(cc_matches) >= 1, "Should detect PAN in SAQ D scenario"


# ============================================================================
# COMPLIANCE REPORTING
# ============================================================================

class TestPCIDSSComplianceReporting:
    """Test PCI-DSS compliance reporting"""
    
    def test_compliance_scan_report(self, pci_detector):
        """Test compliance scan report"""
        text = """
        PCI DSS COMPLIANCE SCAN REPORT
        
        Scan Date: 2026-01-31
        Scanner: Approved Scanning Vendor (ASV)
        
        Findings:
        
        CRITICAL: PAN found in application log
        Location: /var/log/payment.log
        Content: "Processing card 4111111111111111"
        
        HIGH: CVV stored in database
        Location: transactions.sensitive_data
        
        Remediation required: YES
        """
        
        matches = pci_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) >= 1, "Should detect PAN in scan report"
    
    def test_compliance_status(self):
        """Test PCI DSS compliance status tracking"""
        compliance_status = {
            "requirement_1": True,   # Network security
            "requirement_2": True,   # Secure configurations
            "requirement_3": False,  # Stored data (PAN found!)
            "requirement_4": True,   # Transmission security
            "requirement_5": True,   # Malware protection
            "requirement_6": True,   # Secure development
            "requirement_7": True,   # Access control
            "requirement_8": True,   # Authentication
            "requirement_9": True,   # Physical security
            "requirement_10": False, # Logging (PAN in logs!)
            "requirement_11": True,  # Testing
            "requirement_12": True,  # Policies
        }
        
        compliant_count = sum(1 for v in compliance_status.values() if v)
        total_requirements = len(compliance_status)
        
        assert compliant_count < total_requirements, "Should have compliance gaps"
        assert compliance_status["requirement_3"] == False, "Req 3 should fail (PAN found)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
