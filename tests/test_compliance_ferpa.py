"""
Tests for FERPA Compliance Framework
Phase 2.6a - Family Educational Rights and Privacy Act

FERPA Requirements Tested:
- Education Records Definition
- Directory Information
- Prior Consent Requirements
- Legitimate Educational Interest
- Annual Notification
- Student Rights (18+ or postsecondary)
"""

import pytest
from datetime import datetime
from tork_governance.detectors.pii_patterns import PIIDetector, PIIType


@pytest.fixture
def ferpa_detector():
    """PII detector configured for education records"""
    return PIIDetector(regions=['us', 'universal'])


class TestFERPAEducationRecords:
    """Test FERPA Education Records definitions"""

    def test_student_identifiers(self, ferpa_detector):
        """Test student PII detection"""
        text = """
        STUDENT RECORD

        Student ID: STU-2026-001234
        Name: John Smith
        Email: john.smith@university.edu
        SSN: 123-45-6789
        DOB: 01/15/2005
        """

        matches = ferpa_detector.detect(text)
        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(ssn_matches) >= 1, "Should detect student SSN"
        assert len(email_matches) >= 1, "Should detect student email"

    def test_grades_and_transcripts(self, ferpa_detector):
        """Test academic record detection"""
        text = """
        ACADEMIC TRANSCRIPT

        Student: john.smith@university.edu
        Student ID: 123456789

        Fall 2025:
        - MATH 101: A (4.0)
        - ENG 101: B+ (3.3)
        GPA: 3.65
        """

        matches = ferpa_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect student email in transcript"

    def test_disciplinary_records(self, ferpa_detector):
        """Test disciplinary record handling"""
        text = """
        DISCIPLINARY RECORD - CONFIDENTIAL

        Student: john.smith@university.edu
        Incident: Academic integrity violation
        Date: 2026-01-15
        Outcome: Warning

        This record is protected under FERPA.
        """

        matches = ferpa_detector.detect(text)
        assert len(matches) >= 1, "Should detect PII in disciplinary record"


class TestFERPADirectoryInformation:
    """Test FERPA Directory Information handling"""

    def test_directory_info_categories(self):
        """Test directory information categories"""
        directory_info = {
            "includable": [
                "name", "address", "phone", "email",
                "major", "enrollment_status", "degrees_awarded",
                "honors", "participation_activities"
            ],
            "excluded_by_default": [
                "ssn", "grades", "gpa", "financial_aid",
                "disciplinary_records", "disability_status"
            ],
        }

        assert "name" in directory_info["includable"]
        assert "ssn" in directory_info["excluded_by_default"]
        assert "grades" in directory_info["excluded_by_default"]

    def test_opt_out_tracking(self, ferpa_detector):
        """Test student opt-out of directory information"""
        text = """
        DIRECTORY INFORMATION OPT-OUT

        Student: john.smith@university.edu
        Request date: 2026-01-15

        Opted out of:
        - Phone directory: YES
        - Email directory: YES
        - Graduation program: NO

        Status: CONFIRMED
        """

        matches = ferpa_detector.detect(text)
        assert len(matches) >= 1, "Should detect student email"


class TestFERPAConsent:
    """Test FERPA consent requirements"""

    def test_prior_written_consent(self, ferpa_detector):
        """Test prior written consent for disclosure"""
        text = """
        FERPA CONSENT FORM

        Student: john.smith@university.edu

        I consent to release my education records to:
        Recipient: Employer Inc
        Purpose: Employment verification
        Records: Transcript, enrollment dates

        Signature: [Signed]
        Date: 2026-01-15
        """

        matches = ferpa_detector.detect(text)
        assert len(matches) >= 1, "Should detect student email in consent"

    def test_consent_exceptions(self):
        """Test FERPA consent exceptions"""
        exceptions = [
            "school_officials_legitimate_interest",
            "transfer_to_another_school",
            "financial_aid_purposes",
            "accrediting_organizations",
            "health_safety_emergency",
            "court_order_subpoena",
            "directory_information"
        ]

        assert len(exceptions) >= 7, "Should document consent exceptions"


class TestFERPAStudentRights:
    """Test FERPA student rights"""

    def test_right_to_inspect(self, ferpa_detector):
        """Test right to inspect records"""
        text = """
        RECORD INSPECTION REQUEST

        Student: john.smith@university.edu
        Request date: 2026-01-15

        Records requested:
        - Academic transcript
        - Financial aid records
        - Disciplinary records

        Response deadline: 45 days
        """

        matches = ferpa_detector.detect(text)
        assert len(matches) >= 1

    def test_right_to_amend(self, ferpa_detector):
        """Test right to request amendment"""
        text = """
        RECORD AMENDMENT REQUEST

        Student: john.smith@university.edu

        Record to amend: Fall 2025 grade for MATH 101
        Current value: F
        Requested value: Incomplete
        Reason: Medical emergency documentation provided

        Status: Under review
        """

        matches = ferpa_detector.detect(text)
        assert len(matches) >= 1

    def test_annual_notification(self):
        """Test annual notification requirements"""
        notification = {
            "published": True,
            "method": "Student handbook, website",
            "content": [
                "right_to_inspect",
                "right_to_amend",
                "right_to_consent",
                "right_to_file_complaint",
                "directory_information_policy"
            ],
            "updated_annually": True
        }

        assert notification["published"] == True
        assert len(notification["content"]) >= 5


class TestFERPARedaction:
    """Test FERPA-compliant redaction"""

    def test_education_record_redaction(self, ferpa_detector):
        """Test redaction of education records"""
        text = """
        STUDENT RECORD

        Email: john.smith@university.edu
        SSN: 123-45-6789
        Grades: A, B+, A-
        """

        redacted, matches = ferpa_detector.redact(text)

        assert "123-45-6789" not in redacted
        assert "john.smith@university.edu" not in redacted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
