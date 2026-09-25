"""
Country-layer parity tests.

The fixtures are generated from the cloud's own evidence, not written here:

  pii_unit_cases.json  one valid sample per registry pattern, a checksum-broken
                       variant for each pattern whose checksum is a gate, and
                       the Indonesian boundary cases.
  pii_vectors.json     all 2,092 inputs of the cloud's golden snapshot: every
                       country-corpus sentence for all 249 ISO jurisdictions,
                       and the whole 1,523-line business false-positive corpus.

``expectedOutput`` is the COUNTRY LAYER alone. Where the cloud's own output
differs, the case carries ``cloudOutput`` and a ``divergence`` naming the
cause, so the fixture states its distance from the cloud instead of hiding it.
There are exactly two causes and this suite asserts there are no others.
"""

import json
import re
from pathlib import Path

import pytest

from tork_governance.detectors.pii_checksums import CHECKSUM_FUNCTIONS
from tork_governance.detectors.pii_country import (
    CONTEXT_WINDOW,
    KEYWORD_WINDOW_AFTER,
    KEYWORD_WINDOW_BEFORE,
    TORK_PII_CONTENT_HASH,
    TORK_PII_REGISTRY_VERSION,
    apply_redactions,
    detect_country_pii,
    detect_country_pii_with_ranges,
    has_whole_word_context_around,
    infer_regions,
    labelled_as_reference,
    table_scopes,
)
from tork_governance.detectors.pii_registry import (
    TORK_PII_COUNTRIES,
    TORK_PII_PATTERNS,
    TORK_PII_SIGNALS,
)

FIXTURES = Path(__file__).parent / "fixtures"
UNIT = json.loads((FIXTURES / "pii_unit_cases.json").read_text())
V = json.loads((FIXTURES / "pii_vectors.json").read_text())
CASES = V["cases"]
BY_NAME = {p["name"]: p for p in TORK_PII_PATTERNS}

CORPUS = [c for c in CASES if c["kind"] != "business-fp"]
BUSINESS = [c for c in CASES if c["kind"] == "business-fp"]


# ── the bundle ───────────────────────────────────────────────────────────────

def test_is_the_version_and_content_the_fixtures_were_generated_from():
    assert TORK_PII_REGISTRY_VERSION == V["bundleVersion"]
    assert TORK_PII_CONTENT_HASH == V["contentHash"]


def test_carries_54_patterns_across_24_profiles_with_51_signals():
    assert len(TORK_PII_PATTERNS) == 54
    assert len(TORK_PII_COUNTRIES) == 24
    assert len(TORK_PII_SIGNALS) == 51


def test_au_tfn_abn_medicare_are_always_on_since_1_2_0():
    always_on = {p["name"] for p in TORK_PII_PATTERNS if p.get("always_on")}
    assert always_on == {"au_tfn", "au_abn", "au_medicare"}


def test_covers_indonesia_added_in_1_1_0():
    ind = next((c for c in TORK_PII_COUNTRIES if c["code"] == "ID"), None)
    assert ind is not None, "Indonesia is missing from the bundle"
    assert "id_nik" in ind["patterns"]
    nik = BY_NAME["id_nik"]
    assert nik["label"] == "NIK"
    assert "nik" in nik["whole_word_keywords"]


def test_reads_its_windows_from_the_bundle_and_they_are_not_all_the_same():
    assert KEYWORD_WINDOW_BEFORE == 60
    assert KEYWORD_WINDOW_AFTER == 40
    assert CONTEXT_WINDOW == 60
    assert KEYWORD_WINDOW_AFTER != KEYWORD_WINDOW_BEFORE


def test_names_a_checksum_function_for_every_pattern_that_declares_one():
    for p in TORK_PII_PATTERNS:
        if p["checksum"]:
            assert callable(CHECKSUM_FUNCTIONS.get(p["checksum"])), f"{p['name']} -> {p['checksum']}"


@pytest.mark.parametrize("source", [p["regex"] for p in TORK_PII_PATTERNS] + [s["regex"] for s in TORK_PII_SIGNALS])
def test_uses_only_the_portable_regex_subset(source):
    for bad, why in [(r"\(\?=", "lookahead"), (r"\(\?!", "negative lookahead"),
                     (r"\(\?<[=!]", "lookbehind"), (r"\\[1-9]", "backreference"),
                     (r"\\[pP]\{", "unicode property escape"), (r"\(\?>", "atomic group")]:
        assert not re.search(bad, source), f"{source} uses {why}"


# ── per-pattern unit cases ───────────────────────────────────────────────────

@pytest.mark.parametrize("case", UNIT, ids=lambda c: f"{c['pattern']}-{'detects' if c['expectDetected'] else 'rejects'}")
def test_unit_case(case):
    p = BY_NAME.get(case["pattern"])
    assert p is not None, f"{case['pattern']} is not in the bundle"
    found = detect_country_pii(case["input"], [p])
    hit = next((m for m in found if m.name == case["pattern"]), None)
    if case["expectDetected"]:
        assert hit is not None, f"expected {case['pattern']} to match {case['input']!r}"
        assert case["input"][hit.start_index:hit.end_index] == case["sample"]
        assert hit.redaction == case["redaction"]
    else:
        assert hit is None, f"expected {case['pattern']} NOT to match {case['input']!r}"


# ── golden-snapshot parity ───────────────────────────────────────────────────

