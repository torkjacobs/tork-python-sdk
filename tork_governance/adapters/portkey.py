"""
Tork Governance adapter for Portkey AI gateway.

Provides governance for Portkey's unified AI gateway with automatic
PII detection and redaction for prompts, responses, and logs.

Usage:
    from tork_governance.adapters.portkey import TorkPortkeyClient, govern_completion

    # Wrap Portkey client
    client = TorkPortkeyClient(portkey_client)

    # Or use convenience functions
    result = govern_completion(prompt, tork=tork)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, AsyncIterator
from ..core import Tork, TorkConfig, GovernanceResult, Receipt


@dataclass
class PortkeyGovernanceResult:
    """Result of Portkey governance operation."""

    governed_data: Any
    original_data: Any
    pii_detected: bool
    pii_count: int
    receipts: List[Receipt] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TorkPortkeyClient:
    """
    Governed wrapper for Portkey AI gateway client.

    Automatically applies PII detection and redaction to all
    completions, logs, and gateway operations.

    Example:
        from portkey import Portkey
        from tork_governance.adapters.portkey import TorkPortkeyClient

        portkey = Portkey(api_key="...")
        governed = TorkPortkeyClient(portkey)

        # All completions now governed
        response = governed.completions.create(
            messages=[{"role": "user", "content": "My SSN is 123-45-6789"}]
        )
    """

    def __init__(
        self,
        client: Any,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        redact_prompts: bool = True,
        redact_responses: bool = True,
        redact_metadata: bool = True,
        redact_logs: bool = True,
    ):
        """
        Initialize governed Portkey client.

        Args:
            client: Portkey client instance
            tork: Tork instance for governance
            config: TorkConfig if tork not provided
            redact_prompts: Whether to redact PII in prompts
            redact_responses: Whether to redact PII in responses
            redact_metadata: Whether to redact PII in metadata
            redact_logs: Whether to redact PII in logs
        """
        self._client = client
        self._tork = tork or Tork(config=config or TorkConfig())
        self._redact_prompts = redact_prompts
        self._redact_responses = redact_responses
        self._redact_metadata = redact_metadata
        self._redact_logs = redact_logs
        self._receipts: List[Receipt] = []

    @property
    def receipts(self) -> List[Receipt]:
        """Get all governance receipts."""
        return self._receipts.copy()

    @property
    def client(self) -> Any:
        """Access underlying Portkey client."""
        return self._client

    def _govern_text(self, text: Any) -> tuple[Any, Optional[GovernanceResult]]:
        """Apply governance to text content."""
        if not isinstance(text, str):
            return text, None
        result = self._tork.govern(text)
        if result.receipt:
            self._receipts.append(result.receipt)
        return result.output, result

    def _govern_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply governance to message list."""
        governed = []
        for msg in messages:
            governed_msg = msg.copy()
            if "content" in governed_msg:
                if isinstance(governed_msg["content"], str):
                    governed_msg["content"], _ = self._govern_text(governed_msg["content"])
                elif isinstance(governed_msg["content"], list):
                    # Handle multi-modal content
                    governed_content = []
                    for part in governed_msg["content"]:
                        if isinstance(part, dict) and "text" in part:
                            governed_part = part.copy()
                            governed_part["text"], _ = self._govern_text(part["text"])
                            governed_content.append(governed_part)
                        else:
                            governed_content.append(part)
                    governed_msg["content"] = governed_content
            governed.append(governed_msg)
        return governed

    def _govern_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply governance to dictionary values."""
        if not isinstance(data, dict):
            return data

        governed = {}
        for key, value in data.items():
            if isinstance(value, str):
                governed[key], _ = self._govern_text(value)
            elif isinstance(value, dict):
                governed[key] = self._govern_dict(value)
            elif isinstance(value, list):
                governed[key] = self._govern_list(value)
            else:
                governed[key] = value
        return governed

    def _govern_list(self, data: List[Any]) -> List[Any]:
        """Apply governance to list items."""
        governed = []
        for item in data:
            if isinstance(item, str):
                text, _ = self._govern_text(item)
                governed.append(text)
            elif isinstance(item, dict):
                governed.append(self._govern_dict(item))
            elif isinstance(item, list):
                governed.append(self._govern_list(item))
            else:
                governed.append(item)
        return governed

    def create_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        virtual_key: Optional[str] = None,
        cache: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> PortkeyGovernanceResult:
        """
        Create completion with governance.

        Args:
            messages: Chat messages
            model: Model to use
            virtual_key: Portkey virtual key
            cache: Whether to use caching
            metadata: Request metadata
            **kwargs: Additional arguments

        Returns:
            PortkeyGovernanceResult with governed response
        """
        original_messages = messages
        receipts_before = len(self._receipts)

        # Govern prompts
        if self._redact_prompts:
            messages = self._govern_messages(messages)

        # Govern metadata
        governed_metadata = metadata
        if self._redact_metadata and metadata:
            governed_metadata = self._govern_dict(metadata)

        # Build request kwargs
        request_kwargs = {
            "messages": messages,
            **kwargs,
        }
        if model:
            request_kwargs["model"] = model
        if virtual_key:
            request_kwargs["virtual_key"] = virtual_key
        if cache is not None:
            request_kwargs["cache"] = cache
        if governed_metadata:
            request_kwargs["metadata"] = governed_metadata

        # Call Portkey
        response = None
        if hasattr(self._client, "chat") and hasattr(self._client.chat, "completions"):
            response = self._client.chat.completions.create(**request_kwargs)
        elif hasattr(self._client, "completions"):
            response = self._client.completions.create(**request_kwargs)

        # Govern response
        governed_response = response
        if self._redact_responses and response:
            if hasattr(response, "choices"):
                for choice in response.choices:
                    if hasattr(choice, "message") and hasattr(choice.message, "content"):
                        if isinstance(choice.message.content, str):
                            choice.message.content, _ = self._govern_text(choice.message.content)

        new_receipts = self._receipts[receipts_before:]

        return PortkeyGovernanceResult(
            governed_data=governed_response,
            original_data={"messages": original_messages, "metadata": metadata},
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            metadata={"operation": "create_completion", "model": model},
        )

    async def acreate_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        virtual_key: Optional[str] = None,
        cache: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> PortkeyGovernanceResult:
        """
        Create completion asynchronously with governance.

        Args:
            messages: Chat messages
            model: Model to use
            virtual_key: Portkey virtual key
            cache: Whether to use caching
            metadata: Request metadata
            **kwargs: Additional arguments

        Returns:
            PortkeyGovernanceResult with governed response
        """
        original_messages = messages
        receipts_before = len(self._receipts)

        # Govern prompts
        if self._redact_prompts:
            messages = self._govern_messages(messages)

        # Govern metadata
        governed_metadata = metadata
        if self._redact_metadata and metadata:
            governed_metadata = self._govern_dict(metadata)

        # Build request kwargs
        request_kwargs = {
            "messages": messages,
            **kwargs,
        }
        if model:
            request_kwargs["model"] = model
        if virtual_key:
            request_kwargs["virtual_key"] = virtual_key
        if cache is not None:
            request_kwargs["cache"] = cache
        if governed_metadata:
            request_kwargs["metadata"] = governed_metadata

        # Call Portkey
        response = None
        if hasattr(self._client, "chat") and hasattr(self._client.chat, "completions"):
            response = await self._client.chat.completions.acreate(**request_kwargs)
        elif hasattr(self._client, "completions"):
            response = await self._client.completions.acreate(**request_kwargs)

        # Govern response
        governed_response = response
        if self._redact_responses and response:
            if hasattr(response, "choices"):
                for choice in response.choices:
                    if hasattr(choice, "message") and hasattr(choice.message, "content"):
                        if isinstance(choice.message.content, str):
                            choice.message.content, _ = self._govern_text(choice.message.content)

        new_receipts = self._receipts[receipts_before:]

        return PortkeyGovernanceResult(
            governed_data=governed_response,
            original_data={"messages": original_messages, "metadata": metadata},
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            metadata={"operation": "acreate_completion", "model": model},
        )

    def log(
        self,
        data: Dict[str, Any],
        **kwargs,
    ) -> PortkeyGovernanceResult:
        """
        Log data with governance.

        Args:
            data: Data to log
            **kwargs: Additional arguments

        Returns:
            PortkeyGovernanceResult with governed log data
        """
        original = data
        receipts_before = len(self._receipts)

        # Govern log data
        governed = data
        if self._redact_logs:
            governed = self._govern_dict(data)

        # Send to Portkey
        if hasattr(self._client, "log"):
            self._client.log(governed, **kwargs)

        new_receipts = self._receipts[receipts_before:]

        return PortkeyGovernanceResult(
            governed_data=governed,
            original_data=original,
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            metadata={"operation": "log"},
        )

    def feedback(
        self,
        trace_id: str,
        value: Any,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> PortkeyGovernanceResult:
        """
        Submit feedback with governance.

        Args:
            trace_id: Trace ID for feedback
            value: Feedback value
            weight: Feedback weight
            metadata: Additional metadata
            **kwargs: Additional arguments

        Returns:
            PortkeyGovernanceResult with governed feedback
        """
        receipts_before = len(self._receipts)

        # Govern value if string
        governed_value = value
        if isinstance(value, str):
            governed_value, _ = self._govern_text(value)

        # Govern metadata
        governed_metadata = metadata
        if self._redact_metadata and metadata:
            governed_metadata = self._govern_dict(metadata)

        # Send feedback
        if hasattr(self._client, "feedback"):
            self._client.feedback(
                trace_id=trace_id,
                value=governed_value,
                weight=weight,
                metadata=governed_metadata,
                **kwargs,
            )

        new_receipts = self._receipts[receipts_before:]

        return PortkeyGovernanceResult(
            governed_data={"trace_id": trace_id, "value": governed_value, "metadata": governed_metadata},
            original_data={"trace_id": trace_id, "value": value, "metadata": metadata},
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            metadata={"operation": "feedback"},
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy other methods to underlying client."""
        return getattr(self._client, name)


