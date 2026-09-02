"""Parity tests for SDK-PYTHON-PII-DETECTOR-DROPS-THREE-DECLARED-TYPES.

core.py declared 10 PIIType values but PII_PATTERNS only had regexes for 7
of them -- passport, drivers_license, and bank_account passed through
govern() and scan_tool_result() unflagged and unmasked. This file pins two
things down so that regression can't happen silently again:

  1. Every PIIType has a PII_PATTERNS entry.
  2. Fixtures ported from tork-js-sdk's detectPII test suite (core.test.ts /
     index.test.ts) produce the same type label here as they do there. The
     JS suite only exercises 6 of the 10 types with detectPII() calls (ssn,
     email, credit_card, phone, ip_address, date_of_birth); it never calls
     detectPII with address/passport/drivers_license/bank_account fixtures,
     so those four are built from the ported regex sources themselves
     (PII_PATTERNS in tork-js-sdk/src/pii.ts), keeping the same
     one-fixture-one-type-label shape as the six JS-native ones.
"""

from tork_governance.core import PII_PATTERNS, PIIType, detect_pii

# (text, expected type label) -- text chosen so exactly one PIIType fires,
# matching the containment-style assertions (`toContain`) the JS suite uses.
JS_PARITY_FIXTURES = [
    ("My SSN is 123-45-6789", "ssn"),
    ("Contact me at john@example.com", "email"),
    ("Card: 4111-1111-1111-1111", "credit_card"),
    ("Call me at 555-123-4567", "phone"),
    ("Server IP: 192.168.1.1", "ip_address"),
    ("DOB: 01/15/1990", "date_of_birth"),
    ("I live at 123 Main Street", "address"),
    ("Passport AB1234567", "passport"),
    ("License A1234567890", "drivers_license"),
    ("Account number: 123456789012", "bank_account"),
]


class TestEveryPIITypeHasAPattern:
    def test_pii_patterns_covers_every_declared_type(self):
        assert set(PII_PATTERNS.keys()) == set(PIIType)

    def test_ten_types_declared(self):
        assert len(list(PIIType)) == 10


class TestJSFixtureParity:
    def test_all_ten_fixtures_present(self):
        assert len(JS_PARITY_FIXTURES) == 10
        assert {expected for _, expected in JS_PARITY_FIXTURES} == {t.value for t in PIIType}

    def test_fixtures_produce_the_same_type_label_as_the_js_suite(self):
        for text, expected_type in JS_PARITY_FIXTURES:
            result = detect_pii(text)
            types = [t.value for t in result.types]
            assert expected_type in types, (
                f"detect_pii({text!r}) -> {types}, expected {expected_type!r} "
                f"(JS detectPII parity)"
            )
