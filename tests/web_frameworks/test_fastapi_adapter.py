"""
Tests for FastAPI adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Middleware governance
- Dependency injection governance
- ASGI interface
"""

import pytest
import json
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.fastapi import (
    TorkFastAPIMiddleware,
    TorkFastAPIDependency,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class MockApp:
    """Mock ASGI app for testing."""

    def __init__(self):
        self.calls = []

    async def __call__(self, scope, receive, send):
        self.calls.append((scope, receive, send))
        # Send a basic response
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json")],
        })
        await send({
            "type": "http.response.body",
            "body": b'{"status": "ok"}',
        })


def create_mock_receive(body: bytes):
    """Create a mock receive function."""
    sent = False

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    return receive


def create_mock_send():
    """Create a mock send function."""
    messages = []

    async def send(message):
        messages.append(message)

    send.messages = messages
    return send


class TestFastAPIImportInstantiation:
    """Test import and instantiation of FastAPI adapter."""

    def test_import_middleware(self):
        """Test TorkFastAPIMiddleware can be imported."""
        assert TorkFastAPIMiddleware is not None

    def test_import_dependency(self):
        """Test TorkFastAPIDependency can be imported."""
        assert TorkFastAPIDependency is not None

    def test_instantiate_middleware(self):
        """Test middleware instantiation."""
        app = MockApp()
        middleware = TorkFastAPIMiddleware(app)
        assert middleware is not None
        assert middleware.app is app
        assert middleware.tork is not None

    def test_instantiate_dependency(self):
        """Test dependency instantiation."""
        dep = TorkFastAPIDependency()
        assert dep is not None
        assert dep.tork is not None


class TestFastAPIConfiguration:
    """Test configuration of FastAPI adapter."""

    def test_middleware_with_tork_instance(self):
        """Test middleware with existing Tork instance."""
        app = MockApp()
        tork = Tork()
        middleware = TorkFastAPIMiddleware(app, tork=tork)
        assert middleware.tork is tork

    def test_middleware_with_api_key(self):
        """Test middleware with API key."""
        app = MockApp()
        middleware = TorkFastAPIMiddleware(app, api_key="test-key")
        assert middleware.tork is not None

    def test_middleware_with_skip_paths(self):
        """Test middleware with skip paths."""
        app = MockApp()
        middleware = TorkFastAPIMiddleware(app, skip_paths=["/health", "/metrics"])
        assert middleware.skip_paths == ["/health", "/metrics"]

    def test_middleware_custom_content_extractor(self):
        """Test middleware with custom content extractor."""
        app = MockApp()

        def custom_extractor(data):
            return data.get("custom_field")

        middleware = TorkFastAPIMiddleware(app, extract_content=custom_extractor)
        assert middleware.extract_content == custom_extractor

    def test_dependency_with_tork_instance(self):
        """Test dependency with existing Tork instance."""
        tork = Tork()
        dep = TorkFastAPIDependency(tork=tork)
        assert dep.tork is tork


class TestFastAPIPIIDetection:
    """Test PII detection and redaction in FastAPI adapter."""

    def test_dependency_govern_email_pii(self):
        """Test dependency detects and governs email PII."""
        dep = TorkFastAPIDependency()
        result = dep.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result.output
        assert "[EMAIL_REDACTED]" in result.output

    def test_dependency_govern_phone_pii(self):
        """Test dependency detects and governs phone PII."""
        dep = TorkFastAPIDependency()
        result = dep.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result.output
        assert "[PHONE_REDACTED]" in result.output

    def test_dependency_govern_ssn_pii(self):
        """Test dependency detects and governs SSN PII."""
        dep = TorkFastAPIDependency()
        result = dep.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result.output
        assert "[SSN_REDACTED]" in result.output

    def test_dependency_govern_credit_card_pii(self):
        """Test dependency detects and governs credit card PII."""
        dep = TorkFastAPIDependency()
        result = dep.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result.output
        assert "[CARD_REDACTED]" in result.output

    def test_dependency_clean_text_passthrough(self):
        """Test dependency passes through clean text."""
        dep = TorkFastAPIDependency()
        clean_text = "What is the weather today?"
        result = dep.govern(clean_text)
        assert result.output == clean_text
        assert result.action == GovernanceAction.ALLOW


class TestFastAPIErrorHandling:
    """Test error handling in FastAPI adapter."""

    @pytest.mark.asyncio
    async def test_middleware_skips_non_http(self):
        """Test middleware skips non-HTTP requests."""
        app = MockApp()
        middleware = TorkFastAPIMiddleware(app)

        scope = {"type": "websocket", "path": "/ws"}
        receive = create_mock_receive(b"")
        send = create_mock_send()

        await middleware(scope, receive, send)
        assert len(app.calls) == 1

    @pytest.mark.asyncio
    async def test_middleware_skips_get_requests(self):
        """Test middleware skips GET requests."""
        app = MockApp()
        middleware = TorkFastAPIMiddleware(app)

        scope = {"type": "http", "method": "GET", "path": "/api/test"}
        receive = create_mock_receive(b"")
        send = create_mock_send()

        await middleware(scope, receive, send)
        assert len(app.calls) == 1

    @pytest.mark.asyncio
    async def test_middleware_skips_skip_paths(self):
        """Test middleware skips configured skip paths."""
        app = MockApp()
        middleware = TorkFastAPIMiddleware(app, skip_paths=["/health"])

        scope = {"type": "http", "method": "POST", "path": "/health"}
        receive = create_mock_receive(b'{"content": "test"}')
        send = create_mock_send()

        await middleware(scope, receive, send)
        assert len(app.calls) == 1

    @pytest.mark.asyncio
    async def test_middleware_handles_invalid_json(self):
        """Test middleware handles invalid JSON."""
        app = MockApp()
        middleware = TorkFastAPIMiddleware(app)

        scope = {"type": "http", "method": "POST", "path": "/api/test"}
        receive = create_mock_receive(b"not valid json")
        send = create_mock_send()

        await middleware(scope, receive, send)
        # Should still call app
        assert len(app.calls) == 1

    def test_dependency_handles_empty_string(self):
        """Test dependency handles empty string."""
        dep = TorkFastAPIDependency()
        result = dep.govern("")
        assert result.output == ""


