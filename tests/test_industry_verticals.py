"""
Tests for Industry Vertical Compliance
Phase 3 of Comprehensive Test Plan

Industry Verticals Tested:
- Healthcare (hospitals, clinics, telehealth)
- Finance (banking, insurance, fintech)
- Education (K-12, higher education, EdTech)
- Retail (e-commerce, POS, loyalty programs)
- Technology (SaaS, cloud, AI/ML)
- Government (federal, state, local)
- Legal (law firms, legal tech)
- HR/Recruiting (employment, background checks)
"""

import pytest
from tork_governance.detectors.pii_patterns import PIIDetector, PIIType


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def healthcare_detector():
    """PII detector for healthcare industry"""
    return PIIDetector(regions=['us', 'universal', 'healthcare', 'biometric'])


@pytest.fixture
def finance_detector():
    """PII detector for financial industry"""
    return PIIDetector(regions=['us', 'universal', 'financial'])


@pytest.fixture
def education_detector():
    """PII detector for education industry"""
    return PIIDetector(regions=['us', 'universal'])


@pytest.fixture
def retail_detector():
    """PII detector for retail industry"""
    return PIIDetector(regions=['us', 'universal', 'financial'])


@pytest.fixture
def tech_detector():
    """PII detector for technology industry"""
    return PIIDetector(regions=['us', 'universal', 'eu_uk'])


# ============================================================================
# HEALTHCARE VERTICAL
# ============================================================================

class TestHealthcareVertical:
    """Test healthcare industry scenarios"""

    def test_hospital_patient_record(self, healthcare_detector):
        """Test hospital patient record handling"""
        text = """
        PATIENT ADMISSION RECORD

        Patient: John Smith
        MRN: MRN-2026-001234
        SSN: 123-45-6789
        DOB: 01/15/1985
        Email: john.smith@email.com
        Phone: 555-123-4567

        Insurance: BlueCross
        Policy: BC-123456789

        Diagnosis: ICD-10: J18.9 (Pneumonia)
        Attending: Dr. Jane Doe (NPI: 1234567890)
        """

        matches = healthcare_detector.detect(text)

        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(ssn_matches) >= 1, "Should detect patient SSN"
        assert len(email_matches) >= 1, "Should detect patient email"

    def test_telehealth_session(self, healthcare_detector):
        """Test telehealth session data"""
        text = """
        TELEHEALTH SESSION LOG

        Patient: john.smith@email.com
        Provider: dr.jane@clinic.com

        Session ID: TH-2026-001234
        Date: 2026-01-31
        Duration: 30 minutes

        Patient IP: 192.168.1.100

        Chief complaint: Headache
        Assessment: Tension headache
        Plan: OTC pain relief, follow-up PRN
        """

        matches = healthcare_detector.detect(text)

        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]

        assert len(email_matches) >= 1, "Should detect patient email"
        assert len(ip_matches) >= 1, "Should detect patient IP"

    def test_lab_results(self, healthcare_detector):
        """Test laboratory results handling"""
        text = """
        LABORATORY RESULTS

        Patient: john.smith@email.com
        MRN: MRN-2026-001234

        Test: Complete Blood Count (CBC)
        Order ID: LAB-2026-567890

        Results:
        - WBC: 7.5 (normal)
        - RBC: 4.8 (normal)
        - Hemoglobin: 14.2 (normal)

        Reviewed by: Dr. Jane Doe
        """

        matches = healthcare_detector.detect(text)
        assert len(matches) >= 1, "Should detect PII in lab results"

    def test_prescription_record(self, healthcare_detector):
        """Test prescription/pharmacy data"""
        text = """
        PRESCRIPTION RECORD

        Patient: John Smith
        DOB: 01/15/1985
        Email: john.smith@email.com

        Prescriber: Dr. Jane Doe
        DEA: AD1234567
        NPI: 1234567890

        Medication: Amoxicillin 500mg
        Quantity: 30 capsules
        Directions: Take 1 capsule 3x daily
        Refills: 0
        """

        matches = healthcare_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect patient email"

    def test_insurance_claim(self, healthcare_detector):
        """Test insurance claim processing"""
        text = """
        INSURANCE CLAIM

        Patient: john.smith@email.com
        SSN: 123-45-6789

        Provider: General Hospital
        NPI: 1234567890

        Service date: 2026-01-15
        Diagnosis: ICD-10: J18.9
        Procedure: CPT: 99213

        Billed amount: $250.00
        Allowed amount: $175.00
        Patient responsibility: $35.00
        """

        matches = healthcare_detector.detect(text)
        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]

        assert len(ssn_matches) >= 1, "Should detect SSN in claim"


