"""
The country layer: 24 country profiles, 54 patterns, 20 check digits.

This implements the seven rules that ``generated/sdk-registry/README.md`` marks
**SDK**, from the bundle alone. Bundle 1.2.0 carries the data all seven need --
the activation signals, the country map, the three windows, the whole-word
vocabulary, the near-miss policy, the table constants and the reference labels
-- so nothing here is hand-written registry data and no window is hard-coded.

  1. ACTIVATE   a country's patterns run only when one of its signals fires.
  1a. ALWAYS ON au_tfn, au_abn and au_medicare run on every document, whatever
                rule 1 returns, and before the activated country patterns.
  2. MATCH      the regex, case-sensitively, globally.
  3. KEYWORD    whole-word (symmetric CONTEXT_WINDOW) or column verdict or the
                ASYMMETRIC substring window (60 before, 40 after); then 7b may
                close the gate again.
  4. CHECKSUM   when required. Advisory checksums never reject.
  5. SUPERSEDE  a match containing every range it overlaps takes them.
  6. NEAR MISS  a checksum-failing identifier is redacted generically, never
                released in clear.
  7. COLUMN     in a delimited table a bare value cell is judged by its header.
  7b. NEAREST LABEL  a closer commercial label closes the gate.

Still cloud-only, by design: the universal (L0) patterns, the slot, context,
gravity and name layers, industry profiles and org configuration.

Pure and local: no network, no clock. Every regex is compiled once at import.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .pii_checksums import CHECKSUM_FUNCTIONS
from .pii_registry import (
    TORK_PII_CONTENT_HASH,
    TORK_PII_CONTEXT_WINDOW,
    TORK_PII_COUNTRIES,
    TORK_PII_GENERIC_ID_KEYWORDS,
    TORK_PII_KEYWORD_WINDOW_AFTER,
    TORK_PII_KEYWORD_WINDOW_BEFORE,
    TORK_PII_LABEL_REACH,
    TORK_PII_LABEL_WINDOW,
    TORK_PII_LOCAL_ID_KEYWORDS,
    TORK_PII_NEAR_MISS_REDACTION,
    TORK_PII_NEAR_MISS_TYPE,
    TORK_PII_PATTERNS,
    TORK_PII_REFERENCE_LABELS,
    TORK_PII_REGISTRY_VERSION,
    TORK_PII_SIGNALS,
    TORK_PII_TABLE_DELIMITERS,
    TORK_PII_TABLE_MAX_HEADER_LENGTH,
    TORK_PII_TABLE_MAX_HEADER_WORDS,
    TORK_PII_TABLE_MIN_COMMA_COLUMNS,
    TORK_PII_TABLE_MIN_ROWS,
)

__all__ = [
    "CountryPIIMatch", "detect_country_pii", "detect_country_pii_with_ranges",
    "infer_regions", "patterns_for_regions", "apply_redactions",
    "labelled_as_reference", "has_whole_word_context_around", "table_scopes",
    "KEYWORD_WINDOW_BEFORE", "KEYWORD_WINDOW_AFTER", "CONTEXT_WINDOW",
    "TORK_PII_REGISTRY_VERSION", "TORK_PII_CONTENT_HASH",
]

#: Characters before a match that count as "nearby" for the substring gate.
KEYWORD_WINDOW_BEFORE = TORK_PII_KEYWORD_WINDOW_BEFORE
#: Characters after a match that count as "nearby" for the substring gate.
KEYWORD_WINDOW_AFTER = TORK_PII_KEYWORD_WINDOW_AFTER
#: The symmetric window: whole-word keywords and the near-miss gate.
CONTEXT_WINDOW = TORK_PII_CONTEXT_WINDOW

_NATIONAL_ID_KEYWORDS = list(TORK_PII_GENERIC_ID_KEYWORDS) + list(TORK_PII_LOCAL_ID_KEYWORDS)
_GENERIC_SET = set(TORK_PII_GENERIC_ID_KEYWORDS)

# Compile once at import, not per call.
_PATTERN_RE: Dict[str, "re.Pattern[str]"] = {p["name"]: re.compile(p["regex"]) for p in TORK_PII_PATTERNS}
_SIGNAL_RE: List["re.Pattern[str]"] = [
    re.compile(s["regex"], re.IGNORECASE if "i" in s.get("flags", "") else 0) for s in TORK_PII_SIGNALS
]

_BY_NAME = {p["name"]: p for p in TORK_PII_PATTERNS}
_COUNTRY_PATTERNS = {c["code"]: c["patterns"] for c in TORK_PII_COUNTRIES}

#: Rule 1a -- patterns that run on every document, country activation or not.
#: Bundle 1.2.0's three: au_tfn, au_abn, au_medicare. Run first so an activated
#: country pattern can still supersede one of these under rule 5.
_ALWAYS_ON_PATTERNS: List[dict] = [p for p in TORK_PII_PATTERNS if p.get("always_on")]
_ALWAYS_ON_NAMES = {p["name"] for p in _ALWAYS_ON_PATTERNS}

_SIGNAL_ORDER: List[str] = []
for _s in TORK_PII_SIGNALS:
    if _s["country"] not in _SIGNAL_ORDER:
        _SIGNAL_ORDER.append(_s["country"])

_SIGNALS_BY_COUNTRY: Dict[str, List[Tuple[int, dict]]] = {}
for _i, _s in enumerate(TORK_PII_SIGNALS):
    _SIGNALS_BY_COUNTRY.setdefault(_s["country"], []).append((_i, _s))

_ALNUM = re.compile(r"[a-z0-9]")
_ALNUM_ANY = re.compile(r"[0-9A-Za-z]")


@dataclass
class CountryPIIMatch:
    """One country identifier found in the content."""

    name: str
    country: str
    label: str
    type: str
    redaction: str
    start_index: int
    end_index: int


@dataclass
class TableScope:
    start: int
    end: int
    header: str
    row_start: int
    row_end: int


# ── shared helpers ───────────────────────────────────────────────────────────

def _all_keywords_of(p: dict) -> List[str]:
    """A pattern's whole vocabulary: the substring keywords and the whole-word ones."""
    ww = p.get("whole_word_keywords") or []
    return list(p["keywords"]) + list(ww) if ww else list(p["keywords"])


