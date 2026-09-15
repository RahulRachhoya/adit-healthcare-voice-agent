# External services for the local demonstration

External services provide LiveKit voice transport and recording, telephony, speech/models, private audio storage, and Opik. The application can run locally or use the [public reviewer deployment](deployment.md): Render for FastAPI, LiveKit Cloud for the agent, and Supabase for shared PostgreSQL.

Use [setup.md](setup.md) first. Account registration is covered in [cloud-onboarding.md](cloud-onboarding.md); all configuration fields are listed in [configuration.md](configuration.md).

## 1. Verify telephone eligibility

Before enabling calls, confirm in the actual accounts:

| Component | Required evidence |
|---|---|
| LiveKit | Usable project credentials and available SIP, inference and Egress allocation |
| Telephone provider | Outbound SIP enabled, eligible balance, authorized caller ID and allowed destination |
| Recipient | A number the owner or consenting tester can answer; recorded-demo agreement |
| Gemini | Configured model supports the conversation/tools and structured analysis with available quota |
| Storage | Private bucket accepts an upload and permits authenticated playback |
| Opik | Workspace/project, free judge access and an enabled online evaluation rule |

Free signup alone does not establish a usable telephone route. Keep the existing zero-payment constraint: if a required operation needs payment, record the restriction and stop that operation. No paid upgrade or automatic top-up is authorized.

## 2. Connect LiveKit and the SIP provider

1. Enter the LiveKit project WebSocket URL, API key and secret privately in `.env`.
2. Complete the telephone provider's account, caller-ID and destination verification.
3. Create its outbound SIP trunk with the provider's endpoint and authentication.
4. Create the corresponding outbound trunk in LiveKit using the authorized caller ID and matching credentials.
5. Set the returned LiveKit trunk ID as `LIVEKIT_SIP_TRUNK_ID`.
6. Verify any regional media/routing restrictions for the actual caller ID and destination; set `LIVEKIT_DESTINATION_COUNTRY` if needed.
7. Put the consenting recipient's exact E.164 number in `ALLOWED_PHONE_NUMBERS`.

Vobiz is now the verified provider. Its account displayed completed identity
verification, ₹25 trial credit and an active trial caller ID. The owner created
the SIP credential; `adit-assessment` was created in Vobiz and its address,
credentials and caller ID were configured in LiveKit. Set the trunk's
`destination_country` and `LIVEKIT_DESTINATION_COUNTRY` to `IN` for this India
route. The real call completed and used ₹0.76 of trial credit.

The application uses LiveKit's trunk ID and has no provider-specific SDK
dependency. Earlier Plivo and Twilio routes were blocked by business KYC or a
funded-upgrade requirement; they are not needed for the verified Vobiz route.

Provider setup and trial references, checked September 15, 2026:

- `https://docs.livekit.io/telephony/start/providers/twilio/`
- `https://www.twilio.com/docs/sip-trunking`
- `https://www.twilio.com/docs/api/sip-trunking/key-concepts`

The public SIP-trial documentation did not establish eligibility for this new Twilio account. Its actual console upgrade gate is authoritative. The 75 free Programmable Voice minutes do not unlock the required SIP integration; no upgrade, purchase or real call was made.

The [actual call evidence](call-evidence.md) includes the saved booking,
recording, completed analysis and automatic Opik score.

See [telephone trial alternatives](telephony-alternatives.md) for the September 15
research on the other providers and the subsequent verified Vobiz account.

## 3. Configure private recording storage

1. Create a private Supabase Storage bucket, for example `call-recordings`.
2. Copy its project URL, server-side Storage credential, exact S3 endpoint, region, access key and secret into the corresponding `.env` fields.
3. Keep `DATABASE_URL` pointing at the local PostgreSQL service. This setup does not use the Supabase database.
4. Verify that a small test object can be uploaded and read through an authenticated signed URL.
5. Keep the bucket private. Neither browser code nor Opik receives the storage credentials.

LiveKit Egress writes an audio-only OGG object at `calls/<call_id>/conversation.ogg`. After Egress reports a nonempty completed file, the application stores the endpoint, bucket and object key in the call report. The local results page obtains a fresh temporary playback URL.

This storage path has been verified with a 16.22-second synthetic LiveKit recording. Completion handles both `file_results` and the singular `file` response observed from LiveKit Cloud. The private signed URL returned the recording, while the unauthenticated public URL was denied. This proves recording integration, not a telephone conversation.

## 4. Configure models and online evaluation

Set `GOOGLE_API_KEY`, `GEMINI_MODEL`, `GEMINI_ANALYSIS_MODEL` and a supported
`TTS_VOICE`. Voice uses `gemini-3.6-flash`; actual-call analysis succeeded with
`gemini-3.5-flash-lite` after 3.6 Flash returned availability/rate-limit errors.
An empty analysis-model setting falls back to the voice model. The existing
STT/TTS settings use LiveKit Inference.

The verified model is `gemini-3.6-flash`. Google rejected the originally planned 2.5 Flash model for this key and recommended that replacement. Actual Docker checks passed for tool selection and structured analysis; a subsequent tool-result reply accurately read the synthetic HbA1c and appointment details and asked for confirmation. Initial HTTP 503 capacity errors show that free-tier availability can vary. Google lists free input/output tokens for this model at `https://ai.google.dev/gemini-api/docs/pricing#gemini-3.6-flash`; no billing upgrade was made.

Set the Opik credentials and workspace/project. Confirm `gpt-5-nano (free)` is available in Opik's model selector, then follow [evaluation.md](evaluation.md). The versioned rule selects Opik's built-in provider and requires no separate judge key:

```powershell
uv run adit-configure-evaluation
```

Inspect the rule and set its returned `OPIK_RULE_ID`. Verify the rubric against its labeled positive and negative examples. A score means correctness of the reported outcome, not whether the person agreed to book.

## 5. Run the assessment

Keep `APP_ENV=development` and the local `APP_BASE_URL` matching the web port. Start PostgreSQL, run migrations/seed, and start the local web app and worker as described in [setup.md](setup.md).

Only after the account checks pass, set `FREE_TRIAL_VERIFIED=true` and `LIVE_CALLS_ENABLED=true`, then restart both application processes. Run:

```powershell
uv run adit-check --database
```

The command checks configuration and database access; it never dials and does not prove the external integrations.

Start one call through the local form. Verify the answered telephone call, supplied metrics, actual booking outcome, playable recording, saved analysis, complete Opik trace and automatic score. Capture the walkthrough using [demo-guide.md](demo-guide.md).
