"""Tests for TORK-DNA-v2 canonical form + salted fingerprinting.

These pin the Python port to lib/governance/dna-fingerprint.ts in the
tork.network landing repo: same canonical shape, same hashing scheme.
"""

import json

from tork_governance.core import (
    build_canonical,
    canonical_json,
    classify_risk,
    compute_salted_fingerprint,
    compute_score,
    derive_policies,
    generate_fingerprint_salt,
)


class TestKnownGoodVector:
    """A vector computed independently and ACCEPTED by production."""

    CANONICAL = {
        "hitl": False,
        "pii": ["email"],
        "policies": ["pii-redact", "rate-limit"],
        "risk": "low",
        "score": 100,
        "ts": 1785700000,
        "v": "1.0.0",
    }
    SALT = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
    EXPECTED_FINGERPRINT = "TORK-DNA-v2-cb8605eed6b4878f"

    def test_reproduces_known_fingerprint(self):
        cj = canonical_json(self.CANONICAL)
        fingerprint = compute_salted_fingerprint(cj, self.SALT)
        assert fingerprint == self.EXPECTED_FINGERPRINT

    def test_build_canonical_reproduces_the_same_shape(self):
        canonical = build_canonical(
            policy_version="1.0.0",
            verdict="redact",
            pii_types=["email"],
            pii_count=1,
            hitl=False,
            ts=1785700000,
        )
        assert canonical == self.CANONICAL

    def test_end_to_end_from_build_canonical(self):
        canonical = build_canonical(
            policy_version="1.0.0",
            verdict="redact",
            pii_types=["email"],
            pii_count=1,
            hitl=False,
            ts=1785700000,
        )
        cj = canonical_json(canonical)
        fingerprint = compute_salted_fingerprint(cj, self.SALT)
        assert fingerprint == self.EXPECTED_FINGERPRINT


class TestCanonicalJsonEncoding:
    def test_no_whitespace(self):
        canonical = build_canonical("1.0.0", "allow", [], 0, False, 1785700000)
        cj = canonical_json(canonical)
        assert " " not in cj
        assert "\n" not in cj
        assert "\t" not in cj

    def test_keys_sorted_alphabetically(self):
        canonical = build_canonical("1.0.0", "redact", ["email", "ssn"], 2, True, 1785700000)
        cj = canonical_json(canonical)
        parsed_order = list(json.loads(cj).keys())
        assert parsed_order == sorted(parsed_order)
        # Also check the literal string has keys appearing in sorted order.
        keys_in_string_order = sorted(canonical.keys())
        assert cj.startswith(f'{{"{keys_in_string_order[0]}"')

    def test_booleans_lowercase(self):
        canonical = build_canonical("1.0.0", "allow", [], 0, True, 1785700000)
        cj = canonical_json(canonical)
        assert '"hitl":true' in cj
        assert "True" not in cj
        assert "False" not in cj

    def test_absent_autonomy_level_is_omitted_not_null(self):
        canonical = build_canonical("1.0.0", "allow", [], 0, False, 1785700000)
        assert "autonomy_level" not in canonical
        cj = canonical_json(canonical)
        assert "autonomy_level" not in cj
        assert "null" not in cj

    def test_present_autonomy_level_is_included(self):
        canonical = build_canonical(
            "1.0.0", "allow", [], 0, False, 1785700000, autonomy_level=4
        )
        assert canonical["autonomy_level"] == 4
        cj = canonical_json(canonical)
        assert '"autonomy_level":4' in cj

    def test_score_is_integer_no_decimal_point(self):
        canonical = build_canonical("1.0.0", "redact", ["email"], 1, False, 1785700000)
        cj = canonical_json(canonical)
        assert '"score":100' in cj
        assert '"score":100.0' not in cj


class TestClassifyRisk:
    def test_deny_is_always_critical(self):
        assert classify_risk([], "deny") == "critical"
        assert classify_risk(["email"], "deny") == "critical"

    def test_no_pii_is_none(self):
        assert classify_risk([], "allow") == "none"

    def test_high_risk_pii(self):
        assert classify_risk(["ssn"], "redact") == "high"
        assert classify_risk(["credit_card"], "redact") == "high"

    def test_medium_risk_pii(self):
        assert classify_risk(["us_drivers_license"], "redact") == "medium"

    def test_low_risk_pii_by_default(self):
        assert classify_risk(["email"], "redact") == "low"
        assert classify_risk(["phone"], "redact") == "low"


class TestDerivePolicies:
    def test_redact_with_pii(self):
        assert derive_policies("redact", ["email"]) == ["pii-redact", "rate-limit"]

    def test_deny_with_pii(self):
        assert derive_policies("deny", ["ssn"]) == ["pii-deny", "rate-limit"]

    def test_allow_or_flag_with_pii_uses_detect(self):
        assert derive_policies("allow", ["email"]) == ["pii-detect", "rate-limit"]
        assert derive_policies("flag", ["email"]) == ["pii-detect", "rate-limit"]

    def test_no_pii_only_rate_limit(self):
        assert derive_policies("allow", []) == ["rate-limit"]


class TestComputeScore:
    def test_perfect_allow_no_pii(self):
        assert compute_score([], 0, "allow") == 100

    def test_redact_recovers_points_vs_deny(self):
        redact_score = compute_score(["email"], 1, "redact")
        deny_score = compute_score(["email"], 1, "deny")
        assert redact_score > deny_score

    def test_score_bounded_0_to_100(self):
        score = compute_score(["ssn", "credit_card"], 50, "deny", autonomy_level=5)
        assert 0 <= score <= 100


class TestFingerprintSalt:
    def test_salt_is_32_lowercase_hex_chars(self):
        salt = generate_fingerprint_salt()
        assert len(salt) == 32
        assert salt == salt.lower()
        int(salt, 16)  # raises if not valid hex

    def test_salts_are_random(self):
        salts = {generate_fingerprint_salt() for _ in range(20)}
        assert len(salts) == 20
