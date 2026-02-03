"""
Tork Governance adapter for Humanloop prompt optimization.

Provides governance for Humanloop's prompt management and optimization
with automatic PII detection and redaction.

Usage:
    from tork_governance.adapters.humanloop import TorkHumanloopClient, govern_log

    # Wrap Humanloop client
    client = TorkHumanloopClient(humanloop_client)

    # Or use convenience functions
    result = govern_log(log_data, tork=tork)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from ..core import Tork, TorkConfig, GovernanceResult, Receipt


@dataclass
class HumanloopGovernanceResult:
    """Result of Humanloop governance operation."""

    governed_data: Any
    original_data: Any
    pii_detected: bool
    pii_count: int
    receipts: List[Receipt] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TorkHumanloopClient:
    """
    Governed wrapper for Humanloop client.

    Automatically applies PII detection and redaction to all
    logging, feedback, and prompt operations.

    Example:
        from humanloop import Humanloop
        from tork_governance.adapters.humanloop import TorkHumanloopClient

        humanloop = Humanloop(api_key="...")
        governed = TorkHumanloopClient(humanloop)

        # All operations now governed
        governed.log(...)
    """

    def __init__(
        self,
        client: Any,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        redact_inputs: bool = True,
        redact_outputs: bool = True,
        redact_feedback: bool = True,
        redact_metadata: bool = True,
    ):
        """
        Initialize governed Humanloop client.

        Args:
            client: Humanloop client instance
            tork: Tork instance for governance
            config: TorkConfig if tork not provided
            redact_inputs: Whether to redact PII in inputs
            redact_outputs: Whether to redact PII in outputs
            redact_feedback: Whether to redact PII in feedback
            redact_metadata: Whether to redact PII in metadata
        """
        self._client = client
        self._tork = tork or Tork(config=config or TorkConfig())
        self._redact_inputs = redact_inputs
        self._redact_outputs = redact_outputs
        self._redact_feedback = redact_feedback
        self._redact_metadata = redact_metadata
        self._receipts: List[Receipt] = []

    @property
    def receipts(self) -> List[Receipt]:
        """Get all governance receipts."""
        return self._receipts.copy()

    @property
    def client(self) -> Any:
        """Access underlying Humanloop client."""
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

    def log(
        self,
        project: str,
        inputs: Optional[Dict[str, Any]] = None,
        output: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        config_id: Optional[str] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> HumanloopGovernanceResult:
        """
        Log data with governance.

        Args:
            project: Project name or ID
            inputs: Input variables
            output: Model output
            messages: Chat messages
            config_id: Configuration ID
            source: Source identifier
            metadata: Additional metadata
            **kwargs: Additional arguments

        Returns:
            HumanloopGovernanceResult with governed data
        """
        original_inputs = inputs
        original_output = output
        original_messages = messages
        receipts_before = len(self._receipts)

        # Govern inputs
        governed_inputs = inputs
        if self._redact_inputs and inputs:
            governed_inputs = self._govern_dict(inputs)

        # Govern output
        governed_output = output
        if self._redact_outputs and output:
            governed_output, _ = self._govern_text(output)

        # Govern messages
        governed_messages = messages
        if self._redact_inputs and messages:
            governed_messages = self._govern_messages(messages)

        # Govern metadata
        governed_metadata = metadata
        if self._redact_metadata and metadata:
            governed_metadata = self._govern_dict(metadata)

        # Call Humanloop
        result = None
        if hasattr(self._client, "log"):
            log_kwargs = {
                "project": project,
                **kwargs,
            }
            if governed_inputs is not None:
                log_kwargs["inputs"] = governed_inputs
            if governed_output is not None:
                log_kwargs["output"] = governed_output
            if governed_messages is not None:
                log_kwargs["messages"] = governed_messages
            if config_id is not None:
                log_kwargs["config_id"] = config_id
            if source is not None:
                log_kwargs["source"] = source
            if governed_metadata is not None:
                log_kwargs["metadata"] = governed_metadata

            result = self._client.log(**log_kwargs)

        new_receipts = self._receipts[receipts_before:]

        return HumanloopGovernanceResult(
            governed_data={
                "project": project,
                "inputs": governed_inputs,
                "output": governed_output,
                "messages": governed_messages,
                "metadata": governed_metadata,
                "result": result,
            },
            original_data={
                "project": project,
                "inputs": original_inputs,
                "output": original_output,
                "messages": original_messages,
                "metadata": metadata,
            },
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            metadata={"operation": "log", "project": project},
        )

    def feedback(
        self,
        data_id: str,
        type: str,
        value: Any,
        user: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> HumanloopGovernanceResult:
        """
        Submit feedback with governance.

        Args:
            data_id: Data ID for feedback
            type: Feedback type
            value: Feedback value
            user: User identifier
            metadata: Additional metadata
            **kwargs: Additional arguments

        Returns:
            HumanloopGovernanceResult with governed feedback
        """
        original_value = value
        receipts_before = len(self._receipts)

        # Govern value if string
        governed_value = value
        if self._redact_feedback and isinstance(value, str):
            governed_value, _ = self._govern_text(value)
        elif self._redact_feedback and isinstance(value, dict):
            governed_value = self._govern_dict(value)

        # Govern user if provided
        governed_user = user
        if self._redact_feedback and user:
            governed_user, _ = self._govern_text(user)

        # Govern metadata
        governed_metadata = metadata
        if self._redact_metadata and metadata:
            governed_metadata = self._govern_dict(metadata)

        # Call Humanloop
        result = None
        if hasattr(self._client, "feedback"):
            feedback_kwargs = {
                "data_id": data_id,
                "type": type,
                "value": governed_value,
                **kwargs,
            }
            if governed_user is not None:
                feedback_kwargs["user"] = governed_user
            if governed_metadata is not None:
                feedback_kwargs["metadata"] = governed_metadata

            result = self._client.feedback(**feedback_kwargs)

        new_receipts = self._receipts[receipts_before:]

        return HumanloopGovernanceResult(
            governed_data={
                "data_id": data_id,
                "type": type,
                "value": governed_value,
                "user": governed_user,
                "metadata": governed_metadata,
                "result": result,
            },
            original_data={
                "data_id": data_id,
                "type": type,
                "value": original_value,
                "user": user,
                "metadata": metadata,
            },
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            metadata={"operation": "feedback", "type": type},
        )

    def complete(
        self,
        project: str,
        inputs: Optional[Dict[str, Any]] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        config_id: Optional[str] = None,
        provider_api_keys: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> HumanloopGovernanceResult:
        """
        Generate completion with governance.

        Args:
            project: Project name or ID
            inputs: Input variables
            messages: Chat messages
            config_id: Configuration ID
            provider_api_keys: API keys for providers
            metadata: Additional metadata
            **kwargs: Additional arguments

        Returns:
            HumanloopGovernanceResult with governed completion
        """
        original_inputs = inputs
        original_messages = messages
        receipts_before = len(self._receipts)

        # Govern inputs
        governed_inputs = inputs
        if self._redact_inputs and inputs:
            governed_inputs = self._govern_dict(inputs)

        # Govern messages
        governed_messages = messages
        if self._redact_inputs and messages:
            governed_messages = self._govern_messages(messages)

        # Govern metadata
        governed_metadata = metadata
        if self._redact_metadata and metadata:
            governed_metadata = self._govern_dict(metadata)

        # Call Humanloop
        result = None
        if hasattr(self._client, "complete"):
            complete_kwargs = {
                "project": project,
                **kwargs,
            }
            if governed_inputs is not None:
                complete_kwargs["inputs"] = governed_inputs
            if governed_messages is not None:
                complete_kwargs["messages"] = governed_messages
            if config_id is not None:
                complete_kwargs["config_id"] = config_id
            if provider_api_keys is not None:
                complete_kwargs["provider_api_keys"] = provider_api_keys
            if governed_metadata is not None:
                complete_kwargs["metadata"] = governed_metadata

            result = self._client.complete(**complete_kwargs)

        # Govern response output
        governed_result = result
        if self._redact_outputs and result:
            if hasattr(result, "output") and isinstance(result.output, str):
                result.output, _ = self._govern_text(result.output)

        new_receipts = self._receipts[receipts_before:]

        return HumanloopGovernanceResult(
            governed_data={
                "project": project,
                "inputs": governed_inputs,
                "messages": governed_messages,
                "metadata": governed_metadata,
                "result": governed_result,
            },
            original_data={
                "project": project,
                "inputs": original_inputs,
                "messages": original_messages,
                "metadata": metadata,
            },
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            metadata={"operation": "complete", "project": project},
        )

    def chat(
        self,
        project: str,
        messages: List[Dict[str, Any]],
        inputs: Optional[Dict[str, Any]] = None,
        config_id: Optional[str] = None,
        provider_api_keys: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> HumanloopGovernanceResult:
        """
        Generate chat completion with governance.

        Args:
            project: Project name or ID
            messages: Chat messages
            inputs: Input variables
            config_id: Configuration ID
            provider_api_keys: API keys for providers
            metadata: Additional metadata
            **kwargs: Additional arguments

        Returns:
            HumanloopGovernanceResult with governed chat
        """
        original_messages = messages
        original_inputs = inputs
        receipts_before = len(self._receipts)

        # Govern messages
        governed_messages = messages
        if self._redact_inputs:
            governed_messages = self._govern_messages(messages)

        # Govern inputs
        governed_inputs = inputs
        if self._redact_inputs and inputs:
            governed_inputs = self._govern_dict(inputs)

        # Govern metadata
        governed_metadata = metadata
        if self._redact_metadata and metadata:
            governed_metadata = self._govern_dict(metadata)

        # Call Humanloop
        result = None
        if hasattr(self._client, "chat"):
            chat_kwargs = {
                "project": project,
                "messages": governed_messages,
                **kwargs,
            }
            if governed_inputs is not None:
                chat_kwargs["inputs"] = governed_inputs
            if config_id is not None:
                chat_kwargs["config_id"] = config_id
            if provider_api_keys is not None:
                chat_kwargs["provider_api_keys"] = provider_api_keys
            if governed_metadata is not None:
                chat_kwargs["metadata"] = governed_metadata

            result = self._client.chat(**chat_kwargs)

        # Govern response
        governed_result = result
        if self._redact_outputs and result:
            if hasattr(result, "output") and isinstance(result.output, str):
                result.output, _ = self._govern_text(result.output)
            if hasattr(result, "message") and hasattr(result.message, "content"):
                if isinstance(result.message.content, str):
                    result.message.content, _ = self._govern_text(result.message.content)

        new_receipts = self._receipts[receipts_before:]

        return HumanloopGovernanceResult(
            governed_data={
                "project": project,
                "messages": governed_messages,
                "inputs": governed_inputs,
                "metadata": governed_metadata,
                "result": governed_result,
            },
            original_data={
                "project": project,
                "messages": original_messages,
                "inputs": original_inputs,
                "metadata": metadata,
            },
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            metadata={"operation": "chat", "project": project},
        )

    def evaluate(
        self,
        project: str,
        data_id: str,
        evaluator_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> HumanloopGovernanceResult:
        """
        Run evaluation with governance.

        Args:
            project: Project name or ID
            data_id: Data ID to evaluate
            evaluator_id: Evaluator to use
            metadata: Additional metadata
            **kwargs: Additional arguments

        Returns:
            HumanloopGovernanceResult with governed evaluation
        """
        receipts_before = len(self._receipts)

        # Govern metadata
        governed_metadata = metadata
        if self._redact_metadata and metadata:
            governed_metadata = self._govern_dict(metadata)

        # Call Humanloop
        result = None
        if hasattr(self._client, "evaluate"):
            result = self._client.evaluate(
                project=project,
                data_id=data_id,
                evaluator_id=evaluator_id,
                metadata=governed_metadata,
                **kwargs,
            )

        new_receipts = self._receipts[receipts_before:]

        return HumanloopGovernanceResult(
            governed_data={
                "project": project,
                "data_id": data_id,
                "evaluator_id": evaluator_id,
                "metadata": governed_metadata,
                "result": result,
            },
            original_data={
                "project": project,
                "data_id": data_id,
                "evaluator_id": evaluator_id,
                "metadata": metadata,
            },
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            metadata={"operation": "evaluate", "project": project},
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy other methods to underlying client."""
        return getattr(self._client, name)


