"""Persist today's synthetic schedule without moving previously offered appointments."""

import json
from datetime import UTC, datetime, timedelta
from importlib.resources import files
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError

from adit_voice_agent.db.models import Slot, utcnow


def ensure_upcoming_slots(db) -> list[str]:
    definition = json.loads(
        files("adit_voice_agent").joinpath("data/appointment_slots.json").read_text(encoding="utf-8")
    )
    if definition.get("synthetic") is not True:
        raise ValueError("Only explicitly synthetic appointment definitions are supported.")
    zone = ZoneInfo(definition["timezone"])
    today = utcnow().astimezone(zone).date()
    identifiers = []
    for item in definition["slots"]:
        if item["days_from_today"] < 1:
            raise ValueError("Appointment offsets must be in the future.")
        day = today + timedelta(days=item["days_from_today"])
        start = datetime(day.year, day.month, day.day, item["hour"], item["minute"], tzinfo=zone)
        identifier = f"demo-{start:%Y%m%d-%H%M}"
        identifiers.append(identifier)
        if db.get(Slot, identifier) is not None:
            continue
        try:
            # The web service and worker may request availability together.
            # A concurrent insert must not roll back the rest of this request.
            with db.begin_nested():
                db.add(Slot(id=identifier, doctor=item["doctor"], starts_at=start.astimezone(UTC),
                            timezone=definition["timezone"]))
                db.flush()
        except IntegrityError:
            if db.get(Slot, identifier) is None:
                raise
    return identifiers
