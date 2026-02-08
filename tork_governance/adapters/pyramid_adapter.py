"""
Tork Governance adapter for Pyramid.

Provides governance as a Pyramid tween for automatic PII detection
and policy enforcement in Pyramid web applications.

Usage:
    from tork_governance.adapters.pyramid_adapter import TorkPyramidTween

    config.add_tween('tork_governance.adapters.pyramid_adapter.tork_tween_factory')
"""

from typing import Any, Dict, List, Optional
from functools import wraps


class TorkPyramidTween:
    """Pyramid tween for Tork governance."""

    def __init__(
        self,
        handler: Any,
        registry: Any,
        tork: Any = None,
        skip_paths: List[str] = None,
    ):
        self.handler = handler
        self.registry = registry
        self.tork = tork
        self.skip_paths = skip_paths or []

    def __call__(self, request):
        """Process a Pyramid request with governance."""
        if not self.tork:
            return self.handler(request)

        # Skip configured paths
        path = request.path
        for skip in self.skip_paths:
            if path.startswith(skip):
                return self.handler(request)

        # Only process mutating methods
        method = request.method
        if method not in ("POST", "PUT", "PATCH"):
            return self.handler(request)

        # Extract and govern body
        try:
            body = request.json_body
            content = self._extract_content(body)
            if content:
                result = self.tork.govern(content)
                request.tork_result = result
        except Exception:
            pass

        return self.handler(request)

    def _extract_content(self, data: dict) -> str:
        """Extract content from common body fields."""
        keys = ["content", "message", "text", "prompt", "query", "input"]
        for key in keys:
            if key in data and isinstance(data[key], str) and data[key]:
                return data[key]
        return ""


def tork_tween_factory(handler, registry, tork=None, skip_paths=None):
    """Factory function for creating Tork Pyramid tweens."""
    return TorkPyramidTween(handler, registry, tork=tork, skip_paths=skip_paths)


class TorkPyramidMiddleware:
    """Standalone Pyramid middleware for governance."""

    def __init__(self, tork: Any = None, skip_paths: List[str] = None):
        self.tork = tork
        self.skip_paths = skip_paths or []

    def govern_request(self, request) -> Optional[Any]:
        """Govern a Pyramid request."""
        if not self.tork:
            from ...core import Tork
            self.tork = Tork()

        path = getattr(request, 'path', '')
        for skip in self.skip_paths:
            if path.startswith(skip):
                return None

        method = getattr(request, 'method', 'GET')
        if method not in ("POST", "PUT", "PATCH"):
            return None

        try:
            body = request.json_body
        except Exception:
            return None

        content = self._extract_content(body)
        if not content:
            return None

        return self.tork.govern(content)

    def _extract_content(self, data: dict) -> str:
        keys = ["content", "message", "text", "prompt", "query", "input"]
        for key in keys:
            if key in data and isinstance(data[key], str) and data[key]:
                return data[key]
        return ""


def pyramid_governed(tork: Any):
    """Decorator to govern Pyramid view functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                body = request.json_body
                for key in ["content", "message", "text", "prompt"]:
                    if key in body and isinstance(body[key], str):
                        result = tork.govern(body[key])
                        body[key] = result.output if result.action in ('redact', 'REDACT') else body[key]
                request.tork_governed_body = body
            except Exception:
                pass
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
