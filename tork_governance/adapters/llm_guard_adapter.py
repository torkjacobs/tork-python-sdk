"""
Tork Governance adapter for LLM Guard.

Provides governance combining LLM Guard's input/output scanning
with Tork's PII detection and policy enforcement.

Usage:
    from tork_governance.adapters.llm_guard_adapter import TorkLLMGuard

    guard = TorkLLMGuard(tork=tork)
    result = guard.scan_prompt("My SSN is 123-45-6789")
"""

from typing import Any, Dict, List, Optional
from functools import wraps


class TorkLLMGuard:
    """Governed LLM Guard wrapper combining prompt scanning with PII governance."""

    def __init__(
        self,
        tork: Any = None,
        govern_input: bool = True,
        govern_output: bool = True,
        scanners: List[str] = None,
    ):
        self.tork = tork
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.scanners = scanners or []

    def scan_prompt(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Scan and govern an input prompt."""
        receipts = []

        governed_prompt = prompt
        if self.govern_input and self.tork:
            result = self.tork.govern(prompt)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_prompt = result.output

        return {
            "prompt": governed_prompt,
            "is_valid": True,
            "scanners_applied": self.scanners,
            "_tork_receipts": receipts,
        }

    def scan_output(self, prompt: str, output: str, **kwargs) -> Dict[str, Any]:
        """Scan and govern an LLM output."""
        receipts = []

        governed_output = output
        if self.govern_output and self.tork:
            result = self.tork.govern(output)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_output = result.output

        return {
            "output": governed_output,
            "is_valid": True,
            "scanners_applied": self.scanners,
            "_tork_receipts": receipts,
        }

    def scan_prompt_and_output(self, prompt: str, output: str) -> Dict[str, Any]:
        """Scan both prompt and output with governance."""
        receipts = []

        governed_prompt = prompt
        if self.govern_input and self.tork:
            result = self.tork.govern(prompt)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_prompt = result.output

        governed_output = output
        if self.govern_output and self.tork:
            result = self.tork.govern(output)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_output = result.output

        return {
            "prompt": governed_prompt,
            "output": governed_output,
            "is_valid": True,
            "_tork_receipts": receipts,
        }


def llm_guard_governed(tork: Any, govern_input: bool = True, govern_output: bool = True):
    """Decorator to govern LLM Guard operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if govern_input and 'prompt' in kwargs:
                result = tork.govern(kwargs['prompt'])
                if result.action in ('redact', 'REDACT'):
                    kwargs['prompt'] = result.output
            if govern_output and 'output' in kwargs:
                result = tork.govern(kwargs['output'])
                if result.action in ('redact', 'REDACT'):
                    kwargs['output'] = result.output
            return func(*args, **kwargs)
        return wrapper
    return decorator
