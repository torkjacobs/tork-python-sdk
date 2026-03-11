"""
Smolagents (HuggingFace) Integration for Tork Governance

Provides middleware and wrappers for HuggingFace's Smolagents framework.
Smolagents supports CodeAgent and ToolCallingAgent patterns.
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


def _extract_smol_content(response: Any) -> Optional[str]:
    """Extract text content from a Smolagents response."""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        if "output" in response:
            return str(response["output"])
        if "content" in response:
            return str(response["content"])
        if "result" in response:
            return str(response["result"])
    if hasattr(response, "output"):
        return str(response.output)
    if hasattr(response, "content"):
        return str(response.content)
    return None


class TorkSmolAgent:
    """
    Wrapper class governing a Smolagents agent (CodeAgent or ToolCallingAgent).

    Example:
        >>> from tork_governance.adapters.smolagents import TorkSmolAgent
        >>> from smolagents import CodeAgent, HfApiModel
        >>>
        >>> agent = CodeAgent(tools=[], model=HfApiModel())
        >>> governed = TorkSmolAgent(agent)
        >>> response = governed.run("Find info about john@example.com")
    """

    def __init__(
        self,
        agent: Any = None,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "smolagents-agent",
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

    def run(self, task: str, **kwargs) -> str:
        """Run the agent with governance applied to task and output."""
        if self.govern_input:
            input_result = self._govern_text(task, "input")
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Task blocked by governance: {input_result.receipt.receipt_id}")
            task = input_result.output

        if hasattr(self._agent, "run"):
            output = self._agent.run(task, **kwargs)
        else:
            output = f"Agent response to: {task}"

        output_text = _extract_smol_content(output) or str(output)

        if self.govern_output:
            output_result = self._govern_text(output_text, "output")
            return output_result.output

        return output_text

    async def run_async(self, task: str, **kwargs) -> str:
        """Async version of run with governance applied."""
        if self.govern_input:
            input_result = self._govern_text(task, "input")
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Task blocked by governance: {input_result.receipt.receipt_id}")
            task = input_result.output

        if hasattr(self._agent, "run_async"):
            output = await self._agent.run_async(task, **kwargs)
        elif hasattr(self._agent, "run"):
            output = self._agent.run(task, **kwargs)
        else:
            output = f"Agent response to: {task}"

        output_text = _extract_smol_content(output) or str(output)

        if self.govern_output:
            output_result = self._govern_text(output_text, "output")
            return output_result.output

        return output_text

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self._govern_text(text, "govern").output


class TorkSmolTool:
    """
    Wrapper for individual Smolagents tools with governance.

    Example:
        >>> from tork_governance.adapters.smolagents import TorkSmolTool
        >>>
        >>> wrapper = TorkSmolTool()
        >>> governed_tool = wrapper.wrap(my_tool)
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "smolagents-tool",
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

            if self.govern_output and isinstance(output, str):
                result = self._govern_text(output, "tool_output")
                return result.output

            return output
        return wrapper

    def govern_tool_args(self, tool_name: str, tool_args: Dict) -> Dict:
        """Govern a tool's arguments before execution."""
        governed = {}
        for key, value in tool_args.items():
            if isinstance(value, str):
                result = self._govern_text(value, "tool_arg")
                if result.action == GovernanceAction.DENY:
                    raise ValueError(f"Tool arg blocked for {tool_name}: {result.receipt.receipt_id}")
                governed[key] = result.output
            else:
                governed[key] = value
        return governed

    def govern_tool_result(self, result: Any) -> Any:
        """Govern a tool's result after execution."""
        if isinstance(result, str):
            gov_result = self._govern_text(result, "tool_result")
            return gov_result.output
        return result


def govern_smol_run(
    tork: Optional[Tork] = None,
    api_key: Optional[str] = None,
    policy_version: str = "1.0.0",
    agent_id: str = "smolagents-run",
    govern_input: bool = True,
    govern_output: bool = True,
) -> Callable:
    """
    Decorator for agent.run() calls. Governs task description and agent output.

    Example:
        >>> from tork_governance.adapters.smolagents import govern_smol_run
        >>>
        >>> @govern_smol_run()
        ... def ask_agent(task: str) -> str:
        ...     return agent.run(task)
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
                output_text = _extract_smol_content(output) or str(output)
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


def govern_smol_tool(
    tork: Optional[Tork] = None,
    api_key: Optional[str] = None,
    policy_version: str = "1.0.0",
    agent_id: str = "smolagents-tool",
    govern_input: bool = True,
    govern_output: bool = True,
) -> Callable:
    """
    Decorator for Smolagents tool functions. Governs tool inputs and outputs.

    Example:
        >>> from tork_governance.adapters.smolagents import govern_smol_tool
        >>>
        >>> @govern_smol_tool()
        ... def web_search(query: str) -> str:
        ...     return search_engine.search(query)
    """
    _tork = tork or Tork(api_key=api_key, policy_version=policy_version)
    _receipts: List[Dict] = []

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
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
