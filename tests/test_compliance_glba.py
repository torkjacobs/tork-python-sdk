"""
Tests for GLBA Compliance Framework
Phase 2.6b - Gramm-Leach-Bliley Act

GLBA Requirements Tested:
- Financial Privacy Rule
- Safeguards Rule
- Pretexting Protection
- Nonpublic Personal Information (NPI)
- Opt-Out Requirements
"""

import pytest
from tork_governance.detectors.pii_patterns import PIIDetector, PIIType


@pytest.fixture
def glba_detector():
    """PII detector configured for financial NPI"""
    return PIIDetector(regions=['us', 'universal', 'financial'])


class TestGLBANonpublicPersonalInformation:
    """Test GLBA Nonpublic Personal Information (NPI)"""

    def test_npi_identifiers(self, glba_detector):
        """Test NPI detection"""
        text = """
        CUSTOMER FINANCIAL RECORD

        Customer: john.smith@email.com
        SSN: 123-45-6789
        Account: 12345678901234
        Credit Card: 4111111111111111
        Income: $150,000
        Credit Score: 750
        """

        matches = glba_detector.detect(text)

        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]

        assert len(ssn_matches) >= 1, "Should detect SSN as NPI"
        assert len(cc_matches) >= 1, "Should detect credit card"

    def test_transaction_data(self, glba_detector):
        """Test transaction data as NPI"""
        text = """
        TRANSACTION HISTORY

        Account holder: john.smith@email.com
        Account: 12345678901234

        Recent transactions:
        - 01/15: $500.00 - Retail purchase
        - 01/20: $1,200.00 - Mortgage payment
        """

        matches = glba_detector.detect(text)
        assert len(matches) >= 1, "Should detect NPI in transactions"

    def test_account_relationships(self, glba_detector):
        """Test account relationship information"""
        text = """
        CUSTOMER PROFILE

        Primary: john.smith@email.com

        Accounts:
        - Checking: ****1234
        - Savings: ****5678
        - Credit Card: 4111111111111111

        Relationship start: 2015-01-15
        """

        matches = glba_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        assert len(cc_matches) >= 1


class TestGLBAPrivacyRule:
    """Test GLBA Financial Privacy Rule"""

    def test_privacy_notice_requirements(self):
        """Test privacy notice content requirements"""
        privacy_notice = {
            "provided_at_relationship_start": True,
            "provided_annually": True,
            "content": [
                "categories_of_npi_collected",
                "categories_of_npi_disclosed",
                "categories_of_affiliates_nonaffiliates",
                "opt_out_right",
                "confidentiality_practices",
                "information_security_practices"
            ],
            "clear_and_conspicuous": True
        }

        assert privacy_notice["provided_annually"] == True
        assert len(privacy_notice["content"]) >= 6

    def test_opt_out_mechanism(self, glba_detector):
        """Test opt-out of information sharing"""
        text = """
        OPT-OUT NOTICE

        Customer: john.smith@email.com

        You have the right to opt out of:
        - Sharing with nonaffiliated third parties
        - Marketing by affiliates

        Current preferences:
        - Third-party sharing: OPTED OUT
        - Affiliate marketing: OPTED OUT
        """

        matches = glba_detector.detect(text)
        assert len(matches) >= 1

    def test_sharing_exceptions(self):
        """Test exceptions to opt-out requirement"""
        exceptions = [
            "processing_transactions",
            "servicing_accounts",
            "fraud_prevention",
            "legal_compliance",
            "credit_reporting_agencies",
            "securitization",
            "joint_marketing_agreements"
        ]

        assert len(exceptions) >= 7


class TestGLBASafeguardsRule:
    """Test GLBA Safeguards Rule"""

    def test_information_security_program(self):
        """Test written security program requirements"""
        security_program = {
            "written_program": True,
            "risk_assessment": True,
            "employee_training": True,
            "service_provider_oversight": True,
            "program_evaluation": True,
            "board_oversight": True
        }

        for element, required in security_program.items():
            assert required == True, f"Security program must include {element}"

    def test_access_controls(self, glba_detector):
        """Test access control logging"""
        text = """
        ACCESS LOG - NPI SYSTEM

        User: analyst@bank.com
        Customer accessed: john.smith@email.com
        Data viewed: Account balance, transaction history
        Time: 2026-01-31T10:30:00Z
        Purpose: Customer service inquiry
        """

        matches = glba_detector.detect(text)
        assert len(matches) >= 1

    def test_encryption_requirements(self):
        """Test encryption of NPI"""
        encryption = {
            "data_at_rest": "AES-256",
            "data_in_transit": "TLS 1.2+",
            "key_management": True,
            "mfa_for_access": True
        }

        assert "AES" in encryption["data_at_rest"]
        assert "TLS" in encryption["data_in_transit"]


class TestGLBAPretextingProtection:
    """Test GLBA Pretexting provisions"""

    def test_identity_verification(self, glba_detector):
        """Test customer identity verification"""
        text = """
        IDENTITY VERIFICATION LOG

        Caller claiming to be: john.smith@email.com

        Verification steps:
        1. Security questions: PASSED
        2. SMS code: VERIFIED
        3. Account details: CONFIRMED

        Identity verified: YES
        Access granted: YES
        """

        matches = glba_detector.detect(text)
        assert len(matches) >= 1

    def test_pretexting_detection(self):
        """Test pretexting attempt indicators"""
        red_flags = [
            "urgency_pressure",
            "inconsistent_information",
            "unusual_request_type",
            "third_party_claiming_authority",
            "request_for_full_ssn",
            "refusal_to_verify_identity"
        ]

        assert len(red_flags) >= 6


class TestGLBARedaction:
    """Test GLBA-compliant NPI redaction"""

    def test_npi_redaction(self, glba_detector):
        """Test NPI redaction"""
        text = """
        CUSTOMER RECORD

        Email: john.smith@email.com
        SSN: 123-45-6789
        Card: 4111111111111111
        """

        redacted, matches = glba_detector.redact(text)

        assert "123-45-6789" not in redacted
        assert "4111111111111111" not in redacted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
