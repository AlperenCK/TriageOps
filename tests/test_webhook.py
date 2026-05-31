"""Webhook payload ayristirma testleri (build id + basarisizlik tespiti)."""

from devops_agent.triggers.webhook import extract_build_id, is_failure


def test_extract_build_complete(load_fixture):
    payload = load_fixture("webhook_build_complete.json")
    assert extract_build_id(payload) == 12345
    assert is_failure(payload) is True


def test_extract_run_state_changed(load_fixture):
    payload = load_fixture("webhook_run_state_changed.json")
    assert extract_build_id(payload) == 67890
    assert is_failure(payload) is True


def test_not_failure():
    payload = {"resource": {"id": 1, "result": "succeeded"}}
    assert is_failure(payload) is False
