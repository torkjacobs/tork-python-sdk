"""
Model Context Protocol (MCP) adapter for Tork Governance.

Provides tool wrappers and server integration for Anthropic's MCP standard.
"""

from typing import Any, Callable, Dict, List, Optional
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkMCPToolWrapper:
    """
    Wraps MCP tools with Tork governance.

    Example:
        >>> from tork_governance.adapters.mcp import TorkMCPToolWrapper
        >>>
        >>> wrapper = TorkMCPToolWrapper()
        >>>
        >>> @wrapper.wrap_tool
        >>> def search(query: str) -> str:
        >>>     return f"Results for: {query}"
    """

    def __init__(self, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern(self, text: str) -> str:
        """Govern text - standalone method."""
        return self.tork.govern(text).output

    def govern_tool_input(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Govern tool input dictionary."""
        governed = {}
        for key, value in inputs.items():
            if isinstance(value, str):
                result = self.tork.govern(value)
                governed[key] = result.output
                self.receipts.append({
                    "type": "tool_input",
                    "argument": key,
                    "receipt_id": result.receipt.receipt_id,
                    "action": result.action.value
                })
            else:
                governed[key] = value
        return governed

    def wrap_tool(self, tool_func: Callable) -> Callable:
        """
        Wrap an MCP tool function with governance.

        Args:
            tool_func: The tool function to wrap

        Returns:
            Governed tool function
        """
        def governed_tool(*args, **kwargs):
            # Govern string inputs
            governed_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    governed_kwargs[key] = result.output
                    self.receipts.append({
                        "type": "tool_input",
                        "argument": key,
                        "receipt_id": result.receipt.receipt_id,
                        "action": result.action.value
                    })
                else:
                    governed_kwargs[key] = value

            # Execute tool
            output = tool_func(*args, **governed_kwargs)

            # Govern output
            if isinstance(output, str):
                result = self.tork.govern(output)
                self.receipts.append({
                    "type": "tool_output",
                    "receipt_id": result.receipt.receipt_id,
                    "action": result.action.value
                })
                return result.output

            return output

        governed_tool.__name__ = tool_func.__name__
        governed_tool.__doc__ = tool_func.__doc__
        return governed_tool

    def get_receipts(self) -> List[Dict]:
        """Get all governance receipts."""
        return self.receipts


class TorkMCPServer:
    """
    MCP Server with built-in Tork governance.

    Example:
        >>> from tork_governance.adapters.mcp import TorkMCPServer
        >>>
        >>> server = TorkMCPServer()
        >>>
        >>> @server.tool("search")
        >>> def search(query: str) -> str:
        >>>     return f"Results for: {query}"
        >>>
        >>> # All tool calls are automatically governed
    """

    def __init__(
        self,
        name: str = "tork-mcp-server",
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None
    ):
        self.name = name
        self.tork = tork or Tork(api_key=api_key)
        self.tools: Dict[str, Callable] = {}
        self.tool_schemas: Dict[str, Dict] = {}
        self._wrapper = TorkMCPToolWrapper(self.tork)

    def tool(self, name: str, description: str = ""):
        """
        Decorator to register a governed tool.

        Args:
            name: Tool name
            description: Tool description
        """
        def decorator(func: Callable) -> Callable:
            wrapped = self._wrapper.wrap_tool(func)
            self.tools[name] = wrapped
            self.tool_schemas[name] = {
                "name": name,
                "description": description or func.__doc__ or ""
            }
            return wrapped
        return decorator

    def list_tools(self) -> List[Dict]:
        """List all registered tools."""
        return list(self.tool_schemas.values())

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool with governance applied."""
        if name not in self.tools:
            return {"content": f"Unknown tool: {name}", "isError": True}

        try:
            result = self.tools[name](**arguments)
            return {"content": result, "isError": False}
        except Exception as e:
            return {"content": str(e), "isError": True}

    def get_receipts(self) -> List[Dict]:
        """Get all governance receipts."""
        return self._wrapper.receipts


class TorkMCPMiddleware:
    """
    Middleware for intercepting MCP requests and responses.

    Example:
        >>> middleware = TorkMCPMiddleware()
        >>> governed_request = middleware.govern_request(request)
        >>> governed_response = middleware.govern_response(response)
    """

    def __init__(self, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def govern_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Govern an MCP request."""
        governed = dict(request)

        # Govern tool arguments
        if "params" in governed and "arguments" in governed["params"]:
            args = governed["params"]["arguments"]
            governed_args = {}
            for key, value in args.items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    governed_args[key] = result.output
                    self.receipts.append({
                        "type": "request",
                        "receipt_id": result.receipt.receipt_id
                    })
                else:
                    governed_args[key] = value
            governed["params"]["arguments"] = governed_args

        return governed

    def govern_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Govern an MCP response."""
        governed = dict(response)

        if "result" in governed:
            result_content = governed["result"]
            if isinstance(result_content, str):
                gov_result = self.tork.govern(result_content)
                governed["result"] = gov_result.output
                self.receipts.append({
                    "type": "response",
                    "receipt_id": gov_result.receipt.receipt_id
                })
            elif isinstance(result_content, dict) and "content" in result_content:
                if isinstance(result_content["content"], str):
                    gov_result = self.tork.govern(result_content["content"])
                    governed["result"]["content"] = gov_result.output

        return governed
