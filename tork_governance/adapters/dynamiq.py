"""
Dynamiq Orchestration Integration for Tork Governance

Provides middleware and wrappers for the Dynamiq workflow orchestration
platform with governance checks on workflow nodes and connections.
"""

from typing import Any, Dict, List, Optional
from ..core import Tork, GovernanceResult, GovernanceAction


class DynamiqAdapter:
    """
    Middleware for Dynamiq that applies Tork governance to workflow nodes
    and orchestration pipelines.

    Example:
        >>> from tork_governance.adapters.dynamiq import DynamiqAdapter
        >>> adapter = DynamiqAdapter()
        >>> governed_text = adapter.govern("user input text")
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "dynamiq-agent"
    ):
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.agent_id = agent_id
        self.receipts: List[Dict] = []

    def wrap_node(self, node: Any) -> "GovernedDynamiqNode":
        """Wrap a Dynamiq workflow node with governance controls."""
        return GovernedDynamiqNode(node, self)

    def wrap_workflow(self, workflow: Any) -> "GovernedDynamiqWorkflow":
        """Wrap an entire Dynamiq workflow with governance controls."""
        return GovernedDynamiqWorkflow(workflow, self)

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


class GovernedDynamiqNode:
    """
    Wrapper for a Dynamiq workflow node that applies governance to execution.

    Example:
        >>> from tork_governance.adapters.dynamiq import DynamiqAdapter
        >>> adapter = DynamiqAdapter()
        >>> governed = adapter.wrap_node(my_node)
        >>> result = governed.execute({"input": "data"})
    """

    def __init__(self, node: Any = None, middleware: DynamiqAdapter = None, api_key: Optional[str] = None):
        self._node = node
        self._middleware = middleware or DynamiqAdapter(api_key=api_key)

    def govern_input(self, text: str) -> str:
        """Govern input text - standalone method."""
        return self._middleware.govern_input(text)

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped node."""
        return getattr(self._node, name)

    def execute(self, inputs: Optional[Dict] = None, **kwargs) -> Any:
        """Execute the node with governance applied to inputs and output."""
        if inputs:
            for key, value in list(inputs.items()):
                if isinstance(value, str):
                    result = self._middleware.process_input(value)
                    if result.action == GovernanceAction.DENY:
                        raise ValueError(f"Node input blocked by governance: {result.receipt.receipt_id}")
                    inputs[key] = result.output

        try:
            if hasattr(self._node, 'execute'):
                output = self._node.execute(inputs, **kwargs)
            elif hasattr(self._node, 'run'):
                output = self._node.run(inputs, **kwargs)
            else:
                output = str(inputs or "Node execution simulated")
        except Exception as e:
            raise e

        if isinstance(output, str):
            output_result = self._middleware.process_output(output)
            return output_result.output
        elif isinstance(output, dict):
            for key, value in output.items():
                if isinstance(value, str):
                    out_result = self._middleware.process_output(value)
                    output[key] = out_result.output
            return output
        return output


class GovernedDynamiqWorkflow:
    """
    Wrapper for a Dynamiq Workflow that applies governance to the entire pipeline.

    Example:
        >>> from tork_governance.adapters.dynamiq import DynamiqAdapter
        >>> adapter = DynamiqAdapter()
        >>> governed = adapter.wrap_workflow(my_workflow)
        >>> result = governed.run({"query": "hello"})
    """

    def __init__(self, workflow: Any = None, middleware: DynamiqAdapter = None, api_key: Optional[str] = None):
        self._workflow = workflow
        self._middleware = middleware or DynamiqAdapter(api_key=api_key)

    def govern_input(self, text: str) -> str:
        """Govern input text - standalone method."""
        return self._middleware.govern_input(text)

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped workflow."""
        return getattr(self._workflow, name)

    def run(self, inputs: Optional[Dict] = None, **kwargs) -> str:
        """Run the workflow with governance applied to inputs and final output."""
        if inputs:
            for key, value in inputs.items():
                if isinstance(value, str):
                    result = self._middleware.process_input(value)
                    if result.action == GovernanceAction.DENY:
                        raise ValueError(f"Input blocked: {result.receipt.receipt_id}")
                    inputs[key] = result.output

        try:
            if hasattr(self._workflow, 'run'):
                output = self._workflow.run(**(inputs or {}), **kwargs)
            else:
                output = "Workflow execution simulated"
        except Exception as e:
            raise e

        output_str = str(output)
        output_result = self._middleware.process_output(output_str)
        return output_result.output
