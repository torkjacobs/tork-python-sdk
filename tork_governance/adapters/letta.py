"""
Letta (formerly MemGPT) Integration for Tork Governance

Provides middleware and wrappers for Letta agents and memory operations.
"""

from typing import Any, Dict, List, Optional
from ..core import Tork, GovernanceResult, GovernanceAction


class LettaAdapter:
    """
    Middleware for Letta (formerly MemGPT) that applies Tork governance
    to agent memory operations and message handling.

    Example:
        >>> from tork_governance.adapters.letta import LettaAdapter
        >>> adapter = LettaAdapter()
        >>> governed_text = adapter.govern("user input text")
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "letta-agent"
    ):
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.agent_id = agent_id
        self.receipts: List[Dict] = []

    def wrap_agent(self, agent: Any) -> "GovernedLettaAgent":
        """Wrap a Letta agent with governance controls."""
        return GovernedLettaAgent(agent, self)

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

    def check_memory_operation(self, operation: str, content: str) -> GovernanceResult:
        """Validate a memory operation (read/write/search) before execution."""
        combined = f"{operation}: {content}"
        result = self.tork.govern(combined)
        self.receipts.append({
            'type': 'memory_operation',
            'operation': operation,
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


class GovernedLettaAgent:
    """
    Wrapper for a Letta agent that applies governance to all interactions
    including memory reads, memory writes, and message sends.

    Example:
        >>> from tork_governance.adapters.letta import LettaAdapter
        >>> adapter = LettaAdapter()
        >>> governed = adapter.wrap_agent(letta_agent)
        >>> result = governed.send_message("Hello")
    """

    def __init__(self, agent: Any = None, middleware: LettaAdapter = None, api_key: Optional[str] = None):
        self._agent = agent
        self._middleware = middleware or LettaAdapter(api_key=api_key)

    def govern_input(self, text: str) -> str:
        """Govern input text - standalone method."""
        return self._middleware.govern_input(text)

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped agent."""
        return getattr(self._agent, name)

    def send_message(self, message: str, **kwargs) -> str:
        """Send a message with governance applied."""
        input_result = self._middleware.process_input(message)
        if input_result.action == GovernanceAction.DENY:
            raise ValueError(f"Message blocked by governance: {input_result.receipt.receipt_id}")

        try:
            if hasattr(self._agent, 'send_message'):
                output = self._agent.send_message(input_result.output, **kwargs)
            else:
                output = str(input_result.output)
        except Exception as e:
            raise e

        output_result = self._middleware.process_output(str(output))
        return output_result.output

    def memory_write(self, content: str, **kwargs) -> str:
        """Write to agent memory with governance applied."""
        mem_result = self._middleware.check_memory_operation("write", content)
        if mem_result.action == GovernanceAction.DENY:
            raise ValueError(f"Memory write blocked by governance: {mem_result.receipt.receipt_id}")

        try:
            if hasattr(self._agent, 'memory_write'):
                output = self._agent.memory_write(mem_result.output, **kwargs)
            elif hasattr(self._agent, 'insert'):
                output = self._agent.insert(mem_result.output, **kwargs)
            else:
                output = str(mem_result.output)
        except Exception as e:
            raise e

        return str(output)

    def memory_search(self, query: str, **kwargs) -> Any:
        """Search agent memory with governance applied to the query."""
        search_result = self._middleware.check_memory_operation("search", query)
        if search_result.action == GovernanceAction.DENY:
            raise ValueError(f"Memory search blocked by governance: {search_result.receipt.receipt_id}")

        try:
            if hasattr(self._agent, 'memory_search'):
                output = self._agent.memory_search(search_result.output, **kwargs)
            elif hasattr(self._agent, 'search'):
                output = self._agent.search(search_result.output, **kwargs)
            else:
                output = []
        except Exception as e:
            raise e

        return output
