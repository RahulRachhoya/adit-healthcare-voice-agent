"""Installed-SDK contract checks; no connections, microphone, or phone calls."""

import json
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from google import genai
from google.genai import types
from google.protobuf.duration_pb2 import Duration
from livekit import api
from livekit.agents import llm

from adit_voice_agent.agent.healthcare_agent import HealthcareAgent
from adit_voice_agent.services.calls import LiveKitGateway
from adit_voice_agent.services.post_call import GeminiAnalyzer


def test_agent_tools_register_with_livekit():
    agent = HealthcareAgent(
        {"name": "Synthetic", "phone": "+12025550123", "biomarkers": []},
        SimpleNamespace(), set(), lambda: None,
    )
    assert agent is not None
    assert "+12025550123" not in agent.instructions
    assert len(agent.tools) == 3


def test_sip_and_recording_protobuf_contracts():
    request = api.CreateSIPParticipantRequest(
        sip_trunk_id="synthetic", room_name="synthetic", sip_call_to="+12025550123",
        participant_identity="synthetic", wait_until_answered=True,
        max_call_duration=Duration(seconds=180), ringing_timeout=Duration(seconds=35),
    )
    request.destination.country = "IN"
    assert request.max_call_duration.ToTimedelta() == timedelta(seconds=180)
    output = api.EncodedFileOutput(file_type=api.EncodedFileType.OGG, filepath="synthetic.ogg",
                                  s3=api.S3Upload(force_path_style=True, bucket="private"))
    egress = api.RoomCompositeEgressRequest(room_name="synthetic", audio_only=True, file_outputs=[output])
    assert egress.audio_only and egress.file_outputs[0].s3.force_path_style


async def test_dispatch_uses_real_sdk_list_shape(settings, monkeypatch):
    seen = []

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        @property
        def agent_dispatch(self):
            return self

        async def list_dispatch(self, room):
            seen.append(room)
            return [SimpleNamespace(id="existing", agent_name=settings.livekit_agent_name)]

    gateway = LiveKitGateway(settings)
    monkeypatch.setattr(gateway, "client", lambda: Client())
    assert await gateway.find_dispatch("synthetic-room") == "existing"
    assert seen == ["synthetic-room"]


def test_transcript_and_tool_output_fields_exist():
    message = llm.ChatMessage(role="user", content=["Yes."])
    assert message.text_content == "Yes."
    output = llm.FunctionCallOutput(call_id="tool-one", name="book_appointment", output='{"status":"booked"}', is_error=False)
    assert output.call_id == "tool-one" and not output.is_error


@pytest.mark.parametrize("analysis_model,expected_model", [
    ("", "gemini-3.6-flash"),
    ("gemini-3.5-flash-lite", "gemini-3.5-flash-lite"),
])
async def test_gemini_analysis_uses_supported_json_schema(settings, monkeypatch, analysis_model, expected_model):
    """Exercise model selection and the real SDK serializer without network calls."""
    settings = settings.model_copy(update={"gemini_analysis_model": analysis_model})
    fixture = json.loads(
        (Path(__file__).parents[2] / "examples" / "completed_call.synthetic.json").read_text()
    )
    requests = []

    def respond(request):
        assert request.url.path.endswith(f"/models/{expected_model}:generateContent")
        assert settings.gemini_model == "gemini-3.6-flash"
        body = json.loads(request.content)
        requests.append(body)
        config = body["generationConfig"]
        if "responseSchema" in config:
            return httpx.Response(400, json={"error": {
                "code": 400, "status": "INVALID_ARGUMENT",
                "message": "Use responseJsonSchema for additionalProperties.",
            }})
        schema = config["responseJsonSchema"]
        assert schema["additionalProperties"] is False
        assert "appointment_details" in schema["properties"]
        assert config["responseMimeType"] == "application/json"
        assert config["thinkingConfig"]["thinking_level"] == "MINIMAL"
        return httpx.Response(200, json={"candidates": [{
            "content": {"role": "model", "parts": [{"text": json.dumps(fixture["analysis"])}]},
            "finishReason": "STOP",
        }]})

    original_client = genai.Client
    transport = httpx.MockTransport(respond)
    monkeypatch.setattr(genai, "Client", lambda **kwargs: original_client(
        **kwargs, http_options=types.HttpOptions(async_client_args={"transport": transport}),
    ))
    result = await GeminiAnalyzer(settings).analyze({
        name: fixture[name] for name in ("transcript", "tool_events", "booking")
    })
    assert len(requests) == 1
    assert result.model_dump() == fixture["analysis"]


@pytest.mark.parametrize("module", ["adit_voice_agent.agent.worker", "adit_voice_agent.web.app"])
def test_entrypoints_import_without_provider_connections(module):
    import importlib
    assert importlib.import_module(module)
