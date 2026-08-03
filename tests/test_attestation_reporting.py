"""Tests for optional metadata-only reporting to tork.network.

No test in this file makes a real network call — urllib.request.urlopen is
always monkeypatched. See the bottom of core_python_sdk's task notes for the
real command to test against production with a live key.
"""

import json
import io
import urllib.error

import pytest

import tork_governance.core as core
from tork_governance import GovernanceAction, Tork, TorkConfig


class FakeResponse:
    def __init__(self, status: int, body: dict):
        self.status = status
        self._body = json.dumps(body).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture(autouse=True)
def reset_warning_flag():
    core._api_key_warning_emitted = False
    yield
    core._api_key_warning_emitted = False


class TestReportingDisabled:
    def test_no_api_key_means_not_attempted(self):
        tork = Tork()
        result = tork.govern("Contact me at test@example.com")
        assert result.report is not None
        assert result.report.attempted is False
        assert result.report.succeeded is False
        assert result.report.receipt_id is None
        assert result.report.reason is not None

    def test_no_api_key_never_touches_network(self, monkeypatch):
        def _fail(*args, **kwargs):
            raise AssertionError("urlopen must not be called without an api_key")
        monkeypatch.setattr(core.urllib.request, "urlopen", _fail)
        tork = Tork()
        tork.govern("Contact me at test@example.com")  # must not raise


class TestReportingSuccess:
    def test_new_attestation_201(self, monkeypatch):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse(201, {"receipt_id": "tork_rcpt_attest_abc123", "replayed": False})

        monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
        tork = Tork(api_key="tork_sk_live_test")
        result = tork.govern("Contact me at test@example.com")

        assert result.report.attempted is True
        assert result.report.wait(5) is True
        assert result.report.succeeded is True
        assert result.report.receipt_id == "tork_rcpt_attest_abc123"
        assert result.report.reason is None
        assert captured["timeout"] == core._REPORT_TIMEOUT_SECONDS

    def test_replayed_200_still_succeeds(self, monkeypatch):
        def fake_urlopen(request, timeout=None):
            return FakeResponse(200, {"receipt_id": "tork_rcpt_attest_abc123", "replayed": True})

        monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
        tork = Tork(api_key="tork_sk_live_test")
        result = tork.govern("hello world")

        assert result.report.wait(5) is True
        assert result.report.succeeded is True
        assert result.report.receipt_id == "tork_rcpt_attest_abc123"


class TestReportingFailureNeverRaises:
    def test_connection_error_does_not_raise(self, monkeypatch):
        def fake_urlopen(request, timeout=None):
            raise OSError("simulated network failure")

        monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
        tork = Tork(api_key="tork_sk_live_test")
        result = tork.govern("Contact me at test@example.com")

        assert result.report.attempted is True
        assert result.report.wait(5) is True
        assert result.report.succeeded is False
        assert "simulated network failure" in result.report.reason

    def test_http_error_does_not_raise(self, monkeypatch):
        def fake_urlopen(request, timeout=None):
            body = json.dumps({"error": "invalid api key", "code": "UNAUTHORIZED"}).encode("utf-8")
            raise urllib.error.HTTPError(
                core.ATTESTATIONS_ENDPOINT, 401, "Unauthorized", {}, io.BytesIO(body)
            )

        monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
        tork = Tork(api_key="tork_sk_live_bad")
        result = tork.govern("hello world")

        assert result.report.attempted is True
        assert result.report.wait(5) is True
        assert result.report.succeeded is False
        assert "invalid api key" in result.report.reason

    def test_missing_receipt_id_in_response_is_a_failure(self, monkeypatch):
        def fake_urlopen(request, timeout=None):
            return FakeResponse(201, {"replayed": False})

        monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
        tork = Tork(api_key="tork_sk_live_test")
        result = tork.govern("hello world")

        assert result.report.wait(5) is True
        assert result.report.succeeded is False
        assert "receipt_id" in result.report.reason

    def test_local_decision_unaffected_by_reporting_failure(self, monkeypatch):
        def fake_urlopen(request, timeout=None):
            raise OSError("simulated network failure")

        monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
        tork = Tork(api_key="tork_sk_live_test")
        result = tork.govern("My SSN is 123-45-6789")

        assert result.action == GovernanceAction.REDACT
        assert "[SSN_REDACTED]" in result.output


