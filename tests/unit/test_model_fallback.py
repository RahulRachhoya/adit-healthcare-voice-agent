import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
from livekit.agents import APIConnectionError, APIConnectOptions, APIStatusError, llm
from pydantic import SecretStr

from adit_voice_agent.agent.models import VoiceFallback
from adit_voice_agent.services.post_call import PostCallAnalyzer
from tests.unit.test_analysis import analysis


class ScriptedModel(llm.LLM):
    """Exercise the installed LiveKit fallback with controlled provider streams."""

    def __init__(self, *, failure=None, chunks=()):
        super().__init__()
        self.failure, self.chunks = failure, chunks
        self.requests = []
        self.closed = False

    def chat(self, *, chat_ctx, tools=None, conn_options=None, **kwargs):
        self.requests.append((chat_ctx, tools, kwargs))
        return ScriptedStream(
            self, chat_ctx=chat_ctx, tools=tools or [], conn_options=conn_options,
        )

    async def aclose(self):
        self.closed = True


class ScriptedStream(llm.LLMStream):
    async def _run(self):
        for chunk in self._llm.chunks:
            self._event_ch.send_nowait(chunk)
        if self._llm.failure:
            raise self._llm.failure


async def collect(model, context, tools=None):
    async with model.chat(
        chat_ctx=context, tools=tools, conn_options=APIConnectOptions(max_retry=0),
    ) as stream:
        return [chunk async for chunk in stream]


@pytest.mark.parametrize("failure", [
    APIStatusError("quota", status_code=429),
    APIStatusError("upstream unavailable", status_code=503),
    TimeoutError(),
])
async def test_failover_keeps_context_and_tool_calls(failure):
    tool = llm.FunctionToolCall(name="get_available_slots", arguments="{}", call_id="slot-check")
    chunk = llm.ChatChunk(id="reply", delta=llm.ChoiceDelta(tool_calls=[tool]))
    primary = ScriptedModel(failure=failure)
    backup = ScriptedModel(chunks=[chunk])
    chain = VoiceFallback([primary, backup])
    context = llm.ChatContext()
    context.add_message(role="user", content="Please check appointment times.")
    try:
        result = await collect(chain, context)
        assert result[0].delta.tool_calls[0].call_id == "slot-check"
        assert backup.requests[0][0] is context
    finally:
        await chain.aclose()
    assert primary.closed and backup.closed


async def test_partial_tool_response_is_not_replayed():
    tool = llm.FunctionToolCall(name="book_appointment", arguments="{}", call_id="one-booking")
    primary = ScriptedModel(
        chunks=[llm.ChatChunk(id="reply", delta=llm.ChoiceDelta(tool_calls=[tool]))],
        failure=APIConnectionError("connection lost"),
    )
    backup = ScriptedModel()
    chain = VoiceFallback([primary, backup])
    try:
        with pytest.raises(APIConnectionError):
            await collect(chain, llm.ChatContext())
        assert backup.requests == []
    finally:
        await chain.aclose()


async def test_all_providers_unavailable_remains_a_failure():
    chain = VoiceFallback([
        ScriptedModel(failure=APIStatusError("quota", status_code=429)),
        ScriptedModel(failure=APIStatusError("quota", status_code=429)),
    ])
    try:
        with pytest.raises(APIConnectionError):
            await collect(chain, llm.ChatContext())
    finally:
        await chain.aclose()


async def test_analysis_falls_back_through_real_http_contract(monkeypatch, settings):
    settings.groq_api_key = SecretStr("synthetic-groq-key")
    analyzer = PostCallAnalyzer(settings)
    analyzer._gemini = AsyncMock(side_effect=TimeoutError())
    expected = analysis()
    requests = []

    def respond(request):
        requests.append(request)
        assert request.url.host == "api.groq.com"
        assert request.headers["authorization"] == "Bearer synthetic-groq-key"
        return httpx.Response(200, json={"choices": [{"message": {"content": expected.model_dump_json()}}]})

    client_type = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client_type(
        transport=httpx.MockTransport(respond), **kwargs,
    ))
    result = await analyzer.analyze({"transcript": [], "booking": {"status": "not_attempted"}})
    assert result == expected and len(requests) == 1
    assert analyzer.model_used == "groq/" + settings.groq_model


async def test_analysis_without_backup_key_reports_primary_failure(settings):
    analyzer = PostCallAnalyzer(settings)
    analyzer._gemini = AsyncMock(side_effect=TimeoutError())
    analyzer._groq = AsyncMock()
    with pytest.raises(TimeoutError):
        await analyzer.analyze({})
    analyzer._groq.assert_not_awaited()


async def test_cancelled_analysis_does_not_start_another_provider(settings):
    settings.groq_api_key = SecretStr("synthetic")
    analyzer = PostCallAnalyzer(settings)
    analyzer._gemini = AsyncMock(side_effect=asyncio.CancelledError())
    analyzer._groq = AsyncMock()
    with pytest.raises(asyncio.CancelledError):
        await analyzer.analyze({})
    analyzer._groq.assert_not_awaited()