# ============================================================================
# FINANCE VERTICAL
# ============================================================================

class TestFinanceVertical:
    """Test financial industry scenarios"""

    def test_bank_account_application(self, finance_detector):
        """Test bank account application"""
        text = """
        ACCOUNT APPLICATION

        Applicant: John Smith
        SSN: 123-45-6789
        Email: john.smith@email.com
        Phone: 555-123-4567

        Employment: Software Engineer
        Annual income: $150,000

        Account type: Checking
        Initial deposit: $5,000

        Funding source: 4111111111111111
        """

        matches = finance_detector.detect(text)

        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]

        assert len(ssn_matches) >= 1, "Should detect applicant SSN"
        assert len(cc_matches) >= 1, "Should detect funding card"

    def test_loan_application(self, finance_detector):
        """Test loan application processing"""
        text = """
        MORTGAGE APPLICATION

        Borrower: john.smith@email.com
        SSN: 123-45-6789

        Property: 123 Main St, Anytown, USA
        Purchase price: $500,000
        Down payment: $100,000
        Loan amount: $400,000

        Credit score: 750
        DTI ratio: 28%

        Bank account for verification: 12345678901234
        """

        matches = finance_detector.detect(text)

        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]

        assert len(ssn_matches) >= 1, "Should detect borrower SSN"

    def test_wire_transfer(self, finance_detector):
        """Test wire transfer data"""
        text = """
        WIRE TRANSFER REQUEST

        Sender: john.smith@email.com
        Account: 12345678901234
        Routing: 021000021

        Beneficiary: Jane Doe
        Beneficiary bank: ABC Bank
        SWIFT: ABCDEFGH
        IBAN: DE89370400440532013000

        Amount: $10,000.00
        Purpose: Family support
        """

        matches = finance_detector.detect(text)

        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect sender email"

    def test_investment_account(self, finance_detector):
        """Test investment account data"""
        text = """
        BROKERAGE ACCOUNT STATEMENT

        Account holder: john.smith@email.com
        SSN: 123-45-6789
        Account: 12345678

        Holdings:
        - AAPL: 100 shares @ $150.00
        - GOOGL: 50 shares @ $2,800.00

        Total value: $155,000.00
        YTD gains: $12,500.00
        """

        matches = finance_detector.detect(text)
        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]

        assert len(ssn_matches) >= 1, "Should detect holder SSN"

    def test_insurance_policy(self, finance_detector):
        """Test insurance policy data"""
        text = """
        LIFE INSURANCE POLICY

        Policyholder: john.smith@email.com
        SSN: 123-45-6789

        Policy number: LI-2026-123456
        Coverage: $1,000,000
        Premium: $150/month

        Beneficiary: Jane Smith (spouse)
        Beneficiary SSN: 987-65-4321
        """

        matches = finance_detector.detect(text)
        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]

        assert len(ssn_matches) >= 1, "Should detect SSNs"


# ============================================================================
# EDUCATION VERTICAL
# ============================================================================

