"""
Anthropic Agent SDK Integration for Tork Governance

Provides middleware and wrappers for the Anthropic Agent SDK,
which powers Claude Code and similar agent systems.
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


def _extract_anthropic_content(message: Any) -> Optional[str]:
    """Extract text content from an Anthropic message or content block."""
    if isinstance(message, str):
        return message
    if isinstance(message, dict):
        # Handle content blocks: {"type": "text", "text": "..."}
        if message.get("type") == "text" and "text" in message:
            return message["text"]
        # Handle message format: {"role": "...", "content": "..." or [...]}
        if "content" in message:
            content = message["content"]
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                texts = []
                for block in content:
                    if isinstance(block, str):
                        texts.append(block)
                    elif isinstance(block, dict) and block.get("type") == "text":
                        texts.append(block.get("text", ""))
                return "\n".join(texts) if texts else None
    # Handle objects with .content attribute (SDK response objects)
    if hasattr(message, "content"):
        content = message.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = []
            for block in content:
                if hasattr(block, "text"):
                    texts.append(block.text)
                elif isinstance(block, dict) and block.get("type") == "text":
                    texts.append(block.get("text", ""))
            return "\n".join(texts) if texts else None
    return None


def _govern_anthropic_message(tork: Tork, message: Any, receipts: List[Dict], direction: str, agent_id: str) -> Any:
    """Govern text content within an Anthropic message."""
    if isinstance(message, str):
        result = tork.govern(message)
        receipts.append({
            'type': direction,
            'agent_id': agent_id,
            'receipt_id': result.receipt.receipt_id,
            'action': result.action.value,
        })
        if result.action == GovernanceAction.DENY:
            raise ValueError(f"Content blocked by governance: {result.receipt.receipt_id}")
        return result.output

    if isinstance(message, dict):
        governed = dict(message)
        if governed.get("type") == "text" and "text" in governed:
            result = tork.govern(governed["text"])
            receipts.append({
                'type': direction,
                'agent_id': agent_id,
                'receipt_id': result.receipt.receipt_id,
                'action': result.action.value,
            })
            if result.action == GovernanceAction.DENY:
                raise ValueError(f"Content blocked by governance: {result.receipt.receipt_id}")
            governed["text"] = result.output
            return governed

        if "content" in governed:
            content = governed["content"]
            if isinstance(content, str):
                result = tork.govern(content)
                receipts.append({
                    'type': direction,
                    'agent_id': agent_id,
                    'receipt_id': result.receipt.receipt_id,
                    'action': result.action.value,
                })
                if result.action == GovernanceAction.DENY:
                    raise ValueError(f"Message blocked by governance: {result.receipt.receipt_id}")
                governed["content"] = result.output
            elif isinstance(content, list):
                governed_blocks = []
                for block in content:
                    governed_blocks.append(
                        _govern_anthropic_message(tork, block, receipts, direction, agent_id)
                    )
                governed["content"] = governed_blocks
            return governed

    return message


class TorkAnthropicAgent:
    """
    Wrapper class governing an Anthropic agent's conversation.

    Governs user messages before the agent processes them and
    agent responses before they're returned.

    Example:
        >>> from tork_governance.adapters.anthropic_agents import TorkAnthropicAgent
        >>> from agents import Agent
        >>>
        >>> agent = Agent(name="assistant", model="claude-sonnet-4-20250514")
        >>> governed = TorkAnthropicAgent(agent)
        >>> response = governed.run("Tell me about user john@example.com")
    """

    def __init__(
        self,
        agent: Any = None,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "anthropic-agent",
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
        """Govern a text string and track receipt."""
        result = self.tork.govern(text)
        self.receipts.append({
            'type': direction,
            'agent_id': self.agent_id,
            'receipt_id': result.receipt.receipt_id,
            'action': result.action.value,
        })
        return result

    def run(self, user_message: Any, **kwargs) -> str:
        """Run the agent with governance applied."""
        # Govern user message
        if self.govern_input:
            if isinstance(user_message, str):
                result = self._govern_text(user_message, "input")
                if result.action == GovernanceAction.DENY:
                    raise ValueError(f"Input blocked by governance: {result.receipt.receipt_id}")
                user_message = result.output
            elif isinstance(user_message, dict):
                user_message = _govern_anthropic_message(
                    self.tork, user_message, self.receipts, "input", self.agent_id
                )
            elif isinstance(user_message, list):
                user_message = [
                    _govern_anthropic_message(self.tork, msg, self.receipts, "input", self.agent_id)
                    for msg in user_message
                ]

        # Execute via wrapped agent
        if hasattr(self._agent, "run"):
            output = self._agent.run(user_message, **kwargs)
        else:
            output = f"Agent response to: {user_message}"

        # Govern output
        if self.govern_output:
            output_text = _extract_anthropic_content(output) or str(output)
            result = self._govern_text(output_text, "output")
            return result.output

        return _extract_anthropic_content(output) or str(output)

    async def run_async(self, user_message: Any, **kwargs) -> str:
        """Async version of run with governance applied."""
        if self.govern_input:
            if isinstance(user_message, str):
                result = self._govern_text(user_message, "input")
                if result.action == GovernanceAction.DENY:
                    raise ValueError(f"Input blocked by governance: {result.receipt.receipt_id}")
                user_message = result.output
            elif isinstance(user_message, dict):
                user_message = _govern_anthropic_message(
                    self.tork, user_message, self.receipts, "input", self.agent_id
                )

        if hasattr(self._agent, "run_async"):
            output = await self._agent.run_async(user_message, **kwargs)
        elif hasattr(self._agent, "run"):
            output = self._agent.run(user_message, **kwargs)
        else:
            output = f"Agent response to: {user_message}"

        if self.govern_output:
            output_text = _extract_anthropic_content(output) or str(output)
            result = self._govern_text(output_text, "output")
            return result.output

        return _extract_anthropic_content(output) or str(output)

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self._govern_text(text, "govern").output


class TorkAnthropicToolWrapper:
    """
    Wraps individual Anthropic agent tools to govern their inputs/outputs.

    Governs tool_use input JSON and tool_result content.

    Example:
        >>> from tork_governance.adapters.anthropic_agents import TorkAnthropicToolWrapper
        >>>
        >>> wrapper = TorkAnthropicToolWrapper()
        >>> governed_tool = wrapper.wrap(my_tool_function)
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "anthropic-tool",
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

    def wrap(self, func: Callable) -> Callable:
        """Wrap a tool function with governance."""
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Govern string arguments (tool_use inputs)
            if self.govern_input:
                governed_args = []
                for arg in args:
                    if isinstance(arg, str):
                        result = self._govern_text(arg, "tool_input")
                        if result.action == GovernanceAction.DENY:
                            raise ValueError(f"Tool input blocked: {result.receipt.receipt_id}")
                        governed_args.append(result.output)
                    else:
                        governed_args.append(arg)
                args = tuple(governed_args)

                governed_kwargs = {}
                for key, value in kwargs.items():
                    if isinstance(value, str):
                        result = self._govern_text(value, "tool_input")
                        if result.action == GovernanceAction.DENY:
                            raise ValueError(f"Tool input blocked: {result.receipt.receipt_id}")
                        governed_kwargs[key] = result.output
                    else:
                        governed_kwargs[key] = value
                kwargs = governed_kwargs

            output = func(*args, **kwargs)

            # Govern tool_result content
            if self.govern_output and isinstance(output, str):
                result = self._govern_text(output, "tool_output")
                return result.output

            return output
        return wrapper

    def govern_tool_use(self, tool_name: str, tool_input: Dict) -> Dict:
        """Govern a tool_use block's input."""
        governed = {}
        for key, value in tool_input.items():
            if isinstance(value, str):
                result = self._govern_text(value, "tool_use_input")
                if result.action == GovernanceAction.DENY:
                    raise ValueError(f"Tool use blocked for {tool_name}: {result.receipt.receipt_id}")
                governed[key] = result.output
            else:
                governed[key] = value
        return governed

    def govern_tool_result(self, content: Any) -> Any:
        """Govern a tool_result block's content."""
        if isinstance(content, str):
            result = self._govern_text(content, "tool_result")
            return result.output
        if isinstance(content, list):
            governed = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    result = self._govern_text(block.get("text", ""), "tool_result")
                    governed.append({**block, "text": result.output})
                else:
                    governed.append(block)
            return governed
        return content


