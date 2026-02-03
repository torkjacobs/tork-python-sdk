"""
Ollama adapter for Tork Governance.

Provides governance integration for Ollama, which runs LLMs locally.
Supports generate, chat, and streaming responses.

Example:
    from tork_governance.adapters.ollama import TorkOllamaClient, govern_generate

    # Use governed client
    client = TorkOllamaClient()
    response = client.generate(model="llama2", prompt="My SSN is 123-45-6789")

    # Use convenience function
    response = govern_generate(model="llama2", prompt="My email is test@example.com")
"""

from typing import Any, Callable, Dict, Generator, Iterator, List, Optional, Union
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkOllamaClient:
    """
    Governed Ollama client wrapper.

    Provides a drop-in replacement for the Ollama client with
    automatic governance applied to prompts and responses.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        host: Optional[str] = None,
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self.tork = Tork(api_key=api_key)
        self.host = host
        self.govern_input = govern_input
        self.govern_output = govern_output
        self._receipts: List[str] = []
        self._client: Any = None

    def _get_client(self) -> Any:
        """Get or create the Ollama client."""
        if self._client is None:
            try:
                import ollama
            except ImportError:
                raise ImportError("ollama is required: pip install ollama")

            if self.host:
                self._client = ollama.Client(host=self.host)
            else:
                self._client = ollama
        return self._client

    def generate(
        self,
        model: str,
        prompt: str,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], Generator[Dict[str, Any], None, None]]:
        """
        Generate text with governance applied.

        Args:
            model: The Ollama model to use
            prompt: The prompt text (will be governed)
            stream: Whether to stream the response
            **kwargs: Additional arguments passed to Ollama

        Returns:
            Response dictionary or generator if streaming
        """
        client = self._get_client()

        # Govern input prompt
        if self.govern_input:
            result = self.tork.govern(prompt)
            prompt = result.output
            if result.receipt:
                self._receipts.append(result.receipt.receipt_id)

        if stream:
            return self._stream_generate(client, model, prompt, **kwargs)

        # Non-streaming
        response = client.generate(model=model, prompt=prompt, **kwargs)

        # Govern output
        if self.govern_output and "response" in response:
            result = self.tork.govern(response["response"])
            response["response"] = result.output
            if result.receipt:
                self._receipts.append(result.receipt.receipt_id)
            response["_tork_receipt_id"] = result.receipt.receipt_id if result.receipt else None

        return response

    def _stream_generate(
        self,
        client: Any,
        model: str,
        prompt: str,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream generate with governance on accumulated response."""
        stream = client.generate(model=model, prompt=prompt, stream=True, **kwargs)

        full_response = ""
        for chunk in stream:
            if "response" in chunk:
                full_response += chunk["response"]
            yield chunk

        # Govern the accumulated response (for logging/auditing)
        if self.govern_output and full_response:
            result = self.tork.govern(full_response)
            if result.receipt:
                self._receipts.append(result.receipt.receipt_id)

    def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        stream: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], Generator[Dict[str, Any], None, None]]:
        """
        Chat with governance applied.

        Args:
            model: The Ollama model to use
            messages: List of chat messages
            stream: Whether to stream the response
            **kwargs: Additional arguments passed to Ollama

        Returns:
            Response dictionary or generator if streaming
        """
        client = self._get_client()

        # Govern input messages
        if self.govern_input:
            messages = self._govern_messages(messages)

        if stream:
            return self._stream_chat(client, model, messages, **kwargs)

        # Non-streaming
        response = client.chat(model=model, messages=messages, **kwargs)

        # Govern output
        if self.govern_output:
            if "message" in response and "content" in response["message"]:
                result = self.tork.govern(response["message"]["content"])
                response["message"]["content"] = result.output
                if result.receipt:
                    self._receipts.append(result.receipt.receipt_id)
                response["_tork_receipt_id"] = result.receipt.receipt_id if result.receipt else None

        return response

    def _stream_chat(
        self,
        client: Any,
        model: str,
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream chat with governance on accumulated response."""
        stream = client.chat(model=model, messages=messages, stream=True, **kwargs)

        full_content = ""
        for chunk in stream:
            if "message" in chunk and "content" in chunk["message"]:
                full_content += chunk["message"]["content"]
            yield chunk

        # Govern the accumulated response
        if self.govern_output and full_content:
            result = self.tork.govern(full_content)
            if result.receipt:
                self._receipts.append(result.receipt.receipt_id)

    def _govern_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Govern a list of chat messages."""
        governed = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str) and content:
                result = self.tork.govern(content)
                governed_msg = msg.copy()
                governed_msg["content"] = result.output
                if result.receipt:
                    self._receipts.append(result.receipt.receipt_id)
                governed.append(governed_msg)
            else:
                governed.append(msg)
        return governed

    def embeddings(
        self,
        model: str,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate embeddings with governed input.

        Note: Only input is governed for embeddings.
        """
        client = self._get_client()

        # Govern input
        if self.govern_input:
            result = self.tork.govern(prompt)
            prompt = result.output
            if result.receipt:
                self._receipts.append(result.receipt.receipt_id)

        return client.embeddings(model=model, prompt=prompt, **kwargs)

    def pull(self, model: str, **kwargs) -> Any:
        """Pull a model (passthrough to Ollama)."""
        return self._get_client().pull(model, **kwargs)

    def list(self) -> Any:
        """List available models (passthrough to Ollama)."""
        return self._get_client().list()

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipt IDs."""
        return self._receipts.copy()


def govern_generate(
    model: str,
    prompt: str,
    api_key: Optional[str] = None,
    host: Optional[str] = None,
    govern_input: bool = True,
    govern_output: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Governed Ollama generate call.

    Convenience function that wraps ollama.generate with governance.

    Example:
        response = govern_generate(
            model="llama2",
            prompt="My SSN is 123-45-6789"
        )
        print(response["response"])  # PII redacted
    """
    client = TorkOllamaClient(
        api_key=api_key,
        host=host,
        govern_input=govern_input,
        govern_output=govern_output,
    )
    return client.generate(model=model, prompt=prompt, **kwargs)


def govern_chat(
    model: str,
    messages: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    host: Optional[str] = None,
    govern_input: bool = True,
    govern_output: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Governed Ollama chat call.

    Convenience function that wraps ollama.chat with governance.

    Example:
        response = govern_chat(
            model="llama2",
            messages=[{"role": "user", "content": "My email is test@example.com"}]
        )
        print(response["message"]["content"])  # PII redacted
    """
    client = TorkOllamaClient(
        api_key=api_key,
        host=host,
        govern_input=govern_input,
        govern_output=govern_output,
    )
    return client.chat(model=model, messages=messages, **kwargs)


def ollama_governed(
    api_key: Optional[str] = None,
    govern_input: bool = True,
    govern_output: bool = True,
):
    """
    Decorator to add Tork governance to Ollama-based functions.

    Example:
        @ollama_governed()
        def my_ollama_function(prompt: str) -> str:
            response = ollama.generate(model="llama2", prompt=prompt)
            return response["response"]
    """
    def decorator(func: Callable) -> Callable:
        tork = Tork(api_key=api_key)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Govern string arguments
            if govern_input:
                args = tuple(
                    tork.govern(arg).output if isinstance(arg, str) else arg
                    for arg in args
                )
                kwargs = {
                    k: tork.govern(v).output if isinstance(v, str) else v
                    for k, v in kwargs.items()
                }

            result = func(*args, **kwargs)

            # Govern output
            if govern_output and isinstance(result, str):
                result = tork.govern(result).output

            return result

        return wrapper
    return decorator


class AsyncTorkOllamaClient:
    """
    Async governed Ollama client wrapper.

    Provides async methods for Ollama operations with governance.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        host: Optional[str] = None,
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self.tork = Tork(api_key=api_key)
        self.host = host
        self.govern_input = govern_input
        self.govern_output = govern_output
        self._receipts: List[str] = []
        self._client: Any = None

    def _get_client(self) -> Any:
        """Get or create the async Ollama client."""
        if self._client is None:
            try:
                import ollama
            except ImportError:
                raise ImportError("ollama is required: pip install ollama")

            if self.host:
                self._client = ollama.AsyncClient(host=self.host)
            else:
                self._client = ollama.AsyncClient()
        return self._client

    async def generate(
        self,
        model: str,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Async generate with governance."""
        client = self._get_client()

        # Govern input
        if self.govern_input:
            result = self.tork.govern(prompt)
            prompt = result.output
            if result.receipt:
                self._receipts.append(result.receipt.receipt_id)

        response = await client.generate(model=model, prompt=prompt, **kwargs)

        # Govern output
        if self.govern_output and "response" in response:
            result = self.tork.govern(response["response"])
            response["response"] = result.output
            if result.receipt:
                self._receipts.append(result.receipt.receipt_id)

        return response

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Any]:
        """Async chat with governance."""
        client = self._get_client()

        # Govern input
        if self.govern_input:
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
            messages = governed

        response = await client.chat(model=model, messages=messages, **kwargs)

        # Govern output
        if self.govern_output:
            if "message" in response and "content" in response["message"]:
                result = self.tork.govern(response["message"]["content"])
                response["message"]["content"] = result.output
                if result.receipt:
                    self._receipts.append(result.receipt.receipt_id)

        return response

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipt IDs."""
        return self._receipts.copy()
