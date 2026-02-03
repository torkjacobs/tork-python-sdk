"""
FastAPI Integration for Tork Governance

Provides middleware and dependencies for FastAPI applications.
"""

from typing import Any, Callable, Optional
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkFastAPIMiddleware:
    """
    FastAPI/Starlette middleware that applies Tork governance to requests.

    Example:
        >>> from fastapi import FastAPI
        >>> from tork_governance.adapters.fastapi import TorkFastAPIMiddleware
        >>>
        >>> app = FastAPI()
        >>> app.add_middleware(TorkFastAPIMiddleware)
        >>>
        >>> @app.post("/chat")
        >>> async def chat(request: Request):
        >>>     # request.state.tork_result contains governance result
        >>>     return {"message": "ok"}
    """

    def __init__(
        self,
        app: Any,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0",
        extract_content: Optional[Callable] = None,
        skip_paths: Optional[list] = None
    ):
        self.app = app
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)
        self.extract_content = extract_content or self._default_extract_content
        self.skip_paths = skip_paths or []

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Skip specified paths
        path = scope.get("path", "")
        if any(path.startswith(skip) for skip in self.skip_paths):
            await self.app(scope, receive, send)
            return

        # Only process POST, PUT, PATCH
        method = scope.get("method", "GET")
        if method not in ("POST", "PUT", "PATCH"):
            await self.app(scope, receive, send)
            return

        # Read body
        body = b""
        more_body = True

        async def receive_wrapper():
            nonlocal body, more_body
            message = await receive()
            if message["type"] == "http.request":
                body += message.get("body", b"")
                more_body = message.get("more_body", False)
            return message

        # Collect full body
        while more_body:
            await receive_wrapper()

        # Try to parse and govern
        try:
            import json
            data = json.loads(body.decode("utf-8"))
            content = self.extract_content(data)

            if content:
                result = self.tork.govern(content)
                scope["state"] = scope.get("state", {})
                scope["state"]["tork_result"] = result

                if result.action == GovernanceAction.DENY:
                    # Return 403 response
                    response_body = json.dumps({
                        "error": "Request blocked by governance policy",
                        "receipt_id": result.receipt.receipt_id
                    }).encode("utf-8")

                    await send({
                        "type": "http.response.start",
                        "status": 403,
                        "headers": [(b"content-type", b"application/json")],
                    })
                    await send({
                        "type": "http.response.body",
                        "body": response_body,
                    })
                    return

                # Modify body if redacted
                if result.action == GovernanceAction.REDACT and result.pii.has_pii:
                    if "content" in data:
                        data["content"] = result.output
                    if "message" in data:
                        data["message"] = result.output
                    if "text" in data:
                        data["text"] = result.output
                    body = json.dumps(data).encode("utf-8")

        except (json.JSONDecodeError, UnicodeDecodeError):
            pass  # Not JSON, pass through

        # Create new receive that returns the (possibly modified) body
        body_sent = False

        async def modified_receive():
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, modified_receive, send)

    def _default_extract_content(self, data: dict) -> Optional[str]:
        """Default content extraction from request body."""
        if isinstance(data, dict):
            for key in ("content", "message", "text", "prompt", "query"):
                if key in data and isinstance(data[key], str):
                    return data[key]
        return None


class TorkFastAPIDependency:
    """
    FastAPI dependency for Tork governance.

    Example:
        >>> from fastapi import FastAPI, Depends
        >>> from tork_governance.adapters.fastapi import TorkFastAPIDependency
        >>>
        >>> app = FastAPI()
        >>> tork_dep = TorkFastAPIDependency()
        >>>
        >>> @app.post("/chat")
        >>> async def chat(content: str, tork_result: GovernanceResult = Depends(tork_dep)):
        >>>     return {"output": tork_result.output}
    """

    def __init__(
        self,
        tork: Optional[Tork] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0"
    ):
        self.tork = tork or Tork(api_key=api_key, policy_version=policy_version)

    async def __call__(self, content: str) -> GovernanceResult:
        """Dependency that governs the content parameter."""
        return self.tork.govern(content)

    def govern(self, content: str) -> GovernanceResult:
        """Explicitly govern content."""
        return self.tork.govern(content)
