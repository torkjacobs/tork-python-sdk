"""
Langroid Integration for Tork Governance

Provides middleware and wrappers for the Langroid multi-agent framework
with governance checks on agent interactions and task orchestration.
"""

from typing import Any, Dict, List, Optional
from ..core import Tork, GovernanceResult, GovernanceAction


class LangroidAdapter:
    """
    Middleware for Langroid that applies Tork governance to multi-agent
    interactions and task orchestration.

    Example:
        >>> from tork_governance.adapters.langroid import LangroidAdapter
        >>> adapter = LangroidAdapter()
        >>> governed_text = adapter.govern("user input text")
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "langroid-agent"
    ):
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.agent_id = agent_id
        self.receipts: List[Dict] = []

    def wrap_agent(self, agent: Any) -> "GovernedLangroidAgent":
        """Wrap a Langroid agent with governance controls."""
        return GovernedLangroidAgent(agent, self)

    def wrap_task(self, task: Any) -> "GovernedLangroidTask":
        """Wrap a Langroid task with governance controls."""
        return GovernedLangroidTask(task, self)

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


class GovernedLangroidAgent:
    """
    Wrapper for a Langroid agent that applies governance to all interactions.

    Example:
        >>> from tork_governance.adapters.langroid import LangroidAdapter
        >>> adapter = LangroidAdapter()
        >>> governed = adapter.wrap_agent(langroid_agent)
        >>> result = governed.llm_response("Hello")
    """

    def __init__(self, agent: Any = None, middleware: LangroidAdapter = None, api_key: Optional[str] = None):
        self._agent = agent
        self._middleware = middleware or LangroidAdapter(api_key=api_key)

    def govern_input(self, text: str) -> str:
        """Govern input text - standalone method."""
        return self._middleware.govern_input(text)

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped agent."""
        return getattr(self._agent, name)

    def llm_response(self, message: str, **kwargs) -> str:
        """Get an LLM response with governance applied."""
        input_result = self._middleware.process_input(message)
        if input_result.action == GovernanceAction.DENY:
            raise ValueError(f"Message blocked by governance: {input_result.receipt.receipt_id}")

        try:
            if hasattr(self._agent, 'llm_response'):
                output = self._agent.llm_response(input_result.output, **kwargs)
            elif hasattr(self._agent, 'respond'):
                output = self._agent.respond(input_result.output, **kwargs)
            else:
                output = str(input_result.output)
        except Exception as e:
            raise e

        output_result = self._middleware.process_output(str(output))
        return output_result.output

    def agent_response(self, message: str, **kwargs) -> str:
        """Get an agent response with governance applied."""
        input_result = self._middleware.process_input(message)
        if input_result.action == GovernanceAction.DENY:
            raise ValueError(f"Message blocked by governance: {input_result.receipt.receipt_id}")

        try:
            if hasattr(self._agent, 'agent_response'):
                output = self._agent.agent_response(input_result.output, **kwargs)
            else:
                output = str(input_result.output)
        except Exception as e:
            raise e

        output_result = self._middleware.process_output(str(output))
        return output_result.output


class GovernedLangroidTask:
    """
    Wrapper for a Langroid Task that applies governance to task orchestration.

    Example:
        >>> from tork_governance.adapters.langroid import LangroidAdapter
        >>> adapter = LangroidAdapter()
        >>> governed = adapter.wrap_task(langroid_task)
        >>> result = governed.run("Hello")
    """

    def __init__(self, task: Any = None, middleware: LangroidAdapter = None, api_key: Optional[str] = None):
        self._task = task
        self._middleware = middleware or LangroidAdapter(api_key=api_key)

    def govern_input(self, text: str) -> str:
        """Govern input text - standalone method."""
        return self._middleware.govern_input(text)

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped task."""
        return getattr(self._task, name)

    def run(self, message: str = "", **kwargs) -> str:
        """Run the task with governance applied to input and output."""
        if message:
            input_result = self._middleware.process_input(message)
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Task input blocked by governance: {input_result.receipt.receipt_id}")
            message = input_result.output

        try:
            if hasattr(self._task, 'run'):
                output = self._task.run(message, **kwargs)
            else:
                output = str(message or "Task execution simulated")
        except Exception as e:
            raise e

        output_result = self._middleware.process_output(str(output))
        return output_result.output
