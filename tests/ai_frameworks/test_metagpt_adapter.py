"""
Tests for MetaGPT adapter.

Tests cover:
- Import/instantiation
- Configuration
- PII detection & redaction (email, phone, SSN, credit card)
- Error handling
- Compliance receipts
- Role action governance
- Team message governance
- Document governance
- Code governance
- Requirement governance
"""

import pytest
import asyncio
from tork_governance import Tork, GovernanceAction
from tork_governance.adapters.metagpt import (
    TorkMetaGPTRole,
    TorkMetaGPTTeam,
    TorkMetaGPTAction,
    TorkMetaGPTEnvironment,
)
from .test_data import PII_SAMPLES, PII_MESSAGES


class TestMetaGPTImportInstantiation:
    """Test import and instantiation of MetaGPT adapter."""

    def test_import_role(self):
        """Test TorkMetaGPTRole can be imported."""
        assert TorkMetaGPTRole is not None

    def test_import_team(self):
        """Test TorkMetaGPTTeam can be imported."""
        assert TorkMetaGPTTeam is not None

    def test_import_action(self):
        """Test TorkMetaGPTAction can be imported."""
        assert TorkMetaGPTAction is not None

    def test_instantiate_role_default(self):
        """Test role instantiation with defaults."""
        role = TorkMetaGPTRole()
        assert role is not None
        assert role.tork is not None
        assert role.receipts == []

    def test_instantiate_team_default(self):
        """Test team instantiation with defaults."""
        team = TorkMetaGPTTeam()
        assert team is not None
        assert team.tork is not None


class TestMetaGPTConfiguration:
    """Test configuration of MetaGPT adapter."""

    def test_role_with_tork_instance(self, tork_instance):
        """Test role with existing Tork instance."""
        role = TorkMetaGPTRole(tork=tork_instance)
        assert role.tork is tork_instance

    def test_team_with_tork_instance(self, tork_instance):
        """Test team with existing Tork instance."""
        team = TorkMetaGPTTeam(tork=tork_instance)
        assert team.tork is tork_instance

    def test_action_with_tork_instance(self, tork_instance):
        """Test action with existing Tork instance."""
        action = TorkMetaGPTAction(tork=tork_instance)
        assert action.tork is tork_instance

    def test_role_with_api_key(self):
        """Test role with API key."""
        role = TorkMetaGPTRole(api_key="test-key")
        assert role.tork is not None