class TestEducationVertical:
    """Test education industry scenarios"""

    def test_student_enrollment(self, education_detector):
        """Test student enrollment data"""
        text = """
        STUDENT ENROLLMENT FORM

        Student: John Smith Jr.
        DOB: 03/15/2015
        Grade: 5th

        Parent/Guardian: john.smith@email.com
        Phone: 555-123-4567

        Emergency contact: jane.smith@email.com

        Medical conditions: None
        IEP: No
        504 Plan: No
        """

        matches = education_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect parent email"

    def test_transcript_request(self, education_detector):
        """Test transcript request processing"""
        text = """
        TRANSCRIPT REQUEST

        Student: john.smith@university.edu
        Student ID: 123456789
        SSN: 123-45-6789

        Degree: Bachelor of Science
        Major: Computer Science
        GPA: 3.75
        Graduation: May 2025

        Send to: employer@company.com
        """

        matches = education_detector.detect(text)

        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(ssn_matches) >= 1, "Should detect student SSN"
        assert len(email_matches) >= 1, "Should detect student email"

    def test_financial_aid(self, education_detector):
        """Test financial aid application"""
        text = """
        FAFSA APPLICATION DATA

        Student: john.smith@email.com
        SSN: 123-45-6789

        Parent 1 SSN: 111-22-3333
        Parent 1 income: $85,000

        Parent 2 SSN: 444-55-6666
        Parent 2 income: $75,000

        Expected Family Contribution: $15,000
        Financial need: $35,000
        """

        matches = education_detector.detect(text)
        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]

        assert len(ssn_matches) >= 1, "Should detect SSNs"

    def test_online_learning(self, education_detector):
        """Test online learning platform data"""
        text = """
        LMS USER PROFILE

        Student: john.smith@school.edu
        Student ID: STU-2026-001

        IP address: 192.168.1.100
        Last login: 2026-01-31T10:30:00Z

        Courses enrolled:
        - MATH 101
        - ENG 101
        - CS 101

        Progress: 75% complete
        """

        matches = education_detector.detect(text)

        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]

        assert len(email_matches) >= 1
        assert len(ip_matches) >= 1


# ============================================================================
# RETAIL VERTICAL
# ============================================================================

class TestRetailVertical:
    """Test retail industry scenarios"""

    def test_ecommerce_order(self, retail_detector):
        """Test e-commerce order processing"""
        text = """
        ORDER CONFIRMATION

        Customer: john.smith@email.com
        Order #: ORD-2026-123456

        Billing:
        Card: 4111111111111111
        Exp: 12/28
        CVV: [redacted]

        Shipping:
        John Smith
        123 Main St
        Anytown, CA 90001
        Phone: 555-123-4567

        Items:
        - Widget Pro: $99.99
        - Shipping: $9.99
        Total: $109.98
        """

        matches = retail_detector.detect(text)

        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(cc_matches) >= 1, "Should detect credit card"
        assert len(email_matches) >= 1, "Should detect customer email"

    def test_loyalty_program(self, retail_detector):
        """Test loyalty program data"""
        text = """
        LOYALTY MEMBER PROFILE

        Member: john.smith@email.com
        Member ID: LYL-123456789
        Phone: 555-123-4567

        Tier: Gold
        Points balance: 15,234
        Lifetime points: 125,000

        Preferences:
        - Electronics
        - Home & Garden

        Linked payment: ****1111
        """

        matches = retail_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect member email"

    def test_pos_transaction(self, retail_detector):
        """Test point of sale transaction"""
        text = """
        POS TRANSACTION LOG

        Store: #1234
        Terminal: POS-05
        Cashier: emp@store.com

        Customer card: 4111111111111111
        Auth code: 123456

        Items:
        - Product A: $25.00
        - Product B: $15.00
        Tax: $3.20
        Total: $43.20

        Customer email (receipt): john.smith@email.com
        """

        matches = retail_detector.detect(text)
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]

        assert len(cc_matches) >= 1, "Should detect payment card"

    def test_return_request(self, retail_detector):
        """Test return/refund request"""
        text = """
        RETURN REQUEST

        Customer: john.smith@email.com
        Order: ORD-2026-123456

        Item: Widget Pro
        Reason: Defective

        Refund to: 4111111111111111
        Amount: $99.99

        Status: Approved
        """

        matches = retail_detector.detect(text)

        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(cc_matches) >= 1
        assert len(email_matches) >= 1


# ============================================================================
# TECHNOLOGY VERTICAL
# ============================================================================