def govern_completion(
    messages: List[Dict[str, Any]],
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> PortkeyGovernanceResult:
    """
    Apply governance to completion messages.

    Args:
        messages: Chat messages to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        PortkeyGovernanceResult with governed messages
    """
    tork_instance = tork or Tork(config=config or TorkConfig())
    receipts = []

    def govern_text(text: str) -> str:
        result = tork_instance.govern(text)
        if result.receipt:
            receipts.append(result.receipt)
        return result.output

    governed = []
    for msg in messages:
        governed_msg = msg.copy()
        if "content" in governed_msg and isinstance(governed_msg["content"], str):
            governed_msg["content"] = govern_text(governed_msg["content"])
        governed.append(governed_msg)

    return PortkeyGovernanceResult(
        governed_data=governed,
        original_data=messages,
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_completion"},
    )


def govern_log(
    data: Dict[str, Any],
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> PortkeyGovernanceResult:
    """
    Apply governance to log data.

    Args:
        data: Data to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        PortkeyGovernanceResult with governed data
    """
    tork_instance = tork or Tork(config=config or TorkConfig())
    receipts = []

    def govern_text(text: str) -> str:
        result = tork_instance.govern(text)
        if result.receipt:
            receipts.append(result.receipt)
        return result.output

    def govern_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        governed = {}
        for key, value in d.items():
            if isinstance(value, str):
                governed[key] = govern_text(value)
            elif isinstance(value, dict):
                governed[key] = govern_dict(value)
            elif isinstance(value, list):
                governed[key] = [
                    govern_text(v) if isinstance(v, str)
                    else govern_dict(v) if isinstance(v, dict)
                    else v
                    for v in value
                ]
            else:
                governed[key] = value
        return governed

    governed = govern_dict(data)

    return PortkeyGovernanceResult(
        governed_data=governed,
        original_data=data,
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_log"},
    )


def portkey_governed(
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
):
    """
    Decorator to add governance to Portkey operations.

    Args:
        tork: Tork instance
        config: TorkConfig if tork not provided

    Returns:
        Decorator function
    """
    tork_instance = tork or Tork(config=config or TorkConfig())

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Govern string arguments
            governed_args = []
            for arg in args:
                if isinstance(arg, str):
                    result = tork_instance.govern(arg)
                    governed_args.append(result.output)
                else:
                    governed_args.append(arg)

            # Govern messages in kwargs
            governed_kwargs = {}
            for key, value in kwargs.items():
                if key == "messages" and isinstance(value, list):
                    governed_msgs = []
                    for msg in value:
                        if isinstance(msg, dict) and "content" in msg:
                            governed_msg = msg.copy()
                            if isinstance(msg["content"], str):
                                result = tork_instance.govern(msg["content"])
                                governed_msg["content"] = result.output
                            governed_msgs.append(governed_msg)
                        else:
                            governed_msgs.append(msg)
                    governed_kwargs[key] = governed_msgs
                elif isinstance(value, str):
                    result = tork_instance.govern(value)
                    governed_kwargs[key] = result.output
                else:
                    governed_kwargs[key] = value

            return func(*governed_args, **governed_kwargs)

        return wrapper

    return decorator


__all__ = [
    "TorkPortkeyClient",
    "PortkeyGovernanceResult",
    "govern_completion",
    "govern_log",
    "portkey_governed",
]
