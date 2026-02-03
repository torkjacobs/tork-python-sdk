"""
Flask Integration for Tork Governance

Provides extension and decorators for Flask applications.
"""

from functools import wraps
from typing import Any, Callable, Optional
from ..core import Tork, GovernanceResult, GovernanceAction


class TorkFlask:
    """
    Flask extension for Tork governance.

    Example:
        >>> from flask import Flask, request, g
        >>> from tork_governance.adapters.flask import TorkFlask
        >>>
        >>> app = Flask(__name__)
        >>> tork = TorkFlask(app)
        >>>
        >>> @app.route('/chat', methods=['POST'])
        >>> def chat():
        >>>     # g.tork_result contains governance result
        >>>     return {'message': 'ok'}
    """

    def __init__(
        self,
        app: Optional[Any] = None,
        api_key: Optional[str] = None,
        policy_version: str = "1.0.0"
    ):
        self.tork = Tork(api_key=api_key, policy_version=policy_version)
        self.app = app
        self._protected_paths = ['/api/']

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Any) -> None:
        """Initialize the extension with a Flask app."""
        self.app = app

        # Get config from app
        api_key = app.config.get('TORK_API_KEY')
        policy_version = app.config.get('TORK_POLICY_VERSION', '1.0.0')
        self._protected_paths = app.config.get('TORK_PROTECTED_PATHS', ['/api/'])

        if api_key:
            self.tork = Tork(api_key=api_key, policy_version=policy_version)

        # Register before_request handler
        app.before_request(self._before_request)

    def _before_request(self) -> Optional[Any]:
        """Before request hook to apply governance."""
        from flask import request, g, jsonify

        # Only process POST, PUT, PATCH
        if request.method not in ('POST', 'PUT', 'PATCH'):
            return None

        # Check if path should be protected
        if not any(request.path.startswith(p) for p in self._protected_paths):
            return None

        # Try to get JSON body
        try:
            data = request.get_json(silent=True)
            if not data:
                return None

            content = self._extract_content(data)
            if not content:
                return None

            result = self.tork.govern(content)
            g.tork_result = result

            if result.action == GovernanceAction.DENY:
                return jsonify({
                    'error': 'Request blocked by governance policy',
                    'receipt_id': result.receipt.receipt_id,
                    'pii_types': [t.value for t in result.pii.types]
                }), 403

        except Exception:
            pass  # Not JSON or other error, pass through

        return None

    def _extract_content(self, data: dict) -> Optional[str]:
        """Extract content from request body."""
        if isinstance(data, dict):
            for key in ('content', 'message', 'text', 'prompt', 'query'):
                if key in data and isinstance(data[key], str):
                    return data[key]
        return None

    def govern(self, content: str) -> GovernanceResult:
        """Manually govern content."""
        return self.tork.govern(content)


def tork_required(f: Callable) -> Callable:
    """
    Decorator that requires content to pass Tork governance.

    Example:
        >>> from flask import Flask, request
        >>> from tork_governance.adapters.flask import tork_required
        >>>
        >>> @app.route('/chat', methods=['POST'])
        >>> @tork_required
        >>> def chat():
        >>>     # request.tork_result contains governance result
        >>>     return {'message': 'ok'}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, g, jsonify

        # Get content from request
        data = request.get_json(silent=True)
        if not data:
            return f(*args, **kwargs)

        content = None
        for key in ('content', 'message', 'text', 'prompt', 'query'):
            if key in data and isinstance(data[key], str):
                content = data[key]
                break

        if not content:
            return f(*args, **kwargs)

        # Get or create Tork instance
        tork = getattr(g, '_tork', None)
        if not tork:
            from flask import current_app
            api_key = current_app.config.get('TORK_API_KEY')
            tork = Tork(api_key=api_key)
            g._tork = tork

        result = tork.govern(content)
        g.tork_result = result

        if result.action == GovernanceAction.DENY:
            return jsonify({
                'error': 'Content blocked by governance policy',
                'receipt_id': result.receipt.receipt_id
            }), 403

        return f(*args, **kwargs)

    return decorated_function
