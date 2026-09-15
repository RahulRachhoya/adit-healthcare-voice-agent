"""Call admission, dispatch reconciliation, and persistent session evidence."""

import asyncio
import hashlib
import json
from uuid import uuid4

from sqlalchemy import select

from adit_voice_agent.db.models import Call, Control, utcnow

TERMINAL = {"completed", "unanswered", "failed", "cancelled", "disconnected"}


class CallError(Exception):
    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.status = status


class LiveKitGateway:
    def __init__(self, settings):
        self.settings = settings

    def client(self):
        from livekit import api
        return api.LiveKitAPI(
            url=self.settings.livekit_url,
            api_key=self.settings.livekit_api_key.get_secret_value(),
            api_secret=self.settings.livekit_api_secret.get_secret_value(),
        )

    async def dispatch(self, call_id, room):
        from livekit import api
        async with self.client() as client:
            dispatch = await client.agent_dispatch.create_dispatch(api.CreateAgentDispatchRequest(
                agent_name=self.settings.livekit_agent_name,
                room=room, metadata=json.dumps({"call_id": call_id}),
            ))
            return dispatch.id

    async def find_dispatch(self, room):
        async with self.client() as client:
            dispatches = await client.agent_dispatch.list_dispatch(room)
            return next((d.id for d in dispatches if d.agent_name == self.settings.livekit_agent_name), None)

    async def end(self, room):
        from livekit import api
        async with self.client() as client:
            try:
                await client.room.delete_room(api.DeleteRoomRequest(room=room))
            except api.TwirpError as exc:
                if exc.code != "not_found":
                    raise