class TestFastAPIComplianceReceipts:
    """Test compliance receipt generation in FastAPI adapter."""

    def test_dependency_generates_receipt(self):
        """Test dependency generates governance receipt."""
        dep = TorkFastAPIDependency()
        result = dep.govern("Test message")

        assert result.receipt is not None
        assert result.receipt.receipt_id is not None

    @pytest.mark.asyncio
    async def test_dependency_callable_returns_result(self):
        """Test dependency callable returns GovernanceResult."""
        dep = TorkFastAPIDependency()
        result = await dep("Test content")

        assert result is not None
        assert result.receipt is not None


class TestFastAPIMiddlewareGovernance:
    """Test middleware governance behavior."""

    @pytest.mark.asyncio
    async def test_middleware_processes_post(self):
        """Test middleware processes POST requests."""
        app = MockApp()
        middleware = TorkFastAPIMiddleware(app)

        body = json.dumps({"content": "test"}).encode("utf-8")
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/test",
            "state": {}
        }
        receive = create_mock_receive(body)
        send = create_mock_send()

        await middleware(scope, receive, send)
        assert len(app.calls) == 1

    @pytest.mark.asyncio
    async def test_middleware_governs_content(self):
        """Test middleware governs content field."""
        app = MockApp()
        middleware = TorkFastAPIMiddleware(app)

        body = json.dumps({"content": PII_MESSAGES["email_message"]}).encode("utf-8")
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/test",
            "state": {}
        }
        receive = create_mock_receive(body)
        send = create_mock_send()

        await middleware(scope, receive, send)

        # Check that tork_result is in scope state
        assert "tork_result" in scope.get("state", {})

    @pytest.mark.asyncio
    async def test_middleware_default_content_extraction(self):
        """Test middleware default content extraction."""
        app = MockApp()
        middleware = TorkFastAPIMiddleware(app)

        # Test various field names
        for field in ["content", "message", "text", "prompt", "query"]:
            body = json.dumps({field: "test"}).encode("utf-8")
            content = middleware._default_extract_content(json.loads(body.decode()))
            assert content == "test"

    @pytest.mark.asyncio
    async def test_middleware_no_extraction_for_unknown_field(self):
        """Test middleware doesn't extract from unknown fields."""
        app = MockApp()
        middleware = TorkFastAPIMiddleware(app)

        data = {"unknown_field": "test"}
        content = middleware._default_extract_content(data)
        assert content is None


class TestFastAPIDependencyGovernance:
    """Test dependency injection governance."""

    def test_dependency_govern_method(self):
        """Test dependency govern method."""
        dep = TorkFastAPIDependency()
        result = dep.govern(PII_MESSAGES["ssn_message"])

        assert result.action == GovernanceAction.REDACT
        assert PII_SAMPLES["ssn"] not in result.output

    @pytest.mark.asyncio
    async def test_dependency_as_callable(self):
        """Test dependency as async callable."""
        dep = TorkFastAPIDependency()
        result = await dep(PII_MESSAGES["phone_message"])

        assert result.action == GovernanceAction.REDACT
        assert PII_SAMPLES["phone_us"] not in result.output

    def test_dependency_with_policy_version(self):
        """Test dependency with custom policy version."""
        dep = TorkFastAPIDependency(policy_version="2.0.0")
        assert dep.tork is not None


class TestFastAPIASGIInterface:
    """Test ASGI interface behavior."""

    @pytest.mark.asyncio
    async def test_asgi_scope_state_preserved(self):
        """Test ASGI scope state is preserved."""
        app = MockApp()
        middleware = TorkFastAPIMiddleware(app)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/test",
            "state": {"existing": "value"}
        }
        body = json.dumps({"content": "test"}).encode("utf-8")
        receive = create_mock_receive(body)
        send = create_mock_send()

        await middleware(scope, receive, send)

        # Existing state should be preserved
        assert scope["state"]["existing"] == "value"

    @pytest.mark.asyncio
    async def test_asgi_passes_modified_receive(self):
        """Test ASGI passes modified receive to app."""
        received_bodies = []

        async def capturing_app(scope, receive, send):
            message = await receive()
            received_bodies.append(message.get("body", b""))
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        middleware = TorkFastAPIMiddleware(capturing_app)

        body = json.dumps({"content": PII_MESSAGES["email_message"]}).encode("utf-8")
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/test",
            "state": {}
        }
        receive = create_mock_receive(body)
        send = create_mock_send()

        await middleware(scope, receive, send)

        # Body should have been modified (email redacted)
        assert len(received_bodies) == 1
        modified_body = json.loads(received_bodies[0].decode("utf-8"))
        assert PII_SAMPLES["email"] not in modified_body.get("content", "")
