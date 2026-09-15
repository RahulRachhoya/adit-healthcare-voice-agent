# Model fallback and free-plan research

Verified **September 15, 2026 (UTC)**. Account limits can change; these are not guaranteed credits or an uptime promise.

## Selected backup

Keep Gemini Flash-Lite as the primary conversation and analysis model. Use **Groq's `openai/gpt-oss-120b`** as the independent backup. This is Groq-hosted inference, paid for or limited by the Groq account; it does not use an OpenAI account or API key.

Groq's public free-plan table currently lists:

| Model | Requests/minute | Requests/day | Tokens/minute | Tokens/day |
|---|---:|---:|---:|---:|
| `openai/gpt-oss-120b` | 30 | 1,000 | 8,000 | 200,000 |
| `openai/gpt-oss-20b` | 30 | 1,000 | 8,000 | 200,000 |

These are API requests, not telephone calls. Each conversation can require several requests and repeatedly sends context. Any request or token limit can be exhausted first. Groq describes limits at organization level and directs users to their own Limits page for exact allowances. No paid upgrade or automatic top-up is required by this integration.

The 120B model supports function calling and low reasoning effort, and its structured output mode accepts the application's analysis schema. A real SDK streaming request, tool-calling turn, and validated structured-analysis request succeeded with the configured account. Public free-plan allowances are documented above; the console's billing page requires a separate sign-in, so the account's exact limits were not independently read there.

## Failure behavior

- `agent/models.py` configures the provider clients and uses LiveKit's `FallbackAdapter`.
- A quota response, unavailable provider, connection error or request timeout can switch the current generation to Groq before output has been emitted. Each provider attempt has a five-second timeout and no foreground retries.
- The same conversation context and tool definitions go to the backup. Appointment writes remain transactionally persisted and idempotent.
- A partially emitted response or tool call is **not replayed**. If a connection fails after output has started, the existing error handler closes the call with a bounded technical-failure notice. This prevents duplicate speech or booking execution.
- A model-capacity check runs before dialing, with a twelve-second total deadline. Both providers unavailable means the call fails without dialing.
- LiveKit may probe a failed provider in the background for recovery. Those probes also consume its quota.
- Post-call analysis tries Gemini, then Groq when the primary request or JSON parsing fails. Each request is bounded; cancellation does not trigger fallback. The same schema and authoritative-booking validation apply to either model. The exported analysis metadata identifies the model that actually produced the result.
- If both analysis providers fail, saved evidence remains available for `adit-retry`; it never redials.
- This is an LLM fallback. Telephone, speech recognition, speech synthesis, recording and Opik retain their own independent service requirements.

## Configuration

Save `GROQ_API_KEY` privately in local `.env` and the existing Render/LiveKit runtime settings. Set `GROQ_MODEL=openai/gpt-oss-120b`. These values do not belong in GitHub source or Docker build arguments. The dashboard readiness response exposes whether the backup is configured, never its key.

If the key is absent, Gemini remains the only configured model. No free fallback is claimed solely because the integration code exists.

## Verification

The automated suite covers quota and server errors, timeout failover, preserved context/tool calls, all-provider failure, partial-tool replay prevention, provider cleanup, analysis fallback, missing credentials and cancellation. Tests do not contact providers or dial.

A separate, real **text-only** check forced the primary to fail with a synthetic 429. Groq executed `get_available_slots` and returned the supplied metric and synthetic appointment details in 1.58 seconds for that check. A second forced-primary-failure check produced a valid `not_attempted` analysis through Groq without inventing a booking. These checks created no room, audio recording or telephone call, and are not telephone latency benchmarks.

## Primary sources

- [Groq rate limits](https://console.groq.com/docs/rate-limits)
- [Groq GPT-OSS 120B capabilities](https://console.groq.com/docs/model/openai/gpt-oss-120b)
- [Groq structured outputs and their streaming/tool limitations](https://console.groq.com/docs/structured-outputs)
- [LiveKit fallback implementation](https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/llm/fallback_adapter.py) — implementation also inspected in the installed, locked SDK version `1.8.1`.

Voice responses use the streaming chat/tool API. Post-call analysis uses the non-streaming structured-output API; Groq's structured-output mode is not combined with streaming or tool calls.