def _specific_keywords(keywords: Sequence[str]) -> List[str]:
    """The half of a vocabulary that names ONE country's identifier."""
    return [k for k in keywords if k not in _GENERIC_SET]


def _has_nearby_context(content: str, start: int, end: int, keywords: Sequence[str]) -> bool:
    """Rule 3, substring half: ASYMMETRIC -- 60 before the match, 40 after it."""
    before = content[max(0, start - KEYWORD_WINDOW_BEFORE):start].lower()
    after = content[end:min(len(content), end + KEYWORD_WINDOW_AFTER)].lower()
    return any(kw in before or kw in after for kw in keywords)


def _has_context_around(content: str, start: int, end: int, keywords: Sequence[str]) -> bool:
    """Symmetric CONTEXT_WINDOW either side, substring. Used by rule 6."""
    window = content[max(0, start - CONTEXT_WINDOW):min(len(content), end + CONTEXT_WINDOW)].lower()
    return any(kw in window for kw in keywords)


def has_whole_word_context_around(content: str, start: int, end: int, words: Optional[Sequence[str]]) -> bool:
    """Rule 3, whole-word half: symmetric CONTEXT_WINDOW, a boundary each side.

    A boundary is "not a letter or digit". This is the gate Indonesia needs:
    ``nik`` sits inside teknik, elektronik, klinik and pabrik, so a substring
    test would open the gate on a sales ledger.
    """
    if not words:
        return False
    window = content[max(0, start - CONTEXT_WINDOW):min(len(content), end + CONTEXT_WINDOW)].lower()
    n = len(window)
    for w in words:
        frm = 0
        while True:
            i = window.find(w, frm)
            if i == -1:
                break
            before = "" if i == 0 else window[i - 1]
            after = "" if i + len(w) >= n else window[i + len(w)]
            if not _ALNUM.match(before or "") and not _ALNUM.match(after or ""):
                return True
            frm = i + 1
    return False


