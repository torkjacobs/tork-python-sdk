"""
LiteLLM adapter for Tork Governance.

Provides governance integration for LiteLLM, a unified interface to 100+ LLMs.
Supports completion calls, streaming responses, and custom callbacks.

Example:
    from litellm import completion
    from tork_governance.adapters.litellm import govern_completion, TorkLiteLLMCallback

    # Use governed completion
    response = govern_completion(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "My SSN is 123-45-6789"}]
    )

    # Use callback handler
    callback = TorkLiteLLMCallback()
    response = completion(
        model="gpt-3.5-turbo",
        messages=[...],
        callbacks=[callback]
    )
"""

from typing import Any, Callable, Dict, Generator, List, Optional, Union
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkLiteLLMCallback:
    """
    LiteLLM callback handler for Tork governance.

    Intercepts completion calls and applies governance to both
    input messages and output responses.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        govern_input: bool = True,
        govern_output: bool = True,
        on_pii_detected: Optional[Callable[[GovernanceResult], None]] = None,
    ):
        self.tork = Tork(api_key=api_key)
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.on_pii_detected = on_pii_detected
        self._receipts: List[str] = []
        self._last_result: Optional[GovernanceResult] = None

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[Dict[str, Any]]],
        **kwargs
    ) -> List[List[Dict[str, Any]]]:
        """Called when LLM starts, governs input messages."""
        if not self.govern_input:
            return messages

        governed_messages = []
        for message_list in messages:
            governed_list = []
            for msg in message_list:
                if isinstance(msg.get("content"), str):
                    result = self.tork.govern(msg["content"])
                    governed_msg = msg.copy()
                    governed_msg["content"] = result.output

                    if result.receipt:
                        self._receipts.append(result.receipt.receipt_id)

                    if result.pii.has_pii and self.on_pii_detected:
                        self.on_pii_detected(result)

                    governed_list.append(governed_msg)
                else:
                    governed_list.append(msg)
            governed_messages.append(governed_list)

        return governed_messages

    def on_llm_end(self, response: Any, **kwargs) -> Any:
        """Called when LLM ends, governs output response."""
        if not self.govern_output:
            return response

        # Handle different response formats
        if hasattr(response, "choices"):
            for choice in response.choices:
                if hasattr(choice, "message") and hasattr(choice.message, "content"):
                    if isinstance(choice.message.content, str):
                        result = self.tork.govern(choice.message.content)
                        choice.message.content = result.output
                        self._last_result = result

                        if result.receipt:
                            self._receipts.append(result.receipt.receipt_id)

        return response

    def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Called on LLM error."""
        pass

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipt IDs."""
        return self._receipts.copy()

    @property
    def last_result(self) -> Optional[GovernanceResult]:
        """Get the last governance result."""
        return self._last_result


class TorkLiteLLMProxy:
    """
    Proxy client that wraps LiteLLM with Tork governance.

    Provides a drop-in replacement for litellm with automatic governance.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        govern_input: bool = True,
        govern_output: bool = True,
        default_model: str = "gpt-3.5-turbo",
    ):
        self.tork = Tork(api_key=api_key)
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.default_model = default_model
        self._receipts: List[str] = []

    def _govern_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Govern a list of messages."""
        governed = []
        for msg in messages:
            if isinstance(msg.get("content"), str):
                result = self.tork.govern(msg["content"])
                governed_msg = msg.copy()
                governed_msg["content"] = result.output
                if result.receipt:
                    self._receipts.append(result.receipt.receipt_id)
                governed.append(governed_msg)
            else:
                governed.append(msg)
        return governed

    def _govern_response(self, response: Any) -> Any:
        """Govern an LLM response."""
        if hasattr(response, "choices"):
            for choice in response.choices:
                if hasattr(choice, "message") and hasattr(choice.message, "content"):
                    if isinstance(choice.message.content, str):
                        result = self.tork.govern(choice.message.content)
                        choice.message.content = result.output
                        if result.receipt:
                            self._receipts.append(result.receipt.receipt_id)
        return response

    def completion(
        self,
        model: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs
    ) -> Any:
        """
        Governed completion call.

        Wraps litellm.completion with governance applied to
        input messages and output responses.
        """
        try:
            import litellm
        except ImportError:
            raise ImportError("litellm is required: pip install litellm")

        model = model or self.default_model
        messages = messages or []

        # Govern input
        if self.govern_input:
            messages = self._govern_messages(messages)

        # Handle streaming
        if stream:
            return self._stream_completion(litellm, model, messages, **kwargs)

        # Non-streaming completion
        response = litellm.completion(model=model, messages=messages, **kwargs)

        # Govern output
        if self.govern_output:
            response = self._govern_response(response)

        return response

    def _stream_completion(
        self,
        litellm: Any,
        model: str,
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> Generator[Any, None, None]:
        """Stream completion with governance on final response."""
        response = litellm.completion(
            model=model,
            messages=messages,
            stream=True,
            **kwargs
        )

        full_content = ""
        for chunk in response:
            if hasattr(chunk, "choices") and chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    full_content += delta.content
            yield chunk

        # Govern the accumulated response
        if self.govern_output and full_content:
            result = self.tork.govern(full_content)
            if result.receipt:
                self._receipts.append(result.receipt.receipt_id)

    def acompletion(
        self,
        model: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Any:
        """Async governed completion call."""
        try:
            import litellm
        except ImportError:
            raise ImportError("litellm is required: pip install litellm")

        import asyncio

        model = model or self.default_model
        messages = messages or []

        # Govern input
        if self.govern_input:
            messages = self._govern_messages(messages)

        async def _async_completion():
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                **kwargs
            )

            # Govern output
            if self.govern_output:
                response = self._govern_response(response)

            return response

        return _async_completion()

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipt IDs."""
        return self._receipts.copy()


