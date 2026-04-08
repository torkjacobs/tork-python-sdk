"""
CAMEL-AI Multi-Agent Integration for Tork Governance

Provides governance wrappers for the CAMEL-AI multi-agent framework,
applying policy enforcement to role-playing sessions and agent interactions.

Version support: CAMEL-AI >= 0.1.0
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkCAMELAgent:
    """
    Governance wrapper for CAMEL-AI agents.

    Example:
        >>> from tork_governance.adapters.camel_ai import TorkCAMELAgent
        >>> agent = TorkCAMELAgent(api_key="tork-key")
        >>> result = agent.govern("user input text")
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "camel-ai-agent",
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.agent_id = agent_id
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.receipts: List[Dict] = []

    def wrap_agent(self, agent: Any) -> "GovernedCAMELAgentInstance":
        """Wrap a CAMEL-AI agent with governance controls."""
        return GovernedCAMELAgentInstance(agent, self)

    def wrap_session(self, session: Any) -> "GovernedCAMELSession":
        """Wrap a CAMEL-AI role-playing session with governance."""
        return GovernedCAMELSession(session, self)

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


class GovernedCAMELAgentInstance:
    """Wrapper for a CAMEL-AI agent with governance applied."""

    def __init__(self, agent: Any, middleware: TorkCAMELAgent):
        self._agent = agent
        self._middleware = middleware

    def __getattr__(self, name: str) -> Any:
        return getattr(self._agent, name)

    def step(self, message: str, **kwargs) -> str:
        """Execute a single agent step with governance."""
        if self._middleware.govern_input:
            input_result = self._middleware.process_input(message)
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Input blocked by governance: {input_result.receipt.receipt_id}")
            message = input_result.output

        if hasattr(self._agent, 'step'):
            output = self._agent.step(message, **kwargs)
        else:
            output = str(message)

        output_str = str(output)
        if self._middleware.govern_output:
            output_result = self._middleware.process_output(output_str)
            return output_result.output
        return output_str


class GovernedCAMELSession:
    """Wrapper for a CAMEL-AI role-playing session with governance."""

    def __init__(self, session: Any, middleware: TorkCAMELAgent):
        self._session = session
        self._middleware = middleware

    def __getattr__(self, name: str) -> Any:
        return getattr(self._session, name)

    def step(self, **kwargs) -> Dict[str, Any]:
        """Execute a session step with governance on messages."""
        if hasattr(self._session, 'step'):
            result = self._session.step(**kwargs)
        else:
            result = {"assistant_msg": "simulated", "user_msg": "simulated"}

        if isinstance(result, dict):
            for key in ('assistant_msg', 'user_msg'):
                if key in result and isinstance(result[key], str):
                    gov_result = self._middleware.process_output(result[key])
                    result[key] = gov_result.output
        return result


def camel_ai_governed(
    tork: Any = None,
    api_key: Optional[str] = None,
    govern_input: bool = True,
    govern_output: bool = True,
):
    """Decorator to govern CAMEL-AI operations."""
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
