# Demonstration artifacts

This directory holds observed integration/evaluation evidence and the actual
September 15 telephone call. See [the evidence guide](../docs/call-evidence.md).

`vobiz-call-2026-09-15.json` contains the saved call report and automatic score.
`vobiz-call-2026-09-15.ogg` is the actual 133.56-second telephone recording.
`vobiz-opik-2026-09-15.json` verifies all required trace fields and the online
score of 1.0. The companion recording, connection and HTTP-check JSON files
record playback, trial usage and application verification. These are distinct
from the synthetic checks below.

`opik-evaluation-2026-09-15.json` records actual Opik online scores for five **synthetic** cases, their trace IDs, and the initial rubric failure. The final run matched 5/5 expected scores. This proves the judge check, not a telephone call or a complete assessment demonstration.

`speech-verification-2026-09-15.json` and `tts-synthetic-2026-09-15.wav` record a synthetic TTS/STT check through LiveKit. The audio was generated from test text; it is not an Egress recording or a recipient conversation.

`recording-verification-2026-09-15.json` and `recording-synthetic-2026-09-15.ogg` record an actual **synthetic LiveKit Egress** check: a 16.22-second, 123,140-byte OGG uploaded to private Supabase Storage and retrieved through the application's signed playback URL. `recording-verification-initial-2026-09-15.json` preserves the first failure, caused by the code checking `file_results` while Cloud returned the singular `file` field. The corrected code recovered the same recording; no telephone call was placed.

`telephony-eligibility-2026-09-15.json` records the actual Twilio trial account's funded-upgrade gate for Elastic SIP Trunking. It is a blocker record, not telephone-call evidence.

`gemini-docker-2026-09-15.json` records successful Gemini 3.6 Flash tool selection and structured analysis of a synthetic refusal inside the running Docker worker. `gemini-tool-roundtrip-2026-09-15.json` records a successful reply to a synthetic appointment-tool result, including accurate metrics, slot details and a confirmation question. Neither check dialed a phone or saved a booking.

The other `gemini-*.json` files preserve the initial schema rejection, the unavailable 2.5 Flash model and temporary timeout/503 responses. `local-gemini-setup-2026-09-15.json` records container/configuration verification, source hashes, the worker registration, 86 passing tests, nine HTTP checks and zero telephone attempts. Credentials and their hashes are excluded.

Generated contents are ignored by Git. Keep full phone numbers, credentials, raw database exports and audio private. Synthetic fixtures live in `examples/` and `evaluations/`, clearly labeled; they are not telephone evidence.

Suggested local files after verification:

- `verification.md`: date, source revision, real call/room/dispatch, booking outcome, trace/rule IDs and checks.
- `walkthrough.mp4`: complete reviewer demonstration.
- Redacted screenshots of call details, recording playback, trace and automatic score.

Recordings are stored in the private cloud bucket; a local copy is optional. Only share evidence with the intended reviewer and provide dashboard access separately.
