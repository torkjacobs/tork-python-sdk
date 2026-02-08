"""
Tork Governance adapter for Magentic.

Provides governance for Magentic's @prompt decorator framework
with automatic PII detection and policy enforcement.

Usage:
    from tork_governance.adapters.magentic_adapter import TorkMagenticPrompt

    prompt = TorkMagenticPrompt(tork=tork)
    response = prompt.call("My SSN is 123-45-6789")
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps


class TorkMagenticPrompt:
    """Governed Magentic prompt wrapper."""

    def __init__(
        self,
        tork: Any = None,
        govern_input: bool = True,
        govern_output: bool = True,
        model: str = "gpt-3.5-turbo",
    ):
        self.tork = tork
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.model = model
        self._client = None

    def _get_client(self):
        """Lazy initialize the Magentic module."""
        if self._client is None:
            try:
                import magentic
                self._client = magentic
            except ImportError:
                raise ImportError(
                    "magentic is required. Install with: pip install magentic"
                )
        return self._client

    def call(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Execute a governed Magentic prompt call."""
        receipts = []

        governed_prompt = prompt
        if self.govern_input and self.tork:
            result = self.tork.govern(prompt)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_prompt = result.output

        client = self._get_client()
        response = client.prompt(governed_prompt, model=self.model, **kwargs)

        content = str(response)
        if self.govern_output and self.tork and content:
            gov_result = self.tork.govern(content)
            if gov_result.action in ('redact', 'REDACT'):
                content = gov_result.output

        return {
            "content": content,
            "model": self.model,
            "_tork_receipts": receipts,
        }

    def wrap_prompt_function(self, func: Callable) -> Callable:
        """Wrap a @prompt decorated function with governance."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.govern_input:
                new_args = list(args)
                for i, arg in enumerate(new_args):
                    if isinstance(arg, str) and self.tork:
                        result = self.tork.govern(arg)
                        if result.action in ('redact', 'REDACT'):
                            new_args[i] = result.output
                args = tuple(new_args)
                for key, val in kwargs.items():
                    if isinstance(val, str) and self.tork:
                        result = self.tork.govern(val)
                        if result.action in ('redact', 'REDACT'):
                            kwargs[key] = result.output

            output = func(*args, **kwargs)

            if self.govern_output and self.tork and isinstance(output, str):
                gov_result = self.tork.govern(output)
                if gov_result.action in ('redact', 'REDACT'):
                    output = gov_result.output

            return output
        return wrapper


def magentic_governed(tork: Any, govern_input: bool = True, govern_output: bool = True):
    """Decorator to govern Magentic prompt functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if govern_input:
                new_args = list(args)
                for i, arg in enumerate(new_args):
                    if isinstance(arg, str):
                        result = tork.govern(arg)
                        if result.action in ('redact', 'REDACT'):
                            new_args[i] = result.output
                args = tuple(new_args)
            result = func(*args, **kwargs)
            if govern_output and isinstance(result, str):
                gov_result = tork.govern(result)
                if gov_result.action in ('redact', 'REDACT'):
                    result = gov_result.output
            return result
        return wrapper
    return decorator
