"""Small LiveKit Agent; business operations remain outside the SDK subclass."""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from livekit.agents import Agent, RunContext, function_tool

from adit_voice_agent.timezones import TIMEZONE_LABELS


class HealthcareAgent(Agent):
    def __init__(self, patient, appointment_tools, pending_writes):
        prompt = (Path(__file__).parents[1] / "prompts" / "healthcare_agent.md").read_text(encoding="utf-8")
        facts = dict(patient)
        facts.pop("phone", None)
        super().__init__(instructions=f"{prompt}\n\nPATIENT_DATA:\n{json.dumps(facts, ensure_ascii=False)}")
        self.appointment_tools = appointment_tools
        self.pending_writes = pending_writes
        self._closing = False

    async def _close_after_speech(self, context: RunContext, message: str):
        if self._closing:
            return
        self._closing = True
        await context.wait_for_playout()
        await context.session.say(message, allow_interruptions=False)
        # Drain preserves the spoken farewell and this tool's result before the
        # worker receives the close event and deletes the telephone room.
        context.session.once("function_tools_executed", lambda event: event.cancel_tool_reply())
        context.session.shutdown(drain=True)

    @function_tool
    async def finish_call(self, context: RunContext) -> dict:
        """Speak the final goodbye and disconnect. Use for refusal or wrong recipient.

        This tool delivers the farewell itself; do not speak another goodbye first.
        """
        await self._close_after_speech(context, "Thank you. Goodbye, and take care.")
        return {"status": "ending"}

    @function_tool
    async def get_available_slots(self, context: RunContext) -> dict:
        """Get the real available simulated doctor slots. Never invent slots."""
        return await self.appointment_tools.run(context.function_call.call_id, "get_available_slots", {})

    @function_tool
    async def book_appointment(self, context: RunContext, slot_id: str, confirmed: bool) -> dict:
        """Book a returned slot after explicit recipient confirmation.

        Success speaks the saved appointment details and goodbye, then disconnects.
        Failure leaves the call open so the recipient can choose another slot or retry.
        """
        if self.pending_writes:
            await asyncio.gather(*list(self.pending_writes))
        result = await self.appointment_tools.run(
            context.function_call.call_id, "book_appointment",
            {"slot_id": slot_id, "confirmed": confirmed},
        )
        if result["status"] == "booked":
            slot = result["slot"]
            local = datetime.fromisoformat(slot["local_time"])
            date = f"{local:%B} {local.day}, {local.year}"
            time = local.strftime("%I:%M %p").lstrip("0")
            timezone = TIMEZONE_LABELS.get(slot["timezone"], slot["timezone"].replace("_", " "))
            await self._close_after_speech(
                context,
                f"Your simulated appointment is confirmed with {slot['doctor']} "
                f"on {date} at {time}, {timezone} time. "
                "Thank you. Goodbye, and take care.",
            )
        return result
