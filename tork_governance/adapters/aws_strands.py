"""
AWS Strands Agents Integration for Tork Governance

Provides middleware and wrappers for Amazon's Strands Agents framework
for building agents on AWS Bedrock.
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


def _extract_strands_content(response: Any) -> Optional[str]:
    """Extract text content from a Strands agent response."""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        if "output" in response:
            content = response["output"]
            if isinstance(content, str):
                return content
            if isinstance(content, dict) and "text" in content:
                return content["text"]
        if "content" in response:
            return str(response["content"])
        if "message" in response:
            msg = response["message"]
            if isinstance(msg, str):
                return msg
            if isinstance(msg, dict) and "content" in msg:
                return str(msg["content"])
    if hasattr(response, "output"):
        return str(response.output)
    if hasattr(response, "content"):
        return str(response.content)
    return None


class TorkStrandsAgent:
    """
    Wrapper class governing an AWS Strands agent.

    Example:
        >>> from tork_governance.adapters.aws_strands import TorkStrandsAgent
        >>> from strands import Agent
        >>>
        >>> agent = Agent()
        >>> governed = TorkStrandsAgent(agent)
        >>> response = governed.invoke("Tell me about user john@example.com")
    """

    def __init__(
        self,
        agent: Any = None,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "strands-agent",
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

    def invoke(self, prompt: str, **kwargs) -> str:
        """Invoke the agent with governance applied to input and output."""
        if self.govern_input:
            input_result = self._govern_text(prompt, "input")
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Input blocked by governance: {input_result.receipt.receipt_id}")
            prompt = input_result.output

        if hasattr(self._agent, "invoke"):
            output = self._agent.invoke(prompt, **kwargs)
        elif hasattr(self._agent, "__call__"):
            output = self._agent(prompt, **kwargs)
        else:
            output = f"Agent response to: {prompt}"

        output_text = _extract_strands_content(output) or str(output)

        if self.govern_output:
            output_result = self._govern_text(output_text, "output")
            return output_result.output

        return output_text

    def __call__(self, prompt: str, **kwargs) -> str:
        """Allow calling the governed agent directly."""
        return self.invoke(prompt, **kwargs)

    def stream(self, prompt: str, **kwargs):
        """Stream the agent response with governance on each chunk."""
        if self.govern_input:
            input_result = self._govern_text(prompt, "stream_input")
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Input blocked by governance: {input_result.receipt.receipt_id}")
            prompt = input_result.output

        if hasattr(self._agent, "stream"):
            stream_iter = self._agent.stream(prompt, **kwargs)
        elif hasattr(self._agent, "invoke"):
            stream_iter = [self._agent.invoke(prompt, **kwargs)]
        else:
            stream_iter = [f"Agent response to: {prompt}"]

        for chunk in stream_iter:
            if self.govern_output:
                chunk_text = _extract_strands_content(chunk) or str(chunk)
                result = self._govern_text(chunk_text, "stream_output")
                yield result.output
            else:
                yield chunk

    async def invoke_async(self, prompt: str, **kwargs) -> str:
        """Async version of invoke with governance applied."""
        if self.govern_input:
            input_result = self._govern_text(prompt, "input")
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Input blocked by governance: {input_result.receipt.receipt_id}")
            prompt = input_result.output

        if hasattr(self._agent, "invoke_async"):
            output = await self._agent.invoke_async(prompt, **kwargs)
        elif hasattr(self._agent, "invoke"):
            output = self._agent.invoke(prompt, **kwargs)
        else:
            output = f"Agent response to: {prompt}"

        output_text = _extract_strands_content(output) or str(output)

        if self.govern_output:
            output_result = self._govern_text(output_text, "output")
            return output_result.output

        return output_text

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self._govern_text(text, "govern").output


class TorkStrandsToolWrapper:
    """
    Wraps Strands agent tools with governance.

    Example:
        >>> from tork_governance.adapters.aws_strands import TorkStrandsToolWrapper
        >>>
        >>> wrapper = TorkStrandsToolWrapper()
        >>> governed_tool = wrapper.wrap(my_tool_function)
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "strands-tool",
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

    def govern_tool_input(self, tool_name: str, tool_input: Dict) -> Dict:
        """Govern a tool's input arguments."""
        governed = {}
        for key, value in tool_input.items():
            if isinstance(value, str):
                result = self._govern_text(value, "tool_input")
                if result.action == GovernanceAction.DENY:
                    raise ValueError(f"Tool input blocked for {tool_name}: {result.receipt.receipt_id}")
                governed[key] = result.output
            else:
                governed[key] = value
        return governed

    def govern_tool_output(self, result: Any) -> Any:
        """Govern a tool's output."""
        if isinstance(result, str):
            gov_result = self._govern_text(result, "tool_output")
            return gov_result.output
        return result


def govern_strands_invoke(
    tork: Optional[Tork] = None,
    api_key: Optional[str] = None,
    policy_version: str = "1.0.0",
    agent_id: str = "strands-invoke",
    govern_input: bool = True,
    govern_output: bool = True,
) -> Callable:
    """
    Decorator for agent invocations. Governs prompt and response.

    Example:
        >>> from tork_governance.adapters.aws_strands import govern_strands_invoke
        >>>
        >>> @govern_strands_invoke()
        ... def ask_agent(prompt: str) -> str:
        ...     return agent(prompt)
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
                    'type': 'invoke_input',
                    'agent_id': agent_id,
                    'receipt_id': result.receipt.receipt_id,
                    'action': result.action.value,
                })
                if result.action == GovernanceAction.DENY:
                    raise ValueError(f"Invoke input blocked: {result.receipt.receipt_id}")
                governed_args[0] = result.output

            output = func(*governed_args, **kwargs)

            if govern_output:
                output_text = _extract_strands_content(output) or str(output)
                result = _tork.govern(output_text)
                _receipts.append({
                    'type': 'invoke_output',
                    'agent_id': agent_id,
                    'receipt_id': result.receipt.receipt_id,
                    'action': result.action.value,
                })
                return result.output

            return output

        wrapper.receipts = _receipts
        return wrapper
    return decorator


def govern_strands_tool(
    tork: Optional[Tork] = None,
    api_key: Optional[str] = None,
    policy_version: str = "1.0.0",
    agent_id: str = "strands-tool",
    govern_input: bool = True,
    govern_output: bool = True,
) -> Callable:
    """
    Decorator for Strands tool functions. Governs tool inputs and outputs.

    Example:
        >>> from tork_governance.adapters.aws_strands import govern_strands_tool
        >>>
        >>> @govern_strands_tool()
        ... def query_database(sql: str) -> str:
        ...     return db.execute(sql)
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
