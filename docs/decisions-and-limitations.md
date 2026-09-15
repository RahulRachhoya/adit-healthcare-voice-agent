# Decisions and limitations

| Decision | Reason / tradeoff |
|---|---|
| LiveKit Agents + Python 3.12 | Required voice framework with one language for worker, services and dashboard |
| FastAPI/Jinja | Existing small form for patient input and required call evidence |
| PostgreSQL shared by both services | Durable state and transactional booking across separate processes |
| SQLite preview only | Enables offline local review; not live admission or PostgreSQL race verification |
| Separate LiveKit worker | Conversation survives closing the browser; local development and hosted deployment use different dispatch names |
| Simulated appointment store | Meets the assessment tool requirement without a calendar/EHR account |
| Separate Gemini analysis model | Flash-Lite completed analysis after the voice model's capacity/rate-limit failures, using the existing Google account |
| Explicit affirmative confirmation | Conservative English phrase check; ambiguous wording triggers another confirmation question |
| OGG room Egress | Single mixed audio recording uploaded directly to private S3-compatible storage |
| Private recording reference in Opik | Storage endpoint, bucket and key identify the audio; local playback requires the app and login |
| Single-module Opik integration | Reusable dictionary interface with no web/agent/domain dependencies |
| Post-call database lease and stable trace IDs | Operator can retry incomplete processing without redialing |
| Online judge checks correctness | Declines and genuine failures can pass when reported honestly |
| One operator / one call / ten attempts | Bounded demonstration scope and free-credit protection |

## Current verified state

- Vobiz, LiveKit, speech inference, private recording and Opik completed one real telephone workflow. The account's KYC was verified; the call used ₹0.76 of trial credit without payment.
- The real appointment, 133.56-second recording and complete report are saved. Opik automatically scored the actual call 1.0. See [call evidence](call-evidence.md).
- Gemini 3.6 Flash handled voice but encountered quota/capacity errors. Gemini 3.5 Flash-Lite completed the saved call's analysis without redialing and is now separately configurable.
- A fresh locked Python installation passed all 93 tests, Ruff and migration checks. Fifteen running-app checks passed. Docker refreshes reused existing locked dependency images; they are not fresh uncached Docker dependency builds.
- Plivo, Twilio and Sinch were not used. Their earlier account restrictions remain documented in the provider research.

## Deliberate limits

- No diagnosis, treatment recommendation, real calendar, EHR, SMS/email follow-up or actual clinical workflow.
- Only synthetic health information. Demo prompts are not a production medical safety evaluation.
- Trial credits and number rental vary by country/account; no guaranteed free PSTN route or uptime is claimed.
- Call attempt limits are application bounds, not provider spending caps. Provider balances and top-up settings still require verification.
- Maximum SIP connected-call duration is 180 seconds; ringing and post-call processing add wall-clock time.
- No automated redial or background finalization scheduler. An operator invokes the retry command after outages.
- A hard worker crash can leave a reservation and incomplete evidence. End the original room and recover actual session evidence; do not declare completion from partial records.
- Conversational identity, recipient intent and chosen appointment semantics still require real-call evaluation. The booking service checks the latest affirmative response, but does not independently prove the entire preceding spoken slot confirmation.
- `disconnected` is supported as a lifecycle value; a normal SDK close can be recorded as `completed`. Transcript/analysis determines whether the conversation was interrupted or the recipient declined.
- Login throttling is process-local; restarting the web service resets that short-term guard.
- The local web process, voice worker and database must stay running during the demonstration. The computer must remain awake and connected.
- Model access and quota must be rechecked before the real demonstration. Gemini 2.5 Flash was unavailable for this key; 3.6 Flash succeeded after initial timeout/capacity errors. Minimal-thinking tool turns took 3.01 and 1.79 seconds in one synthetic check; these are observations, not a latency guarantee.
- Analysis validates booking facts and reference IDs. It does not deterministically validate every natural-language sentence; the online rubric and reviewer cover that gap.
- Opik/LLM and transcript errors must remain visible. One real completed call and five synthetic judge cases passed; this does not establish general reliability across all conversations.
- The audio link to `127.0.0.1` only opens on the machine running the app. Demonstrate playback locally; the stored endpoint/bucket/key is the permanent audio reference.
- Public reviewer hosting is being prepared using Render Free, LiveKit Cloud Build, and Supabase Free. Sleep, quota, and inactivity limits apply; see [deployment.md](deployment.md).

## Remaining completion checklist

1. Capture the separate narrated screen walkthrough using the verified call and [demo script](demo-guide.md).
2. Replace any credential shared in chat privately before sharing access, then recreate the application containers.
3. Additional live refusal, unanswered and hangup scenarios remain optional manual verification; automated tests cover their application behavior. Do not redial without the recipient's agreement.
