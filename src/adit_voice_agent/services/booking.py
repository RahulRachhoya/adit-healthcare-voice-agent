"""Transactional simulated appointments with explicit conversational evidence."""

from datetime import UTC
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from adit_voice_agent.db.models import Booking, Call, Slot, utcnow
from adit_voice_agent.services.availability import ensure_upcoming_slots


def slot_dict(slot: Slot, timezone: str | None = None) -> dict:
    start = slot.starts_at
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    timezone = timezone or slot.timezone
    return {"id": slot.id, "doctor": slot.doctor, "starts_at": start.isoformat(),
            "local_time": start.astimezone(ZoneInfo(timezone)).isoformat(),
            "timezone": timezone}


def booking_dict(booking: Booking, slot: Slot, timezone: str | None = None) -> dict:
    return {"status": "booked", "appointment_id": booking.id, "slot": slot_dict(slot, timezone),
            "confirmation_evidence": booking.confirmation_evidence, "reason": ""}


class BookingService:
    def __init__(self, sessions):
        self.sessions = sessions

    def available(self, timezone: str | None = None) -> dict:
        with self.sessions.begin() as db:
            current_slots = ensure_upcoming_slots(db)
            occupied = select(Booking.slot_id)
            slots = db.scalars(select(Slot).where(
                Slot.id.in_(current_slots), Slot.starts_at > utcnow(), Slot.id.not_in(occupied)
            ).order_by(Slot.starts_at)).all()
            return {"slots": [slot_dict(slot, timezone) for slot in slots], "simulated": True}

    def result(self, call_id: str) -> dict:
        with self.sessions() as db:
            booking = db.scalar(select(Booking).where(Booking.call_id == call_id))
            if not booking:
                return {"status": "not_attempted", "appointment_id": None, "slot": None, "reason": ""}
            call = db.get(Call, call_id)
            return booking_dict(booking, db.get(Slot, booking.slot_id), call.input_data.get("timezone"))

    def book(self, call_id: str, slot_id: str, confirmed: bool, evidence_turn_id: str) -> dict:
        def failure(reason):
            return {"status": "failed", "appointment_id": None, "slot": None, "reason": reason}

        try:
            with self.sessions.begin() as db:
                call = db.scalar(select(Call).where(Call.id == call_id).with_for_update())
                if not call:
                    return failure("Unknown call.")
                existing = db.scalar(select(Booking).where(Booking.call_id == call_id))
                if existing:
                    return booking_dict(existing, db.get(Slot, existing.slot_id), call.input_data.get("timezone"))
                if call.status != "active":
                    return failure("The call is no longer active.")
                evidence = next((t for t in call.transcript
                                 if t.get("id") == evidence_turn_id and t.get("speaker") == "user"), None)
                latest_user = next((t for t in reversed(call.transcript) if t.get("speaker") == "user"), None)
                text = evidence["text"].lower().translate(str.maketrans(",.!?", "    ")) if evidence else ""
                affirmation = " ".join(text.split())
                affirmative = {
                    "yes", "yes please", "yes book it", "yes please book it", "please book it",
                    "i confirm", "confirmed", "go ahead", "yes go ahead", "that works", "yes that works",
                    "yes you can book the appointment", "please book the appointment",
                    "yes please book the appointment", "yes book the appointment",
                }
                if not confirmed or not evidence or evidence != latest_user or affirmation not in affirmative:
                    return failure("Please ask the recipient to say yes to confirm the appointment.")
                slot = db.scalar(select(Slot).where(Slot.id == slot_id).with_for_update())
                if not slot:
                    return failure("Unknown appointment slot.")
                start = slot.starts_at.replace(tzinfo=UTC) if slot.starts_at.tzinfo is None else slot.starts_at
                if start <= utcnow():
                    return failure("The slot is in the past.")
                if db.scalar(select(Booking).where(Booking.slot_id == slot_id)):
                    return failure("That slot is no longer available.")
                booking = Booking(id=str(uuid4()), call_id=call_id, slot_id=slot_id,
                                  confirmation_evidence=evidence_turn_id)
                db.add(booking)
                db.flush()
                return booking_dict(booking, slot, call.input_data.get("timezone"))
        except IntegrityError:
            # A concurrent writer may have booked either this call or this slot.
            existing = self.result(call_id)
            return existing if existing["status"] == "booked" else failure("That slot is no longer available.")
