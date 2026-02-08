"""
Tork Governance adapter for Sanic.

Provides governance middleware for Sanic async web applications
with automatic PII detection and policy enforcement.

Usage:
    from tork_governance.adapters.sanic_adapter import TorkSanicMiddleware

    middleware = TorkSanicMiddleware(tork=tork)
    app.register_middleware(middleware.request_middleware, "request")
"""

from typing import Any, Dict, List, Optional
from functools import wraps


class TorkSanicMiddleware:
    """Sanic middleware for Tork governance."""

    def __init__(
        self,
        tork: Any = None,
        skip_paths: List[str] = None,
    ):
        self.tork = tork
        self.skip_paths = skip_paths or []

    async def request_middleware(self, request):
        """Sanic request middleware that governs incoming requests."""
        if not self.tork:
            return None

        path = request.path
        for skip in self.skip_paths:
            if path.startswith(skip):
                return None

        method = request.method
        if method not in ("POST", "PUT", "PATCH"):
            return None

        try:
            body = request.json
        except Exception:
            return None

        if not body:
            return None

        content = self._extract_content(body)
        if not content:
            return None

        result = self.tork.govern(content)
        request.ctx.tork_result = result
        return None

    async def response_middleware(self, request, response):
        """Sanic response middleware that governs outgoing responses."""
        if not self.tork:
            return response

        try:
            import json
            body = json.loads(response.body)
            content = self._extract_content(body)
            if content:
                result = self.tork.govern(content)
                if result.action in ('redact', 'REDACT'):
                    for key in ["content", "message", "text", "output"]:
                        if key in body:
                            body[key] = result.output
                    response.body = json.dumps(body).encode()
        except Exception:
            pass

        return response

    def _extract_content(self, data: dict) -> str:
        keys = ["content", "message", "text", "prompt", "query", "input"]
        for key in keys:
            if key in data and isinstance(data[key], str) and data[key]:
                return data[key]
        return ""


def sanic_governed(tork: Any):
    """Decorator to govern Sanic route handlers."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            try:
                body = request.json
                if body:
                    for key in ["content", "message", "text", "prompt"]:
                        if key in body and isinstance(body[key], str):
                            result = tork.govern(body[key])
                            body[key] = result.output if result.action in ('redact', 'REDACT') else body[key]
                    request.ctx.tork_governed_body = body
            except Exception:
                pass
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