def govern_log(
    log_data: Dict[str, Any],
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> HumanloopGovernanceResult:
    """
    Apply governance to log data.

    Args:
        log_data: Log data to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        HumanloopGovernanceResult with governed data
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

    governed = govern_dict(log_data)

    return HumanloopGovernanceResult(
        governed_data=governed,
        original_data=log_data,
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_log"},
    )


def govern_feedback(
    feedback_data: Dict[str, Any],
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> HumanloopGovernanceResult:
    """
    Apply governance to feedback data.

    Args:
        feedback_data: Feedback data to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional options

    Returns:
        HumanloopGovernanceResult with governed data
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

    governed = govern_dict(feedback_data)

    return HumanloopGovernanceResult(
        governed_data=governed,
        original_data=feedback_data,
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_feedback"},
    )


def humanloop_governed(
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
):
    """
    Decorator to add governance to Humanloop operations.

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

            # Govern kwargs
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
                elif key == "messages" and isinstance(value, list):
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
                else:
                    governed_kwargs[key] = value

            return func(*governed_args, **governed_kwargs)

        return wrapper

    return decorator


__all__ = [
    "TorkHumanloopClient",
    "HumanloopGovernanceResult",
    "govern_log",
    "govern_feedback",
    "humanloop_governed",
]
