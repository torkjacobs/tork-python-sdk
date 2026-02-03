"""
Tork Governance adapter for Azure OpenAI.

Provides governance for Azure OpenAI Service with automatic
PII detection and redaction in chat completions, completions, and embeddings.

Usage:
    from tork_governance.adapters.azure_openai import TorkAzureOpenAIClient

    # Wrap Azure OpenAI client
    from openai import AzureOpenAI
    client = TorkAzureOpenAIClient(AzureOpenAI(...))

    # All API calls now governed
    response = client.chat_completions_create(
        messages=[{"role": "user", "content": "My SSN is 123-45-6789"}]
    )
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from ..core import Tork, TorkConfig, GovernanceResult, Receipt


@dataclass
class AzureOpenAIGovernanceResult:
    """Result of Azure OpenAI governance operation."""

    governed_data: Any
    original_data: Any
    pii_detected: bool
    pii_count: int
    receipts: List[Receipt] = field(default_factory=list)
    response: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TorkAzureOpenAIClient:
    """
    Governed wrapper for Azure OpenAI client.

    Automatically applies PII detection and redaction to all
    chat completions, completions, and embedding requests.

    Example:
        from openai import AzureOpenAI
        from tork_governance.adapters.azure_openai import TorkAzureOpenAIClient

        client = AzureOpenAI(
            api_key="...",
            api_version="2024-02-15-preview",
            azure_endpoint="https://your-resource.openai.azure.com"
        )
        governed = TorkAzureOpenAIClient(client)

        # Chat completions are governed
        response = governed.chat_completions_create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}]
        )
    """

    def __init__(
        self,
        client: Any,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        redact_user_messages: bool = True,
        redact_system_messages: bool = True,
        redact_assistant_messages: bool = False,
        redact_responses: bool = True,
        redact_embeddings: bool = True,
        deployment_name: Optional[str] = None,
    ):
        """
        Initialize governed Azure OpenAI client.

        Args:
            client: Azure OpenAI client instance
            tork: Tork instance for governance
            config: TorkConfig if tork not provided
            redact_user_messages: Whether to redact PII in user messages
            redact_system_messages: Whether to redact PII in system messages
            redact_assistant_messages: Whether to redact PII in assistant messages
            redact_responses: Whether to redact PII in responses
            redact_embeddings: Whether to redact PII in embedding inputs
            deployment_name: Default Azure deployment name
        """
        self._client = client
        self._tork = tork or Tork(config=config or TorkConfig())
        self._redact_user = redact_user_messages
        self._redact_system = redact_system_messages
        self._redact_assistant = redact_assistant_messages
        self._redact_responses = redact_responses
        self._redact_embeddings = redact_embeddings
        self._deployment_name = deployment_name
        self._receipts: List[Receipt] = []

    @property
    def receipts(self) -> List[Receipt]:
        """Get all governance receipts."""
        return self._receipts.copy()

    @property
    def client(self) -> Any:
        """Access underlying Azure OpenAI client."""
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
            role = msg.get("role", "")

            should_redact = (
                (role == "user" and self._redact_user) or
                (role == "system" and self._redact_system) or
                (role == "assistant" and self._redact_assistant)
            )

            if should_redact and "content" in governed_msg:
                if isinstance(governed_msg["content"], str):
                    governed_msg["content"], _ = self._govern_text(governed_msg["content"])
                elif isinstance(governed_msg["content"], list):
                    governed_content = []
                    for part in governed_msg["content"]:
                        if isinstance(part, dict) and part.get("type") == "text":
                            governed_part = part.copy()
                            governed_part["text"], _ = self._govern_text(part.get("text", ""))
                            governed_content.append(governed_part)
                        else:
                            governed_content.append(part)
                    governed_msg["content"] = governed_content

            governed.append(governed_msg)
        return governed

    def chat_completions_create(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs,
    ) -> AzureOpenAIGovernanceResult:
        """
        Create chat completion with governance.

        Args:
            messages: Chat messages
            model: Deployment name (defaults to configured deployment)
            stream: Whether to stream responses
            **kwargs: Additional arguments for Azure OpenAI

        Returns:
            AzureOpenAIGovernanceResult with governed response
        """
        original_messages = messages
        receipts_before = len(self._receipts)
        deployment = model or self._deployment_name

        # Govern messages
        governed_messages = self._govern_messages(messages)

        # Call Azure OpenAI
        response = self._client.chat.completions.create(
            model=deployment,
            messages=governed_messages,
            stream=stream,
            **kwargs,
        )

        # Handle streaming
        if stream:
            return AzureOpenAIGovernanceResult(
                governed_data=governed_messages,
                original_data=original_messages,
                pii_detected=len(self._receipts) > receipts_before,
                pii_count=sum(r.pii_count for r in self._receipts[receipts_before:] if hasattr(r, "pii_count")),
                receipts=self._receipts[receipts_before:],
                response=response,
                metadata={"operation": "chat_completions_create", "deployment": deployment, "stream": True},
            )

        # Govern response
        if self._redact_responses and response.choices:
            for choice in response.choices:
                if hasattr(choice, "message") and hasattr(choice.message, "content"):
                    if isinstance(choice.message.content, str):
                        choice.message.content, _ = self._govern_text(choice.message.content)

        new_receipts = self._receipts[receipts_before:]

        return AzureOpenAIGovernanceResult(
            governed_data=governed_messages,
            original_data=original_messages,
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,
            metadata={"operation": "chat_completions_create", "deployment": deployment},
        )

    async def achat_completions_create(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs,
    ) -> AzureOpenAIGovernanceResult:
        """
        Create chat completion asynchronously with governance.

        Args:
            messages: Chat messages
            model: Deployment name
            stream: Whether to stream responses
            **kwargs: Additional arguments for Azure OpenAI

        Returns:
            AzureOpenAIGovernanceResult with governed response
        """
        original_messages = messages
        receipts_before = len(self._receipts)
        deployment = model or self._deployment_name

        # Govern messages
        governed_messages = self._govern_messages(messages)

        # Call Azure OpenAI
        response = await self._client.chat.completions.create(
            model=deployment,
            messages=governed_messages,
            stream=stream,
            **kwargs,
        )

        if stream:
            return AzureOpenAIGovernanceResult(
                governed_data=governed_messages,
                original_data=original_messages,
                pii_detected=len(self._receipts) > receipts_before,
                pii_count=sum(r.pii_count for r in self._receipts[receipts_before:] if hasattr(r, "pii_count")),
                receipts=self._receipts[receipts_before:],
                response=response,
                metadata={"operation": "achat_completions_create", "deployment": deployment, "stream": True},
            )

        # Govern response
        if self._redact_responses and response.choices:
            for choice in response.choices:
                if hasattr(choice, "message") and hasattr(choice.message, "content"):
                    if isinstance(choice.message.content, str):
                        choice.message.content, _ = self._govern_text(choice.message.content)

        new_receipts = self._receipts[receipts_before:]

        return AzureOpenAIGovernanceResult(
            governed_data=governed_messages,
            original_data=original_messages,
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,
            metadata={"operation": "achat_completions_create", "deployment": deployment},
        )

    def completions_create(
        self,
        prompt: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs,
    ) -> AzureOpenAIGovernanceResult:
        """
        Create completion with governance.

        Args:
            prompt: Prompt text or list of prompts
            model: Deployment name
            **kwargs: Additional arguments for Azure OpenAI

        Returns:
            AzureOpenAIGovernanceResult with governed response
        """
        original_prompt = prompt
        receipts_before = len(self._receipts)
        deployment = model or self._deployment_name

        # Govern prompt
        if isinstance(prompt, str):
            governed_prompt, _ = self._govern_text(prompt)
        else:
            governed_prompt = []
            for p in prompt:
                text, _ = self._govern_text(p)
                governed_prompt.append(text)

        # Call Azure OpenAI
        response = self._client.completions.create(
            model=deployment,
            prompt=governed_prompt,
            **kwargs,
        )

        # Govern response
        if self._redact_responses and response.choices:
            for choice in response.choices:
                if hasattr(choice, "text") and isinstance(choice.text, str):
                    choice.text, _ = self._govern_text(choice.text)

        new_receipts = self._receipts[receipts_before:]

        return AzureOpenAIGovernanceResult(
            governed_data=governed_prompt,
            original_data=original_prompt,
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,
            metadata={"operation": "completions_create", "deployment": deployment},
        )

    def embeddings_create(
        self,
        input: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs,
    ) -> AzureOpenAIGovernanceResult:
        """
        Create embeddings with governance.

        Args:
            input: Text or list of texts to embed
            model: Deployment name
            **kwargs: Additional arguments for Azure OpenAI

        Returns:
            AzureOpenAIGovernanceResult with governed response
        """
        original_input = input
        receipts_before = len(self._receipts)
        deployment = model or self._deployment_name

        # Govern input
        if self._redact_embeddings:
            if isinstance(input, str):
                governed_input, _ = self._govern_text(input)
            else:
                governed_input = []
                for text in input:
                    governed_text, _ = self._govern_text(text)
                    governed_input.append(governed_text)
        else:
            governed_input = input

        # Call Azure OpenAI
        response = self._client.embeddings.create(
            input=governed_input,
            model=deployment,
            **kwargs,
        )

        new_receipts = self._receipts[receipts_before:]

        return AzureOpenAIGovernanceResult(
            governed_data=governed_input,
            original_data=original_input,
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,
            metadata={"operation": "embeddings_create", "deployment": deployment},
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy other methods to underlying client."""
        return getattr(self._client, name)