def _document_has_whole_word(content: str, words: Optional[Sequence[str]]) -> bool:
    if not words:
        return False
    return has_whole_word_context_around(content, 0, len(content), words)


# ── rule 1: activation ───────────────────────────────────────────────────────

def infer_regions(content: str) -> List[str]:
    """The countries whose patterns this text activates, in the bundle's signal order."""
    regions: List[str] = []
    lower = content.lower()
    for code in _SIGNAL_ORDER:
        for idx, signal in _SIGNALS_BY_COUNTRY.get(code, []):
            if not _SIGNAL_RE[idx].search(content):
                continue
            kws = signal["keywords"]
            wws = signal.get("whole_word_keywords") or []
            by_substring = bool(kws) and any(k in lower for k in kws)
            by_whole_word = _document_has_whole_word(content, wws)
            # Both lists empty means the shape alone is distinctive enough.
            if (kws or wws) and not (by_substring or by_whole_word):
                continue
            target = signal.get("activates") or code
            if target not in regions:
                regions.append(target)
            break  # one signal per country is enough
    return regions


def patterns_for_regions(regions: Sequence[str]) -> List[dict]:
    """The patterns those regions switch on, de-duplicated, in registry order."""
    out: List[dict] = []
    seen = set()
    for code in regions:
        for name in _COUNTRY_PATTERNS.get(code.upper(), []):
            if name in seen:
                continue
            p = _BY_NAME.get(name)
            if p is None:
                continue
            seen.add(name)
            out.append(p)
    return out


# ── rule 7: the column is the context ────────────────────────────────────────

_HEADER_HAS_LETTER = re.compile(r"[A-Za-zÀ-￿]")
_HEADER_ALL_NUMERIC = re.compile(r"^\+?[\d\s.\-/]+$")
_HEADER_SENTENCE = re.compile(r"[.?!]")


def _looks_like_header(cells: Sequence[str], delimiter: str) -> bool:
    minimum = TORK_PII_TABLE_MIN_COMMA_COLUMNS if delimiter == "," else 2
    if len(cells) < minimum:
        return False
    for c in cells:
        t = c.strip()
        if not t or len(t) > TORK_PII_TABLE_MAX_HEADER_LENGTH:
            return False
        if not _HEADER_HAS_LETTER.search(t):
            return False
        if _HEADER_ALL_NUMERIC.match(t):
            return False
        if _HEADER_SENTENCE.search(t):
            return False
        if len(t.split()) > TORK_PII_TABLE_MAX_HEADER_WORDS:
            return False
    return True


def table_scopes(content: str) -> List[TableScope]:
    """The cells of ``content``, when it is a delimited table with a header row."""
    lines = content.split("\n")
    if len(lines) < TORK_PII_TABLE_MIN_ROWS:
        return []

    offsets, at = [], 0
    for line in lines:
        offsets.append(at)
        at += len(line) + 1

    for delimiter in TORK_PII_TABLE_DELIMITERS:
        header_cells = lines[0].split(delimiter)
        if not _looks_like_header(header_cells, delimiter):
            continue
        width = len(header_cells)

        data_rows = []
        for i in range(1, len(lines)):
            if lines[i].strip() == "":
                continue
            if len(lines[i].split(delimiter)) != width:
                return []
            data_rows.append(i)
        if len(data_rows) < TORK_PII_TABLE_MIN_ROWS - 1:
            continue

        scopes: List[TableScope] = []
        for row in data_rows:
            cells = lines[row].split(delimiter)
            row_start = offsets[row]
            row_end = row_start + len(lines[row])
            cell_start = row_start
            for col in range(width):
                scopes.append(TableScope(
                    start=cell_start, end=cell_start + len(cells[col]),
                    header=header_cells[col].strip().lower(),
                    row_start=row_start, row_end=row_end,
                ))
                cell_start += len(cells[col]) + len(delimiter)
        return scopes
    return []


