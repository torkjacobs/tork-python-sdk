"""
Tork Governance adapter for Mistral AI SDK.

Provides governance for Mistral chat, embeddings, and function calls
with automatic PII detection and policy enforcement.

Usage:
    from tork_governance.adapters.mistral_sdk import TorkMistralClient

    client = TorkMistralClient(api_key="...", tork=tork)
    response = client.chat("My SSN is 123-45-6789")
"""

from typing import Any, Dict, List, Optional, Union
from functools import wraps


class TorkMistralClient:
    """Governed Mistral AI client wrapper."""

    def __init__(
        self,
        api_key: str,
        tork: Any,
        govern_input: bool = True,
        govern_output: bool = True
    ):
        self.api_key = api_key
        self.tork = tork
        self.govern_input = govern_input
        self.govern_output = govern_output
        self._client = None

    def _get_client(self):
        """Lazy initialize the Mistral client."""
        if self._client is None:
            try:
                from mistralai.client import MistralClient
                self._client = MistralClient(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "mistralai is required. Install with: pip install mistralai"
                )
        return self._client

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "mistral-small-latest",
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
        from mistralai.models.chat_completion import ChatMessage
        chat_messages = [
            ChatMessage(role=m["role"], content=m["content"])
            for m in governed_messages
        ]

        response = client.chat(
            model=model,
            messages=chat_messages,
            **kwargs
        )

        # Convert to dict
        result_dict = {
            "id": response.id,
            "model": response.model,
            "choices": [],
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
        model: str = "mistral-small-latest",
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

        from mistralai.models.chat_completion import ChatMessage
        chat_messages = [
            ChatMessage(role=m["role"], content=m["content"])
            for m in governed_messages
        ]

        for chunk in client.chat_stream(model=model, messages=chat_messages, **kwargs):
            yield chunk

    def embeddings(
        self,
        texts: Union[str, List[str]],
        model: str = "mistral-embed",
        **kwargs
    ) -> Dict[str, Any]:
        """Get governed embeddings."""
        client = self._get_client()

        # Normalize to list
        if isinstance(texts, str):
            texts = [texts]

        # Govern input texts
        governed_texts = []
        if self.govern_input:
            for text in texts:
                result = self.tork.govern(text)
                governed_texts.append(
                    result.output if result.action in ('redact', 'REDACT') else text
                )
        else:
            governed_texts = texts

        response = client.embeddings(model=model, input=governed_texts, **kwargs)

        return {
            "model": response.model,
            "data": [{"embedding": d.embedding, "index": d.index} for d in response.data],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }


class AsyncTorkMistralClient:
    """Async governed Mistral AI client wrapper."""

    def __init__(
        self,
        api_key: str,
        tork: Any,
        govern_input: bool = True,
        govern_output: bool = True
    ):
        self.api_key = api_key
        self.tork = tork
        self.govern_input = govern_input
        self.govern_output = govern_output
        self._client = None

    def _get_client(self):
        """Lazy initialize the async Mistral client."""
        if self._client is None:
            try:
                from mistralai.async_client import MistralAsyncClient
                self._client = MistralAsyncClient(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "mistralai is required. Install with: pip install mistralai"
                )
        return self._client

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "mistral-small-latest",
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

        from mistralai.models.chat_completion import ChatMessage
        chat_messages = [
            ChatMessage(role=m["role"], content=m["content"])
            for m in governed_messages
        ]

        response = await client.chat(model=model, messages=chat_messages, **kwargs)

        result_dict = {
            "id": response.id,
            "model": response.model,
            "choices": [],
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

    async def embeddings(
        self,
        texts: Union[str, List[str]],
        model: str = "mistral-embed",
        **kwargs
    ) -> Dict[str, Any]:
        """Get governed async embeddings."""
        client = self._get_client()

        if isinstance(texts, str):
            texts = [texts]

        governed_texts = []
        if self.govern_input:
            for text in texts:
                result = self.tork.govern(text)
                governed_texts.append(
                    result.output if result.action in ('redact', 'REDACT') else text
                )
        else:
            governed_texts = texts

        response = await client.embeddings(model=model, input=governed_texts, **kwargs)

        return {
            "model": response.model,
            "data": [{"embedding": d.embedding, "index": d.index} for d in response.data],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }


def mistral_governed(tork: Any, govern_input: bool = True, govern_output: bool = True):
    """Decorator to govern Mistral API calls."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Govern messages if present
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
