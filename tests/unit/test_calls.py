import pytest

from adit_voice_agent.db.models import Control
from adit_voice_agent.services.calls import CallError


async def test_duplicate_submission_dials_only_once(calls, patient, gateway, sessions):
    first = await calls.create(patient, "same-request")
    second = await calls.create(patient, "same-request")
    assert first["id"] == second["id"]
    assert gateway.dispatch_count == 1
    with sessions() as db:
        assert db.get(Control, 1).attempts == 1


async def test_reused_key_with_changed_input_rejected(calls, patient):
    await calls.create(patient, "same-request")
    with pytest.raises(CallError, match="different call input"):
        await calls.create(patient.model_copy(update={"name": "Different"}), "same-request")


async def test_second_active_call_rejected(calls, patient, gateway):
    await calls.create(patient, "first")
    with pytest.raises(CallError, match="already active"):
        await calls.create(patient, "second")
    assert gateway.dispatch_count == 1


async def test_dispatch_timeout_reconciles_without_redial(calls, patient, gateway):
    gateway.fail_dispatch = True
    gateway.found = "accepted-original-dispatch"
    call = await calls.create(patient, "request")
    assert calls.raw(call["id"]).dispatch_id == gateway.found
    assert gateway.dispatch_count == 1


async def test_unknown_dispatch_blocks_new_call_until_ended(calls, patient, gateway):
    gateway.fail_dispatch = True
    call = await calls.create(patient, "first")
    assert call["status"] == "dispatch_unknown"
    with pytest.raises(CallError):
        await calls.create(patient, "second")
    await calls.end(call["id"])
    assert calls.raw(call["id"]).status == "cancelled"


async def test_unconfirmed_termination_keeps_reservation(calls, patient, gateway, sessions):
    call = await calls.create(patient, "first")
    gateway.fail_end = True
    with pytest.raises(CallError, match="termination"):
        await calls.end(call["id"])
    with sessions() as db:
        assert db.get(Control, 1).active_call_id == call["id"]


async def test_call_attempt_limit_is_persistent(calls, patient, settings):
    settings.max_call_attempts = 1
    first = await calls.create(patient, "first")
    await calls.end(first["id"])
    with pytest.raises(CallError, match="attempt limit"):
        await calls.create(patient, "second")


async def test_destination_allowlist(calls, patient):
    with pytest.raises(CallError, match="approved"):
        await calls.create(patient.model_copy(update={"phone": "+12025550999"}), "request")


def test_duplicate_worker_and_dial_are_rejected(calls, patient):
    call_id, room, _ = calls.reserve(patient, "request")
    assert calls.claim_worker(call_id, room)
    assert not calls.claim_worker(call_id, room)
    assert calls.claim_dial(call_id)
    assert not calls.claim_dial(call_id)


def test_event_deduplication_and_phone_redaction(calls, active_call):
    call = calls.raw(active_call)
    calls.append_event(active_call, "transcript", call.transcript[0])
    assert len(calls.raw(active_call).transcript) == 1
    assert "+12025550123" not in str(calls.detail(active_call))
