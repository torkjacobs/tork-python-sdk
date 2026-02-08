"""
Tork Governance adapter for Tornado.

Provides governance middleware for Tornado web applications
with automatic PII detection and policy enforcement.

Usage:
    from tork_governance.adapters.tornado_adapter import TorkTornadoMixin

    class ChatHandler(TorkTornadoMixin, tornado.web.RequestHandler):
        def post(self):
            result = self.govern_body()
            self.write({"output": result.output})
"""

from typing import Any, Dict, List, Optional
from functools import wraps


class TorkTornadoMixin:
    """Mixin for Tornado RequestHandler with governance capabilities."""

    _tork = None
    _tork_skip_paths: List[str] = []

    @classmethod
    def configure_tork(cls, tork: Any, skip_paths: List[str] = None):
        """Configure Tork governance for this handler class."""
        cls._tork = tork
        cls._tork_skip_paths = skip_paths or []

    def govern_body(self) -> Any:
        """Govern the request body and return the governance result."""
        if not self._tork:
            from ...core import Tork
            self._tork = Tork()

        body = self.request.body
        if isinstance(body, bytes):
            body = body.decode("utf-8")

        import json
        try:
            data = json.loads(body)
            content = self._extract_content(data)
        except (json.JSONDecodeError, TypeError):
            content = body

        if not content:
            return None

        result = self._tork.govern(content)
        return result

    def govern_text(self, text: str) -> Any:
        """Govern arbitrary text."""
        if not self._tork:
            from ...core import Tork
            self._tork = Tork()
        return self._tork.govern(text)

    def _extract_content(self, data: dict) -> str:
        """Extract content from common body fields."""
        keys = ["content", "message", "text", "prompt", "query", "input"]
        for key in keys:
            if key in data and isinstance(data[key], str) and data[key]:
                return data[key]
        return ""


class TorkTornadoMiddleware:
    """Standalone Tornado middleware for governance."""

    def __init__(self, tork: Any = None, skip_paths: List[str] = None):
        self.tork = tork
        self.skip_paths = skip_paths or []

    def govern_request(self, handler) -> Optional[Any]:
        """Govern a Tornado request handler's body."""
        if not self.tork:
            from ...core import Tork
            self.tork = Tork()

        path = handler.request.path
        for skip in self.skip_paths:
            if path.startswith(skip):
                return None

        method = handler.request.method
        if method not in ("POST", "PUT", "PATCH"):
            return None

        body = handler.request.body
        if isinstance(body, bytes):
            body = body.decode("utf-8")

        if not body:
            return None

        import json
        try:
            data = json.loads(body)
            keys = ["content", "message", "text", "prompt", "query", "input"]
            content = ""
            for key in keys:
                if key in data and isinstance(data[key], str):
                    content = data[key]
                    break
        except (json.JSONDecodeError, TypeError):
            content = body

        if not content:
            return None

        return self.tork.govern(content)


def tornado_governed(tork: Any):
    """Decorator to govern Tornado handler methods."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            body = self.request.body
            if isinstance(body, bytes):
                body = body.decode("utf-8")

            import json
            try:
                data = json.loads(body)
                for key in ["content", "message", "text", "prompt"]:
                    if key in data and isinstance(data[key], str):
                        result = tork.govern(data[key])
                        data[key] = result.output if result.action in ('redact', 'REDACT') else data[key]
                self.request._tork_governed_body = data
            except (json.JSONDecodeError, TypeError, AttributeError):
                pass

            return func(self, *args, **kwargs)
        return wrapper
    return decorator
