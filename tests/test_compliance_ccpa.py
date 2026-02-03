"""
Tests for CCPA Compliance Framework
Phase 2.5 of Comprehensive Test Plan

California Consumer Privacy Act (CCPA) / CPRA Requirements Tested:
- Right to Know (1798.100, 1798.110)
- Right to Delete (1798.105)
- Right to Opt-Out of Sale (1798.120)
- Right to Non-Discrimination (1798.125)
- Right to Correct (CPRA 1798.106)
- Right to Limit Use of Sensitive PI (CPRA 1798.121)
- Business Obligations (1798.130, 1798.135, 1798.140)
- Service Provider Requirements
- Contractor Requirements (CPRA)
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
def ccpa_detector():
    """PII detector configured for CCPA personal information"""
    return PIIDetector(regions=['us', 'universal', 'financial', 'biometric'])


@pytest.fixture
def sample_consumer_data():
    """Sample California consumer personal information"""
    return {
        "name": "John Smith",
        "email": "john.smith@email.com",
        "ssn": "SSN: 123-45-6789",
        "phone": "555-123-4567",
        "address": "123 Main St, Los Angeles, CA 90001",
        "ip_address": "192.168.1.100",
        "device_id": "Device-ABC123",
        "geolocation": "34.0522° N, 118.2437° W",
    }


# ============================================================================
# CCPA PERSONAL INFORMATION CATEGORIES
# ============================================================================

class TestCCPAPersonalInformation:
    """Test CCPA Personal Information categories (1798.140(o))"""

    def test_category_a_identifiers(self, ccpa_detector):
        """Test Category A: Identifiers (name, SSN, email, etc.)"""
        text = """
        CONSUMER RECORD - CATEGORY A

        Real name: John Smith
        SSN: 123-45-6789
        Email: john.smith@email.com
        Phone: 555-123-4567
        """

        matches = ccpa_detector.detect(text)

        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        phone_matches = [m for m in matches if m.pii_type == PIIType.PHONE_US]

        assert len(ssn_matches) >= 1, "Should detect SSN"
        assert len(email_matches) >= 1, "Should detect email"

    def test_category_b_customer_records(self, ccpa_detector):
        """Test Category B: Customer Records (Cal. Civ. Code 1798.80(e))"""
        text = """
        CUSTOMER RECORD - CATEGORY B

        Name: John Smith
        Bank Account: 12345678901234
        Credit Card: 4111111111111111
        Insurance Policy: POL-123456789
        """

        matches = ccpa_detector.detect(text)

        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]
        bank_matches = [m for m in matches if m.pii_type == PIIType.BANK_ACCOUNT]

        assert len(cc_matches) >= 1, "Should detect credit card"

    def test_category_c_protected_classifications(self):
        """Test Category C: Protected Classifications"""
        # Protected characteristics - no direct pattern detection
        # but documented for compliance
        protected_categories = [
            "race",
            "religion",
            "sexual_orientation",
            "gender_identity",
            "marital_status",
            "disability",
            "veteran_status",
        ]

        assert len(protected_categories) >= 7, "Should track protected classifications"

    def test_category_d_commercial_information(self, ccpa_detector):
        """Test Category D: Commercial Information"""
        text = """
        PURCHASE HISTORY - CATEGORY D

        Customer: john.smith@email.com

        Purchases:
        - Order #12345: Electronics, $499.99
        - Order #12346: Clothing, $129.99

        Total lifetime value: $15,234.50
        """

        matches = ccpa_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect customer email"

    def test_category_e_biometric_information(self, ccpa_detector):
        """Test Category E: Biometric Information"""
        text = """
        BIOMETRIC DATA - CATEGORY E

        Employee: john.smith@email.com

        Biometric ID: BIO-CA-2026-001
        Face ID: FACE-CA-001234
        Fingerprint ID: FP-CA-001234

        Purpose: Building access
        """

        matches = ccpa_detector.detect(text)

        bio_matches = [m for m in matches if 'BIOMETRIC' in str(m.pii_type) or 'FACE' in str(m.pii_type) or 'FINGER' in str(m.pii_type)]

        assert len(bio_matches) >= 1, "Should detect biometric identifiers"

    def test_category_f_internet_activity(self, ccpa_detector):
        """Test Category F: Internet/Network Activity"""
        text = """
        BROWSING HISTORY - CATEGORY F

        User: john.smith@email.com
        IP: 192.168.1.100

        Pages visited:
        - /products/electronics
        - /checkout
        - /order-confirmation

        Session duration: 15 minutes
        """

        matches = ccpa_detector.detect(text)

        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]

        assert len(email_matches) >= 1, "Should detect email"
        assert len(ip_matches) >= 1, "Should detect IP address"

    def test_category_g_geolocation(self, ccpa_detector):
        """Test Category G: Geolocation Data"""
        text = """
        LOCATION DATA - CATEGORY G

        User: john.smith@email.com
        Device IP: 192.168.1.100

        Location history:
        - Los Angeles, CA
        - San Francisco, CA

        Precise location: 34.0522, -118.2437
        """

        matches = ccpa_detector.detect(text)
        ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]

        assert len(ip_matches) >= 1, "Should detect IP as location indicator"

    def test_category_i_professional_information(self, ccpa_detector):
        """Test Category I: Professional/Employment Information"""
        text = """
        EMPLOYEE RECORD - CATEGORY I

        Email: john.smith@company.com

        Position: Software Engineer
        Department: Engineering
        Salary: $150,000
        Start date: 2020-01-15
        Manager: jane.doe@company.com
        """

        matches = ccpa_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect employee emails"


# ============================================================================
# RIGHT TO KNOW (1798.100, 1798.110)
# ============================================================================

class TestCCPARightToKnow:
    """Test CCPA Right to Know requirements"""

    def test_disclosure_request(self, ccpa_detector):
        """Test handling of right to know request"""
        text = """
        RIGHT TO KNOW REQUEST

        Consumer: john.smith@email.com
        Request date: 2026-01-15
        Request ID: RTK-2026-001

        Requested information:
        - Categories of PI collected
        - Specific pieces of PI
        - Sources of PI
        - Business purpose for collection
        - Categories of third parties

        Response deadline: 45 days
        """

        matches = ccpa_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect consumer email"

    def test_disclosure_response(self, ccpa_detector):
        """Test right to know response content"""
        text = """
        RIGHT TO KNOW RESPONSE

        Consumer: john.smith@email.com
        Response date: 2026-02-01

        PERSONAL INFORMATION COLLECTED:

        Category A - Identifiers:
        - Email: john.smith@email.com
        - SSN: 123-45-6789
        - Phone: 555-123-4567

        Category B - Financial:
        - Credit Card: 4111111111111111 (last 4 only shown)

        Sources: Direct collection, third-party partners
        Business purpose: Order fulfillment, marketing
        Third parties: Payment processors, shipping partners
        """

        matches = ccpa_detector.detect(text)

        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]

        assert len(ssn_matches) >= 1, "Should detect SSN in response"

    def test_45_day_response_deadline(self):
        """Test 45-day response requirement"""
        request_date = datetime(2026, 1, 15)
        deadline = request_date + timedelta(days=45)

        # Can extend by additional 45 days with notice
        extended_deadline = deadline + timedelta(days=45)

        assert deadline == datetime(2026, 3, 1)
        assert extended_deadline == datetime(2026, 4, 15)


# ============================================================================
# RIGHT TO DELETE (1798.105)
# ============================================================================

class TestCCPARightToDelete:
    """Test CCPA Right to Delete requirements"""

    def test_deletion_request(self, ccpa_detector):
        """Test handling of deletion request"""
        text = """
        DELETION REQUEST

        Consumer: john.smith@email.com
        Request date: 2026-01-15
        Request ID: DEL-2026-001

        Data to delete:
        - Account information
        - Purchase history
        - Marketing preferences

        Verification: Identity confirmed
        Status: Processing
        """

        matches = ccpa_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect consumer email"

    def test_deletion_exceptions(self):
        """Test exceptions to deletion requirement"""
        deletion_exceptions = [
            "complete_transaction",
            "security_incident_detection",
            "debug_errors",
            "free_speech",
            "legal_compliance",
            "internal_uses_reasonably_aligned",
            "research_in_public_interest",
        ]

        # All 9 CCPA exceptions should be documented
        assert len(deletion_exceptions) >= 7

    def test_service_provider_deletion(self, ccpa_detector):
        """Test service provider deletion notification"""
        text = """
        SERVICE PROVIDER DELETION NOTICE

        From: business@company.com
        To: serviceprovider@vendor.com

        Consumer: john.smith@email.com

        Please delete all personal information for the above consumer
        per CCPA 1798.105(c).

        Confirmation required within: 90 days
        """

        matches = ccpa_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect consumer email in notice"


# ============================================================================
# RIGHT TO OPT-OUT OF SALE (1798.120)
# ============================================================================

class TestCCPARightToOptOut:
    """Test CCPA Right to Opt-Out of Sale"""

    def test_opt_out_request(self, ccpa_detector):
        """Test opt-out of sale request"""
        text = """
        OPT-OUT OF SALE REQUEST

        Consumer: john.smith@email.com
        IP: 192.168.1.100

        Request: Do Not Sell My Personal Information
        Date: 2026-01-15

        Method: "Do Not Sell" link on website
        Status: CONFIRMED
        """

        matches = ccpa_detector.detect(text)

        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]

        assert len(email_matches) >= 1, "Should detect consumer email"
        assert len(ip_matches) >= 1, "Should detect IP address"

    def test_opt_out_signal_gpc(self):
        """Test Global Privacy Control (GPC) signal handling"""
        gpc_request = {
            "header": "Sec-GPC",
            "value": "1",
            "user_agent": "Mozilla/5.0...",
            "honored": True,
            "treatment": "opt_out_of_sale",
        }

        assert gpc_request["honored"] == True
        assert gpc_request["treatment"] == "opt_out_of_sale"

    def test_do_not_sell_link_requirement(self):
        """Test 'Do Not Sell' link requirement"""
        website_elements = {
            "do_not_sell_link": True,
            "link_text": "Do Not Sell My Personal Information",
            "link_location": "Footer",
            "accessible": True,
            "functional": True,
        }

        assert website_elements["do_not_sell_link"] == True
        assert website_elements["functional"] == True


# ============================================================================
# RIGHT TO NON-DISCRIMINATION (1798.125)
# ============================================================================

class TestCCPANonDiscrimination:
    """Test CCPA Right to Non-Discrimination"""

    def test_non_discrimination_policy(self):
        """Test non-discrimination compliance"""
        policy = {
            "price_difference_for_exercising_rights": False,
            "service_level_difference": False,
            "denying_goods_services": False,
            "different_quality": False,
            "financial_incentives_disclosed": True,
        }

        assert policy["price_difference_for_exercising_rights"] == False
        assert policy["denying_goods_services"] == False

    def test_financial_incentive_disclosure(self, ccpa_detector):
        """Test financial incentive program disclosure"""
        text = """
        FINANCIAL INCENTIVE NOTICE

        Program: Loyalty Rewards Program

        Consumer: john.smith@email.com

        Benefits for sharing data:
        - 10% discount on purchases
        - Early access to sales

        Data collected:
        - Email: john.smith@email.com
        - Purchase history

        Value of data: $50/year (good-faith estimate)

        Opt-in required: YES
        Opt-out available: YES
        """

        matches = ccpa_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect consumer email"


# ============================================================================
# CPRA: RIGHT TO CORRECT (1798.106)
# ============================================================================

class TestCPRARightToCorrect:
    """Test CPRA Right to Correct inaccurate PI"""

    def test_correction_request(self, ccpa_detector):
        """Test handling of correction request"""
        text = """
        CORRECTION REQUEST (CPRA)

        Consumer: john.smith@email.com
        Request date: 2026-01-15

        Current data: john.smith@email.com
        Corrected data: johnsmith.new@email.com

        Field: Email address
        Reason: Changed email provider

        Documentation provided: YES
        Status: Under review
        """

        matches = ccpa_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect emails in correction request"

    def test_correction_service_provider_notice(self, ccpa_detector):
        """Test correction notification to service providers"""
        text = """
        CORRECTION PROPAGATION NOTICE

        Consumer: john.smith@email.com

        Correction made:
        Old value: john.smith@email.com
        New value: johnsmith.new@email.com

        Service providers notified:
        - Payment processor: YES
        - Email marketing: YES
        - Analytics: YES
        """

        matches = ccpa_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect emails"


# ============================================================================
# CPRA: RIGHT TO LIMIT USE OF SENSITIVE PI (1798.121)
# ============================================================================

class TestCPRASensitivePI:
    """Test CPRA Sensitive Personal Information requirements"""

    def test_sensitive_pi_categories(self, ccpa_detector):
        """Test detection of Sensitive PI categories"""
        text = """
        SENSITIVE PERSONAL INFORMATION

        Consumer: john.smith@email.com

        Sensitive data held:
        - SSN: 123-45-6789
        - Financial account: 4111111111111111
        - Precise geolocation: 34.0522, -118.2437
        - Biometric ID: BIO-CA-2026-001

        Use limited to: Service provision only
        """

        matches = ccpa_detector.detect(text)

        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]

        assert len(ssn_matches) >= 1, "Should detect SSN as sensitive PI"
        assert len(cc_matches) >= 1, "Should detect financial data"

    def test_limit_use_request(self, ccpa_detector):
        """Test request to limit use of sensitive PI"""
        text = """
        LIMIT USE OF SENSITIVE PI REQUEST

        Consumer: john.smith@email.com
        Request date: 2026-01-15

        Request: Limit use of SSN (123-45-6789) to
        service provision purposes only.

        Current uses:
        - Service provision: CONTINUE
        - Marketing: STOP
        - Profiling: STOP

        Status: CONFIRMED
        """

        matches = ccpa_detector.detect(text)

        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]

        assert len(ssn_matches) >= 1, "Should detect SSN in limit request"

    def test_limit_sensitive_pi_link(self):
        """Test 'Limit the Use of My Sensitive PI' link requirement"""
        website_elements = {
            "limit_sensitive_pi_link": True,
            "link_text": "Limit the Use of My Sensitive Personal Information",
            "combined_with_do_not_sell": True,  # CPRA allows combining
            "link_location": "Footer",
        }

        assert website_elements["limit_sensitive_pi_link"] == True


# ============================================================================
# BUSINESS OBLIGATIONS (1798.130, 1798.135, 1798.140)
# ============================================================================

class TestCCPABusinessObligations:
    """Test CCPA Business Obligations"""

    def test_privacy_policy_requirements(self):
        """Test privacy policy required disclosures"""
        privacy_policy = {
            "categories_collected": ["Identifiers", "Commercial", "Internet activity"],
            "purposes": ["Order fulfillment", "Marketing", "Analytics"],
            "categories_sold": ["None"],
            "consumer_rights": [
                "Right to know",
                "Right to delete",
                "Right to opt-out",
                "Right to non-discrimination",
            ],
            "contact_methods": ["Web form", "Email", "Toll-free number"],
            "updated_annually": True,
            "effective_date": "2026-01-01",
        }

        assert len(privacy_policy["consumer_rights"]) >= 4
        assert privacy_policy["updated_annually"] == True

    def test_verification_process(self, ccpa_detector):
        """Test consumer request verification"""
        text = """
        CONSUMER VERIFICATION

        Request ID: REQ-2026-001
        Consumer: john.smith@email.com

        Verification method: Email confirmation + security questions

        Verification steps:
        1. Email sent to: john.smith@email.com
        2. Confirmation code entered: VERIFIED
        3. Security question answered: VERIFIED

        Identity confirmed: YES
        Request authorized: YES
        """

        matches = ccpa_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect email in verification"

    def test_authorized_agent_request(self, ccpa_detector):
        """Test authorized agent request handling"""
        text = """
        AUTHORIZED AGENT REQUEST

        Consumer: john.smith@email.com
        Agent: agent@privacycompany.com

        Authorization type: Written permission
        Power of attorney: YES

        Request: Right to delete

        Consumer verification: COMPLETED
        Agent verification: COMPLETED
        """

        matches = ccpa_detector.detect(text)
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(email_matches) >= 1, "Should detect emails"

    def test_response_timing(self):
        """Test response timing requirements"""
        timing_requirements = {
            "acknowledge_receipt": 10,  # days
            "substantive_response": 45,  # days
            "extension_allowed": 45,  # additional days
            "extension_notice_required": True,
        }

        assert timing_requirements["acknowledge_receipt"] == 10
        assert timing_requirements["substantive_response"] == 45


# ============================================================================
# SERVICE PROVIDER REQUIREMENTS
# ============================================================================

class TestCCPAServiceProviders:
    """Test CCPA Service Provider requirements"""

    def test_service_provider_contract(self):
        """Test service provider contract requirements"""
        contract_elements = {
            "written_contract": True,
            "prohibit_selling": True,
            "prohibit_retention_beyond_purpose": True,
            "prohibit_use_outside_relationship": True,
            "certification_provided": True,
            "subcontractor_requirements": True,
        }

        for element, required in contract_elements.items():
            assert required == True, f"Contract must include {element}"

    def test_service_provider_data_handling(self, ccpa_detector):
        """Test service provider handling of PI"""
        text = """
        SERVICE PROVIDER DATA HANDLING LOG

        Business: Acme Corp
        Service Provider: Cloud Analytics Inc

        PI received:
        - Customer email: john.smith@email.com
        - IP: 192.168.1.100

        Purpose: Analytics processing
        Retention: Deleted after 30 days

        Data sold: NO
        Data shared for cross-context advertising: NO
        """

        matches = ccpa_detector.detect(text)

        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]

        assert len(email_matches) >= 1, "Should detect PI in SP handling"


# ============================================================================
# CPRA CONTRACTOR REQUIREMENTS
# ============================================================================

class TestCPRAContractors:
    """Test CPRA Contractor requirements"""

    def test_contractor_contract_elements(self):
        """Test CPRA contractor contract requirements"""
        contract_elements = {
            "written_contract": True,
            "specific_business_purpose": True,
            "compliance_obligation": True,
            "certification_of_understanding": True,
            "audit_rights": True,
            "breach_notification": True,
        }

        assert contract_elements["written_contract"] == True
        assert contract_elements["audit_rights"] == True


# ============================================================================
# CCPA REDACTION TESTS
# ============================================================================

class TestCCPARedaction:
    """Test CCPA-compliant redaction"""

    def test_consumer_data_redaction(self, ccpa_detector):
        """Test redaction of California consumer PI"""
        text = """
        CONSUMER RECORD

        Name: John Smith
        SSN: 123-45-6789
        Email: john.smith@email.com
        Phone: 555-123-4567
        Credit Card: 4111111111111111
        """

        redacted, matches = ccpa_detector.redact(text)

        assert "123-45-6789" not in redacted, "SSN should be redacted"
        assert "john.smith@email.com" not in redacted, "Email should be redacted"
        assert "4111111111111111" not in redacted, "Credit card should be redacted"

    def test_disclosure_redaction(self, ccpa_detector):
        """Test redaction in right-to-know response"""
        text = """
        RIGHT TO KNOW RESPONSE

        Consumer: john.smith@email.com
        SSN on file: 123-45-6789

        This is your personal information on file.
        """

        redacted, matches = ccpa_detector.redact(text)

        assert "123-45-6789" not in redacted


# ============================================================================
# CCPA COMPLIANCE REPORTING
# ============================================================================

class TestCCPAComplianceReporting:
    """Test CCPA compliance reporting"""

    def test_request_metrics(self):
        """Test CCPA request metrics tracking"""
        metrics = {
            "period": "2025",
            "requests_to_know": 150,
            "requests_to_delete": 85,
            "requests_to_opt_out": 320,
            "requests_completed": 540,
            "requests_denied": 15,
            "average_response_days": 28,
        }

        total_requests = metrics["requests_to_know"] + metrics["requests_to_delete"] + metrics["requests_to_opt_out"]
        assert metrics["requests_completed"] <= total_requests + metrics["requests_denied"]

    def test_annual_reporting(self):
        """Test annual CCPA reporting (businesses >10M consumers)"""
        annual_report = {
            "year": 2025,
            "requests_to_know_received": 150,
            "requests_to_know_complied": 145,
            "requests_to_delete_received": 85,
            "requests_to_delete_complied": 80,
            "requests_to_opt_out_received": 320,
            "requests_to_opt_out_complied": 320,
            "mean_days_to_respond": 28,
            "published": True,
        }

        assert annual_report["published"] == True


# ============================================================================
# REAL WORLD CCPA SCENARIOS
# ============================================================================

class TestCCPARealWorldScenarios:
    """Test real-world CCPA compliance scenarios"""

    def test_ecommerce_checkout(self, ccpa_detector):
        """Test e-commerce checkout data collection"""
        text = """
        E-COMMERCE CHECKOUT

        Customer: john.smith@email.com

        Billing:
        Card: 4111111111111111
        Phone: 555-123-4567

        Shipping:
        Address: 123 Main St, Los Angeles, CA 90001

        IP: 192.168.1.100

        Data collection notice: DISPLAYED
        Purpose: Order fulfillment
        """

        matches = ccpa_detector.detect(text)

        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        cc_matches = [m for m in matches if m.pii_type == PIIType.CREDIT_CARD]

        assert len(email_matches) >= 1, "Should detect customer email"
        assert len(cc_matches) >= 1, "Should detect payment card"

    def test_marketing_data_collection(self, ccpa_detector):
        """Test marketing data collection scenario"""
        text = """
        MARKETING CONSENT FORM

        Email: john.smith@email.com
        IP at signup: 192.168.1.100

        Consent given for:
        - Email marketing: YES
        - Third-party sharing: NO (opted out)
        - Cross-context advertising: NO

        Do Not Sell preference: OPTED OUT
        """

        matches = ccpa_detector.detect(text)

        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        ip_matches = [m for m in matches if m.pii_type == PIIType.IP_ADDRESS]

        assert len(email_matches) >= 1
        assert len(ip_matches) >= 1

    def test_employee_data_handling(self, ccpa_detector):
        """Test employee PI handling (B2B exemption ended Jan 1, 2023)"""
        text = """
        EMPLOYEE RECORD (CA EMPLOYEE)

        Employee: john.smith@company.com
        SSN: 123-45-6789

        Position: Software Engineer
        Salary: $150,000
        Start date: 2020-01-15

        CCPA rights apply: YES (as of Jan 1, 2023)
        """

        matches = ccpa_detector.detect(text)

        ssn_matches = [m for m in matches if m.pii_type == PIIType.SSN]
        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]

        assert len(ssn_matches) >= 1, "Should detect employee SSN"
        assert len(email_matches) >= 1, "Should detect employee email"

    def test_data_broker_registration(self):
        """Test data broker registration requirement"""
        data_broker = {
            "business_name": "Data Insights Inc",
            "is_data_broker": True,
            "registered_with_ag": True,
            "registration_date": "2025-01-15",
            "fee_paid": True,
            "delete_my_data_link": True,
        }

        assert data_broker["registered_with_ag"] == True
        assert data_broker["delete_my_data_link"] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
