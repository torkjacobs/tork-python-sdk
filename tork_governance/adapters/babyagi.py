"""
BabyAGI adapter for Tork Governance.

Provides agent and task manager wrappers for BabyAGI task-driven agents.
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkBabyAGIAgent:
    """
    Wrapper for BabyAGI agents with governance.

    Example:
        >>> from tork_governance.adapters.babyagi import TorkBabyAGIAgent
        >>>
        >>> agent = BabyAGI(objective="Research AI")
        >>> governed_agent = TorkBabyAGIAgent(agent)
        >>>
        >>> result = governed_agent.run("Find info about user@example.com")
    """

    def __init__(self, agent: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.agent = agent
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def govern_objective(self, text: str) -> str:
        """Govern objective text - standalone method."""
        return self.govern(text)

    def run(self, objective: Optional[str] = None, **kwargs) -> Any:
        """Run agent with governed objective."""
        # Govern objective if provided
        if objective:
            input_result = self.tork.govern(objective)
            self.receipts.append({
                "type": "agent_objective",
                "receipt_id": input_result.receipt.receipt_id,
                "action": input_result.action.value
            })

            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Objective blocked: {input_result.receipt.receipt_id}")

            objective = input_result.output

        # Run agent
        output = self.agent.run(objective=objective, **kwargs)

        # Govern output
        if isinstance(output, str):
            output_result = self.tork.govern(output)
            self.receipts.append({
                "type": "agent_output",
                "receipt_id": output_result.receipt.receipt_id
            })
            return output_result.output
        elif isinstance(output, list):
            return self._govern_list(output)
        elif isinstance(output, dict):
            return self._govern_dict(output)

        return output

    def set_objective(self, objective: str) -> None:
        """Set governed objective."""
        result = self.tork.govern(objective)
        self.receipts.append({
            "type": "set_objective",
            "receipt_id": result.receipt.receipt_id
        })
        if hasattr(self.agent, 'set_objective'):
            self.agent.set_objective(result.output)
        elif hasattr(self.agent, 'objective'):
            self.agent.objective = result.output

    def add_task(self, task: str) -> None:
        """Add governed task."""
        result = self.tork.govern(task)
        self.receipts.append({
            "type": "add_task",
            "receipt_id": result.receipt.receipt_id
        })
        if hasattr(self.agent, 'add_task'):
            self.agent.add_task(result.output)

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

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkBabyAGITaskManager:
    """
    Task manager with governance for BabyAGI.

    Example:
        >>> from tork_governance.adapters.babyagi import TorkBabyAGITaskManager
        >>>
        >>> task_manager = TorkBabyAGITaskManager()
        >>> task_manager.create_task("Research user@email.com")
        >>> tasks = task_manager.get_tasks()
    """

    def __init__(self, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []
        self.tasks: List[Dict] = []
        self._task_counter = 0

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def create_task(self, description: str, priority: int = 0) -> Dict:
        """Create governed task."""
        result = self.tork.govern(description)
        self.receipts.append({
            "type": "task_create",
            "receipt_id": result.receipt.receipt_id,
            "action": result.action.value
        })

        if result.action == GovernanceAction.DENY:
            raise ValueError(f"Task creation blocked: {result.receipt.receipt_id}")

        self._task_counter += 1
        task = {
            "id": self._task_counter,
            "description": result.output,
            "priority": priority,
            "status": "pending",
            "receipt_id": result.receipt.receipt_id
        }
        self.tasks.append(task)
        return task

    def complete_task(self, task_id: int, result_text: str) -> Dict:
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

    def prioritize_tasks(self, objective: str) -> List[Dict]:
        """Reprioritize with governed objective."""
        result = self.tork.govern(objective)
        self.receipts.append({
            "type": "prioritize",
            "receipt_id": result.receipt.receipt_id
        })

        # Sort by priority (higher first)
        pending = [t for t in self.tasks if t["status"] == "pending"]
        return sorted(pending, key=lambda t: t["priority"], reverse=True)

    def get_next_task(self) -> Optional[Dict]:
        """Get highest priority pending task."""
        pending = [t for t in self.tasks if t["status"] == "pending"]
        if pending:
            return max(pending, key=lambda t: t["priority"])
        return None

    def get_tasks(self) -> List[Dict]:
        """Get all tasks."""
        return self.tasks.copy()

    def get_receipts(self) -> List[Dict]:
        return self.receipts


def governed_task(tork: Optional[Tork] = None):
    """
    Decorator for governed BabyAGI tasks.

    Example:
        >>> @governed_task()
        >>> def research_task(query: str) -> str:
        >>>     return search_web(query)
    """
    _tork = tork or Tork()
    receipts: List[Dict] = []

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Govern string args
            governed_args = []
            for arg in args:
                if isinstance(arg, str):
                    result = _tork.govern(arg)
                    governed_args.append(result.output)
                    receipts.append({
                        "type": "task_input_arg",
                        "receipt_id": result.receipt.receipt_id
                    })
                else:
                    governed_args.append(arg)

            # Govern string kwargs
            governed_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    result = _tork.govern(value)
                    governed_kwargs[key] = result.output
                    receipts.append({
                        "type": "task_input_kwarg",
                        "key": key,
                        "receipt_id": result.receipt.receipt_id
                    })
                else:
                    governed_kwargs[key] = value

            # Execute task
            output = func(*governed_args, **governed_kwargs)

            # Govern output
            if isinstance(output, str):
                result = _tork.govern(output)
                receipts.append({
                    "type": "task_output",
                    "receipt_id": result.receipt.receipt_id
                })
                return result.output

            return output

        wrapper.get_receipts = lambda: receipts
        return wrapper

    return decorator


class TorkBabyAGIMemory:
    """Memory manager with governance for BabyAGI."""

    def __init__(self, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []
        self.memories: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def add_memory(self, content: str, metadata: Optional[Dict] = None) -> Dict:
        """Add governed memory."""
        result = self.tork.govern(content)
        self.receipts.append({
            "type": "memory_add",
            "receipt_id": result.receipt.receipt_id
        })

        memory = {
            "content": result.output,
            "metadata": metadata or {},
            "receipt_id": result.receipt.receipt_id
        }
        self.memories.append(memory)
        return memory

    def search_memories(self, query: str) -> List[Dict]:
        """Search with governed query."""
        result = self.tork.govern(query)
        # Simple substring search for demo
        return [m for m in self.memories if result.output.lower() in m["content"].lower()]

    def get_receipts(self) -> List[Dict]:
        return self.receipts
