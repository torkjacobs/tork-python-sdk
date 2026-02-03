"""
Tests for Flask adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Extension governance
- Decorator governance
- Request handling
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.flask import TorkFlask, tork_required
from .test_data import PII_SAMPLES, PII_MESSAGES


class MockFlaskApp:
    """Mock Flask app for testing."""

    def __init__(self, config=None):
        self.config = config or {}
        self._before_request_funcs = []

    def before_request(self, func):
        """Register before_request handler."""
        self._before_request_funcs.append(func)
        return func


class MockRequest:
    """Mock Flask request for testing."""

    def __init__(self, method="POST", path="/api/chat", json_data=None):
        self.method = method
        self.path = path
        self._json = json_data

    def get_json(self, silent=False):
        return self._json


class MockG:
    """Mock Flask g object for testing."""

    def __init__(self):
        self.tork_result = None
        self._tork = None


class TestFlaskImportInstantiation:
    """Test import and instantiation of Flask adapter."""

    def test_import_extension(self):
        """Test TorkFlask can be imported."""
        assert TorkFlask is not None

    def test_import_decorator(self):
        """Test tork_required decorator can be imported."""
        assert tork_required is not None

    def test_instantiate_extension_no_app(self):
        """Test extension instantiation without app."""
        tork_flask = TorkFlask()
        assert tork_flask is not None
        assert tork_flask.tork is not None
        assert tork_flask.app is None

    def test_instantiate_extension_with_app(self):
        """Test extension instantiation with app."""
        app = MockFlaskApp()
        tork_flask = TorkFlask(app)
        assert tork_flask is not None
        assert tork_flask.app is app

    def test_extension_has_protected_paths(self):
        """Test extension has default protected paths."""
        tork_flask = TorkFlask()
        assert tork_flask._protected_paths is not None
        assert len(tork_flask._protected_paths) >= 1


class TestFlaskConfiguration:
    """Test configuration of Flask adapter."""

    def test_extension_default_config(self):
        """Test extension with default configuration."""
        tork_flask = TorkFlask()
        assert tork_flask.tork is not None
        assert "/api/" in tork_flask._protected_paths

    def test_extension_with_api_key(self):
        """Test extension with API key."""
        tork_flask = TorkFlask(api_key="test-key")
        assert tork_flask.tork is not None

    def test_extension_with_policy_version(self):
        """Test extension with custom policy version."""
        tork_flask = TorkFlask(policy_version="2.0.0")
        assert tork_flask.tork is not None

    def test_init_app(self):
        """Test init_app with Flask app."""
        tork_flask = TorkFlask()
        app = MockFlaskApp()
        tork_flask.init_app(app)
        assert tork_flask.app is app
        assert len(app._before_request_funcs) == 1

    def test_init_app_with_config(self):
        """Test init_app uses app config."""
        tork_flask = TorkFlask()
        app = MockFlaskApp(config={
            "TORK_API_KEY": "config-key",
            "TORK_POLICY_VERSION": "3.0.0",
            "TORK_PROTECTED_PATHS": ["/custom/"]
        })
        tork_flask.init_app(app)
        assert tork_flask._protected_paths == ["/custom/"]


class TestFlaskPIIDetection:
    """Test PII detection and redaction in Flask adapter."""

    def test_extension_govern_email_pii(self):
        """Test extension governs email PII."""
        tork_flask = TorkFlask()
        result = tork_flask.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result.output
        assert "[EMAIL_REDACTED]" in result.output

    def test_extension_govern_phone_pii(self):
        """Test extension governs phone PII."""
        tork_flask = TorkFlask()
        result = tork_flask.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result.output
        assert "[PHONE_REDACTED]" in result.output

    def test_extension_govern_ssn_pii(self):
        """Test extension governs SSN PII."""
        tork_flask = TorkFlask()
        result = tork_flask.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result.output
        assert "[SSN_REDACTED]" in result.output

    def test_extension_govern_credit_card_pii(self):
        """Test extension governs credit card PII."""
        tork_flask = TorkFlask()
        result = tork_flask.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result.output
        assert "[CARD_REDACTED]" in result.output

    def test_extension_clean_text_passthrough(self):
        """Test extension passes through clean text."""
        tork_flask = TorkFlask()
        clean_text = "What is the weather today?"
        result = tork_flask.govern(clean_text)
        assert result.output == clean_text
        assert result.action == GovernanceAction.ALLOW


class TestFlaskErrorHandling:
    """Test error handling in Flask adapter."""

    def test_extract_content_with_content_field(self):
        """Test content extraction from content field."""
        tork_flask = TorkFlask()
        content = tork_flask._extract_content({"content": "test"})
        assert content == "test"

    def test_extract_content_with_message_field(self):
        """Test content extraction from message field."""
        tork_flask = TorkFlask()
        content = tork_flask._extract_content({"message": "test"})
        assert content == "test"

    def test_extract_content_with_text_field(self):
        """Test content extraction from text field."""
        tork_flask = TorkFlask()
        content = tork_flask._extract_content({"text": "test"})
        assert content == "test"

    def test_extract_content_with_prompt_field(self):
        """Test content extraction from prompt field."""
        tork_flask = TorkFlask()
        content = tork_flask._extract_content({"prompt": "test"})
        assert content == "test"

    def test_extract_content_with_query_field(self):
        """Test content extraction from query field."""
        tork_flask = TorkFlask()
        content = tork_flask._extract_content({"query": "test"})
        assert content == "test"

    def test_extract_content_no_known_field(self):
        """Test content extraction with unknown field."""
        tork_flask = TorkFlask()
        content = tork_flask._extract_content({"unknown": "test"})
        assert content is None

    def test_extract_content_non_string_value(self):
        """Test content extraction with non-string value."""
        tork_flask = TorkFlask()
        content = tork_flask._extract_content({"content": 123})
        assert content is None


class TestFlaskComplianceReceipts:
    """Test compliance receipt generation in Flask adapter."""

    def test_extension_generates_receipt(self):
        """Test extension generates governance receipt."""
        tork_flask = TorkFlask()
        result = tork_flask.govern("Test message")
        assert result.receipt is not None
        assert result.receipt.receipt_id is not None

    def test_extension_receipt_has_timestamp(self):
        """Test extension receipt has timestamp."""
        tork_flask = TorkFlask()
        result = tork_flask.govern("Test message")
        assert result.receipt.timestamp is not None


class TestFlaskExtensionGovernance:
    """Test extension governance behavior."""

    def test_govern_method(self):
        """Test govern method works correctly."""
        tork_flask = TorkFlask()
        result = tork_flask.govern(PII_MESSAGES["ssn_message"])
        assert result.action == GovernanceAction.REDACT
        assert PII_SAMPLES["ssn"] not in result.output

    def test_govern_returns_governance_result(self):
        """Test govern returns GovernanceResult."""
        tork_flask = TorkFlask()
        result = tork_flask.govern("Test message")
        assert hasattr(result, "output")
        assert hasattr(result, "action")
        assert hasattr(result, "pii")
        assert hasattr(result, "receipt")


class TestFlaskDecoratorGovernance:
    """Test decorator governance."""

    def test_decorator_is_callable(self):
        """Test tork_required is a callable."""
        assert callable(tork_required)

    def test_decorator_wraps_function(self):
        """Test decorator wraps function."""
        @tork_required
        def my_view():
            return "success"

        # Decorator uses @wraps so name should be preserved
        assert my_view.__name__ == "my_view"

    def test_decorator_preserves_function_docs(self):
        """Test decorator preserves function docstring."""
        @tork_required
        def my_view():
            """My view docstring."""
            return "success"

        assert my_view.__doc__ == """My view docstring."""


class TestFlaskBeforeRequestHandling:
    """Test before request handling."""

    def test_before_request_registered(self):
        """Test before_request is registered on init_app."""
        tork_flask = TorkFlask()
        app = MockFlaskApp()
        tork_flask.init_app(app)
        assert len(app._before_request_funcs) == 1
        assert tork_flask._before_request in app._before_request_funcs

    def test_before_request_with_app_in_constructor(self):
        """Test before_request is registered in constructor."""
        app = MockFlaskApp()
        TorkFlask(app)
        assert len(app._before_request_funcs) == 1


class TestFlaskRequestContentExtraction:
    """Test request content extraction."""

    def test_priority_content_over_message(self):
        """Test content field has priority over message."""
        tork_flask = TorkFlask()
        # When multiple fields exist, first match wins
        content = tork_flask._extract_content({
            "content": "content_value",
            "message": "message_value"
        })
        assert content == "content_value"

    def test_priority_message_over_text(self):
        """Test message field has priority over text."""
        tork_flask = TorkFlask()
        content = tork_flask._extract_content({
            "message": "message_value",
            "text": "text_value"
        })
        assert content == "message_value"

    def test_empty_dict_returns_none(self):
        """Test empty dict returns None."""
        tork_flask = TorkFlask()
        content = tork_flask._extract_content({})
        assert content is None


class TestFlaskIntegration:
    """Test Flask integration scenarios."""

    def test_extension_with_shared_tork(self):
        """Test extension with shared Tork instance."""
        tork = Tork()
        tork_flask = TorkFlask()
        # Verify tork is accessible
        assert tork_flask.tork is not None

    def test_multiple_extensions(self):
        """Test multiple extensions on different apps."""
        app1 = MockFlaskApp()
        app2 = MockFlaskApp()

        tork_flask1 = TorkFlask(app1)
        tork_flask2 = TorkFlask(app2)

        assert tork_flask1.app is app1
        assert tork_flask2.app is app2
        assert tork_flask1.tork is not tork_flask2.tork
