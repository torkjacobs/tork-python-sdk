"""
Tork Governance adapter for ChatDev.

Provides governance for ChatDev's multi-agent software development framework
with automatic PII detection and policy enforcement.

Usage:
    from tork_governance.adapters.chatdev_adapter import TorkChatDevPhase

    phase = TorkChatDevPhase(tork=tork)
    response = phase.run("Build a tool that stores SSN 123-45-6789")
"""

from typing import Any, Dict, List, Optional
from functools import wraps


class TorkChatDevPhase:
    """Governed ChatDev phase wrapper."""

    def __init__(
        self,
        tork: Any = None,
        govern_input: bool = True,
        govern_output: bool = True,
        phase_name: str = "default",
    ):
        self.tork = tork
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.phase_name = phase_name

    def run(self, task: str, **kwargs) -> Dict[str, Any]:
        """Run a governed ChatDev phase."""
        receipts = []

        governed_task = task
        if self.govern_input and self.tork:
            result = self.tork.govern(task)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_task = result.output

        return {
            "task": governed_task,
            "phase": self.phase_name,
            "_tork_receipts": receipts,
        }

    def govern_chat_messages(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Govern chat messages exchanged between ChatDev agents."""
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

    def govern_code_output(self, code: str) -> Dict[str, Any]:
        """Govern generated code for PII leakage."""
        receipts = []

        governed_code = code
        if self.govern_output and self.tork:
            result = self.tork.govern(code)
            receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_code = result.output

        return {
            "code": governed_code,
            "_tork_receipts": receipts,
        }


def chatdev_governed(tork: Any, govern_input: bool = True, govern_output: bool = True):
    """Decorator to govern ChatDev phase functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if govern_input and 'task' in kwargs:
                result = tork.govern(kwargs['task'])
                if result.action in ('redact', 'REDACT'):
                    kwargs['task'] = result.output
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
