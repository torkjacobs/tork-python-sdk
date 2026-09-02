"""Parity tests for SDK-PYTHON-PII-DETECTOR-DROPS-THREE-DECLARED-TYPES and
SDK-PYTHON-REGIONAL-DETECTOR-DECLARES-FIVE-TYPES-WITH-NO-PATTERN.

core.py declared 10 PIIType values but PII_PATTERNS only had regexes for 7
of them -- passport, drivers_license, and bank_account passed through
govern() and scan_tool_result() unflagged and unmasked. Separately,
detectors/pii_patterns.py (the "regional" detector, the runtime default
since 0.26.0) declared 5 PIIType values -- address, name, phone_generic,
ssn_no_dashes, url_with_pii -- with no pattern in any of its per-region
dicts at all. Both are the same class of bug: an enum member that looks
like a supported type but silently never fires. This file pins down, for
*both* detectors, that it can't happen silently again:

  1. Every basic PIIType has a PII_PATTERNS entry (TestEveryPIITypeHasAPattern).
  2. Every regional PIIType has an entry in one of the per-region pattern
     dicts (TestEveryRegionalPIITypeHasAPattern) -- no exceptions list. name
     and address were removed from the regional enum (free text needs an
     NER model, not a regex); ssn_no_dashes was removed because the
     existing `ssn` pattern's separators are already optional and so already
     matches unformatted 9-digit input under the `ssn` label -- a second
     type for the same span doesn't just duplicate the label, it corrupts
     PIIDetector.redact()'s reversed-replacement algorithm, which assumes
     matches don't share a span (verified: two same-span matches from
     regions=['all'] already do this today for ssn/tfn on rare colliding
     checksums -- see test_redact_does_not_yet_support_same_span_matches
     below). phone_generic and url_with_pii got real keyword-gated patterns,
     the same style already used for bank_account/mrn/patient_id.
  3. Fixtures ported from tork-js-sdk's detectPII test suite (core.test.ts /
     index.test.ts) produce the same type label here as they do there. The
     JS suite only exercises 6 of the 10 types with detectPII() calls (ssn,
     email, credit_card, phone, ip_address, date_of_birth); it never calls
     detectPII with address/passport/drivers_license/bank_account fixtures,
     so those four are built from the ported regex sources themselves
     (PII_PATTERNS in tork-js-sdk/src/pii.ts), keeping the same
     one-fixture-one-type-label shape as the six JS-native ones.
"""

from tork_governance.core import PII_PATTERNS, PIIType, detect_pii
from tork_governance.detectors.pii_patterns import (
    AU_PATTERNS,
    BIOMETRIC_PATTERNS,
    EU_PATTERNS,
    FINANCIAL_PATTERNS,
    HEALTHCARE_PATTERNS,
    PIIDetector as RegionalPIIDetector,
    PIIType as RegionalPIIType,
    UK_PATTERNS,
    UNIVERSAL_PATTERNS,
    US_PATTERNS,
)

REGIONAL_PATTERN_DICTS = [
    US_PATTERNS,
    AU_PATTERNS,
    EU_PATTERNS,
    UK_PATTERNS,
    UNIVERSAL_PATTERNS,
    FINANCIAL_PATTERNS,
    HEALTHCARE_PATTERNS,
    BIOMETRIC_PATTERNS,
]

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


class TestEveryRegionalPIITypeHasAPattern:
    """Same coverage guarantee as TestEveryPIITypeHasAPattern above, but for
    the regional detector (detectors/pii_patterns.py) -- the runtime default
    since 0.26.0. No exceptions list: every RegionalPIIType must have a
    pattern in one of the per-region dicts."""

    def test_regional_patterns_cover_every_declared_type(self):
        all_patterns = {}
        for patterns in REGIONAL_PATTERN_DICTS:
            all_patterns.update(patterns)
        assert set(all_patterns.keys()) == set(RegionalPIIType)

    def test_forty_four_types_declared(self):
        assert len(list(RegionalPIIType)) == 44

    def test_get_supported_types_matches_declared_count(self):
        detector = RegionalPIIDetector(regions=["all"])
        assert len(detector.get_supported_types()) == len(list(RegionalPIIType))


class TestRedactAssumesNonOverlappingMatches:
    """Documents an existing limitation of PIIDetector.redact(): its
    reversed-replacement loop assumes matches don't share a span. When two
    types match the identical (start, end) -- e.g. a bare 9-digit number
    that happens to pass both the `ssn` and `tfn` checksums -- the second
    replacement slices into text already mutated by the first, corrupting
    the output. This is why ssn_no_dashes was removed rather than added: its
    pattern would have matched the exact same span as `ssn` on every
    unformatted SSN (ssn's separators are already optional), turning this
    from a rare checksum coincidence into a routine occurrence."""

    def test_same_span_double_match_corrupts_redaction(self):
        detector = RegionalPIIDetector(regions=["all"])
        text = "Number: 100010006 end"

        matches = detector.detect(text)
        types_at_same_span = {
            (m.start, m.end): [mm.pii_type for mm in matches if mm.start == m.start and mm.end == m.end]
            for m in matches
        }
        assert any(len(v) >= 2 for v in types_at_same_span.values()), (
            "expected this fixture to still produce a same-span double match; "
            "if it no longer does, the fixture (not the assumption) needs updating"
        )

        redacted, _ = detector.redact(text)
        assert "100010006" not in redacted
        # Known-bad output: the second redaction slices into text already
        # shortened/lengthened by the first, so the result is garbled rather
        # than a single clean redaction marker.
        assert redacted != "Number: [SSN_REDACTED] end"
