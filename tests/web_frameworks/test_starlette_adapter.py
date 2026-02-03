"""
Tests for Starlette adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Middleware governance
- Route governance
- WebSocket governance
- Background task governance
"""

import pytest
import json
from typing import Dict, List
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.starlette import (
    TorkStarletteMiddleware,
    TorkStarletteRoute,
    tork_route,
    TorkStarletteWebSocket,
    TorkBackgroundTask,
    _govern_value,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class MockApp:
    """Mock ASGI app for testing."""

    def __init__(self):
        self.calls = []

    async def __call__(self, scope, receive, send):
        self.calls.append((scope, receive, send))
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json")],
        })
        await send({
            "type": "http.response.body",
            "body": b'{"status": "ok"}',
        })


class MockRequest:
    """Mock Starlette request for testing."""

    def __init__(self, body=None, json_data=None):
        self._body = body or b""
        self._json = json_data
        self.state = MockState()

    async def body(self):
        return self._body

    async def json(self):
        return self._json or {}


class MockState:
    """Mock request state."""

    def __init__(self):
        self.governed_body = None
        self.tork_result = None


class MockResponse:
    """Mock Starlette response for testing."""

    def __init__(self, body=None):
        self.body = body or b"{}"


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self._receive_queue = []
        self._sent = []

    async def accept(self):
        pass

    async def receive_text(self):
        if self._receive_queue:
            return self._receive_queue.pop(0)
        return ""

    async def send_text(self, data):
        self._sent.append(data)

    def queue_receive(self, text):
        self._receive_queue.append(text)


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


class TestStarletteImportInstantiation:
    """Test import and instantiation of Starlette adapter."""

    def test_import_middleware(self):
        """Test TorkStarletteMiddleware can be imported."""
        assert TorkStarletteMiddleware is not None

    def test_import_route(self):
        """Test TorkStarletteRoute can be imported."""
        assert TorkStarletteRoute is not None

    def test_import_decorator(self):
        """Test tork_route can be imported."""
        assert tork_route is not None

    def test_import_websocket(self):
        """Test TorkStarletteWebSocket can be imported."""
        assert TorkStarletteWebSocket is not None

    def test_import_background_task(self):
        """Test TorkBackgroundTask can be imported."""
        assert TorkBackgroundTask is not None

    def test_instantiate_middleware(self):
        """Test middleware instantiation."""
        app = MockApp()
        middleware = TorkStarletteMiddleware(app)
        assert middleware is not None
        assert middleware.app is app
        assert middleware.tork is not None

    def test_instantiate_route(self):
        """Test route wrapper instantiation."""
        route = TorkStarletteRoute()
        assert route is not None
        assert route.tork is not None

    def test_instantiate_websocket(self):
        """Test WebSocket handler instantiation."""
        ws = TorkStarletteWebSocket()
        assert ws is not None
        assert ws.tork is not None

    def test_instantiate_background_task(self):
        """Test background task instantiation."""
        task = TorkBackgroundTask()
        assert task is not None
        assert task.tork is not None


class TestStarletteConfiguration:
    """Test configuration of Starlette adapter."""

    def test_middleware_with_tork_instance(self):
        """Test middleware with existing Tork instance."""
        app = MockApp()
        tork = Tork()
        middleware = TorkStarletteMiddleware(app, tork=tork)
        assert middleware.tork is tork

    def test_middleware_with_api_key(self):
        """Test middleware with API key."""
        app = MockApp()
        middleware = TorkStarletteMiddleware(app, api_key="test-key")
        assert middleware.tork is not None

    def test_middleware_with_protected_paths(self):
        """Test middleware with custom protected paths."""
        app = MockApp()
        middleware = TorkStarletteMiddleware(app, protected_paths=["/custom/"])
        assert middleware.protected_paths == ["/custom/"]

    def test_middleware_with_excluded_paths(self):
        """Test middleware with custom excluded paths."""
        app = MockApp()
        middleware = TorkStarletteMiddleware(app, excluded_paths=["/skip/"])
        assert middleware.excluded_paths == ["/skip/"]

    def test_middleware_govern_input_option(self):
        """Test middleware with govern_input option."""
        app = MockApp()
        middleware = TorkStarletteMiddleware(app, govern_input=False)
        assert middleware.govern_input is False

    def test_middleware_govern_output_option(self):
        """Test middleware with govern_output option."""
        app = MockApp()
        middleware = TorkStarletteMiddleware(app, govern_output=False)
        assert middleware.govern_output is False

    def test_route_with_tork_instance(self):
        """Test route with existing Tork instance."""
        tork = Tork()
        route = TorkStarletteRoute(tork=tork)
        assert route.tork is tork

    def test_route_with_api_key(self):
        """Test route with API key."""
        route = TorkStarletteRoute(api_key="test-key")
        assert route.tork is not None

    def test_websocket_with_tork_instance(self):
        """Test WebSocket with existing Tork instance."""
        tork = Tork()
        ws = TorkStarletteWebSocket(tork=tork)
        assert ws.tork is tork

    def test_background_task_with_tork_instance(self):
        """Test background task with existing Tork instance."""
        tork = Tork()
        task = TorkBackgroundTask(tork=tork)
        assert task.tork is tork


