"""Tests for DECIDED-SDK-REGIONAL-DETECTOR-IS-THE-RUNTIME-PATH.

detectors/pii_patterns.py (50+ region-aware, checksum-validated PII types)
used to be exercised only by its own direct tests (test_pii_us.py,
test_pii_au.py, ...). This file pins the decision that it is now the
default detector behind Tork.govern() / Tork.scan_tool_result(), with an
opt-out back to the original 10-type detector via TorkConfig.detector /
the constructor's `detector=` kwarg / the TORK_PII_DETECTOR env var.
"""

import os

import pytest

import tork_governance.core as core
from tork_governance.core import GovernanceAction, Tork, TorkConfig, detect_pii

# Known checksum-VALID fixtures (reused from test_pii_eu_uk.py / test_pii_au.py,
# which already prove these pass their respective checksums).
VALID_IBAN = "DE89370400440532013000"
VALID_TFN = "123 456 782"
VALID_NHS = "943 476 5919"

# Known checksum-FAILING lookalikes (same source files) -- right shape,
# wrong checksum.
INVALID_IBAN = "DE00000000000000000000"
INVALID_TFN = "123 456 789"
INVALID_NHS = "123 456 7890"


class TestRegionalIsTheDefault:
    """Types the basic 10-type detector structurally cannot label (no
    PIIType.IBAN / .TFN / .NHS_UK exists) that the default (regional)
    detector catches, checksum-validated."""

    def test_default_tork_catches_an_iban_the_basic_detector_misses(self):
        tork = Tork()
        result = tork.govern(f"Bank Account: {VALID_IBAN}")
        assert "iban" in result.pii.types
        assert "[IBAN_REDACTED]" in result.output

        basic = detect_pii(f"Bank Account: {VALID_IBAN}")
        assert basic.has_pii is False

    def test_default_tork_catches_an_au_tfn_the_basic_detector_misses(self):
        tork = Tork()
        result = tork.govern(f"TFN: {VALID_TFN}")
        assert "tfn" in result.pii.types
        assert "[TFN_REDACTED]" in result.output

        basic = detect_pii(f"TFN: {VALID_TFN}")
        assert basic.has_pii is False

    def test_default_tork_catches_a_uk_nhs_number_the_basic_detector_misses(self):
        tork = Tork()
        result = tork.govern(f"NHS Number: {VALID_NHS}")
        assert "nhs_uk" in result.pii.types
        assert "[NHS_REDACTED]" in result.output

        # The basic detector has no NHS type at all -- it structurally
        # cannot produce "nhs_uk" (it may still flag the same digits as a
        # "phone" false-classification, since 3-3-4 grouping happens to
        # match the basic phone pattern too, but never with NHS's identity
        # or its checksum guarantee).
        basic = detect_pii(f"NHS Number: {VALID_NHS}")
        assert "nhs_uk" not in [str(t) for t in basic.types]

    def test_govern_default_config_resolves_to_regional(self):
        assert Tork().config.detector == "regional"
        assert TorkConfig().detector == "regional"


class TestChecksumFailingLookalikesAreNotFlagged:
    """No false positives from the switch: a lookalike that fails its
    type's checksum must not be flagged as that type, by either the raw
    regional detector or Tork.govern()."""

    def test_iban_with_invalid_checksum_is_not_flagged(self):
        result = Tork().govern(f"Bank Account: {INVALID_IBAN}")
        assert "iban" not in result.pii.types

    def test_tfn_with_invalid_checksum_is_not_flagged(self):
        result = Tork().govern(f"TFN: {INVALID_TFN}")
        assert "tfn" not in result.pii.types

    def test_nhs_with_invalid_checksum_is_not_flagged(self):
        result = Tork().govern(f"NHS Number: {INVALID_NHS}")
        assert "nhs_uk" not in result.pii.types


class TestBasicFlagRestoresBasicBehaviorExactly:
    """detector="basic" (constructor kwarg, TorkConfig.detector, or the
    TORK_PII_DETECTOR env var) must reproduce the original 10-type
    detector's output byte-for-byte -- same types, same redacted text."""

    FIXTURES = [
        "My SSN is 123-45-6789",
        "Contact me at john@example.com",
        "Card: 4111-1111-1111-1111",
        "Call me at 555-123-4567",
        "Server IP: 192.168.1.1",
        "DOB: 01/15/1990",
        f"Bank Account: {VALID_IBAN}",  # regional-only type; basic sees nothing
        "Hello, this is a safe message.",
    ]

    def _assert_matches_standalone_basic(self, result_pii):
        for text in self.FIXTURES:
            expected = detect_pii(text)
            assert result_pii(text).redacted_text == expected.redacted_text
            assert sorted(str(t) for t in result_pii(text).types) == sorted(
                str(t) for t in expected.types
            )

    def test_constructor_kwarg_detector_basic(self):
        tork = Tork(detector="basic")
        assert tork.config.detector == "basic"
        self._assert_matches_standalone_basic(lambda text: tork.govern(text).pii)

    def test_torkconfig_detector_basic(self):
        tork = Tork(config=TorkConfig(detector="basic"))
        assert tork.config.detector == "basic"
        self._assert_matches_standalone_basic(lambda text: tork.govern(text).pii)

    def test_env_var_restores_basic(self, monkeypatch):
        monkeypatch.setenv("TORK_PII_DETECTOR", "basic")
        tork = Tork()
        assert tork.config.detector == "basic"
        self._assert_matches_standalone_basic(lambda text: tork.govern(text).pii)

    def test_constructor_kwarg_wins_over_env_var(self, monkeypatch):
        monkeypatch.setenv("TORK_PII_DETECTOR", "basic")
        tork = Tork(detector="regional")
        assert tork.config.detector == "regional"

    def test_unknown_detector_name_raises(self):
        with pytest.raises(ValueError):
            Tork(detector="nope")

    def test_unknown_detector_env_var_raises(self, monkeypatch):
        monkeypatch.setenv("TORK_PII_DETECTOR", "nope")
        with pytest.raises(ValueError):
            Tork()

    def test_basic_flag_also_applies_to_scan_tool_result(self):
        tork = Tork(detector="basic")
        result = tork.scan_tool_result("lookup", {"text": f"Bank Account: {VALID_IBAN}"})
        # basic detector has no IBAN type -- scan_tool_result must not
        # invent one just because detector="regional" would have.
        assert result.findings == []
        assert result.sanitized == {"text": f"Bank Account: {VALID_IBAN}"}

    def test_default_scan_tool_result_uses_regional(self):
        tork = Tork()
        result = tork.scan_tool_result("lookup", {"text": f"Bank Account: {VALID_IBAN}"})
        assert [(f.kind, f.type) for f in result.findings] == [("pii", "iban")]
        assert result.sanitized == {"text": "Bank Account: [IBAN_REDACTED]"}


class TestZeroNetworkCallsFromEitherDetector:
    def test_regional_detector_never_touches_urlopen(self, monkeypatch):
        def _fail(*args, **kwargs):
            raise AssertionError("PII detection must never make a network call")

        monkeypatch.setattr(core.urllib.request, "urlopen", _fail)

        tork = Tork()  # no api_key -- regional detector, fully local
        tork.govern(f"IBAN {VALID_IBAN}, TFN {VALID_TFN}, NHS {VALID_NHS}")
        tork.scan_tool_result("t", {"text": f"IBAN {VALID_IBAN}"})

        basic_tork = Tork(detector="basic")
        basic_tork.govern("My SSN is 123-45-6789")
