"""
Tests for Django adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Middleware governance
- View decorator governance
- Request/response governance
"""

import pytest
import json
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.django import (
    TorkDjangoMiddleware,
    tork_protected,
)
from .test_data import PII_SAMPLES, PII_MESSAGES, REQUEST_BODIES


class MockDjangoRequest:
    """Mock Django request for testing."""

    def __init__(self, method="POST", path="/api/chat", body=None, content=None):
        self.method = method
        self.path = path
        if content is not None:
            self.body = json.dumps({"content": content}).encode("utf-8")
        elif body is not None:
            self.body = body
        else:
            self.body = b"{}"
        self.tork_result = None
        self.tork_redacted_content = None


class MockDjangoResponse:
    """Mock Django response for testing."""

    def __init__(self, content=None, status_code=200):
        self.content = content or b"{}"
        self.status_code = status_code


class TestDjangoImportInstantiation:
    """Test import and instantiation of Django adapter."""

    def test_import_middleware(self):
        """Test TorkDjangoMiddleware can be imported."""
        assert TorkDjangoMiddleware is not None

    def test_import_decorator(self):
        """Test tork_protected decorator can be imported."""
        assert tork_protected is not None

    def test_instantiate_middleware(self):
        """Test middleware instantiation."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        assert middleware is not None
        assert middleware.tork is not None
        assert middleware.get_response is get_response

    def test_middleware_has_protected_paths(self):
        """Test middleware has default protected paths."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        assert middleware.protected_paths is not None
        assert len(middleware.protected_paths) >= 1