class TestTechnologyVertical:
    """Test technology industry scenarios"""

    def test_saas_user_account(self, tech_detector):
        """Test SaaS user account data"""
        text = """
        USER ACCOUNT

        Email: john.smith@company.com
        User ID: usr_abc123xyz

        Organization: Acme Corp
        Role: Admin

        API key: sk_live_abc123xyz789

        Last login: 2026-01-31T10:30:00Z
        IP: 192.168.1.100

        MFA: Enabled
        """

        matches = tech_detector.detect(text)

        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]

        assert len(email_matches) >= 1, "Should detect user email"
        assert len(ip_matches) >= 1, "Should detect user IP"

    def test_cloud_infrastructure(self, tech_detector):
        """Test cloud infrastructure logs"""
        text = """
        CLOUD AUDIT LOG

        User: admin@company.com
        Action: CreateInstance
        Resource: EC2 i-1234567890abcdef0

        Source IP: 192.168.1.100
        Region: us-west-2

        Instance details:
        - Private IP: 10.0.1.50
        - Public IP: 52.24.123.45

        IAM role: arn:aws:iam::123456789012:role/AdminRole
        """

        matches = tech_detector.detect(text)

        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]

        assert len(email_matches) >= 1
        assert len(ip_matches) >= 1

    def test_ai_ml_training_data(self, tech_detector):
        """Test AI/ML training data handling"""
        text = """
        TRAINING DATA SAMPLE

        Record ID: train_001

        Input features:
        - user_email: john.smith@email.com
        - user_ip: 192.168.1.100
        - purchase_amount: 150.00

        Label: fraud_score = 0.15

        Note: PII must be anonymized before training
        """

        matches = tech_detector.detect(text)

        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]

        assert len(email_matches) >= 1, "Should detect email in training data"
        assert len(ip_matches) >= 1, "Should detect IP in training data"

    def test_api_request_log(self, tech_detector):
        """Test API request logging"""
        text = """
        API REQUEST LOG

        Endpoint: POST /api/v1/users

        Request headers:
        - Authorization: Bearer eyJhbGc...
        - X-Forwarded-For: 192.168.1.100

        Request body:
        {
            "email": "john.smith@email.com",
            "name": "John Smith",
            "phone": "555-123-4567"
        }

        Response: 201 Created
        """

        matches = tech_detector.detect(text)

        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]

        assert len(email_matches) >= 1
        assert len(ip_matches) >= 1


# ============================================================================
# GOVERNMENT VERTICAL
# ============================================================================

class TestGovernmentVertical:
    """Test government industry scenarios"""

    def test_citizen_services(self, tech_detector):
        """Test citizen services portal"""
        text = """
        CITIZEN ACCOUNT

        Name: John Smith
        SSN: 123-45-6789
        Email: john.smith@email.com

        Services enrolled:
        - Tax filing
        - Benefits
        - License renewal

        Verification: ID.me verified
        Last login: 2026-01-31
        """

        matches = tech_detector.detect(text)
        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]

        assert len(ssn_matches) >= 1, "Should detect citizen SSN"

    def test_tax_filing(self, finance_detector):
        """Test tax filing data"""
        text = """
        TAX RETURN DATA

        Taxpayer: John Smith
        SSN: 123-45-6789
        Email: john.smith@email.com

        Filing status: Married Filing Jointly
        Spouse SSN: 987-65-4321

        Income: $175,000
        Deductions: $25,000
        Tax due: $28,500

        Bank account for refund: 12345678901234
        Routing: 021000021
        """

        matches = finance_detector.detect(text)
        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]

        assert len(ssn_matches) >= 1


# ============================================================================
# LEGAL VERTICAL
# ============================================================================

