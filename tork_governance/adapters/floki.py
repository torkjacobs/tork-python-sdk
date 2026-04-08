"""
Floki AI Integration for Tork Governance

Provides middleware and wrappers for Floki agent orchestration
with governance checks on agent interactions and tool usage.
"""

from typing import Any, Dict, List, Optional
from ..core import Tork, GovernanceResult, GovernanceAction


class FlokiAdapter:
    """
    Middleware for Floki AI that applies Tork governance to agent
    orchestration and message handling.

    Example:
        >>> from tork_governance.adapters.floki import FlokiAdapter
        >>> adapter = FlokiAdapter()
        >>> governed_text = adapter.govern("user input text")
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "floki-agent"
    ):
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.agent_id = agent_id
        self.receipts: List[Dict] = []

    def wrap_agent(self, agent: Any) -> "GovernedFlokiAgent":
        """Wrap a Floki agent with governance controls."""
        return GovernedFlokiAgent(agent, self)

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


class GovernedFlokiAgent:
    """
    Wrapper for a Floki agent that applies governance to all interactions.

    Example:
        >>> from tork_governance.adapters.floki import FlokiAdapter
        >>> adapter = FlokiAdapter()
        >>> governed = adapter.wrap_agent(floki_agent)
        >>> result = governed.run("Hello")
    """

    def __init__(self, agent: Any = None, middleware: FlokiAdapter = None, api_key: Optional[str] = None):
        self._agent = agent
        self._middleware = middleware or FlokiAdapter(api_key=api_key)

    def govern_input(self, text: str) -> str:
        """Govern input text - standalone method."""
        return self._middleware.govern_input(text)

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped agent."""
        return getattr(self._agent, name)

    def run(self, message: str, **kwargs) -> str:
        """Run the agent with governance applied to input and output."""
        input_result = self._middleware.process_input(message)
        if input_result.action == GovernanceAction.DENY:
            raise ValueError(f"Message blocked by governance: {input_result.receipt.receipt_id}")

        try:
            if hasattr(self._agent, 'run'):
                output = self._agent.run(input_result.output, **kwargs)
            elif hasattr(self._agent, 'execute'):
                output = self._agent.execute(input_result.output, **kwargs)
            else:
                output = str(input_result.output)
        except Exception as e:
            raise e

        output_result = self._middleware.process_output(str(output))
        return output_result.output

    def chat(self, message: str, **kwargs) -> str:
        """Send a chat message with governance applied."""
        input_result = self._middleware.process_input(message)
        if input_result.action == GovernanceAction.DENY:
            raise ValueError(f"Chat blocked by governance: {input_result.receipt.receipt_id}")

        try:
            if hasattr(self._agent, 'chat'):
                output = self._agent.chat(input_result.output, **kwargs)
            else:
                output = str(input_result.output)
        except Exception as e:
            raise e

        output_result = self._middleware.process_output(str(output))
        return output_result.output
