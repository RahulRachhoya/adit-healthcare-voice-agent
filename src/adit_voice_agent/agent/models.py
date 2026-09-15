"""Voice model selection; LiveKit owns streaming and tool-safe failover."""

import asyncio

from google.genai import types
from livekit.agents import llm
from livekit.plugins import google, openai

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class VoiceFallback(llm.FallbackAdapter):
    """Also close the provider clients that the SDK adapter does not own."""

    def __init__(self, providers):
        self.providers = providers
        super().__init__(
            providers, attempt_timeout=5, max_retry_per_llm=0,
            retry_on_chunk_sent=False,
        )

    async def aclose(self):
        await super().aclose()
        await asyncio.gather(*(model.aclose() for model in self.providers))


def build_voice_model(settings):
    primary = google.LLM(
        model=settings.gemini_model, api_key=settings.google_api_key.get_secret_value(),
        thinking_config={"thinking_level": "minimal"},
        automatic_function_calling_config=types.AutomaticFunctionCallingConfig(disable=True),
        http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)),
    )
    if not settings.present("groq_api_key"):
        return primary
    backup = openai.LLM(
        model=settings.groq_model, api_key=settings.groq_api_key.get_secret_value(),
        base_url=GROQ_BASE_URL, reasoning_effort="low",
        parallel_tool_calls=False, max_retries=0, max_completion_tokens=1024,
    )
    return VoiceFallback([primary, backup])
