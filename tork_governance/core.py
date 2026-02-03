"""
Tork Governance Core Module

PII detection, redaction, and governance with cryptographic receipts.
"""

import re
import hashlib
import secrets
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


@dataclass
class TorkConfig:
    """Configuration for Tork client."""
    policy_version: str = "1.0.0"
    default_action: GovernanceAction = GovernanceAction.REDACT
    custom_patterns: Optional[Dict[str, Pattern]] = None
    api_key: Optional[str] = None


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
                value=match.group(),
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

    def govern(self, input_text: str) -> GovernanceResult:
        """
        Apply governance rules to input text.

        Args:
            input_text: The text to govern

        Returns:
            GovernanceResult with action, output, PII info, and receipt
        """
        start_time = time.time_ns()

        # Detect PII
        pii = detect_pii(input_text, self.config.custom_patterns)

        # Determine action and output
        if pii.has_pii:
            action = self.config.default_action
            output = pii.redacted_text if action == GovernanceAction.REDACT else input_text
        else:
            action = GovernanceAction.ALLOW
            output = input_text

        processing_time_ns = time.time_ns() - start_time

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
            pii_count=pii.count
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
            receipt=receipt
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
