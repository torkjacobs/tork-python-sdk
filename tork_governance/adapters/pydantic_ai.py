"""
Pydantic AI adapter for Tork Governance.

Provides middleware and agent wrappers for Pydantic AI.
"""

from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction

T = TypeVar("T")


class TorkPydanticAIMiddleware:
    """
    Middleware for Pydantic AI agents.

    Example:
        >>> from tork_governance.adapters.pydantic_ai import TorkPydanticAIMiddleware
        >>> from pydantic_ai import Agent
        >>>
        >>> agent = Agent("openai:gpt-4")
        >>> middleware = TorkPydanticAIMiddleware()
        >>> governed_agent = middleware.wrap_agent(agent)
        >>>
        >>> result = await governed_agent.run("Process user data")
    """

    def __init__(self, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def wrap_agent(self, agent: Any) -> Any:
        """
        Wrap a Pydantic AI agent with governance.

        Args:
            agent: Pydantic AI Agent instance

        Returns:
            Governed agent
        """
        original_run = agent.run
        original_run_sync = getattr(agent, "run_sync", None)
        tork = self.tork
        receipts = self.receipts

        async def governed_run(prompt: str, *args, **kwargs):
            # Govern input
            input_result = tork.govern(prompt)
            receipts.append({
                "type": "agent_input",
                "receipt_id": input_result.receipt.receipt_id,
                "action": input_result.action.value,
                "has_pii": input_result.pii.has_pii
            })

            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Input blocked: {input_result.receipt.receipt_id}")

            # Run agent
            result = await original_run(input_result.output, *args, **kwargs)

            # Govern output
            if hasattr(result, "data") and isinstance(result.data, str):
                output_result = tork.govern(result.data)
                result.data = output_result.output
                receipts.append({
                    "type": "agent_output",
                    "receipt_id": output_result.receipt.receipt_id
                })

            return result

        def governed_run_sync(prompt: str, *args, **kwargs):
            # Govern input
            input_result = tork.govern(prompt)
            receipts.append({
                "type": "agent_input_sync",
                "receipt_id": input_result.receipt.receipt_id
            })

            if input_result.action == GovernanceAction.DENY:
                raise ValueError(f"Input blocked: {input_result.receipt.receipt_id}")

            # Run agent
            result = original_run_sync(input_result.output, *args, **kwargs)

            # Govern output
            if hasattr(result, "data") and isinstance(result.data, str):
                output_result = tork.govern(result.data)
                result.data = output_result.output

            return result

        agent.run = governed_run
        if original_run_sync:
            agent.run_sync = governed_run_sync

        return agent

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkPydanticAITool:
    """
    Wrapper for Pydantic AI tools with governance.

    Example:
        >>> from tork_governance.adapters.pydantic_ai import TorkPydanticAITool
        >>>
        >>> tool_wrapper = TorkPydanticAITool()
        >>>
        >>> @tool_wrapper.governed_tool
        >>> def search(query: str) -> str:
        >>>     return f"Results for: {query}"
    """

    def __init__(self, tork: Optional[Tork] = None):
        self.tork = tork or Tork()
        self.receipts: List[Dict] = []

    def governed_tool(self, func: Callable) -> Callable:
        """Decorator to wrap tools with governance."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Govern string arguments
            governed_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    governed_kwargs[key] = result.output
                    self.receipts.append({
                        "type": "tool_input",
                        "argument": key,
                        "receipt_id": result.receipt.receipt_id
                    })
                else:
                    governed_kwargs[key] = value

            # Execute tool
            output = func(*args, **governed_kwargs)

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

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkAgentDependency:
    """
    Pydantic AI dependency with governance.

    Use as a dependency in Pydantic AI agents.

    Example:
        >>> from pydantic_ai import Agent
        >>> from tork_governance.adapters.pydantic_ai import TorkAgentDependency
        >>>
        >>> agent = Agent("openai:gpt-4", deps_type=TorkAgentDependency)
        >>>
        >>> @agent.tool
        >>> def process(ctx: RunContext[TorkAgentDependency], data: str) -> str:
        >>>     governed = ctx.deps.govern(data)
        >>>     return f"Processed: {governed}"
    """

    def __init__(self, tork: Optional[Tork] = None):
        self.tork = tork or Tork()
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text and return output."""
        result = self.tork.govern(text)
        self.receipts.append({
            "type": "dependency_govern",
            "receipt_id": result.receipt.receipt_id,
            "has_pii": result.pii.has_pii
        })
        return result.output

    def check_pii(self, text: str) -> bool:
        """Check if text contains PII."""
        result = self.tork.govern(text)
        return result.pii.has_pii

    def get_result(self, text: str) -> GovernanceResult:
        """Get full governance result."""
        return self.tork.govern(text)
