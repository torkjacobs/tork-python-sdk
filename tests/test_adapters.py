"""Tests for framework adapters."""

import pytest
from tork_governance.core import Tork, GovernanceAction


class TestLangChainAdapter:
    """Tests for LangChain adapter."""

    def test_import(self):
        """Test adapter can be imported."""
        from tork_governance.adapters.langchain import (
            TorkCallbackHandler,
            TorkGovernedChain,
            create_governed_chain,
        )
        assert TorkCallbackHandler is not None
        assert TorkGovernedChain is not None
        assert create_governed_chain is not None

    def test_callback_handler_creation(self):
        """Test TorkCallbackHandler creation."""
        from tork_governance.adapters.langchain import TorkCallbackHandler
        handler = TorkCallbackHandler()
        assert handler.tork is not None
        assert len(handler.receipts) == 0


class TestCrewAIAdapter:
    """Tests for CrewAI adapter."""

    def test_import(self):
        """Test adapter can be imported."""
        from tork_governance.adapters.crewai import (
            TorkCrewAIMiddleware,
            GovernedAgent,
            GovernedCrew,
        )
        assert TorkCrewAIMiddleware is not None
        assert GovernedAgent is not None
        assert GovernedCrew is not None

    def test_middleware_creation(self):
        """Test TorkCrewAIMiddleware creation."""
        from tork_governance.adapters.crewai import TorkCrewAIMiddleware
        middleware = TorkCrewAIMiddleware()
        assert middleware.tork is not None

    def test_message_governance(self):
        """Test message governance."""
        from tork_governance.adapters.crewai import TorkCrewAIMiddleware
        middleware = TorkCrewAIMiddleware()
        result = middleware.govern_message("My SSN is 123-45-6789", "input")
        assert result.pii.has_pii
        assert "[SSN_REDACTED]" in result.output


class TestAutoGenAdapter:
    """Tests for AutoGen adapter."""

    def test_import(self):
        """Test adapter can be imported."""
        from tork_governance.adapters.autogen import (
            TorkAutoGenMiddleware,
            GovernedAutoGenAgent,
        )
        assert TorkAutoGenMiddleware is not None
        assert GovernedAutoGenAgent is not None

    def test_middleware_creation(self):
        """Test TorkAutoGenMiddleware creation."""
        from tork_governance.adapters.autogen import TorkAutoGenMiddleware
        middleware = TorkAutoGenMiddleware()
        assert middleware.tork is not None

    def test_process_message(self):
        """Test message processing."""
        from tork_governance.adapters.autogen import TorkAutoGenMiddleware
        middleware = TorkAutoGenMiddleware()
        result = middleware.process_message("Email: test@example.com", "input")
        assert result.pii.has_pii


class TestOpenAIAgentsAdapter:
    """Tests for OpenAI Agents adapter."""

    def test_import(self):
        """Test adapter can be imported."""
        from tork_governance.adapters.openai_agents import (
            TorkOpenAIAgentsMiddleware,
            GovernedOpenAIAgent,
            GovernedRunner,
        )
        assert TorkOpenAIAgentsMiddleware is not None
        assert GovernedOpenAIAgent is not None
        assert GovernedRunner is not None

    def test_middleware_creation(self):
        """Test TorkOpenAIAgentsMiddleware creation."""
        from tork_governance.adapters.openai_agents import TorkOpenAIAgentsMiddleware
        middleware = TorkOpenAIAgentsMiddleware()
        assert middleware.tork is not None

    def test_process_input(self):
        """Test input processing."""
        from tork_governance.adapters.openai_agents import TorkOpenAIAgentsMiddleware
        middleware = TorkOpenAIAgentsMiddleware()
        result = middleware.process_input("Card: 4111-1111-1111-1111")
        assert result.pii.has_pii
        assert len(middleware.receipts) == 1


class TestFastAPIAdapter:
    """Tests for FastAPI adapter."""

    def test_import(self):
        """Test adapter can be imported."""
        from tork_governance.adapters.fastapi import (
            TorkFastAPIMiddleware,
            TorkFastAPIDependency,
        )
        assert TorkFastAPIMiddleware is not None
        assert TorkFastAPIDependency is not None


class TestDjangoAdapter:
    """Tests for Django adapter."""

    def test_import(self):
        """Test adapter can be imported."""
        from tork_governance.adapters.django import (
            TorkDjangoMiddleware,
            tork_protected,
        )
        assert TorkDjangoMiddleware is not None
        assert tork_protected is not None


class TestFlaskAdapter:
    """Tests for Flask adapter."""

    def test_import(self):
        """Test adapter can be imported."""
        from tork_governance.adapters.flask import TorkFlask, tork_required
        assert TorkFlask is not None
        assert tork_required is not None

    def test_flask_extension_creation(self):
        """Test TorkFlask extension creation."""
        from tork_governance.adapters.flask import TorkFlask
        ext = TorkFlask()
        assert ext.tork is not None

    def test_manual_govern(self):
        """Test manual governance."""
        from tork_governance.adapters.flask import TorkFlask
        ext = TorkFlask()
        result = ext.govern("SSN: 123-45-6789")
        assert result.pii.has_pii


class TestAdaptersExport:
    """Tests for adapters module exports."""

    def test_all_exports(self):
        """Test all adapters are exported."""
        from tork_governance.adapters import (
            TorkCallbackHandler,
            TorkGovernedChain,
            create_governed_chain,
            TorkCrewAIMiddleware,
            GovernedAgent,
            GovernedCrew,
            TorkAutoGenMiddleware,
            GovernedAutoGenAgent,
            TorkOpenAIAgentsMiddleware,
            GovernedOpenAIAgent,
            TorkFastAPIMiddleware,
            TorkFastAPIDependency,
            TorkDjangoMiddleware,
            TorkFlask,
            tork_required,
        )
        # All imports should succeed
        assert True
