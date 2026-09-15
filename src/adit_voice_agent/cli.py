"""Small, explicit operator commands. No command places a telephone call."""

import argparse
import asyncio
import getpass
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from argon2 import PasswordHasher
from sqlalchemy import text

from adit_voice_agent.config import get_settings
from adit_voice_agent.db.models import Slot
from adit_voice_agent.db.session import create_session_factory
from adit_voice_agent.services.post_call import PostCallProcessor, adapter_for


def hash_password():
    first = getpass.getpass("New operator password (at least 12 characters): ")
    second = getpass.getpass("Repeat password: ")
    if first != second or len(first) < 12:
        raise SystemExit("Passwords must match and be at least 12 characters.")
    print(PasswordHasher().hash(first))


def check_setup():
    parser = argparse.ArgumentParser(description="Check configuration and database access; never dial.")
    parser.add_argument("--database", action="store_true", help="Also connect to the database.")
    args = parser.parse_args()
    settings = get_settings()
    result = settings.readiness()
    if args.database:
        try:
            sessions = create_session_factory(settings.database_url)
            with sessions() as db:
                db.execute(text("SELECT id FROM control WHERE id=1")).scalar_one()
            result["database"] = "connected and migrated"
        except Exception:
            result["database"] = "unavailable or not migrated"
    print(json.dumps(result, indent=2))


def seed_demo_data():
    parser = argparse.ArgumentParser(description="Seed future synthetic appointment slots; never create calls.")
    parser.add_argument("--file", default="examples/appointment_slots.json")
    args = parser.parse_args()
    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    if data.get("synthetic") is not True:
        raise SystemExit("Only explicitly synthetic slot definitions are accepted.")
    zone = ZoneInfo(data["timezone"])
    today = datetime.now(zone).date()
    sessions = create_session_factory(get_settings().database_url)
    count = 0
    with sessions.begin() as db:
        for item in data["slots"]:
            day = today + timedelta(days=item["days_from_today"])
            start = datetime(day.year, day.month, day.day, item["hour"], item["minute"], tzinfo=zone)
            slot_id = f"demo-{start:%Y%m%d-%H%M}"
            if db.get(Slot, slot_id) is None:
                db.add(Slot(id=slot_id, doctor=item["doctor"], starts_at=start.astimezone(UTC), timezone=data["timezone"]))
                count += 1
    print(f"Created {count} synthetic appointment slots.")


def retry_finalization():
    parser = argparse.ArgumentParser(description="Resume saved post-call processing; never redial.")
    parser.add_argument("call_id")
    args = parser.parse_args()
    settings = get_settings()
    processor = PostCallProcessor(create_session_factory(settings.database_url), settings)
    asyncio.run(processor.process(args.call_id))
    call = processor.calls.raw(args.call_id)
    print(json.dumps({"call_id": call.id, "finalization": call.finalization_status,
                      "analysis": call.analysis_status, "recording": call.recording.get("status"),
                      "export": call.export_status}, indent=2))


def configure_evaluation():
    parser = argparse.ArgumentParser(description="Create the documented Opik online evaluation rule.")
    parser.add_argument("--file", default="evaluations/booking_outcome_correctness.json")
    args = parser.parse_args()
    result = adapter_for(get_settings()).configure_evaluation(
        json.loads(Path(args.file).read_text(encoding="utf-8"))
    )
    print(json.dumps(result, indent=2))
