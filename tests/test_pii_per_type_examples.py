"""Per-type detection tests (SDK-DECLARED-PII-TYPES-WITHOUT-PATTERNS).

test_pii_type_parity.py asserts every declared type has a pattern entry.
This file asserts the pattern actually *works*: every type either detector
declares has one positive example it must flag and one negative example it
must not, so a pattern that exists but never fires (or fires on anything)
fails here. The case tables are checked against the enums, so adding a type
without a case fails too.
"""

import pytest

from tork_governance.core import PIIType, detect_pii
from tork_governance.detectors.pii_patterns import PIIDetector
from tork_governance.detectors.pii_patterns import PIIType as RegionalPIIType

BASIC_CASES = {
 "ssn": ("My SSN is 123-45-6789", "Order ref 12-345-67890"),
 "credit_card": ("Card: 4111-1111-1111-1111", "Card: 4111-1111-111"),
 "email": ("Contact john@example.com", "Contact john at example dot com"),
 "phone": ("Call me at 555-123-4567", "Call me at 555-1234"),
 "address": ("I live at 123 Main Street", "I live on Main Street"),
 "ip_address": ("Server IP: 192.168.1.1", "Version 1.2.3"),
 "date_of_birth": ("DOB: 01/15/1990", "Meeting on 13/45/1990"),
 "passport": ("Passport AB1234567", "Passport"),
 "drivers_license": ("License A1234567890", "License to operate"),
 "bank_account": ("Account number: 123456789012", "Account number: 123"),
}
REGIONAL_CASES = {
 "ssn": ("My SSN is 123-45-6789", "My SSN is 000-45-6789"),
 "phone_us": ("Call (415) 555-2671", "Call (115) 555-2671"),
 "driver_license_us": ("Driver License: D1234567", "Driver License"),
 "passport_us": ("Passport: 123456789", "Passport: 12"),
 "ein": ("EIN: 12-3456789", "EIN: 12"),
 "itin": ("ITIN 912-70-1234", "ITIN 812-70-1234"),
 "phone_au": ("Mobile 0412 345 678", "Mobile 0112 345 678"),
 "medicare_au": ("Medicare 2123 45670 1", "Medicare 1123 45670 1"),
 "tfn": ("TFN 123 456 782", "TFN 123 456 780"),
 "abn": ("ABN 51 824 753 556", "ABN 51 824 753 557"),
 "acn": ("ACN 000 000 019", "ACN 12"),
 "iban": ("IBAN GB82 WEST 1234 5698 7654 32", "IBAN GB82 WEST 1234 5698 7654 33"),
 "vat_eu": ("VAT DE123456789", "VAT"),
 "phone_eu": ("Phone +49 30 1234 5678", "Phone 12"),
 "german_id": ("ID T220001293", "ID ABC"),
 "french_ssn": ("INSEE 2 69 05 49 588 157 80", "INSEE 2 69 05"),
 "nino_uk": ("NINO AB 12 34 56 C", "NINO DQ 12 34 56 C"),
 "nhs_uk": ("NHS 943 476 5919", "NHS 943 476 5918"),
 "postcode_uk": ("Postcode SW1A 1AA", "Postcode 1234"),
 "sort_code_uk": ("Sort code 20-00-00", "Sort code 20"),
 "email": ("Contact john@example.com", "Contact john at example"),
 "credit_card": ("Card 4111 1111 1111 1111", "Card 4111 1111 1111 1112"),
 "ip_address": ("Server 192.168.1.1", "Server 999.999.1.1"),
 "ipv6_address": ("IPv6 2001:0db8:85a3:0000:0000:8a2e:0370:7334", "IPv6 2001:0db8:85a3"),
 "mac_address": ("MAC 00:1A:2B:3C:4D:5E", "MAC 00:1A:2B"),
 "url_with_pii": ("See https://x.com/a?email=a@b.com", "See https://x.com/a?page=2"),
 "date_of_birth": ("DOB: 01/15/1990", "Date 01/15/1990"),
 "phone_generic": ("Phone: +1 202 555 0143", "Phone"),
 "bank_account": ("Account Number: 123456789012", "Account Number: 123"),
 "routing_number": ("Routing Number: 021000021", "Routing Number: 021000022"),
 "swift_bic": ("SWIFT DEUTDEFF", "SWIFT 12"),
 "cvv": ("CVV: 123", "CVV"),
 "card_expiry": ("Exp: 12/26", "Exp"),
 "crypto_address": ("BTC 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2", "BTC 1234"),
 "patient_id": ("Patient ID: P123456", "Patient ID"),
 "mrn": ("MRN: 12345678", "MRN: 12"),
 "health_plan_id": ("Member ID: ABC123456789", "Member"),
 "npi": ("NPI: 1234567893", "NPI: 1234567890"),
 "dea_number": ("DEA: AB1234563", "DEA: AB1234560"),
 "icd_code": ("ICD-10: E11.9", "ICD-10"),
 "cpt_code": ("CPT: 99213", "CPT: 12"),
 "biometric_id": ("Biometric ID: BIO-12345", "Biometric"),
 "face_id": ("Face ID: FACE-12345", "Face"),
 "fingerprint_id": ("Fingerprint ID: FP-12345", "Fingerprint"),
}


class TestBasicDetectorPerType:
    def test_cases_cover_every_declared_type(self):
        assert set(BASIC_CASES) == {t.value for t in PIIType}

    @pytest.mark.parametrize("pii_type", sorted(BASIC_CASES))
    def test_positive_example_is_detected(self, pii_type):
        positive, _ = BASIC_CASES[pii_type]
        assert pii_type in [t.value for t in detect_pii(positive).types]

    @pytest.mark.parametrize("pii_type", sorted(BASIC_CASES))
    def test_negative_example_is_not_detected(self, pii_type):
        _, negative = BASIC_CASES[pii_type]
        assert pii_type not in [t.value for t in detect_pii(negative).types]


class TestRegionalDetectorPerType:
    detector = PIIDetector(regions=["all"])

    def test_cases_cover_every_declared_type(self):
        assert set(REGIONAL_CASES) == {t.value for t in RegionalPIIType}

    @pytest.mark.parametrize("pii_type", sorted(REGIONAL_CASES))
    def test_positive_example_is_detected(self, pii_type):
        positive, _ = REGIONAL_CASES[pii_type]
        assert pii_type in [m.pii_type.value for m in self.detector.detect(positive)]

    @pytest.mark.parametrize("pii_type", sorted(REGIONAL_CASES))
    def test_negative_example_is_not_detected(self, pii_type):
        _, negative = REGIONAL_CASES[pii_type]
        assert pii_type not in [m.pii_type.value for m in self.detector.detect(negative)]
