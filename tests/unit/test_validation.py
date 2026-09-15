from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from adit_voice_agent.config import Settings
from adit_voice_agent.schemas import PatientInput


@pytest.mark.parametrize("phone", ["12345", "+012345678", "hello", "+1<script>", "+123"])
def test_invalid_phone_rejected(patient, phone):
    data = patient.model_dump(mode="json")
    data["phone"] = phone
    with pytest.raises(ValidationError):
        PatientInput.model_validate(data)


@pytest.mark.parametrize("change", [
    {"recipient_consented": False}, {"timezone": "not/a/timezone"}, {"name": "   "},
    {"unexpected_field": "ignored?"}, {"biomarkers": []},
])
def test_invalid_call_input_rejected(patient, change):
    with pytest.raises(ValidationError):
        PatientInput.model_validate({**patient.model_dump(mode="json"), **change})


def test_missing_unit_and_future_date_rejected(patient):
    data = patient.model_dump(mode="json")
    data["biomarkers"][0]["unit"] = ""
    with pytest.raises(ValidationError):
        PatientInput.model_validate(data)
    data["biomarkers"][0]["unit"] = "%"
    data["biomarkers"][0]["measured_at"] = (date.today() + timedelta(days=1)).isoformat()
    with pytest.raises(ValidationError):
        PatientInput.model_validate(data)


def test_decimal_value_is_preserved(patient):
    assert patient.model_dump(mode="json")["biomarkers"][0]["value"] == "5.8"


def test_calls_disabled_by_default():
    settings = Settings(_env_file=None)
    assert settings.readiness()["calls_enabled"] is False
    assert settings.readiness()["live_test_verified"] is False


def test_production_cannot_use_sqlite_or_http():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production")


def test_limits_cannot_exceed_approved_budget():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, max_call_attempts=11)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, max_call_seconds=181)
