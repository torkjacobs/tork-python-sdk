"""
Agno (ex-Phidata) Integration for Tork Governance

Provides middleware and wrappers for the Agno high-performance multi-agent runtime.
Agno agents have tools, memory, and structured outputs.
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


def _extract_agno_content(response: Any) -> Optional[str]:
    """Extract text content from an Agno response object."""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        if "content" in response:
            return str(response["content"])
        if "message" in response:
            return str(response["message"])
        if "text" in response:
            return str(response["text"])
    if hasattr(response, "content"):
        return str(response.content)
    if hasattr(response, "message"):
        return str(response.message)
    return None


class TorkAgnoAgent:
    """
    Wrapper class that governs an Agno Agent's input/output.

    Example:
        >>> from tork_governance.adapters.agno import TorkAgnoAgent
        >>> from agno.agent import Agent
        >>>
        >>> agent = Agent(model=OpenAIChat(id="gpt-4o"))
        >>> governed = TorkAgnoAgent(agent)
        >>> response = governed.run("Tell me about user john@example.com")
    """

    def __init__(
        self,
        agent: Any = None,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "agno-agent",
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

    def run(self, message: str, **kwargs) -> str:
        """Run the agent with governance applied to input and output."""
        if self.govern_input:
            input_result = self._govern_text(message, "input")
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Input blocked by governance: {input_result.receipt.receipt_id}")
            message = input_result.output

        if hasattr(self._agent, "run"):
            output = self._agent.run(message, **kwargs)
        else:
            output = f"Agent response to: {message}"

        output_text = _extract_agno_content(output) or str(output)

        if self.govern_output:
            output_result = self._govern_text(output_text, "output")
            return output_result.output

        return output_text

    async def run_async(self, message: str, **kwargs) -> str:
        """Async version of run with governance applied."""
        if self.govern_input:
            input_result = self._govern_text(message, "input")
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Input blocked by governance: {input_result.receipt.receipt_id}")
            message = input_result.output

        if hasattr(self._agent, "arun"):
            output = await self._agent.arun(message, **kwargs)
        elif hasattr(self._agent, "run_async"):
            output = await self._agent.run_async(message, **kwargs)
        elif hasattr(self._agent, "run"):
            output = self._agent.run(message, **kwargs)
        else:
            output = f"Agent response to: {message}"

        output_text = _extract_agno_content(output) or str(output)

        if self.govern_output:
            output_result = self._govern_text(output_text, "output")
            return output_result.output

        return output_text

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self._govern_text(text, "govern").output


class TorkAgnoTeam:
    """
    Wrapper for Agno multi-agent teams. Governs inter-agent communication.

    Example:
        >>> from tork_governance.adapters.agno import TorkAgnoTeam
        >>> from agno.agent import Agent
        >>> from agno.team import Team
        >>>
        >>> team = Team(agents=[agent1, agent2])
        >>> governed = TorkAgnoTeam(team)
        >>> result = governed.run("Research and write a report")
    """

    def __init__(
        self,
        team: Any = None,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "agno-team",
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self._team = team
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.agent_id = agent_id
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.receipts: List[Dict] = []

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped team."""
        return getattr(self._team, name)

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

    def run(self, message: str, **kwargs) -> str:
        """Run the team with governance applied to input and final output."""
        if self.govern_input:
            input_result = self._govern_text(message, "team_input")
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Team input blocked: {input_result.receipt.receipt_id}")
            message = input_result.output

        if hasattr(self._team, "run"):
            output = self._team.run(message, **kwargs)
        else:
            output = f"Team response to: {message}"

        output_text = _extract_agno_content(output) or str(output)

        if self.govern_output:
            output_result = self._govern_text(output_text, "team_output")
            return output_result.output

        return output_text

    async def run_async(self, message: str, **kwargs) -> str:
        """Async version of run with governance applied."""
        if self.govern_input:
            input_result = self._govern_text(message, "team_input")
            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Team input blocked: {input_result.receipt.receipt_id}")
            message = input_result.output

        if hasattr(self._team, "arun"):
            output = await self._team.arun(message, **kwargs)
        elif hasattr(self._team, "run"):
            output = self._team.run(message, **kwargs)
        else:
            output = f"Team response to: {message}"

        output_text = _extract_agno_content(output) or str(output)

        if self.govern_output:
            output_result = self._govern_text(output_text, "team_output")
            return output_result.output

        return output_text

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self._govern_text(text, "govern").output


def govern_agno_tool(
    tork: Optional[Tork] = None,
    api_key: Optional[str] = None,
    policy_version: str = "1.0.0",
    agent_id: str = "agno-tool",
    govern_input: bool = True,
    govern_output: bool = True,
) -> Callable:
    """
    Decorator for Agno tool functions. Governs tool inputs and outputs.

    Example:
        >>> from tork_governance.adapters.agno import govern_agno_tool
        >>>
        >>> @govern_agno_tool()
        ... def search_database(query: str) -> str:
        ...     return db.search(query)
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


def govern_agno_run(
    tork: Optional[Tork] = None,
    api_key: Optional[str] = None,
    policy_version: str = "1.0.0",
    agent_id: str = "agno-run",
    govern_input: bool = True,
    govern_output: bool = True,
) -> Callable:
    """
    Decorator for agent.run() calls. Governs user message and agent response.

    Example:
        >>> from tork_governance.adapters.agno import govern_agno_run
        >>>
        >>> @govern_agno_run()
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
                output_text = _extract_agno_content(output) or str(output)
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
