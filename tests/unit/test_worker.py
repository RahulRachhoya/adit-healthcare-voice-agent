import json
import time
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from livekit.agents import APIConnectionError, APIStatusError, llm

from adit_voice_agent.agent import worker


@pytest.fixture
def worker_run(monkeypatch, settings, sessions, calls, patient, gateway):
    """Exercise the actual worker lifecycle without any provider connections."""
    call_id, room, _ = calls.reserve(patient, "worker-failure-test")
    quota = APIConnectionError("Synthetic completion attempts exhausted")
    quota.__cause__ = APIStatusError("Synthetic model quota exhausted", status_code=429)
    model = SimpleNamespace(aclose=AsyncMock(), preflight_error=False)
    dial = AsyncMock()
    recording = SimpleNamespace(start=AsyncMock(return_value={"status": "recording"}))
    spoken = []
    callbacks = {}
    behavior = SimpleNamespace(recoverable=False)

    @asynccontextmanager
    async def chat(**kwargs):
        assert kwargs["conn_options"].max_retry == 0
        if model.preflight_error:
            raise quota

        async def chunks():
            yield SimpleNamespace(delta=SimpleNamespace(content="READY"))

        yield chunks()

    model.chat = chat

    @asynccontextmanager
    async def client():
        yield SimpleNamespace(sip=SimpleNamespace(create_sip_participant=dial))

    gateway.client = client

    class Session:
        def __init__(self, **kwargs):
            assert kwargs["conn_options"].llm_conn_options.max_retry == 1
            self.history = SimpleNamespace(items=[])

        def on(self, name):
            def register(callback):
                callbacks[name] = callback
                return callback
            return register

        async def start(self, **kwargs):
            pass

        async def say(self, text, **kwargs):
            spoken.append(text)
            if len(spoken) == 1:
                event = SimpleNamespace(error=llm.LLMError(
                    timestamp=time.time(), label="synthetic", error=quota,
                    recoverable=behavior.recoverable,
                ))
                callbacks["error"](event)
                callbacks["error"](event)
                if behavior.recoverable:
                    callbacks["close"](SimpleNamespace(error=None))

        async def aclose(self):
            callbacks["close"](SimpleNamespace(error=None))

    monkeypatch.setattr(worker, "settings", settings)
    monkeypatch.setattr(worker, "create_session_factory", lambda _: sessions)
    monkeypatch.setattr(worker, "CallService", lambda *_: calls)
    monkeypatch.setattr(worker, "LiveKitGateway", lambda _: gateway)
    monkeypatch.setattr(worker, "RecordingService", lambda _: recording)
    monkeypatch.setattr(worker, "AgentSession", Session)
    monkeypatch.setattr(worker.google, "LLM", lambda **_: model)
    monkeypatch.setattr(worker.inference, "STT", lambda **_: None)
    monkeypatch.setattr(worker.inference, "TTS", lambda **_: None)
    monkeypatch.setattr(worker.silero.VAD, "load", lambda: None)
    ctx = SimpleNamespace(
        job=SimpleNamespace(metadata=json.dumps({"call_id": call_id})),
        room=SimpleNamespace(name=room), connect=AsyncMock(), shutdown=Mock(),
    )
    return SimpleNamespace(
        ctx=ctx, model=model, dial=dial, recording=recording, spoken=spoken,
        behavior=behavior, call_id=call_id,
    )


async def test_unavailable_model_stops_before_dial_or_recording(worker_run, calls):
    worker_run.model.preflight_error = True
    await worker.entrypoint(worker_run.ctx)
    saved = calls.raw(worker_run.call_id)
    assert saved.status == "failed" and "429" in saved.session_error
    assert not saved.dial_started
    worker_run.dial.assert_not_awaited()
    worker_run.recording.start.assert_not_awaited()
    worker_run.model.aclose.assert_awaited_once()


@pytest.mark.parametrize("recoverable", [False, True])
async def test_session_errors_have_the_correct_outcome(worker_run, calls, recoverable):
    worker_run.behavior.recoverable = recoverable
    await worker.entrypoint(worker_run.ctx)
    saved = calls.raw(worker_run.call_id)
    worker_run.dial.assert_awaited_once()
    if recoverable:
        assert saved.status == "completed" and saved.session_error is None
        assert len(worker_run.spoken) == 1
    else:
        assert saved.status == "failed" and "429" in saved.session_error
        assert len(worker_run.spoken) == 2
        assert "technical problem" in worker_run.spoken[-1]
        assert calls.detail(saved.id)["error"] == saved.session_error
