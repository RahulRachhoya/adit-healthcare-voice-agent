"""Separate LiveKit worker: dial once, preserve evidence, finalize after hangup."""

import asyncio
import json
import logging
from datetime import UTC, datetime

from google.genai import types
from google.protobuf.duration_pb2 import Duration
from livekit import api
from livekit.agents import (
    AgentServer,
    AgentSession,
    APIConnectOptions,
    JobContext,
    cli,
    inference,
    llm,
    room_io,
)
from livekit.agents.voice.agent_session import SessionConnectOptions
from livekit.plugins import google, silero

from adit_voice_agent.agent.evidence import history_evidence
from adit_voice_agent.agent.healthcare_agent import HealthcareAgent
from adit_voice_agent.agent.tools import AppointmentTools
from adit_voice_agent.config import get_settings
from adit_voice_agent.db.session import create_session_factory
from adit_voice_agent.services.calls import CallService, LiveKitGateway
from adit_voice_agent.services.post_call import PostCallProcessor
from adit_voice_agent.services.recording import RecordingService

logger = logging.getLogger("adit.agent")
settings = get_settings()
server = AgentServer(
    num_idle_processes=0, session_end_timeout=180, shutdown_process_timeout=30,
    ws_url=settings.livekit_url or None,
    api_key=settings.livekit_api_key.get_secret_value() or None,
    api_secret=settings.livekit_api_secret.get_secret_value() or None,
)


class VoiceModelUnavailable(RuntimeError):
    """The model could not respond before a telephone call was attempted."""


def model_failure_reason(exc: Exception) -> str:
    seen = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        if getattr(exc, "status_code", None) == 429 or getattr(exc, "code", None) == 429:
            return "Conversation model quota exhausted (429). The voice conversation could not continue."
        exc = exc.__cause__ or exc.__context__
    return "The conversation model was unavailable. The voice conversation could not continue."


async def verify_voice_model(model):
    """Check usable model capacity before spending telephone or recording credit."""
    context = llm.ChatContext()
    context.add_message(role="user", content="Reply with READY only.")
    try:
        async with asyncio.timeout(10):
            async with model.chat(
                chat_ctx=context, conn_options=APIConnectOptions(max_retry=0, timeout=8),
            ) as stream:
                async for chunk in stream:
                    if chunk.delta and chunk.delta.content and chunk.delta.content.strip():
                        return
        raise RuntimeError("The model returned no text.")
    except Exception as exc:
        raise VoiceModelUnavailable(model_failure_reason(exc)) from exc


async def after_session(ctx: JobContext):
    state = getattr(ctx, "adit_state", None)
    if not state:
        return
    if state["writes"]:
        await asyncio.gather(*list(state["writes"]), return_exceptions=True)
    try:
        session = state.get("session")
        items = session.history.items if session is not None else []
        transcript, tools = history_evidence(items, datetime.now(UTC).isoformat())
        await asyncio.to_thread(state["calls"].finalize_evidence, state["call_id"], transcript, tools)
        await PostCallProcessor(state["sessions"], settings).process(state["call_id"])
    except Exception:
        logger.error("Post-call processing requires retry for call_id=%s", state["call_id"])


