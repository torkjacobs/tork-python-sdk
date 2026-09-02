"""README's regional PII type table (DECIDED-SDK-REGIONAL-DETECTOR-IS-THE-
RUNTIME-PATH) must be generated from the live detector, not hand-typed --
this test regenerates it the same way and fails if the README has drifted
from what PIIDetector(regions=['all']) actually supports."""

import pathlib

from tork_governance.detectors.pii_patterns import (
    AU_PATTERNS,
    BIOMETRIC_PATTERNS,
    EU_PATTERNS,
    FINANCIAL_PATTERNS,
    HEALTHCARE_PATTERNS,
    PIIDetector,
    UK_PATTERNS,
    UNIVERSAL_PATTERNS,
    US_PATTERNS,
)

README_PATH = pathlib.Path(__file__).resolve().parent.parent / "README.md"

CATEGORIES = [
    ("US", US_PATTERNS),
    ("Australia", AU_PATTERNS),
    ("EU", EU_PATTERNS),
    ("UK", UK_PATTERNS),
    ("Universal", UNIVERSAL_PATTERNS),
    ("Financial", FINANCIAL_PATTERNS),
    ("Healthcare", HEALTHCARE_PATTERNS),
    ("Biometric", BIOMETRIC_PATTERNS),
]


def _expected_rows():
    rows = []
    for label, patterns in CATEGORIES:
        types = sorted(t.value for t in patterns.keys())
        type_list = ", ".join(f"`{t}`" for t in types)
        rows.append(f"| **{label}** ({len(types)}) | {type_list} |")
    return rows


class TestReadmePIITypeListIsGenerated:
    def test_all_regions_type_count_matches_the_documented_total(self):
        detector = PIIDetector(regions=["all"])
        assert len(detector.get_supported_types()) == 42

    def test_readme_table_matches_the_live_detector(self):
        content = README_PATH.read_text()
        for row in _expected_rows():
            assert row in content, f"README.md PII type table is stale, expected row: {row}"
