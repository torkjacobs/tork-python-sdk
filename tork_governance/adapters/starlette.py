"""
Starlette adapter for Tork Governance.

Provides middleware and route decorators for Starlette/FastAPI applications.
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkStarletteMiddleware:
    """
    ASGI middleware for Starlette with Tork governance.

    Example:
        >>> from tork_governance.adapters.starlette import TorkStarletteMiddleware
        >>> from starlette.applications import Starlette
        >>> from starlette.middleware import Middleware
        >>>
        >>> app = Starlette(
        >>>     middleware=[
        >>>         Middleware(TorkStarletteMiddleware)
        >>>     ]
        >>> )
    """

    def __init__(
        self,
        app: Any,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        govern_input: bool = True,
        govern_output: bool = True,
        protected_paths: Optional[List[str]] = None,
        excluded_paths: Optional[List[str]] = None
    ):
        self.app = app
        self.tork = tork or Tork(api_key=api_key)
        self.govern_input = govern_input
        self.govern_output = govern_output
        self.protected_paths = protected_paths or ["/api/"]
        self.excluded_paths = excluded_paths or ["/health", "/metrics"]
        self.receipts: List[Dict] = []

    async def __call__(self, scope: Dict, receive: Callable, send: Callable) -> None:
        """ASGI interface."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Check if path should be excluded
        if any(path.startswith(exc) for exc in self.excluded_paths):
            await self.app(scope, receive, send)
            return

        # Check if path should be protected
        should_govern = any(path.startswith(prot) for prot in self.protected_paths)

        if not should_govern:
            await self.app(scope, receive, send)
            return

        # Wrap receive to govern request body
        if self.govern_input:
            receive = self._wrap_receive(receive)

        # Wrap send to govern response body
        if self.govern_output:
            send = self._wrap_send(send)

        await self.app(scope, receive, send)

    def _wrap_receive(self, receive: Callable) -> Callable:
        """Wrap receive to govern incoming request body."""
        async def governed_receive() -> Dict:
            message = await receive()

            if message["type"] == "http.request":
                body = message.get("body", b"")
                if body:
                    try:
                        # Decode and govern
                        text = body.decode("utf-8")
                        result = self.tork.govern(text)
                        self.receipts.append({
                            "type": "request_body",
                            "receipt_id": result.receipt.receipt_id,
                            "action": result.action.value,
                            "has_pii": result.pii.has_pii
                        })

                        if result.action == GovernanceAction.DENY:
                            # Return empty body for denied requests
                            message["body"] = b""
                        else:
                            message["body"] = result.output.encode("utf-8")
                    except UnicodeDecodeError:
                        # Binary data, skip governance
                        pass

            return message

        return governed_receive

    def _wrap_send(self, send: Callable) -> Callable:
        """Wrap send to govern outgoing response body."""
        response_body: List[bytes] = []

        async def governed_send(message: Dict) -> None:
            if message["type"] == "http.response.body":
                body = message.get("body", b"")
                if body:
                    try:
                        text = body.decode("utf-8")
                        result = self.tork.govern(text)
                        self.receipts.append({
                            "type": "response_body",
                            "receipt_id": result.receipt.receipt_id,
                            "action": result.action.value
                        })
                        message["body"] = result.output.encode("utf-8")
                    except UnicodeDecodeError:
                        pass

            await send(message)

        return governed_send

    def get_receipts(self) -> List[Dict]:
        """Get all governance receipts."""
        return self.receipts.copy()


class TorkStarletteRoute:
    """
    Route wrapper for Starlette with governance.

    Example:
        >>> from tork_governance.adapters.starlette import TorkStarletteRoute
        >>> from starlette.routing import Route
        >>>
        >>> tork_route = TorkStarletteRoute()
        >>>
        >>> async def homepage(request):
        >>>     return JSONResponse({"message": "Hello"})
        >>>
        >>> routes = [
        >>>     Route("/", tork_route.wrap(homepage))
        >>> ]
    """

    def __init__(self, tork: Optional[Tork] = None, api_key: Optional[str] = None):
        self.tork = tork or Tork(api_key=api_key)
        self.receipts: List[Dict] = []

    def wrap(self, handler: Callable) -> Callable:
        """Wrap a route handler with governance."""
        @wraps(handler)
        async def governed_handler(request: Any) -> Any:
            # Govern request body if present
            if hasattr(request, "body"):
                body_method = getattr(request, "body", None)
                if callable(body_method):
                    try:
                        body = await body_method()
                        if body:
                            text = body.decode("utf-8")
                            result = self.tork.govern(text)
                            self.receipts.append({
                                "type": "route_request",
                                "receipt_id": result.receipt.receipt_id
                            })
                            # Store governed body in request state
                            if hasattr(request, "state"):
                                request.state.governed_body = result.output
                                request.state.tork_result = result
                    except Exception:
                        pass

            # Call original handler
            response = await handler(request)

            # Govern response body if it's a JSON response
            if hasattr(response, "body"):
                try:
                    body = response.body.decode("utf-8")
                    result = self.tork.govern(body)
                    self.receipts.append({
                        "type": "route_response",
                        "receipt_id": result.receipt.receipt_id
                    })
                    response.body = result.output.encode("utf-8")
                except Exception:
                    pass

            return response

        return governed_handler

    def get_receipts(self) -> List[Dict]:
        return self.receipts


