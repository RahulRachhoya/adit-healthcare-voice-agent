"""Validated application contracts independent of any voice or telemetry SDK."""

from datetime import date
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Biomarker(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)
    value: Decimal = Field(ge=0, max_digits=12, decimal_places=4)
    unit: str = Field(min_length=1, max_length=30)
    measured_at: date

    @field_validator("measured_at")
    @classmethod
    def no_future_measurement(cls, value):
        if value > date.today():
            raise ValueError("Measurement date must not be in the future.")
        return value


class PatientInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(pattern=r"^\+[1-9]\d{6,14}$")
    timezone: str = "Asia/Kolkata"
    biomarkers: list[Biomarker] = Field(min_length=1, max_length=10)
    recipient_consented: Literal[True]

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Use an IANA timezone such as Asia/Kolkata.") from exc
        return value


class Analysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(max_length=2500)
    patient_reached: bool
    metrics_discussed: list[str]
    consultation_offered: bool
    appointment_booked: bool
    appointment_details: dict | None = None
    outcome: Literal["booked", "declined", "callback_requested", "failed", "not_attempted", "unknown"]
    outcome_reason: str
    follow_up_needed: bool
    evidence: list[str]


class CallReport(BaseModel):
    schema_version: int = 1
    call_id: str
    started_at: str
    ended_at: str
    call_status: str
    metadata: dict
    variables: dict
    transcript: list[dict]
    tool_events: list[dict]
    booking: dict
    recording: dict
    analysis: dict
