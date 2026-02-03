"""
Tork Governance adapter for Weights & Biases (W&B) ML experiment tracking.

Provides governance for W&B logging with automatic PII detection
and redaction in experiment data, configs, and artifacts.
"""

from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
import functools

from ..core import Tork, TorkConfig, GovernanceResult, GovernanceAction


@dataclass
class WandbGovernanceResult:
    """Result of a governed W&B operation."""
    success: bool
    operation: str
    governed_data: Any
    receipts: List[str] = field(default_factory=list)
    pii_detected: bool = False
    pii_types: List[str] = field(default_factory=list)
    redacted_fields: List[str] = field(default_factory=list)
    run_id: Optional[str] = None


class TorkWandbRun:
    """Governed W&B run wrapper."""

    def __init__(
        self,
        run: Any = None,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        govern_logs: bool = True,
        govern_config: bool = True,
        govern_artifacts: bool = True,
        govern_tables: bool = True,
    ):
        """
        Initialize governed W&B run.

        Args:
            run: W&B run object
            tork: Tork governance instance
            config: Tork configuration
            govern_logs: Whether to govern log data
            govern_config: Whether to govern config data
            govern_artifacts: Whether to govern artifacts
            govern_tables: Whether to govern table data
        """
        self._run = run
        self._tork = tork or Tork(config)
        self._govern_logs = govern_logs
        self._govern_config = govern_config
        self._govern_artifacts = govern_artifacts
        self._govern_tables = govern_tables
        self._receipts: List[str] = []

    @property
    def run(self) -> Any:
        """Get the underlying W&B run."""
        return self._run

    @run.setter
    def run(self, value: Any):
        """Set the W&B run."""
        self._run = value

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
            return governed_list, any_pii, list(set(all_types)), all_receipts
        return value, False, [], []

    def _govern_dict(self, data: Dict[str, Any]) -> tuple:
        """Govern all values in a dictionary."""
        governed = {}
        any_pii = False
        all_types = []
        all_receipts = []
        redacted_fields = []

        for key, value in data.items():
            gov_value, pii, types, receipts = self._govern_value(value)
            governed[key] = gov_value
            if pii:
                any_pii = True
                all_types.extend(types)
                redacted_fields.append(key)
            all_receipts.extend(receipts)

        return governed, any_pii, list(set(all_types)), all_receipts, redacted_fields

    def log(
        self,
        data: Dict[str, Any],
        step: Optional[int] = None,
        commit: bool = True,
        **kwargs
    ) -> WandbGovernanceResult:
        """
        Log metrics/data with governance.

        Args:
            data: Data to log
            step: Step number
            commit: Whether to commit the log
            **kwargs: Additional logging arguments

        Returns:
            WandbGovernanceResult
        """
        if not self._govern_logs:
            if self._run:
                self._run.log(data, step=step, commit=commit, **kwargs)
            return WandbGovernanceResult(
                success=True,
                operation="log",
                governed_data=data,
            )

        governed_data, any_pii, all_types, all_receipts, redacted_fields = self._govern_dict(data)

        try:
            if self._run:
                self._run.log(governed_data, step=step, commit=commit, **kwargs)

            return WandbGovernanceResult(
                success=True,
                operation="log",
                governed_data=governed_data,
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=all_types,
                redacted_fields=redacted_fields,
                run_id=self._run.id if self._run and hasattr(self._run, 'id') else None,
            )
        except Exception as e:
            return WandbGovernanceResult(
                success=False,
                operation="log",
                governed_data=str(e),
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=all_types,
                redacted_fields=redacted_fields,
            )

    def config_update(
        self,
        config_dict: Dict[str, Any],
        **kwargs
    ) -> WandbGovernanceResult:
        """
        Update run config with governance.

        Args:
            config_dict: Config to update
            **kwargs: Additional arguments

        Returns:
            WandbGovernanceResult
        """
        if not self._govern_config:
            if self._run:
                self._run.config.update(config_dict, **kwargs)
            return WandbGovernanceResult(
                success=True,
                operation="config_update",
                governed_data=config_dict,
            )

        governed_config, any_pii, all_types, all_receipts, redacted_fields = self._govern_dict(config_dict)

        try:
            if self._run:
                self._run.config.update(governed_config, **kwargs)

            return WandbGovernanceResult(
                success=True,
                operation="config_update",
                governed_data=governed_config,
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=all_types,
                redacted_fields=redacted_fields,
            )
        except Exception as e:
            return WandbGovernanceResult(
                success=False,
                operation="config_update",
                governed_data=str(e),
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=all_types,
            )

    def log_table(
        self,
        table_name: str,
        data: List[Dict[str, Any]],
        columns: Optional[List[str]] = None,
        **kwargs
    ) -> WandbGovernanceResult:
        """
        Log a table with governance.

        Args:
            table_name: Name for the table
            data: Table data as list of dicts
            columns: Column names
            **kwargs: Additional arguments

        Returns:
            WandbGovernanceResult
        """
        if not self._govern_tables:
            if self._run:
                try:
                    import wandb
                    table = wandb.Table(columns=columns or list(data[0].keys()) if data else [], data=data)
                    self._run.log({table_name: table}, **kwargs)
                except ImportError:
                    pass
            return WandbGovernanceResult(
                success=True,
                operation="log_table",
                governed_data=data,
            )

        governed_rows = []
        all_receipts = []
        any_pii = False
        all_types = []
        all_redacted_fields = []

        for row in data:
            governed_row, pii, types, receipts, fields = self._govern_dict(row)
            governed_rows.append(governed_row)
            all_receipts.extend(receipts)
            if pii:
                any_pii = True
                all_types.extend(types)
                all_redacted_fields.extend(fields)

        try:
            if self._run:
                try:
                    import wandb
                    table = wandb.Table(
                        columns=columns or list(governed_rows[0].keys()) if governed_rows else [],
                        data=[[row.get(c) for c in (columns or list(governed_rows[0].keys()))] for row in governed_rows] if governed_rows else []
                    )
                    self._run.log({table_name: table}, **kwargs)
                except ImportError:
                    pass

            return WandbGovernanceResult(
                success=True,
                operation="log_table",
                governed_data=governed_rows,
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
                redacted_fields=list(set(all_redacted_fields)),
            )
        except Exception as e:
            return WandbGovernanceResult(
                success=False,
                operation="log_table",
                governed_data=str(e),
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=list(set(all_types)),
            )

    def summary_update(
        self,
        summary_dict: Dict[str, Any],
        **kwargs
    ) -> WandbGovernanceResult:
        """
        Update run summary with governance.

        Args:
            summary_dict: Summary data to update
            **kwargs: Additional arguments

        Returns:
            WandbGovernanceResult
        """
        governed_summary, any_pii, all_types, all_receipts, redacted_fields = self._govern_dict(summary_dict)

        try:
            if self._run:
                self._run.summary.update(governed_summary, **kwargs)

            return WandbGovernanceResult(
                success=True,
                operation="summary_update",
                governed_data=governed_summary,
                receipts=all_receipts,
                pii_detected=any_pii,
                pii_types=all_types,
                redacted_fields=redacted_fields,
            )
        except Exception as e:
            return WandbGovernanceResult(
                success=False,
                operation="summary_update",
                governed_data=str(e),
                receipts=all_receipts,
            )

    def finish(self, **kwargs) -> WandbGovernanceResult:
        """Finish the run."""
        try:
            if self._run:
                self._run.finish(**kwargs)
            return WandbGovernanceResult(
                success=True,
                operation="finish",
                governed_data={"receipts_total": len(self._receipts)},
                receipts=self._receipts,
            )
        except Exception as e:
            return WandbGovernanceResult(
                success=False,
                operation="finish",
                governed_data=str(e),
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        return self._tork.get_stats()


class TorkWandbCallback:
    """
    LangChain callback handler with Tork governance for W&B.

    Automatically governs all data logged to W&B from LangChain.
    """

    def __init__(
        self,
        run: Any = None,
        tork: Optional[Tork] = None,
        config: Optional[TorkConfig] = None,
        govern_inputs: bool = True,
        govern_outputs: bool = True,
    ):
        """
        Initialize governed W&B callback.

        Args:
            run: W&B run object
            tork: Tork governance instance
            config: Tork configuration
            govern_inputs: Whether to govern inputs
            govern_outputs: Whether to govern outputs
        """
        self._tork_run = TorkWandbRun(run=run, tork=tork, config=config)
        self._govern_inputs = govern_inputs
        self._govern_outputs = govern_outputs
        self._receipts: List[str] = []

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipts."""
        return self._receipts + self._tork_run.receipts

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs
    ) -> None:
        """Govern and log LLM start."""
        if self._govern_inputs:
            governed_prompts = []
            for prompt in prompts:
                result = self._tork_run._tork.govern(prompt)
                governed_prompts.append(result.output)
                self._receipts.append(result.receipt.receipt_id)

            self._tork_run.log({
                "llm_start": {
                    "prompts": governed_prompts,
                    "model": serialized.get("name", "unknown"),
                }
            })

    def on_llm_end(
        self,
        response: Any,
        **kwargs
    ) -> None:
        """Govern and log LLM end."""
        if self._govern_outputs and hasattr(response, 'generations'):
            governed_outputs = []
            for generation_list in response.generations:
                for generation in generation_list:
                    if hasattr(generation, 'text'):
                        result = self._tork_run._tork.govern(generation.text)
                        governed_outputs.append(result.output)
                        self._receipts.append(result.receipt.receipt_id)

            self._tork_run.log({
                "llm_end": {
                    "outputs": governed_outputs,
                }
            })

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs
    ) -> None:
        """Govern and log chain start."""
        if self._govern_inputs:
            result = self._tork_run.log({
                "chain_start": {
                    "name": serialized.get("name", "unknown"),
                    "inputs": inputs,
                }
            })
            self._receipts.extend(result.receipts)

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        **kwargs
    ) -> None:
        """Govern and log chain end."""
        if self._govern_outputs:
            result = self._tork_run.log({
                "chain_end": {
                    "outputs": outputs,
                }
            })
            self._receipts.extend(result.receipts)


def govern_log(
    run: Any,
    data: Dict[str, Any],
    tork: Optional[Tork] = None,
    step: Optional[int] = None,
    **kwargs
) -> WandbGovernanceResult:
    """
    Govern and log data to W&B.

    Args:
        run: W&B run
        data: Data to log
        tork: Tork instance
        step: Step number
        **kwargs: Additional arguments

    Returns:
        WandbGovernanceResult
    """
    governed_run = TorkWandbRun(run=run, tork=tork)
    return governed_run.log(data, step=step, **kwargs)


def govern_table(
    run: Any,
    table_name: str,
    data: List[Dict[str, Any]],
    tork: Optional[Tork] = None,
    **kwargs
) -> WandbGovernanceResult:
    """
    Govern and log a table to W&B.

    Args:
        run: W&B run
        table_name: Table name
        data: Table data
        tork: Tork instance
        **kwargs: Additional arguments

    Returns:
        WandbGovernanceResult
    """
    governed_run = TorkWandbRun(run=run, tork=tork)
    return governed_run.log_table(table_name, data, **kwargs)


def wandb_governed(
    tork: Optional[Tork] = None,
    govern_logs: bool = True,
    govern_config: bool = True,
):
    """
    Decorator to add W&B governance to a function.

    Args:
        tork: Tork instance
        govern_logs: Whether to govern logs
        govern_config: Whether to govern config

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create governed run wrapper
            if 'run' in kwargs:
                kwargs['run'] = TorkWandbRun(
                    run=kwargs['run'],
                    tork=tork,
                    govern_logs=govern_logs,
                    govern_config=govern_config,
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator
