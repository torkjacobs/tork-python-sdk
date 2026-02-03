"""
Dify adapter for Tork Governance.

Provides integration with Dify low-code AI platform.
Supports workflow nodes, API hooks, and chat applications.

Example:
    from tork_governance.adapters.dify import TorkDifyNode, TorkDifyHook

    # Use as a workflow node
    node = TorkDifyNode()
    result = node.process({"query": "My SSN is 123-45-6789"})

    # Use as API hook
    hook = TorkDifyHook(webhook_url="https://api.dify.ai/...")
    hook.govern_and_forward(data)
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
import json
import hashlib
from datetime import datetime
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkDifyNode:
    """
    Dify workflow node for Tork governance.

    Can be used as a custom node in Dify workflows to add
    PII detection and redaction to any workflow.
    """

    # Node metadata for Dify
    NODE_TYPE = "tork-governance"
    NODE_NAME = "Tork PII Governance"
    NODE_DESCRIPTION = "Detect and redact PII from text using Tork Governance"

    def __init__(
        self,
        api_key: Optional[str] = None,
        input_field: str = "query",
        output_field: str = "governed_text",
        include_receipt: bool = True,
    ):
        self.tork = Tork(api_key=api_key)
        self.input_field = input_field
        self.output_field = output_field
        self.include_receipt = include_receipt

    def process(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process workflow node input."""
        text = inputs.get(self.input_field, "")

        if not text or not isinstance(text, str):
            return {
                self.output_field: text,
                "tork_action": "skip",
                "tork_reason": "No text input",
            }

        result = self.tork.govern(text)

        output = {
            self.output_field: result.output,
            "tork_action": result.action.value,
            "tork_pii_types": [m.type.value for m in result.pii.matches],
        }

        if self.include_receipt and result.receipt:
            output["tork_receipt_id"] = result.receipt.receipt_id
            output["tork_timestamp"] = result.receipt.timestamp

        return output

    def get_schema(self) -> Dict[str, Any]:
        """Get node schema for Dify."""
        return {
            "type": self.NODE_TYPE,
            "name": self.NODE_NAME,
            "description": self.NODE_DESCRIPTION,
            "inputs": {
                self.input_field: {
                    "type": "string",
                    "description": "Text to govern for PII",
                    "required": True,
                }
            },
            "outputs": {
                self.output_field: {
                    "type": "string",
                    "description": "Governed text with PII redacted",
                },
                "tork_action": {
                    "type": "string",
                    "description": "Governance action taken",
                    "enum": ["allow", "redact", "deny"],
                },
                "tork_pii_types": {
                    "type": "array",
                    "description": "Types of PII found",
                },
                "tork_receipt_id": {
                    "type": "string",
                    "description": "Governance receipt ID",
                },
            }
        }


class TorkDifyHook:
    """
    Dify webhook/API hook for Tork governance.

    Intercepts API calls to/from Dify and applies governance.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        webhook_url: Optional[str] = None,
        govern_request: bool = True,
        govern_response: bool = True,
    ):
        self.tork = Tork(api_key=api_key)
        self.webhook_url = webhook_url
        self.govern_request = govern_request
        self.govern_response = govern_response

    def govern_chat_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Govern a Dify chat message."""
        content = message.get("content", "") or message.get("query", "")

        if not content:
            return message

        result = self.tork.govern(content)

        # Update message with governed content
        governed_message = message.copy()
        if "content" in message:
            governed_message["content"] = result.output
        if "query" in message:
            governed_message["query"] = result.output

        # Add governance metadata
        governed_message["_tork"] = {
            "action": result.action.value,
            "receipt_id": result.receipt.receipt_id if result.receipt else None,
            "pii_found": [m.type.value for m in result.pii.matches],
        }

        return governed_message

    def govern_completion_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Govern a Dify completion API request."""
        governed = request.copy()

        # Govern inputs
        if "inputs" in request and isinstance(request["inputs"], dict):
            governed["inputs"] = {}
            for key, value in request["inputs"].items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    governed["inputs"][key] = result.output
                else:
                    governed["inputs"][key] = value

        # Govern query
        if "query" in request and isinstance(request["query"], str):
            result = self.tork.govern(request["query"])
            governed["query"] = result.output

        return governed

    def govern_completion_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Govern a Dify completion API response."""
        governed = response.copy()

        # Govern answer
        if "answer" in response and isinstance(response["answer"], str):
            result = self.tork.govern(response["answer"])
            governed["answer"] = result.output
            governed["_tork_receipt_id"] = result.receipt.receipt_id if result.receipt else None

        return governed


class TorkDifyApp:
    """
    Full Dify application wrapper with Tork governance.

    Wraps an entire Dify app to add governance to all interactions.
    """

    def __init__(
        self,
        app_id: str,
        api_key: Optional[str] = None,
        dify_api_key: Optional[str] = None,
        dify_base_url: str = "https://api.dify.ai/v1",
    ):
        self.app_id = app_id
        self.tork = Tork(api_key=api_key)
        self.dify_api_key = dify_api_key
        self.dify_base_url = dify_base_url
        self._receipts: List[str] = []

    def chat(
        self,
        query: str,
        user: str = "default",
        conversation_id: Optional[str] = None,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send governed chat message to Dify app."""
        # Govern query
        query_result = self.tork.govern(query)
        governed_query = query_result.output

        if query_result.receipt:
            self._receipts.append(query_result.receipt.receipt_id)

        # Govern inputs
        governed_inputs = {}
        if inputs:
            for key, value in inputs.items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    governed_inputs[key] = result.output
                    if result.receipt:
                        self._receipts.append(result.receipt.receipt_id)
                else:
                    governed_inputs[key] = value

        # Return governed request (actual API call would happen here)
        return {
            "query": governed_query,
            "user": user,
            "conversation_id": conversation_id,
            "inputs": governed_inputs,
            "_tork_governance": {
                "query_action": query_result.action.value,
                "receipt_ids": self._receipts[-5:],  # Last 5 receipts
            }
        }

    @property
    def receipts(self) -> List[str]:
        """Get all governance receipt IDs."""
        return self._receipts.copy()


def dify_governed(
    api_key: Optional[str] = None,
    govern_inputs: bool = True,
    govern_outputs: bool = True,
):
    """
    Decorator for Dify workflow functions.

    Example:
        @dify_governed()
        def my_workflow(query: str) -> str:
            # Process query
            return response
    """
    def decorator(func: Callable) -> Callable:
        tork = Tork(api_key=api_key)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Govern inputs
            if govern_inputs:
                args = tuple(
                    tork.govern(arg).output if isinstance(arg, str) else arg
                    for arg in args
                )
                kwargs = {
                    k: tork.govern(v).output if isinstance(v, str) else v
                    for k, v in kwargs.items()
                }

            result = func(*args, **kwargs)

            # Govern outputs
            if govern_outputs and isinstance(result, str):
                result = tork.govern(result).output

            return result

        return wrapper
    return decorator
