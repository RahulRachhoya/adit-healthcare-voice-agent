"""Real PostgreSQL concurrency checks in a disposable, uniquely named schema."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from adit_voice_agent.db.models import Base, Booking, Call, Control, Slot, utcnow
from adit_voice_agent.services.booking import BookingService
from adit_voice_agent.services.calls import CallError, CallService

pytestmark = pytest.mark.postgres


@pytest.fixture
def pg_sessions():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url or not url.startswith("postgresql"):
        pytest.skip("TEST_DATABASE_URL is required for real PostgreSQL verification.")
    namespace = f"assessment_test_{uuid4().hex}"
    root = create_engine(url)
    with root.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{namespace}"'))
    engine = root.execution_options(schema_translate_map={None: namespace})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions.begin() as db:
        db.add(Control(id=1, attempts=0))
        db.add(Slot(id="slot-one", doctor="Dr. Synthetic", starts_at=utcnow() + timedelta(days=1), timezone="UTC"))
    try:
        yield sessions
    finally:
        with root.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{namespace}" CASCADE'))
        root.dispose()


def test_postgres_slot_race_has_one_winner(pg_sessions, patient):
    identifiers = [str(uuid4()), str(uuid4())]
    with pg_sessions.begin() as db:
        for identifier in identifiers:
            db.add(Call(id=identifier, request_key=identifier, request_digest="test",
                        room_name=identifier, input_data=patient.model_dump(mode="json"), status="active",
                        transcript=[{"id": "yes", "speaker": "user", "text": "Yes.", "timestamp": utcnow().isoformat()}]))
    service = BookingService(pg_sessions)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda identifier: service.book(identifier, "slot-one", True, "yes"), identifiers))
    assert sorted(result["status"] for result in results) == ["booked", "failed"]
    with pg_sessions() as db:
        assert len(db.scalars(select(Booking)).all()) == 1


def test_postgres_duplicate_admission_is_atomic(pg_sessions, settings, patient, gateway):
    service = CallService(pg_sessions, settings, gateway)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: service.reserve(patient, "same-key"), range(2)))
    assert results[0][0] == results[1][0]
    assert sorted(result[2] for result in results) == [False, True]


def test_postgres_global_call_limit_is_atomic(pg_sessions, settings, patient, gateway):
    service = CallService(pg_sessions, settings, gateway)

    def reserve(index):
        try:
            return service.reserve(patient, f"request-{index}")[0]
        except CallError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, range(2)))
    assert sum(result is not None for result in results) == 1
