"""
Tork Governance adapter for AWS Bedrock.

Provides governance for AWS Bedrock model invocations with automatic
PII detection and redaction for Claude, Titan, Llama, and other models.

Usage:
    from tork_governance.adapters.aws_bedrock import TorkBedrockClient

    # Wrap Bedrock client
    import boto3
    bedrock = boto3.client("bedrock-runtime")
    governed = TorkBedrockClient(bedrock)

    # All API calls now governed
    response = governed.invoke_model(
        modelId="anthropic.claude-3-sonnet-20240229-v1:0",
        body={"messages": [...]}
    )
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from ..core import Tork, TorkConfig, GovernanceResult, Receipt


@dataclass
class BedrockGovernanceResult:
    """Result of Bedrock governance operation."""

    governed_data: Any
    original_data: Any
    pii_detected: bool
    pii_count: int
    receipts: List[Receipt] = field(default_factory=list)
    response: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TorkBedrockClient:
    """
    Governed wrapper for AWS Bedrock client.

    Automatically applies PII detection and redaction to all
    model invocations and conversations.

    Example:
        import boto3
        from tork_governance.adapters.aws_bedrock import TorkBedrockClient

        bedrock = boto3.client("bedrock-runtime")
        governed = TorkBedrockClient(bedrock)

        # Model invocations are governed
        response = governed.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body={"messages": [{"role": "user", "content": "Hello"}]}
        )
    """

    def __init__(
        self,
        client: Any,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        redact_prompts: bool = True,
        redact_responses: bool = True,
        redact_system: bool = True,
    ):
        """
        Initialize governed Bedrock client.

        Args:
            client: Boto3 Bedrock runtime client
            tork: Tork instance for governance
            config: TorkConfig if tork not provided
            redact_prompts: Whether to redact PII in prompts
            redact_responses: Whether to redact PII in responses
            redact_system: Whether to redact PII in system prompts
        """
        self._client = client
        self._tork = tork or Tork(config=config or TorkConfig())
        self._redact_prompts = redact_prompts
        self._redact_responses = redact_responses
        self._redact_system = redact_system
        self._receipts: List[Receipt] = []

    @property
    def receipts(self) -> List[Receipt]:
        """Get all governance receipts."""
        return self._receipts.copy()

    @property
    def client(self) -> Any:
        """Access underlying Bedrock client."""
        return self._client

    def _govern_text(self, text: Any) -> tuple[Any, Optional[GovernanceResult]]:
        """Apply governance to text content."""
        if not isinstance(text, str):
            return text, None
        result = self._tork.govern(text)
        if result.receipt:
            self._receipts.append(result.receipt)
        return result.output, result

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

    def _govern_claude_body(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Apply governance to Claude-specific body format."""
        governed = body.copy()

        # Govern messages
        if self._redact_prompts and "messages" in governed:
            governed_messages = []
            for msg in governed["messages"]:
                governed_msg = msg.copy()
                if "content" in governed_msg:
                    if isinstance(governed_msg["content"], str):
                        governed_msg["content"], _ = self._govern_text(governed_msg["content"])
                    elif isinstance(governed_msg["content"], list):
                        governed_content = []
                        for block in governed_msg["content"]:
                            if isinstance(block, dict) and block.get("type") == "text":
                                governed_block = block.copy()
                                governed_block["text"], _ = self._govern_text(block.get("text", ""))
                                governed_content.append(governed_block)
                            else:
                                governed_content.append(block)
                        governed_msg["content"] = governed_content
                governed_messages.append(governed_msg)
            governed["messages"] = governed_messages

        # Govern system prompt
        if self._redact_system and "system" in governed:
            if isinstance(governed["system"], str):
                governed["system"], _ = self._govern_text(governed["system"])
            elif isinstance(governed["system"], list):
                governed_system = []
                for block in governed["system"]:
                    if isinstance(block, dict) and block.get("type") == "text":
                        governed_block = block.copy()
                        governed_block["text"], _ = self._govern_text(block.get("text", ""))
                        governed_system.append(governed_block)
                    else:
                        governed_system.append(block)
                governed["system"] = governed_system

        return governed

    def _govern_titan_body(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Apply governance to Titan-specific body format."""
        governed = body.copy()

        if self._redact_prompts and "inputText" in governed:
            governed["inputText"], _ = self._govern_text(governed["inputText"])

        return governed

    def _govern_llama_body(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Apply governance to Llama-specific body format."""
        governed = body.copy()

        if self._redact_prompts and "prompt" in governed:
            governed["prompt"], _ = self._govern_text(governed["prompt"])

        return governed

    def _govern_body(self, body: Dict[str, Any], model_id: str) -> Dict[str, Any]:
        """Apply governance to request body based on model type."""
        if "anthropic" in model_id.lower() or "claude" in model_id.lower():
            return self._govern_claude_body(body)
        elif "titan" in model_id.lower():
            return self._govern_titan_body(body)
        elif "llama" in model_id.lower() or "meta" in model_id.lower():
            return self._govern_llama_body(body)
        else:
            # Generic governance for unknown models
            return self._govern_dict(body)

    def _govern_response_body(self, body: Dict[str, Any], model_id: str) -> Dict[str, Any]:
        """Apply governance to response body based on model type."""
        governed = body.copy()

        if "anthropic" in model_id.lower() or "claude" in model_id.lower():
            if "content" in governed:
                governed_content = []
                for block in governed["content"]:
                    if isinstance(block, dict) and block.get("type") == "text":
                        governed_block = block.copy()
                        governed_block["text"], _ = self._govern_text(block.get("text", ""))
                        governed_content.append(governed_block)
                    else:
                        governed_content.append(block)
                governed["content"] = governed_content
        elif "titan" in model_id.lower():
            if "results" in governed:
                for result in governed["results"]:
                    if "outputText" in result:
                        result["outputText"], _ = self._govern_text(result["outputText"])
        elif "llama" in model_id.lower() or "meta" in model_id.lower():
            if "generation" in governed:
                governed["generation"], _ = self._govern_text(governed["generation"])

        return governed

    def invoke_model(
        self,
        modelId: str,
        body: Union[str, bytes, Dict[str, Any]],
        contentType: str = "application/json",
        accept: str = "application/json",
        **kwargs,
    ) -> BedrockGovernanceResult:
        """
        Invoke model with governance.

        Args:
            modelId: Model ID to invoke
            body: Request body (JSON string, bytes, or dict)
            contentType: Content type
            accept: Accept header
            **kwargs: Additional arguments

        Returns:
            BedrockGovernanceResult with governed response
        """
        receipts_before = len(self._receipts)

        # Parse body if needed
        if isinstance(body, str):
            original_body = json.loads(body)
        elif isinstance(body, bytes):
            original_body = json.loads(body.decode("utf-8"))
        else:
            original_body = body

        # Govern body
        governed_body = self._govern_body(original_body, modelId)

        # Call Bedrock
        response = self._client.invoke_model(
            modelId=modelId,
            body=json.dumps(governed_body),
            contentType=contentType,
            accept=accept,
            **kwargs,
        )

        # Parse and govern response
        response_body = json.loads(response["body"].read())
        if self._redact_responses:
            response_body = self._govern_response_body(response_body, modelId)

        new_receipts = self._receipts[receipts_before:]

        return BedrockGovernanceResult(
            governed_data=governed_body,
            original_data=original_body,
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response_body,
            metadata={"operation": "invoke_model", "model_id": modelId},
        )

    def invoke_model_with_response_stream(
        self,
        modelId: str,
        body: Union[str, bytes, Dict[str, Any]],
        contentType: str = "application/json",
        accept: str = "application/json",
        **kwargs,
    ) -> BedrockGovernanceResult:
        """
        Invoke model with streaming response and governance.

        Args:
            modelId: Model ID to invoke
            body: Request body
            contentType: Content type
            accept: Accept header
            **kwargs: Additional arguments

        Returns:
            BedrockGovernanceResult with stream response
        """
        receipts_before = len(self._receipts)

        # Parse body if needed
        if isinstance(body, str):
            original_body = json.loads(body)
        elif isinstance(body, bytes):
            original_body = json.loads(body.decode("utf-8"))
        else:
            original_body = body

        # Govern body
        governed_body = self._govern_body(original_body, modelId)

        # Call Bedrock
        response = self._client.invoke_model_with_response_stream(
            modelId=modelId,
            body=json.dumps(governed_body),
            contentType=contentType,
            accept=accept,
            **kwargs,
        )

        new_receipts = self._receipts[receipts_before:]

        return BedrockGovernanceResult(
            governed_data=governed_body,
            original_data=original_body,
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,  # Stream response
            metadata={"operation": "invoke_model_with_response_stream", "model_id": modelId, "stream": True},
        )

    def converse(
        self,
        modelId: str,
        messages: List[Dict[str, Any]],
        system: Optional[List[Dict[str, Any]]] = None,
        inferenceConfig: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> BedrockGovernanceResult:
        """
        Converse with model using governance.

        Args:
            modelId: Model ID to use
            messages: Conversation messages
            system: System prompts
            inferenceConfig: Inference configuration
            **kwargs: Additional arguments

        Returns:
            BedrockGovernanceResult with governed response
        """
        original_messages = messages
        original_system = system
        receipts_before = len(self._receipts)

        # Govern messages
        governed_messages = []
        if self._redact_prompts:
            for msg in messages:
                governed_msg = msg.copy()
                if "content" in governed_msg:
                    governed_content = []
                    for block in governed_msg["content"]:
                        if isinstance(block, dict) and "text" in block:
                            governed_block = block.copy()
                            governed_block["text"], _ = self._govern_text(block["text"])
                            governed_content.append(governed_block)
                        else:
                            governed_content.append(block)
                    governed_msg["content"] = governed_content
                governed_messages.append(governed_msg)
        else:
            governed_messages = messages

        # Govern system
        governed_system = system
        if self._redact_system and system:
            governed_system = []
            for block in system:
                if isinstance(block, dict) and "text" in block:
                    governed_block = block.copy()
                    governed_block["text"], _ = self._govern_text(block["text"])
                    governed_system.append(governed_block)
                else:
                    governed_system.append(block)

        # Build request
        request_kwargs = {
            "modelId": modelId,
            "messages": governed_messages,
            **kwargs,
        }
        if governed_system:
            request_kwargs["system"] = governed_system
        if inferenceConfig:
            request_kwargs["inferenceConfig"] = inferenceConfig

        # Call Bedrock
        response = self._client.converse(**request_kwargs)

        # Govern response
        if self._redact_responses and "output" in response:
            if "message" in response["output"]:
                msg = response["output"]["message"]
                if "content" in msg:
                    governed_content = []
                    for block in msg["content"]:
                        if isinstance(block, dict) and "text" in block:
                            governed_block = block.copy()
                            governed_block["text"], _ = self._govern_text(block["text"])
                            governed_content.append(governed_block)
                        else:
                            governed_content.append(block)
                    msg["content"] = governed_content

        new_receipts = self._receipts[receipts_before:]

        return BedrockGovernanceResult(
            governed_data={"messages": governed_messages, "system": governed_system},
            original_data={"messages": original_messages, "system": original_system},
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,
            metadata={"operation": "converse", "model_id": modelId},
        )

    def converse_stream(
        self,
        modelId: str,
        messages: List[Dict[str, Any]],
        system: Optional[List[Dict[str, Any]]] = None,
        inferenceConfig: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> BedrockGovernanceResult:
        """
        Converse with streaming response and governance.

        Args:
            modelId: Model ID to use
            messages: Conversation messages
            system: System prompts
            inferenceConfig: Inference configuration
            **kwargs: Additional arguments

        Returns:
            BedrockGovernanceResult with stream response
        """
        original_messages = messages
        original_system = system
        receipts_before = len(self._receipts)

        # Govern messages
        governed_messages = []
        if self._redact_prompts:
            for msg in messages:
                governed_msg = msg.copy()
                if "content" in governed_msg:
                    governed_content = []
                    for block in governed_msg["content"]:
                        if isinstance(block, dict) and "text" in block:
                            governed_block = block.copy()
                            governed_block["text"], _ = self._govern_text(block["text"])
                            governed_content.append(governed_block)
                        else:
                            governed_content.append(block)
                    governed_msg["content"] = governed_content
                governed_messages.append(governed_msg)
        else:
            governed_messages = messages

        # Govern system
        governed_system = system
        if self._redact_system and system:
            governed_system = []
            for block in system:
                if isinstance(block, dict) and "text" in block:
                    governed_block = block.copy()
                    governed_block["text"], _ = self._govern_text(block["text"])
                    governed_system.append(governed_block)
                else:
                    governed_system.append(block)

        # Build request
        request_kwargs = {
            "modelId": modelId,
            "messages": governed_messages,
            **kwargs,
        }
        if governed_system:
            request_kwargs["system"] = governed_system
        if inferenceConfig:
            request_kwargs["inferenceConfig"] = inferenceConfig

        # Call Bedrock
        response = self._client.converse_stream(**request_kwargs)

        new_receipts = self._receipts[receipts_before:]

        return BedrockGovernanceResult(
            governed_data={"messages": governed_messages, "system": governed_system},
            original_data={"messages": original_messages, "system": original_system},
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            response=response,
            metadata={"operation": "converse_stream", "model_id": modelId, "stream": True},
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy other methods to underlying client."""
        return getattr(self._client, name)


def govern_invoke_model(
    body: Dict[str, Any],
    model_id: str,
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> BedrockGovernanceResult:
    """
    Apply governance to Bedrock invoke_model body.

    Args:
        body: Request body to govern
        model_id: Model ID for format detection
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        BedrockGovernanceResult with governed body
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

    governed = govern_dict(body)

    return BedrockGovernanceResult(
        governed_data=governed,
        original_data=body,
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_invoke_model", "model_id": model_id},
    )


def govern_converse(
    messages: List[Dict[str, Any]],
    system: Optional[List[Dict[str, Any]]] = None,
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> BedrockGovernanceResult:
    """
    Apply governance to Bedrock converse messages.

    Args:
        messages: Messages to govern
        system: System prompts to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        BedrockGovernanceResult with governed messages
    """
    tork_instance = tork or Tork(config=config or TorkConfig())
    receipts = []

    def govern_text(text: str) -> str:
        result = tork_instance.govern(text)
        if result.receipt:
            receipts.append(result.receipt)
        return result.output

    # Govern messages
    governed_messages = []
    for msg in messages:
        governed_msg = msg.copy()
        if "content" in governed_msg:
            governed_content = []
            for block in governed_msg["content"]:
                if isinstance(block, dict) and "text" in block:
                    governed_block = block.copy()
                    governed_block["text"] = govern_text(block["text"])
                    governed_content.append(governed_block)
                else:
                    governed_content.append(block)
            governed_msg["content"] = governed_content
        governed_messages.append(governed_msg)

    # Govern system
    governed_system = None
    if system:
        governed_system = []
        for block in system:
            if isinstance(block, dict) and "text" in block:
                governed_block = block.copy()
                governed_block["text"] = govern_text(block["text"])
                governed_system.append(governed_block)
            else:
                governed_system.append(block)

    return BedrockGovernanceResult(
        governed_data={"messages": governed_messages, "system": governed_system},
        original_data={"messages": messages, "system": system},
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_converse"},
    )


def bedrock_governed(
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
):
    """
    Decorator to add governance to Bedrock operations.

    Args:
        tork: Tork instance
        config: TorkConfig if tork not provided

    Returns:
        Decorator function
    """
    tork_instance = tork or Tork(config=config or TorkConfig())

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Govern body if present
            if "body" in kwargs:
                body = kwargs["body"]
                if isinstance(body, str):
                    body = json.loads(body)
                elif isinstance(body, bytes):
                    body = json.loads(body.decode("utf-8"))

                # Recursive governance
                def govern_value(v):
                    if isinstance(v, str):
                        return tork_instance.govern(v).output
                    elif isinstance(v, dict):
                        return {k: govern_value(val) for k, val in v.items()}
                    elif isinstance(v, list):
                        return [govern_value(item) for item in v]
                    return v

                kwargs["body"] = json.dumps(govern_value(body))

            return func(*args, **kwargs)

        return wrapper

    return decorator


__all__ = [
    "TorkBedrockClient",
    "BedrockGovernanceResult",
    "govern_invoke_model",
    "govern_converse",
    "bedrock_governed",
]
