from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from adit_voice_agent.services.review import review_metrics


def saved_call(**changes):
    start = datetime(2026, 9, 15, 12, tzinfo=UTC)
    return SimpleNamespace(**{
        "created_at": start, "ended_at": start + timedelta(seconds=100),
        "status": "failed", "recording": {"status": "ready"},
        "input_data": {"biomarkers": [{"name": "Blood glucose"}, {"name": "HbA1c"}]},
        "transcript": [{"speaker": "assistant"}, {"speaker": "user"}], "tool_events": [],
        "analysis": {"outcome": "not_attempted", "patient_reached": True,
                     "consultation_offered": False, "metrics_discussed": []},
        "analysis_status": "ready", "evaluation": {"status": "completed", "scores": [{"value": 1}]},
        **changes,
    })


def test_passing_report_does_not_hide_call_failure():
    result = review_metrics(saved_call(), {"status": "not_attempted"})
    assert result["call_status"] == "failed"
    assert result["booking_outcome"] == "not_attempted"
    assert result["metrics_discussed"] == 0 and result["metrics_supplied"] == 2
    assert result["recipient_turns"] == 1 and result["request_duration_seconds"] == 100
    assert result["recording_duration_seconds"] is None


def test_pending_analysis_and_active_duration_are_unknown():
    result = review_metrics(saved_call(analysis=None, ended_at=None, status="active"), {"status": "not_attempted"})
    assert result["metrics_discussed"] is None
    assert result["consultation_offered"] is None
    assert result["request_duration_seconds"] is None


def test_metrics_count_only_supplied_names_and_actual_tool_failures():
    call = saved_call(
        analysis={"outcome": "failed", "metrics_discussed": ["hba1c", "HbA1c", "invented metric"]},
        tool_events=[{"result": {"status": "failed"}}, {"result": []}, {"error": "Tool failed."}],
    )
    result = review_metrics(call, {"status": "not_attempted"})
    assert result["metrics_discussed"] == 1
    assert result["tool_calls"] == 3 and result["failed_tool_calls"] == 2