def tork_route(
    tork: Optional[Tork] = None,
    govern_input: bool = True,
    govern_output: bool = True
):
    """
    Decorator for governed Starlette routes.

    Example:
        >>> from tork_governance.adapters.starlette import tork_route
        >>> from starlette.responses import JSONResponse
        >>>
        >>> @tork_route()
        >>> async def chat_endpoint(request):
        >>>     data = await request.json()
        >>>     # data is already governed
        >>>     return JSONResponse({"response": "Hello"})
    """
    _tork = tork or Tork()
    receipts: List[Dict] = []

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Any, *args, **kwargs) -> Any:
            # Govern input
            if govern_input and hasattr(request, "json"):
                try:
                    json_method = getattr(request, "json")
                    if callable(json_method):
                        # Store original json method
                        original_json = json_method

                        async def governed_json():
                            data = await original_json()
                            return _govern_value(data, _tork, receipts, "input")

                        request.json = governed_json
                except Exception:
                    pass

            # Call handler
            response = await func(request, *args, **kwargs)

            # Govern output
            if govern_output and hasattr(response, "body"):
                try:
                    body = response.body
                    if isinstance(body, bytes):
                        text = body.decode("utf-8")
                        result = _tork.govern(text)
                        receipts.append({
                            "type": "output",
                            "receipt_id": result.receipt.receipt_id
                        })
                        response.body = result.output.encode("utf-8")
                except Exception:
                    pass

            return response

        wrapper.get_receipts = lambda: receipts
        return wrapper

    return decorator


def _govern_value(value: Any, tork: Tork, receipts: List[Dict], direction: str) -> Any:
    """Recursively govern values."""
    if isinstance(value, str):
        result = tork.govern(value)
        receipts.append({
            "type": f"{direction}_string",
            "receipt_id": result.receipt.receipt_id
        })
        return result.output
    elif isinstance(value, dict):
        return {k: _govern_value(v, tork, receipts, direction) for k, v in value.items()}
    elif isinstance(value, list):
        return [_govern_value(item, tork, receipts, direction) for item in value]
    return value


class TorkStarletteWebSocket:
    """
    WebSocket handler wrapper with governance.

    Example:
        >>> from tork_governance.adapters.starlette import TorkStarletteWebSocket
        >>>
        >>> ws_handler = TorkStarletteWebSocket()
        >>>
        >>> @ws_handler.wrap
        >>> async def websocket_endpoint(websocket):
        >>>     await websocket.accept()
        >>>     data = await websocket.receive_text()  # Governed
        >>>     await websocket.send_text(data)  # Governed
    """

    def __init__(self, tork: Optional[Tork] = None):
        self.tork = tork or Tork()
        self.receipts: List[Dict] = []

    def wrap(self, handler: Callable) -> Callable:
        """Wrap WebSocket handler with governance."""
        tork = self.tork
        receipts = self.receipts

        @wraps(handler)
        async def governed_handler(websocket: Any) -> Any:
            # Wrap receive_text
            original_receive_text = websocket.receive_text

            async def governed_receive_text() -> str:
                text = await original_receive_text()
                result = tork.govern(text)
                receipts.append({
                    "type": "ws_receive",
                    "receipt_id": result.receipt.receipt_id
                })
                return result.output

            websocket.receive_text = governed_receive_text

            # Wrap send_text
            original_send_text = websocket.send_text

            async def governed_send_text(data: str) -> None:
                result = tork.govern(data)
                receipts.append({
                    "type": "ws_send",
                    "receipt_id": result.receipt.receipt_id
                })
                await original_send_text(result.output)

            websocket.send_text = governed_send_text

            return await handler(websocket)

        return governed_handler

    def get_receipts(self) -> List[Dict]:
        return self.receipts


class TorkBackgroundTask:
    """Wrapper for Starlette background tasks with governance."""

    def __init__(self, tork: Optional[Tork] = None):
        self.tork = tork or Tork()
        self.receipts: List[Dict] = []

    def wrap(self, func: Callable) -> Callable:
        """Wrap background task with governance."""
        @wraps(func)
        async def governed_task(*args, **kwargs):
            # Govern string arguments
            governed_args = []
            for arg in args:
                if isinstance(arg, str):
                    result = self.tork.govern(arg)
                    governed_args.append(result.output)
                    self.receipts.append({
                        "type": "background_arg",
                        "receipt_id": result.receipt.receipt_id
                    })
                else:
                    governed_args.append(arg)

            governed_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    result = self.tork.govern(value)
                    governed_kwargs[key] = result.output
                else:
                    governed_kwargs[key] = value

            return await func(*governed_args, **governed_kwargs)

        return governed_task

    def get_receipts(self) -> List[Dict]:
        return self.receipts
