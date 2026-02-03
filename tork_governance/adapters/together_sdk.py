"""
Tork Governance adapter for Together AI SDK.

Provides governance for Together AI inference
with automatic PII detection and policy enforcement.

Usage:
    from tork_governance.adapters.together_sdk import TorkTogetherClient

    client = TorkTogetherClient(api_key="...", tork=tork)
    response = client.chat([{"role": "user", "content": "My SSN is 123-45-6789"}])
"""

from typing import Any, Dict, List, Optional, Union
from functools import wraps


class TorkTogetherClient:
    """Governed Together AI client wrapper."""

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
        """Lazy initialize the Together client."""
        if self._client is None:
            try:
                from together import Together
                self._client = Together(api_key=self.api_key) if self.api_key else Together()
            except ImportError:
                raise ImportError(
                    "together is required. Install with: pip install together"
                )
        return self._client

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "meta-llama/Llama-3-70b-chat-hf",
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
            } if response.usage else {},
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
        model: str = "meta-llama/Llama-3-70b-chat-hf",
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

    def complete(
        self,
        prompt: str,
        model: str = "meta-llama/Llama-3-70b-chat-hf",
        **kwargs
    ) -> Dict[str, Any]:
        """Send governed completion request."""
        client = self._get_client()

        # Govern input prompt
        governed_prompt = prompt
        receipt = None
        if self.govern_input:
            result = self.tork.govern(prompt)
            governed_prompt = result.output if result.action in ('redact', 'REDACT') else prompt
            receipt = result.receipt

        response = client.completions.create(
            model=model,
            prompt=governed_prompt,
            **kwargs
        )

        # Govern output
        text = response.choices[0].text if response.choices else ""
        if self.govern_output and text:
            gov_result = self.tork.govern(text)
            text = gov_result.output if gov_result.action in ('redact', 'REDACT') else text

        return {
            "id": response.id,
            "model": response.model,
            "text": text,
            "usage": response.usage.__dict__ if response.usage else {},
            "_tork_receipt": receipt
        }

    def embeddings(
        self,
        texts: Union[str, List[str]],
        model: str = "togethercomputer/m2-bert-80M-8k-retrieval",
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

        response = client.embeddings.create(model=model, input=governed_texts, **kwargs)

        return {
            "model": response.model,
            "data": [{"embedding": d.embedding, "index": d.index} for d in response.data],
        }


class AsyncTorkTogetherClient:
    """Async governed Together AI client wrapper."""

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
        """Lazy initialize the async Together client."""
        if self._client is None:
            try:
                from together import AsyncTogether
                self._client = AsyncTogether(api_key=self.api_key) if self.api_key else AsyncTogether()
            except ImportError:
                raise ImportError(
                    "together is required. Install with: pip install together"
                )
        return self._client

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "meta-llama/Llama-3-70b-chat-hf",
        **kwargs
    ) -> Dict[str, Any]:
        """Send governed async chat completion request."""
        client = self._get_client()
        receipts = []

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

    async def complete(
        self,
        prompt: str,
        model: str = "meta-llama/Llama-3-70b-chat-hf",
        **kwargs
    ) -> Dict[str, Any]:
        """Send governed async completion request."""
        client = self._get_client()

        governed_prompt = prompt
        receipt = None
        if self.govern_input:
            result = self.tork.govern(prompt)
            governed_prompt = result.output if result.action in ('redact', 'REDACT') else prompt
            receipt = result.receipt

        response = await client.completions.create(
            model=model,
            prompt=governed_prompt,
            **kwargs
        )

        text = response.choices[0].text if response.choices else ""
        if self.govern_output and text:
            gov_result = self.tork.govern(text)
            text = gov_result.output if gov_result.action in ('redact', 'REDACT') else text

        return {
            "id": response.id,
            "model": response.model,
            "text": text,
            "_tork_receipt": receipt
        }

    async def embeddings(
        self,
        texts: Union[str, List[str]],
        model: str = "togethercomputer/m2-bert-80M-8k-retrieval",
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

        response = await client.embeddings.create(model=model, input=governed_texts, **kwargs)

        return {
            "model": response.model,
            "data": [{"embedding": d.embedding, "index": d.index} for d in response.data],
        }


def together_governed(tork: Any, govern_input: bool = True, govern_output: bool = True):
    """Decorator to govern Together AI API calls."""
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

            if 'prompt' in kwargs and govern_input:
                result = tork.govern(kwargs['prompt'])
                kwargs['prompt'] = result.output if result.action in ('redact', 'REDACT') else kwargs['prompt']

            return func(*args, **kwargs)
        return wrapper
    return decorator