def govern_completion(
    model: str,
    messages: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    govern_input: bool = True,
    govern_output: bool = True,
    **kwargs
) -> Any:
    """
    Governed LiteLLM completion call.

    Convenience function that wraps litellm.completion with governance.

    Example:
        response = govern_completion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "My email is test@example.com"}]
        )
    """
    proxy = TorkLiteLLMProxy(
        api_key=api_key,
        govern_input=govern_input,
        govern_output=govern_output,
    )
    return proxy.completion(model=model, messages=messages, **kwargs)


async def agovern_completion(
    model: str,
    messages: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    govern_input: bool = True,
    govern_output: bool = True,
    **kwargs
) -> Any:
    """
    Async governed LiteLLM completion call.

    Example:
        response = await agovern_completion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "My SSN is 123-45-6789"}]
        )
    """
    proxy = TorkLiteLLMProxy(
        api_key=api_key,
        govern_input=govern_input,
        govern_output=govern_output,
    )
    return await proxy.acompletion(model=model, messages=messages, **kwargs)


def litellm_governed(
    api_key: Optional[str] = None,
    govern_input: bool = True,
    govern_output: bool = True,
):
    """
    Decorator to add Tork governance to LiteLLM-based functions.

    Example:
        @litellm_governed()
        def my_chat_function(messages: List[Dict]) -> str:
            response = litellm.completion(model="gpt-3.5-turbo", messages=messages)
            return response.choices[0].message.content
    """
    def decorator(func: Callable) -> Callable:
        tork = Tork(api_key=api_key)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Govern message arguments
            if govern_input:
                new_args = []
                for arg in args:
                    if isinstance(arg, list) and arg and isinstance(arg[0], dict):
                        # Assume it's a messages list
                        governed = []
                        for msg in arg:
                            if isinstance(msg.get("content"), str):
                                result = tork.govern(msg["content"])
                                governed_msg = msg.copy()
                                governed_msg["content"] = result.output
                                governed.append(governed_msg)
                            else:
                                governed.append(msg)
                        new_args.append(governed)
                    else:
                        new_args.append(arg)
                args = tuple(new_args)

                if "messages" in kwargs and isinstance(kwargs["messages"], list):
                    governed = []
                    for msg in kwargs["messages"]:
                        if isinstance(msg.get("content"), str):
                            result = tork.govern(msg["content"])
                            governed_msg = msg.copy()
                            governed_msg["content"] = result.output
                            governed.append(governed_msg)
                        else:
                            governed.append(msg)
                    kwargs["messages"] = governed

            result = func(*args, **kwargs)

            # Govern output
            if govern_output and isinstance(result, str):
                result = tork.govern(result).output

            return result

        return wrapper
    return decorator