class TestLegalVertical:
    """Test legal industry scenarios"""

    def test_client_intake(self, tech_detector):
        """Test law firm client intake"""
        text = """
        CLIENT INTAKE FORM

        Client: John Smith
        Email: john.smith@email.com
        Phone: 555-123-4567
        SSN: 123-45-6789

        Matter type: Personal injury
        Adverse party: ABC Corporation

        Confidential - Attorney-Client Privileged
        """

        matches = tech_detector.detect(text)

        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(ssn_matches) >= 1
        assert len(email_matches) >= 1

    def test_ediscovery_document(self, tech_detector):
        """Test e-discovery document processing"""
        text = """
        E-DISCOVERY DOCUMENT

        Custodian: john.smith@company.com
        Document ID: DOC-2026-123456

        From: john.smith@company.com
        To: jane.doe@company.com
        Date: 2025-06-15

        Content contains:
        - Employee SSN: 123-45-6789
        - Customer credit card: 4111111111111111

        Review status: Privileged
        """

        matches = tech_detector.detect(text)

        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]

        assert len(ssn_matches) >= 1
        assert len(cc_matches) >= 1


# ============================================================================
# HR/RECRUITING VERTICAL
# ============================================================================

class TestHRRecruitingVertical:
    """Test HR and recruiting industry scenarios"""

    def test_job_application(self, tech_detector):
        """Test job application processing"""
        text = """
        JOB APPLICATION

        Applicant: John Smith
        Email: john.smith@email.com
        Phone: 555-123-4567

        Position: Software Engineer

        Education:
        - BS Computer Science, MIT, 2020

        Experience:
        - 5 years software development

        Work authorization: US Citizen
        """

        matches = tech_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect applicant email"

    def test_background_check(self, tech_detector):
        """Test background check data"""
        text = """
        BACKGROUND CHECK REPORT

        Subject: John Smith
        SSN: 123-45-6789
        DOB: 01/15/1990

        Criminal history: None found
        Employment verification: Confirmed
        Education verification: Confirmed
        Credit check: Score 750

        Report generated: 2026-01-31
        """

        matches = tech_detector.detect(text)
        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]

        assert len(ssn_matches) >= 1, "Should detect subject SSN"

    def test_employee_onboarding(self, tech_detector):
        """Test employee onboarding data"""
        text = """
        NEW HIRE ONBOARDING

        Employee: john.smith@company.com
        SSN: 123-45-6789

        Start date: 2026-02-01
        Department: Engineering
        Manager: jane.doe@company.com

        Direct deposit:
        Bank: Chase
        Account: 12345678901234
        Routing: 021000021

        Emergency contact:
        Jane Smith: 555-987-6543
        """

        matches = tech_detector.detect(text)

        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(ssn_matches) >= 1
        assert len(email_matches) >= 1

    def test_payroll_record(self, finance_detector):
        """Test payroll data handling"""
        text = """
        PAYROLL RECORD

        Employee: john.smith@company.com
        SSN: 123-45-6789

        Pay period: 01/01/2026 - 01/15/2026

        Gross pay: $6,250.00
        Federal tax: $1,250.00
        State tax: $500.00
        FICA: $478.13
        Net pay: $4,021.87

        Direct deposit: ****1234
        """

        matches = finance_detector.detect(text)
        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]

        assert len(ssn_matches) >= 1


# ============================================================================
# CROSS-INDUSTRY REDACTION TESTS
# ============================================================================

class TestIndustryRedaction:
    """Test redaction across industry verticals"""

    def test_healthcare_redaction(self, healthcare_detector):
        """Test healthcare data redaction"""
        text = """
        Patient: john.smith@email.com
        SSN: 123-45-6789
        MRN: MRN-001234
        """

        redacted, matches = healthcare_detector.redact(text)

        assert "123-45-6789" not in redacted
        assert "john.smith@email.com" not in redacted

    def test_finance_redaction(self, finance_detector):
        """Test financial data redaction"""
        text = """
        Customer: john.smith@email.com
        SSN: 123-45-6789
        Card: 4111111111111111
        """

        redacted, matches = finance_detector.redact(text)

        assert "123-45-6789" not in redacted
        assert "4111111111111111" not in redacted

    def test_education_redaction(self, education_detector):
        """Test education data redaction"""
        text = """
        Student: john.smith@university.edu
        SSN: 123-45-6789
        GPA: 3.75
        """

        redacted, matches = education_detector.redact(text)

        assert "123-45-6789" not in redacted
        assert "john.smith@university.edu" not in redacted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
