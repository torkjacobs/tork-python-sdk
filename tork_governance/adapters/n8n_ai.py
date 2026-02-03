"""
Tork Governance adapter for n8n AI workflows.

Provides governance for n8n automation workflows
with automatic PII detection and policy enforcement.

Usage:
    from tork_governance.adapters.n8n_ai import TorkN8nWebhook, TorkN8nNode

    # Webhook handler
    webhook = TorkN8nWebhook(tork=tork)
    governed_data = webhook.handle(request_data)

    # Node wrapper
    node = TorkN8nNode(tork=tork)
    result = node.execute(input_data)
"""

from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
import json
import hashlib
from datetime import datetime


class TorkN8nWebhook:
    """Governed n8n webhook handler for incoming requests."""

    def __init__(
        self,
        tork: Any = None,
        govern_input: bool = True,
        govern_output: bool = True,
        text_fields: List[str] = None
    ):
        self.tork = tork
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.text_fields = text_fields or [
            'body', 'message', 'content', 'text', 'query',
            'prompt', 'input', 'data', 'payload', 'description'
        ]
        self._receipts = []

    @property
    def receipts(self) -> List[Any]:
        """Get all governance receipts."""
        return self._receipts

    def _govern_value(self, value: Any) -> tuple:
        """Govern a single value, returning (governed_value, receipt)."""
        if isinstance(value, str) and value.strip():
            result = self.tork.govern(value)
            if result.action in ('redact', 'REDACT'):
                return result.output, result.receipt
            return value, result.receipt
        return value, None

    def _govern_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively govern text fields in a dictionary."""
        governed = {}
        for key, value in data.items():
            if key in self.text_fields and isinstance(value, str):
                governed_value, receipt = self._govern_value(value)
                governed[key] = governed_value
                if receipt:
                    self._receipts.append(receipt)
            elif isinstance(value, dict):
                governed[key] = self._govern_dict(value)
            elif isinstance(value, list):
                governed[key] = self._govern_list(value)
            else:
                governed[key] = value
        return governed

    def _govern_list(self, data: List[Any]) -> List[Any]:
        """Govern items in a list."""
        governed = []
        for item in data:
            if isinstance(item, dict):
                governed.append(self._govern_dict(item))
            elif isinstance(item, str):
                governed_value, receipt = self._govern_value(item)
                governed.append(governed_value)
                if receipt:
                    self._receipts.append(receipt)
            else:
                governed.append(item)
        return governed

    def handle(
        self,
        request_data: Dict[str, Any],
        headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Handle incoming webhook request with governance."""
        self._receipts = []

        # Govern request body
        if self.govern_input:
            governed_data = self._govern_dict(request_data)
        else:
            governed_data = request_data

        return {
            "data": governed_data,
            "headers": headers or {},
            "_tork_receipts": self._receipts,
            "_tork_governed": self.govern_input
        }

    def respond(
        self,
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Govern outgoing webhook response."""
        receipts = []

        if self.govern_output:
            # Temporarily store receipts in instance
            old_receipts = self._receipts
            self._receipts = []
            governed_data = self._govern_dict(response_data)
            receipts = self._receipts
            self._receipts = old_receipts
        else:
            governed_data = response_data

        return {
            "data": governed_data,
            "_tork_receipts": receipts,
            "_tork_governed": self.govern_output
        }


class TorkN8nNode:
    """Governed n8n node execution wrapper."""

    def __init__(
        self,
        tork: Any = None,
        node_type: str = "tork-governance",
        govern_input: bool = True,
        govern_output: bool = True,
        text_fields: List[str] = None
    ):
        self.tork = tork
        self.node_type = node_type
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.text_fields = text_fields or [
            'text', 'message', 'content', 'body', 'query',
            'prompt', 'input', 'output', 'response', 'data'
        ]
        self._receipts = []

    @property
    def receipts(self) -> List[Any]:
        """Get all governance receipts."""
        return self._receipts

    def _govern_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Govern a single workflow item."""
        governed = {}
        for key, value in item.items():
            if key == 'json' and isinstance(value, dict):
                # n8n stores data in 'json' property
                governed[key] = self._govern_json_data(value)
            elif key in self.text_fields and isinstance(value, str):
                result = self.tork.govern(value)
                if result.action in ('redact', 'REDACT'):
                    governed[key] = result.output
                else:
                    governed[key] = value
                self._receipts.append(result.receipt)
            else:
                governed[key] = value
        return governed

    def _govern_json_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Govern the json data of a workflow item."""
        governed = {}
        for key, value in data.items():
            if key in self.text_fields and isinstance(value, str):
                result = self.tork.govern(value)
                if result.action in ('redact', 'REDACT'):
                    governed[key] = result.output
                else:
                    governed[key] = value
                self._receipts.append(result.receipt)
            elif isinstance(value, dict):
                governed[key] = self._govern_json_data(value)
            elif isinstance(value, list):
                governed[key] = [
                    self._govern_json_data(v) if isinstance(v, dict) else v
                    for v in value
                ]
            else:
                governed[key] = value
        return governed

    def execute(
        self,
        items: List[Dict[str, Any]],
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute node with governed input/output."""
        self._receipts = []
        parameters = parameters or {}

        # Govern input items
        governed_items = []
        if self.govern_input:
            for item in items:
                governed_items.append(self._govern_item(item))
        else:
            governed_items = items

        return {
            "items": governed_items,
            "parameters": parameters,
            "_tork_receipts": self._receipts,
            "_tork_node_type": self.node_type
        }

    def process_output(
        self,
        output_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process and govern node output."""
        receipts = []

        if self.govern_output:
            old_receipts = self._receipts
            self._receipts = []
            governed_items = [self._govern_item(item) for item in output_items]
            receipts = self._receipts
            self._receipts = old_receipts
        else:
            governed_items = output_items

        return {
            "items": governed_items,
            "_tork_receipts": receipts
        }


class TorkN8nAIChain:
    """Governed n8n AI chain processor for LLM operations."""

    def __init__(
        self,
        tork: Any = None,
        govern_input: bool = True,
        govern_output: bool = True,
        model: str = None
    ):
        self.tork = tork
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.model = model
        self._receipts = []

    @property
    def receipts(self) -> List[Any]:
        """Get all governance receipts."""
        return self._receipts

    def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Process chat messages with governance."""
        self._receipts = []

        # Govern input messages
        governed_messages = []
        if self.govern_input:
            for msg in messages:
                if msg.get("role") in ("user", "human") and msg.get("content"):
                    result = self.tork.govern(msg["content"])
                    self._receipts.append(result.receipt)
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
            "model": self.model,
            "parameters": kwargs,
            "_tork_receipts": self._receipts,
            "_tork_governed_input": self.govern_input
        }

    def complete(
        self,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Process completion request with governance."""
        self._receipts = []

        # Govern input prompt
        governed_prompt = prompt
        if self.govern_input and prompt:
            result = self.tork.govern(prompt)
            self._receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_prompt = result.output

        return {
            "prompt": governed_prompt,
            "model": self.model,
            "parameters": kwargs,
            "_tork_receipts": self._receipts,
            "_tork_governed_input": self.govern_input
        }

    def process_response(
        self,
        response: Union[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process and govern LLM response."""
        receipts = []

        if self.govern_output:
            if isinstance(response, str):
                result = self.tork.govern(response)
                receipts.append(result.receipt)
                governed_response = result.output if result.action in ('redact', 'REDACT') else response
            elif isinstance(response, dict):
                governed_response = {}
                for key, value in response.items():
                    if key in ('content', 'text', 'message', 'output') and isinstance(value, str):
                        result = self.tork.govern(value)
                        receipts.append(result.receipt)
                        governed_response[key] = result.output if result.action in ('redact', 'REDACT') else value
                    else:
                        governed_response[key] = value
            else:
                governed_response = response
        else:
            governed_response = response

        return {
            "response": governed_response,
            "_tork_receipts": receipts,
            "_tork_governed_output": self.govern_output
        }


class AsyncTorkN8nAIChain:
    """Async governed n8n AI chain processor."""

    def __init__(
        self,
        tork: Any = None,
        govern_input: bool = True,
        govern_output: bool = True,
        model: str = None
    ):
        self.tork = tork
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.model = model
        self._receipts = []

    @property
    def receipts(self) -> List[Any]:
        """Get all governance receipts."""
        return self._receipts

    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Process chat messages with governance (async)."""
        self._receipts = []

        governed_messages = []
        if self.govern_input:
            for msg in messages:
                if msg.get("role") in ("user", "human") and msg.get("content"):
                    result = self.tork.govern(msg["content"])
                    self._receipts.append(result.receipt)
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
            "model": self.model,
            "parameters": kwargs,
            "_tork_receipts": self._receipts
        }

    async def complete(
        self,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Process completion request with governance (async)."""
        self._receipts = []

        governed_prompt = prompt
        if self.govern_input and prompt:
            result = self.tork.govern(prompt)
            self._receipts.append(result.receipt)
            if result.action in ('redact', 'REDACT'):
                governed_prompt = result.output

        return {
            "prompt": governed_prompt,
            "model": self.model,
            "parameters": kwargs,
            "_tork_receipts": self._receipts
        }

    async def process_response(
        self,
        response: Union[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process and govern LLM response (async)."""
        receipts = []

        if self.govern_output:
            if isinstance(response, str):
                result = self.tork.govern(response)
                receipts.append(result.receipt)
                governed_response = result.output if result.action in ('redact', 'REDACT') else response
            elif isinstance(response, dict):
                governed_response = {}
                for key, value in response.items():
                    if key in ('content', 'text', 'message', 'output') and isinstance(value, str):
                        result = self.tork.govern(value)
                        receipts.append(result.receipt)
                        governed_response[key] = result.output if result.action in ('redact', 'REDACT') else value
                    else:
                        governed_response[key] = value
            else:
                governed_response = response
        else:
            governed_response = response

        return {
            "response": governed_response,
            "_tork_receipts": receipts
        }


def n8n_governed(
    tork: Any,
    govern_input: bool = True,
    govern_output: bool = True,
    text_fields: List[str] = None
):
    """Decorator to govern n8n workflow functions."""
    text_fields = text_fields or [
        'text', 'message', 'content', 'body', 'query',
        'prompt', 'input', 'output', 'response', 'data'
    ]

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Govern input kwargs
            if govern_input:
                governed_kwargs = {}
                for key, value in kwargs.items():
                    if key in text_fields and isinstance(value, str):
                        result = tork.govern(value)
                        governed_kwargs[key] = result.output if result.action in ('redact', 'REDACT') else value
                    elif key == 'items' and isinstance(value, list):
                        # Handle n8n items array
                        governed_items = []
                        for item in value:
                            if isinstance(item, dict) and 'json' in item:
                                governed_json = {}
                                for k, v in item['json'].items():
                                    if k in text_fields and isinstance(v, str):
                                        result = tork.govern(v)
                                        governed_json[k] = result.output if result.action in ('redact', 'REDACT') else v
                                    else:
                                        governed_json[k] = v
                                governed_items.append({**item, 'json': governed_json})
                            else:
                                governed_items.append(item)
                        governed_kwargs[key] = governed_items
                    else:
                        governed_kwargs[key] = value
                kwargs = governed_kwargs

            return func(*args, **kwargs)
        return wrapper
    return decorator


def create_n8n_governance_node(
    tork: Any,
    node_name: str = "Tork Governance",
    node_description: str = "Add PII governance to your workflow"
) -> Dict[str, Any]:
    """Generate n8n node definition for Tork governance."""
    return {
        "displayName": node_name,
        "name": "torkGovernance",
        "icon": "file:tork.svg",
        "group": ["transform"],
        "version": 1,
        "description": node_description,
        "defaults": {
            "name": node_name
        },
        "inputs": ["main"],
        "outputs": ["main"],
        "properties": [
            {
                "displayName": "Operation",
                "name": "operation",
                "type": "options",
                "options": [
                    {
                        "name": "Govern Text",
                        "value": "governText",
                        "description": "Detect and redact PII in text fields"
                    },
                    {
                        "name": "Govern All",
                        "value": "governAll",
                        "description": "Govern all text fields in the item"
                    },
                    {
                        "name": "Check Only",
                        "value": "checkOnly",
                        "description": "Check for PII without redacting"
                    }
                ],
                "default": "governText"
            },
            {
                "displayName": "Text Field",
                "name": "textField",
                "type": "string",
                "default": "text",
                "description": "The field containing text to govern",
                "displayOptions": {
                    "show": {
                        "operation": ["governText"]
                    }
                }
            },
            {
                "displayName": "Text Fields",
                "name": "textFields",
                "type": "string",
                "default": "text,message,content,body",
                "description": "Comma-separated list of fields to govern",
                "displayOptions": {
                    "show": {
                        "operation": ["governAll"]
                    }
                }
            },
            {
                "displayName": "Governance Action",
                "name": "action",
                "type": "options",
                "options": [
                    {
                        "name": "Redact",
                        "value": "redact",
                        "description": "Replace PII with redaction tokens"
                    },
                    {
                        "name": "Hash",
                        "value": "hash",
                        "description": "Replace PII with hashed values"
                    },
                    {
                        "name": "Block",
                        "value": "block",
                        "description": "Block the workflow if PII is detected"
                    }
                ],
                "default": "redact"
            },
            {
                "displayName": "Include Receipt",
                "name": "includeReceipt",
                "type": "boolean",
                "default": True,
                "description": "Include governance receipt in output"
            }
        ],
        "_tork_instance": tork
    }


class N8nGovernanceResult:
    """Result container for n8n governance operations."""

    def __init__(
        self,
        items: List[Dict[str, Any]],
        receipts: List[Any],
        governed: bool = True,
        metadata: Dict[str, Any] = None
    ):
        self.items = items
        self.receipts = receipts
        self.governed = governed
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for n8n output."""
        return {
            "items": self.items,
            "_tork_receipts": self.receipts,
            "_tork_governed": self.governed,
            "_tork_timestamp": self.timestamp,
            "_tork_metadata": self.metadata
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)
