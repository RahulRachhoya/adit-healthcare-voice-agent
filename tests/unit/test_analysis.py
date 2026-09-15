import pytest

from adit_voice_agent.schemas import Analysis
from adit_voice_agent.services.post_call import validate_analysis


def analysis(**changes):
    return Analysis(
        **{
            "summary": "Test", "patient_reached": True, "metrics_discussed": [],
            "consultation_offered": True, "appointment_booked": False,
            "appointment_details": None, "outcome": "declined", "outcome_reason": "No",
            "follow_up_needed": False, "evidence": ["turn1"], **changes,
        }
    )


def test_valid_refusal():
    value = analysis()
    assert validate_analysis(value, {"status": "not_attempted"}, [{"id": "turn1"}], []) == value


def test_invented_booking_is_rejected():
    with pytest.raises(ValueError, match="contradicts"):
        validate_analysis(analysis(appointment_booked=True, outcome="booked"), {"status": "not_attempted"}, [], [])


def test_wrong_booking_details_are_rejected():
    with pytest.raises(ValueError, match="details"):
        validate_analysis(analysis(appointment_booked=True, outcome="booked", appointment_details={"id": "wrong"}),
                          {"status": "booked", "appointment_id": "right"}, [], [])


def test_call_failure_does_not_imply_failed_booking():
    with pytest.raises(ValueError, match="without a failed booking attempt"):
        validate_analysis(analysis(outcome="failed"), {"status": "not_attempted"}, [{"id": "turn1"}], [])
    value = analysis(outcome="not_attempted", outcome_reason="Voice model quota exhausted.")
    assert validate_analysis(value, {"status": "not_attempted"}, [{"id": "turn1"}], []) == value


def test_failed_booking_tool_supports_failed_outcome():
    value = analysis(outcome="failed", evidence=["booking-tool"])
    tools = [{"id": "booking-tool", "name": "book_appointment", "result": {"status": "failed"}}]
    assert validate_analysis(value, {"status": "not_attempted"}, [], tools) == value


def test_nonexistent_evidence_rejected():
    with pytest.raises(ValueError, match="nonexistent"):
        validate_analysis(analysis(), {"status": "not_attempted"}, [], [])
