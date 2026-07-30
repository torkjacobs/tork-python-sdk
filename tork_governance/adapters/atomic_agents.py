"""
Atomic Agents Framework Integration for Tork Governance

Provides governance wrappers for the Atomic Agents framework,
applying policy enforcement to agent pipelines and tool execution.

Version support: Atomic Agents >= 1.0.0
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkAtomicAgent:
    """
    Governance wrapper for Atomic Agents framework.

    Example:
        >>> from tork_governance.adapters.atomic_agents import TorkAtomicAgent
        >>> agent = TorkAtomicAgent()
        >>> result = agent.govern("user input text")
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "atomic-agent",
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.agent_id = agent_id
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.receipts: List[Dict] = []

    def wrap_agent(self, agent: Any) -> "GovernedAtomicAgentInstance":
        """Wrap an Atomic Agent with governance controls."""
        return GovernedAtomicAgentInstance(agent, self)

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


class GovernedAtomicAgentInstance:
    """Wrapper for an Atomic Agent with governance applied."""

    def __init__(self, agent: Any, middleware: TorkAtomicAgent):
        self._agent = agent
        self._middleware = middleware

    def __getattr__(self, name: str) -> Any:
        return getattr(self._agent, name)

    def run(self, input_data: Any, **kwargs) -> Any:
        """Run the agent with governance applied."""
        if isinstance(input_data, str) and self._middleware.govern_input:
            input_result = self._middleware.process_input(input_data)
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Input blocked by governance: {input_result.receipt.receipt_id}")
            input_data = input_result.output

        if hasattr(self._agent, 'run'):
            output = self._agent.run(input_data, **kwargs)
        else:
            output = str(input_data)

        output_str = str(output)
        if self._middleware.govern_output:
            output_result = self._middleware.process_output(output_str)
            return output_result.output
        return output_str

    def process(self, input_data: Any, **kwargs) -> Any:
        """Process input through the agent pipeline with governance (alias for run)."""
        return self.run(input_data, **kwargs)


class TorkAtomicToolWrapper:
    """Wraps individual Atomic Agent tools with governance."""

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        agent_id: str = "atomic-tool",
    ):
        self.tork = tork or Tork(api_key=api_key)
        self.agent_id = agent_id
        self.receipts: List[Dict] = []

    def wrap_tool(self, tool_fn: Callable) -> Callable:
        """Wrap a tool function with governance checks."""
        @wraps(tool_fn)
        def wrapper(*args, **kwargs):
            for arg in args:
                if isinstance(arg, str):
                    result = self.tork.govern(arg)
                    self.receipts.append({
                        'type': 'tool_input',
                        'agent_id': self.agent_id,
                        'receipt_id': result.receipt.receipt_id,
                        'action': result.action.value,
                    })
                    if result.action == GovernanceAction.DENY:
                        raise ValueError(f"Tool input blocked: {result.receipt.receipt_id}")
            output = tool_fn(*args, **kwargs)
            if isinstance(output, str):
                result = self.tork.govern(output)
                self.receipts.append({
                    'type': 'tool_output',
                    'agent_id': self.agent_id,
                    'receipt_id': result.receipt.receipt_id,
                    'action': result.action.value,
                })
                return result.output
            return output
        return wrapper


def atomic_governed(
    tork: Any = None,
    api_key: Optional[str] = None,
    govern_input: bool = True,
    govern_output: bool = True,
):
    """Decorator to govern Atomic Agents operations."""
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
