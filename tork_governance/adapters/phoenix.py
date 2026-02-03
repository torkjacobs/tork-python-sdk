"""
Tork Governance adapter for Arize Phoenix (open-source LLM observability).

Provides governance for Phoenix tracing and observability with automatic
PII detection and redaction.

Usage:
    from tork_governance.adapters.phoenix import TorkPhoenixClient, govern_log_traces

    # Wrap Phoenix client
    client = TorkPhoenixClient(phoenix_client)

    # Or use convenience functions
    result = govern_log_traces(traces, tork=tork)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from ..core import Tork, TorkConfig, GovernanceResult, Receipt


@dataclass
class PhoenixGovernanceResult:
    """Result of Phoenix governance operation."""

    governed_data: Any
    original_data: Any
    pii_detected: bool
    pii_count: int
    receipts: List[Receipt] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TorkPhoenixClient:
    """
    Governed wrapper for Arize Phoenix client.

    Automatically applies PII detection and redaction to all trace
    and span data before logging to Phoenix.

    Example:
        from phoenix.trace import TraceClient
        from tork_governance.adapters.phoenix import TorkPhoenixClient

        phoenix_client = TraceClient()
        governed_client = TorkPhoenixClient(phoenix_client)

        # All logging now governed
        governed_client.log_traces(traces)
    """

    def __init__(
        self,
        client: Any,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        redact_inputs: bool = True,
        redact_outputs: bool = True,
        redact_metadata: bool = True,
        redact_attributes: bool = True,
    ):
        """
        Initialize governed Phoenix client.

        Args:
            client: Phoenix TraceClient or similar
            tork: Tork instance for governance
            config: TorkConfig if tork not provided
            redact_inputs: Whether to redact PII in inputs
            redact_outputs: Whether to redact PII in outputs
            redact_metadata: Whether to redact PII in metadata
            redact_attributes: Whether to redact PII in span attributes
        """
        self._client = client
        self._tork = tork or Tork(config=config or TorkConfig())
        self._redact_inputs = redact_inputs
        self._redact_outputs = redact_outputs
        self._redact_metadata = redact_metadata
        self._redact_attributes = redact_attributes
        self._receipts: List[Receipt] = []

    @property
    def receipts(self) -> List[Receipt]:
        """Get all governance receipts."""
        return self._receipts.copy()

    @property
    def client(self) -> Any:
        """Access underlying Phoenix client."""
        return self._client

    def _govern_text(self, text: Any) -> tuple[Any, GovernanceResult]:
        """Apply governance to text content."""
        if not isinstance(text, str):
            return text, None
        result = self._tork.govern(text)
        if result.receipt:
            self._receipts.append(result.receipt)
        return result.output, result

    def _govern_dict(self, data: Dict[str, Any], keys_to_govern: List[str] = None) -> Dict[str, Any]:
        """Apply governance to dictionary values."""
        if not isinstance(data, dict):
            return data

        governed = {}
        for key, value in data.items():
            if keys_to_govern is None or key in keys_to_govern:
                if isinstance(value, str):
                    governed[key], _ = self._govern_text(value)
                elif isinstance(value, dict):
                    governed[key] = self._govern_dict(value, keys_to_govern)
                elif isinstance(value, list):
                    governed[key] = self._govern_list(value)
                else:
                    governed[key] = value
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

    def _govern_trace(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        """Apply governance to a single trace."""
        governed = trace.copy()

        # Govern input
        if self._redact_inputs and "input" in governed:
            if isinstance(governed["input"], str):
                governed["input"], _ = self._govern_text(governed["input"])
            elif isinstance(governed["input"], dict):
                governed["input"] = self._govern_dict(governed["input"])

        # Govern output
        if self._redact_outputs and "output" in governed:
            if isinstance(governed["output"], str):
                governed["output"], _ = self._govern_text(governed["output"])
            elif isinstance(governed["output"], dict):
                governed["output"] = self._govern_dict(governed["output"])

        # Govern metadata
        if self._redact_metadata and "metadata" in governed:
            governed["metadata"] = self._govern_dict(governed["metadata"])

        # Govern attributes
        if self._redact_attributes and "attributes" in governed:
            governed["attributes"] = self._govern_dict(governed["attributes"])

        # Govern spans within trace
        if "spans" in governed:
            governed["spans"] = [self._govern_span(s) for s in governed["spans"]]

        return governed

    def _govern_span(self, span: Dict[str, Any]) -> Dict[str, Any]:
        """Apply governance to a single span."""
        governed = span.copy()

        # Govern span input
        if self._redact_inputs and "input" in governed:
            if isinstance(governed["input"], str):
                governed["input"], _ = self._govern_text(governed["input"])
            elif isinstance(governed["input"], dict):
                governed["input"] = self._govern_dict(governed["input"])

        # Govern span output
        if self._redact_outputs and "output" in governed:
            if isinstance(governed["output"], str):
                governed["output"], _ = self._govern_text(governed["output"])
            elif isinstance(governed["output"], dict):
                governed["output"] = self._govern_dict(governed["output"])

        # Govern span attributes
        if self._redact_attributes and "attributes" in governed:
            governed["attributes"] = self._govern_dict(governed["attributes"])

        # Govern events
        if "events" in governed:
            governed["events"] = self._govern_list(governed["events"])

        return governed

    def log_traces(
        self,
        traces: Union[Dict[str, Any], List[Dict[str, Any]]],
        **kwargs,
    ) -> PhoenixGovernanceResult:
        """
        Log traces with governance.

        Args:
            traces: Trace data (single trace or list)
            **kwargs: Additional arguments for Phoenix client

        Returns:
            PhoenixGovernanceResult with governed data
        """
        original = traces
        receipts_before = len(self._receipts)

        if isinstance(traces, dict):
            governed = self._govern_trace(traces)
        else:
            governed = [self._govern_trace(t) for t in traces]

        # Log to Phoenix
        if hasattr(self._client, "log_traces"):
            self._client.log_traces(governed, **kwargs)
        elif hasattr(self._client, "log"):
            self._client.log(governed, **kwargs)

        new_receipts = self._receipts[receipts_before:]

        return PhoenixGovernanceResult(
            governed_data=governed,
            original_data=original,
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            metadata={"operation": "log_traces"},
        )

    def log_spans(
        self,
        spans: Union[Dict[str, Any], List[Dict[str, Any]]],
        **kwargs,
    ) -> PhoenixGovernanceResult:
        """
        Log spans with governance.

        Args:
            spans: Span data (single span or list)
            **kwargs: Additional arguments for Phoenix client

        Returns:
            PhoenixGovernanceResult with governed data
        """
        original = spans
        receipts_before = len(self._receipts)

        if isinstance(spans, dict):
            governed = self._govern_span(spans)
        else:
            governed = [self._govern_span(s) for s in spans]

        # Log to Phoenix
        if hasattr(self._client, "log_spans"):
            self._client.log_spans(governed, **kwargs)
        elif hasattr(self._client, "log"):
            self._client.log(governed, **kwargs)

        new_receipts = self._receipts[receipts_before:]

        return PhoenixGovernanceResult(
            governed_data=governed,
            original_data=original,
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            metadata={"operation": "log_spans"},
        )

    def log_evaluations(
        self,
        evaluations: Union[Dict[str, Any], List[Dict[str, Any]]],
        **kwargs,
    ) -> PhoenixGovernanceResult:
        """
        Log evaluations with governance.

        Args:
            evaluations: Evaluation data
            **kwargs: Additional arguments for Phoenix client

        Returns:
            PhoenixGovernanceResult with governed data
        """
        original = evaluations
        receipts_before = len(self._receipts)

        if isinstance(evaluations, dict):
            governed = self._govern_dict(evaluations)
        else:
            governed = [self._govern_dict(e) for e in evaluations]

        # Log to Phoenix
        if hasattr(self._client, "log_evaluations"):
            self._client.log_evaluations(governed, **kwargs)

        new_receipts = self._receipts[receipts_before:]

        return PhoenixGovernanceResult(
            governed_data=governed,
            original_data=original,
            pii_detected=len(new_receipts) > 0,
            pii_count=sum(r.pii_count for r in new_receipts if hasattr(r, "pii_count")),
            receipts=new_receipts,
            metadata={"operation": "log_evaluations"},
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy other methods to underlying client."""
        return getattr(self._client, name)


