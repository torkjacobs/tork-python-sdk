"""
Google Agent Development Kit (ADK) Integration for Tork Governance

Provides middleware and wrappers for Google's ADK agent framework.
ADK agents use tools, have instructions, and process user messages.
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


def _extract_adk_content(message: Any) -> Optional[str]:
    """Extract text content from an ADK message or content object."""
    if isinstance(message, str):
        return message
    if isinstance(message, dict):
        if "text" in message:
            return message["text"]
        if "content" in message:
            return _extract_adk_content(message["content"])
        if "parts" in message:
            texts = []
            for part in message["parts"]:
                if isinstance(part, str):
                    texts.append(part)
                elif isinstance(part, dict) and "text" in part:
                    texts.append(part["text"])
            return "\n".join(texts) if texts else None
    if hasattr(message, "text"):
        return message.text
    if hasattr(message, "content"):
        return _extract_adk_content(message.content)
    return None


class TorkADKAgent:
    """
    Wrapper class that governs a Google ADK Agent's input/output.

    Example:
        >>> from tork_governance.adapters.google_adk import TorkADKAgent
        >>> from google.adk import Agent
        >>>
        >>> agent = Agent(name="assistant", model="gemini-2.0-flash")
        >>> governed = TorkADKAgent(agent)
        >>> response = governed.run("Tell me about user john@example.com")
    """

    def __init__(
        self,
        agent: Any = None,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "google-adk-agent",
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self._agent = agent
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.agent_id = agent_id
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.receipts: List[Dict] = []

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped agent."""
        return getattr(self._agent, name)

    def _govern_text(self, text: str, direction: str) -> GovernanceResult:
        """Govern a text string and track the receipt."""
        result = self.tork.govern(text)
        self.receipts.append({
            'type': direction,
            'agent_id': self.agent_id,
            'receipt_id': result.receipt.receipt_id,
            'action': result.action.value,
        })
        return result

    def run(self, user_message: str, **kwargs) -> str:
        """Run the agent with governance applied to input and output."""
        if self.govern_input:
            input_result = self._govern_text(user_message, "input")
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Input blocked by governance: {input_result.receipt.receipt_id}")
            user_message = input_result.output

        # Execute via the wrapped agent
        if hasattr(self._agent, "run"):
            output = self._agent.run(user_message, **kwargs)
        else:
            output = f"Agent response to: {user_message}"

        output_text = _extract_adk_content(output) or str(output)

        if self.govern_output:
            output_result = self._govern_text(output_text, "output")
            return output_result.output

        return output_text

    async def run_async(self, user_message: str, **kwargs) -> str:
        """Async version of run with governance applied."""
        if self.govern_input:
            input_result = self._govern_text(user_message, "input")
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Input blocked by governance: {input_result.receipt.receipt_id}")
            user_message = input_result.output

        if hasattr(self._agent, "run_async"):
            output = await self._agent.run_async(user_message, **kwargs)
        elif hasattr(self._agent, "run"):
            output = self._agent.run(user_message, **kwargs)
        else:
            output = f"Agent response to: {user_message}"

        output_text = _extract_adk_content(output) or str(output)

        if self.govern_output:
            output_result = self._govern_text(output_text, "output")
            return output_result.output

        return output_text

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self._govern_text(text, "govern").output