def govern_azure_chat_completion(
    messages: List[Dict[str, Any]],
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> AzureOpenAIGovernanceResult:
    """
    Apply governance to Azure OpenAI chat completion messages.

    Args:
        messages: Chat messages to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        AzureOpenAIGovernanceResult with governed messages
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

    return AzureOpenAIGovernanceResult(
        governed_data=governed,
        original_data=messages,
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_azure_chat_completion"},
    )


def govern_azure_completion(
    prompt: Union[str, List[str]],
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> AzureOpenAIGovernanceResult:
    """
    Apply governance to Azure OpenAI completion prompt.

    Args:
        prompt: Prompt to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        AzureOpenAIGovernanceResult with governed prompt
    """
    tork_instance = tork or Tork(config=config or TorkConfig())
    receipts = []

    def govern_text(text: str) -> str:
        result = tork_instance.govern(text)
        if result.receipt:
            receipts.append(result.receipt)
        return result.output

    if isinstance(prompt, str):
        governed = govern_text(prompt)
    else:
        governed = [govern_text(p) for p in prompt]

    return AzureOpenAIGovernanceResult(
        governed_data=governed,
        original_data=prompt,
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_azure_completion"},
    )


def govern_azure_embedding(
    input: Union[str, List[str]],
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> AzureOpenAIGovernanceResult:
    """
    Apply governance to Azure OpenAI embedding input.

    Args:
        input: Input text(s) to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        AzureOpenAIGovernanceResult with governed input
    """
    tork_instance = tork or Tork(config=config or TorkConfig())
    receipts = []

    def govern_text(text: str) -> str:
        result = tork_instance.govern(text)
        if result.receipt:
            receipts.append(result.receipt)
        return result.output

    if isinstance(input, str):
        governed = govern_text(input)
    else:
        governed = [govern_text(t) for t in input]

    return AzureOpenAIGovernanceResult(
        governed_data=governed,
        original_data=input,
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_azure_embedding"},
    )


def azure_openai_governed(
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
):
    """
    Decorator to add governance to Azure OpenAI operations.

    Args:
        tork: Tork instance
        config: TorkConfig if tork not provided

    Returns:
        Decorator function
    """
    tork_instance = tork or Tork(config=config or TorkConfig())

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Govern messages in kwargs
            if "messages" in kwargs:
                governed_msgs = []
                for msg in kwargs["messages"]:
                    governed_msg = msg.copy()
                    if "content" in msg and isinstance(msg["content"], str):
                        result = tork_instance.govern(msg["content"])
                        governed_msg["content"] = result.output
                    governed_msgs.append(governed_msg)
                kwargs["messages"] = governed_msgs

            # Govern prompt in kwargs
            if "prompt" in kwargs:
                if isinstance(kwargs["prompt"], str):
                    result = tork_instance.govern(kwargs["prompt"])
                    kwargs["prompt"] = result.output
                elif isinstance(kwargs["prompt"], list):
                    kwargs["prompt"] = [
                        tork_instance.govern(p).output for p in kwargs["prompt"]
                    ]

            return func(*args, **kwargs)

        return wrapper

    return decorator


__all__ = [
    "TorkAzureOpenAIClient",
    "AzureOpenAIGovernanceResult",
    "govern_azure_chat_completion",
    "govern_azure_completion",
    "govern_azure_embedding",
    "azure_openai_governed",
]
