"""
Tork Governance SDK for Python

On-device AI governance with PII detection, redaction, and local audit receipts.
"""

from .core import (
    Tork,
    TorkConfig,
    PIIResult,
    GovernanceResult,
    Receipt,
    SessionContext,
    AttestationReport,
    detect_pii,
    redact_pii,
    hash_text,
    generate_receipt_id,
    PIIType,
    GovernanceAction,
    __version__,
)

__all__ = [
    "Tork",
    "TorkConfig",
    "PIIResult",
    "GovernanceResult",
    "Receipt",
    "SessionContext",
    "AttestationReport",
    "detect_pii",
    "redact_pii",
    "hash_text",
    "generate_receipt_id",
    "PIIType",
    "GovernanceAction",
    "__version__",
]
