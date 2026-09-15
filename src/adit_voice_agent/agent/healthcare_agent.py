"""Small LiveKit Agent; business operations remain outside the SDK subclass."""

import asyncio
import json
from pathlib import Path

from livekit.agents import Agent, RunContext, function_tool


class HealthcareAgent(Agent):
    def __init__(self, patient, appointment_tools, pending_writes, end_conversation):
        prompt = (Path(__file__).parents[1] / "prompts" / "healthcare_agent.md").read_text(encoding="utf-8")
        facts = dict(patient)
        facts.pop("phone", None)
        super().__init__(instructions=f"{prompt}\n\nPATIENT_DATA:\n{json.dumps(facts, ensure_ascii=False)}")
        self.appointment_tools = appointment_tools
        self.pending_writes = pending_writes
        self.end_conversation = end_conversation

    @function_tool
    async def finish_call(self, context: RunContext) -> dict:
        """After speaking goodbye, end the call. Also use for refusal or wrong recipient."""
        await context.wait_for_playout()
        self.end_conversation()
        return {"status": "ending"}

    @function_tool
    async def get_available_slots(self, context: RunContext) -> dict:
        """Get the real available simulated doctor slots. Never invent slots."""
        return await self.appointment_tools.run(context.function_call.call_id, "get_available_slots", {})

    @function_tool
    async def book_appointment(self, context: RunContext, slot_id: str, confirmed: bool) -> dict:
        """Book a returned slot only after the recipient explicitly confirms the full appointment."""
        if self.pending_writes:
            await asyncio.gather(*list(self.pending_writes))
        return await self.appointment_tools.run(
            context.function_call.call_id, "book_appointment",
            {"slot_id": slot_id, "confirmed": confirmed},
        )
