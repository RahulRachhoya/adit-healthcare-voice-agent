from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from adit_voice_agent.agent.tools import AppointmentTools
from adit_voice_agent.db.models import Slot
from adit_voice_agent.services import availability, booking
from adit_voice_agent.services.booking import BookingService


@pytest.fixture
def clock(monkeypatch):
    def set_clock(instant):
        monkeypatch.setattr(availability, "utcnow", lambda: instant)
        monkeypatch.setattr(booking, "utcnow", lambda: instant)
    set_clock(datetime(2026, 9, 15, 22, tzinfo=UTC))  # Already September 16 in India.
    return set_clock


def test_upcoming_dates_use_clinic_day_and_distinct_names(sessions, clock):
    slots = BookingService(sessions).available()["slots"]
    assert [slot["local_time"][:10] for slot in slots] == [
        "2026-09-20", "2026-09-24", "2026-09-28",
    ]
    assert [slot["doctor"] for slot in slots] == [
        "Dr. Meera Shah", "Dr. Arjun Rao", "Dr. Kavya Menon",
    ]
    assert all("(demo)" not in slot["doctor"] for slot in slots)


def test_refresh_does_not_duplicate_slots_and_rollover_keeps_booking(sessions, active_call, clock):
    service = BookingService(sessions)
    slots = service.available()["slots"]
    with sessions() as db:
        before = db.scalar(select(func.count()).select_from(Slot))
    assert service.available()["slots"] == slots
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Slot)) == before
    saved = service.book(active_call, slots[0]["id"], True, "turn-yes")
    assert saved["status"] == "booked"
    assert slots[0]["id"] not in [slot["id"] for slot in service.available()["slots"]]
    clock(datetime(2026, 9, 16, 22, tzinfo=UTC))
    assert [slot["local_time"][:10] for slot in service.available()["slots"]] == [
        "2026-09-21", "2026-09-25", "2026-09-29",
    ]
    assert service.result(active_call) == saved


def test_offsets_roll_into_next_year(sessions, clock):
    clock(datetime(2026, 12, 27, 22, tzinfo=UTC))
    assert [slot["local_time"][:10] for slot in BookingService(sessions).available()["slots"]] == [
        "2027-01-01", "2027-01-05", "2027-01-09",
    ]


@pytest.mark.parametrize("instant,offset", [
    (datetime(2026, 9, 15, 22, tzinfo=UTC), timedelta(hours=-4)),
    (datetime(2026, 10, 28, 22, tzinfo=UTC), timedelta(hours=-5)),
])
async def test_selected_timezone_matches_offer_booking_and_report(
    sessions, calls, active_call, clock, instant, offset,
):
    clock(instant)
    patient = calls.raw(active_call).input_data
    calls.update(active_call, input_data={**patient, "timezone": "America/New_York"})
    tools = AppointmentTools(sessions, calls, active_call)
    slot = (await tools.run("get-slots", "get_available_slots", {}))["slots"][0]
    assert slot["timezone"] == "America/New_York"
    local = datetime.fromisoformat(slot["local_time"])
    assert local.utcoffset() == offset
    assert local == datetime.fromisoformat(slot["starts_at"])
    saved = await tools.run("book-slot", "book_appointment", {
        "slot_id": slot["id"], "confirmed": True,
    })
    assert saved["status"] == "booked"
    assert saved["slot"] == slot
    assert BookingService(sessions).result(active_call) == saved
    with sessions() as db:
        assert db.get(Slot, slot["id"]).timezone == "Asia/Kolkata"
