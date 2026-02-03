"""
Tork Governance adapter for PromptLayer prompt management.

Provides governance for PromptLayer's prompt tracking and logging
with automatic PII detection and redaction.

Usage:
    from tork_governance.adapters.promptlayer import TorkPromptLayerClient, govern_log_request

    # Wrap PromptLayer client
    client = TorkPromptLayerClient(promptlayer_client)

    # Or use convenience functions
    result = govern_log_request(request_data, tork=tork)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from ..core import Tork, TorkConfig, GovernanceResult, Receipt


@dataclass
class PromptLayerGovernanceResult:
    """Result of PromptLayer governance operation."""

    governed_data: Any
    original_data: Any
    pii_detected: bool
    pii_count: int
    receipts: List[Receipt] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TorkPromptLayerClient:
    """
    Governed wrapper for PromptLayer client.

    Automatically applies PII detection and redaction to all
    prompt tracking and logging operations.

    Example:
        import promptlayer
        from tork_governance.adapters.promptlayer import TorkPromptLayerClient

        promptlayer.api_key = "..."
        governed = TorkPromptLayerClient(promptlayer)

        # All tracking now governed
        governed.track_request(...)
    """

    def __init__(
        self,
        client: Any,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        redact_prompts: bool = True,
        redact_responses: bool = True,
        redact_metadata: bool = True,
        redact_tags: bool = True,
    ):
        """
        Initialize governed PromptLayer client.

        Args:
            client: PromptLayer client/module
            tork: Tork instance for governance
            config: TorkConfig if tork not provided
            redact_prompts: Whether to redact PII in prompts
            redact_responses: Whether to redact PII in responses
            redact_metadata: Whether to redact PII in metadata
            redact_tags: Whether to redact PII in tags
        """
        self._client = client
        self._tork = tork or Tork(config=config or TorkConfig())
        self._redact_prompts = redact_prompts
        self._redact_responses = redact_responses
        self._redact_metadata = redact_metadata
        self._redact_tags = redact_tags
        self._receipts: List[Receipt] = []

    @property
    def receipts(self) -> List[Receipt]:
        """Get all governance receipts."""
        return self._receipts.copy()

    @property
    def client(self) -> Any:
        """Access underlying PromptLayer client."""
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
            if "content" in governed_msg and isinstance(governed_msg["content"], str):
                governed_msg["content"], _ = self._govern_text(governed_msg["content"])
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

    def log_request(
        self,
        function_name: str,
        provider_type: str,
        args: List[Any],
        kwargs: Dict[str, Any],
        tags: Optional[List[str]] = None,
        request_response: Optional[Dict[str, Any]] = None,
        request_start_time: Optional[float] = None,
        request_end_time: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **extra_kwargs,
    ) -> PromptLayerGovernanceResult:
        """
        Log a request with governance.

        Args:
            function_name: Name of the function called
            provider_type: Provider type (openai, anthropic, etc.)
            args: Positional arguments
            kwargs: Keyword arguments
            tags: Optional tags
            request_response: Response data
            request_start_time: Request start timestamp
            request_end_time: Request end timestamp
            metadata: Additional metadata
            **extra_kwargs: Additional arguments

        Returns:
            PromptLayerGovernanceResult with governed data
        """
        original_kwargs = kwargs.copy()
        receipts_before = len(self._receipts)

        # Govern prompt in kwargs
        governed_kwargs = kwargs.copy()
        if self._redact_prompts:
            if "messages" in governed_kwargs:
                governed_kwargs["messages"] = self._govern_messages(governed_kwargs["messages"])
            if "prompt" in governed_kwargs:
                governed_kwargs["prompt"], _ = self._govern_text(governed_kwargs["prompt"])

        # Govern response
        governed_response = request_response
        if self._redact_responses and request_response:
            governed_response = self._govern_dict(request_response)

        # Govern tags
        governed_tags = tags
        if self._redact_tags and tags:
            governed_tags = []
            for tag in tags:
                text, _ = self._govern_text(tag)
                governed_tags.append(text)

        # Govern metadata
        governed_metadata = metadata
        if self._redact_metadata and metadata:
            governed_metadata = self._govern_dict(metadata)

        # Call PromptLayer
        result = None
        if hasattr(self._client, "log_request"):
            result = self._client.log_request(
                function_name=function_name,
                provider_type=provider_type,
                args=args,
                kwargs=governed_kwargs,
                tags=governed_tags,
                request_response=governed_response,
                request_start_time=request_start_time,
                request_end_time=request_end_time,
                metadata=governed_metadata,
                **extra_kwargs,
            )

        new_receipts = self._receipts[receipts_before:]

        return PromptLayerGovernanceResult(
            governed_data={
                "kwargs": governed_kwargs,
                "response": governed_response,
                "tags": governed_tags,
                "metadata": governed_metadata,
                "result": result,
            },
            original_data={
                "kwargs": original_kwargs,
                "response": request_response,
                "tags": tags,
                "metadata": metadata,
            },
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            metadata={"operation": "log_request", "function_name": function_name},
        )

    def track_request(
        self,
        request_id: str,
        prompt_name: Optional[str] = None,
        prompt_input_variables: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> PromptLayerGovernanceResult:
        """
        Track a request with governance.

        Args:
            request_id: Request ID to track
            prompt_name: Name of the prompt template
            prompt_input_variables: Variables passed to prompt
            tags: Optional tags
            metadata: Additional metadata
            **kwargs: Additional arguments

        Returns:
            PromptLayerGovernanceResult with governed data
        """
        receipts_before = len(self._receipts)

        # Govern input variables
        governed_variables = prompt_input_variables
        if self._redact_prompts and prompt_input_variables:
            governed_variables = self._govern_dict(prompt_input_variables)

        # Govern tags
        governed_tags = tags
        if self._redact_tags and tags:
            governed_tags = []
            for tag in tags:
                text, _ = self._govern_text(tag)
                governed_tags.append(text)

        # Govern metadata
        governed_metadata = metadata
        if self._redact_metadata and metadata:
            governed_metadata = self._govern_dict(metadata)

        # Call PromptLayer
        result = None
        if hasattr(self._client, "track_request"):
            result = self._client.track_request(
                request_id=request_id,
                prompt_name=prompt_name,
                prompt_input_variables=governed_variables,
                tags=governed_tags,
                metadata=governed_metadata,
                **kwargs,
            )

        new_receipts = self._receipts[receipts_before:]

        return PromptLayerGovernanceResult(
            governed_data={
                "request_id": request_id,
                "prompt_input_variables": governed_variables,
                "tags": governed_tags,
                "metadata": governed_metadata,
                "result": result,
            },
            original_data={
                "request_id": request_id,
                "prompt_input_variables": prompt_input_variables,
                "tags": tags,
                "metadata": metadata,
            },
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            metadata={"operation": "track_request", "prompt_name": prompt_name},
        )

    def track_prompt(
        self,
        prompt_name: str,
        prompt_template: str,
        input_variables: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> PromptLayerGovernanceResult:
        """
        Track a prompt template with governance.

        Args:
            prompt_name: Name of the prompt
            prompt_template: The prompt template
            input_variables: Variables for the template
            tags: Optional tags
            metadata: Additional metadata
            **kwargs: Additional arguments

        Returns:
            PromptLayerGovernanceResult with governed data
        """
        receipts_before = len(self._receipts)

        # Govern prompt template
        governed_template = prompt_template
        if self._redact_prompts:
            governed_template, _ = self._govern_text(prompt_template)

        # Govern input variables
        governed_variables = input_variables
        if self._redact_prompts and input_variables:
            governed_variables = self._govern_dict(input_variables)

        # Govern tags
        governed_tags = tags
        if self._redact_tags and tags:
            governed_tags = []
            for tag in tags:
                text, _ = self._govern_text(tag)
                governed_tags.append(text)

        # Govern metadata
        governed_metadata = metadata
        if self._redact_metadata and metadata:
            governed_metadata = self._govern_dict(metadata)

        # Call PromptLayer
        result = None
        if hasattr(self._client, "track_prompt"):
            result = self._client.track_prompt(
                prompt_name=prompt_name,
                prompt_template=governed_template,
                input_variables=governed_variables,
                tags=governed_tags,
                metadata=governed_metadata,
                **kwargs,
            )

        new_receipts = self._receipts[receipts_before:]

        return PromptLayerGovernanceResult(
            governed_data={
                "prompt_name": prompt_name,
                "prompt_template": governed_template,
                "input_variables": governed_variables,
                "tags": governed_tags,
                "metadata": governed_metadata,
                "result": result,
            },
            original_data={
                "prompt_name": prompt_name,
                "prompt_template": prompt_template,
                "input_variables": input_variables,
                "tags": tags,
                "metadata": metadata,
            },
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            metadata={"operation": "track_prompt", "prompt_name": prompt_name},
        )

    def get_prompt_template(
        self,
        prompt_name: str,
        version: Optional[int] = None,
        **kwargs,
    ) -> PromptLayerGovernanceResult:
        """
        Get a prompt template with governance applied to response.

        Args:
            prompt_name: Name of the prompt
            version: Optional version number
            **kwargs: Additional arguments

        Returns:
            PromptLayerGovernanceResult with governed template
        """
        receipts_before = len(self._receipts)

        # Get from PromptLayer
        result = None
        if hasattr(self._client, "get_prompt_template"):
            result = self._client.get_prompt_template(
                prompt_name=prompt_name,
                version=version,
                **kwargs,
            )

        # Govern the returned template
        governed_result = result
        if self._redact_prompts and result:
            if isinstance(result, dict):
                governed_result = self._govern_dict(result)
            elif isinstance(result, str):
                governed_result, _ = self._govern_text(result)

        new_receipts = self._receipts[receipts_before:]

        return PromptLayerGovernanceResult(
            governed_data=governed_result,
            original_data=result,
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            metadata={"operation": "get_prompt_template", "prompt_name": prompt_name},
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy other methods to underlying client."""
        return getattr(self._client, name)


