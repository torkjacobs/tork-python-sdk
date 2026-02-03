"""
Microsoft AutoGen Integration for Tork Governance

Provides middleware and wrappers for AutoGen conversational agents.
"""

from typing import Any, Dict, List, Optional, Callable
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkAutoGenMiddleware:
    """
    Middleware for AutoGen that applies Tork governance to agent conversations.

    Example:
        >>> from tork_governance.adapters.autogen import TorkAutoGenMiddleware
        >>> from autogen import AssistantAgent, UserProxyAgent
        >>>
        >>> middleware = TorkAutoGenMiddleware()
        >>> assistant = AssistantAgent("assistant", llm_config={...})
        >>> governed_assistant = middleware.wrap_agent(assistant)
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        agent_id: str = "autogen-agent"
    ):
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.agent_id = agent_id
        self.receipts: List[Dict] = []

    def wrap_agent(self, agent: Any) -> "GovernedAutoGenAgent":
        """Wrap an AutoGen agent with governance controls."""
        return GovernedAutoGenAgent(agent, self)

    def process_message(self, message: str, direction: str = "input") -> GovernanceResult:
        """Process and validate a message."""
        result = self.tork.govern(message)
        self.receipts.append({
            'type': direction,
            'agent_id': self.agent_id,
            'receipt_id': result.receipt.receipt_id,
            'action': result.action.value,
            'has_pii': result.pii.has_pii
        })
        return result

    def govern_message(self, text: str) -> str:
        """Govern message text - standalone method."""
        return self.process_message(text).output

    def govern(self, text: str) -> str:
        """Govern text - alias for govern_message."""
        return self.govern_message(text)

    def create_message_filter(self) -> Callable:
        """Create a message filter function for AutoGen agents."""
        def message_filter(message: Dict) -> Dict:
            if 'content' in message and isinstance(message['content'], str):
                result = self.process_message(message['content'], 'filter')
                if result.action == GovernanceAction.DENY:
                    message['content'] = "[Message blocked by governance policy]"
                elif result.action == GovernanceAction.REDACT:
                    message['content'] = result.output
            return message
        return message_filter


class GovernedAutoGenAgent:
    """
    Wrapper for an AutoGen agent that applies governance to all messages.

    Example:
        >>> from tork_governance.adapters.autogen import GovernedAutoGenAgent, TorkAutoGenMiddleware
        >>> from autogen import AssistantAgent
        >>>
        >>> middleware = TorkAutoGenMiddleware()
        >>> agent = AssistantAgent("assistant", llm_config={...})
        >>> governed = GovernedAutoGenAgent(agent, middleware)
        >>> governed.initiate_chat(user_proxy, message="Hello")
    """

    def __init__(self, agent: Any = None, middleware: TorkAutoGenMiddleware = None, api_key: Optional[str] = None):
        self._agent = agent
        self._middleware = middleware or TorkAutoGenMiddleware(api_key=api_key)

    def govern_message(self, text: str) -> str:
        """Govern message text - standalone method."""
        return self._middleware.govern_message(text)

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped agent."""
        return getattr(self._agent, name)

    def send(
        self,
        message: str,
        recipient: Any,
        request_reply: Optional[bool] = None,
        silent: bool = False
    ) -> None:
        """Send a message with governance applied."""
        # Govern outgoing message
        result = self._middleware.process_message(message, 'outgoing')

        if result.action == GovernanceAction.DENY:
            raise ValueError(f"Message blocked by governance: {result.receipt.receipt_id}")

        governed_message = result.output

        # Send via original agent
        if hasattr(self._agent, 'send'):
            self._agent.send(governed_message, recipient, request_reply, silent)

    def receive(
        self,
        message: str,
        sender: Any,
        request_reply: Optional[bool] = None,
        silent: bool = False
    ) -> None:
        """Receive a message with governance applied."""
        # Govern incoming message
        result = self._middleware.process_message(message, 'incoming')

        governed_message = result.output

        # Receive via original agent
        if hasattr(self._agent, 'receive'):
            self._agent.receive(governed_message, sender, request_reply, silent)

    def initiate_chat(
        self,
        recipient: Any,
        message: str,
        clear_history: bool = True,
        silent: bool = False,
        **kwargs
    ) -> Dict:
        """Initiate a chat with governance applied to the initial message."""
        # Govern initial message
        result = self._middleware.process_message(message, 'initiate')

        if result.action == GovernanceAction.DENY:
            raise ValueError(f"Initial message blocked: {result.receipt.receipt_id}")

        governed_message = result.output

        # Initiate via original agent
        if hasattr(self._agent, 'initiate_chat'):
            return self._agent.initiate_chat(
                recipient, governed_message, clear_history, silent, **kwargs
            )

        return {'history': [], 'cost': 0}

    def generate_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Any] = None,
        **kwargs
    ) -> Optional[str]:
        """Generate a reply with governance applied."""
        # Generate via original agent
        if hasattr(self._agent, 'generate_reply'):
            reply = self._agent.generate_reply(messages, sender, **kwargs)

            if reply:
                # Govern the reply
                result = self._middleware.process_message(reply, 'reply')
                return result.output

        return None
