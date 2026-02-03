"""
Tork Governance adapter for Langfuse LLM analytics.

Provides governance for Langfuse tracing with automatic PII detection
and redaction in inputs, outputs, and metadata.
"""

from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
import functools
import uuid

from ..core import Tork, TorkConfig, GovernanceResult, GovernanceAction


@dataclass
class LangfuseGovernanceResult:
    """Result of a governed Langfuse operation."""
    success: bool
    operation: str
    governed_data: Any
    receipts: List[str] = field(default_factory=list)
    pii_detected: bool = False
    pii_types: List[str] = field(default_factory=list)
    redacted_fields: List[str] = field(default_factory=list)
    trace_id: Optional[str] = None
    generation_id: Optional[str] = None


class TorkLangfuseClient:
    """Governed Langfuse client wrapper."""

    def __init__(
        self,
        client: Any = None,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        govern_inputs: bool = True,
        govern_outputs: bool = True,
        govern_metadata: bool = True,
        attach_receipts: bool = True,
    ):
        """
        Initialize governed Langfuse client.

        Args:
            client: Langfuse client instance
            tork: Tork governance instance
            config: Tork configuration
            govern_inputs: Whether to govern input data
            govern_outputs: Whether to govern output data
            govern_metadata: Whether to govern metadata
            attach_receipts: Whether to attach governance receipts
        """
        self._client = client
        self._tork = tork or Tork(config)
        self._govern_inputs = govern_inputs
        self._govern_outputs = govern_outputs
        self._govern_metadata = govern_metadata
        self._attach_receipts = attach_receipts
        self._receipts: List[str] = []
        self._trace_receipts: Dict[str, List[str]] = {}

    @property
    def client(self) -> Any:
        """Get the underlying Langfuse client."""
        return self._client

    @client.setter
    def client(self, value: Any):
        """Set the Langfuse client."""
        self._client = value

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipts."""
        return self._receipts.copy()

    def get_trace_receipts(self, trace_id: str) -> List[str]:
        """Get receipts for a specific trace."""
        return self._trace_receipts.get(trace_id, []).copy()

    def _govern_value(self, value: Any, trace_id: Optional[str] = None) -> tuple:
        """Govern a value and return governed version with metadata."""
        if isinstance(value, str):
            result = self._tork.govern(value)
            self._receipts.append(result.receipt.receipt_id)
            if trace_id:
                if trace_id not in self._trace_receipts:
                    self._trace_receipts[trace_id] = []
                self._trace_receipts[trace_id].append(result.receipt.receipt_id)
            return result.output, result.pii.has_pii, result.pii.types, [result.receipt.receipt_id]
        elif isinstance(value, dict):
            return self._govern_dict(value, trace_id)
        elif isinstance(value, list):
            governed_list = []
            any_pii = False
            all_types = []
            all_receipts = []
            for item in value:
                gov_item, pii, types, receipts = self._govern_value(item, trace_id)
                governed_list.append(gov_item)
                if pii:
                    any_pii = True
                    all_types.extend(types)
                all_receipts.extend(receipts)
            return governed_list, any_pii, list(set(all_types)), all_receipts
        return value, False, [], []

    def _govern_dict(self, data: Dict[str, Any], trace_id: Optional[str] = None) -> tuple:
        """Govern all values in a dictionary."""
        governed = {}
        any_pii = False
        all_types = []
        all_receipts = []
        redacted_fields = []

        for key, value in data.items():
            gov_value, pii, types, receipts = self._govern_value(value, trace_id)
            governed[key] = gov_value
            if pii:
                any_pii = True
                all_types.extend(types)
                redacted_fields.append(key)
            all_receipts.extend(receipts)

        return governed, any_pii, list(set(all_types)), all_receipts, redacted_fields

    def _govern_messages(self, messages: List[Dict[str, Any]], trace_id: Optional[str] = None) -> tuple:
        """Govern chat messages."""
        governed_messages = []
        any_pii = False
        all_types = []
        all_receipts = []
        redacted_fields = []

        for message in messages:
            governed_msg = message.copy()
            if 'content' in message and isinstance(message['content'], str):
                result = self._tork.govern(message['content'])
                governed_msg['content'] = result.output
                self._receipts.append(result.receipt.receipt_id)
                if trace_id:
                    if trace_id not in self._trace_receipts:
                        self._trace_receipts[trace_id] = []
                    self._trace_receipts[trace_id].append(result.receipt.receipt_id)
                all_receipts.append(result.receipt.receipt_id)
                if result.pii.has_pii:
                    any_pii = True
                    all_types.extend(result.pii.types)
                    redacted_fields.append('content')
            governed_messages.append(governed_msg)

        return governed_messages, any_pii, list(set(all_types)), all_receipts, redacted_fields

    def trace(
        self,
        name: str,
        input: Optional[Any] = None,
        output: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> LangfuseGovernanceResult:
        """
        Create a trace with governance.

        Args:
            name: Trace name
            input: Trace input
            output: Trace output
            metadata: Trace metadata
            user_id: User ID
            session_id: Session ID
            **kwargs: Additional arguments

        Returns:
            LangfuseGovernanceResult
        """
        trace_id = kwargs.get('id', str(uuid.uuid4()))
        all_receipts = []
        any_pii = False
        all_types = []
        all_redacted_fields = []

        governed_input = input
        governed_output = output
        governed_metadata = metadata

        # Govern input
        if input is not None and self._govern_inputs:
            governed_input, pii, types, receipts = self._govern_value(input, trace_id)
            all_receipts.extend(receipts)
            if pii:
                any_pii = True
                all_types.extend(types)
                all_redacted_fields.append('input')

        # Govern output
        if output is not None and self._govern_outputs:
            governed_output, pii, types, receipts = self._govern_value(output, trace_id)
            all_receipts.extend(receipts)
            if pii:
                any_pii = True
                all_types.extend(types)
                all_redacted_fields.append('output')

        # Govern metadata
        if metadata and self._govern_metadata:
            governed_metadata, pii, types, receipts, fields = self._govern_dict(metadata, trace_id)
            all_receipts.extend(receipts)
            if pii:
                any_pii = True
                all_types.extend(types)
                all_redacted_fields.extend([f'metadata.{f}' for f in fields])

        # Add governance info to metadata
        if self._attach_receipts:
            governed_metadata = governed_metadata or {}
            governed_metadata['_tork_governance'] = {
                'enabled': True,
                'receipts': all_receipts,
                'pii_detected': any_pii,
            }

        try:
            if self._client:
                trace = self._client.trace(
                    name=name,
                    input=governed_input,
                    output=governed_output,
                    metadata=governed_metadata,
                    user_id=user_id,
                    session_id=session_id,
                    id=trace_id,
                    **kwargs
                )
            else:
                trace = {
                    'id': trace_id,
                    'name': name,
                    'input': governed_input,
                    'output': governed_output,
                    'metadata': governed_metadata,
                }

            return LangfuseGovernanceResult(
                success=True,
                operation="trace",
                governed_data=trace,
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=all_redacted_fields,
                trace_id=trace_id,
            )
        except Exception as e:
            return LangfuseGovernanceResult(
                success=False,
                operation="trace",
                governed_data=str(e),
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=all_redacted_fields,
                trace_id=trace_id,
            )

    def generation(
        self,
        name: str,
        trace_id: Optional[str] = None,
        input: Optional[Any] = None,
        output: Optional[Any] = None,
        model: Optional[str] = None,
        model_parameters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> LangfuseGovernanceResult:
        """
        Log a generation with governance.

        Args:
            name: Generation name
            trace_id: Parent trace ID
            input: Generation input (prompt/messages)
            output: Generation output
            model: Model name
            model_parameters: Model parameters
            metadata: Additional metadata
            **kwargs: Additional arguments

        Returns:
            LangfuseGovernanceResult
        """
        generation_id = kwargs.get('id', str(uuid.uuid4()))
        all_receipts = []
        any_pii = False
        all_types = []
        all_redacted_fields = []

        governed_input = input
        governed_output = output
        governed_metadata = metadata

        # Govern input
        if input is not None and self._govern_inputs:
            if isinstance(input, list):
                # Messages format
                governed_input, pii, types, receipts, fields = self._govern_messages(input, trace_id)
            else:
                governed_input, pii, types, receipts = self._govern_value(input, trace_id)
            all_receipts.extend(receipts)
            if pii:
                any_pii = True
                all_types.extend(types)
                all_redacted_fields.append('input')

        # Govern output
        if output is not None and self._govern_outputs:
            governed_output, pii, types, receipts = self._govern_value(output, trace_id)
            all_receipts.extend(receipts)
            if pii:
                any_pii = True
                all_types.extend(types)
                all_redacted_fields.append('output')

        # Govern metadata
        if metadata and self._govern_metadata:
            governed_metadata, pii, types, receipts, fields = self._govern_dict(metadata, trace_id)
            all_receipts.extend(receipts)
            if pii:
                any_pii = True
                all_types.extend(types)
                all_redacted_fields.extend([f'metadata.{f}' for f in fields])

        try:
            if self._client:
                generation = self._client.generation(
                    name=name,
                    trace_id=trace_id,
                    input=governed_input,
                    output=governed_output,
                    model=model,
                    model_parameters=model_parameters,
                    metadata=governed_metadata,
                    id=generation_id,
                    **kwargs
                )
            else:
                generation = {
                    'id': generation_id,
                    'trace_id': trace_id,
                    'name': name,
                    'input': governed_input,
                    'output': governed_output,
                    'model': model,
                }

            return LangfuseGovernanceResult(
                success=True,
                operation="generation",
                governed_data=generation,
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=all_redacted_fields,
                trace_id=trace_id,
                generation_id=generation_id,
            )
        except Exception as e:
            return LangfuseGovernanceResult(
                success=False,
                operation="generation",
                governed_data=str(e),
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                trace_id=trace_id,
                generation_id=generation_id,
            )

    def score(
        self,
        trace_id: str,
        name: str,
        value: Union[float, str],
        comment: Optional[str] = None,
        **kwargs
    ) -> LangfuseGovernanceResult:
        """
        Create a score with governance.

        Args:
            trace_id: Trace ID to score
            name: Score name
            value: Score value
            comment: Score comment
            **kwargs: Additional arguments

        Returns:
            LangfuseGovernanceResult
        """
        all_receipts = []
        any_pii = False
        all_types = []
        all_redacted_fields = []

        governed_value = value
        governed_comment = comment

        # Govern value if string
        if isinstance(value, str):
            result = self._tork.govern(value)
            governed_value = result.output
            all_receipts.append(result.receipt.receipt_id)
            if result.pii.has_pii:
                any_pii = True
                all_types.extend(result.pii.types)
                all_redacted_fields.append('value')

        # Govern comment
        if comment:
            result = self._tork.govern(comment)
            governed_comment = result.output
            all_receipts.append(result.receipt.receipt_id)
            if result.pii.has_pii:
                any_pii = True
                all_types.extend(result.pii.types)
                all_redacted_fields.append('comment')

        try:
            if self._client:
                score = self._client.score(
                    trace_id=trace_id,
                    name=name,
                    value=governed_value,
                    comment=governed_comment,
                    **kwargs
                )
            else:
                score = {
                    'trace_id': trace_id,
                    'name': name,
                    'value': governed_value,
                    'comment': governed_comment,
                }

            return LangfuseGovernanceResult(
                success=True,
                operation="score",
                governed_data=score,
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=all_redacted_fields,
                trace_id=trace_id,
            )
        except Exception as e:
            return LangfuseGovernanceResult(
                success=False,
                operation="score",
                governed_data=str(e),
                receipts=all_receipts,
                trace_id=trace_id,
            )

    def flush(self) -> LangfuseGovernanceResult:
        """Flush pending data to Langfuse."""
        try:
            if self._client:
                self._client.flush()
            return LangfuseGovernanceResult(
                success=True,
                operation="flush",
                governed_data={"receipts_total": len(self._receipts)},
                receipts=self._receipts,
            )
        except Exception as e:
            return LangfuseGovernanceResult(
                success=False,
                operation="flush",
                governed_data=str(e),
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        return self._tork.get_stats()

    def reset_stats(self):
        """Reset governance statistics."""
        self._tork.reset_stats()


class TorkLangfuseCallback:
    """
    LangChain callback handler with Tork governance for Langfuse.

    Automatically governs all data logged to Langfuse from LangChain.
    """

    def __init__(
        self,
        client: Any = None,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        govern_inputs: bool = True,
        govern_outputs: bool = True,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """
        Initialize governed Langfuse callback.

        Args:
            client: Langfuse client
            tork: Tork governance instance
            config: Tork configuration
            govern_inputs: Whether to govern inputs
            govern_outputs: Whether to govern outputs
            session_id: Session ID for traces
            user_id: User ID for traces
        """
        self._langfuse = TorkLangfuseClient(client=client, tork=tork, config=config)
        self._govern_inputs = govern_inputs
        self._govern_outputs = govern_outputs
        self._session_id = session_id
        self._user_id = user_id
        self._traces: Dict[str, str] = {}  # run_id -> trace_id

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipts."""
        return self._langfuse.receipts

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: str,
        **kwargs
    ) -> None:
        """Govern and log LLM start."""
        trace_result = self._langfuse.trace(
            name=serialized.get('name', 'llm'),
            input=prompts if len(prompts) > 1 else prompts[0] if prompts else None,
            user_id=self._user_id,
            session_id=self._session_id,
        )
        if trace_result.trace_id:
            self._traces[run_id] = trace_result.trace_id

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: str,
        **kwargs
    ) -> None:
        """Govern and log LLM end."""
        trace_id = self._traces.get(run_id)
        if trace_id and hasattr(response, 'generations'):
            outputs = []
            for generation_list in response.generations:
                for generation in generation_list:
                    if hasattr(generation, 'text'):
                        outputs.append(generation.text)

            self._langfuse.generation(
                name='llm_completion',
                trace_id=trace_id,
                output=outputs[0] if len(outputs) == 1 else outputs,
            )

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: str,
        **kwargs
    ) -> None:
        """Govern and log chain start."""
        trace_result = self._langfuse.trace(
            name=serialized.get('name', 'chain'),
            input=inputs,
            user_id=self._user_id,
            session_id=self._session_id,
        )
        if trace_result.trace_id:
            self._traces[run_id] = trace_result.trace_id

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: str,
        **kwargs
    ) -> None:
        """Govern and log chain end."""
        trace_id = self._traces.get(run_id)
        if trace_id:
            # Update trace with output (would need span support in real impl)
            pass


