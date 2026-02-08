"""
Tork Governance adapter for LocalAI.

Provides governance for LocalAI's OpenAI-compatible local LLM server
with automatic PII detection and policy enforcement.

Usage:
    from tork_governance.adapters.localai_adapter import TorkLocalAIClient

    client = TorkLocalAIClient(tork=tork, base_url="http://localhost:8080")
    response = client.chat([{"role": "user", "content": "My SSN is 123-45-6789"}])
"""

from typing import Any, Dict, List, Optional
from functools import wraps


class TorkLocalAIClient:
    """Governed LocalAI client wrapper."""

    def __init__(
        self,
        tork: Any = None,
        base_url: str = "http://localhost:8080",
        api_key: str = None,
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self.tork = tork
        self.base_url = base_url
        self.api_key = api_key
        self.govern_input = govern_input
        self.govern_output = govern_output
        self._client = None

    def _get_client(self):
        """Lazy initialize the LocalAI client (OpenAI-compatible)."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    base_url=f"{self.base_url}/v1",
                    api_key=self.api_key or "not-needed",
                )
            except ImportError:
                raise ImportError(
                    "openai is required for LocalAI. Install with: pip install openai"
                )
        return self._client

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        **kwargs
    ) -> Dict[str, Any]:
        """Send governed chat completion to LocalAI."""
        client = self._get_client()
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

        response = client.chat.completions.create(
            model=model,
            messages=governed_messages,
            **kwargs
        )

        result_dict = {
            "id": response.id,
            "model": response.model,
            "choices": [],
            "_tork_receipts": receipts,
        }

        for choice in response.choices:
            content = choice.message.content
            if self.govern_output and self.tork and content:
                gov_result = self.tork.govern(content)
                if gov_result.action in ('redact', 'REDACT'):
                    content = gov_result.output

            result_dict["choices"].append({
                "index": choice.index,
                "message": {"role": choice.message.role, "content": content},
                "finish_reason": choice.finish_reason,
            })

        return result_dict

    def generate(self, prompt: str, model: str = "gpt-3.5-turbo", **kwargs) -> Dict[str, Any]:
        """Send governed completion to LocalAI."""
        receipts = []

        governed_prompt = prompt
        if self.govern_input and self.tork:
            result = self.tork.govern(prompt)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_prompt = result.output

        client = self._get_client()
        response = client.completions.create(
            model=model,
            prompt=governed_prompt,
            **kwargs
        )

        text = response.choices[0].text if response.choices else ""
        if self.govern_output and self.tork and text:
            gov_result = self.tork.govern(text)
            if gov_result.action in ('redact', 'REDACT'):
                text = gov_result.output

        return {
            "text": text,
            "_tork_receipts": receipts,
        }


def localai_governed(tork: Any, govern_input: bool = True, govern_output: bool = True):
    """Decorator to govern LocalAI calls."""
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
            return func(*args, **kwargs)
        return wrapper
    return decorator
