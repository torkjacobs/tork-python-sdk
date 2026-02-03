"""
CrewAI Integration for Tork Governance

Provides middleware and wrappers for CrewAI agents and crews.
"""

from typing import Any, Dict, List, Optional
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkCrewAIMiddleware:
    """
    Middleware for CrewAI that applies Tork governance to agent interactions.

    Example:
        >>> from tork_governance.adapters.crewai import TorkCrewAIMiddleware
        >>> from crewai import Agent, Task, Crew
        >>>
        >>> middleware = TorkCrewAIMiddleware()
        >>> researcher = Agent(role="Researcher", goal="Find info")
        >>> governed_researcher = middleware.wrap_agent(researcher)
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "crewai-agent"
    ):
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.agent_id = agent_id
        self.receipts: List[Dict] = []

    def wrap_agent(self, agent: Any) -> "GovernedAgent":
        """Wrap a CrewAI agent with governance controls."""
        return GovernedAgent(agent, self)

    def wrap_crew(self, crew: Any) -> "GovernedCrew":
        """Wrap an entire CrewAI crew with governance controls."""
        return GovernedCrew(crew, self)

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


class GovernedAgent:
    """
    Wrapper for a CrewAI Agent that applies governance to all interactions.

    Example:
        >>> from tork_governance.adapters.crewai import GovernedAgent, TorkCrewAIMiddleware
        >>> from crewai import Agent, Task
        >>>
        >>> middleware = TorkCrewAIMiddleware()
        >>> agent = Agent(role="Writer", goal="Write content")
        >>> governed = GovernedAgent(agent, middleware)
        >>> task = Task(description="Write a blog post", agent=governed)
    """

    def __init__(self, agent: Any = None, middleware: TorkCrewAIMiddleware = None, api_key: Optional[str] = None):
        self._agent = agent
        self._middleware = middleware or TorkCrewAIMiddleware(api_key=api_key)

    def govern_input(self, text: str) -> str:
        """Govern input text - standalone method."""
        return self._middleware.govern_input(text)

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped agent."""
        return getattr(self._agent, name)

    def execute_task(self, task: Any, context: Optional[str] = None, tools: Optional[List] = None) -> str:
        """Execute a task with governance applied."""
        # Govern task description
        task_result = self._middleware.process_input(task.description)
        if task_result.action == GovernanceAction.DENY:
            raise ValueError(f"Task blocked by governance: {task_result.receipt.receipt_id}")

        # Execute the original task
        try:
            if hasattr(self._agent, 'execute_task'):
                output = self._agent.execute_task(task, context, tools)
            else:
                output = str(task.description)  # Fallback for testing
        except Exception as e:
            raise e

        # Govern output
        output_result = self._middleware.process_output(output)
        return output_result.output


class GovernedCrew:
    """
    Wrapper for a CrewAI Crew that applies governance to the entire workflow.

    Example:
        >>> from tork_governance.adapters.crewai import GovernedCrew, TorkCrewAIMiddleware
        >>> from crewai import Agent, Task, Crew
        >>>
        >>> middleware = TorkCrewAIMiddleware()
        >>> crew = Crew(agents=[...], tasks=[...])
        >>> governed = GovernedCrew(crew, middleware)
        >>> result = governed.kickoff()
    """

    def __init__(self, crew: Any = None, middleware: TorkCrewAIMiddleware = None, api_key: Optional[str] = None):
        self._crew = crew
        self._middleware = middleware or TorkCrewAIMiddleware(api_key=api_key)

    def govern_input(self, text: str) -> str:
        """Govern input text - standalone method."""
        return self._middleware.govern_input(text)

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped crew."""
        return getattr(self._crew, name)

    def kickoff(self, inputs: Optional[Dict] = None) -> str:
        """Kickoff the crew with governance applied to final output."""
        # Govern inputs if provided
        if inputs:
            for key, value in inputs.items():
                if isinstance(value, str):
                    result = self._middleware.process_input(value)
                    if result.action == GovernanceAction.DENY:
                        raise ValueError(f"Input blocked: {result.receipt.receipt_id}")
                    inputs[key] = result.output

        # Execute crew
        try:
            if hasattr(self._crew, 'kickoff'):
                output = self._crew.kickoff(inputs)
            else:
                output = "Crew execution simulated"  # Fallback for testing
        except Exception as e:
            raise e

        # Govern final output
        output_str = str(output)
        output_result = self._middleware.process_output(output_str)
        return output_result.output