@server.rtc_session(agent_name=settings.livekit_agent_name, on_session_end=after_session)
async def entrypoint(ctx: JobContext):
    try:
        call_id = json.loads(ctx.job.metadata or "{}")["call_id"]
    except (ValueError, KeyError):
        ctx.shutdown(reason="Missing call identity")
        return
    sessions = create_session_factory(settings.database_url)
    calls = CallService(sessions, settings)
    if not await asyncio.to_thread(calls.claim_worker, call_id, ctx.room.name):
        ctx.shutdown(reason="Duplicate or invalid dispatch")
        return
    writes = set()
    write_errors = []
    ctx.adit_state = {"sessions": sessions, "calls": calls, "call_id": call_id, "writes": writes}
    call = await asyncio.to_thread(calls.raw, call_id)
    closed = asyncio.Event()
    close_error = False
    outcome = "failed"
    error = None
    session = None
    voice_model = None

    def enqueue(field, event):
        task = asyncio.create_task(asyncio.to_thread(calls.append_event, call_id, field, event))
        writes.add(task)

        def completed(done):
            writes.discard(done)
            if not done.cancelled() and done.exception():
                write_errors.append(type(done.exception()).__name__)
                closed.set()

        task.add_done_callback(completed)

    try:
        if not settings.readiness()["calls_enabled"] or call.input_data["phone"] not in settings.destinations:
            raise RuntimeError("Agent preflight incomplete or destination not approved")
        voice_model = google.LLM(
            model=settings.gemini_model, api_key=settings.google_api_key.get_secret_value(),
            thinking_config={"thinking_level": "minimal"},
            automatic_function_calling_config=types.AutomaticFunctionCallingConfig(disable=True),
            http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)),
        )
        await verify_voice_model(voice_model)
        session = AgentSession(
            stt=inference.STT(model=settings.stt_model, language="en",
                              api_key=settings.livekit_api_key.get_secret_value(),
                              api_secret=settings.livekit_api_secret.get_secret_value()),
            llm=voice_model,
            conn_options=SessionConnectOptions(
                llm_conn_options=APIConnectOptions(max_retry=1, retry_interval=0.5, timeout=8),
            ),
            tts=inference.TTS(model=settings.tts_model, voice=settings.tts_voice, language="en",
                              api_key=settings.livekit_api_key.get_secret_value(),
                              api_secret=settings.livekit_api_secret.get_secret_value()),
            vad=silero.VAD.load(), max_tool_steps=3,
        )

        ctx.adit_state["session"] = session

        @session.on("conversation_item_added")
        def capture(event):
            transcript, _ = history_evidence([event.item], datetime.now(UTC).isoformat())
            for turn in transcript:
                enqueue("transcript", turn)

        @session.on("function_tools_executed")
        def capture_tools(event):
            outputs = event.function_call_outputs
            completed_ids = {output.call_id for output in outputs}
            # Missing outputs are recovered from final history after the session ends.
            completed_calls = [tool for tool in event.function_calls if tool.call_id in completed_ids]
            _, tools = history_evidence(
                [*completed_calls, *outputs], datetime.fromtimestamp(event.created_at, UTC).isoformat(),
            )
            for tool in tools:
                enqueue("tool_events", tool)

        @session.on("error")
        def provider_failed(event):
            nonlocal close_error, error
            if getattr(event.error, "recoverable", True) or close_error:
                return
            close_error = True
            error = (
                model_failure_reason(event.error.error)
                if event.error.type == "llm_error"
                else "A speech service failed. The voice conversation could not continue."
            )
            logger.error("Provider failure for call_id=%s, component=%s", call_id, event.error.type)
            closed.set()

        @session.on("close")
        def session_closed(event):
            nonlocal close_error, error
            close_error = close_error or event.error is not None
            if close_error and not error:
                error = "The voice session closed because of a provider error."
            closed.set()

        await ctx.connect()
        rec = await asyncio.wait_for(RecordingService(settings).start(call_id, call.room_name), timeout=30)
        await asyncio.to_thread(calls.update, call_id, recording=rec)
        identity = f"recipient-{call_id}"
        await session.start(
            agent=HealthcareAgent(call.input_data, AppointmentTools(sessions, calls, call_id), writes, closed.set),
            room=ctx.room,
            room_options=room_io.RoomOptions(participant_identity=identity, close_on_disconnect=True),
        )
        if close_error:
            raise RuntimeError("A speech service failed before dialing.")
        if not await asyncio.to_thread(calls.claim_dial, call_id):
            return
        request = api.CreateSIPParticipantRequest(
            sip_trunk_id=settings.livekit_sip_trunk_id, sip_call_to=call.input_data["phone"],
            room_name=call.room_name, participant_identity=identity,
            participant_name="Test recipient", hide_phone_number=True, wait_until_answered=True,
            ringing_timeout=Duration(seconds=35), max_call_duration=Duration(seconds=settings.max_call_seconds),
        )
        if settings.livekit_destination_country:
            request.destination.country = settings.livekit_destination_country
        async with LiveKitGateway(settings).client() as client:
            await asyncio.wait_for(client.sip.create_sip_participant(request), timeout=45)
        current = await asyncio.to_thread(calls.raw, call_id)
        if current.ended_at is not None:
            return
        await asyncio.to_thread(calls.update, call_id, status="active")
        await session.say(
            "Hello, this is an AI assistant for a healthcare demonstration. This call is being recorded. "
            f"Am I speaking with {call.input_data['name']}, and are you comfortable continuing?",
            allow_interruptions=True,
        )
        try:
            await asyncio.wait_for(closed.wait(), timeout=settings.max_call_seconds)
        except TimeoutError:
            await session.say("We have reached the demonstration time limit. Thank you, and goodbye.")
        if close_error:
            try:
                await asyncio.wait_for(session.say(
                    "I'm sorry, a technical problem means I cannot continue this call. "
                    "Please try again later. Goodbye.", allow_interruptions=False,
                ), timeout=8)
            except Exception:
                logger.warning("Could not play the failure notice for call_id=%s", call_id)
        outcome = "failed" if close_error or write_errors else "completed"
        if write_errors:
            error = "Conversation evidence could not be saved completely. Do not treat this call as verified."
    except Exception as exc:
        if isinstance(exc, api.TwirpError) and str((exc.metadata or {}).get("sip_status_code", "")) in {"408", "480", "486", "603"}:
            outcome = "unanswered"
        error = error or (
            str(exc) if isinstance(exc, VoiceModelUnavailable)
            else "The voice session did not complete. Inspect LiveKit/provider logs using the call identity."
        )
        logger.error("Voice session failed for call_id=%s, error_type=%s", call_id, type(exc).__name__)
    finally:
        if session is not None:
            try:
                await session.aclose()
            except Exception:
                error = error or "Voice session shutdown was interrupted. Verify saved evidence."
        if voice_model is not None:
            try:
                await voice_model.aclose()
            except Exception:
                logger.warning("Model connection cleanup failed for call_id=%s", call_id)
        if writes:
            await asyncio.gather(*list(writes), return_exceptions=True)
        if close_error or write_errors:
            outcome = "failed"
        try:
            await asyncio.wait_for(calls.gateway.end(call.room_name), timeout=15)
        except Exception:
            await asyncio.to_thread(calls.update, call_id, error="Room termination is unconfirmed. Use End call to reconcile.")
        else:
            await asyncio.to_thread(calls.finish, call_id, outcome, error)
        ctx.shutdown(reason="Assessment call finished")


def main():
    cli.run_app(server)


if __name__ == "__main__":
    main()