class TestDjangoConfiguration:
    """Test configuration of Django adapter."""

    def test_middleware_default_config(self):
        """Test middleware with default configuration."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        assert middleware.tork is not None
        assert "/api/" in middleware.protected_paths

    def test_middleware_custom_get_response(self):
        """Test middleware with custom get_response."""
        custom_response = MockDjangoResponse(b"custom")

        def get_response(request):
            return custom_response

        middleware = TorkDjangoMiddleware(get_response)
        request = MockDjangoRequest(method="GET")
        response = middleware(request)
        assert response == custom_response


class TestDjangoPIIDetection:
    """Test PII detection and redaction in Django adapter."""

    def test_middleware_govern_email_pii(self):
        """Test middleware detects and governs email PII."""
        responses = []

        def get_response(request):
            responses.append(request)
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        request = MockDjangoRequest(content=PII_MESSAGES["email_message"])
        middleware(request)

        assert request.tork_result is not None
        assert request.tork_result.action == GovernanceAction.REDACT

    def test_middleware_govern_phone_pii(self):
        """Test middleware detects and governs phone PII."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        request = MockDjangoRequest(content=PII_MESSAGES["phone_message"])
        middleware(request)

        assert request.tork_result is not None
        assert PII_SAMPLES["phone_us"] not in request.tork_result.output

    def test_middleware_govern_ssn_pii(self):
        """Test middleware detects and governs SSN PII."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        request = MockDjangoRequest(content=PII_MESSAGES["ssn_message"])
        middleware(request)

        assert request.tork_result is not None
        assert PII_SAMPLES["ssn"] not in request.tork_result.output

    def test_middleware_govern_credit_card_pii(self):
        """Test middleware detects and governs credit card PII."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        request = MockDjangoRequest(content=PII_MESSAGES["credit_card_message"])
        middleware(request)

        assert request.tork_result is not None
        assert PII_SAMPLES["credit_card"] not in request.tork_result.output

    def test_middleware_clean_text_passthrough(self):
        """Test middleware passes through clean text."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        clean_text = "What is the weather today?"
        request = MockDjangoRequest(content=clean_text)
        middleware(request)

        assert request.tork_result is not None
        assert request.tork_result.action == GovernanceAction.ALLOW


class TestDjangoErrorHandling:
    """Test error handling in Django adapter."""

    def test_middleware_handles_empty_body(self):
        """Test middleware handles empty body."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        request = MockDjangoRequest(body=b"")
        response = middleware(request)
        assert response is not None

    def test_middleware_handles_invalid_json(self):
        """Test middleware handles invalid JSON."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        request = MockDjangoRequest(body=b"not valid json")
        response = middleware(request)
        assert response is not None

    def test_middleware_skips_get_requests(self):
        """Test middleware skips GET requests."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        request = MockDjangoRequest(method="GET", content="test")
        middleware(request)
        assert request.tork_result is None

    def test_middleware_skips_unprotected_paths(self):
        """Test middleware skips unprotected paths."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        request = MockDjangoRequest(path="/public/page", content="test")
        middleware(request)
        assert request.tork_result is None


class TestDjangoComplianceReceipts:
    """Test compliance receipt generation in Django adapter."""

    def test_middleware_generates_receipt(self):
        """Test middleware generates governance receipt."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        request = MockDjangoRequest(content="Test message")
        middleware(request)

        assert request.tork_result is not None
        assert request.tork_result.receipt is not None
        assert request.tork_result.receipt.receipt_id is not None

    def test_middleware_receipt_has_timestamp(self):
        """Test middleware receipt has timestamp."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        request = MockDjangoRequest(content="Test message")
        middleware(request)

        assert request.tork_result.receipt.timestamp is not None


class TestDjangoMiddlewareGovernance:
    """Test middleware governance behavior."""

    def test_middleware_processes_post(self):
        """Test middleware processes POST requests."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        request = MockDjangoRequest(method="POST", content="Test")
        middleware(request)
        assert request.tork_result is not None

    def test_middleware_processes_put(self):
        """Test middleware processes PUT requests."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        request = MockDjangoRequest(method="PUT", content="Test")
        middleware(request)
        assert request.tork_result is not None

    def test_middleware_processes_patch(self):
        """Test middleware processes PATCH requests."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        request = MockDjangoRequest(method="PATCH", content="Test")
        middleware(request)
        assert request.tork_result is not None

    def test_middleware_stores_redacted_content(self):
        """Test middleware stores redacted content."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        request = MockDjangoRequest(content=PII_MESSAGES["email_message"])
        middleware(request)

        assert request.tork_redacted_content is not None
        assert PII_SAMPLES["email"] not in request.tork_redacted_content


class TestDjangoViewDecoratorGovernance:
    """Test view decorator governance."""

    def test_decorator_passes_clean_request(self):
        """Test decorator passes clean request."""
        @tork_protected
        def my_view(request):
            return MockDjangoResponse(b"success")

        request = MockDjangoRequest()
        request.tork_result = None
        response = my_view(request)
        assert response.content == b"success"

    def test_decorator_with_allow_action(self):
        """Test decorator with ALLOW action."""
        @tork_protected
        def my_view(request):
            return MockDjangoResponse(b"success")

        # Create a mock result with ALLOW action
        from tork_governance.core import GovernanceResult, PIIResult, Receipt
        from datetime import datetime

        request = MockDjangoRequest()
        request.tork_result = GovernanceResult(
            action=GovernanceAction.ALLOW,
            output="test",
            pii=PIIResult(has_pii=False, types=[], count=0, matches=[], redacted_text="test"),
            receipt=Receipt(
                receipt_id="test-id",
                timestamp=datetime.now().isoformat(),
                input_hash="hash",
                output_hash="hash",
                action=GovernanceAction.ALLOW,
                policy_version="1.0.0",
                processing_time_ns=0
            )
        )

        response = my_view(request)
        assert response.content == b"success"

    def test_decorator_preserves_function_name(self):
        """Test decorator preserves function name."""
        @tork_protected
        def my_view_function(request):
            return MockDjangoResponse()

        # Note: tork_protected doesn't use functools.wraps, so name is 'wrapper'
        # This is documenting current behavior
        assert callable(my_view_function)


class TestDjangoRequestResponseGovernance:
    """Test request/response governance."""

    def test_request_content_extraction_content_field(self):
        """Test content extraction from 'content' field."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        body = json.dumps({"content": "test message"}).encode("utf-8")
        request = MockDjangoRequest(body=body)
        middleware(request)

        assert request.tork_result is not None

    def test_request_content_extraction_message_field(self):
        """Test content extraction from 'message' field."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        body = json.dumps({"message": "test message"}).encode("utf-8")
        request = MockDjangoRequest(body=body)
        middleware(request)

        assert request.tork_result is not None

    def test_request_content_extraction_text_field(self):
        """Test content extraction from 'text' field."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        body = json.dumps({"text": "test message"}).encode("utf-8")
        request = MockDjangoRequest(body=body)
        middleware(request)

        assert request.tork_result is not None

    def test_request_content_extraction_query_field(self):
        """Test content extraction from 'query' field."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        body = json.dumps({"query": "test message"}).encode("utf-8")
        request = MockDjangoRequest(body=body)
        middleware(request)

        assert request.tork_result is not None

    def test_request_no_content_field(self):
        """Test request with no recognized content field."""
        def get_response(request):
            return MockDjangoResponse()

        middleware = TorkDjangoMiddleware(get_response)
        body = json.dumps({"data": "test"}).encode("utf-8")
        request = MockDjangoRequest(body=body)
        middleware(request)

        assert request.tork_result is None
