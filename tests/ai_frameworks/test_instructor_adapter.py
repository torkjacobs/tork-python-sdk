"""
Tests for Instructor adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Client governance
- Patch governance
- Response decorator governance
- Structured output governance
- Async governance
"""

import pytest
import asyncio
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.instructor import (
    TorkInstructorClient,
    TorkInstructorPatch,
    governed_response,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestInstructorImportInstantiation:
    """Test import and instantiation of Instructor adapter."""

    def test_import_client(self):
        """Test TorkInstructorClient can be imported."""
        assert TorkInstructorClient is not None

    def test_import_patch(self):
        """Test TorkInstructorPatch can be imported."""
        assert TorkInstructorPatch is not None

    def test_import_governed_response(self):
        """Test governed_response can be imported."""
        assert governed_response is not None

    def test_instantiate_client_default(self):
        """Test client instantiation with defaults."""
        client = TorkInstructorClient()
        assert client is not None
        assert client.tork is not None
        assert client.receipts == []

    def test_instantiate_patch_default(self):
        """Test patch instantiation with defaults."""
        patch = TorkInstructorPatch()
        assert patch is not None
        assert patch.tork is not None


class TestInstructorConfiguration:
    """Test configuration of Instructor adapter."""

    def test_client_with_tork_instance(self, tork_instance):
        """Test client with existing Tork instance."""
        client = TorkInstructorClient(tork=tork_instance)
        assert client.tork is tork_instance

    def test_patch_with_tork_instance(self, tork_instance):
        """Test patch with existing Tork instance."""
        patch = TorkInstructorPatch(tork=tork_instance)
        assert patch.tork is tork_instance

    def test_client_with_api_key(self):
        """Test client with API key."""
        client = TorkInstructorClient(api_key="test-key")
        assert client.tork is not None

    def test_client_has_chat_namespace(self):
        """Test client has chat namespace."""
        client = TorkInstructorClient()
        assert hasattr(client, "chat")
        assert hasattr(client.chat, "completions")


class TestInstructorPIIDetection:
    """Test PII detection and redaction in Instructor adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        client = TorkInstructorClient()
        result = client.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        client = TorkInstructorClient()
        result = client.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        client = TorkInstructorClient()
        result = client.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        client = TorkInstructorClient()
        result = client.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        client = TorkInstructorClient()
        clean_text = "Extract user information"
        result = client.govern(clean_text)
        assert result == clean_text


class TestInstructorErrorHandling:
    """Test error handling in Instructor adapter."""

    def test_client_empty_string(self):
        """Test client handles empty string."""
        client = TorkInstructorClient()
        result = client.govern("")
        assert result == ""

    def test_client_whitespace(self):
        """Test client handles whitespace."""
        client = TorkInstructorClient()
        result = client.govern("   ")
        assert result == "   "

    def test_client_empty_receipts(self):
        """Test client starts with empty receipts."""
        client = TorkInstructorClient()
        assert client.get_receipts() == []

    def test_patch_empty_receipts(self):
        """Test patch starts with empty receipts."""
        patch = TorkInstructorPatch()
        assert patch.get_receipts() == []


class TestInstructorComplianceReceipts:
    """Test compliance receipt generation in Instructor adapter."""

    def test_govern_messages_generates_receipts(self):
        """Test _govern_messages generates receipts."""
        client = TorkInstructorClient()
        messages = [{"role": "user", "content": "Test message"}]
        client._govern_messages(messages)
        assert len(client.receipts) == 1
        assert client.receipts[0]["type"] == "message_input"
        assert "receipt_id" in client.receipts[0]

    def test_govern_messages_includes_role(self):
        """Test receipt includes message role."""
        client = TorkInstructorClient()
        messages = [{"role": "user", "content": "Test"}]
        client._govern_messages(messages)
        assert client.receipts[0]["role"] == "user"

    def test_client_get_receipts(self):
        """Test client get_receipts method."""
        client = TorkInstructorClient()
        receipts = client.get_receipts()
        assert isinstance(receipts, list)


class TestInstructorClientGovernance:
    """Test client governance."""

    def test_govern_messages_pii(self):
        """Test _govern_messages removes PII."""
        client = TorkInstructorClient()
        messages = [{"role": "user", "content": PII_MESSAGES["email_message"]}]
        governed = client._govern_messages(messages)
        assert PII_SAMPLES["email"] not in governed[0]["content"]

    def test_govern_messages_multiple(self):
        """Test _govern_messages handles multiple messages."""
        client = TorkInstructorClient()
        messages = [
            {"role": "user", "content": PII_MESSAGES["email_message"]},
            {"role": "assistant", "content": "I see an email"},
            {"role": "user", "content": PII_MESSAGES["phone_message"]}
        ]
        governed = client._govern_messages(messages)
        assert len(governed) == 3
        assert PII_SAMPLES["email"] not in governed[0]["content"]
        assert PII_SAMPLES["phone_us"] not in governed[2]["content"]

    def test_govern_response_fields(self):
        """Test _govern_response governs string fields."""
        client = TorkInstructorClient()

        class MockResponse:
            def __init__(self):
                self.name = "John"
                self.email = PII_SAMPLES["email"]

        response = MockResponse()
        governed = client._govern_response(response)
        assert PII_SAMPLES["email"] not in governed.email

    def test_govern_input_alias(self):
        """Test govern_input is alias for govern."""
        client = TorkInstructorClient()
        result1 = client.govern("test")
        result2 = client.govern_input("test")
        assert result1 == result2


class TestInstructorPatchGovernance:
    """Test patch governance."""

    def test_patch_governs_messages(self):
        """Test patch governs messages."""
        patch = TorkInstructorPatch()

        class MockCompletions:
            def create(self, messages, **kwargs):
                class Response:
                    def __init__(self):
                        self.content = messages[0]["content"]
                return Response()

        class MockChat:
            def __init__(self):
                self.completions = MockCompletions()

        class MockClient:
            def __init__(self):
                self.chat = MockChat()

        client = MockClient()
        patched = patch.patch(client)

        messages = [{"role": "user", "content": PII_MESSAGES["email_message"]}]
        response = patched.chat.completions.create(messages=messages)
        assert len(patch.receipts) >= 1
        assert patch.receipts[0]["type"] == "patched_input"

    def test_patch_governs_response(self):
        """Test patch governs response fields."""
        patch = TorkInstructorPatch()

        class MockCompletions:
            def create(self, messages, **kwargs):
                class Response:
                    def __init__(self):
                        self.email = PII_MESSAGES["ssn_message"]
                return Response()

        class MockChat:
            def __init__(self):
                self.completions = MockCompletions()

        class MockClient:
            def __init__(self):
                self.chat = MockChat()

        client = MockClient()
        patched = patch.patch(client)

        messages = [{"role": "user", "content": "Get SSN"}]
        response = patched.chat.completions.create(messages=messages)
        assert PII_SAMPLES["ssn"] not in response.email


class TestInstructorResponseDecoratorGovernance:
    """Test response decorator governance."""

    def test_governed_response_decorator(self):
        """Test governed_response decorator."""
        @governed_response()
        def get_info(text: str):
            class Info:
                def __init__(self):
                    self.data = text
            return Info()

        result = get_info(text="test data")
        assert result.data == "test data"

    def test_governed_response_governs_input(self):
        """Test governed_response governs input."""
        @governed_response()
        def process(text: str):
            class Result:
                def __init__(self):
                    self.processed = text
            return Result()

        result = process(PII_MESSAGES["email_message"])
        receipts = process.get_receipts()
        assert len(receipts) >= 1
        assert receipts[0]["type"] == "response_input"

    def test_governed_response_governs_output_fields(self):
        """Test governed_response governs output fields."""
        @governed_response()
        def get_user():
            class User:
                def __init__(self):
                    self.email = PII_MESSAGES["email_message"]
            return User()

        result = get_user()
        assert PII_SAMPLES["email"] not in result.email

    def test_governed_response_receipt_has_field(self):
        """Test receipt includes field name."""
        @governed_response()
        def get_data():
            class Data:
                def __init__(self):
                    self.value = "test"
            return Data()

        get_data()
        receipts = get_data.get_receipts()
        assert any(r.get("field") == "value" for r in receipts)

    def test_governed_response_with_tork(self, tork_instance):
        """Test governed_response with Tork instance."""
        @governed_response(tork=tork_instance)
        def process(text: str):
            return text

        result = process("test")
        assert result == "test"


class TestInstructorStructuredOutputGovernance:
    """Test structured output governance."""

    def test_response_multiple_fields(self):
        """Test governing multiple response fields."""
        client = TorkInstructorClient()

        class MockResponse:
            def __init__(self):
                self.email = PII_MESSAGES["email_message"]
                self.phone = PII_MESSAGES["phone_message"]
                self.name = "John Doe"

        response = MockResponse()
        governed = client._govern_response(response)

        assert PII_SAMPLES["email"] not in governed.email
        assert PII_SAMPLES["phone_us"] not in governed.phone
        assert governed.name == "John Doe"

    def test_response_field_receipts(self):
        """Test receipts generated for each field."""
        client = TorkInstructorClient()

        class MockResponse:
            def __init__(self):
                self.field1 = "value1"
                self.field2 = "value2"

        client._govern_response(MockResponse())
        receipts = client.get_receipts()
        assert len(receipts) == 2
        fields = [r.get("field") for r in receipts]
        assert "field1" in fields
        assert "field2" in fields

    def test_response_non_string_fields(self):
        """Test non-string fields are passed through."""
        client = TorkInstructorClient()

        class MockResponse:
            def __init__(self):
                self.count = 42
                self.active = True
                self.name = "test"

        response = MockResponse()
        governed = client._govern_response(response)

        assert governed.count == 42
        assert governed.active is True


class TestInstructorAsyncGovernance:
    """Test async governance."""

    @pytest.mark.asyncio
    async def test_governed_response_async_compatible(self):
        """Test governed_response works with async patterns."""
        @governed_response()
        def sync_func(text: str):
            class Result:
                def __init__(self):
                    self.data = text
            return Result()

        # Simulate async usage pattern
        async def async_wrapper():
            return sync_func("test")

        result = await async_wrapper()
        assert result.data == "test"

    def test_completions_namespace_exists(self):
        """Test async completions method exists."""
        client = TorkInstructorClient()
        assert hasattr(client.chat.completions, "acreate")
