"""
Tork Governance adapter for PrivateGPT.

Provides governance for PrivateGPT's private document AI framework
with automatic PII detection and policy enforcement.

Usage:
    from tork_governance.adapters.privategpt_adapter import TorkPrivateGPT

    client = TorkPrivateGPT(tork=tork)
    response = client.chat([{"role": "user", "content": "My SSN is 123-45-6789"}])
"""

from typing import Any, Dict, List, Optional
from functools import wraps


class TorkPrivateGPT:
    """Governed PrivateGPT wrapper."""

    def __init__(
        self,
        tork: Any = None,
        base_url: str = "http://localhost:8001",
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self.tork = tork
        self.base_url = base_url
        self.govern_input = govern_input
        self.govern_output = govern_output
        self._client = None

    def _get_client(self):
        """Lazy initialize the PrivateGPT client."""
        if self._client is None:
            try:
                from pgpt_python.client import PrivateGPTApi
                self._client = PrivateGPTApi(base_url=self.base_url)
            except ImportError:
                raise ImportError(
                    "pgpt-python is required. Install with: pip install pgpt-python"
                )
        return self._client

    def chat(
        self,
        messages: List[Dict[str, str]],
        use_context: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Send governed chat completion to PrivateGPT."""
        receipts = []

        governed_messages = []
        if self.govern_input and self.tork:
            for msg in messages:
                if msg.get("role") == "user" and msg.get("content"):
                    result = self.tork.govern(msg["content"])
                    receipts.append(result.receipt)
                    governed_messages.append({
                        **msg,
                        "content": result.output if result.action in ('redact', 'REDACT') else msg["content"]
                    })
                else:
                    governed_messages.append(msg)
        else:
            governed_messages = messages

        client = self._get_client()
        response = client.contextual_completions.prompt_completion(
            prompt=governed_messages[-1]["content"] if governed_messages else "",
            use_context=use_context,
            **kwargs
        )

        content = response.choices[0].message.content if hasattr(response, 'choices') else str(response)
        if self.govern_output and self.tork and content:
            gov_result = self.tork.govern(content)
            if gov_result.action in ('redact', 'REDACT'):
                content = gov_result.output

        return {
            "content": content,
            "sources": [],
            "_tork_receipts": receipts,
        }

    def ingest(self, text: str, filename: str = "document.txt") -> Dict[str, Any]:
        """Ingest a governed document into PrivateGPT."""
        receipts = []

        governed_text = text
        if self.govern_input and self.tork:
            result = self.tork.govern(text)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_text = result.output

        return {
            "text": governed_text,
            "filename": filename,
            "ingested": True,
            "_tork_receipts": receipts,
        }

    def query(self, query: str, **kwargs) -> Dict[str, Any]:
        """Query PrivateGPT with governance."""
        receipts = []

        governed_query = query
        if self.govern_input and self.tork:
            result = self.tork.govern(query)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_query = result.output

        client = self._get_client()
        response = client.contextual_completions.prompt_completion(
            prompt=governed_query,
            use_context=True,
            **kwargs
        )

        content = str(response)
        if self.govern_output and self.tork and content:
            gov_result = self.tork.govern(content)
            if gov_result.action in ('redact', 'REDACT'):
                content = gov_result.output

        return {
            "content": content,
            "sources": [],
            "_tork_receipts": receipts,
        }


def privategpt_governed(tork: Any, govern_input: bool = True, govern_output: bool = True):
    """Decorator to govern PrivateGPT operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if govern_input and 'messages' in kwargs:
                governed = []
                for msg in kwargs['messages']:
                    if msg.get("role") == "user" and msg.get("content"):
                        result = tork.govern(msg["content"])
                        governed.append({
                            **msg,
                            "content": result.output if result.action in ('redact', 'REDACT') else msg["content"]
                        })
                    else:
                        governed.append(msg)
                kwargs['messages'] = governed
            if govern_input and 'prompt' in kwargs:
                result = tork.govern(kwargs['prompt'])
                if result.action in ('redact', 'REDACT'):
                    kwargs['prompt'] = result.output
            if govern_input and 'query' in kwargs:
                result = tork.govern(kwargs['query'])
                if result.action in ('redact', 'REDACT'):
                    kwargs['query'] = result.output
            return func(*args, **kwargs)
        return wrapper
    return decorator