class TestMetaGPTPIIDetection:
    """Test PII detection and redaction in MetaGPT adapter."""

    def test_govern_email_pii(self):
        """Test email PII is detected and redacted."""
        role = TorkMetaGPTRole()
        result = role.govern(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result
        assert "[EMAIL_REDACTED]" in result

    def test_govern_phone_pii(self):
        """Test phone PII is detected and redacted."""
        role = TorkMetaGPTRole()
        result = role.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result
        assert "[PHONE_REDACTED]" in result

    def test_govern_ssn_pii(self):
        """Test SSN PII is detected and redacted."""
        role = TorkMetaGPTRole()
        result = role.govern(PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result
        assert "[SSN_REDACTED]" in result

    def test_govern_credit_card_pii(self):
        """Test credit card PII is detected and redacted."""
        role = TorkMetaGPTRole()
        result = role.govern(PII_MESSAGES["credit_card_message"])
        assert PII_SAMPLES["credit_card"] not in result
        assert "[CARD_REDACTED]" in result

    def test_govern_clean_text(self):
        """Test clean text passes through unchanged."""
        role = TorkMetaGPTRole()
        clean_text = "Implement user authentication"
        result = role.govern(clean_text)
        assert result == clean_text


class TestMetaGPTErrorHandling:
    """Test error handling in MetaGPT adapter."""

    def test_role_empty_string(self):
        """Test role handles empty string."""
        role = TorkMetaGPTRole()
        result = role.govern("")
        assert result == ""

    def test_role_whitespace(self):
        """Test role handles whitespace."""
        role = TorkMetaGPTRole()
        result = role.govern("   ")
        assert result == "   "

    def test_team_empty_string(self):
        """Test team handles empty string."""
        team = TorkMetaGPTTeam()
        result = team.govern("")
        assert result == ""

    def test_role_empty_receipts(self):
        """Test role starts with empty receipts."""
        role = TorkMetaGPTRole()
        assert role.get_receipts() == []


class TestMetaGPTComplianceReceipts:
    """Test compliance receipt generation in MetaGPT adapter."""

    @pytest.mark.asyncio
    async def test_role_run_generates_receipt(self):
        """Test role run generates receipt."""
        class MockRole:
            name = "Engineer"

            async def run(self, message, **kwargs):
                return f"Processed: {message}"

        role = TorkMetaGPTRole(MockRole())
        await role.run("Test message")
        assert len(role.receipts) >= 1
        assert role.receipts[0]["type"] == "role_input"
        assert "receipt_id" in role.receipts[0]

    def test_role_get_receipts(self):
        """Test role get_receipts method."""
        role = TorkMetaGPTRole()
        receipts = role.get_receipts()
        assert isinstance(receipts, list)


class TestMetaGPTRoleActionGovernance:
    """Test role action governance."""

    @pytest.mark.asyncio
    async def test_role_run_governs_input(self):
        """Test role run governs message input."""
        class MockRole:
            name = "Engineer"

            async def run(self, message, **kwargs):
                return message

        role = TorkMetaGPTRole(MockRole())
        result = await role.run(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    @pytest.mark.asyncio
    async def test_role_run_governs_output(self):
        """Test role run governs output."""
        class MockRole:
            name = "Engineer"

            async def run(self, message, **kwargs):
                return PII_MESSAGES["ssn_message"]

        role = TorkMetaGPTRole(MockRole())
        result = await role.run("get ssn")
        assert PII_SAMPLES["ssn"] not in result

    def test_govern_message_alias(self):
        """Test govern_message is alias for govern."""
        role = TorkMetaGPTRole()
        result1 = role.govern("test")
        result2 = role.govern_message("test")
        assert result1 == result2


class TestMetaGPTTeamMessageGovernance:
    """Test team message governance."""

    @pytest.mark.asyncio
    async def test_team_run_governs_idea(self):
        """Test team run governs idea input."""
        class MockTeam:
            async def run(self, idea, **kwargs):
                return f"Built: {idea}"

        team = TorkMetaGPTTeam(MockTeam())
        result = await team.run(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    @pytest.mark.asyncio
    async def test_team_run_governs_output(self):
        """Test team run governs output."""
        class MockTeam:
            async def run(self, idea, **kwargs):
                return PII_MESSAGES["phone_message"]

        team = TorkMetaGPTTeam(MockTeam())
        result = await team.run("build app")
        assert PII_SAMPLES["phone_us"] not in result

    @pytest.mark.asyncio
    async def test_team_run_list_output(self):
        """Test team run governs list output."""
        class MockTeam:
            async def run(self, idea, **kwargs):
                return [PII_MESSAGES["email_message"], "clean output"]

        team = TorkMetaGPTTeam(MockTeam())
        result = await team.run("test")
        assert PII_SAMPLES["email"] not in result[0]
        assert result[1] == "clean output"


class TestMetaGPTDocumentGovernance:
    """Test document governance (via action)."""

    @pytest.mark.asyncio
    async def test_action_run_governs_args(self):
        """Test action run governs string arguments."""
        class MockAction:
            async def run(self, *args, **kwargs):
                return args[0] if args else ""

        action = TorkMetaGPTAction(MockAction())
        result = await action.run(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in result

    @pytest.mark.asyncio
    async def test_action_run_governs_kwargs(self):
        """Test action run governs keyword arguments."""
        class MockAction:
            async def run(self, *args, **kwargs):
                return kwargs.get("content", "")

        action = TorkMetaGPTAction(MockAction())
        result = await action.run(content=PII_MESSAGES["ssn_message"])
        assert PII_SAMPLES["ssn"] not in result


class TestMetaGPTCodeGovernance:
    """Test code/output governance."""

    @pytest.mark.asyncio
    async def test_action_run_governs_output(self):
        """Test action run governs output."""
        class MockAction:
            async def run(self, *args, **kwargs):
                return PII_MESSAGES["credit_card_message"]

        action = TorkMetaGPTAction(MockAction())
        result = await action.run("generate code")
        assert PII_SAMPLES["credit_card"] not in result

    def test_action_govern_method(self):
        """Test action govern method."""
        action = TorkMetaGPTAction()
        result = action.govern(PII_MESSAGES["phone_message"])
        assert PII_SAMPLES["phone_us"] not in result


class TestMetaGPTRequirementGovernance:
    """Test requirement governance."""

    def test_role_set_goal(self):
        """Test role set_goal governs goal."""
        class MockRole:
            goal = None

            def set_goal(self, goal):
                self.goal = goal

            async def run(self, message, **kwargs):
                return message

        mock_role = MockRole()
        role = TorkMetaGPTRole(mock_role)
        role.set_goal(PII_MESSAGES["email_message"])
        assert PII_SAMPLES["email"] not in mock_role.goal

    def test_role_goal_receipt(self):
        """Test role generates goal receipt."""
        class MockRole:
            def set_goal(self, goal):
                pass

        role = TorkMetaGPTRole(MockRole())
        role.set_goal("Test goal")
        assert any(r["type"] == "role_goal" for r in role.receipts)