class TestRequestBodyContract:
    def _capture(self, monkeypatch):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["request"] = request
            return FakeResponse(201, {"receipt_id": "tork_rcpt_attest_abc123"})

        monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
        return captured

    def test_body_contains_no_content_field(self, monkeypatch):
        captured = self._capture(monkeypatch)
        tork = Tork(api_key="tork_sk_live_test")
        secret_text = "My SSN is 123-45-6789 and email is test@example.com"
        result = tork.govern(secret_text)
        result.report.wait(5)

        raw_body = captured["request"].data
        body = json.loads(raw_body)

        assert set(body.keys()) == {
            "client_event_id", "action", "canonical_json",
            "fingerprint_salt", "fingerprint", "decided_at",
        }
        # No content/output/PII-value fields anywhere in the payload.
        assert "content" not in body
        assert "input" not in body
        assert "output" not in body
        assert "123-45-6789" not in raw_body.decode("utf-8")
        assert "test@example.com" not in raw_body.decode("utf-8")
        assert "123-45-6789" not in body["canonical_json"]
        assert "test@example.com" not in body["canonical_json"]

    def test_canonical_json_only_carries_type_labels(self, monkeypatch):
        captured = self._capture(monkeypatch)
        tork = Tork(api_key="tork_sk_live_test")
        result = tork.govern("My SSN is 123-45-6789")
        result.report.wait(5)

        body = json.loads(captured["request"].data)
        canonical = json.loads(body["canonical_json"])
        assert canonical["pii"] == ["ssn"]  # a type label, not the value

    def test_headers(self, monkeypatch):
        captured = self._capture(monkeypatch)
        tork = Tork(api_key="tork_sk_live_test")
        result = tork.govern("hello world")
        result.report.wait(5)

        headers = {k.lower(): v for k, v in captured["request"].headers.items()}
        assert headers["x-tork-api-key"] == "tork_sk_live_test"
        assert headers["x-tork-sdk-language"] == "python"
        assert headers["x-tork-sdk-version"] == core._sdk_version()
        assert headers["content-type"] == "application/json"

    def test_user_agent_is_not_urllib_default(self, monkeypatch):
        # Cloudflare (fronting tork.network) blocks the bare urllib default
        # User-Agent ("Python-urllib/<ver>") as a bot signature (HTTP 403,
        # Cloudflare error 1010). The request must carry an explicit
        # tork-governance-python/<version> User-Agent instead.
        captured = self._capture(monkeypatch)
        tork = Tork(api_key="tork_sk_live_test")
        result = tork.govern("hello world")
        result.report.wait(5)

        headers = {k.lower(): v for k, v in captured["request"].headers.items()}
        user_agent = headers["user-agent"]
        assert not user_agent.startswith("Python-urllib")
        assert "tork-governance" in user_agent
        assert core._sdk_version() in user_agent

    def test_client_event_id_matches_local_receipt_id(self, monkeypatch):
        captured = self._capture(monkeypatch)
        tork = Tork(api_key="tork_sk_live_test")
        result = tork.govern("hello world")
        result.report.wait(5)

        body = json.loads(captured["request"].data)
        assert body["client_event_id"] == result.receipt.receipt_id

    def test_decided_at_matches_canonical_ts(self, monkeypatch):
        import datetime
        captured = self._capture(monkeypatch)
        tork = Tork(api_key="tork_sk_live_test")
        result = tork.govern("hello world")
        result.report.wait(5)

        body = json.loads(captured["request"].data)
        canonical = json.loads(body["canonical_json"])
        decided_at_ms = datetime.datetime.fromisoformat(
            body["decided_at"].replace("Z", "+00:00")
        ).timestamp() * 1000
        assert int(decided_at_ms // 1000) == canonical["ts"]

    def test_block_action_never_used_deny_or_allow_used_instead(self, monkeypatch):
        captured = self._capture(monkeypatch)
        tork = Tork(api_key="tork_sk_live_test", default_action=GovernanceAction.DENY)
        result = tork.govern("My SSN is 123-45-6789")
        result.report.wait(5)

        body = json.loads(captured["request"].data)
        assert body["action"] in ("allow", "redact", "deny", "flag")
        assert body["action"] == "deny"


class TestApiKeyWarningStillFiresOnce(object):
    def test_warning_and_reporting_coexist(self, monkeypatch):
        def fake_urlopen(request, timeout=None):
            return FakeResponse(201, {"receipt_id": "tork_rcpt_attest_abc123"})

        monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
        with pytest.warns(UserWarning):
            tork = Tork(api_key="tork_sk_live_test")
        result = tork.govern("hello world")
        assert result.report.wait(5) is True
        assert result.report.succeeded is True


def test_report_timeout_is_15_seconds():
    # Measured production latency (3 consecutive calls, 3 Aug): 8.0s, 5.7s,
    # 4.8s. 15s gives comfortable headroom above the observed worst case.
    assert core._REPORT_TIMEOUT_SECONDS == 15


class TestRetryLogic:
    """Direct tests of _report_attestation_with_retry — the retry policy
    itself, independent of the background-thread wiring in govern()."""

    def _kwargs(self):
        return dict(
            api_key="tork_sk_live_test",
            client_event_id="rcpt_test123",
            verdict="allow",
            canonical_json_str='{"v":"1"}',
            salt="deadbeef",
            fingerprint="TORK-DNA-v2-deadbeef",
            decided_at="2026-08-03T00:00:00Z",
        )

    def test_timeout_triggers_exactly_one_retry(self, monkeypatch):
        calls = {"n": 0}

        def fake_urlopen(request, timeout=None):
            calls["n"] += 1
            raise TimeoutError("The read operation timed out")

        sleeps = []
        monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setattr(core.time, "sleep", lambda s: sleeps.append(s))

        report = core._report_attestation_with_retry(**self._kwargs())

        assert calls["n"] == 2  # initial attempt + exactly one retry
        assert sleeps == [core._REPORT_RETRY_BACKOFF_SECONDS]
        assert report.attempted is True
        assert report.succeeded is False
        assert "not confirmed" in report.reason
        assert "rcpt_test123" in report.reason  # points at the replay-safe client_event_id

    def test_timeout_then_success_retries_once_and_succeeds(self, monkeypatch):
        calls = {"n": 0}

        def fake_urlopen(request, timeout=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise TimeoutError("The read operation timed out")
            return FakeResponse(201, {"receipt_id": "tork_rcpt_attest_abc123"})

        monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setattr(core.time, "sleep", lambda s: None)

        report = core._report_attestation_with_retry(**self._kwargs())

        assert calls["n"] == 2
        assert report.succeeded is True
        assert report.receipt_id == "tork_rcpt_attest_abc123"

    def test_5xx_triggers_one_retry(self, monkeypatch):
        calls = {"n": 0}

        def fake_urlopen(request, timeout=None):
            calls["n"] += 1
            raise urllib.error.HTTPError(
                core.ATTESTATIONS_ENDPOINT, 503, "Service Unavailable", {}, io.BytesIO(b"{}")
            )

        monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setattr(core.time, "sleep", lambda s: None)

        report = core._report_attestation_with_retry(**self._kwargs())

        assert calls["n"] == 2
        assert report.succeeded is False

    def test_422_triggers_no_retry(self, monkeypatch):
        calls = {"n": 0}

        def fake_urlopen(request, timeout=None):
            calls["n"] += 1
            body = json.dumps({"error": "canonical_json mismatch"}).encode("utf-8")
            raise urllib.error.HTTPError(
                core.ATTESTATIONS_ENDPOINT, 422, "Unprocessable Entity", {}, io.BytesIO(body)
            )

        slept = []
        monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setattr(core.time, "sleep", lambda s: slept.append(s))

        report = core._report_attestation_with_retry(**self._kwargs())

        assert calls["n"] == 1  # a 4xx is a real rejection, not retried
        assert slept == []
        assert report.succeeded is False
        assert "canonical_json mismatch" in report.reason

    def test_4xx_reason_does_not_say_not_confirmed(self, monkeypatch):
        # A 4xx is a definitive rejection, not an unknown outcome — the
        # "not confirmed" wording is reserved for timeout/5xx exhaustion.
        def fake_urlopen(request, timeout=None):
            raise urllib.error.HTTPError(
                core.ATTESTATIONS_ENDPOINT, 400, "Bad Request", {}, io.BytesIO(b"{}")
            )

        monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
        report = core._report_attestation_with_retry(**self._kwargs())

        assert "not confirmed" not in report.reason


class TestGovernNeverBlocksOrRaisesOnReporting:
    def test_persistent_timeout_never_raises_and_local_result_still_returned(self, monkeypatch):
        def fake_urlopen(request, timeout=None):
            raise TimeoutError("The read operation timed out")

        monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setattr(core.time, "sleep", lambda s: None)

        tork = Tork(api_key="tork_sk_live_test")
        result = tork.govern("My SSN is 123-45-6789")  # must not raise

        assert result.action == GovernanceAction.REDACT
        assert "[SSN_REDACTED]" in result.output

        assert result.report.wait(5) is True
        assert result.report.succeeded is False
        assert "not confirmed" in result.report.reason
        assert "failed" not in result.report.reason.lower()

    def test_reporting_is_handed_off_to_a_background_thread(self, monkeypatch):
        def fake_urlopen(request, timeout=None):
            return FakeResponse(201, {"receipt_id": "tork_rcpt_attest_abc123"})

        monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)

        tork = Tork(api_key="tork_sk_live_test")
        result = tork.govern("hello world")

        # A background thread was actually created for this call — proof the
        # network call didn't run inline on the caller's thread.
        assert result.report._thread is not None
        assert result.report.wait(5) is True
        assert result.report.succeeded is True
