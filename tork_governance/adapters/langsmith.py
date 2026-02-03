"""
Tork Governance adapter for LangSmith observability.

Provides governance for LangSmith tracing and logging with automatic
PII detection and redaction in traces, inputs, outputs, and feedback.
"""

from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from ..core import Tork, TorkConfig, GovernanceResult, GovernanceAction


@dataclass
class LangSmithGovernanceResult:
    """Result of a governed LangSmith operation."""
    success: bool
    operation: str
    governed_data: Any
    receipts: List[str] = field(default_factory=list)
    pii_detected: bool = False
    pii_types: List[str] = field(default_factory=list)
    redacted_fields: List[str] = field(default_factory=list)
    trace_id: Optional[str] = None


class TorkTracerCallback:
    """
    LangChain callback handler with Tork governance for LangSmith tracing.

    Automatically redacts PII from traces before they are sent to LangSmith.
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        govern_inputs: bool = True,
        govern_outputs: bool = True,
        govern_metadata: bool = True,
        attach_receipts: bool = True,
    ):
        """
        Initialize governed tracer callback.

        Args:
            tork: Tork governance instance
            config: Tork configuration
            govern_inputs: Whether to govern input data
            govern_outputs: Whether to govern output data
            govern_metadata: Whether to govern metadata
            attach_receipts: Whether to attach governance receipts to traces
        """
        self._tork = tork or Tork(config)
        self._govern_inputs = govern_inputs
        self._govern_outputs = govern_outputs
        self._govern_metadata = govern_metadata
        self._attach_receipts = attach_receipts
        self._receipts: List[str] = []
        self._run_receipts: Dict[str, List[str]] = {}

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipts."""
        return self._receipts.copy()

    def get_run_receipts(self, run_id: str) -> List[str]:
        """Get receipts for a specific run."""
        return self._run_receipts.get(run_id, []).copy()

    def _govern_dict(self, data: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        """Govern all string values in a dictionary."""
        governed = {}
        for key, value in data.items():
            if isinstance(value, str):
                result = self._tork.govern(value)
                governed[key] = result.output
                self._receipts.append(result.receipt.receipt_id)
                if run_id not in self._run_receipts:
                    self._run_receipts[run_id] = []
                self._run_receipts[run_id].append(result.receipt.receipt_id)
            elif isinstance(value, dict):
                governed[key] = self._govern_dict(value, run_id)
            elif isinstance(value, list):
                governed[key] = [
                    self._govern_dict(item, run_id) if isinstance(item, dict)
                    else self._tork.govern(item).output if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                governed[key] = value
        return governed

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: str,
        **kwargs
    ) -> None:
        """Govern LLM start event."""
        if not self._govern_inputs:
            return

        governed_prompts = []
        for prompt in prompts:
            result = self._tork.govern(prompt)
            governed_prompts.append(result.output)
            self._receipts.append(result.receipt.receipt_id)
            if run_id not in self._run_receipts:
                self._run_receipts[run_id] = []
            self._run_receipts[run_id].append(result.receipt.receipt_id)

        # Modify prompts in place if possible
        prompts.clear()
        prompts.extend(governed_prompts)

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[Any]],
        *,
        run_id: str,
        **kwargs
    ) -> None:
        """Govern chat model start event."""
        if not self._govern_inputs:
            return

        for message_list in messages:
            for message in message_list:
                if hasattr(message, 'content') and isinstance(message.content, str):
                    result = self._tork.govern(message.content)
                    message.content = result.output
                    self._receipts.append(result.receipt.receipt_id)
                    if run_id not in self._run_receipts:
                        self._run_receipts[run_id] = []
                    self._run_receipts[run_id].append(result.receipt.receipt_id)

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: str,
        **kwargs
    ) -> None:
        """Govern LLM end event."""
        if not self._govern_outputs:
            return

        if hasattr(response, 'generations'):
            for generation_list in response.generations:
                for generation in generation_list:
                    if hasattr(generation, 'text'):
                        result = self._tork.govern(generation.text)
                        generation.text = result.output
                        self._receipts.append(result.receipt.receipt_id)
                        if run_id not in self._run_receipts:
                            self._run_receipts[run_id] = []
                        self._run_receipts[run_id].append(result.receipt.receipt_id)

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: str,
        **kwargs
    ) -> None:
        """Govern chain start event."""
        if self._govern_inputs:
            governed_inputs = self._govern_dict(inputs, run_id)
            inputs.clear()
            inputs.update(governed_inputs)

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: str,
        **kwargs
    ) -> None:
        """Govern chain end event."""
        if self._govern_outputs:
            governed_outputs = self._govern_dict(outputs, run_id)
            outputs.clear()
            outputs.update(governed_outputs)

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: str,
        **kwargs
    ) -> str:
        """Govern tool start event."""
        if self._govern_inputs:
            result = self._tork.govern(input_str)
            self._receipts.append(result.receipt.receipt_id)
            if run_id not in self._run_receipts:
                self._run_receipts[run_id] = []
            self._run_receipts[run_id].append(result.receipt.receipt_id)
            return result.output
        return input_str

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: str,
        **kwargs
    ) -> str:
        """Govern tool end event."""
        if self._govern_outputs:
            result = self._tork.govern(output)
            self._receipts.append(result.receipt.receipt_id)
            if run_id not in self._run_receipts:
                self._run_receipts[run_id] = []
            self._run_receipts[run_id].append(result.receipt.receipt_id)
            return result.output
        return output

    def get_metadata(self, run_id: str) -> Dict[str, Any]:
        """Get governance metadata for a run."""
        return {
            "tork_governance": {
                "enabled": True,
                "receipts": self._run_receipts.get(run_id, []),
                "receipt_count": len(self._run_receipts.get(run_id, [])),
            }
        }


