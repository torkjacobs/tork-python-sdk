"""
Tork Governance adapter for Rebuff.

Provides governance for Rebuff's prompt injection detection framework
with automatic PII detection and policy enforcement.

Usage:
    from tork_governance.adapters.rebuff_adapter import TorkRebuff

    rebuff = TorkRebuff(tork=tork)
    result = rebuff.detect_injection("My SSN is 123-45-6789")
"""

from typing import Any, Dict, List, Optional
from functools import wraps


class TorkRebuff:
    """Governed Rebuff wrapper combining prompt injection detection with PII governance."""

    def __init__(
        self,
        tork: Any = None,
        api_key: str = None,
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self.tork = tork
        self.api_key = api_key
        self.govern_input = govern_input
        self.govern_output = govern_output
        self._client = None

    def _get_client(self):
        """Lazy initialize the Rebuff client."""
        if self._client is None:
            try:
                from rebuff import Rebuff
                self._client = Rebuff(api_key=self.api_key) if self.api_key else Rebuff()
            except ImportError:
                raise ImportError(
                    "rebuff is required. Install with: pip install rebuff"
                )
        return self._client

    def detect_injection(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Detect prompt injection with PII governance."""
        receipts = []

        governed_prompt = prompt
        if self.govern_input and self.tork:
            result = self.tork.govern(prompt)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_prompt = result.output

        client = self._get_client()
        detection = client.detect_injection(governed_prompt, **kwargs)

        return {
            "injection_detected": detection.injection_detected if hasattr(detection, 'injection_detected') else False,
            "governed_prompt": governed_prompt,
            "_tork_receipts": receipts,
        }

    def is_injection(self, prompt: str, max_heuristic_score: float = 0.75) -> Dict[str, Any]:
        """Check if prompt is an injection attempt with PII governance."""
        receipts = []

        governed_prompt = prompt
        if self.govern_input and self.tork:
            result = self.tork.govern(prompt)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_prompt = result.output

        client = self._get_client()
        is_inj = client.is_injection(governed_prompt, max_heuristic_score=max_heuristic_score)

        return {
            "is_injection": is_inj,
            "governed_prompt": governed_prompt,
            "_tork_receipts": receipts,
        }


def rebuff_governed(tork: Any, govern_input: bool = True, govern_output: bool = True):
    """Decorator to govern Rebuff operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if govern_input:
                if args:
                    new_args = list(args)
                    for i, arg in enumerate(new_args):
                        if isinstance(arg, str):
                            result = tork.govern(arg)
                            if result.action in ('redact', 'REDACT'):
                                new_args[i] = result.output
                    args = tuple(new_args)
                if 'prompt' in kwargs:
                    result = tork.govern(kwargs['prompt'])
                    if result.action in ('redact', 'REDACT'):
                        kwargs['prompt'] = result.output
            return func(*args, **kwargs)
        return wrapper
    return decorator
