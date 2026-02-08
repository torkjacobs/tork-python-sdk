"""Tests for Replicate SDK adapter."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from tork_governance.core import Tork, GovernanceAction


class TestTorkReplicateClient:
    """Tests for TorkReplicateClient."""

    def setup_method(self):
        self.tork = Tork()

    def test_govern_input_prompt(self):
        """Test that governance is applied to input prompt."""
        from tork_governance.adapters.replicate_sdk import TorkReplicateClient

        client = TorkReplicateClient(api_token="test", tork=self.tork)

        mock_replicate = MagicMock()
        mock_replicate.run.return_value = "Here is the answer."
        client._client = mock_replicate

        result = client.run(
            "meta/llama-2-70b-chat",
            input={"prompt": "My SSN is 123-45-6789"}
        )

        # Verify the prompt was governed before API call
        call_args = mock_replicate.run.call_args
        called_input = call_args.kwargs.get("input", {})
        assert "123-45-6789" not in called_input.get("prompt", "")
        assert result["_tork_receipts"] is not None
        assert len(result["_tork_receipts"]) > 0

    def test_govern_output_string(self):
        """Test that governance is applied to string output."""
        from tork_governance.adapters.replicate_sdk import TorkReplicateClient

        client = TorkReplicateClient(api_token="test", tork=self.tork)

        mock_replicate = MagicMock()
        mock_replicate.run.return_value = "Your email is john@secret.com"
        client._client = mock_replicate

        result = client.run(
            "meta/llama-2-70b-chat",
            input={"prompt": "Hello"}
        )

        assert "[EMAIL_REDACTED]" in result["output"]
        assert "john@secret.com" not in result["output"]

    def test_pii_redaction_in_messages(self):
        """Test PII redaction in input with multiple text fields."""
        from tork_governance.adapters.replicate_sdk import TorkReplicateClient

        client = TorkReplicateClient(api_token="test", tork=self.tork)

        mock_replicate = MagicMock()
        mock_replicate.run.return_value = "Done."
        client._client = mock_replicate

        result = client.run(
            "meta/llama-2-70b-chat",
            input={
                "prompt": "Card: 4111-1111-1111-1111",
                "system_prompt": "SSN: 123-45-6789",
            }
        )

        # Both text fields should have been governed
        call_args = mock_replicate.run.call_args
        called_input = call_args.kwargs.get("input", {})
        assert "4111-1111-1111-1111" not in called_input.get("prompt", "")
        assert "123-45-6789" not in called_input.get("system_prompt", "")
        assert len(result["_tork_receipts"]) == 2

    def test_govern_list_output(self):
        """Test governance on list output (common for streaming results)."""
        from tork_governance.adapters.replicate_sdk import TorkReplicateClient

        client = TorkReplicateClient(api_token="test", tork=self.tork)

        mock_replicate = MagicMock()
        mock_replicate.run.return_value = ["Your SSN ", "is 123-45-6789"]
        client._client = mock_replicate

        result = client.run(
            "meta/llama-2-70b-chat",
            input={"prompt": "Hello"}
        )

        # List output should be joined and governed
        assert "123-45-6789" not in str(result["output"])

    def test_predictions_create(self):
        """Test governed predictions.create()."""
        from tork_governance.adapters.replicate_sdk import TorkReplicateClient

        client = TorkReplicateClient(api_token="test", tork=self.tork)

        mock_replicate = MagicMock()
        mock_prediction = MagicMock()
        mock_prediction.id = "pred-123"
        mock_prediction.model = "meta/llama-2-70b-chat"
        mock_prediction.version = "v1"
        mock_prediction.status = "starting"
        mock_replicate.predictions.create.return_value = mock_prediction
        client._client = mock_replicate

        result = client.predictions_create(
            model="meta/llama-2-70b-chat",
            input={"prompt": "My SSN is 123-45-6789"}
        )

        assert result["id"] == "pred-123"
        assert len(result["_tork_receipts"]) > 0


class TestReplicateGoverned:
    """Tests for replicate_governed decorator."""

    def test_decorator_governs_input(self):
        """Test that the decorator governs input dict."""
        from tork_governance.adapters.replicate_sdk import replicate_governed

        tork = Tork()

        @replicate_governed(tork)
        def fake_run(**kwargs):
            return kwargs

        result = fake_run(
            model="test",
            input={"prompt": "My SSN is 123-45-6789", "max_tokens": 100}
        )

        assert "123-45-6789" not in result["input"]["prompt"]
        assert "[SSN_REDACTED]" in result["input"]["prompt"]
        # Non-text fields should be untouched
        assert result["input"]["max_tokens"] == 100
