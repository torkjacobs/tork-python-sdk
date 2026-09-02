"""
Tork Governance SDK for Python

On-device AI governance with PII detection, redaction, and local audit receipts.
"""

from .core import (
    Tork,
    TorkConfig,
    PIIResult,
    GovernanceResult,
    GovernedToolResultScanResult,
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
from .tool_result_scan import (
    scan_tool_result,
    build_tool_result_scan_block,
    scan_pii_types,
    scan_pii_count,
    scan_injection_count,
    INJECTION_HEURISTIC_PREFIX,
    INJECTION_RULESET,
    INJECTION_TYPES,
    ToolResultFinding,
    ToolResultScanResult,
)

__all__ = [
    "Tork",
    "TorkConfig",
    "PIIResult",
    "GovernanceResult",
    "GovernedToolResultScanResult",
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
    "scan_tool_result",
    "build_tool_result_scan_block",
    "scan_pii_types",
    "scan_pii_count",
    "scan_injection_count",
    "INJECTION_HEURISTIC_PREFIX",
    "INJECTION_RULESET",
    "INJECTION_TYPES",
    "ToolResultFinding",
    "ToolResultScanResult",
]
