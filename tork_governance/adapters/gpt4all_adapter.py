"""
Tork Governance adapter for GPT4All.

Provides governance for GPT4All's local LLM inference
with automatic PII detection and policy enforcement.

Usage:
    from tork_governance.adapters.gpt4all_adapter import TorkGPT4All

    client = TorkGPT4All(tork=tork, model_name="orca-mini-3b")
    response = client.generate("My SSN is 123-45-6789")
"""

from typing import Any, Dict, List, Optional
from functools import wraps


class TorkGPT4All:
    """Governed GPT4All wrapper."""

    def __init__(
        self,
        tork: Any = None,
        model_name: str = "orca-mini-3b-gguf2-q4_0.gguf",
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self.tork = tork
        self.model_name = model_name
        self.govern_input = govern_input
        self.govern_output = govern_output
        self._model = None

    def _get_model(self):
        """Lazy initialize the GPT4All model."""
        if self._model is None:
            try:
                from gpt4all import GPT4All
                self._model = GPT4All(self.model_name)
            except ImportError:
                raise ImportError(
                    "gpt4all is required. Install with: pip install gpt4all"
                )
        return self._model

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate governed text from GPT4All."""
        receipts = []

        governed_prompt = prompt
        if self.govern_input and self.tork:
            result = self.tork.govern(prompt)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_prompt = result.output

        model = self._get_model()
        response = model.generate(governed_prompt, **kwargs)

        content = str(response)
        if self.govern_output and self.tork and content:
            gov_result = self.tork.govern(content)
            if gov_result.action in ('redact', 'REDACT'):
                content = gov_result.output

        return {
            "content": content,
            "model": self.model_name,
            "_tork_receipts": receipts,
        }

    def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Chat with governed messages via GPT4All."""
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

        model = self._get_model()
        with model.chat_session():
            last_user_msg = ""
            for msg in governed_messages:
                if msg.get("role") == "user":
                    last_user_msg = msg["content"]

            response = model.generate(last_user_msg, **kwargs)

        content = str(response)
        if self.govern_output and self.tork and content:
            gov_result = self.tork.govern(content)
            if gov_result.action in ('redact', 'REDACT'):
                content = gov_result.output

        return {
            "content": content,
            "model": self.model_name,
            "_tork_receipts": receipts,
        }

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """OpenAI-compatible chat completion with governance."""
        result = self.chat(messages, **kwargs)
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": result["content"],
                },
                "finish_reason": "stop",
            }],
            "model": self.model_name,
            "_tork_receipts": result["_tork_receipts"],
        }


def gpt4all_governed(tork: Any, govern_input: bool = True, govern_output: bool = True):
    """Decorator to govern GPT4All calls."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if govern_input:
                if 'prompt' in kwargs:
                    result = tork.govern(kwargs['prompt'])
                    if result.action in ('redact', 'REDACT'):
                        kwargs['prompt'] = result.output
                if 'messages' in kwargs:
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
            return func(*args, **kwargs)
        return wrapper
    return decorator
