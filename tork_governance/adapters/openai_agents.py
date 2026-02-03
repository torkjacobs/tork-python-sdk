"""
OpenAI Agents SDK Integration for Tork Governance

Provides middleware and wrappers for OpenAI's Agents SDK.
"""

from typing import Any, Dict, List, Optional, Callable
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkOpenAIAgentsMiddleware:
    """
    Middleware for OpenAI Agents SDK that applies Tork governance.

    Example:
        >>> from tork_governance.adapters.openai_agents import TorkOpenAIAgentsMiddleware
        >>> from openai_agents import Agent, Runner
        >>>
        >>> middleware = TorkOpenAIAgentsMiddleware()
        >>> agent = Agent(name="assistant", instructions="Help users")
        >>> governed_agent = middleware.wrap_agent(agent)
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "openai-agent"
    ):
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.agent_id = agent_id
        self.receipts: List[Dict] = []

    def wrap_agent(self, agent: Any) -> "GovernedOpenAIAgent":
        """Wrap an OpenAI Agent with governance controls."""
        return GovernedOpenAIAgent(agent, self)

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

    def create_governed_runner(self) -> "GovernedRunner":
        """Create a governed runner for executing agents."""
        return GovernedRunner(self)


class GovernedOpenAIAgent:
    """
    Wrapper for an OpenAI Agent that applies governance to all interactions.

    Example:
        >>> from tork_governance.adapters.openai_agents import GovernedOpenAIAgent
        >>> from openai_agents import Agent
        >>>
        >>> agent = Agent(name="assistant", instructions="Help users")
        >>> governed = GovernedOpenAIAgent(agent, middleware)
    """

    def __init__(self, agent: Any, middleware: TorkOpenAIAgentsMiddleware):
        self._agent = agent
        self._middleware = middleware

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped agent."""
        return getattr(self._agent, name)

    @property
    def wrapped_agent(self) -> Any:
        """Access the original wrapped agent."""
        return self._agent

    def run(self, user_input: str, **kwargs) -> str:
        """Run the agent with governance applied."""
        # Govern input
        input_result = self._middleware.process_input(user_input)
        if input_result.action == GovernanceAction.DENY:
            raise ValueError(f"Input blocked: {input_result.receipt.receipt_id}")

        governed_input = input_result.output

        # Run via original agent
        try:
            if hasattr(self._agent, 'run'):
                output = self._agent.run(governed_input, **kwargs)
            else:
                output = f"Agent response to: {governed_input}"  # Fallback
        except Exception as e:
            raise e

        # Govern output
        output_result = self._middleware.process_output(str(output))
        return output_result.output


class GovernedRunner:
    """
    Governed runner for OpenAI Agents SDK.

    Example:
        >>> from tork_governance.adapters.openai_agents import TorkOpenAIAgentsMiddleware
        >>>
        >>> middleware = TorkOpenAIAgentsMiddleware()
        >>> runner = middleware.create_governed_runner()
        >>> result = runner.run(agent, "Hello, help me with something")
    """

    def __init__(self, middleware: TorkOpenAIAgentsMiddleware):
        self._middleware = middleware

    def run(self, agent: Any, user_input: str, **kwargs) -> str:
        """Run an agent with governance applied."""
        # Wrap agent if not already wrapped
        if isinstance(agent, GovernedOpenAIAgent):
            governed_agent = agent
        else:
            governed_agent = GovernedOpenAIAgent(agent, self._middleware)

        return governed_agent.run(user_input, **kwargs)

    async def run_async(self, agent: Any, user_input: str, **kwargs) -> str:
        """Async run an agent with governance applied."""
        # Governance is synchronous (fast, CPU-bound)
        return self.run(agent, user_input, **kwargs)
