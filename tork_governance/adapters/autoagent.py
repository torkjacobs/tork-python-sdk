"""
AutoAgent Framework Integration for Tork Governance

Provides governance wrappers for the AutoAgent framework,
applying policy enforcement to agent execution and tool calls.

Version support: AutoAgent >= 0.1.0
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkAutoAgent:
    """
    Governance wrapper for AutoAgent framework agents.

    Example:
        >>> from tork_governance.adapters.autoagent import TorkAutoAgent
        >>> agent = TorkAutoAgent()
        >>> result = agent.govern("user input text")
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "autoagent",
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.agent_id = agent_id
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.receipts: List[Dict] = []

    def wrap_agent(self, agent: Any) -> "GovernedAutoAgentInstance":
        """Wrap an AutoAgent instance with governance controls."""
        return GovernedAutoAgentInstance(agent, self)

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


class GovernedAutoAgentInstance:
    """
    Wrapper for an AutoAgent instance with governance applied.

    Example:
        >>> from tork_governance.adapters.autoagent import TorkAutoAgent
        >>> middleware = TorkAutoAgent()
        >>> governed = middleware.wrap_agent(my_agent)
        >>> result = governed.run("Hello")
    """

    def __init__(self, agent: Any, middleware: TorkAutoAgent):
        self._agent = agent
        self._middleware = middleware

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped agent."""
        return getattr(self._agent, name)

    def run(self, task: str, **kwargs) -> str:
        """Run the agent with governance applied."""
        if self._middleware.govern_input:
            input_result = self._middleware.process_input(task)
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Input blocked by governance: {input_result.receipt.receipt_id}")
            task = input_result.output

        if hasattr(self._agent, 'run'):
            output = self._agent.run(task, **kwargs)
        else:
            output = str(task)

        output_str = str(output)
        if self._middleware.govern_output:
            output_result = self._middleware.process_output(output_str)
            return output_result.output
        return output_str

    def execute(self, task: str, **kwargs) -> str:
        """Execute a task with governance applied (alias for run)."""
        return self.run(task, **kwargs)


def autoagent_governed(
    tork: Any = None,
    api_key: Optional[str] = None,
    govern_input: bool = True,
    govern_output: bool = True,
):
    """Decorator to govern AutoAgent operations."""
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
