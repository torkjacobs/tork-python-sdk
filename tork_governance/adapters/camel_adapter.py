"""
Tork Governance adapter for CAMEL.

Provides governance for CAMEL's multi-agent role-playing framework
with automatic PII detection and policy enforcement.

Usage:
    from tork_governance.adapters.camel_adapter import TorkCamelAgent

    agent = TorkCamelAgent(tork=tork, role="assistant")
    response = agent.step("My SSN is 123-45-6789")
"""

from typing import Any, Dict, List, Optional
from functools import wraps


class TorkCamelAgent:
    """Governed CAMEL agent wrapper."""

    def __init__(
        self,
        tork: Any = None,
        role: str = "assistant",
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self.tork = tork
        self.role = role
        self.govern_input = govern_input
        self.govern_output = govern_output
        self._agent = None

    def _get_agent(self):
        """Lazy initialize the CAMEL agent."""
        if self._agent is None:
            try:
                from camel.agents import ChatAgent
                self._agent = ChatAgent(system_message=f"You are a {self.role}.")
            except ImportError:
                raise ImportError(
                    "camel-ai is required. Install with: pip install camel-ai"
                )
        return self._agent

    def step(self, message: str, **kwargs) -> Dict[str, Any]:
        """Execute a governed agent step."""
        receipts = []

        governed_message = message
        if self.govern_input and self.tork:
            result = self.tork.govern(message)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_message = result.output

        agent = self._get_agent()
        response = agent.step(governed_message, **kwargs)

        content = response.msg.content if hasattr(response, 'msg') else str(response)
        if self.govern_output and self.tork and content:
            gov_result = self.tork.govern(content)
            if gov_result.action in ('redact', 'REDACT'):
                content = gov_result.output

        return {
            "content": content,
            "role": self.role,
            "_tork_receipts": receipts,
        }


class TorkCamelRolePlaying:
    """Governed CAMEL role-playing session wrapper."""

    def __init__(
        self,
        tork: Any = None,
        assistant_role: str = "assistant",
        user_role: str = "user",
        govern_input: bool = True,
        govern_output: bool = True,
    ):
        self.tork = tork
        self.assistant_role = assistant_role
        self.user_role = user_role
        self.govern_input = govern_input
        self.govern_output = govern_output

    def init_chat(self, task: str) -> Dict[str, Any]:
        """Initialize a governed role-playing chat."""
        receipts = []

        governed_task = task
        if self.govern_input and self.tork:
            result = self.tork.govern(task)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_task = result.output

        return {
            "task": governed_task,
            "assistant_role": self.assistant_role,
            "user_role": self.user_role,
            "_tork_receipts": receipts,
        }

    def step(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Execute a governed role-playing step."""
        receipts = []
        governed_messages = []

        if self.govern_input and self.tork:
            for msg in messages:
                if msg.get("content"):
                    result = self.tork.govern(msg["content"])
                    receipts.append(result.receipt)
                    governed_messages.append({
                        **msg,
                        "content": result.output if result.action in ('redact', 'REDACT') else msg["content"]
                    })
                else:
                    governed_messages.append(msg)
        else:
            governed_messages = messages

        return {
            "messages": governed_messages,
            "_tork_receipts": receipts,
        }


def camel_governed(tork: Any, govern_input: bool = True, govern_output: bool = True):
    """Decorator to govern CAMEL agent functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if govern_input and 'message' in kwargs:
                result = tork.govern(kwargs['message'])
                if result.action in ('redact', 'REDACT'):
                    kwargs['message'] = result.output
            if govern_input and 'messages' in kwargs:
                governed = []
                for msg in kwargs['messages']:
                    if msg.get("content"):
                        result = tork.govern(msg["content"])
                        governed.append({
                            **msg,
                            "content": result.output if result.action in ('redact', 'REDACT') else msg["content"]
                        })
                    else:
                        governed.append(msg)
                kwargs['messages'] = governed
            return func(*args, **kwargs)
        return wrapper
    return decorator