def govern_agent_turn(
    tork: Optional[Tork] = None,
    api_key: Optional[str] = None,
    policy_version: str = "1.0.0",
    agent_id: str = "anthropic-turn",
    govern_input: bool = True,
    govern_output: bool = True,
) -> Callable:
    """
    Decorator for a single agent turn (user message -> agent response).

    Example:
        >>> from tork_governance.adapters.anthropic_agents import govern_agent_turn
        >>>
        >>> @govern_agent_turn()
        ... def chat(user_message: str) -> str:
        ...     return agent.run(user_message)
    """
    _tork = tork or Tork(api_key=api_key, policy_version=policy_version)
    _receipts: List[Dict] = []

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            governed_args = list(args)

            # Govern first string argument (user message)
            if govern_input and governed_args and isinstance(governed_args[0], str):
                result = _tork.govern(governed_args[0])
                _receipts.append({
                    'type': 'turn_input',
                    'agent_id': agent_id,
                    'receipt_id': result.receipt.receipt_id,
                    'action': result.action.value,
                })
                if result.action == GovernanceAction.DENY:
                    raise ValueError(f"Turn input blocked: {result.receipt.receipt_id}")
                governed_args[0] = result.output

            output = func(*governed_args, **kwargs)

            if govern_output:
                output_text = _extract_anthropic_content(output) or str(output)
                result = _tork.govern(output_text)
                _receipts.append({
                    'type': 'turn_output',
                    'agent_id': agent_id,
                    'receipt_id': result.receipt.receipt_id,
                    'action': result.action.value,
                })
                return result.output

            return output

        wrapper.receipts = _receipts
        return wrapper
    return decorator


def govern_tool_use(
    tork: Optional[Tork] = None,
    api_key: Optional[str] = None,
    policy_version: str = "1.0.0",
    agent_id: str = "anthropic-tool-use",
    govern_input: bool = True,
    govern_output: bool = True,
) -> Callable:
    """
    Decorator for tool execution within an agent turn.

    Example:
        >>> from tork_governance.adapters.anthropic_agents import govern_tool_use
        >>>
        >>> @govern_tool_use()
        ... def execute_tool(tool_name: str, tool_input: dict) -> str:
        ...     return tools[tool_name](**tool_input)
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
                            'type': 'tool_use_input',
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
                            'type': 'tool_use_input',
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
                    'type': 'tool_use_output',
                    'agent_id': agent_id,
                    'receipt_id': result.receipt.receipt_id,
                    'action': result.action.value,
                })
                return result.output

            return output

        wrapper.receipts = _receipts
        return wrapper
    return decorator