class TestStarlettePIIDetection:
    """Test PII detection and redaction in Starlette adapter."""

    def test_govern_value_email_pii(self):
        """Test _govern_value governs email PII."""
        tork = Tork()
        receipts = []
        result = _govern_value(PII_MESSAGES["email_message"], tork, receipts, "input")
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_value_phone_pii(self):
        """Test _govern_value governs phone PII."""
        tork = Tork()
        receipts = []
        result = _govern_value(PII_MESSAGES["phone_message"], tork, receipts, "input")
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_value_ssn_pii(self):
        """Test _govern_value governs SSN PII."""
        tork = Tork()
        receipts = []
        result = _govern_value(PII_MESSAGES["ssn_message"], tork, receipts, "input")
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_value_credit_card_pii(self):
        """Test _govern_value governs credit card PII."""
        tork = Tork()
        receipts = []
        result = _govern_value(PII_MESSAGES["credit_card_message"], tork, receipts, "input")
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_value_clean_text(self):
        """Test _govern_value passes through clean text."""
        tork = Tork()
        receipts = []
        clean_text = "What is the weather today?"
        result = _govern_value(clean_text, tork, receipts, "input")
        assert result == clean_text


class TestStarletteErrorHandling:
    """Test error handling in Starlette adapter."""

    @pytest.mark.asyncio
    async def test_middleware_skips_non_http(self):
        """Test middleware skips non-HTTP requests."""
        app = MockApp()
        middleware = TorkStarletteMiddleware(app)

        scope = {"type": "websocket", "path": "/ws"}
        receive = create_mock_receive(b"")
        send = create_mock_send()

        await middleware(scope, receive, send)
        assert len(app.calls) == 1

    @pytest.mark.asyncio
    async def test_middleware_skips_excluded_paths(self):
        """Test middleware skips excluded paths."""
        app = MockApp()
        middleware = TorkStarletteMiddleware(app)

        scope = {"type": "http", "path": "/health"}
        receive = create_mock_receive(b"test")
        send = create_mock_send()

        await middleware(scope, receive, send)
        assert len(app.calls) == 1

    @pytest.mark.asyncio
    async def test_middleware_skips_unprotected_paths(self):
        """Test middleware skips unprotected paths."""
        app = MockApp()
        middleware = TorkStarletteMiddleware(app)

        scope = {"type": "http", "path": "/public/page"}
        receive = create_mock_receive(b"test")
        send = create_mock_send()

        await middleware(scope, receive, send)
        assert len(app.calls) == 1


class TestStarletteComplianceReceipts:
    """Test compliance receipt generation in Starlette adapter."""

    def test_govern_value_generates_receipt(self):
        """Test _govern_value generates receipt."""
        tork = Tork()
        receipts = []
        _govern_value("Test message", tork, receipts, "input")
        assert len(receipts) == 1
        assert "receipt_id" in receipts[0]
        assert receipts[0]["type"] == "input_string"

    def test_middleware_get_receipts(self):
        """Test middleware get_receipts method."""
        app = MockApp()
        middleware = TorkStarletteMiddleware(app)
        receipts = middleware.get_receipts()
        assert isinstance(receipts, list)

    def test_route_get_receipts(self):
        """Test route get_receipts method."""
        route = TorkStarletteRoute()
        receipts = route.get_receipts()
        assert isinstance(receipts, list)

    def test_websocket_get_receipts(self):
        """Test WebSocket get_receipts method."""
        ws = TorkStarletteWebSocket()
        receipts = ws.get_receipts()
        assert isinstance(receipts, list)

    def test_background_task_get_receipts(self):
        """Test background task get_receipts method."""
        task = TorkBackgroundTask()
        receipts = task.get_receipts()
        assert isinstance(receipts, list)


class TestStarletteMiddlewareGovernance:
    """Test middleware governance behavior."""

    @pytest.mark.asyncio
    async def test_middleware_processes_protected_path(self):
        """Test middleware processes protected paths."""
        app = MockApp()
        middleware = TorkStarletteMiddleware(app)

        scope = {"type": "http", "path": "/api/test"}
        receive = create_mock_receive(b"test content")
        send = create_mock_send()

        await middleware(scope, receive, send)
        assert len(app.calls) == 1

    @pytest.mark.asyncio
    async def test_middleware_governs_request_body(self):
        """Test middleware governs request body."""
        received_bodies = []

        async def capturing_app(scope, receive, send):
            message = await receive()
            received_bodies.append(message.get("body", b""))
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        middleware = TorkStarletteMiddleware(capturing_app)

        body = PII_MESSAGES["email_message"].encode("utf-8")
        scope = {"type": "http", "path": "/api/test"}
        receive = create_mock_receive(body)
        send = create_mock_send()

        await middleware(scope, receive, send)

        assert len(received_bodies) == 1
        received_text = received_bodies[0].decode("utf-8")
        assert PII_SAMPLES["email"] not in received_text


class TestStarletteRouteGovernance:
    """Test route wrapper governance."""

    def test_route_wrap_returns_callable(self):
        """Test route wrap returns callable."""
        route = TorkStarletteRoute()

        async def my_handler(request):
            return MockResponse()

        wrapped = route.wrap(my_handler)
        assert callable(wrapped)

    def test_route_wrap_preserves_function_name(self):
        """Test route wrap preserves function name."""
        route = TorkStarletteRoute()

        async def my_handler(request):
            return MockResponse()

        wrapped = route.wrap(my_handler)
        assert wrapped.__name__ == "my_handler"

    @pytest.mark.asyncio
    async def test_route_processes_request(self):
        """Test route processes request."""
        route = TorkStarletteRoute()

        async def my_handler(request):
            return MockResponse(b'{"result": "ok"}')

        wrapped = route.wrap(my_handler)
        request = MockRequest()
        response = await wrapped(request)
        assert response is not None


class TestStarletteTorkRouteDecorator:
    """Test tork_route decorator."""

    def test_decorator_is_callable(self):
        """Test tork_route is callable."""
        assert callable(tork_route)

    def test_decorator_returns_decorator(self):
        """Test tork_route returns a decorator."""
        decorator = tork_route()
        assert callable(decorator)

    def test_decorator_wraps_function(self):
        """Test decorator wraps function."""
        @tork_route()
        async def my_handler(request):
            return MockResponse()

        assert my_handler.__name__ == "my_handler"

    def test_decorator_with_tork_instance(self):
        """Test decorator with Tork instance."""
        tork = Tork()

        @tork_route(tork=tork)
        async def my_handler(request):
            return MockResponse()

        assert callable(my_handler)

    def test_decorator_govern_input_option(self):
        """Test decorator with govern_input option."""
        @tork_route(govern_input=False)
        async def my_handler(request):
            return MockResponse()

        assert callable(my_handler)

    def test_decorator_govern_output_option(self):
        """Test decorator with govern_output option."""
        @tork_route(govern_output=False)
        async def my_handler(request):
            return MockResponse()

        assert callable(my_handler)

    @pytest.mark.asyncio
    async def test_decorator_processes_request(self):
        """Test decorator processes request."""
        @tork_route()
        async def my_handler(request):
            return MockResponse(b'{"result": "ok"}')

        request = MockRequest()
        response = await my_handler(request)
        assert response is not None

    def test_decorator_has_get_receipts(self):
        """Test decorated function has get_receipts."""
        @tork_route()
        async def my_handler(request):
            return MockResponse()

        assert hasattr(my_handler, "get_receipts")
        assert callable(my_handler.get_receipts)


class TestStarletteWebSocketGovernance:
    """Test WebSocket handler governance."""

    def test_websocket_wrap_returns_callable(self):
        """Test WebSocket wrap returns callable."""
        ws = TorkStarletteWebSocket()

        async def my_handler(websocket):
            pass

        wrapped = ws.wrap(my_handler)
        assert callable(wrapped)

    def test_websocket_wrap_preserves_function_name(self):
        """Test WebSocket wrap preserves function name."""
        ws = TorkStarletteWebSocket()

        async def my_handler(websocket):
            pass

        wrapped = ws.wrap(my_handler)
        assert wrapped.__name__ == "my_handler"

    @pytest.mark.asyncio
    async def test_websocket_governs_receive_text(self):
        """Test WebSocket governs receive_text."""
        ws = TorkStarletteWebSocket()

        async def my_handler(websocket):
            text = await websocket.receive_text()
            return text

        wrapped = ws.wrap(my_handler)
        mock_ws = MockWebSocket()
        mock_ws.queue_receive(PII_MESSAGES["email_message"])

        result = await wrapped(mock_ws)
        assert PII_SAMPLES["email"] not in result

    @pytest.mark.asyncio
    async def test_websocket_governs_send_text(self):
        """Test WebSocket governs send_text."""
        ws = TorkStarletteWebSocket()

        async def my_handler(websocket):
            await websocket.send_text(PII_MESSAGES["phone_message"])

        wrapped = ws.wrap(my_handler)
        mock_ws = MockWebSocket()

        await wrapped(mock_ws)
        assert len(mock_ws._sent) == 1
        assert PII_SAMPLES["phone_us"] not in mock_ws._sent[0]

    @pytest.mark.asyncio
    async def test_websocket_generates_receipts(self):
        """Test WebSocket generates receipts."""
        ws = TorkStarletteWebSocket()

        async def my_handler(websocket):
            await websocket.receive_text()

        wrapped = ws.wrap(my_handler)
        mock_ws = MockWebSocket()
        mock_ws.queue_receive("test message")

        await wrapped(mock_ws)
        receipts = ws.get_receipts()
        assert len(receipts) >= 1


class TestStarletteBackgroundTaskGovernance:
    """Test background task governance."""

    def test_background_task_wrap_returns_callable(self):
        """Test background task wrap returns callable."""
        task = TorkBackgroundTask()

        async def my_task(data):
            return data

        wrapped = task.wrap(my_task)
        assert callable(wrapped)

    def test_background_task_wrap_preserves_function_name(self):
        """Test background task wrap preserves function name."""
        task = TorkBackgroundTask()

        async def my_task(data):
            return data

        wrapped = task.wrap(my_task)
        assert wrapped.__name__ == "my_task"

    @pytest.mark.asyncio
    async def test_background_task_governs_string_args(self):
        """Test background task governs string arguments."""
        task = TorkBackgroundTask()

        async def my_task(data):
            return data

        wrapped = task.wrap(my_task)
        result = await wrapped(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result

    @pytest.mark.asyncio
    async def test_background_task_governs_string_kwargs(self):
        """Test background task governs string kwargs."""
        task = TorkBackgroundTask()

        async def my_task(data=None):
            return data

        wrapped = task.wrap(my_task)
        result = await wrapped(data=PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result

    @pytest.mark.asyncio
    async def test_background_task_passes_non_strings(self):
        """Test background task passes non-string args."""
        task = TorkBackgroundTask()

        async def my_task(data, count):
            return data, count

        wrapped = task.wrap(my_task)
        result = await wrapped("test", 42)
        assert result[1] == 42

    @pytest.mark.asyncio
    async def test_background_task_generates_receipts(self):
        """Test background task generates receipts."""
        task = TorkBackgroundTask()

        async def my_task(data):
            return data

        wrapped = task.wrap(my_task)
        await wrapped("test message")
        receipts = task.get_receipts()
        assert len(receipts) >= 1


class TestGovernValueHelper:
    """Test _govern_value helper function."""

    def test_govern_value_string(self):
        """Test _govern_value with string."""
        tork = Tork()
        receipts = []
        result = _govern_value("test", tork, receipts, "input")
        assert result == "test"

    def test_govern_value_dict(self):
        """Test _govern_value with dict."""
        tork = Tork()
        receipts = []
        result = _govern_value({"key": "value"}, tork, receipts, "input")
        assert isinstance(result, dict)
        assert result["key"] == "value"

    def test_govern_value_list(self):
        """Test _govern_value with list."""
        tork = Tork()
        receipts = []
        result = _govern_value(["a", "b", "c"], tork, receipts, "input")
        assert isinstance(result, list)
        assert len(result) == 3

    def test_govern_value_nested_dict_with_pii(self):
        """Test _govern_value with nested dict containing PII."""
        tork = Tork()
        receipts = []
        data = {
            "user": {
                "email": PII_MESSAGES["email_message"]
            }
        }
        result = _govern_value(data, tork, receipts, "input")
        assert PII_SAMPLES["email"] not in result["user"]["email"]

    def test_govern_value_list_with_pii(self):
        """Test _govern_value with list containing PII."""
        tork = Tork()
        receipts = []
        data = [PII_MESSAGES["email_message"], PII_MESSAGES["phone_message"]]
        result = _govern_value(data, tork, receipts, "input")
        assert PII_SAMPLES["email"] not in result[0]
        assert PII_SAMPLES["phone_us"] not in result[1]

    def test_govern_value_passthrough_non_string_non_container(self):
        """Test _govern_value passes through non-string, non-container values."""
        tork = Tork()
        receipts = []

        assert _govern_value(42, tork, receipts, "input") == 42
        assert _govern_value(3.14, tork, receipts, "input") == 3.14
        assert _govern_value(True, tork, receipts, "input") is True
        assert _govern_value(None, tork, receipts, "input") is None
