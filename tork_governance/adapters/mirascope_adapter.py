"""
Tork Governance adapter for Mirascope.

Provides governance for Mirascope's decorator-based LLM call framework
with automatic PII detection and policy enforcement.

Usage:
    from tork_governance.adapters.mirascope_adapter import TorkMirascopeCall

    call = TorkMirascopeCall(tork=tork)
    response = call.call("My SSN is 123-45-6789")
"""

from typing import Any, Dict, List, Optional
from functools import wraps


class TorkMirascopeCall:
    """Governed Mirascope call wrapper."""

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
        """Lazy initialize the Mirascope client."""
        if self._client is None:
            try:
                import mirascope
                self._client = mirascope
            except ImportError:
                raise ImportError(
                    "mirascope is required. Install with: pip install mirascope"
                )
        return self._client

    def call(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Execute a governed Mirascope call."""
        receipts = []

        # Govern input
        governed_prompt = prompt
        if self.govern_input and self.tork:
            result = self.tork.govern(prompt)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_prompt = result.output

        # Make call via Mirascope
        client = self._get_client()
        response = client.chat(
            model=self.model,
            messages=[{"role": "user", "content": governed_prompt}],
            **kwargs
        )

        # Govern output
        content = response.content if hasattr(response, 'content') else str(response)
        if self.govern_output and self.tork and content:
            gov_result = self.tork.govern(content)
            if gov_result.action in ('redact', 'REDACT'):
                content = gov_result.output

        return {
            "content": content,
            "model": self.model,
            "_tork_receipts": receipts,
        }

    def stream(self, prompt: str, **kwargs):
        """Stream a governed Mirascope call."""
        receipts = []

        governed_prompt = prompt
        if self.govern_input and self.tork:
            result = self.tork.govern(prompt)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_prompt = result.output

        client = self._get_client()
        for chunk in client.chat(
            model=self.model,
            messages=[{"role": "user", "content": governed_prompt}],
            stream=True,
            **kwargs
        ):
            yield chunk

    def extract(self, prompt: str, response_model: Any = None, **kwargs) -> Dict[str, Any]:
        """Extract structured data with governance."""
        receipts = []

        governed_prompt = prompt
        if self.govern_input and self.tork:
            result = self.tork.govern(prompt)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_prompt = result.output

        client = self._get_client()
        response = client.extract(
            model=self.model,
            prompt=governed_prompt,
            response_model=response_model,
            **kwargs
        )

        return {
            "data": response,
            "_tork_receipts": receipts,
        }


def mirascope_governed(tork: Any, govern_input: bool = True, govern_output: bool = True):
    """Decorator to govern Mirascope calls."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if govern_input and args:
                new_args = list(args)
                for i, arg in enumerate(new_args):
                    if isinstance(arg, str):
                        result = tork.govern(arg)
                        if result.action in ('redact', 'REDACT'):
                            new_args[i] = result.output
                args = tuple(new_args)
            if govern_input and 'prompt' in kwargs:
                result = tork.govern(kwargs['prompt'])
                if result.action in ('redact', 'REDACT'):
                    kwargs['prompt'] = result.output
            return func(*args, **kwargs)
        return wrapper
    return decorator
