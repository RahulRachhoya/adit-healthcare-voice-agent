from adit_voice_agent.services.booking import BookingService
from adit_voice_agent.services.post_call import PostCallProcessor


def processor(sessions, settings, fakes):
    return PostCallProcessor(sessions, settings, analyzer=fakes.analyzer,
                             recording=fakes.recording, adapter=fakes.adapter)


async def test_complete_flow_preserves_authoritative_booking(calls, sessions, settings, active_call, fakes):
    booking = BookingService(sessions).book(active_call, "slot-one", True, "turn-yes")
    calls.finish(active_call, "completed")
    process = processor(sessions, settings, fakes)
    await process.process(active_call)
    result = calls.raw(active_call)
    assert result.finalization_status == "complete"
    assert result.analysis["appointment_details"] == booking
    assert result.export_status == "ready"
    report = fakes.adapter.reports[0]
    assert "phone" not in report["variables"]
    # The recording remains identifiable when the app only has a loopback address.
    assert report["recording"]["storage_endpoint"] == settings.s3_endpoint
    assert report["recording"]["bucket"] == settings.recording_bucket
    assert report["recording"]["object_key"] == "synthetic.ogg"
    assert report["recording"]["playback_page"].endswith(f"/calls/{active_call}#recording")
    assert "s3_secret_key" not in report["recording"]
    assert "supabase_service_role_key" not in report["recording"]
    await process.process(active_call)
    assert fakes.analyzer.count == 1
    assert len(fakes.adapter.reports) == 1


async def test_export_failure_can_resume_without_rebooking(calls, sessions, settings, active_call, fakes):
    BookingService(sessions).book(active_call, "slot-one", True, "turn-yes")
    calls.finish(active_call, "completed")
    fakes.adapter.fail = True
    process = processor(sessions, settings, fakes)
    await process.process(active_call)
    before = calls.raw(active_call)
    assert before.export_status == "failed"
    assert before.analysis["appointment_booked"]
    assert before.finalization_until is None
    fakes.adapter.fail = False
    await process.process(active_call)
    assert calls.raw(active_call).export_status == "ready"
    assert fakes.analyzer.count == 1


async def test_pending_recording_does_not_become_success(calls, sessions, settings, active_call, fakes):
    calls.finish(active_call, "disconnected")
    fakes.recording.ready = False
    await processor(sessions, settings, fakes).process(active_call)
    call = calls.raw(active_call)
    assert call.recording["status"] == "pending"
    assert call.export_status == "waiting_for_recording"
    assert call.finalization_status == "pending"
    assert fakes.adapter.reports == []


async def test_analysis_outage_preserves_transcript(calls, sessions, settings, active_call, fakes):
    calls.finish(active_call, "completed")
    fakes.analyzer.fail = True
    await processor(sessions, settings, fakes).process(active_call)
    call = calls.raw(active_call)
    assert call.transcript and call.analysis_status == "failed"
    assert call.recording["status"] == "ready"
    assert call.finalization_until is None
    assert fakes.adapter.reports == []


async def test_incomplete_evidence_cannot_be_exported(calls, sessions, settings, active_call, fakes):
    calls.finish(active_call, "completed")
    calls.update(active_call, evidence_complete=False)
    await processor(sessions, settings, fakes).process(active_call)
    call = calls.raw(active_call)
    assert call.analysis_status == "blocked"
    assert call.finalization_status == "pending"
    assert fakes.analyzer.count == 0
    assert fakes.adapter.reports == []


async def test_unanswered_call_has_no_fabricated_conversation(calls, patient, sessions, settings, fakes):
    call_id, _, _ = calls.reserve(patient, "no-answer")
    calls.finish(call_id, "unanswered")
    calls.finalize_evidence(call_id, [], [])
    await processor(sessions, settings, fakes).process(call_id)
    call = calls.raw(call_id)
    assert call.analysis["patient_reached"] is False
    assert call.transcript == []
    assert call.export_status == "not_applicable"
    assert fakes.analyzer.count == 0
