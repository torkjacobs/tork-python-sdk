"""
Tork Governance SDK for Python

On-device AI governance with PII detection, redaction, and cryptographic receipts.
"""

from .core import (
    Tork,
    TorkConfig,
    PIIResult,
    GovernanceResult,
    Receipt,
    detect_pii,
    redact_pii,
    hash_text,
    generate_receipt_id,
    PIIType,
    GovernanceAction,
)

__version__ = "0.17.0"
__all__ = [
    "Tork",
    "TorkConfig",
    "PIIResult",
    "GovernanceResult",
    "Receipt",
    "detect_pii",
    "redact_pii",
    "hash_text",
    "generate_receipt_id",
    "PIIType",
    "GovernanceAction",
]
