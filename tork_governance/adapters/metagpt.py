"""
MetaGPT adapter for Tork Governance.

Provides role, team, and action wrappers for MetaGPT multi-agent development.
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkMetaGPTRole:
    """
    Wrapper for MetaGPT roles with governance.

    Example:
        >>> from tork_governance.adapters.metagpt import TorkMetaGPTRole
        >>> from metagpt.roles import Engineer
        >>>
        >>> engineer = Engineer()
        >>> governed_engineer = TorkMetaGPTRole(engineer)
        >>>
        >>> result = await governed_engineer.run("Implement user auth for test@email.com")
    """

    def __init__(self, role: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.role = role
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def govern_message(self, text: str) -> str:
        """Govern message text - standalone method."""
        return self.govern(text)

    async def run(self, message: str, **kwargs) -> Any:
        """Run role with governed message."""
        # Govern input
        input_result = self.tork.govern(message)
        self.receipts.append({
            "type": "role_input",
            "role": getattr(self.role, 'name', 'unknown'),
            "receipt_id": input_result.receipt.receipt_id,
            "action": input_result.action.value
        })

        if input_result.action == GovernanceAction.DENY:
            raise ValueError(f"Role input blocked: {input_result.receipt.receipt_id}")

        # Run role
        output = await self.role.run(input_result.output, **kwargs)

        # Govern output
        if isinstance(output, str):
            output_result = self.tork.govern(output)
            self.receipts.append({
                "type": "role_output",
                "receipt_id": output_result.receipt.receipt_id
            })
            return output_result.output
        elif hasattr(output, 'content'):
            content = str(output.content)
            output_result = self.tork.govern(content)
            output.content = output_result.output
            return output

        return output

    def set_goal(self, goal: str) -> None:
        """Set governed goal."""
        result = self.tork.govern(goal)
        self.receipts.append({
            "type": "role_goal",
            "receipt_id": result.receipt.receipt_id
        })
        if hasattr(self.role, 'set_goal'):
            self.role.set_goal(result.output)
        elif hasattr(self.role, 'goal'):
            self.role.goal = result.output

    def add_action(self, action: Any) -> None:
        """Add governed action to role."""
        governed_action = TorkMetaGPTAction(action, tork=self.tork)
        self.role.add_action(governed_action.action)

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkMetaGPTTeam:
    """
    Wrapper for MetaGPT teams with governance.

    Example:
        >>> from tork_governance.adapters.metagpt import TorkMetaGPTTeam
        >>> from metagpt.team import Team
        >>>
        >>> team = Team()
        >>> governed_team = TorkMetaGPTTeam(team)
        >>>
        >>> result = await governed_team.run("Build a web app")
    """

    def __init__(self, team: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.team = team
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    async def run(self, idea: str, **kwargs) -> Any:
        """Run team with governed idea."""
        # Govern input
        input_result = self.tork.govern(idea)
        self.receipts.append({
            "type": "team_idea",
            "receipt_id": input_result.receipt.receipt_id,
            "action": input_result.action.value
        })

        if input_result.action == GovernanceAction.DENY:
            raise ValueError(f"Team idea blocked: {input_result.receipt.receipt_id}")

        # Run team
        output = await self.team.run(input_result.output, **kwargs)

        # Govern outputs
        if isinstance(output, str):
            output_result = self.tork.govern(output)
            self.receipts.append({
                "type": "team_output",
                "receipt_id": output_result.receipt.receipt_id
            })
            return output_result.output
        elif isinstance(output, list):
            governed_outputs = []
            for item in output:
                if isinstance(item, str):
                    result = self.tork.govern(item)
                    governed_outputs.append(result.output)
                else:
                    governed_outputs.append(item)
            return governed_outputs

        return output

    def hire(self, roles: List[Any]) -> None:
        """Hire governed roles."""
        governed_roles = []
        for role in roles:
            governed_role = TorkMetaGPTRole(role, tork=self.tork)
            governed_roles.append(governed_role.role)
        self.team.hire(governed_roles)

    def invest(self, investment: str) -> None:
        """Set governed investment description."""
        result = self.tork.govern(investment)
        self.receipts.append({
            "type": "team_investment",
            "receipt_id": result.receipt.receipt_id
        })
        self.team.invest(result.output)

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkMetaGPTAction:
    """
    Wrapper for MetaGPT actions with governance.

    Example:
        >>> from tork_governance.adapters.metagpt import TorkMetaGPTAction
        >>>
        >>> action = WriteCode()
        >>> governed_action = TorkMetaGPTAction(action)
    """

    def __init__(self, action: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.action = action
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    async def run(self, *args, **kwargs) -> Any:
        """Run action with governance."""
        # Govern string args
        governed_args = []
        for arg in args:
            if isinstance(arg, str):
                result = self.tork.govern(arg)
                governed_args.append(result.output)
                self.receipts.append({
                    "type": "action_input_arg",
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
                    "type": "action_input_kwarg",
                    "key": key,
                    "receipt_id": result.receipt.receipt_id
                })
            else:
                governed_kwargs[key] = value

        # Execute action
        output = await self.action.run(*governed_args, **governed_kwargs)

        # Govern output
        if isinstance(output, str):
            output_result = self.tork.govern(output)
            self.receipts.append({
                "type": "action_output",
                "receipt_id": output_result.receipt.receipt_id
            })
            return output_result.output

        return output

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkMetaGPTEnvironment:
    """Wrapper for MetaGPT environment with governance."""

    def __init__(self, environment: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.environment = environment
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def publish_message(self, message: Any) -> None:
        """Publish governed message."""
        if hasattr(message, 'content') and isinstance(message.content, str):
            result = self.tork.govern(message.content)
            message.content = result.output
            self.receipts.append({
                "type": "env_message",
                "receipt_id": result.receipt.receipt_id
            })
        self.environment.publish_message(message)

    def get_receipts(self) -> List[Dict]:
        return self.receipts