class CallService:
    def __init__(self, sessions, settings, gateway=None):
        self.sessions = sessions
        self.settings = settings
        self.gateway = gateway or LiveKitGateway(settings)

    def reserve(self, patient, request_key):
        if not request_key or len(request_key) > 100:
            raise CallError("Provide an Idempotency-Key of 1-100 characters.", 422)
        payload = patient.model_dump(mode="json")
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        with self.sessions.begin() as db:
            control = db.scalar(select(Control).where(Control.id == 1).with_for_update())
            if not control:
                raise CallError("Run the database migrations first.", 503)
            existing = db.scalar(select(Call).where(Call.request_key == request_key))
            if existing:
                if existing.request_digest != digest:
                    raise CallError("This request key belongs to different call input.")
                return existing.id, existing.room_name, False
            if not self.settings.readiness()["calls_enabled"]:
                raise CallError("Live calling is disabled. Complete the setup and trial preflight.", 503)
            if patient.phone not in self.settings.destinations:
                raise CallError("This destination is not on the approved test-number list.", 403)
            if control.active_call_id:
                raise CallError("One call is already active or awaiting dispatch reconciliation.")
            if control.attempts >= self.settings.max_call_attempts:
                raise CallError("The test-call attempt limit has been reached.", 429)
            call_id = str(uuid4())
            room = f"adit-{call_id}"
            call = Call(id=call_id, request_key=request_key, request_digest=digest,
                        room_name=room, input_data=payload)
            db.add(call)
            control.attempts += 1
            control.active_call_id = call_id
            return call_id, room, True

    async def create(self, patient, request_key):
        call_id, room, is_new = await asyncio.to_thread(self.reserve, patient, request_key)
        if is_new:
            try:
                dispatch_id = await asyncio.wait_for(self.gateway.dispatch(call_id, room), timeout=15)
                await asyncio.to_thread(self.update, call_id, dispatch_id=dispatch_id)
            except Exception:
                # A timed-out write might have succeeded. Never automatically create another call.
                try:
                    dispatch_id = await asyncio.wait_for(self.gateway.find_dispatch(room), timeout=10)
                except Exception:
                    dispatch_id = None
                if dispatch_id:
                    await asyncio.to_thread(self.update, call_id, dispatch_id=dispatch_id)
                else:
                    await asyncio.to_thread(
                        self.update_if_queued, call_id, "dispatch_unknown",
                        "Dispatch could not be confirmed. End this call before creating another attempt.",
                    )
        return await asyncio.to_thread(self.detail, call_id)

    def update_if_queued(self, call_id, status, error):
        with self.sessions.begin() as db:
            call = db.scalar(select(Call).where(Call.id == call_id).with_for_update())
            if call.status == "queued":
                call.status, call.error = status, error

    def update(self, call_id, **fields):
        with self.sessions.begin() as db:
            call = db.scalar(select(Call).where(Call.id == call_id).with_for_update())
            if not call:
                raise CallError("Call not found.", 404)
            for name, value in fields.items():
                setattr(call, name, value)

    def raw(self, call_id):
        with self.sessions() as db:
            call = db.get(Call, call_id)
            if not call:
                raise CallError("Call not found.", 404)
            return call

    def claim_worker(self, call_id, room):
        with self.sessions.begin() as db:
            call = db.scalar(select(Call).where(Call.id == call_id).with_for_update())
            if not call or call.room_name != room or call.worker_claimed or call.status in TERMINAL:
                return False
            call.worker_claimed = True
            call.status = "preparing"
            return True

    def claim_dial(self, call_id):
        with self.sessions.begin() as db:
            call = db.scalar(select(Call).where(Call.id == call_id).with_for_update())
            if call.dial_started or call.status in TERMINAL:
                return False
            call.dial_started = True
            call.status = "dialing"
            return True

    def append_event(self, call_id, field, event):
        if field not in {"transcript", "tool_events"}:
            raise ValueError("Unsupported event collection.")
        with self.sessions.begin() as db:
            call = db.scalar(select(Call).where(Call.id == call_id).with_for_update())
            current = getattr(call, field)
            if not any(item["id"] == event["id"] for item in current):
                time_key = "timestamp" if field == "transcript" else "started_at"
                setattr(call, field, sorted([*current, event], key=lambda item: (item.get(time_key, ""), item["id"])))

    def finalize_evidence(self, call_id, transcript, tools):
        with self.sessions.begin() as db:
            call = db.scalar(select(Call).where(Call.id == call_id).with_for_update())
            if call.transcript and not transcript:
                raise ValueError("Final session history is missing persisted conversation turns.")
            merged = {tool["id"]: tool for tool in tools}
            # Business tool events retain their actual transaction timing and result.
            merged.update({tool["id"]: tool for tool in call.tool_events})
            call.transcript = transcript
            call.tool_events = sorted(merged.values(), key=lambda item: (item["started_at"], item["id"]))
            call.evidence_complete = True

    def finish(self, call_id, status, error=None):
        if status not in TERMINAL:
            raise ValueError("Expected a terminal call status.")
        with self.sessions.begin() as db:
            control = db.scalar(select(Control).where(Control.id == 1).with_for_update())
            call = db.scalar(select(Call).where(Call.id == call_id).with_for_update())
            if call.status not in TERMINAL:
                call.status = status
                call.ended_at = utcnow()
            if error:
                call.error = error
                if status == "failed":
                    call.session_error = error
            if control and control.active_call_id == call_id:
                control.active_call_id = None

    async def end(self, call_id):
        call = await asyncio.to_thread(self.raw, call_id)
        if call.status not in TERMINAL:
            try:
                await asyncio.wait_for(self.gateway.end(call.room_name), timeout=15)
            except Exception as exc:
                raise CallError("Unable to confirm call termination. The call remains reserved.", 503) from exc
            await asyncio.to_thread(self.finish, call_id, "cancelled")
        return await asyncio.to_thread(self.detail, call_id)

    def detail(self, call_id):
        from adit_voice_agent.services.booking import BookingService
        call = self.raw(call_id)
        from adit_voice_agent.services.review import review_metrics
        booking = BookingService(self.sessions).result(call_id)
        patient = dict(call.input_data)
        patient["phone"] = f"••••{patient['phone'][-4:]}"
        return {
            "id": call.id, "status": call.status, "patient": patient,
            "created_at": call.created_at.isoformat(),
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            "transcript": call.transcript, "tool_events": call.tool_events,
            "evidence_complete": call.evidence_complete,
            "booking": booking, "review_metrics": review_metrics(call, booking),
            "recording": {"status": call.recording.get("status", "pending")},
            "analysis": call.analysis, "analysis_status": call.analysis_status,
            "finalization_status": call.finalization_status, "export_status": call.export_status,
            "trace_url": call.trace_url, "evaluation": call.evaluation,
            "error": call.error or call.session_error, "session_error": call.session_error,
        }

    def listing(self):
        with self.sessions() as db:
            calls = db.scalars(select(Call).order_by(Call.created_at.desc()).limit(50)).all()
            return [{"id": c.id, "name": c.input_data["name"], "status": c.status,
                     "created_at": c.created_at.isoformat(), "analysis_status": c.analysis_status,
                     "export_status": c.export_status} for c in calls]
