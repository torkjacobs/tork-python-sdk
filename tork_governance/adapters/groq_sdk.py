"""
Tork Governance adapter for Groq SDK.

Provides governance for Groq's ultra-fast LLM inference
with automatic PII detection and policy enforcement.

Usage:
    from tork_governance.adapters.groq_sdk import TorkGroqClient

    client = TorkGroqClient(api_key="...", tork=tork)
    response = client.chat([{"role": "user", "content": "My SSN is 123-45-6789"}])
"""

from typing import Any, Dict, List, Optional, Union
from functools import wraps


class TorkGroqClient:
    """Governed Groq client wrapper."""

    def __init__(
        self,
        api_key: str = None,
        tork: Any = None,
        govern_input: bool = True,
        govern_output: bool = True
    ):
        self.api_key = api_key
        self.tork = tork
        self.govern_input = govern_input
        self.govern_output = govern_output
        self._client = None

    def _get_client(self):
        """Lazy initialize the Groq client."""
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key) if self.api_key else Groq()
            except ImportError:
                raise ImportError(
                    "groq is required. Install with: pip install groq"
                )
        return self._client

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "llama-3.1-70b-versatile",
        **kwargs
    ) -> Dict[str, Any]:
        """Send governed chat completion request."""
        client = self._get_client()
        receipts = []

        # Govern input messages
        governed_messages = []
        if self.govern_input:
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

        # Make API call
        response = client.chat.completions.create(
            model=model,
            messages=governed_messages,
            **kwargs
        )

        # Convert to dict and govern output
        result_dict = {
            "id": response.id,
            "model": response.model,
            "choices": [],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "_tork_receipts": receipts
        }

        for choice in response.choices:
            content = choice.message.content

            # Govern output
            if self.govern_output and content:
                gov_result = self.tork.govern(content)
                content = gov_result.output if gov_result.action in ('redact', 'REDACT') else content

            result_dict["choices"].append({
                "index": choice.index,
                "message": {
                    "role": choice.message.role,
                    "content": content
                },
                "finish_reason": choice.finish_reason
            })

        return result_dict

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "llama-3.1-70b-versatile",
        **kwargs
    ):
        """Stream governed chat completion."""
        client = self._get_client()

        # Govern input messages
        governed_messages = []
        if self.govern_input:
            for msg in messages:
                if msg.get("role") == "user" and msg.get("content"):
                    result = self.tork.govern(msg["content"])
                    governed_messages.append({
                        **msg,
                        "content": result.output if result.action in ('redact', 'REDACT') else msg["content"]
                    })
                else:
                    governed_messages.append(msg)
        else:
            governed_messages = messages

        for chunk in client.chat.completions.create(
            model=model,
            messages=governed_messages,
            stream=True,
            **kwargs
        ):
            yield chunk

    def transcribe(
        self,
        file: Any,
        model: str = "whisper-large-v3",
        **kwargs
    ) -> Dict[str, Any]:
        """Transcribe audio with governed output."""
        client = self._get_client()

        response = client.audio.transcriptions.create(
            file=file,
            model=model,
            **kwargs
        )

        # Govern transcription output
        text = response.text
        receipt = None
        if self.govern_output and text:
            result = self.tork.govern(text)
            text = result.output if result.action in ('redact', 'REDACT') else text
            receipt = result.receipt

        return {
            "text": text,
            "_tork_receipt": receipt
        }


class AsyncTorkGroqClient:
    """Async governed Groq client wrapper."""

    def __init__(
        self,
        api_key: str = None,
        tork: Any = None,
        govern_input: bool = True,
        govern_output: bool = True
    ):
        self.api_key = api_key
        self.tork = tork
        self.govern_input = govern_input
        self.govern_output = govern_output
        self._client = None

    def _get_client(self):
        """Lazy initialize the async Groq client."""
        if self._client is None:
            try:
                from groq import AsyncGroq
                self._client = AsyncGroq(api_key=self.api_key) if self.api_key else AsyncGroq()
            except ImportError:
                raise ImportError(
                    "groq is required. Install with: pip install groq"
                )
        return self._client

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "llama-3.1-70b-versatile",
        **kwargs
    ) -> Dict[str, Any]:
        """Send governed async chat completion request."""
        client = self._get_client()
        receipts = []

        # Govern input messages
        governed_messages = []
        if self.govern_input:
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

        response = await client.chat.completions.create(
            model=model,
            messages=governed_messages,
            **kwargs
        )

        result_dict = {
            "id": response.id,
            "model": response.model,
            "choices": [],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "_tork_receipts": receipts
        }

        for choice in response.choices:
            content = choice.message.content
            if self.govern_output and content:
                gov_result = self.tork.govern(content)
                content = gov_result.output if gov_result.action in ('redact', 'REDACT') else content

            result_dict["choices"].append({
                "index": choice.index,
                "message": {"role": choice.message.role, "content": content},
                "finish_reason": choice.finish_reason
            })

        return result_dict

    async def transcribe(
        self,
        file: Any,
        model: str = "whisper-large-v3",
        **kwargs
    ) -> Dict[str, Any]:
        """Async transcribe audio with governed output."""
        client = self._get_client()

        response = await client.audio.transcriptions.create(
            file=file,
            model=model,
            **kwargs
        )

        text = response.text
        receipt = None
        if self.govern_output and text:
            result = self.tork.govern(text)
            text = result.output if result.action in ('redact', 'REDACT') else text
            receipt = result.receipt

        return {
            "text": text,
            "_tork_receipt": receipt
        }


def groq_governed(tork: Any, govern_input: bool = True, govern_output: bool = True):
    """Decorator to govern Groq API calls."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if 'messages' in kwargs and govern_input:
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
