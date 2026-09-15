from types import SimpleNamespace

import pytest
from livekit.agents import llm

from adit_voice_agent.agent.evidence import history_evidence


def test_final_history_preserves_interruption_and_missing_tool_output():
    items = [
        SimpleNamespace(type="message", role="assistant", text_content="Your appointment",
                        id="message-one", created_at=10, interrupted=True),
        SimpleNamespace(type="function_call", call_id="tool-one", name="book_appointment",
                        arguments='{"slot_id":"slot-one"}', created_at=11),
    ]
    transcript, tools = history_evidence(items, "1970-01-01T00:00:12+00:00")
    assert transcript[0]["interrupted"] is True
    assert tools[0]["result"]["status"] == "unknown"
    assert "booked" not in tools[0]["result"]


def test_final_history_maps_real_tool_output():
    items = [
        SimpleNamespace(type="function_call", call_id="tool-one", name="get_available_slots",
                        arguments="{}", created_at=10),
        SimpleNamespace(type="function_call_output", call_id="tool-one",
                        output='{"slots":[]}', created_at=11, is_error=False),
    ]
    _, tools = history_evidence(items, "unused")
    assert tools[0]["result"] == {"slots": []}
    assert tools[0]["ended_at"] == "1970-01-01T00:00:11+00:00"


@pytest.mark.parametrize("output,expected", [
    ('["slot-one"]', {"output": ["slot-one"]}),
    ("provider unavailable", {"output": "provider unavailable", "is_error": True}),
])
def test_shared_normalizer_preserves_non_object_and_error_outputs(output, expected):
    call = llm.FunctionCall(
        call_id="tool-one", name="get_available_slots", arguments="invalid-json", created_at=10,
    )
    result = llm.FunctionCallOutput(
        call_id="tool-one", name="get_available_slots", output=output, is_error=True, created_at=11,
    )
    _, tools = history_evidence([call, result], "unused")
    assert tools[0]["arguments"] == {"invalid_arguments": True}
    assert tools[0]["result"] == expected