def _header_names(header: str, keywords: Sequence[str]) -> bool:
    """A whole-word match, not a substring."""
    for kw in keywords:
        i = header.find(kw)
        if i == -1:
            continue
        before_ok = i == 0 or not _ALNUM.match(header[i - 1])
        j = i + len(kw)
        after_ok = j >= len(header) or not _ALNUM.match(header[j])
        if before_ok and after_ok:
            return True
    return False


def _cell_at(scopes: Sequence[TableScope], start: int, end: int) -> Optional[TableScope]:
    for s in scopes:
        if start >= s.start and end <= s.end:
            return s
    return None


def _column_verdict(content, scopes, start, end, all_keywords, specific) -> Optional[bool]:
    """None when the window should be consulted as usual."""
    if not scopes:
        return None
    cell = _cell_at(scopes, start, end)
    if cell is None:
        return None
    # A cell whose own row names the identifier is prose in a delimited block.
    row_text = content[cell.row_start:cell.row_end].lower()
    if any(k in row_text for k in all_keywords):
        return None
    return _header_names(cell.header, specific) if specific else False


# ── rule 7b: nearest label wins ──────────────────────────────────────────────

def _closest_before(before: str, keywords: Sequence[str]) -> Optional[int]:
    best = None
    for kw in keywords:
        i = before.rfind(kw)
        if i == -1:
            continue
        distance = len(before) - (i + len(kw))
        if best is None or distance < best:
            best = distance
    return best


def _closest_after(after: str, keywords: Sequence[str]) -> Optional[int]:
    best = None
    for kw in keywords:
        i = after.find(kw)
        if i == -1:
            continue
        if best is None or i < best:
            best = i
    return best


def labelled_as_reference(content: str, start: int, end: int, identifier_keywords: Optional[Sequence[str]]) -> bool:
    """True when the number is labelled as a commercial reference more closely
    than as an identifier. It can only ever close a gate, never open one."""
    before = content[max(0, start - TORK_PII_LABEL_WINDOW):start].lower()
    ref = _closest_before(before, TORK_PII_REFERENCE_LABELS)
    if ref is None or ref > TORK_PII_LABEL_REACH:
        return False
    if not identifier_keywords:
        return True
    id_before = _closest_before(before, identifier_keywords)
    if id_before is not None and id_before <= ref:
        return False
    after = content[end:min(len(content), end + TORK_PII_LABEL_WINDOW)].lower()
    id_after = _closest_after(after, identifier_keywords)
    if id_after is not None and id_after <= ref:
        return False
    return True


# ── the pass ─────────────────────────────────────────────────────────────────

def _trimmed_core(content: str, start: int, end: int) -> Tuple[int, int]:
    """The span with leading and trailing non-alphanumeric characters removed."""
    s, e = start, end
    while s < e and not _ALNUM_ANY.match(content[s]):
        s += 1
    while e > s and not _ALNUM_ANY.match(content[e - 1]):
        e -= 1
    return (start, end) if s == e else (s, e)


@dataclass
class CountryPIIResult:
    matches: List[CountryPIIMatch] = field(default_factory=list)
    #: Ranges from ``existing_ranges`` that a country match superseded (rule 5).
    superseded_ranges: List[Tuple[int, int]] = field(default_factory=list)


