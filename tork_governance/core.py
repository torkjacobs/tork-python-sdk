"""
Tork Governance Core Module

PII detection, redaction, and governance with cryptographic receipts.
"""

import importlib.metadata
import json
import math
import re
import hashlib
import secrets
import socket
import threading
import urllib.error
import urllib.request
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Pattern, Set
import time

__version__ = "0.23.0"


def _sdk_version() -> str:
    """Package version as reported by installed metadata, falling back to
    the in-source constant when the package isn't installed (e.g. running
    from a checkout without `pip install`)."""
    try:
        return importlib.metadata.version("tork-governance")
    except importlib.metadata.PackageNotFoundError:
        return __version__


_USER_AGENT = f"tork-governance-python/{_sdk_version()}"


class PIIType(str, Enum):
    """Types of PII that can be detected."""
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    IP_ADDRESS = "ip_address"
    DATE_OF_BIRTH = "date_of_birth"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    BANK_ACCOUNT = "bank_account"


class GovernanceAction(str, Enum):
    """Actions that can be taken on content."""
    ALLOW = "allow"
    DENY = "deny"
    REDACT = "redact"
    ESCALATE = "escalate"


@dataclass
class PIIMatch:
    """A single PII match found in text."""
    type: PIIType
    value: str
    start_index: int
    end_index: int


@dataclass
class PIIResult:
    """Result of PII detection."""
    has_pii: bool
    types: List[PIIType]
    count: int
    matches: List[PIIMatch]
    redacted_text: str


@dataclass
class SessionContext:
    """Agent/session context for multi-agent governance tracking.

    Attributes:
        agent_id: Identifier for the agent making the call.
        agent_role: Role of the agent ("planner", "worker", or "judge").
        session_id: Groups all calls from the same agent session.
        session_turn: Position in the conversation (1, 2, 3...).
    """
    agent_id: Optional[str] = None
    agent_role: Optional[str] = None
    session_id: Optional[str] = None
    session_turn: Optional[int] = None


@dataclass
class Receipt:
    """Cryptographic receipt for governance audit trail."""
    receipt_id: str
    timestamp: str
    input_hash: str
    output_hash: str
    action: GovernanceAction
    policy_version: str
    processing_time_ns: int
    pii_types: List[PIIType] = field(default_factory=list)
    pii_count: int = 0
    session_context: Optional[SessionContext] = None

    def verify(self, input_text: str, output_text: str) -> bool:
        """Verify that input/output match the receipt hashes."""
        return (
            hash_text(input_text) == self.input_hash and
            hash_text(output_text) == self.output_hash
        )


