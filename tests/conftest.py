"""Synthetic fixtures; provider calls are replaced, never enabled against a network."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from argon2 import PasswordHasher

from adit_voice_agent.config import Settings
from adit_voice_agent.db.models import Base, Control, Slot, utcnow
from adit_voice_agent.db.session import create_session_factory
from adit_voice_agent.schemas import Analysis, PatientInput
from adit_voice_agent.services.calls import CallService

TEST_PASSWORD = "unit-test-password-only"


@pytest.fixture(scope="session")
def encoded_password():
    return PasswordHasher().hash(TEST_PASSWORD)


@pytest.fixture
def settings(encoded_password):
    return Settings(
        _env_file=None, database_url="postgresql+psycopg://unused:unused@localhost/unused",
        session_secret="test-session-secret-that-is-long-enough", admin_password_hash=encoded_password,
        allowed_hosts="testserver,127.0.0.1,localhost", live_calls_enabled=True,
        free_trial_verified=True, allowed_phone_numbers="+12025550123,+12025550124",
        livekit_url="wss://unused.example", livekit_api_key="unused",
        livekit_api_secret="unused", livekit_sip_trunk_id="unused",
        google_api_key="unused", tts_voice="unused", supabase_url="https://unused.supabase.co",
        supabase_service_role_key="unused", s3_endpoint="https://unused.example",
        s3_region="unused", s3_access_key="unused", s3_secret_key="unused",
        opik_api_key="unused", opik_workspace="unused", opik_rule_id="unused",
    )


@pytest.fixture
def sessions(tmp_path):
    factory = create_session_factory(f"sqlite:///{(tmp_path / 'unit.db').as_posix()}")
    Base.metadata.create_all(factory.kw["bind"])
    with factory.begin() as db:
        db.add(Control(id=1, attempts=0))
        db.add(Slot(id="slot-one", doctor="Dr. Demo", starts_at=utcnow() + timedelta(days=1), timezone="Asia/Kolkata"))
        db.add(Slot(id="slot-two", doctor="Dr. Demo", starts_at=utcnow() + timedelta(days=2), timezone="Asia/Kolkata"))
    yield factory
    factory.kw["bind"].dispose()


@pytest.fixture
def patient():
    return PatientInput(
        name="Alex Synthetic", phone="+12025550123", timezone="Asia/Kolkata",
        biomarkers=[{"name": "HbA1c", "value": "5.8", "unit": "%", "measured_at": "2026-01-01"}],
        recipient_consented=True,
    )


class FakeGateway:
    def __init__(self):
        self.dispatch_count = 0
        self.ends = []
        self.fail_dispatch = False
        self.found = None
        self.fail_end = False

    async def dispatch(self, call_id, room):
        self.dispatch_count += 1
        if self.fail_dispatch:
            raise TimeoutError("synthetic timeout")
        return "dispatch-test"

    async def find_dispatch(self, room):
        return self.found

    async def end(self, room):
        if self.fail_end:
            raise TimeoutError("synthetic termination timeout")
        self.ends.append(room)


@pytest.fixture
def gateway():
    return FakeGateway()


@pytest.fixture
def calls(sessions, settings, gateway):
    return CallService(sessions, settings, gateway)


@pytest.fixture
def active_call(calls, patient):
    call_id, _, _ = calls.reserve(patient, "active-test-request")
    calls.update(call_id, status="active", evidence_complete=True)
    calls.append_event(call_id, "transcript", {
        "id": "turn-yes", "speaker": "user", "text": "Yes, please book it.",
        "timestamp": utcnow().isoformat(), "interrupted": False,
    })
    return call_id


class FakeAnalyzer:
    def __init__(self):
        self.count = 0
        self.fail = False

    async def analyze(self, payload):
        self.count += 1
        if self.fail:
            raise RuntimeError("synthetic model outage")
        booked = payload["booking"]["status"] == "booked"
        return Analysis(
            summary="Synthetic test analysis.", patient_reached=True,
            metrics_discussed=[], consultation_offered=True, appointment_booked=booked,
            appointment_details=payload["booking"] if booked else None,
            outcome="booked" if booked else "declined", outcome_reason="Test evidence.",
            follow_up_needed=False, evidence=[t["id"] for t in payload["transcript"]],
        )


class FakeRecording:
    def __init__(self):
        self.ready = True

    async def complete(self, recording):
        return {**recording, "status": "ready" if self.ready else "pending", "object_key": "synthetic.ogg"}

    async def signed_url(self, recording, expires_in=300):
        if recording.get("status") != "ready":
            raise ValueError("Recording is not ready.")
        return "https://unused.supabase.co/synthetic-signed-reference"


class FakeAdapter:
    def __init__(self):
        self.reports = []
        self.fail = False

    def publish_completed_call(self, report):
        if self.fail:
            raise RuntimeError("synthetic telemetry outage")
        self.reports.append(report)
        return {"trace_id": "synthetic-trace", "url": "https://example.invalid/synthetic-trace"}

    def get_evaluation(self, trace_id):
        return {"status": "completed", "scores": [{"name": "booking_outcome_correctness", "value": 1, "reason": "Synthetic test."}]}


@pytest.fixture
def fakes():
    return SimpleNamespace(analyzer=FakeAnalyzer(), recording=FakeRecording(), adapter=FakeAdapter())
