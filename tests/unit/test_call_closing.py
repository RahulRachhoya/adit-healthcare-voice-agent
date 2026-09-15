import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from livekit.agents import AgentSession, llm

from adit_voice_agent.agent.healthcare_agent import HealthcareAgent
from tests.unit.test_model_fallback import ScriptedModel


def booking():
    return {
        "status": "booked", "appointment_id": "private-confirmation-id",
        "slot": {"doctor": "Dr. Meera Shah", "local_time": "2026-09-17T10:00:00+05:30",
                 "timezone": "Asia/Kolkata"},
    }


def agent_and_context(result=None):
    tools = SimpleNamespace(run=AsyncMock(return_value=result or booking()))
    agent = HealthcareAgent({"name": "Synthetic", "biomarkers": []}, tools, set())
    context = SimpleNamespace(
        function_call=SimpleNamespace(call_id="book-call"),
        wait_for_playout=AsyncMock(),
        session=SimpleNamespace(say=AsyncMock(), shutdown=Mock(), once=Mock()),
    )
    return agent, context, tools


async def test_success_waits_for_confirmation_and_farewell_before_shutdown():
    agent, context, _ = agent_and_context()
    started, played = asyncio.Event(), asyncio.Event()

    async def speak(text, **kwargs):
        assert kwargs["allow_interruptions"] is False
        started.set()
        await played.wait()

    context.session.say.side_effect = speak
    task = asyncio.create_task(agent.book_appointment(context, "slot", True))
    try:
        await asyncio.wait_for(started.wait(), timeout=1)
        context.session.shutdown.assert_not_called()
        text = context.session.say.call_args.args[0]
        assert "Dr. Meera Shah" in text and "September 17, 2026 at 10:00 AM" in text
        assert "India time" in text and "Goodbye, and take care" in text
        assert "(demo)" not in text and "private-confirmation-id" not in text
    finally:
        played.set()
    assert await task == booking()
    context.session.shutdown.assert_called_once_with(drain=True)


async def test_failed_booking_keeps_call_open_for_another_attempt():
    result = {"status": "failed", "reason": "That slot is no longer available."}
    agent, context, tools = agent_and_context(result)
    assert await agent.book_appointment(context, "slot", True) == result
    context.session.say.assert_not_awaited()
    context.session.shutdown.assert_not_called()
    tools.run.return_value = booking()
    assert (await agent.book_appointment(context, "another-slot", True))["status"] == "booked"
    context.session.shutdown.assert_called_once_with(drain=True)


async def test_duplicate_success_does_not_repeat_farewell():
    agent, context, _ = agent_and_context()
    await agent.book_appointment(context, "slot", True)
    await agent.book_appointment(context, "slot", True)
    context.session.say.assert_awaited_once()
    context.session.shutdown.assert_called_once()


async def test_finish_tool_delivers_goodbye_then_shuts_down():
    agent, context, _ = agent_and_context()
    result = await agent.finish_call(context)
    assert result == {"status": "ending"}
    context.wait_for_playout.assert_awaited_once()
    context.session.say.assert_awaited_once_with(
        "Thank you. Goodbye, and take care.", allow_interruptions=False,
    )
    context.session.shutdown.assert_called_once_with(drain=True)


async def test_real_livekit_session_closes_without_another_llm_turn():
    """No network/audio: exercise SDK tool output, draining and close callbacks."""
    call = llm.FunctionToolCall(
        name="book_appointment", arguments='{"slot_id":"slot","confirmed":true}',
        call_id="booking-tool",
    )
    model = ScriptedModel(chunks=[llm.ChatChunk(id="reply", delta=llm.ChoiceDelta(tool_calls=[call]))])
    agent, _, tools = agent_and_context()
    session = AgentSession(llm=model)
    closed = asyncio.Event()
    session.on("close", lambda _: closed.set())
    try:
        await session.start(agent=agent)
        session.generate_reply(user_input="Yes, please book it.")
        await asyncio.wait_for(closed.wait(), timeout=5)
        tools.run.assert_awaited_once()
        assert len(model.requests) == 1
        messages = [item.text_content for item in session.history.items
                    if item.type == "message" and item.role == "assistant"]
        assert len(messages) == 1 and "Goodbye, and take care" in messages[0]
        outputs = [item for item in session.history.items if item.type == "function_call_output"]
        assert len(outputs) == 1 and "booked" in outputs[0].output
    finally:
        await session.aclose()