def govern_log_traces(
    traces: Union[Dict[str, Any], List[Dict[str, Any]]],
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> PhoenixGovernanceResult:
    """
    Apply governance to trace data before logging.

    Args:
        traces: Trace data to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional governance options

    Returns:
        PhoenixGovernanceResult with governed traces
    """
    tork_instance = tork or Tork(config=config or TorkConfig())
    receipts = []

    def govern_text(text: str) -> str:
        result = tork_instance.govern(text)
        if result.receipt:
            receipts.append(result.receipt)
        return result.output

    def govern_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        governed = {}
        for key, value in data.items():
            if isinstance(value, str):
                governed[key] = govern_text(value)
            elif isinstance(value, dict):
                governed[key] = govern_dict(value)
            elif isinstance(value, list):
                governed[key] = govern_list(value)
            else:
                governed[key] = value
        return governed

    def govern_list(data: List[Any]) -> List[Any]:
        governed = []
        for item in data:
            if isinstance(item, str):
                governed.append(govern_text(item))
            elif isinstance(item, dict):
                governed.append(govern_dict(item))
            elif isinstance(item, list):
                governed.append(govern_list(item))
            else:
                governed.append(item)
        return governed

    if isinstance(traces, dict):
        governed = govern_dict(traces)
    else:
        governed = [govern_dict(t) for t in traces]

    return PhoenixGovernanceResult(
        governed_data=governed,
        original_data=traces,
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_log_traces"},
    )


def govern_log_spans(
    spans: Union[Dict[str, Any], List[Dict[str, Any]]],
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
    **kwargs,
) -> PhoenixGovernanceResult:
    """
    Apply governance to span data before logging.

    Args:
        spans: Span data to govern
        tork: Tork instance
        config: TorkConfig if tork not provided
        **kwargs: Additional governance options

    Returns:
        PhoenixGovernanceResult with governed spans
    """
    tork_instance = tork or Tork(config=config or TorkConfig())
    receipts = []

    def govern_text(text: str) -> str:
        result = tork_instance.govern(text)
        if result.receipt:
            receipts.append(result.receipt)
        return result.output

    def govern_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        governed = {}
        for key, value in data.items():
            if isinstance(value, str):
                governed[key] = govern_text(value)
            elif isinstance(value, dict):
                governed[key] = govern_dict(value)
            elif isinstance(value, list):
                governed[key] = govern_list(value)
            else:
                governed[key] = value
        return governed

    def govern_list(data: List[Any]) -> List[Any]:
        governed = []
        for item in data:
            if isinstance(item, str):
                governed.append(govern_text(item))
            elif isinstance(item, dict):
                governed.append(govern_dict(item))
            elif isinstance(item, list):
                governed.append(govern_list(item))
            else:
                governed.append(item)
        return governed

    if isinstance(spans, dict):
        governed = govern_dict(spans)
    else:
        governed = [govern_dict(s) for s in spans]

    return PhoenixGovernanceResult(
        governed_data=governed,
        original_data=spans,
        pii_detected=len(receipts) > 0,
        pii_count=sum(r.pii_count for r in receipts if hasattr(r, "pii_count")),
        receipts=receipts,
        metadata={"operation": "govern_log_spans"},
    )


def phoenix_governed(
    tork: Optional[Tork] = None,
    config: Optional[TorkConfig] = None,
):
    """
    Decorator to add governance to Phoenix operations.

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
                else:
                    governed_kwargs[key] = value

            return func(*governed_args, **governed_kwargs)

        return wrapper

    return decorator


__all__ = [
    "TorkPhoenixClient",
    "PhoenixGovernanceResult",
    "govern_log_traces",
    "govern_log_spans",
    "phoenix_governed",
]
