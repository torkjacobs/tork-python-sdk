"""
Tork Governance adapter for Anthropic Claude SDK.

Provides governance for direct Anthropic API usage with automatic
PII detection and redaction in messages and completions.

Usage:
    from tork_governance.adapters.anthropic_sdk import TorkAnthropicClient

    # Wrap Anthropic client
    from anthropic import Anthropic
    client = TorkAnthropicClient(Anthropic())

    # All API calls now governed
    response = client.messages_create(
        model="claude-3-opus-20240229",
        messages=[{"role": "user", "content": "My SSN is 123-45-6789"}]
    )
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from ..core import Tork, TorkConfig, GovernanceResult, Receipt


@dataclass
class AnthropicGovernanceResult:
    """Result of Anthropic governance operation."""

    governed_data: Any
    original_data: Any
    pii_detected: bool
    pii_count: int
    receipts: List[Receipt] = field(default_factory=list)
    response: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TorkAnthropicClient:
    """
    Governed wrapper for Anthropic client.

    Automatically applies PII detection and redaction to all
    message and completion requests.

    Example:
        from anthropic import Anthropic
        from tork_governance.adapters.anthropic_sdk import TorkAnthropicClient

        client = Anthropic(api_key="...")
        governed = TorkAnthropicClient(client)

        # Messages are governed
        response = governed.messages_create(
            model="claude-3-opus-20240229",
            messages=[{"role": "user", "content": "Hello"}]
        )
    """

    def __init__(
        self,
        client: Any,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        redact_user_messages: bool = True,
        redact_system_prompt: bool = True,
        redact_assistant_messages: bool = False,
        redact_responses: bool = True,
    ):
        """
        Initialize governed Anthropic client.

        Args:
            client: Anthropic client instance
            tork: Tork instance for governance
            config: TorkConfig if tork not provided
            redact_user_messages: Whether to redact PII in user messages
            redact_system_prompt: Whether to redact PII in system prompt
            redact_assistant_messages: Whether to redact PII in assistant messages
            redact_responses: Whether to redact PII in responses
        """
        self._client = client
        self._tork = tork or Tork(config=config or TorkConfig())
        self._redact_user = redact_user_messages
        self._redact_system = redact_system_prompt
        self._redact_assistant = redact_assistant_messages
        self._redact_responses = redact_responses
        self._receipts: List[Receipt] = []

    @property
    def receipts(self) -> List[Receipt]:
        """Get all governance receipts."""
        return self._receipts.copy()

    @property
    def client(self) -> Any:
        """Access underlying Anthropic client."""
        return self._client

    def _govern_text(self, text: Any) -> tuple[Any, Optional[GovernanceResult]]:
        """Apply governance to text content."""
        if not isinstance(text, str):
            return text, None
        result = self._tork.govern(text)
        if result.receipt:
            self._receipts.append(result.receipt)
        return result.output, result

    def _govern_content(self, content: Any) -> Any:
        """Apply governance to message content (string or list of content blocks)."""
        if isinstance(content, str):
            governed, _ = self._govern_text(content)
            return governed
        elif isinstance(content, list):
            governed = []
            for block in content:
                if isinstance(block, dict):
                    governed_block = block.copy()
                    if block.get("type") == "text" and "text" in block:
                        governed_block["text"], _ = self._govern_text(block["text"])
                    governed.append(governed_block)
                elif isinstance(block, str):
                    text, _ = self._govern_text(block)
                    governed.append(text)
                else:
                    governed.append(block)
            return governed
        return content

    def _govern_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply governance to message list."""
        governed = []
        for msg in messages:
            governed_msg = msg.copy()
            role = msg.get("role", "")

            should_redact = (
                (role == "user" and self._redact_user) or
                (role == "assistant" and self._redact_assistant)
            )

            if should_redact and "content" in governed_msg:
                governed_msg["content"] = self._govern_content(governed_msg["content"])

            governed.append(governed_msg)
        return governed

    def messages_create(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        max_tokens: int = 1024,
        system: Optional[str] = None,
        stream: bool = False,
        **kwargs,
    ) -> AnthropicGovernanceResult:
        """
        Create message with governance.

        Args:
            model: Model to use (e.g., claude-3-opus-20240229)
            messages: Chat messages
            max_tokens: Maximum tokens in response
            system: System prompt
            stream: Whether to stream responses
            **kwargs: Additional arguments for Anthropic

        Returns:
            AnthropicGovernanceResult with governed response
        """
        original_messages = messages
        original_system = system
        receipts_before = len(self._receipts)

        # Govern messages
        governed_messages = self._govern_messages(messages)

        # Govern system prompt
        governed_system = system
        if self._redact_system and system:
            governed_system, _ = self._govern_text(system)

        # Build request
        request_kwargs = {
            "model": model,
            "messages": governed_messages,
            "max_tokens": max_tokens,
            **kwargs,
        }
        if governed_system:
            request_kwargs["system"] = governed_system

        # Call Anthropic
        if stream:
            response = self._client.messages.stream(**request_kwargs)
        else:
            response = self._client.messages.create(**request_kwargs)

        # Handle streaming
        if stream:
            return AnthropicGovernanceResult(
                governed_data={"messages": governed_messages, "system": governed_system},
                original_data={"messages": original_messages, "system": original_system},
                pii_detected=len(self._receipts) > receipts_before,
                pii_count=sum(r.pii_count for r in self._receipts[receipts_before:] if hasattr(r, "pii_count")),
                receipts=self._receipts[receipts_before:],
                response=response,
                metadata={"operation": "messages_create", "model": model, "stream": True},
            )

        # Govern response
        if self._redact_responses and hasattr(response, "content"):
            for block in response.content:
                if hasattr(block, "text") and isinstance(block.text, str):
                    block.text, _ = self._govern_text(block.text)

        new_receipts = self._receipts[receipts_before:]

        return AnthropicGovernanceResult(
            governed_data={"messages": governed_messages, "system": governed_system},
            original_data={"messages": original_messages, "system": original_system},
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,
            metadata={"operation": "messages_create", "model": model},
        )

    async def amessages_create(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        max_tokens: int = 1024,
        system: Optional[str] = None,
        stream: bool = False,
        **kwargs,
    ) -> AnthropicGovernanceResult:
        """
        Create message asynchronously with governance.

        Args:
            model: Model to use
            messages: Chat messages
            max_tokens: Maximum tokens in response
            system: System prompt
            stream: Whether to stream responses
            **kwargs: Additional arguments for Anthropic

        Returns:
            AnthropicGovernanceResult with governed response
        """
        original_messages = messages
        original_system = system
        receipts_before = len(self._receipts)

        # Govern messages
        governed_messages = self._govern_messages(messages)

        # Govern system prompt
        governed_system = system
        if self._redact_system and system:
            governed_system, _ = self._govern_text(system)

        # Build request
        request_kwargs = {
            "model": model,
            "messages": governed_messages,
            "max_tokens": max_tokens,
            **kwargs,
        }
        if governed_system:
            request_kwargs["system"] = governed_system

        # Call Anthropic
        if stream:
            response = await self._client.messages.stream(**request_kwargs)
        else:
            response = await self._client.messages.create(**request_kwargs)

        if stream:
            return AnthropicGovernanceResult(
                governed_data={"messages": governed_messages, "system": governed_system},
                original_data={"messages": original_messages, "system": original_system},
                pii_detected=len(self._receipts) > receipts_before,
                pii_count=sum(r.pii_count for r in self._receipts[receipts_before:] if hasattr(r, "pii_count")),
                receipts=self._receipts[receipts_before:],
                response=response,
                metadata={"operation": "amessages_create", "model": model, "stream": True},
            )

        # Govern response
        if self._redact_responses and hasattr(response, "content"):
            for block in response.content:
                if hasattr(block, "text") and isinstance(block.text, str):
                    block.text, _ = self._govern_text(block.text)

        new_receipts = self._receipts[receipts_before:]

        return AnthropicGovernanceResult(
            governed_data={"messages": governed_messages, "system": governed_system},
            original_data={"messages": original_messages, "system": original_system},
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,
            metadata={"operation": "amessages_create", "model": model},
        )

    def completions_create(
        self,
        prompt: str,
        model: str = "claude-2.1",
        max_tokens_to_sample: int = 1024,
        **kwargs,
    ) -> AnthropicGovernanceResult:
        """
        Create completion with governance (legacy API).

        Args:
            prompt: Prompt text
            model: Model to use
            max_tokens_to_sample: Maximum tokens in response
            **kwargs: Additional arguments for Anthropic

        Returns:
            AnthropicGovernanceResult with governed response
        """
        original_prompt = prompt
        receipts_before = len(self._receipts)

        # Govern prompt
        governed_prompt, _ = self._govern_text(prompt)

        # Call Anthropic
        response = self._client.completions.create(
            model=model,
            prompt=governed_prompt,
            max_tokens_to_sample=max_tokens_to_sample,
            **kwargs,
        )

        # Govern response
        if self._redact_responses and hasattr(response, "completion"):
            if isinstance(response.completion, str):
                response.completion, _ = self._govern_text(response.completion)

        new_receipts = self._receipts[receipts_before:]

        return AnthropicGovernanceResult(
            governed_data=governed_prompt,
            original_data=original_prompt,
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,
            metadata={"operation": "completions_create", "model": model},
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy other methods to underlying client."""
        return getattr(self._client, name)


def govern_message(
    messages: List[Dict[str, Any]],
    system: Optional[str] = None,
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> AnthropicGovernanceResult:
    """
    Apply governance to Anthropic messages.

    Args:
        messages: Messages to govern
        system: System prompt to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        AnthropicGovernanceResult with governed messages
    """
    tork_instance = tork or Tork(config=config or TorkConfig())
    receipts = []

    def govern_text(text: str) -> str:
        result = tork_instance.govern(text)
        if result.receipt:
            receipts.append(result.receipt)
        return result.output

    governed_messages = []
    for msg in messages:
        governed_msg = msg.copy()
        if "content" in governed_msg:
            if isinstance(governed_msg["content"], str):
                governed_msg["content"] = govern_text(governed_msg["content"])
            elif isinstance(governed_msg["content"], list):
                governed_content = []
                for block in governed_msg["content"]:
                    if isinstance(block, dict) and block.get("type") == "text":
                        governed_block = block.copy()
                        governed_block["text"] = govern_text(block.get("text", ""))
                        governed_content.append(governed_block)
                    else:
                        governed_content.append(block)
                governed_msg["content"] = governed_content
        governed_messages.append(governed_msg)

    governed_system = govern_text(system) if system else None

    return AnthropicGovernanceResult(
        governed_data={"messages": governed_messages, "system": governed_system},
        original_data={"messages": messages, "system": system},
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_message"},
    )


def govern_anthropic_completion(
    prompt: str,
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> AnthropicGovernanceResult:
    """
    Apply governance to Anthropic completion prompt.

    Args:
        prompt: Prompt to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        AnthropicGovernanceResult with governed prompt
    """
    tork_instance = tork or Tork(config=config or TorkConfig())
    result = tork_instance.govern(prompt)

    return AnthropicGovernanceResult(
        governed_data=result.output,
        original_data=prompt,
        pii_detected=result.receipt is not None,
        pii_count=result.receipt.pii_count if result.receipt and hasattr(result.receipt, "pii_count") else 0,
        receipts=[result.receipt] if result.receipt else [],
        metadata={"operation": "govern_anthropic_completion"},
    )


def anthropic_governed(
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
):
    """
    Decorator to add governance to Anthropic operations.

    Args:
        tork: Tork instance
        config: TorkConfig if tork not provided

    Returns:
        Decorator function
    """
    tork_instance = tork or Tork(config=config or TorkConfig())

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Govern messages
            if "messages" in kwargs:
                governed_msgs = []
                for msg in kwargs["messages"]:
                    governed_msg = msg.copy()
                    if "content" in msg and isinstance(msg["content"], str):
                        result = tork_instance.govern(msg["content"])
                        governed_msg["content"] = result.output
                    governed_msgs.append(governed_msg)
                kwargs["messages"] = governed_msgs

            # Govern system
            if "system" in kwargs and isinstance(kwargs["system"], str):
                result = tork_instance.govern(kwargs["system"])
                kwargs["system"] = result.output

            # Govern prompt
            if "prompt" in kwargs and isinstance(kwargs["prompt"], str):
                result = tork_instance.govern(kwargs["prompt"])
                kwargs["prompt"] = result.output

            return func(*args, **kwargs)

        return wrapper

    return decorator


__all__ = [
    "TorkAnthropicClient",
    "AnthropicGovernanceResult",
    "govern_message",
    "govern_anthropic_completion",
    "anthropic_governed",
]
