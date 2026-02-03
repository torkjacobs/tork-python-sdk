"""
SuperAGI adapter for Tork Governance.

Provides agent, tool, and workflow wrappers for SuperAGI autonomous agents.
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkSuperAGIAgent:
    """
    Wrapper for SuperAGI agents with governance.

    Example:
        >>> from tork_governance.adapters.superagi import TorkSuperAGIAgent
        >>>
        >>> agent = SuperAGIAgent(name="researcher", goals=["Find data"])
        >>> governed_agent = TorkSuperAGIAgent(agent)
        >>>
        >>> result = governed_agent.run("Research user@example.com")
    """

    def __init__(self, agent: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.agent = agent
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def govern_task(self, text: str) -> str:
        """Govern task text - standalone method."""
        return self.govern(text)

    def run(self, task: str, **kwargs) -> Any:
        """Run agent with governed task."""
        # Govern task input
        input_result = self.tork.govern(task)
        self.receipts.append({
            "type": "agent_task",
            "receipt_id": input_result.receipt.receipt_id,
            "action": input_result.action.value
        })

        if input_result.action == GovernanceAction.DENY:
            raise ValueError(f"Task blocked: {input_result.receipt.receipt_id}")

        # Run agent
        output = self.agent.run(input_result.output, **kwargs)

        # Govern output
        if isinstance(output, str):
            output_result = self.tork.govern(output)
            self.receipts.append({
                "type": "agent_output",
                "receipt_id": output_result.receipt.receipt_id
            })
            return output_result.output
        elif isinstance(output, dict):
            return self._govern_dict(output)

        return output

    async def arun(self, task: str, **kwargs) -> Any:
        """Async agent execution."""
        input_result = self.tork.govern(task)

        if input_result.action == GovernanceAction.DENY:
            raise ValueError(f"Task blocked: {input_result.receipt.receipt_id}")

        output = await self.agent.arun(input_result.output, **kwargs)

        if isinstance(output, str):
            output_result = self.tork.govern(output)
            return output_result.output

        return output

    def _govern_dict(self, data: Dict) -> Dict:
        """Govern dictionary values."""
        governed = {}
        for key, value in data.items():
            if isinstance(value, str):
                result = self.tork.govern(value)
                governed[key] = result.output
                self.receipts.append({
                    "type": "agent_dict_value",
                    "key": key,
                    "receipt_id": result.receipt.receipt_id
                })
            elif isinstance(value, dict):
                governed[key] = self._govern_dict(value)
            else:
                governed[key] = value
        return governed

    def set_goals(self, goals: List[str]) -> None:
        """Set governed goals."""
        governed_goals = []
        for goal in goals:
            result = self.tork.govern(goal)
            governed_goals.append(result.output)
            self.receipts.append({
                "type": "agent_goal",
                "receipt_id": result.receipt.receipt_id
            })
        self.agent.set_goals(governed_goals)

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkSuperAGITool:
    """
    Wrapper for SuperAGI tools with governance.

    Example:
        >>> from tork_governance.adapters.superagi import TorkSuperAGITool
        >>>
        >>> tool_wrapper = TorkSuperAGITool()
        >>>
        >>> @tool_wrapper.governed_tool
        >>> def web_search(query: str) -> str:
        >>>     return search_web(query)
    """

    def __init__(self, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def governed_tool(self, func: Callable) -> Callable:
        """Decorator for governed tools."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Govern string args
            governed_args = []
            for arg in args:
                if isinstance(arg, str):
                    result = self.tork.govern(arg)
                    governed_args.append(result.output)
                    self.receipts.append({
                        "type": "tool_input_arg",
                        "receipt_id": result.receipt.receipt_id
                    })
                else:
                    governed_args.append(arg)

            # Govern string kwargs
            governed_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    governed_kwargs[key] = result.output
                    self.receipts.append({
                        "type": "tool_input_kwarg",
                        "key": key,
                        "receipt_id": result.receipt.receipt_id
                    })
                else:
                    governed_kwargs[key] = value

            # Execute tool
            output = func(*governed_args, **governed_kwargs)

            # Govern output
            if isinstance(output, str):
                result = self.tork.govern(output)
                self.receipts.append({
                    "type": "tool_output",
                    "receipt_id": result.receipt.receipt_id
                })
                return result.output

            return output

        return wrapper

    def wrap_tool(self, tool: Any) -> Any:
        """Wrap existing tool with governance."""
        original_run = tool.run if hasattr(tool, 'run') else tool

        def governed_run(*args, **kwargs):
            # Govern inputs
            governed_args = [
                self.tork.govern(a).output if isinstance(a, str) else a
                for a in args
            ]
            governed_kwargs = {
                k: self.tork.govern(v).output if isinstance(v, str) else v
                for k, v in kwargs.items()
            }

            output = original_run(*governed_args, **governed_kwargs)

            if isinstance(output, str):
                return self.tork.govern(output).output
            return output

        if hasattr(tool, 'run'):
            tool.run = governed_run
            return tool
        return governed_run

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkSuperAGIWorkflow:
    """
    Wrapper for SuperAGI workflows with governance.

    Example:
        >>> from tork_governance.adapters.superagi import TorkSuperAGIWorkflow
        >>>
        >>> workflow = SuperAGIWorkflow(agents=[agent1, agent2])
        >>> governed_workflow = TorkSuperAGIWorkflow(workflow)
        >>>
        >>> result = governed_workflow.execute("Process user data")
    """

    def __init__(self, workflow: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.workflow = workflow
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def execute(self, input_data: str, **kwargs) -> Any:
        """Execute workflow with governance."""
        # Govern input
        input_result = self.tork.govern(input_data)
        self.receipts.append({
            "type": "workflow_input",
            "receipt_id": input_result.receipt.receipt_id,
            "action": input_result.action.value
        })

        if input_result.action == GovernanceAction.DENY:
            raise ValueError(f"Workflow input blocked: {input_result.receipt.receipt_id}")

        # Execute workflow
        output = self.workflow.execute(input_result.output, **kwargs)

        # Govern output
        if isinstance(output, str):
            output_result = self.tork.govern(output)
            self.receipts.append({
                "type": "workflow_output",
                "receipt_id": output_result.receipt.receipt_id
            })
            return output_result.output

        return output

    def add_agent(self, agent: Any) -> None:
        """Add governed agent to workflow."""
        governed_agent = TorkSuperAGIAgent(agent, tork=self.tork)
        self.workflow.add_agent(governed_agent.agent)

    def get_receipts(self) -> List[Dict]:
        return self.receipts
