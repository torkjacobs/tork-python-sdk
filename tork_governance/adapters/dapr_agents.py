"""
Dapr Agents (Microsoft) Integration for Tork Governance

Provides governance wrappers for Microsoft's Dapr Agents framework,
applying policy enforcement to actor-based agent workflows.

Version support: Dapr Agents >= 0.1.0
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkDaprAgent:
    """
    Governance wrapper for Dapr Agents (Microsoft).

    Example:
        >>> from tork_governance.adapters.dapr_agents import TorkDaprAgent
        >>> agent = TorkDaprAgent(api_key="tork-key")
        >>> result = agent.govern("user input text")
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "dapr-agent",
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.agent_id = agent_id
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.receipts: List[Dict] = []

    def wrap_agent(self, agent: Any) -> "GovernedDaprAgentInstance":
        """Wrap a Dapr Agent with governance controls."""
        return GovernedDaprAgentInstance(agent, self)

    def process_input(self, content: str) -> GovernanceResult:
        """Process and validate input content."""
        result = self.tork.govern(content)
        self.receipts.append({
            'type': 'input',
            'agent_id': self.agent_id,
            'receipt_id': result.receipt.receipt_id,
            'action': result.action.value,
        })
        return result

    def process_output(self, content: str) -> GovernanceResult:
        """Process and validate output content."""
        result = self.tork.govern(content)
        self.receipts.append({
            'type': 'output',
            'agent_id': self.agent_id,
            'receipt_id': result.receipt.receipt_id,
            'action': result.action.value,
        })
        return result

    def govern(self, text: str) -> str:
        """Govern text through Tork policy."""
        result = self.process_input(text)
        return result.output


class GovernedDaprAgentInstance:
    """Wrapper for a Dapr Agent with governance applied."""

    def __init__(self, agent: Any, middleware: TorkDaprAgent):
        self._agent = agent
        self._middleware = middleware

    def __getattr__(self, name: str) -> Any:
        return getattr(self._agent, name)

    def invoke(self, message: str, **kwargs) -> str:
        """Invoke the agent with governance applied."""
        if self._middleware.govern_input:
            input_result = self._middleware.process_input(message)
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Input blocked by governance: {input_result.receipt.receipt_id}")
            message = input_result.output

        if hasattr(self._agent, 'invoke'):
            output = self._agent.invoke(message, **kwargs)
        else:
            output = str(message)

        output_str = str(output)
        if self._middleware.govern_output:
            output_result = self._middleware.process_output(output_str)
            return output_result.output
        return output_str

    def send_message(self, target: str, message: str, **kwargs) -> str:
        """Send a message to another agent with governance."""
        if self._middleware.govern_input:
            input_result = self._middleware.process_input(message)
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Message blocked by governance: {input_result.receipt.receipt_id}")
            message = input_result.output

        if hasattr(self._agent, 'send_message'):
            output = self._agent.send_message(target, message, **kwargs)
        else:
            output = str(message)

        output_str = str(output)
        if self._middleware.govern_output:
            output_result = self._middleware.process_output(output_str)
            return output_result.output
        return output_str


class TorkDaprWorkflow:
    """Wraps a Dapr agent workflow with governance at each step."""

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        agent_id: str = "dapr-workflow",
    ):
        self.tork = tork or Tork(api_key=api_key)
        self.agent_id = agent_id
        self.receipts: List[Dict] = []

    def govern_step(self, step_fn: Callable) -> Callable:
        """Wrap a workflow step function with governance."""
        @wraps(step_fn)
        def wrapper(*args, **kwargs):
            for arg in args:
                if isinstance(arg, str):
                    result = self.tork.govern(arg)
                    self.receipts.append({
                        'type': 'workflow_input',
                        'agent_id': self.agent_id,
                        'receipt_id': result.receipt.receipt_id,
                        'action': result.action.value,
                    })
                    if result.action == GovernanceAction.DENY:
                        raise ValueError(f"Workflow input blocked: {result.receipt.receipt_id}")
            output = step_fn(*args, **kwargs)
            if isinstance(output, str):
                result = self.tork.govern(output)
                self.receipts.append({
                    'type': 'workflow_output',
                    'agent_id': self.agent_id,
                    'receipt_id': result.receipt.receipt_id,
                    'action': result.action.value,
                })
                return result.output
            return output
        return wrapper


def dapr_governed(
    tork: Any = None,
    api_key: Optional[str] = None,
    govern_input: bool = True,
    govern_output: bool = True,
):
    """Decorator to govern Dapr Agents operations."""
    _tork = tork or Tork(api_key=api_key)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if govern_input and args:
                new_args = list(args)
                for i, arg in enumerate(new_args):
                    if isinstance(arg, str):
                        result = _tork.govern(arg)
                        if result.action == GovernanceAction.DENY:
                            raise ValueError(f"Input blocked: {result.receipt.receipt_id}")
                        new_args[i] = result.output
                args = tuple(new_args)

            output = func(*args, **kwargs)

            if govern_output and isinstance(output, str):
                result = _tork.govern(output)
                return result.output
            return output
        return wrapper
    return decorator
