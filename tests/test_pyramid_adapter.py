"""Tests for Pyramid adapter."""

import pytest
from unittest.mock import MagicMock, PropertyMock
from tork_governance.core import Tork


class TestTorkPyramidMiddleware:
    """Tests for TorkPyramidMiddleware."""

    def setup_method(self):
        self.tork = Tork()

    def test_govern_post_request(self):
        """Test that governance is applied to POST requests."""
        from tork_governance.adapters.pyramid_adapter import TorkPyramidMiddleware

        middleware = TorkPyramidMiddleware(tork=self.tork)

        request = MagicMock()
        request.path = "/chat"
        request.method = "POST"
        request.json_body = {"content": "My SSN is 123-45-6789"}

        result = middleware.govern_request(request)

        assert result is not None
        assert "[SSN_REDACTED]" in result.output
        assert "123-45-6789" not in result.output

    def test_skip_get_requests(self):
        """Test that GET requests are skipped."""
        from tork_governance.adapters.pyramid_adapter import TorkPyramidMiddleware

        middleware = TorkPyramidMiddleware(tork=self.tork)

        request = MagicMock()
        request.path = "/chat"
        request.method = "GET"

        result = middleware.govern_request(request)

        assert result is None

    def test_skip_configured_paths(self):
        """Test that configured paths are skipped."""
        from tork_governance.adapters.pyramid_adapter import TorkPyramidMiddleware

        middleware = TorkPyramidMiddleware(tork=self.tork, skip_paths=["/health"])

        request = MagicMock()
        request.path = "/health"
        request.method = "POST"

        result = middleware.govern_request(request)

        assert result is None

    def test_govern_email_in_body(self):
        """Test that email PII is detected in body."""
        from tork_governance.adapters.pyramid_adapter import TorkPyramidMiddleware

        middleware = TorkPyramidMiddleware(tork=self.tork)

        request = MagicMock()
        request.path = "/chat"
        request.method = "POST"
        request.json_body = {"message": "Contact admin@secret.com"}

        result = middleware.govern_request(request)

        assert result is not None
        assert "[EMAIL_REDACTED]" in result.output


class TestTorkPyramidTween:
    """Tests for TorkPyramidTween."""

    def test_tween_governs_request(self):
        """Test that tween applies governance to request."""
        from tork_governance.adapters.pyramid_adapter import TorkPyramidTween

        tork = Tork()
        handler = MagicMock(return_value="response")

        tween = TorkPyramidTween(handler, registry=None, tork=tork)

        request = MagicMock()
        request.path = "/chat"
        request.method = "POST"
        request.json_body = {"content": "SSN: 123-45-6789"}

        tween(request)

        assert hasattr(request, 'tork_result')
        assert "[SSN_REDACTED]" in request.tork_result.output


class TestPyramidGoverned:
    """Tests for pyramid_governed decorator."""

    def test_decorator_governs_body(self):
        """Test that the decorator governs request body."""
        from tork_governance.adapters.pyramid_adapter import pyramid_governed

        tork = Tork()

        @pyramid_governed(tork)
        def view(request):
            return request.tork_governed_body

        request = MagicMock()
        request.json_body = {"content": "My email is test@example.com"}

        view(request)

        governed = request.tork_governed_body
        assert "[EMAIL_REDACTED]" in governed["content"]