def govern_log_request(
    request_data: Dict[str, Any],
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> PromptLayerGovernanceResult:
    """
    Apply governance to request logging data.

    Args:
        request_data: Request data to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        PromptLayerGovernanceResult with governed data
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

    governed = govern_dict(request_data)

    return PromptLayerGovernanceResult(
        governed_data=governed,
        original_data=request_data,
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_log_request"},
    )


def govern_track_prompt(
    prompt_template: str,
    input_variables: Optional[Dict[str, Any]] = None,
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> PromptLayerGovernanceResult:
    """
    Apply governance to prompt tracking data.

    Args:
        prompt_template: Prompt template to govern
        input_variables: Variables to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        PromptLayerGovernanceResult with governed data
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
            else:
                governed[key] = value
        return governed

    governed_template = govern_text(prompt_template)
    governed_variables = govern_dict(input_variables) if input_variables else None

    return PromptLayerGovernanceResult(
        governed_data={
            "prompt_template": governed_template,
            "input_variables": governed_variables,
        },
        original_data={
            "prompt_template": prompt_template,
            "input_variables": input_variables,
        },
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_track_prompt"},
    )


def promptlayer_governed(
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
):
    """
    Decorator to add governance to PromptLayer operations.

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

            # Govern string keyword arguments
            governed_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    result = tork_instance.govern(value)
                    governed_kwargs[key] = result.output
                elif isinstance(value, dict):
                    governed_kwargs[key] = {
                        k: tork_instance.govern(v).output if isinstance(v, str) else v
                        for k, v in value.items()
                    }
                else:
                    governed_kwargs[key] = value

            return func(*governed_args, **governed_kwargs)

        return wrapper

    return decorator


__all__ = [
    "TorkPromptLayerClient",
    "PromptLayerGovernanceResult",
    "govern_log_request",
    "govern_track_prompt",
    "promptlayer_governed",
]