@dataclass
class AttestationReport:
    """Outcome of optionally reporting a decision to tork.network.

    `attempted` and `succeeded` are independent: check `succeeded`, not just
    `attempted`, before treating a decision as anchored. `receipt_id` is only
    set when the server actually persisted the row; `reason` is only set when
    it did not.

    The network call (and its one retry) runs on a background thread so
    `govern()` never blocks on it — `succeeded`/`receipt_id`/`reason` are
    filled in on this same object once that thread finishes. Immediately
    after `govern()` returns they may still reflect the in-flight placeholder
    state. Call `.wait()` if you need the confirmed outcome before
    proceeding (most callers don't).
    """
    attempted: bool
    succeeded: bool
    receipt_id: Optional[str] = None
    reason: Optional[str] = None
    _thread: Optional[threading.Thread] = field(default=None, repr=False, compare=False)

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Block until the background reporting attempt (if any) finishes.

        Returns True once reporting has settled (or there was nothing to
        wait on), False if `timeout` elapsed first. Never raises. The local
        governance decision this report is attached to is unaffected either
        way — this exists for callers/tests that explicitly want the
        confirmed network outcome.
        """
        if self._thread is None:
            return True
        self._thread.join(timeout)
        return not self._thread.is_alive()


@dataclass
class GovernanceResult:
    """Result of governance evaluation."""
    action: GovernanceAction
    output: str
    pii: PIIResult
    receipt: Receipt
    region: Optional[List[str]] = None
    industry: Optional[str] = None
    session_context: Optional[SessionContext] = None
    report: Optional[AttestationReport] = None


_API_KEY_REPORTING_MESSAGE = (
    "You passed an api_key to tork-governance: reporting to tork.network is now ON. "
    "PII detection, redaction, and the returned decision are still computed entirely "
    "on-device and are never delayed or changed by this. After each govern() call, "
    "this SDK separately POSTs a METADATA-ONLY attestation to "
    "https://tork.network/api/v1/attestations: the action taken, PII type labels and "
    "counts, a risk/score classification, policy labels, and a salted fingerprint. "
    "It NEVER sends input text, output text, redacted content, or "
    "PII values — those never leave this device. The resulting row is recorded as a "
    "CLIENT ATTESTATION (attested_by='client'): a self-reported, internally-consistent "
    "claim that Tork did not itself execute or independently verify, not a "
    "Tork-verified decision. Reporting runs on a background thread and never raises — "
    "check GovernanceResult.report (attempted/succeeded/receipt_id/reason) for the "
    "outcome, or call report.wait() if you need the confirmed outcome before "
    "proceeding. Remove the api_key argument to keep this SDK fully local with zero "
    "network calls."
)

# Module-level flag so the api_key warning fires at most once per process.
_api_key_warning_emitted = False


def _warn_api_key_reporting(stacklevel: int = 2) -> None:
    """Warn once per process that api_key turns on tork.network reporting.

    stacklevel is relative to the caller of this helper: 2 points at the
    caller's caller (i.e. the customer's line), exactly as if the caller
    had invoked warnings.warn(..., stacklevel=2) itself.
    """
    global _api_key_warning_emitted
    if _api_key_warning_emitted:
        return
    _api_key_warning_emitted = True
    warnings.warn(_API_KEY_REPORTING_MESSAGE, UserWarning, stacklevel=stacklevel + 1)


@dataclass
class TorkConfig:
    """Configuration for Tork client.

    Attributes:
        policy_version: Policy version string recorded on receipts.
        default_action: Action taken when PII is detected.
        custom_patterns: Optional custom regex patterns to detect.
        api_key: Optional. PII detection and the governance decision are
            ALWAYS computed on-device regardless of this value. Supplying a
            key additionally turns on best-effort, metadata-only reporting
            of each decision to https://tork.network/api/v1/attestations —
            never input/output text or PII values. See GovernanceResult.report
            for the outcome of a given call. Providing a value emits a
            UserWarning (once per process) describing exactly what is sent.
    """
    policy_version: str = "1.0.0"
    default_action: GovernanceAction = GovernanceAction.REDACT
    custom_patterns: Optional[Dict[str, Pattern]] = None
    api_key: Optional[str] = None

    def __post_init__(self):
        if self.api_key:
            # Frames above the helper's warn(): __post_init__ (1 relative) ->
            # dataclass-generated __init__ (2) -> whoever constructed the
            # config (3) — that construction site is the customer's line.
            _warn_api_key_reporting(stacklevel=3)


# PII Detection Patterns
PII_PATTERNS: Dict[PIIType, tuple] = {
    PIIType.SSN: (
        re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        '[SSN_REDACTED]'
    ),
    PIIType.CREDIT_CARD: (
        re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
        '[CARD_REDACTED]'
    ),
    PIIType.EMAIL: (
        re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
        '[EMAIL_REDACTED]'
    ),
    PIIType.PHONE: (
        re.compile(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
        '[PHONE_REDACTED]'
    ),
    PIIType.ADDRESS: (
        re.compile(r'\b\d{1,5}\s+\w+(?:\s+\w+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Place|Pl)\b', re.IGNORECASE),
        '[ADDRESS_REDACTED]'
    ),
    PIIType.IP_ADDRESS: (
        re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'),
        '[IP_REDACTED]'
    ),
    PIIType.DATE_OF_BIRTH: (
        re.compile(r'\b(?:0[1-9]|1[0-2])/(?:0[1-9]|[12]\d|3[01])/(?:19|20)\d{2}\b'),
        '[DOB_REDACTED]'
    ),
}


def hash_text(text: str) -> str:
    """Generate SHA256 hash of text with prefix."""
    h = hashlib.sha256(text.encode('utf-8')).hexdigest()
    return f"sha256:{h}"


def generate_receipt_id() -> str:
    """Generate a unique receipt ID."""
    return f"rcpt_{secrets.token_hex(16)}"


# ── TORK-DNA-v2 canonical form + salted fingerprinting ──────────────────────
#
# Ports lib/governance/dna-fingerprint.ts (classifyRisk / computeScore /
# derivePolicies / buildCanonical) byte-for-byte. The attestations endpoint
# independently recomputes risk/policies from the submitted canonical_json
# and 422s on mismatch, so this must track the TypeScript source exactly, not
# just approximate it.
#
# NOTE ON PII VOCABULARY: PIIType values here (e.g. "passport",
# "drivers_license") do not all match the server's risk-tier vocabulary
# (which expects "us_passport", "us_drivers_license"). That is not a bug in
# this port — classify_risk() below runs on whatever strings are passed to
# it, so the fingerprint stays internally self-consistent either way. It does
# mean a few Python PII types are silently scored as "low" risk instead of
# "high"/"medium" server-side equivalents would be. See core.py callers.

ATTESTATIONS_ENDPOINT = "https://tork.network/api/v1/attestations"

# Measured production latency (3 consecutive calls, 3 Aug): 8.0s, 5.7s, 4.8s.
# 15s gives comfortable headroom above the observed worst case. urllib's
# `timeout=` is a single socket timeout covering connect+read together —
# there is no separate connect-timeout knob in urllib.request without
# dropping to raw http.client and re-implementing connection handling, which
# isn't warranted here: the endpoint is Cloudflare-fronted, so a hung TCP
# handshake specifically (as opposed to a slow response) isn't the failure
# mode seen in production.
_REPORT_TIMEOUT_SECONDS = 15
_REPORT_RETRY_BACKOFF_SECONDS = 1.0

_HIGH_RISK_PII = frozenset({
    "ssn", "ssn_undashed", "credit_card", "credit_card_amex",
    "bank_routing", "us_passport", "french_ssn",
})

_MEDIUM_RISK_PII = frozenset({
    "us_ein", "us_drivers_license", "uk_nino", "uk_nhs",
    "iban", "swift_bic", "npi", "dea_number", "medical_record",
    "au_tfn", "au_medicare", "crypto_btc", "crypto_eth",
})

# GovernanceAction -> the verdict vocabulary the attestations endpoint
# persists (allow | redact | deny | flag; 'block' normalises to 'deny' on
# the server, never used here). ESCALATE has no analogue in the documented
# 3-value contract (allow|redact|deny); the endpoint's own validator accepts
# a 4th verdict, 'flag', for exactly the human-in-the-loop case ESCALATE
# represents, so it maps there rather than being silently coerced into
# allow or deny.
_ACTION_TO_VERDICT = {
    GovernanceAction.ALLOW: "allow",
    GovernanceAction.REDACT: "redact",
    GovernanceAction.DENY: "deny",
    GovernanceAction.ESCALATE: "flag",
}


def classify_risk(pii_types: List[str], verdict: str) -> str:
    """Port of classifyRisk() in lib/governance/dna-fingerprint.ts."""
    if verdict == "deny":
        return "critical"
    if not pii_types:
        return "none"
    if any(t in _HIGH_RISK_PII for t in pii_types):
        return "high"
    if any(t in _MEDIUM_RISK_PII for t in pii_types):
        return "medium"
    return "low"


def compute_score(
    pii_types: List[str],
    pii_count: int,
    verdict: str,
    autonomy_level: Optional[int] = None,
) -> int:
    """Port of computeScore() in lib/governance/dna-fingerprint.ts."""
    if pii_count == 0 and verdict == "allow" and (autonomy_level is None or autonomy_level <= 3):
        return 100

    score = 100

    for t in pii_types:
        if t in _HIGH_RISK_PII:
            score -= 15
        elif t in _MEDIUM_RISK_PII:
            score -= 10
        else:
            score -= 5

    score -= min(15, math.floor(math.log2(pii_count + 1)) * 3)

    if verdict == "redact":
        score += 10
    if verdict == "deny":
        score -= 10

    if autonomy_level is not None and autonomy_level >= 4:
        score -= (autonomy_level - 3) * 5

    return max(0, min(100, score))


def derive_policies(verdict: str, pii_types: List[str]) -> List[str]:
    """Port of derivePolicies() in lib/governance/dna-fingerprint.ts."""
    policies: List[str] = []
    if pii_types:
        if verdict == "redact":
            policies.append("pii-redact")
        elif verdict == "deny":
            policies.append("pii-deny")
        else:
            policies.append("pii-detect")
    policies.append("rate-limit")
    policies.sort()
    return policies


def build_canonical(
    policy_version: str,
    verdict: str,
    pii_types: List[str],
    pii_count: int,
    hitl: bool,
    ts: int,
    autonomy_level: Optional[int] = None,
) -> Dict:
    """Port of buildCanonical() in lib/governance/dna-fingerprint.ts."""
    pii_sorted = sorted(set(pii_types))
    canonical: Dict = {
        "v": policy_version,
        "policies": derive_policies(verdict, pii_sorted),
        "pii": pii_sorted,
        "risk": classify_risk(pii_sorted, verdict),
        "hitl": hitl,
        "score": compute_score(pii_sorted, pii_count, verdict, autonomy_level),
        "ts": ts,
    }
    if autonomy_level is not None:
        canonical["autonomy_level"] = autonomy_level
    return canonical


def canonical_json(canonical: Dict) -> str:
    """Byte-exact serialisation the server re-hashes and re-derives from.

    Equivalent to JSON.stringify(canonical, Object.keys(canonical).sort())
    on the TypeScript side: keys sorted, no whitespace, booleans lowercase,
    integers with no decimal point.
    """
    return json.dumps(canonical, separators=(",", ":"), sort_keys=True)


def generate_fingerprint_salt() -> str:
    """32 lowercase hex chars (16 random bytes)."""
    return secrets.token_hex(16)


def compute_salted_fingerprint(canonical_json_str: str, salt: str) -> str:
    """TORK-DNA-v2-{first 16 hex chars of sha256(canonical_json + '|' + salt)}."""
    digest = hashlib.sha256(f"{canonical_json_str}|{salt}".encode("utf-8")).hexdigest()
    return f"TORK-DNA-v2-{digest[:16]}"


def _decided_at_pair(ts: Optional[int] = None):
    """A (ts, decided_at) pair guaranteed to satisfy the server's check that
    decided_at, floored to the second, equals canonical.ts exactly."""
    if ts is None:
        ts = int(time.time())
    decided_at = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return ts, decided_at


class _RetryableReportError(Exception):
    """Timeout or 5xx — the server may or may not have written the row."""


class _NonRetryableReportError(Exception):
    """4xx or a malformed response — the server rejected the claim, or the
    exchange completed and definitively did not produce a receipt. Retrying
    would just be noise."""


def _attempt_attestation_once(
    *,
    api_key: str,
    client_event_id: str,
    verdict: str,
    canonical_json_str: str,
    salt: str,
    fingerprint: str,
    decided_at: str,
) -> AttestationReport:
    """POST a metadata-only attestation to tork.network, once.

    Raises `_RetryableReportError` on timeout or a 5xx (ambiguous — the
    write may have landed), `_NonRetryableReportError` on a 4xx or a
    malformed 2xx (unambiguous — no receipt was produced). Returns an
    AttestationReport(succeeded=True) on a confirmed write. Never raises
    anything else.

    The request body carries only: client_event_id, action, canonical_json
    (type labels/counts + structural fields, never PII values), the
    fingerprint salt, the fingerprint, and decided_at. No input text, output
    text, or PII value is ever included.
    """
    body = json.dumps({
        "client_event_id": client_event_id,
        "action": verdict,
        "canonical_json": canonical_json_str,
        "fingerprint_salt": salt,
        "fingerprint": fingerprint,
        "decided_at": decided_at,
    }).encode("utf-8")

    request = urllib.request.Request(
        ATTESTATIONS_ENDPOINT,
        data=body,
        method="POST",
        headers={
            "x-tork-api-key": api_key,
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENT,
            "x-tork-sdk-language": "python",
            "x-tork-sdk-version": _sdk_version(),
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=_REPORT_TIMEOUT_SECONDS) as response:
            status = response.status
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            error_payload = json.loads(exc.read().decode("utf-8"))
            reason = error_payload.get("message") or error_payload.get("error") or f"HTTP {exc.code}"
        except Exception:
            reason = f"HTTP {exc.code}"
        if 500 <= exc.code < 600:
            raise _RetryableReportError(str(reason)) from exc
        raise _NonRetryableReportError(str(reason)) from exc
    except (socket.timeout, TimeoutError) as exc:
        raise _RetryableReportError(f"{type(exc).__name__}: {exc}") from exc
    except Exception as exc:
        raise _NonRetryableReportError(f"{type(exc).__name__}: {exc}") from exc

    if status not in (200, 201):
        raise _NonRetryableReportError(f"unexpected HTTP status {status}")

    receipt_id = payload.get("receipt_id") if isinstance(payload, dict) else None
    if not receipt_id:
        raise _NonRetryableReportError("server response missing receipt_id")

    return AttestationReport(attempted=True, succeeded=True, receipt_id=receipt_id)


def _report_attestation_with_retry(**kwargs) -> AttestationReport:
    """`_attempt_attestation_once`, plus one retry on timeout/5xx. Never raises.

    Safe to retry: the endpoint is idempotent on client_event_id, so a retry
    that lands on top of a write that actually succeeded the first time
    returns the original receipt rather than creating a duplicate. A 4xx is
    the server correctly rejecting the claim — retrying it would only add
    noise, so it is not retried.
    """
    try:
        return _attempt_attestation_once(**kwargs)
    except _NonRetryableReportError as exc:
        return AttestationReport(attempted=True, succeeded=False, reason=str(exc))
    except _RetryableReportError as first_exc:
        pass

    time.sleep(_REPORT_RETRY_BACKOFF_SECONDS)

    try:
        return _attempt_attestation_once(**kwargs)
    except _NonRetryableReportError as exc:
        return AttestationReport(attempted=True, succeeded=False, reason=str(exc))
    except _RetryableReportError as second_exc:
        client_event_id = kwargs.get("client_event_id")
        return AttestationReport(
            attempted=True,
            succeeded=False,
            reason=(
                f"not confirmed after retry: {second_exc}. A timeout or 5xx means the "
                f"outcome is unknown, not that the write was rejected. If it landed, "
                f"a later call with client_event_id={client_event_id!r} will return "
                f"the original receipt instead of writing again."
            ),
        )


def _run_attestation_report(report: AttestationReport, **kwargs) -> None:
    """Background-thread target: run the (retrying) network call and mutate
    `report` in place with the confirmed outcome. Never raises — errors
    from `_report_attestation_with_retry` are already captured as a failed
    AttestationReport, not an exception."""
    result = _report_attestation_with_retry(**kwargs)
    report.succeeded = result.succeeded
    report.receipt_id = result.receipt_id
    report.reason = result.reason


def detect_pii(
    text: str,
    custom_patterns: Optional[Dict[str, Pattern]] = None
) -> PIIResult:
    """
    Detect PII in text and return results with redacted text.

    Args:
        text: The text to scan for PII
        custom_patterns: Optional dict of custom regex patterns to detect

    Returns:
        PIIResult with detection results and redacted text
    """
    matches: List[PIIMatch] = []
    detected_types: Set[PIIType] = set()
    redacted_text = text

    # Check each PII pattern
    for pii_type, (pattern, redaction) in PII_PATTERNS.items():
        for match in pattern.finditer(text):
            detected_types.add(pii_type)
            matches.append(PIIMatch(
                type=pii_type,
                value='[REDACTED]',
                start_index=match.start(),
                end_index=match.end()
            ))
        redacted_text = pattern.sub(redaction, redacted_text)

    # Apply custom patterns
    if custom_patterns:
        for name, pattern in custom_patterns.items():
            redacted_text = pattern.sub(f'[{name.upper()}_REDACTED]', redacted_text)

    return PIIResult(
        has_pii=len(matches) > 0,
        types=list(detected_types),
        count=len(matches),
        matches=matches,
        redacted_text=redacted_text
    )


def redact_pii(text: str) -> str:
    """Convenience function to redact PII from text."""
    result = detect_pii(text)
    return result.redacted_text


class Tork:
    """
    Main Tork governance client.

    Example:
        >>> tork = Tork()
        >>> result = tork.govern("My SSN is 123-45-6789")
        >>> print(result.output)  # "My SSN is [SSN_REDACTED]"
        >>> print(result.receipt.receipt_id)  # "rcpt_..."
    """

    def __init__(
        self,
        config: Optional[TorkConfig] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        default_action: GovernanceAction = GovernanceAction.REDACT
    ):
        if config:
            self.config = config
        else:
            # Warn here (not via TorkConfig.__post_init__) so the warning
            # points at the customer's Tork(...) call rather than this file.
            if api_key:
                _warn_api_key_reporting(stacklevel=2)
            self.config = TorkConfig(
                policy_version=policy_version,
                default_action=default_action,
                api_key=api_key
            )

        self._stats = {
            'total_calls': 0,
            'total_pii_detected': 0,
            'total_processing_ns': 0,
            'action_counts': {action: 0 for action in GovernanceAction}
        }

    def govern(
        self,
        input_text: str,
        region: Optional[List[str]] = None,
        industry: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_role: Optional[str] = None,
        session_id: Optional[str] = None,
        session_turn: Optional[int] = None,
    ) -> GovernanceResult:
        """
        Apply governance rules to input text.

        Args:
            input_text: The text to govern
            region: Optional list of regional PII profiles to activate (e.g. ["ae", "in"])
            industry: Optional industry profile to activate (e.g. "healthcare", "finance", "legal")
            agent_id: Optional identifier for the agent making the call
            agent_role: Optional role of the agent ("planner", "worker", or "judge")
            session_id: Optional identifier that groups all calls from the same agent session
            session_turn: Optional position in the conversation (1, 2, 3...)

        Returns:
            GovernanceResult with action, output, PII info, and receipt
        """
        start_time = time.time_ns()

        # Detect PII
        pii = detect_pii(input_text, self.config.custom_patterns)

        # Determine action and output
        if pii.has_pii:
            action = self.config.default_action
            output = pii.redacted_text
        else:
            action = GovernanceAction.ALLOW
            output = input_text

        processing_time_ns = time.time_ns() - start_time

        # Build session context if any agent/session fields are provided
        session_context = None
        if any(v is not None for v in (agent_id, agent_role, session_id, session_turn)):
            session_context = SessionContext(
                agent_id=agent_id,
                agent_role=agent_role,
                session_id=session_id,
                session_turn=session_turn,
            )

        # Generate receipt
        receipt = Receipt(
            receipt_id=generate_receipt_id(),
            timestamp=datetime.utcnow().isoformat() + 'Z',
            input_hash=hash_text(input_text),
            output_hash=hash_text(output),
            action=action,
            policy_version=self.config.policy_version,
            processing_time_ns=processing_time_ns,
            pii_types=pii.types,
            pii_count=pii.count,
            session_context=session_context,
        )

        # Update stats
        self._stats['total_calls'] += 1
        if pii.has_pii:
            self._stats['total_pii_detected'] += 1
        self._stats['total_processing_ns'] += processing_time_ns
        self._stats['action_counts'][action] += 1

        # Optional metadata-only reporting to tork.network. The decision
        # above (action/output/pii/receipt) is already final by this point
        # and reporting can never change it. Canonical-form/fingerprint
        # construction is local and stays synchronous; the network call
        # (and its one retry) runs on a background thread so this method
        # always returns immediately regardless of endpoint latency, and a
        # reporting failure never raises into the caller.
        if self.config.api_key:
            try:
                verdict = _ACTION_TO_VERDICT[action]
                ts, decided_at = _decided_at_pair()
                canonical = build_canonical(
                    policy_version=self.config.policy_version,
                    verdict=verdict,
                    pii_types=[t.value for t in pii.types],
                    pii_count=pii.count,
                    hitl=(action == GovernanceAction.ESCALATE),
                    ts=ts,
                )
                cjson = canonical_json(canonical)
                salt = generate_fingerprint_salt()
                fingerprint = compute_salted_fingerprint(cjson, salt)
            except Exception as exc:
                report = AttestationReport(
                    attempted=True,
                    succeeded=False,
                    reason=f"failed to build attestation: {type(exc).__name__}: {exc}",
                )
            else:
                report = AttestationReport(
                    attempted=True,
                    succeeded=False,
                    reason="reporting in progress on a background thread; call report.wait() for the confirmed outcome",
                )
                thread = threading.Thread(
                    target=_run_attestation_report,
                    args=(report,),
                    kwargs=dict(
                        api_key=self.config.api_key,
                        client_event_id=receipt.receipt_id,
                        verdict=verdict,
                        canonical_json_str=cjson,
                        salt=salt,
                        fingerprint=fingerprint,
                        decided_at=decided_at,
                    ),
                    daemon=True,
                    name="tork-attestation-report",
                )
                report._thread = thread
                thread.start()
        else:
            report = AttestationReport(
                attempted=False,
                succeeded=False,
                reason="api_key not configured; reporting is disabled",
            )

        return GovernanceResult(
            action=action,
            output=output,
            pii=pii,
            receipt=receipt,
            region=region,
            industry=industry,
            session_context=session_context,
            report=report,
        )

    def get_stats(self) -> dict:
        """Get usage statistics."""
        avg_ns = 0
        if self._stats['total_calls'] > 0:
            avg_ns = self._stats['total_processing_ns'] // self._stats['total_calls']

        return {
            'total_calls': self._stats['total_calls'],
            'total_pii_detected': self._stats['total_pii_detected'],
            'avg_processing_time_ns': avg_ns,
            'action_counts': dict(self._stats['action_counts'])
        }

    def reset_stats(self) -> None:
        """Reset usage statistics."""
        self._stats = {
            'total_calls': 0,
            'total_pii_detected': 0,
            'total_processing_ns': 0,
            'action_counts': {action: 0 for action in GovernanceAction}
        }
