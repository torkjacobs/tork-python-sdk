"""
Django Integration for Tork Governance

Provides middleware for Django applications.
"""

import json
from typing import Any, Callable, Optional, List
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkDjangoMiddleware:
    """
    Django middleware that applies Tork governance to requests.

    Add to MIDDLEWARE in settings.py:
        MIDDLEWARE = [
            ...
            'tork_governance.adapters.django.TorkDjangoMiddleware',
        ]

    Configure in settings.py:
        TORK_API_KEY = 'your_api_key'
        TORK_POLICY_VERSION = '1.0.0'
        TORK_PROTECTED_PATHS = ['/api/chat/', '/api/generate/']

    Example:
        >>> # settings.py
        >>> MIDDLEWARE = [
        >>>     'django.middleware.security.SecurityMiddleware',
        >>>     'tork_governance.adapters.django.TorkDjangoMiddleware',
        >>>     ...
        >>> ]
        >>> TORK_API_KEY = 'your_api_key'
        >>>
        >>> # views.py
        >>> def chat_view(request):
        >>>     # Access governance result
        >>>     tork_result = getattr(request, 'tork_result', None)
        >>>     return JsonResponse({'message': 'ok'})
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

        # Import Django settings
        try:
            from django.conf import settings
            api_key = getattr(settings, 'TORK_API_KEY', None)
            policy_version = getattr(settings, 'TORK_POLICY_VERSION', '1.0.0')
            self.protected_paths = getattr(settings, 'TORK_PROTECTED_PATHS', ['/api/'])
        except ImportError:
            api_key = None
            policy_version = '1.0.0'
            self.protected_paths = ['/api/']

        self.tork = Tork(api_key=api_key, policy_version=policy_version)

    def __call__(self, request: Any) -> Any:
        # Only process POST, PUT, PATCH to protected paths
        if request.method not in ('POST', 'PUT', 'PATCH'):
            return self.get_response(request)

        if not any(request.path.startswith(p) for p in self.protected_paths):
            return self.get_response(request)

        # Try to parse body and govern
        try:
            body = json.loads(request.body.decode('utf-8'))
            content = self._extract_content(body)

            if content:
                result = self.tork.govern(content)
                request.tork_result = result

                if result.action == GovernanceAction.DENY:
                    from django.http import JsonResponse
                    return JsonResponse({
                        'error': 'Request blocked by governance policy',
                        'receipt_id': result.receipt.receipt_id,
                        'pii_types': [t.value for t in result.pii.types]
                    }, status=403)

                # Store redacted content for views to use
                if result.action == GovernanceAction.REDACT and result.pii.has_pii:
                    request.tork_redacted_content = result.output

        except (json.JSONDecodeError, UnicodeDecodeError):
            pass  # Not JSON, pass through

        return self.get_response(request)

    def _extract_content(self, data: dict) -> Optional[str]:
        """Extract content from request body."""
        if isinstance(data, dict):
            for key in ('content', 'message', 'text', 'prompt', 'query'):
                if key in data and isinstance(data[key], str):
                    return data[key]
        return None


def tork_protected(view_func: Callable) -> Callable:
    """
    Decorator for Django views that require Tork governance.

    Example:
        >>> from tork_governance.adapters.django import tork_protected
        >>>
        >>> @tork_protected
        >>> def my_view(request):
        >>>     # request.tork_result is available
        >>>     return JsonResponse({'message': 'ok'})
    """
    def wrapper(request, *args, **kwargs):
        # Check if tork_result exists and action is not deny
        tork_result = getattr(request, 'tork_result', None)
        if tork_result and tork_result.action == GovernanceAction.DENY:
            from django.http import JsonResponse
            return JsonResponse({
                'error': 'Content blocked by governance policy',
                'receipt_id': tork_result.receipt.receipt_id
            }, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper
