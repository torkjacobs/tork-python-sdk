"""
Pytest configuration for web framework adapter tests.
"""

import pytest
from tork_governance import Tork


@pytest.fixture
def tork_instance():
    """Create a Tork instance for testing."""
    return Tork()


@pytest.fixture
def mock_request():
    """Create a mock HTTP request."""
    class MockRequest:
        def __init__(self):
            self.method = "POST"
            self.path = "/api/chat"
            self.body = b'{"content": "Test message"}'
            self._json = {"content": "Test message"}

        def get_json(self, silent=False):
            return self._json

    return MockRequest()


@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""
    class MockResponse:
        def __init__(self, body=b"", status_code=200):
            self.body = body
            self.status_code = status_code

    return MockResponse


@pytest.fixture
def mock_scope():
    """Create a mock ASGI scope."""
    return {
        "type": "http",
        "method": "POST",
        "path": "/api/chat",
        "headers": [(b"content-type", b"application/json")],
    }


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    class MockWebSocket:
        def __init__(self):
            self._received = []
            self._sent = []
            self._receive_queue = []

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

    return MockWebSocket()