@pytest.mark.parametrize("case", CORPUS, ids=lambda c: c["id"])
def test_corpus_vector(case):
    assert infer_regions(case["input"]) == case["expectedRegions"], "activation"
    matches = detect_country_pii(case["input"])
    assert apply_redactions(case["input"], matches) == case["expectedOutput"], "redaction"
    assert list(dict.fromkeys(m.label for m in matches)) == case["expectedLabels"]
    assert list(dict.fromkeys(m.name for m in matches)) == case["expectedNames"]


def test_reproduces_the_cloud_activation_on_every_business_line():
    bad = [c["id"] for c in BUSINESS if infer_regions(c["input"]) != c["expectedRegions"]]
    assert bad == []


def test_adds_no_false_positive_to_the_business_corpus():
    assert len(BUSINESS) > 1500
    bad = [c["id"] for c in BUSINESS if detect_country_pii(c["input"])]
    assert bad == []


def test_diverges_from_the_cloud_for_exactly_one_stated_reason():
    """Bundle 1.2.0 ships au_tfn/au_abn/au_medicare as alwaysOn (rule 1a), so
    the AU bundle-gap cause this test tracked under 1.1.0 is now zero. Only
    L0 (the cloud-only universal layer this bundle deliberately excludes)
    remains."""
    diverged = [c for c in CASES if c.get("divergence")]
    for c in diverged:
        assert c["divergence"].startswith("L0:"), c["id"]
    gaps = {c["id"].split("/")[1] for c in diverged if c["divergence"].startswith("BUNDLE GAP")}
    assert gaps == set(), f"AU bundle gap must be 0, found: {gaps}"


def test_never_leaves_a_digit_beside_a_redaction_token():
    pat = re.compile(r"\d\[[A-Z_]+_REDACTED\]|\[[A-Z_]+_REDACTED\]\d")
    for c in CASES:
        out = apply_redactions(c["input"], detect_country_pii(c["input"]))
        assert not pat.search(out), f"{c['id']}: {out}"


def test_never_leaves_a_detected_identifier_in_the_output():
    for c in CASES:
        matches = detect_country_pii(c["input"])
        if not matches:
            continue
        out = apply_redactions(c["input"], matches)
        for m in matches:
            raw = c["input"][m.start_index:m.end_index]
            assert raw not in out, f"{c['id']}: {raw!r} survived"


# ── Indonesia, the rule 1.1.0 added ──────────────────────────────────────────

NIK = "3171010101900001"


def test_detects_the_short_spelling_which_is_a_whole_word_keyword_only():
    s = f"NIK {NIK} untuk pendaftaran rekening di Jakarta, Indonesia."
    assert infer_regions(s) == ["ID"]
    assert apply_redactions(s, detect_country_pii(s)) == (
        "NIK [NIK_REDACTED] untuk pendaftaran rekening di Jakarta, Indonesia."
    )


def test_detects_the_long_spelling_which_is_an_ordinary_substring_keyword():
    s = f"Nomor Induk Kependudukan {NIK} untuk pendaftaran."
    assert "[NIK_REDACTED]" in apply_redactions(s, detect_country_pii(s))


@pytest.mark.parametrize("word", ["teknik", "elektronik", "klinik", "pabrik", "piknik"])
def test_does_not_open_the_gate_on_nik_inside_an_ordinary_word(word):
    assert detect_country_pii(f"Faktur {word} {NIK} untuk pelanggan.") == []


def test_a_bare_nik_with_no_label_is_not_redacted():
    assert detect_country_pii(NIK) == []


# ── the rules 1.1.0 added to the SDK half of the contract ────────────────────

def test_rule_6_a_checksum_failing_identifier_is_redacted_generically():
    s = "South African ID number 8001015009088 for the FICA check."
    out = apply_redactions(s, detect_country_pii(s))
    assert "8001015009088" not in out
    assert "[NATIONAL_ID_REDACTED]" in out


def test_rule_7_a_column_header_is_the_context_for_a_bare_value_cell():
    csv = "\n".join(["Name,CNIC,City", "Ali,42201-1234567-1,Karachi",
                     "Sana,42201-7654321-2,Lahore", "Omar,42201-1111111-3,Multan"])
    assert table_scopes(csv)
    assert "42201-1234567-1" not in apply_redactions(csv, detect_country_pii(csv))


def test_rule_7_a_generic_header_does_not_act_as_context():
    csv = "\n".join(["Name,Order ID Number,City", "Ali,42201-1234567-1,Karachi",
                     "Sana,42201-7654321-2,Lahore", "Omar,42201-1111111-3,Multan"])
    assert detect_country_pii(csv) == []


def test_rule_7b_a_closer_commercial_label_closes_the_gate():
    s = "Please do not send your CNIC. Use the job number 4220112345671."
    at = s.index("4220112345671")
    assert labelled_as_reference(s, at, at + 13, ["cnic"]) is True
    assert "4220112345671" in apply_redactions(s, detect_country_pii(s))


def test_rule_7b_can_only_close_a_gate_never_open_one():
    assert detect_country_pii("Order 12345678901234 with no identifier word anywhere.") == []


def test_rule_5_a_country_match_supersedes_a_wider_l0_range_it_contains():
    s = "CPF 529.982.247-25 para a nota fiscal no Brasil."
    at = s.index("529.982.247-25")
    result = detect_country_pii_with_ranges(s, None, [(at - 1, at + 14)])
    assert any(m.name == "br_cpf" for m in result.matches)
    assert len(result.superseded_ranges) == 1


def test_whole_word_matching_respects_boundaries_at_the_window_edges():
    assert has_whole_word_context_around("nik 123", 4, 7, ["nik"]) is True
    assert has_whole_word_context_around("teknik 123", 7, 10, ["nik"]) is False
