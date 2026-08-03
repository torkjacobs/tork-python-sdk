"""Tests for the api_key-is-unused UserWarning (0.23.0 honesty fix)."""

import warnings

import pytest

import tork_governance.core as core
from tork_governance import Tork
from tork_governance.core import TorkConfig


@pytest.fixture(autouse=True)
def reset_warning_flag():
    """The warning fires once per process; reset the flag so each test is isolated."""
    core._api_key_warning_emitted = False
    yield
    core._api_key_warning_emitted = False


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """These tests only care about the warning, not reporting — never let a
    govern() call in this file attempt a real request to tork.network."""
    def _blocked(*args, **kwargs):
        raise OSError("network access disabled in tests")
    monkeypatch.setattr(core.urllib.request, "urlopen", _blocked)


class TestApiKeyWarning:
    def test_warns_when_api_key_passed_to_tork(self):
        with pytest.warns(UserWarning, match="reporting to tork.network is now ON"):
            Tork(api_key="tork_sk_live_abc123")

    def test_warns_when_api_key_passed_to_config(self):
        with pytest.warns(UserWarning, match="CLIENT ATTESTATION"):
            TorkConfig(api_key="tork_sk_live_abc123")

    def test_warns_when_config_with_api_key_passed_to_tork(self):
        with pytest.warns(UserWarning):
            Tork(config=TorkConfig(api_key="tork_sk_live_abc123"))

    def test_no_warning_without_api_key(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            Tork()
            TorkConfig()

    def test_no_warning_for_empty_api_key(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            Tork(api_key="")
            TorkConfig(api_key=None)

    def test_warns_only_once_per_process(self):
        with pytest.warns(UserWarning):
            Tork(api_key="first-key")
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            Tork(api_key="second-key")
            TorkConfig(api_key="third-key")

    def test_govern_does_not_warn_again(self):
        with pytest.warns(UserWarning):
            tork = Tork(api_key="tork_sk_live_abc123")
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            tork.govern("My SSN is 123-45-6789")
            tork.govern("hello world")

    def test_adapter_forwarding_api_key_inherits_warning(self):
        from tork_governance.adapters.openclaw import TorkOpenClawAgent

        with pytest.warns(UserWarning, match="tork.network"):
            TorkOpenClawAgent(api_key="tork_sk_live_abc123")
