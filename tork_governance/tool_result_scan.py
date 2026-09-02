"""
Tool-result scanning (DECIDED-TACT2-V2-C).

A tool result returned by an MCP server -- or by any external system the
caller does not control -- is untrusted input that is about to be appended
to a model's context. This module scans it BEFORE that happens, on-device,
for two things:

  1. PII, using the SAME on-device detector as govern() (detect_pii in
     .core). Nothing new was written for this: same patterns, same
     redaction labels, same zero-network guarantee.
  2. Prompt injection, using the conservative heuristic pattern set below.
     The SDK had NO injection heuristics before this module, so these are
     new -- and every injection finding is labelled `heuristic:<type>` in
     the findings so no caller can mistake a regex hit for a verified
     determination.

ZERO NETWORK. Every function here is pure and synchronous: no socket, no
I/O, no clock. The payload never leaves the machine, and the scan itself is
unaffected by whether an api_key is configured.

WHAT THIS IS NOT: this is a client-side control that the CALLER runs and
the caller attests to. It is not gateway-side enforcement -- a compromised
or simply careless caller can skip it entirely, and Tork cannot tell.
Enforcement at the gateway, where skipping is not an option, is a separate
and later control.

This is a byte-for-byte port of tool-result-scan.ts (see DECIDED-TACT2-V2-C
in the JS SDK session). What must match the JS SDK exactly: the
`tool_result_scan` receipt block (snake_case keys, emitted alphabetically,
optional keys omitted rather than nulled), attested_by='client',
capture_mode='edge', injection_ruleset='tork-injection-heuristics-v1', the
`heuristic:` finding-type prefix, the three injection type names
(instruction_override, role_reassignment, exfiltration_url), the four-way
action mapping in Tork.scan_tool_result, the location path grammar
($.a[0].b), and the injection regex sources themselves. Traversal
mechanics, cycle guarding, and identity preservation are reimplemented in
Python idiom but preserve the same semantics as the TypeScript source.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Pattern, Tuple

from .core import PIIResult, PIIType, detect_pii

# Signature every PII detector plugged into scan_tool_result() must match:
# (text, custom_patterns) -> PIIResult. Defaults to core.detect_pii (the
# basic 10-type detector) so the standalone scan_tool_result() function's
# behavior is unchanged; Tork.scan_tool_result() passes one bound to
# TorkConfig.detector instead (DECIDED-SDK-REGIONAL-DETECTOR-IS-THE-
# RUNTIME-PATH).
PIIDetectorFn = Callable[[str, Optional[Dict[str, Pattern]]], PIIResult]

# ============================================================================
# Types
# ============================================================================

# 'pii' -- a detector match. 'injection' -- a heuristic pattern match.
ToolResultFindingKind = str  # Literal["pii", "injection"] (kept as plain str for wire simplicity)


@dataclass
class ToolResultFinding:
    """One (kind, type) match count at one location in a scanned payload.

    For kind='pii', `type` is a PIIType value ('ssn', 'email', ...). For
    kind='injection', `type` is always `heuristic:<name>` -- the prefix is
    part of the value, not decoration, so a downstream reader of a receipt
    cannot mistake a pattern hit for a verified determination.
    """
    kind: str
    type: str
    count: int
    location: str


@dataclass
class ToolResultScanResult:
    """Result of scanning one tool result payload.

    `sanitized` is the payload with PII masked in place, structurally
    identical otherwise; sub-trees containing no PII keep their original
    object identity, so a clean payload comes back untouched. `sanitized`
    is `None` when `blocked` is True -- there is deliberately no masked
    payload to accidentally append.
    """
    sanitized: Any
    findings: List[ToolResultFinding] = field(default_factory=list)
    blocked: bool = False
    reason: Optional[str] = None


# ============================================================================
# Injection heuristics
# ============================================================================

# Prefix on every injection finding's `type`. Not cosmetic: these patterns
# are regexes over untrusted text, they carry false positives and false
# negatives, and the label travels with the finding into the receipt.
INJECTION_HEURISTIC_PREFIX = "heuristic:"

# Identifies this exact pattern set in receipts. Bump when the patterns
# change, so a receipt says which ruleset produced its counts. Every SDK
# mirroring this implementation must emit the SAME value for the same
# ruleset -- it is a shared identifier, not a per-language one.
INJECTION_RULESET = "tork-injection-heuristics-v1"

# Conservative on purpose. Each pattern targets a phrase that has no
# plausible reason to appear in a legitimate tool result -- a database row, a
# search hit, a file listing. Broader "suspicious language" matching would
# fire on ordinary documentation and support tickets, and an alert nobody
# believes is worse than no alert.
#
# Regex sources are ported verbatim from tool-result-scan.ts's
# INJECTION_PATTERNS (the /gi or /gim JS flags become re.IGNORECASE /
# re.IGNORECASE|re.MULTILINE here; there is no Python equivalent of the `g`
# flag to strip since finditer()/findall() already return every match).
_INJECTION_PATTERN_SOURCES: List[Tuple[str, str, int]] = [
    # -- instruction override --------------------------------------------
    (
        "instruction_override",
        r"\b(?:ignore|disregard|forget|override|bypass)\b[^.\n]{0,40}\b(?:previous|prior|earlier|above|preceding|all|any)\b[^.\n]{0,30}\b(?:instruction|instructions|prompt|prompts|rule|rules|direction|directions|guideline|guidelines)\b",
        re.IGNORECASE,
    ),
    (
        "instruction_override",
        r"\b(?:the\s+)?(?:instructions?|prompts?|rules?)\s+(?:above|below|before\s+this)\s+(?:are|is)\s+(?:now\s+)?(?:void|invalid|obsolete|outdated|no\s+longer\s+(?:valid|active|in\s+effect))\b",
        re.IGNORECASE,
    ),
    (
        "instruction_override",
        r"\bdisregard\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions?|guidelines?)\b",
        re.IGNORECASE,
    ),

    # -- role reassignment ------------------------------------------------
    (
        "role_reassignment",
        r"\byou\s+are\s+(?:now|no\s+longer)\s+(?:a|an|the)\b",
        re.IGNORECASE,
    ),
    (
        "role_reassignment",
        r"\b(?:from\s+now\s+on|starting\s+now|for\s+the\s+rest\s+of\s+this\s+(?:conversation|session))\b[^.\n]{0,30}\byou\s+(?:are|will|must|should)\b",
        re.IGNORECASE,
    ),
    (
        "role_reassignment",
        r"\bnew\s+(?:system\s+)?(?:instructions?|prompt|persona|role)\s*:",
        re.IGNORECASE,
    ),
    (
        "role_reassignment",
        r"\b(?:enable|enter|activate|switch\s+to)\s+(?:developer|god|dan|jailbreak|unrestricted)\s+mode\b",
        re.IGNORECASE,
    ),
    (
        "role_reassignment",
        r"\b(?:act|behave|respond|pretend\s+to\s+be)\s+as\s+(?:if\s+you\s+(?:are|were)\s+)?(?:an?\s+)?(?:dan|unrestricted|unfiltered|uncensored|jailbroken)\b",
        re.IGNORECASE,
    ),
    (
        # A role header smuggled into content -- "system:" / "<|im_start|>system"
        # at the start of a line is a conversation-structure forgery, not prose.
        "role_reassignment",
        r"^[ \t>*-]*(?:<\|im_start\|>\s*)?(?:system|assistant|developer)\s*(?::|\]|>)",
        re.IGNORECASE | re.MULTILINE,
    ),

    # -- exfiltration -----------------------------------------------------
    (
        # A markdown image/link whose URL carries the content out as a query
        # parameter -- the classic zero-click exfiltration shape.
        "exfiltration_url",
        r"!?\[[^\]\n]*\]\(\s*https?://[^)\s]*[?&][^)\s]*(?:data|payload|prompt|content|text|secret|token|key|conversation|history)=[^)\s]*\)",
        re.IGNORECASE,
    ),
    (
        "exfiltration_url",
        r"\bhttps?://\S*[?&](?:data|payload|secret|token|api[_-]?key|apikey|password|credential|conversation|history)=",
        re.IGNORECASE,
    ),
    (
        "exfiltration_url",
        r"\b(?:send|post|upload|forward|transmit|exfiltrate|leak|report)\b[^.\n]{0,60}\bto\s+https?://\S+",
        re.IGNORECASE,
    ),
]

INJECTION_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    (name, re.compile(source, flags)) for name, source, flags in _INJECTION_PATTERN_SOURCES
]

# Distinct injection types the ruleset can emit, for documentation/tests.
INJECTION_TYPES: List[str] = sorted({name for name, _ in INJECTION_PATTERNS})

# ============================================================================
# Traversal
# ============================================================================

DEFAULT_MAX_DEPTH = 32

_IDENTIFIER = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")


def _child_path(parent: str, key: str) -> str:
    if _IDENTIFIER.match(key):
        return f"{parent}.{key}"
    import json as _json
    return f"{parent}[{_json.dumps(key)}]"


def _scan_string(
    text: str,
    location: str,
    custom_patterns: Optional[Dict[str, Pattern]],
    findings: List[ToolResultFinding],
    pii_detector: PIIDetectorFn,
) -> str:
    """Scan one string: PII (via the configured detector) then injection
    heuristics. Returns the masked string plus any findings, both keyed to
    `location`."""
    pii = pii_detector(text, custom_patterns)

    if pii.count > 0:
        # Counts per type, emitted in a stable (sorted) order so two runs
        # over the same payload produce identical findings.
        per_type: Dict[str, int] = {}
        for match in pii.matches:
            type_value = match.type.value if isinstance(match.type, PIIType) else str(match.type)
            per_type[type_value] = per_type.get(type_value, 0) + 1
        for type_value in sorted(per_type.keys()):
            findings.append(ToolResultFinding(kind="pii", type=type_value, count=per_type[type_value], location=location))

    per_injection_type: Dict[str, int] = {}
    for injection_type, pattern in INJECTION_PATTERNS:
        count = len(pattern.findall(text))
        if count > 0:
            per_injection_type[injection_type] = per_injection_type.get(injection_type, 0) + count
    for injection_type in sorted(per_injection_type.keys()):
        findings.append(ToolResultFinding(
            kind="injection",
            type=f"{INJECTION_HEURISTIC_PREFIX}{injection_type}",
            count=per_injection_type[injection_type],
            location=location,
        ))

    return pii.redacted_text


def _walk(
    value: Any,
    location: str,
    depth: int,
    max_depth: int,
    custom_patterns: Optional[Dict[str, Pattern]],
    findings: List[ToolResultFinding],
    seen: set,
    pii_detector: PIIDetectorFn,
) -> Any:
    """Walk the payload, scanning every string. Returns a structure with PII
    masked in place; sub-trees with nothing to mask keep their original
    identity (so an untouched payload `is` its input).

    Only strings are scanned. Numbers, booleans, and anything else
    non-dict/non-list pass through untouched -- a bank account stored as a
    JSON number is NOT detected. Cycles are left as-is and not re-entered.
    """
    if isinstance(value, str):
        return _scan_string(value, location, custom_patterns, findings, pii_detector)

    if depth >= max_depth or value is None or not isinstance(value, (dict, list)):
        return value

    obj_id = id(value)
    if obj_id in seen:
        return value
    seen.add(obj_id)

    if isinstance(value, list):
        changed = False
        out = []
        for index, item in enumerate(value):
            next_item = _walk(item, f"{location}[{index}]", depth + 1, max_depth, custom_patterns, findings, seen, pii_detector)
            if next_item is not item:
                changed = True
            out.append(next_item)
        return out if changed else value

    changed = False
    out_dict: Dict[str, Any] = {}
    for key, item in value.items():
        next_item = _walk(item, _child_path(location, key), depth + 1, max_depth, custom_patterns, findings, seen, pii_detector)
        if next_item is not item:
            changed = True
        out_dict[key] = next_item
    return out_dict if changed else value


# ============================================================================
# Public API
# ============================================================================

def scan_tool_result(
    tool_name: str,
    payload: Any,
    server_uri: Optional[str] = None,
    *,
    block_on_injection: bool = False,
    custom_patterns: Optional[Dict[str, Pattern]] = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
    pii_detector: Optional[PIIDetectorFn] = None,
) -> ToolResultScanResult:
    """Scan a tool result for PII and prompt injection before it is
    appended to model context. Pure, synchronous, on-device: makes no
    network call and mutates nothing.

    Args:
        tool_name: Name of the tool that produced this result. Recorded on
            the receipt.
        payload: The tool result itself. Any JSON-shaped value; never
            leaves the machine.
        server_uri: URI of the MCP server (or other origin). Recorded on
            the receipt when present.
        block_on_injection: Block the result when the injection heuristics
            fire. Default False: detect and report, let the caller decide.
            When True and an injection pattern matches, `blocked` is True,
            `reason` is set, and `sanitized` is None -- there is
            deliberately no masked payload to accidentally append.
        custom_patterns: Extra redaction patterns, same shape and semantics
            as TorkConfig.custom_patterns. NOTE (inherited from
            detect_pii): custom patterns redact but are not counted, so
            they can change `sanitized` without producing a finding.
        max_depth: Maximum nesting depth to walk. Deeper values are passed
            through unscanned and unmodified. Default 32.
        pii_detector: PII detector to scan with, as (text, custom_patterns)
            -> PIIResult. Defaults to core.detect_pii (the basic 10-type
            detector) -- calling this standalone function directly keeps
            its original behavior. `Tork.scan_tool_result` passes one bound
            to `TorkConfig.detector` instead, so it follows the same
            basic/regional choice as `Tork.govern()`.

    For the receipt-linked form (attested_by='client', capture_mode='edge'),
    use `Tork.scan_tool_result`, which wraps this and records the scan.
    """
    if pii_detector is None:
        pii_detector = detect_pii
    findings: List[ToolResultFinding] = []
    sanitized = _walk(payload, "$", 0, max_depth, custom_patterns, findings, set(), pii_detector)

    injection_count = sum(f.count for f in findings if f.kind == "injection")
    blocked = bool(block_on_injection) and injection_count > 0

    if blocked:
        types = sorted({f.type for f in findings if f.kind == "injection"})
        reason = (
            f"Blocked: {injection_count} prompt-injection heuristic match(es) [{', '.join(types)}] in the result of "
            f'tool "{tool_name}". These are heuristic pattern matches ({INJECTION_RULESET}), not a verified '
            f"determination. sanitized is None so no masked copy can be appended to context by accident."
        )
        return ToolResultScanResult(sanitized=None, findings=findings, blocked=True, reason=reason)

    return ToolResultScanResult(sanitized=sanitized, findings=findings, blocked=False)


# ============================================================================
# Receipt block
# ============================================================================
#
# The `tool_result_scan` block recorded on the receipt.
#
# snake_case, keys emitted in alphabetical order, optional keys OMITTED
# entirely rather than set to None -- the same discipline as the
# TORK-DNA-v2 canonical form in core.py's build_canonical(), and for the
# same reason: every SDK that mirrors this must produce a byte-identical
# block for the same scan.
#
# It carries COUNTS ONLY. No payload, no matched substring, no location
# path, no tool argument ever appears here.

def _counts_by_type(findings: List[ToolResultFinding], kind: str) -> Dict[str, int]:
    totals: Dict[str, int] = {}
    for finding in findings:
        if finding.kind != kind:
            continue
        totals[finding.type] = totals.get(finding.type, 0) + finding.count
    return {type_: totals[type_] for type_ in sorted(totals.keys())}


def build_tool_result_scan_block(
    *,
    tool_name: str,
    result: ToolResultScanResult,
    sdk_version: str,
    server_uri: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the receipt block for a completed scan. Insertion order here
    IS the emitted key order: alphabetical, with optional keys omitted."""
    pii = _counts_by_type(result.findings, "pii")
    injection = _counts_by_type(result.findings, "injection")

    def _sum(counts: Dict[str, int]) -> int:
        return sum(counts.values())

    block: Dict[str, Any] = {
        "attested_by": "client",
        "blocked": result.blocked,
        "capture_mode": "edge",
        "findings": {"injection": injection, "pii": pii},
        "injection_ruleset": INJECTION_RULESET,
    }
    if result.reason is not None:
        block["reason"] = result.reason
    block["sdk_language"] = "python"
    block["sdk_version"] = sdk_version
    if server_uri is not None:
        block["server_uri"] = server_uri
    block["tool_name"] = tool_name
    block["totals"] = {"injection": _sum(injection), "pii": _sum(pii)}

    return block


def scan_pii_types(findings: List[ToolResultFinding]) -> List[str]:
    """Distinct PII types in a scan result, for the attestation canonical form."""
    return sorted({f.type for f in findings if f.kind == "pii"})


def scan_pii_count(findings: List[ToolResultFinding]) -> int:
    """Total PII match count in a scan result."""
    return sum(f.count for f in findings if f.kind == "pii")


def scan_injection_count(findings: List[ToolResultFinding]) -> int:
    """Total injection match count in a scan result."""
    return sum(f.count for f in findings if f.kind == "injection")
