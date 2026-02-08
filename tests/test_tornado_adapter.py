"""Tests for Tornado adapter."""

import pytest
from unittest.mock import MagicMock
from tork_governance.core import Tork


class TestTorkTornadoMiddleware:
    """Tests for TorkTornadoMiddleware."""

    def setup_method(self):
        self.tork = Tork()

    def test_govern_post_request(self):
        """Test that governance is applied to POST requests."""
        from tork_governance.adapters.tornado_adapter import TorkTornadoMiddleware

        middleware = TorkTornadoMiddleware(tork=self.tork)

        handler = MagicMock()
        handler.request.path = "/chat"
        handler.request.method = "POST"
        handler.request.body = b'{"content": "My SSN is 123-45-6789"}'

        result = middleware.govern_request(handler)

        assert result is not None
        assert "[SSN_REDACTED]" in result.output
        assert "123-45-6789" not in result.output

    def test_skip_get_requests(self):
        """Test that GET requests are skipped."""
        from tork_governance.adapters.tornado_adapter import TorkTornadoMiddleware

        middleware = TorkTornadoMiddleware(tork=self.tork)

        handler = MagicMock()
        handler.request.path = "/chat"
        handler.request.method = "GET"

        result = middleware.govern_request(handler)

        assert result is None

    def test_skip_configured_paths(self):
        """Test that configured paths are skipped."""
        from tork_governance.adapters.tornado_adapter import TorkTornadoMiddleware

        middleware = TorkTornadoMiddleware(tork=self.tork, skip_paths=["/health"])

        handler = MagicMock()
        handler.request.path = "/health"
        handler.request.method = "POST"
        handler.request.body = b'{"content": "SSN: 123-45-6789"}'

        result = middleware.govern_request(handler)

        assert result is None

    def test_govern_email_in_body(self):
        """Test that email PII is detected in body."""
        from tork_governance.adapters.tornado_adapter import TorkTornadoMiddleware

        middleware = TorkTornadoMiddleware(tork=self.tork)

        handler = MagicMock()
        handler.request.path = "/chat"
        handler.request.method = "POST"
        handler.request.body = b'{"message": "Contact admin@secret.com"}'

        result = middleware.govern_request(handler)

        assert result is not None
        assert "[EMAIL_REDACTED]" in result.output


class TestTornadoGoverned:
    """Tests for tornado_governed decorator."""

    def test_decorator_governs_body(self):
        """Test that the decorator governs request body."""
        from tork_governance.adapters.tornado_adapter import tornado_governed

        tork = Tork()

        handler = MagicMock()
        handler.request.body = b'{"content": "My email is test@example.com"}'

        @tornado_governed(tork)
        def post(self):
            return self.request._tork_governed_body

        post(handler)

        governed = handler.request._tork_governed_body
        assert "[EMAIL_REDACTED]" in governed["content"]
