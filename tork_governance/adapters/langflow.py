"""
Langflow adapter for Tork Governance.

Provides component, flow, and API wrappers for Langflow visual LangChain builder.
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkLangflowComponent:
    """
    Wrapper for Langflow components with governance.

    Example:
        >>> from tork_governance.adapters.langflow import TorkLangflowComponent
        >>>
        >>> component = LangflowComponent("TextInput")
        >>> governed_component = TorkLangflowComponent(component)
        >>>
        >>> output = governed_component.run(text="user@example.com")
    """

    def __init__(self, component: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.component = component
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def run(self, **kwargs) -> Any:
        """Run component with governed inputs."""
        # Govern inputs
        governed_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                result = self.tork.govern(value)
                governed_kwargs[key] = result.output
                self.receipts.append({
                    "type": "component_input",
                    "component": getattr(self.component, 'name', 'unknown'),
                    "field": key,
                    "receipt_id": result.receipt.receipt_id,
                    "action": result.action.value
                })
            elif isinstance(value, dict):
                governed_kwargs[key] = self._govern_dict(value, "input")
            elif isinstance(value, list):
                governed_kwargs[key] = self._govern_list(value, "input")
            else:
                governed_kwargs[key] = value

        # Run component
        output = self.component.run(**governed_kwargs)

        # Govern output
        if isinstance(output, str):
            result = self.tork.govern(output)
            self.receipts.append({
                "type": "component_output",
                "receipt_id": result.receipt.receipt_id
            })
            return result.output
        elif isinstance(output, dict):
            return self._govern_dict(output, "output")

        return output

    def _govern_dict(self, data: Dict[str, Any], direction: str) -> Dict[str, Any]:
        """Govern dictionary values."""
        governed = {}
        for key, value in data.items():
            if isinstance(value, str):
                result = self.tork.govern(value)
                governed[key] = result.output
                self.receipts.append({
                    "type": f"component_{direction}_dict",
                    "field": key,
                    "receipt_id": result.receipt.receipt_id
                })
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


class TorkLangflowFlow:
    """
    Wrapper for Langflow flows with governance.

    Example:
        >>> from tork_governance.adapters.langflow import TorkLangflowFlow
        >>>
        >>> flow = LangflowFlow.load("my-flow.json")
        >>> governed_flow = TorkLangflowFlow(flow)
        >>>
        >>> result = governed_flow.run({"input": "user@email.com"})
    """

    def __init__(self, flow: Any = None, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.flow = flow
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run flow with governance."""
        # Govern inputs
        governed_inputs = self._govern_dict(inputs, "flow_input")

        # Run flow
        outputs = self.flow.run(governed_inputs)

        # Govern outputs
        governed_outputs = self._govern_dict(outputs, "flow_output")

        return governed_outputs

    async def arun(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Async flow execution."""
        governed_inputs = self._govern_dict(inputs, "flow_input")
        outputs = await self.flow.arun(governed_inputs)
        return self._govern_dict(outputs, "flow_output")

    def get_component(self, name: str) -> TorkLangflowComponent:
        """Get governed component by name."""
        component = self.flow.get_component(name)
        return TorkLangflowComponent(component, tork=self.tork)

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


class TorkLangflowAPI:
    """
    API client wrapper for Langflow with governance.

    Example:
        >>> from tork_governance.adapters.langflow import TorkLangflowAPI
        >>>
        >>> api = TorkLangflowAPI(base_url="http://localhost:7860")
        >>> result = api.run_flow("flow-id", {"input": "user@email.com"})
    """

    def __init__(
        self,
        base_url: str = "http://localhost:7860",
        api_key: Optional[str] = None,
        tork: Optional[Tork] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.langflow_api_key = api_key
        self.tork = tork or Tork()
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def run_flow(self, flow_id: str, inputs: Dict[str, Any], tweaks: Optional[Dict] = None) -> Dict[str, Any]:
        """Run flow via API with governance."""
        try:
            import requests
        except ImportError:
            raise ImportError("requests package required: pip install requests")

        # Govern inputs
        governed_inputs = self._govern_dict(inputs, "api_input")

        # Prepare request
        headers = {"Content-Type": "application/json"}
        if self.langflow_api_key:
            headers["x-api-key"] = self.langflow_api_key

        payload = {
            "inputs": governed_inputs,
            "tweaks": tweaks or {}
        }

        # Make request
        response = requests.post(
            f"{self.base_url}/api/v1/run/{flow_id}",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        result = response.json()

        # Govern response
        governed_result = self._govern_response(result)

        return governed_result

    async def arun_flow(self, flow_id: str, inputs: Dict[str, Any], tweaks: Optional[Dict] = None) -> Dict[str, Any]:
        """Async flow execution via API."""
        try:
            import aiohttp
        except ImportError:
            raise ImportError("aiohttp package required: pip install aiohttp")

        governed_inputs = self._govern_dict(inputs, "api_input")

        headers = {"Content-Type": "application/json"}
        if self.langflow_api_key:
            headers["x-api-key"] = self.langflow_api_key

        payload = {
            "inputs": governed_inputs,
            "tweaks": tweaks or {}
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/v1/run/{flow_id}",
                json=payload,
                headers=headers
            ) as response:
                response.raise_for_status()
                result = await response.json()

        return self._govern_response(result)

    def upload_flow(self, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Upload flow with governed metadata."""
        try:
            import requests
        except ImportError:
            raise ImportError("requests package required: pip install requests")

        # Govern flow metadata
        if "name" in flow_data and isinstance(flow_data["name"], str):
            result = self.tork.govern(flow_data["name"])
            flow_data["name"] = result.output
        if "description" in flow_data and isinstance(flow_data["description"], str):
            result = self.tork.govern(flow_data["description"])
            flow_data["description"] = result.output

        headers = {"Content-Type": "application/json"}
        if self.langflow_api_key:
            headers["x-api-key"] = self.langflow_api_key

        response = requests.post(
            f"{self.base_url}/api/v1/flows",
            json=flow_data,
            headers=headers
        )
        response.raise_for_status()
        return response.json()

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

    def _govern_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Govern API response."""
        return self._govern_dict(response, "api_output")

    def get_receipts(self) -> List[Dict]:
        return self.receipts
