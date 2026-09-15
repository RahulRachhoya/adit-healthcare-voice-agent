"""Bounded, restartable analysis and export after a call has ended."""

import asyncio
import json
from datetime import UTC, timedelta
from pathlib import Path

from sqlalchemy import select

from adit_voice_agent.db.models import Call, utcnow
from adit_voice_agent.integrations.opik_integration import OpikIntegration, stable_id
from adit_voice_agent.schemas import Analysis, CallReport
from adit_voice_agent.services.booking import BookingService
from adit_voice_agent.services.calls import TERMINAL, CallService
from adit_voice_agent.services.recording import RecordingService


def adapter_for(settings):
    return OpikIntegration(
        api_key=settings.opik_api_key.get_secret_value(), workspace=settings.opik_workspace,
        project_name=settings.opik_project_name, host=settings.opik_url_override,
        web_url=settings.opik_web_url,
    )


def validate_analysis(analysis: Analysis, booking: dict, transcript: list, tools: list) -> Analysis:
    booked = booking["status"] == "booked"
    if analysis.appointment_booked != booked:
        raise ValueError("Analysis contradicts the saved booking.")
    if booked and (analysis.outcome != "booked" or analysis.appointment_details != booking):
        raise ValueError("Analysis appointment details do not match the booking.")
    if not booked and (analysis.outcome == "booked" or analysis.appointment_details is not None):
        raise ValueError("Analysis invents an appointment.")
    ids = {item["id"] for item in [*transcript, *tools]}
    if not set(analysis.evidence).issubset(ids):
        raise ValueError("Analysis cites nonexistent evidence.")
    return analysis


class GeminiAnalyzer:
    def __init__(self, settings):
        self.settings = settings

    async def analyze(self, payload) -> Analysis:
        from google import genai
        from google.genai import types
        prompt = (Path(__file__).parents[1] / "prompts" / "post_call_analysis.md").read_text(encoding="utf-8")
        client = genai.Client(api_key=self.settings.google_api_key.get_secret_value())
        try:
            response = await asyncio.wait_for(client.aio.models.generate_content(
                model=self.settings.analysis_model,
                contents=json.dumps(payload, ensure_ascii=False),
                config=types.GenerateContentConfig(
                    system_instruction=prompt, response_mime_type="application/json",
                    response_json_schema=Analysis.model_json_schema(), temperature=0,
                    thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL),
                ),
            ), timeout=30)
            return Analysis.model_validate_json(response.text)
        finally:
            await client.aio.aclose()


class PostCallProcessor:
    def __init__(self, sessions, settings, analyzer=None, recording=None, adapter=None):
        self.sessions = sessions
        self.settings = settings
        self.calls = CallService(sessions, settings)
        self.bookings = BookingService(sessions)
        self.analyzer = analyzer or GeminiAnalyzer(settings)
        self.recording = recording or RecordingService(settings)
        self.adapter = adapter or adapter_for(settings)

    def acquire(self, call_id):
        with self.sessions.begin() as db:
            call = db.scalar(select(Call).where(Call.id == call_id).with_for_update())
            if not call or call.status not in TERMINAL or call.finalization_status == "complete":
                return False
            until = call.finalization_until
            if until and (until.replace(tzinfo=UTC) if until.tzinfo is None else until) > utcnow():
                return False
            call.finalization_until = utcnow() + timedelta(minutes=3)
            call.finalization_status = "processing"
            return True

    async def process(self, call_id):
        if not await asyncio.to_thread(self.acquire, call_id):
            return
        try:
            call = await asyncio.to_thread(self.calls.raw, call_id)
            if not call.evidence_complete:
                await asyncio.to_thread(self.calls.update, call_id, analysis_status="blocked",
                                        error="Final conversation evidence is incomplete. Recover session history before retrying.")
                return
            # Make saved audio playable even when the analysis provider is unavailable.
            try:
                recording = call.recording
                if recording.get("status") != "ready":
                    recording = await asyncio.wait_for(self.recording.complete(recording), timeout=45)
            except Exception:
                recording = {**call.recording, "status": "pending", "error": "Recording completion could not be confirmed."}
            await asyncio.to_thread(self.calls.update, call_id, recording=recording)
            booking = await asyncio.to_thread(self.bookings.result, call_id)
            payload = {"call_status": call.status, "transcript": call.transcript,
                       "tool_events": call.tool_events, "booking": booking}
            prior_timing = (call.report or {}).get("metadata", {}).get("analysis_timing", {})
            analysis_start = prior_timing.get("started_at") or utcnow().isoformat()
            if call.analysis is not None and call.analysis_status == "ready":
                analysis = Analysis.model_validate(call.analysis)
            elif not call.transcript:
                analysis = Analysis(
                    summary="No conversation was captured.", patient_reached=False, metrics_discussed=[],
                    consultation_offered=False, appointment_booked=booking["status"] == "booked",
                    appointment_details=booking if booking["status"] == "booked" else None,
                    outcome="booked" if booking["status"] == "booked" else "not_attempted",
                    outcome_reason=call.status, follow_up_needed=True, evidence=[],
                )
            else:
                try:
                    analysis = await self.analyzer.analyze(payload)
                    validate_analysis(analysis, booking, call.transcript, call.tool_events)
                except Exception:
                    await asyncio.to_thread(self.calls.update, call_id, analysis_status="failed",
                                            error="Analysis failed validation or the model request failed. Retry finalization.")
                    return
            analysis_end = prior_timing.get("ended_at") or utcnow().isoformat()
            await asyncio.to_thread(self.calls.update, call_id, analysis=analysis.model_dump(mode="json"), analysis_status="ready")
            # A no-answer call has no completed conversation to score. Preserve its evidence locally.
            if not call.transcript and booking["status"] != "booked":
                await asyncio.to_thread(self.calls.update, call_id, export_status="not_applicable",
                                        finalization_status="complete")
                return
            variables = dict(call.input_data)
            variables.pop("phone", None)
            ended = (call.ended_at or utcnow()).isoformat()
            started = call.created_at.isoformat()
            report = CallReport(
                call_id=call.id, started_at=started, ended_at=ended, call_status=call.status,
                metadata={"room_name": call.room_name, "dispatch_id": call.dispatch_id,
                          "synthetic_health_data": True, "finalized_at": utcnow().isoformat(),
                          "analysis_timing": {"started_at": analysis_start, "ended_at": analysis_end,
                                              "model": self.settings.analysis_model}},
                variables=variables, transcript=call.transcript, tool_events=call.tool_events,
                booking=booking,
                recording={**recording, "bucket": self.settings.recording_bucket,
                           "storage_endpoint": self.settings.s3_endpoint,
                           "playback_page": f"{self.settings.app_base_url.rstrip('/')}/calls/{call.id}#recording"},
                analysis=analysis.model_dump(mode="json"),
            ).model_dump(mode="json")
            await asyncio.to_thread(self.calls.update, call_id, report=report, trace_id=stable_id(call.id, started))
            if recording.get("status") != "ready":
                await asyncio.to_thread(self.calls.update, call_id, export_status="waiting_for_recording")
                return
            try:
                reference = await asyncio.to_thread(self.adapter.publish_completed_call, report)
                await asyncio.to_thread(self.calls.update, call_id, trace_id=reference["trace_id"],
                                        trace_url=reference["url"], export_status="ready",
                                        finalization_status="complete", error=None)
            except Exception:
                await asyncio.to_thread(self.calls.update, call_id, export_status="failed",
                                        error="Opik export/read-back failed. Evidence is saved; retry finalization.")
        finally:
            call = await asyncio.to_thread(self.calls.raw, call_id)
            await asyncio.to_thread(
                self.calls.update, call_id, finalization_until=None,
                finalization_status="complete" if call.finalization_status == "complete" else "pending",
            )
