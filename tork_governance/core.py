"""
Tork Governance Core Module

PII detection, redaction, and governance with cryptographic receipts.
"""

import re
import hashlib
import secrets
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Pattern, Set
import time


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
class GovernanceResult:
    """Result of governance evaluation."""
    action: GovernanceAction
    output: str
    pii: PIIResult
    receipt: Receipt
    region: Optional[List[str]] = None
    industry: Optional[str] = None
    session_context: Optional[SessionContext] = None


_API_KEY_UNUSED_MESSAGE = (
    "You passed an api_key to tork-governance, but this package does not use it. "
    "tork-governance (Python) runs entirely on-device: it never authenticates with "
    "or sends any data to tork.network. Governance receipts are generated in local "
    "memory only, are discarded when your process exits, and will NOT appear in "
    "your tork.network dashboard. For cloud governance with persisted dashboard "
    "receipts, use the Node SDK (@torknetwork/sdk) or the Tork REST API. "
    "Remove the api_key argument to silence this warning."
)

# Module-level flag so the api_key warning fires at most once per process.
_api_key_warning_emitted = False


def _warn_api_key_unused(stacklevel: int = 2) -> None:
    """Warn once per process that api_key is accepted but unused.

    stacklevel is relative to the caller of this helper: 2 points at the
    caller's caller (i.e. the customer's line), exactly as if the caller
    had invoked warnings.warn(..., stacklevel=2) itself.
    """
    global _api_key_warning_emitted
    if _api_key_warning_emitted:
        return
    _api_key_warning_emitted = True
    warnings.warn(_API_KEY_UNUSED_MESSAGE, UserWarning, stacklevel=stacklevel + 1)


@dataclass
class TorkConfig:
    """Configuration for Tork client.

    Attributes:
        policy_version: Policy version string recorded on receipts.
        default_action: Action taken when PII is detected.
        custom_patterns: Optional custom regex patterns to detect.
        api_key: Accepted for API compatibility but currently UNUSED —
            this SDK is on-device only and never contacts tork.network.
            Providing a value emits a UserWarning (once per process).
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
            _warn_api_key_unused(stacklevel=3)


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
                _warn_api_key_unused(stacklevel=2)
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

        return GovernanceResult(
            action=action,
            output=output,
            pii=pii,
            receipt=receipt,
            region=region,
            industry=industry,
            session_context=session_context,
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
