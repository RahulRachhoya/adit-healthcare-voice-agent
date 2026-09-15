from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from livekit import api

from adit_voice_agent.services.calls import LiveKitGateway
from adit_voice_agent.services.recording import RecordingService


@pytest.mark.parametrize(
    ("result_fields", "expected_status", "expected_size"),
    [
        ({"file": api.FileInfo(size=123140)}, "ready", 123140),
        ({"file_results": [api.FileInfo(size=123140)]}, "ready", 123140),
        ({"file": api.FileInfo(size=0)}, "failed", None),
        ({"file_results": [api.FileInfo(size=0)]}, "failed", None),
        ({}, "failed", None),
    ],
    ids=["cloud-singular-file", "file-results", "empty-file", "empty-file-results", "missing-file"],
)
async def test_recording_completion_handles_cloud_file_formats(
    monkeypatch, result_fields, expected_status, expected_size,
):
    completed = api.EgressInfo(status=api.EgressStatus.EGRESS_COMPLETE, **result_fields)
    client = SimpleNamespace(egress=SimpleNamespace(
        stop_egress=AsyncMock(),
        list_egress=AsyncMock(return_value=api.ListEgressResponse(items=[completed])),
    ))
    context = MagicMock()
    context.__aenter__.return_value = client
    monkeypatch.setattr(LiveKitGateway, "client", lambda _: context)

    result = await RecordingService(SimpleNamespace()).complete({
        "status": "failed",
        "error": "Earlier recording failure",
        "egress_id": "EG_SYNTHETIC",
        "object_key": "calls/synthetic/conversation.ogg",
    })

    assert result["status"] == expected_status
    assert result.get("size") == expected_size
    assert result["object_key"] == "calls/synthetic/conversation.ogg"
    if expected_status == "ready":
        assert result.get("error") is None