def detect_country_pii_with_ranges(
    content: str,
    patterns: Optional[Sequence[dict]] = None,
    existing_ranges: Optional[Sequence[Tuple[int, int]]] = None,
) -> CountryPIIResult:
    """Country matches for ``content``, de-overlapped and ordered by position.

    ``patterns`` bypasses activation (the per-pattern unit tests use it).
    ``existing_ranges`` are your own L0 spans, so rule 5 can supersede them.
    """
    if patterns is not None:
        active = list(patterns)
    else:
        activated = patterns_for_regions(infer_regions(content))
        active = _ALWAYS_ON_PATTERNS + [p for p in activated if p["name"] not in _ALWAYS_ON_NAMES]
    if not active:
        return CountryPIIResult([], [])

    tables = table_scopes(content)
    active_existing: List[Tuple[int, int]] = list(existing_ranges or [])
    superseded: List[Tuple[int, int]] = []
    claimed: List[Tuple[int, int]] = []
    found: List[CountryPIIMatch] = []
    near_misses: List[Tuple[int, int]] = []

    for pattern in active:
        for m in _PATTERN_RE[pattern["name"]].finditer(content):
            if not m.group(0):
                continue
            start, end = m.start(), m.end()

            # Rules 3, 7 and 7b.
            if pattern["requires_keyword"] and pattern["keywords"]:
                allk = _all_keywords_of(pattern)
                whole = has_whole_word_context_around(content, start, end, pattern.get("whole_word_keywords"))
                column = _column_verdict(content, tables, start, end, allk, _specific_keywords(allk))
                if whole:
                    ok = True
                elif column is not None:
                    ok = column
                else:
                    ok = _has_nearby_context(content, start, end, pattern["keywords"])
                if not ok:
                    continue
                if labelled_as_reference(content, start, end, pattern["keywords"]):
                    continue

            # Rule 4, and rule 6's candidate.
            if pattern["checksum_required"] and pattern["checksum"]:
                fn = CHECKSUM_FUNCTIONS.get(pattern["checksum"])
                if fn is not None and not fn(m.group(0)):
                    if pattern.get("near_miss_fallback"):
                        extra = pattern.get("near_miss_keywords") or pattern["keywords"]
                        vocabulary = _NATIONAL_ID_KEYWORDS + list(extra) if extra else _NATIONAL_ID_KEYWORDS
                        if _has_context_around(content, start, end, vocabulary):
                            near_misses.append((start, end))
                    continue

            # Rule 5.
            all_active = active_existing + claimed
            overlapping = [(rs, re_) for rs, re_ in all_active if start < re_ and end > rs]
            if overlapping:
                def contains(rng):
                    cs, ce = _trimmed_core(content, rng[0], rng[1])
                    return start <= cs and end >= ce
                if not all(contains(r) for r in overlapping):
                    continue
                for rng in overlapping:
                    if rng in active_existing:
                        active_existing.remove(rng)
                        superseded.append(rng)
                    if rng in claimed:
                        claimed.remove(rng)
                        found[:] = [f for f in found if (f.start_index, f.end_index) != rng]

            claimed.append((start, end))
            found.append(CountryPIIMatch(
                name=pattern["name"], country=pattern["country"], label=pattern["label"],
                type=pattern["type"], redaction=pattern["redaction"],
                start_index=start, end_index=end,
            ))

    # Rule 6, last: a near miss can only ever fill a hole.
    taken = active_existing + claimed
    for cs, ce in near_misses:
        if any(cs < rend and ce > rs for rs, rend in taken):
            continue
        taken.append((cs, ce))
        found.append(CountryPIIMatch(
            name=TORK_PII_NEAR_MISS_TYPE, country="", label="NATIONAL_ID",
            type=TORK_PII_NEAR_MISS_TYPE, redaction=TORK_PII_NEAR_MISS_REDACTION,
            start_index=cs, end_index=ce,
        ))

    found.sort(key=lambda f: f.start_index)
    return CountryPIIResult(found, superseded)


def detect_country_pii(content: str, patterns: Optional[Sequence[dict]] = None) -> List[CountryPIIMatch]:
    """Country matches for ``content``. The common case: no L0 ranges to supersede."""
    return detect_country_pii_with_ranges(content, patterns).matches


def apply_redactions(text: str, spans: Sequence[CountryPIIMatch]) -> str:
    """Replace every span with its redaction, right to left.

    Right to left is what keeps the earlier indices valid, and splicing whole
    spans in one pass is what guarantees no partial redaction: a digit can never
    be left standing beside a redaction token, because nothing is ever matched
    against text a previous replacement has already rewritten.
    """
    if not spans:
        return text
    out = text
    for s in sorted(spans, key=lambda x: x.start_index, reverse=True):
        out = out[:s.start_index] + s.redaction + out[s.end_index:]
    return out
