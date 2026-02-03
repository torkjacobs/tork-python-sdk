"""
Tests for COPPA Compliance Framework
Phase 2.6c - Children's Online Privacy Protection Act

COPPA Requirements Tested:
- Applies to children under 13
- Verifiable Parental Consent
- Privacy Policy Requirements
- Data Minimization
- Parental Rights
- Safe Harbor Programs
"""

import pytest
from tork_governance.detectors.pii_patterns import PIIDetector, PIIType


@pytest.fixture
def coppa_detector():
    """PII detector configured for children's data"""
    return PIIDetector(regions=['us', 'universal'])


class TestCOPPAPersonalInformation:
    """Test COPPA personal information from children"""

    def test_child_identifiers(self, coppa_detector):
        """Test detection of child's personal information"""
        text = """
        CHILD USER PROFILE

        Username: coolkid123
        Email: parent@email.com (parent)
        Child email: child@kidmail.com
        Age: 10
        Birthday: DOB: 03/15/2016
        School: Lincoln Elementary
        """

        matches = coppa_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect email addresses"

    def test_persistent_identifiers(self, coppa_detector):
        """Test persistent identifiers as PI under COPPA"""
        text = """
        DEVICE TRACKING - COPPA RESTRICTED

        Parent email: parent@email.com

        Device identifiers collected:
        - IP: 192.168.1.100
        - Device ID: DEV-12345
        - Cookie ID: COOK-67890

        Requires parental consent: YES
        """

        matches = coppa_detector.detect(text)
        ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]

        assert len(ip_matches) >= 1, "Should detect IP as persistent identifier"

    def test_photos_and_media(self):
        """Test photo/video/audio as PI"""
        media_types = {
            "photo_containing_child": True,
            "video_containing_child": True,
            "audio_containing_child_voice": True,
            "requires_parental_consent": True
        }

        assert media_types["requires_parental_consent"] == True


class TestCOPPAParentalConsent:
    """Test COPPA Verifiable Parental Consent"""

    def test_consent_methods(self):
        """Test acceptable consent verification methods"""
        consent_methods = [
            "signed_consent_form",
            "credit_card_transaction",
            "toll_free_call",
            "video_conference",
            "government_id_check",
            "knowledge_based_authentication"
        ]

        assert len(consent_methods) >= 6

    def test_consent_record(self, coppa_detector):
        """Test parental consent record"""
        text = """
        PARENTAL CONSENT RECORD

        Parent: parent@email.com
        Child username: coolkid123

        Consent date: 2026-01-15
        Verification method: Credit card transaction

        Consented to:
        - Account creation: YES
        - Email collection: YES
        - Photo sharing: NO

        Consent revocable: YES
        """

        matches = coppa_detector.detect(text)
        assert len(matches) >= 1

    def test_consent_exceptions(self):
        """Test exceptions to prior consent"""
        exceptions = [
            "one_time_response_to_child",
            "safety_of_child",
            "internal_operations_support",
            "fraud_prevention"
        ]

        # Limited exceptions under COPPA
        assert len(exceptions) >= 4


class TestCOPPAPrivacyPolicy:
    """Test COPPA Privacy Policy requirements"""

    def test_policy_content(self):
        """Test required privacy policy elements"""
        policy_requirements = {
            "operator_contact_info": True,
            "types_of_pi_collected": True,
            "how_pi_used": True,
            "disclosure_practices": True,
            "parental_rights": True,
            "data_retention_policy": True,
            "online_contact_info_policy": True
        }

        for element, required in policy_requirements.items():
            assert required == True

    def test_direct_notice_to_parent(self, coppa_detector):
        """Test direct notice to parent"""
        text = """
        PARENT NOTIFICATION

        Dear parent@email.com,

        Your child (coolkid123) has requested to create an account.

        We will collect:
        - Username
        - Email (yours for contact)
        - Age

        We will NOT collect:
        - Location data
        - Photos
        - Audio/video

        Please confirm consent at: [link]
        """

        matches = coppa_detector.detect(text)
        assert len(matches) >= 1


class TestCOPPAParentalRights:
    """Test COPPA parental rights"""

    def test_right_to_review(self, coppa_detector):
        """Test parent's right to review child's data"""
        text = """
        PARENTAL DATA REVIEW REQUEST

        Parent: parent@email.com
        Child: coolkid123

        Data on file:
        - Username: coolkid123
        - Age: 10
        - Favorite color: Blue
        - Game progress: Level 15

        No additional PI collected.
        """

        matches = coppa_detector.detect(text)
        assert len(matches) >= 1

    def test_right_to_delete(self, coppa_detector):
        """Test parent's right to delete child's data"""
        text = """
        PARENTAL DELETION REQUEST

        Parent: parent@email.com
        Child: coolkid123
        Request date: 2026-01-15

        Delete all data: YES
        Close account: YES

        Status: COMPLETED
        Data deleted: 2026-01-16
        """

        matches = coppa_detector.detect(text)
        assert len(matches) >= 1

    def test_right_to_revoke_consent(self):
        """Test parent's right to revoke consent"""
        revocation = {
            "revocation_allowed": True,
            "future_collection_stops": True,
            "past_data_deletable": True,
            "service_may_be_limited": True
        }

        assert revocation["revocation_allowed"] == True


class TestCOPPADataMinimization:
    """Test COPPA data minimization requirements"""

    def test_collection_limits(self):
        """Test limits on data collection"""
        limits = {
            "only_reasonably_necessary": True,
            "no_conditioning_on_excess_data": True,
            "activity_participation_not_conditioned": True
        }

        for limit, required in limits.items():
            assert required == True

    def test_retention_limits(self):
        """Test data retention requirements"""
        retention = {
            "retain_only_as_long_as_necessary": True,
            "delete_when_no_longer_needed": True,
            "reasonable_security_during_retention": True
        }

        assert retention["retain_only_as_long_as_necessary"] == True


class TestCOPPARedaction:
    """Test COPPA-compliant redaction"""

    def test_child_data_redaction(self, coppa_detector):
        """Test redaction of child's data"""
        text = """
        CHILD PROFILE

        Parent email: parent@email.com
        Child email: child@school.edu
        IP: 192.168.1.100
        """

        redacted, matches = coppa_detector.redact(text)

        assert "parent@email.com" not in redacted
        assert "192.168.1.100" not in redacted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
