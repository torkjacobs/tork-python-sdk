"""Tests for Sanic adapter."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from tork_governance.core import Tork


class TestTorkSanicMiddleware:
    """Tests for TorkSanicMiddleware."""

    def setup_method(self):
        self.tork = Tork()

    @pytest.mark.asyncio
    async def test_govern_post_request(self):
        """Test that governance is applied to POST requests."""
        from tork_governance.adapters.sanic_adapter import TorkSanicMiddleware

        middleware = TorkSanicMiddleware(tork=self.tork)

        request = MagicMock()
        request.path = "/chat"
        request.method = "POST"
        request.json = {"content": "My SSN is 123-45-6789"}
        request.ctx = MagicMock()

        await middleware.request_middleware(request)

        assert hasattr(request.ctx, 'tork_result')
        assert "[SSN_REDACTED]" in request.ctx.tork_result.output

    @pytest.mark.asyncio
    async def test_skip_get_requests(self):
        """Test that GET requests are skipped."""
        from tork_governance.adapters.sanic_adapter import TorkSanicMiddleware

        middleware = TorkSanicMiddleware(tork=self.tork)

        request = MagicMock()
        request.path = "/chat"
        request.method = "GET"

        result = await middleware.request_middleware(request)

        assert result is None

    @pytest.mark.asyncio
    async def test_skip_configured_paths(self):
        """Test that configured paths are skipped."""
        from tork_governance.adapters.sanic_adapter import TorkSanicMiddleware

        middleware = TorkSanicMiddleware(tork=self.tork, skip_paths=["/health"])

        request = MagicMock()
        request.path = "/health"
        request.method = "POST"

        result = await middleware.request_middleware(request)

        assert result is None

    @pytest.mark.asyncio
    async def test_govern_email_in_body(self):
        """Test that email PII is detected in body."""
        from tork_governance.adapters.sanic_adapter import TorkSanicMiddleware

        middleware = TorkSanicMiddleware(tork=self.tork)

        request = MagicMock()
        request.path = "/chat"
        request.method = "POST"
        request.json = {"message": "Contact admin@secret.com"}
        request.ctx = MagicMock()

        await middleware.request_middleware(request)

        assert "[EMAIL_REDACTED]" in request.ctx.tork_result.output


class TestSanicGoverned:
    """Tests for sanic_governed decorator."""

    @pytest.mark.asyncio
    async def test_decorator_governs_body(self):
        """Test that the decorator governs request body."""
        from tork_governance.adapters.sanic_adapter import sanic_governed

        tork = Tork()

        @sanic_governed(tork)
        async def handler(request):
            return request.ctx.tork_governed_body

        request = MagicMock()
        request.json = {"content": "My email is test@example.com"}
        request.ctx = MagicMock()

        await handler(request)

        governed = request.ctx.tork_governed_body
        assert "[EMAIL_REDACTED]" in governed["content"]
