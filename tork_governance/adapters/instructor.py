"""
Instructor adapter for Tork Governance.

Provides client wrappers and response governance for structured outputs.
"""

from typing import Any, Callable, Dict, List, Optional, Type, TypeVar
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction

T = TypeVar("T")


class TorkInstructorClient:
    """
    Wrapped Instructor client with governance.

    Example:
        >>> from tork_governance.adapters.instructor import TorkInstructorClient
        >>> import instructor
        >>> from openai import OpenAI
        >>>
        >>> client = instructor.from_openai(OpenAI())
        >>> governed_client = TorkInstructorClient(client)
        >>>
        >>> response = governed_client.chat.completions.create(
        >>>     model="gpt-4",
        >>>     messages=[{"role": "user", "content": "Extract user info"}],
        >>>     response_model=UserInfo
        >>> )
    """

    def __init__(self, client: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.client = client
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []
        self.chat = _TorkChatNamespace(self)

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def govern_input(self, text: str) -> str:
        """Govern input text - standalone method."""
        return self.govern(text)

    def _govern_messages(self, messages: List[Dict]) -> List[Dict]:
        """Govern message content."""
        governed = []
        for msg in messages:
            governed_msg = dict(msg)
            if isinstance(msg.get("content"), str):
                result = self.tork.govern(msg["content"])
                governed_msg["content"] = result.output
                self.receipts.append({
                    "type": "message_input",
                    "role": msg.get("role"),
                    "receipt_id": result.receipt.receipt_id
                })
            governed.append(governed_msg)
        return governed

    def _govern_response(self, response: Any) -> Any:
        """Govern structured response fields."""
        if hasattr(response, '__dict__'):
            for field, value in vars(response).items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    setattr(response, field, result.output)
                    self.receipts.append({
                        "type": "response_field",
                        "field": field,
                        "receipt_id": result.receipt.receipt_id
                    })
        return response

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class _TorkChatNamespace:
    """Namespace for chat completions."""

    def __init__(self, parent: TorkInstructorClient):
        self.parent = parent
        self.completions = _TorkCompletionsNamespace(parent)


class _TorkCompletionsNamespace:
    """Namespace for completions."""

    def __init__(self, parent: TorkInstructorClient):
        self.parent = parent

    def create(self, messages: List[Dict], response_model: Type[T], **kwargs) -> T:
        """Create governed completion."""
        governed_messages = self.parent._govern_messages(messages)

        response = self.parent.client.chat.completions.create(
            messages=governed_messages,
            response_model=response_model,
            **kwargs
        )

        return self.parent._govern_response(response)

    async def acreate(self, messages: List[Dict], response_model: Type[T], **kwargs) -> T:
        """Async governed completion."""
        governed_messages = self.parent._govern_messages(messages)

        response = await self.parent.client.chat.completions.acreate(
            messages=governed_messages,
            response_model=response_model,
            **kwargs
        )

        return self.parent._govern_response(response)


class TorkInstructorPatch:
    """
    Monkey patch for Instructor with governance.

    Example:
        >>> from tork_governance.adapters.instructor import TorkInstructorPatch
        >>>
        >>> patch = TorkInstructorPatch()
        >>> patched_client = patch.patch(client)
    """

    def __init__(self, tork: Optional[Tork] = None):
        self.tork = tork or Tork()
        self.receipts: List[Dict] = []
        self._original_create = None

    def patch(self, client: Any) -> Any:
        """Patch client with governance."""
        original_create = client.chat.completions.create
        tork = self.tork
        receipts = self.receipts

        def governed_create(messages: List[Dict], **kwargs):
            # Govern messages
            governed_messages = []
            for msg in messages:
                governed_msg = dict(msg)
                if isinstance(msg.get("content"), str):
                    result = tork.govern(msg["content"])
                    governed_msg["content"] = result.output
                    receipts.append({
                        "type": "patched_input",
                        "receipt_id": result.receipt.receipt_id
                    })
                governed_messages.append(governed_msg)

            response = original_create(messages=governed_messages, **kwargs)

            # Govern response
            if hasattr(response, '__dict__'):
                for field, value in vars(response).items():
                    if isinstance(value, str):
                        result = tork.govern(value)
                        setattr(response, field, result.output)

            return response

        client.chat.completions.create = governed_create
        return client

    def get_receipts(self) -> List[Dict]:
        return self.receipts


def governed_response(tork: Optional[Tork] = None):
    """
    Decorator for governed Instructor responses.

    Example:
        >>> @governed_response()
        >>> def get_user_info(text: str) -> UserInfo:
        >>>     return client.chat.completions.create(...)
    """
    _tork = tork or Tork()
    receipts: List[Dict] = []

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Govern string args
            governed_args = []
            for arg in args:
                if isinstance(arg, str):
                    result = _tork.govern(arg)
                    governed_args.append(result.output)
                    receipts.append({
                        "type": "response_input",
                        "receipt_id": result.receipt.receipt_id
                    })
                else:
                    governed_args.append(arg)

            # Govern string kwargs
            governed_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    result = _tork.govern(value)
                    governed_kwargs[key] = result.output
                else:
                    governed_kwargs[key] = value

            # Execute
            response = func(*governed_args, **governed_kwargs)

            # Govern response fields
            if hasattr(response, '__dict__'):
                for field, value in vars(response).items():
                    if isinstance(value, str):
                        result = _tork.govern(value)
                        setattr(response, field, result.output)
                        receipts.append({
                            "type": "response_output",
                            "field": field,
                            "receipt_id": result.receipt.receipt_id
                        })

            return response

        wrapper.get_receipts = lambda: receipts
        return wrapper

    return decorator
