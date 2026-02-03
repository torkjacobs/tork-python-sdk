"""
Flowise adapter for Tork Governance.

Provides node, flow, and API wrappers for Flowise low-code LLM applications.
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkFlowiseNode:
    """
    Custom Flowise node with governance.

    Example:
        >>> from tork_governance.adapters.flowise import TorkFlowiseNode
        >>>
        >>> node = TorkFlowiseNode(name="GovernedInput")
        >>> output = node.process({"text": "user@example.com"})
    """

    def __init__(
        self,
        name: str = "tork-node",
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        govern_input: bool = True,
        govern_output: bool = True
    ):
        self.name = name
        self.tork = tork or Tork(api_key=api_key)
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def process(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process node inputs with governance."""
        # Govern inputs
        governed_inputs = {}
        if self.govern_input:
            for key, value in inputs.items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    governed_inputs[key] = result.output
                    self.receipts.append({
                        "type": "node_input",
                        "node": self.name,
                        "field": key,
                        "receipt_id": result.receipt.receipt_id,
                        "action": result.action.value
                    })
                elif isinstance(value, dict):
                    governed_inputs[key] = self._govern_dict(value, "input")
                elif isinstance(value, list):
                    governed_inputs[key] = self._govern_list(value, "input")
                else:
                    governed_inputs[key] = value
        else:
            governed_inputs = inputs

        return governed_inputs

    def process_output(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process node outputs with governance."""
        if not self.govern_output:
            return outputs

        governed_outputs = {}
        for key, value in outputs.items():
            if isinstance(value, str):
                result = self.tork.govern(value)
                governed_outputs[key] = result.output
                self.receipts.append({
                    "type": "node_output",
                    "node": self.name,
                    "field": key,
                    "receipt_id": result.receipt.receipt_id
                })
            elif isinstance(value, dict):
                governed_outputs[key] = self._govern_dict(value, "output")
            elif isinstance(value, list):
                governed_outputs[key] = self._govern_list(value, "output")
            else:
                governed_outputs[key] = value

        return governed_outputs

    def _govern_dict(self, data: Dict[str, Any], direction: str) -> Dict[str, Any]:
        """Govern dictionary values."""
        governed = {}
        for key, value in data.items():
            if isinstance(value, str):
                result = self.tork.govern(value)
                governed[key] = result.output
            elif isinstance(value, dict):
                governed[key] = self._govern_dict(value, direction)
            elif isinstance(value, list):
                governed[key] = self._govern_list(value, direction)
            else:
                governed[key] = value
        return governed

    def _govern_list(self, items: List[Any], direction: str) -> List[Any]:
        """Govern list items."""
        governed = []
        for item in items:
            if isinstance(item, str):
                result = self.tork.govern(item)
                governed.append(result.output)
            elif isinstance(item, dict):
                governed.append(self._govern_dict(item, direction))
            else:
                governed.append(item)
        return governed

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkFlowiseFlow:
    """
    Wrapper for Flowise flows with governance.

    Example:
        >>> from tork_governance.adapters.flowise import TorkFlowiseFlow
        >>>
        >>> flow = FlowiseFlow.load("my-flow.json")
        >>> governed_flow = TorkFlowiseFlow(flow)
        >>>
        >>> result = governed_flow.execute({"question": "user@email.com"})
    """

    def __init__(self, flow: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.flow = flow
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute flow with governance."""
        # Govern inputs
        governed_inputs = self._govern_dict(inputs, "flow_input")

        # Execute flow
        outputs = self.flow.execute(governed_inputs)

        # Govern outputs
        governed_outputs = self._govern_dict(outputs, "flow_output")

        return governed_outputs

    async def aexecute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Async flow execution."""
        governed_inputs = self._govern_dict(inputs, "flow_input")
        outputs = await self.flow.aexecute(governed_inputs)
        return self._govern_dict(outputs, "flow_output")

    def _govern_dict(self, data: Dict[str, Any], context: str) -> Dict[str, Any]:
        """Govern dictionary values."""
        governed = {}
        for key, value in data.items():
            if isinstance(value, str):
                result = self.tork.govern(value)
                governed[key] = result.output
                self.receipts.append({
                    "type": context,
                    "field": key,
                    "receipt_id": result.receipt.receipt_id
                })
            elif isinstance(value, dict):
                governed[key] = self._govern_dict(value, context)
            elif isinstance(value, list):
                governed[key] = self._govern_list(value, context)
            else:
                governed[key] = value
        return governed

    def _govern_list(self, items: List[Any], context: str) -> List[Any]:
        """Govern list items."""
        governed = []
        for item in items:
            if isinstance(item, str):
                result = self.tork.govern(item)
                governed.append(result.output)
            elif isinstance(item, dict):
                governed.append(self._govern_dict(item, context))
            else:
                governed.append(item)
        return governed

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkFlowiseAPI:
    """
    API client wrapper for Flowise with governance.

    Example:
        >>> from tork_governance.adapters.flowise import TorkFlowiseAPI
        >>>
        >>> api = TorkFlowiseAPI(base_url="http://localhost:3000")
        >>> result = api.predict("chatflow-id", {"question": "user@email.com"})
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        api_key: Optional[str] = None,
        tork: Optional[Tork] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.flowise_api_key = api_key
        self.tork = tork or Tork()
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def predict(self, chatflow_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Make governed prediction request."""
        try:
            import requests
        except ImportError:
            raise ImportError("requests package required: pip install requests")

        # Govern inputs
        governed_inputs = self._govern_dict(inputs, "api_input")

        # Make request
        headers = {}
        if self.flowise_api_key:
            headers["Authorization"] = f"Bearer {self.flowise_api_key}"

        response = requests.post(
            f"{self.base_url}/api/v1/prediction/{chatflow_id}",
            json=governed_inputs,
            headers=headers
        )
        response.raise_for_status()
        result = response.json()

        # Govern response
        governed_result = self._govern_dict(result, "api_output")

        return governed_result

    async def apredict(self, chatflow_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Async prediction request."""
        try:
            import aiohttp
        except ImportError:
            raise ImportError("aiohttp package required: pip install aiohttp")

        governed_inputs = self._govern_dict(inputs, "api_input")

        headers = {}
        if self.flowise_api_key:
            headers["Authorization"] = f"Bearer {self.flowise_api_key}"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/v1/prediction/{chatflow_id}",
                json=governed_inputs,
                headers=headers
            ) as response:
                response.raise_for_status()
                result = await response.json()

        return self._govern_dict(result, "api_output")

    def _govern_dict(self, data: Dict[str, Any], context: str) -> Dict[str, Any]:
        """Govern dictionary values."""
        governed = {}
        for key, value in data.items():
            if isinstance(value, str):
                result = self.tork.govern(value)
                governed[key] = result.output
                self.receipts.append({
                    "type": context,
                    "field": key,
                    "receipt_id": result.receipt.receipt_id
                })
            elif isinstance(value, dict):
                governed[key] = self._govern_dict(value, context)
            elif isinstance(value, list):
                governed[key] = self._govern_list(value, context)
            else:
                governed[key] = value
        return governed

    def _govern_list(self, items: List[Any], context: str) -> List[Any]:
        """Govern list items."""
        governed = []
        for item in items:
            if isinstance(item, str):
                result = self.tork.govern(item)
                governed.append(result.output)
            elif isinstance(item, dict):
                governed.append(self._govern_dict(item, context))
            else:
                governed.append(item)
        return governed

    def get_receipts(self) -> List[Dict]:
        return self.receipts