class TorkLangSmithClient:
    """Governed LangSmith client wrapper."""

    def __init__(
        self,
        client: Any = None,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        govern_inputs: bool = True,
        govern_outputs: bool = True,
        govern_feedback: bool = True,
        text_fields: Optional[List[str]] = None,
    ):
        """
        Initialize governed LangSmith client.

        Args:
            client: LangSmith client instance
            tork: Tork governance instance
            config: Tork configuration
            govern_inputs: Whether to govern run inputs
            govern_outputs: Whether to govern run outputs
            govern_feedback: Whether to govern feedback content
            text_fields: Specific fields to govern
        """
        self._client = client
        self._tork = tork or Tork(config)
        self._govern_inputs = govern_inputs
        self._govern_outputs = govern_outputs
        self._govern_feedback = govern_feedback
        self._text_fields = text_fields
        self._receipts: List[str] = []

    @property
    def client(self) -> Any:
        """Get the underlying LangSmith client."""
        return self._client

    @client.setter
    def client(self, value: Any):
        """Set the LangSmith client."""
        self._client = value

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipts."""
        return self._receipts.copy()

    def _govern_value(self, value: Any) -> tuple:
        """Govern a value and return governed version with metadata."""
        if isinstance(value, str):
            result = self._tork.govern(value)
            self._receipts.append(result.receipt.receipt_id)
            return result.output, result.pii.has_pii, result.pii.types, [result.receipt.receipt_id]
        elif isinstance(value, dict):
            return self._govern_dict(value)
        elif isinstance(value, list):
            governed_list = []
            any_pii = False
            all_types = []
            all_receipts = []
            for item in value:
                gov_item, pii, types, receipts = self._govern_value(item)
                governed_list.append(gov_item)
                if pii:
                    any_pii = True
                    all_types.extend(types)
                all_receipts.extend(receipts)
            return governed_list, any_pii, all_types, all_receipts
        return value, False, [], []

    def _govern_dict(self, data: Dict[str, Any]) -> tuple:
        """Govern all values in a dictionary."""
        governed = {}
        any_pii = False
        all_types = []
        all_receipts = []
        redacted_fields = []

        for key, value in data.items():
            if self._text_fields is None or key in self._text_fields:
                gov_value, pii, types, receipts = self._govern_value(value)
                governed[key] = gov_value
                if pii:
                    any_pii = True
                    all_types.extend(types)
                    redacted_fields.append(key)
                all_receipts.extend(receipts)
            else:
                governed[key] = value

        return governed, any_pii, list(set(all_types)), all_receipts, redacted_fields

    def create_run(
        self,
        name: str,
        run_type: str,
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> LangSmithGovernanceResult:
        """
        Create a run with governance.

        Args:
            name: Run name
            run_type: Type of run
            inputs: Run inputs
            outputs: Run outputs
            **kwargs: Additional arguments

        Returns:
            LangSmithGovernanceResult
        """
        all_receipts = []
        any_pii = False
        all_types = []
        redacted_fields = []

        governed_inputs = inputs
        governed_outputs = outputs

        if inputs and self._govern_inputs:
            governed_inputs, pii, types, receipts, fields = self._govern_dict(inputs)
            if pii:
                any_pii = True
                all_types.extend(types)
                redacted_fields.extend(fields)
            all_receipts.extend(receipts)

        if outputs and self._govern_outputs:
            governed_outputs, pii, types, receipts, fields = self._govern_dict(outputs)
            if pii:
                any_pii = True
                all_types.extend(types)
                redacted_fields.extend(fields)
            all_receipts.extend(receipts)

        # Add governance metadata
        extra = kwargs.get('extra', {})
        extra['tork_governance'] = {
            'enabled': True,
            'receipts': all_receipts,
            'pii_detected': any_pii,
            'redacted_fields': redacted_fields,
        }
        kwargs['extra'] = extra

        try:
            run = self._client.create_run(
                name=name,
                run_type=run_type,
                inputs=governed_inputs,
                outputs=governed_outputs,
                **kwargs
            )
            return LangSmithGovernanceResult(
                success=True,
                operation="create_run",
                governed_data=run,
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=redacted_fields,
                trace_id=str(run.id) if hasattr(run, 'id') else None,
            )
        except Exception as e:
            return LangSmithGovernanceResult(
                success=False,
                operation="create_run",
                governed_data=str(e),
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=redacted_fields,
            )

    def update_run(
        self,
        run_id: str,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        **kwargs
    ) -> LangSmithGovernanceResult:
        """
        Update a run with governance.

        Args:
            run_id: Run ID to update
            outputs: Run outputs
            error: Error message
            **kwargs: Additional arguments

        Returns:
            LangSmithGovernanceResult
        """
        all_receipts = []
        any_pii = False
        all_types = []
        redacted_fields = []

        governed_outputs = outputs
        governed_error = error

        if outputs and self._govern_outputs:
            governed_outputs, pii, types, receipts, fields = self._govern_dict(outputs)
            if pii:
                any_pii = True
                all_types.extend(types)
                redacted_fields.extend(fields)
            all_receipts.extend(receipts)

        if error:
            result = self._tork.govern(error)
            governed_error = result.output
            all_receipts.append(result.receipt.receipt_id)
            if result.pii.has_pii:
                any_pii = True
                all_types.extend(result.pii.types)
                redacted_fields.append("error")

        try:
            run = self._client.update_run(
                run_id=run_id,
                outputs=governed_outputs,
                error=governed_error,
                **kwargs
            )
            return LangSmithGovernanceResult(
                success=True,
                operation="update_run",
                governed_data=run,
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=redacted_fields,
                trace_id=run_id,
            )
        except Exception as e:
            return LangSmithGovernanceResult(
                success=False,
                operation="update_run",
                governed_data=str(e),
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=redacted_fields,
                trace_id=run_id,
            )

    def create_feedback(
        self,
        run_id: str,
        key: str,
        score: Optional[float] = None,
        value: Optional[str] = None,
        comment: Optional[str] = None,
        **kwargs
    ) -> LangSmithGovernanceResult:
        """
        Create feedback with governance.

        Args:
            run_id: Run ID for feedback
            key: Feedback key
            score: Feedback score
            value: Feedback value
            comment: Feedback comment
            **kwargs: Additional arguments

        Returns:
            LangSmithGovernanceResult
        """
        all_receipts = []
        any_pii = False
        all_types = []
        redacted_fields = []

        governed_value = value
        governed_comment = comment

        if value and self._govern_feedback:
            result = self._tork.govern(value)
            governed_value = result.output
            all_receipts.append(result.receipt.receipt_id)
            if result.pii.has_pii:
                any_pii = True
                all_types.extend(result.pii.types)
                redacted_fields.append("value")

        if comment and self._govern_feedback:
            result = self._tork.govern(comment)
            governed_comment = result.output
            all_receipts.append(result.receipt.receipt_id)
            if result.pii.has_pii:
                any_pii = True
                all_types.extend(result.pii.types)
                redacted_fields.append("comment")

        try:
            feedback = self._client.create_feedback(
                run_id=run_id,
                key=key,
                score=score,
                value=governed_value,
                comment=governed_comment,
                **kwargs
            )
            return LangSmithGovernanceResult(
                success=True,
                operation="create_feedback",
                governed_data=feedback,
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=redacted_fields,
                trace_id=run_id,
            )
        except Exception as e:
            return LangSmithGovernanceResult(
                success=False,
                operation="create_feedback",
                governed_data=str(e),
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=redacted_fields,
                trace_id=run_id,
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        return self._tork.get_stats()

    def reset_stats(self):
        """Reset governance statistics."""
        self._tork.reset_stats()


def govern_log_run(
    client: Any,
    name: str,
    run_type: str,
    inputs: Optional[Dict[str, Any]] = None,
    outputs: Optional[Dict[str, Any]] = None,
    tork: Optional[Tork] = None,
    **kwargs
) -> LangSmithGovernanceResult:
    """
    Govern and log a run to LangSmith.

    Args:
        client: LangSmith client
        name: Run name
        run_type: Run type
        inputs: Run inputs
        outputs: Run outputs
        tork: Tork instance
        **kwargs: Additional arguments

    Returns:
        LangSmithGovernanceResult
    """
    governed_client = TorkLangSmithClient(
        client=client,
        tork=tork,
    )
    return governed_client.create_run(name, run_type, inputs, outputs, **kwargs)


def govern_feedback(
    client: Any,
    run_id: str,
    key: str,
    tork: Optional[Tork] = None,
    score: Optional[float] = None,
    value: Optional[str] = None,
    comment: Optional[str] = None,
    **kwargs
) -> LangSmithGovernanceResult:
    """
    Govern and create feedback in LangSmith.

    Args:
        client: LangSmith client
        run_id: Run ID
        key: Feedback key
        tork: Tork instance
        score: Feedback score
        value: Feedback value
        comment: Feedback comment
        **kwargs: Additional arguments

    Returns:
        LangSmithGovernanceResult
    """
    governed_client = TorkLangSmithClient(
        client=client,
        tork=tork,
    )
    return governed_client.create_feedback(run_id, key, score, value, comment, **kwargs)


def create_governed_tracer(
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs
) -> TorkTracerCallback:
    """
    Create a governed tracer callback for LangChain.

    Args:
        tork: Tork instance
        config: Tork configuration
        **kwargs: Additional tracer options

    Returns:
        TorkTracerCallback
    """
    return TorkTracerCallback(
        tork=tork,
        config=config,
        **kwargs
    )
