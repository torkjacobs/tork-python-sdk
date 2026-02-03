"""
AgentGPT adapter for Tork Governance.

Provides agent, task, and goal wrappers for AgentGPT browser agents.
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkAgentGPTAgent:
    """
    Wrapper for AgentGPT agents with governance.

    Example:
        >>> from tork_governance.adapters.agentgpt import TorkAgentGPTAgent
        >>>
        >>> agent = AgentGPTAgent(name="researcher")
        >>> governed_agent = TorkAgentGPTAgent(agent)
        >>>
        >>> result = governed_agent.run("Find contact info for user@example.com")
    """

    def __init__(self, agent: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.agent = agent
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def govern_goal(self, text: str) -> str:
        """Govern goal text - standalone method."""
        return self.govern(text)

    def run(self, goal: str, **kwargs) -> Any:
        """Run agent with governed goal."""
        # Govern goal
        input_result = self.tork.govern(goal)
        self.receipts.append({
            "type": "agent_goal",
            "receipt_id": input_result.receipt.receipt_id,
            "action": input_result.action.value
        })

        if input_result.action == GovernanceAction.DENY:
            raise ValueError(f"Goal blocked: {input_result.receipt.receipt_id}")

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
        elif isinstance(output, list):
            return self._govern_list(output)

        return output

    async def arun(self, goal: str, **kwargs) -> Any:
        """Async agent execution."""
        input_result = self.tork.govern(goal)

        if input_result.action == GovernanceAction.DENY:
            raise ValueError(f"Goal blocked: {input_result.receipt.receipt_id}")

        output = await self.agent.arun(input_result.output, **kwargs)

        if isinstance(output, str):
            output_result = self.tork.govern(output)
            return output_result.output

        return output

    def add_task(self, task: str) -> None:
        """Add governed task."""
        result = self.tork.govern(task)
        self.receipts.append({
            "type": "add_task",
            "receipt_id": result.receipt.receipt_id
        })
        if hasattr(self.agent, 'add_task'):
            self.agent.add_task(result.output)

    def _govern_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Govern dictionary values."""
        governed = {}
        for key, value in data.items():
            if isinstance(value, str):
                result = self.tork.govern(value)
                governed[key] = result.output
                self.receipts.append({
                    "type": "dict_value",
                    "key": key,
                    "receipt_id": result.receipt.receipt_id
                })
            elif isinstance(value, dict):
                governed[key] = self._govern_dict(value)
            elif isinstance(value, list):
                governed[key] = self._govern_list(value)
            else:
                governed[key] = value
        return governed

    def _govern_list(self, items: List[Any]) -> List[Any]:
        """Govern list items."""
        governed = []
        for item in items:
            if isinstance(item, str):
                result = self.tork.govern(item)
                governed.append(result.output)
            elif isinstance(item, dict):
                governed.append(self._govern_dict(item))
            else:
                governed.append(item)
        return governed

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkAgentGPTTask:
    """
    Task wrapper for AgentGPT with governance.

    Example:
        >>> from tork_governance.adapters.agentgpt import TorkAgentGPTTask
        >>>
        >>> task = TorkAgentGPTTask()
        >>> result = task.create("Research user@email.com")
    """

    def __init__(self, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []
        self.tasks: List[Dict] = []
        self._task_counter = 0

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def create(self, description: str, parent_id: Optional[int] = None) -> Dict:
        """Create governed task."""
        result = self.tork.govern(description)
        self.receipts.append({
            "type": "task_create",
            "receipt_id": result.receipt.receipt_id,
            "action": result.action.value
        })

        if result.action == GovernanceAction.DENY:
            raise ValueError(f"Task blocked: {result.receipt.receipt_id}")

        self._task_counter += 1
        task = {
            "id": self._task_counter,
            "description": result.output,
            "parent_id": parent_id,
            "status": "pending",
            "subtasks": [],
            "receipt_id": result.receipt.receipt_id
        }
        self.tasks.append(task)
        return task

    def complete(self, task_id: int, result_text: str) -> Dict:
        """Complete task with governed result."""
        result = self.tork.govern(result_text)
        self.receipts.append({
            "type": "task_complete",
            "task_id": task_id,
            "receipt_id": result.receipt.receipt_id
        })

        for task in self.tasks:
            if task["id"] == task_id:
                task["status"] = "completed"
                task["result"] = result.output
                return task

        raise ValueError(f"Task {task_id} not found")

    def add_subtask(self, parent_id: int, description: str) -> Dict:
        """Add governed subtask."""
        subtask = self.create(description, parent_id=parent_id)

        for task in self.tasks:
            if task["id"] == parent_id:
                task["subtasks"].append(subtask["id"])
                break

        return subtask

    def get_pending(self) -> List[Dict]:
        """Get pending tasks."""
        return [t for t in self.tasks if t["status"] == "pending"]

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkAgentGPTGoal:
    """
    Goal wrapper for AgentGPT with governance.

    Example:
        >>> from tork_governance.adapters.agentgpt import TorkAgentGPTGoal
        >>>
        >>> goal_manager = TorkAgentGPTGoal()
        >>> goal = goal_manager.set_goal("Build a web scraper")
    """

    def __init__(self, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []
        self.current_goal: Optional[Dict] = None
        self.goal_history: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def set_goal(self, goal: str) -> Dict:
        """Set governed goal."""
        result = self.tork.govern(goal)
        self.receipts.append({
            "type": "goal_set",
            "receipt_id": result.receipt.receipt_id,
            "action": result.action.value
        })

        if result.action == GovernanceAction.DENY:
            raise ValueError(f"Goal blocked: {result.receipt.receipt_id}")

        goal_obj = {
            "description": result.output,
            "status": "active",
            "receipt_id": result.receipt.receipt_id,
            "tasks_completed": 0
        }

        if self.current_goal:
            self.current_goal["status"] = "superseded"
            self.goal_history.append(self.current_goal)

        self.current_goal = goal_obj
        return goal_obj

    def update_progress(self, tasks_completed: int) -> None:
        """Update goal progress."""
        if self.current_goal:
            self.current_goal["tasks_completed"] = tasks_completed

    def complete_goal(self, summary: str) -> Dict:
        """Complete goal with governed summary."""
        if not self.current_goal:
            raise ValueError("No active goal")

        result = self.tork.govern(summary)
        self.receipts.append({
            "type": "goal_complete",
            "receipt_id": result.receipt.receipt_id
        })

        self.current_goal["status"] = "completed"
        self.current_goal["summary"] = result.output
        self.goal_history.append(self.current_goal)

        completed = self.current_goal
        self.current_goal = None
        return completed

    def get_current_goal(self) -> Optional[Dict]:
        """Get current goal."""
        return self.current_goal

    def get_history(self) -> List[Dict]:
        """Get goal history."""
        return self.goal_history.copy()

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkAgentGPTBrowser:
    """Browser automation wrapper with governance."""

    def __init__(self, browser: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.browser = browser
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def navigate(self, url: str) -> Any:
        """Navigate with governed URL logging."""
        result = self.tork.govern(url)
        self.receipts.append({
            "type": "browser_navigate",
            "receipt_id": result.receipt.receipt_id
        })
        if self.browser:
            return self.browser.navigate(url)
        return {"url": url, "governed": True}

    def extract_text(self) -> str:
        """Extract and govern page text."""
        if self.browser:
            text = self.browser.extract_text()
        else:
            text = ""

        result = self.tork.govern(text)
        self.receipts.append({
            "type": "browser_extract",
            "receipt_id": result.receipt.receipt_id
        })
        return result.output

    def get_receipts(self) -> List[Dict]:
        return self.receipts
