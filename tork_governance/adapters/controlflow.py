"""
Prefect ControlFlow Integration for Tork Governance

Provides middleware and wrappers for Prefect's ControlFlow task execution
with governance checks on task inputs and outputs.
"""

from typing import Any, Dict, List, Optional
from ..core import Tork, GovernanceResult, GovernanceAction


class ControlFlowAdapter:
    """
    Middleware for Prefect's ControlFlow that applies Tork governance
    to AI task execution and agent interactions.

    Example:
        >>> from tork_governance.adapters.controlflow import ControlFlowAdapter
        >>> adapter = ControlFlowAdapter()
        >>> governed_text = adapter.govern("user input text")
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "controlflow-agent"
    ):
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.agent_id = agent_id
        self.receipts: List[Dict] = []

    def wrap_task(self, task: Any) -> "GovernedControlFlowTask":
        """Wrap a ControlFlow task with governance controls."""
        return GovernedControlFlowTask(task, self)

    def wrap_flow(self, flow: Any) -> "GovernedControlFlowFlow":
        """Wrap an entire ControlFlow flow with governance controls."""
        return GovernedControlFlowFlow(flow, self)

    def process_input(self, content: str) -> GovernanceResult:
        """Process and validate input content."""
        result = self.tork.govern(content)
        self.receipts.append({
            'type': 'input',
            'agent_id': self.agent_id,
            'receipt_id': result.receipt.receipt_id,
            'action': result.action.value
        })
        return result

    def process_output(self, content: str) -> GovernanceResult:
        """Process and validate output content."""
        result = self.tork.govern(content)
        self.receipts.append({
            'type': 'output',
            'agent_id': self.agent_id,
            'receipt_id': result.receipt.receipt_id,
            'action': result.action.value
        })
        return result

    def check_tool_call(self, tool_name: str, tool_args: Dict) -> GovernanceResult:
        """Validate a tool call before execution."""
        content = f"{tool_name}: {tool_args}"
        result = self.tork.govern(content)
        self.receipts.append({
            'type': 'tool_call',
            'tool_name': tool_name,
            'receipt_id': result.receipt.receipt_id,
            'action': result.action.value
        })
        return result

    def govern_input(self, text: str) -> str:
        """Govern input text - standalone method."""
        return self.process_input(text).output

    def govern_output(self, text: str) -> str:
        """Govern output text - standalone method."""
        return self.process_output(text).output

    def govern(self, text: str) -> str:
        """Govern text - alias for govern_input."""
        return self.govern_input(text)


class GovernedControlFlowTask:
    """
    Wrapper for a ControlFlow Task that applies governance to execution.

    Example:
        >>> from tork_governance.adapters.controlflow import ControlFlowAdapter
        >>> adapter = ControlFlowAdapter()
        >>> governed = adapter.wrap_task(cf_task)
        >>> result = governed.run()
    """

    def __init__(self, task: Any = None, middleware: ControlFlowAdapter = None, api_key: Optional[str] = None):
        self._task = task
        self._middleware = middleware or ControlFlowAdapter(api_key=api_key)

    def govern_input(self, text: str) -> str:
        """Govern input text - standalone method."""
        return self._middleware.govern_input(text)

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped task."""
        return getattr(self._task, name)

    def run(self, **kwargs) -> str:
        """Run the task with governance applied."""
        # Govern task objective if available
        objective = getattr(self._task, 'objective', None) or getattr(self._task, 'description', None)
        if objective and isinstance(objective, str):
            input_result = self._middleware.process_input(objective)
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Task blocked by governance: {input_result.receipt.receipt_id}")

        # Execute the original task
        try:
            if hasattr(self._task, 'run'):
                output = self._task.run(**kwargs)
            else:
                output = str(objective or "Task execution simulated")
        except Exception as e:
            raise e

        # Govern output
        output_result = self._middleware.process_output(str(output))
        return output_result.output


class GovernedControlFlowFlow:
    """
    Wrapper for a ControlFlow Flow that applies governance to the entire workflow.

    Example:
        >>> from tork_governance.adapters.controlflow import ControlFlowAdapter
        >>> adapter = ControlFlowAdapter()
        >>> governed = adapter.wrap_flow(cf_flow)
        >>> result = governed.run()
    """

    def __init__(self, flow: Any = None, middleware: ControlFlowAdapter = None, api_key: Optional[str] = None):
        self._flow = flow
        self._middleware = middleware or ControlFlowAdapter(api_key=api_key)

    def govern_input(self, text: str) -> str:
        """Govern input text - standalone method."""
        return self._middleware.govern_input(text)

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped flow."""
        return getattr(self._flow, name)

    def run(self, inputs: Optional[Dict] = None, **kwargs) -> str:
        """Run the flow with governance applied to inputs and final output."""
        if inputs:
            for key, value in inputs.items():
                if isinstance(value, str):
                    result = self._middleware.process_input(value)
                    if result.action == GovernanceAction.DENY:
                        raise ValueError(f"Input blocked: {result.receipt.receipt_id}")
                    inputs[key] = result.output

        try:
            if hasattr(self._flow, 'run'):
                output = self._flow.run(**(inputs or {}), **kwargs)
            else:
                output = "Flow execution simulated"
        except Exception as e:
            raise e

        output_str = str(output)
        output_result = self._middleware.process_output(output_str)
        return output_result.output