def govern_trace(
    client: Any,
    name: str,
    tork: Optional[Tork] = None,
    input: Optional[Any] = None,
    output: Optional[Any] = None,
    **kwargs
) -> LangfuseGovernanceResult:
    """
    Govern and create a trace in Langfuse.

    Args:
        client: Langfuse client
        name: Trace name
        tork: Tork instance
        input: Trace input
        output: Trace output
        **kwargs: Additional arguments

    Returns:
        LangfuseGovernanceResult
    """
    governed_client = TorkLangfuseClient(client=client, tork=tork)
    return governed_client.trace(name=name, input=input, output=output, **kwargs)


def govern_generation(
    client: Any,
    name: str,
    tork: Optional[Tork] = None,
    trace_id: Optional[str] = None,
    input: Optional[Any] = None,
    output: Optional[Any] = None,
    **kwargs
) -> LangfuseGovernanceResult:
    """
    Govern and log a generation in Langfuse.

    Args:
        client: Langfuse client
        name: Generation name
        tork: Tork instance
        trace_id: Parent trace ID
        input: Generation input
        output: Generation output
        **kwargs: Additional arguments

    Returns:
        LangfuseGovernanceResult
    """
    governed_client = TorkLangfuseClient(client=client, tork=tork)
    return governed_client.generation(
        name=name,
        trace_id=trace_id,
        input=input,
        output=output,
        **kwargs
    )


def govern_score(
    client: Any,
    trace_id: str,
    name: str,
    value: Union[float, str],
    tork: Optional[Tork] = None,
    comment: Optional[str] = None,
    **kwargs
) -> LangfuseGovernanceResult:
    """
    Govern and create a score in Langfuse.

    Args:
        client: Langfuse client
        trace_id: Trace ID
        name: Score name
        value: Score value
        tork: Tork instance
        comment: Score comment
        **kwargs: Additional arguments

    Returns:
        LangfuseGovernanceResult
    """
    governed_client = TorkLangfuseClient(client=client, tork=tork)
    return governed_client.score(
        trace_id=trace_id,
        name=name,
        value=value,
        comment=comment,
        **kwargs
    )


def langfuse_governed(
    tork: Optional[Tork] = None,
    govern_inputs: bool = True,
    govern_outputs: bool = True,
):
    """
    Decorator to add Langfuse governance to a function.

    Args:
        tork: Tork instance
        govern_inputs: Whether to govern inputs
        govern_outputs: Whether to govern outputs

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            client = TorkLangfuseClient(
                tork=tork,
                govern_inputs=govern_inputs,
                govern_outputs=govern_outputs,
            )
            kwargs['_tork_langfuse'] = client
            return func(*args, **kwargs)
        return wrapper
    return decorator
