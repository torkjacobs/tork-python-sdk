"""Optional agent telemetry on the governance call: agent_id, agent_role,
session_id, session_turn. Passed through to the attestation request when set,
omitted entirely when not. urllib.request.urlopen is always monkeypatched."""

import json

import pytest

import tork_governance.core as core
from tork_governance import Tork

FIELDS = ("agent_id", "agent_role", "session_id", "session_turn")


class FakeResponse:
    status = 201

    def read(self):
        return json.dumps({"receipt_id": "tork_rcpt_attest_x"}).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def captured(monkeypatch):
    seen = []

    def fake_urlopen(request, timeout=None):
        seen.append(json.loads(request.data.decode("utf-8")))
        return FakeResponse()

    monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
    return seen


def _govern(**kw):
    tork = Tork(api_key="tork_sk_live_test")
    result = tork.govern("Contact me at test@example.com", **kw)
    assert result.report.wait(5) is True
    return result


def test_all_four_fields_sent_when_set(captured):
    _govern(agent_id="a1", agent_role="planner", session_id="s1", session_turn=3)
    body = captured[0]
    assert body["agent_id"] == "a1"
    assert body["agent_role"] == "planner"
    assert body["session_id"] == "s1"
    assert body["session_turn"] == 3
    assert isinstance(body["session_turn"], int)


def test_fields_omitted_when_not_set(captured):
    _govern()
    assert not any(f in captured[0] for f in FIELDS)


def test_only_set_fields_are_sent(captured):
    _govern(session_id="s9")
    body = captured[0]
    assert body["session_id"] == "s9"
    for f in ("agent_id", "agent_role", "session_turn"):
        assert f not in body


def test_session_turn_zero_is_sent(captured):
    _govern(session_turn=0)
    assert captured[0]["session_turn"] == 0


def test_fields_not_in_canonical_json(captured):
    _govern(agent_id="a1", session_turn=2)
    canonical = json.loads(captured[0]["canonical_json"])
    assert not any(f in canonical for f in FIELDS)


def test_local_result_carries_session_context():
    result = Tork().govern("hello", agent_id="a1", session_turn=2)
    assert result.session_context.agent_id == "a1"
    assert result.receipt.session_context.session_turn == 2


@pytest.mark.parametrize("bad", ["3", 1.5, True])
def test_session_turn_must_be_int(bad):
    with pytest.raises(TypeError):
        Tork().govern("hello", session_turn=bad)