class TorkADKCallback:
    """
    Callback class compatible with Google ADK's callback system.

    Governs messages at callback points during agent execution.

    Example:
        >>> from tork_governance.adapters.google_adk import TorkADKCallback
        >>>
        >>> callback = TorkADKCallback()
        >>> # Register with ADK agent
        >>> agent = Agent(name="assistant", callbacks=[callback])
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "google-adk-callback",
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.agent_id = agent_id
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.receipts: List[Dict] = []

    def _govern_text(self, text: str, direction: str) -> GovernanceResult:
        """Govern text and track receipt."""
        result = self.tork.govern(text)
        self.receipts.append({
            'type': direction,
            'agent_id': self.agent_id,
            'receipt_id': result.receipt.receipt_id,
            'action': result.action.value,
        })
        return result

    def on_user_message(self, message: Any) -> Any:
        """Called when a user message is received."""
        if not self.govern_input:
            return message

        text = _extract_adk_content(message)
        if text:
            result = self._govern_text(text, "user_message")
            if result.action == GovernanceAction.DENY:
                raise ValueError(f"User message blocked: {result.receipt.receipt_id}")
            if isinstance(message, str):
                return result.output
            if isinstance(message, dict):
                governed = dict(message)
                if "text" in governed:
                    governed["text"] = result.output
                elif "content" in governed:
                    governed["content"] = result.output
                return governed
        return message

    def on_agent_response(self, response: Any) -> Any:
        """Called when the agent produces a response."""
        if not self.govern_output:
            return response

        text = _extract_adk_content(response)
        if text:
            result = self._govern_text(text, "agent_response")
            if isinstance(response, str):
                return result.output
            if isinstance(response, dict):
                governed = dict(response)
                if "text" in governed:
                    governed["text"] = result.output
                elif "content" in governed:
                    governed["content"] = result.output
                return governed
        return response

    def on_tool_call(self, tool_name: str, tool_args: Dict) -> Dict:
        """Called before a tool is executed."""
        content = f"{tool_name}: {tool_args}"
        result = self._govern_text(content, "tool_call")
        if result.action == GovernanceAction.DENY:
            raise ValueError(f"Tool call blocked: {result.receipt.receipt_id}")
        return tool_args

    def on_tool_result(self, tool_name: str, result: Any) -> Any:
        """Called when a tool returns a result."""
        text = str(result) if not isinstance(result, str) else result
        gov_result = self._govern_text(text, "tool_result")
        return gov_result.output


def govern_adk_tool(
    tork: Optional[Tork] = None,
    api_key: Optional[str] = None,
    policy_version: str = "1.0.0",
    agent_id: str = "google-adk-tool",
    govern_input: bool = True,
    govern_output: bool = True,
) -> Callable:
    """
    Decorator for ADK tool functions. Governs tool inputs and outputs.

    Example:
        >>> from tork_governance.adapters.google_adk import govern_adk_tool
        >>>
        >>> @govern_adk_tool()
        ... def search_database(query: str) -> str:
        ...     return db.search(query)
    """
    _tork = tork or Tork(api_key=api_key, policy_version=policy_version)
    _receipts: List[Dict] = []

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Govern string arguments
            if govern_input:
                governed_args = []
                for arg in args:
                    if isinstance(arg, str):
                        result = _tork.govern(arg)
                        _receipts.append({
                            'type': 'tool_input',
                            'agent_id': agent_id,
                            'receipt_id': result.receipt.receipt_id,
                            'action': result.action.value,
                        })
                        if result.action == GovernanceAction.DENY:
                            raise ValueError(f"Tool input blocked: {result.receipt.receipt_id}")
                        governed_args.append(result.output)
                    else:
                        governed_args.append(arg)
                args = tuple(governed_args)

                governed_kwargs = {}
                for key, value in kwargs.items():
                    if isinstance(value, str):
                        result = _tork.govern(value)
                        _receipts.append({
                            'type': 'tool_input',
                            'agent_id': agent_id,
                            'receipt_id': result.receipt.receipt_id,
                            'action': result.action.value,
                        })
                        if result.action == GovernanceAction.DENY:
                            raise ValueError(f"Tool input blocked: {result.receipt.receipt_id}")
                        governed_kwargs[key] = result.output
                    else:
                        governed_kwargs[key] = value
                kwargs = governed_kwargs

            output = func(*args, **kwargs)

            if govern_output and isinstance(output, str):
                result = _tork.govern(output)
                _receipts.append({
                    'type': 'tool_output',
                    'agent_id': agent_id,
                    'receipt_id': result.receipt.receipt_id,
                    'action': result.action.value,
                })
                return result.output

            return output

        wrapper.receipts = _receipts
        return wrapper
    return decorator


def govern_adk_run(
    tork: Optional[Tork] = None,
    api_key: Optional[str] = None,
    policy_version: str = "1.0.0",
    agent_id: str = "google-adk-run",
    govern_input: bool = True,
    govern_output: bool = True,
) -> Callable:
    """
    Decorator for agent.run() calls. Governs user message and agent response.

    Example:
        >>> from tork_governance.adapters.google_adk import govern_adk_run
        >>>
        >>> @govern_adk_run()
        ... def ask_agent(message: str) -> str:
        ...     return agent.run(message)
    """
    _tork = tork or Tork(api_key=api_key, policy_version=policy_version)
    _receipts: List[Dict] = []

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            governed_args = list(args)
            if govern_input and governed_args and isinstance(governed_args[0], str):
                result = _tork.govern(governed_args[0])
                _receipts.append({
                    'type': 'run_input',
                    'agent_id': agent_id,
                    'receipt_id': result.receipt.receipt_id,
                    'action': result.action.value,
                })
                if result.action == GovernanceAction.DENY:
                    raise ValueError(f"Run input blocked: {result.receipt.receipt_id}")
                governed_args[0] = result.output

            output = func(*governed_args, **kwargs)

            if govern_output:
                output_text = str(output) if not isinstance(output, str) else output
                result = _tork.govern(output_text)
                _receipts.append({
                    'type': 'run_output',
                    'agent_id': agent_id,
                    'receipt_id': result.receipt.receipt_id,
                    'action': result.action.value,
                })
                return result.output

            return output

        wrapper.receipts = _receipts
        return wrapper
    return decorator
