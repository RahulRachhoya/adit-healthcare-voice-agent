"""Application-owned tool execution log with stable LiveKit function-call IDs."""

import asyncio

from adit_voice_agent.db.models import utcnow
from adit_voice_agent.services.booking import BookingService


class AppointmentTools:
    def __init__(self, sessions, calls, call_id):
        self.bookings = BookingService(sessions)
        self.calls = calls
        self.call_id = call_id

    async def run(self, tool_id, name, arguments):
        started = utcnow().isoformat()
        if name == "get_available_slots":
            result = await asyncio.to_thread(self.bookings.available)
        elif name == "book_appointment":
            call = await asyncio.to_thread(self.calls.raw, self.call_id)
            latest_user = next((t for t in reversed(call.transcript) if t["speaker"] == "user"), None)
            evidence = latest_user["id"] if latest_user else ""
            arguments = {**arguments, "evidence_turn_id": evidence}
            result = await asyncio.to_thread(
                self.bookings.book, self.call_id, arguments["slot_id"], arguments["confirmed"], evidence,
            )
        else:
            raise ValueError("Unknown appointment tool.")
        await asyncio.to_thread(self.calls.append_event, self.call_id, "tool_events", {
            "id": tool_id, "name": name, "arguments": arguments, "result": result,
            "started_at": started, "ended_at": utcnow().isoformat(),
        })
        return result
