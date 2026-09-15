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


def test_nonexistent_evidence_rejected():
    with pytest.raises(ValueError, match="nonexistent"):
        validate_analysis(analysis(), {"status": "not_attempted"}, [], [])
