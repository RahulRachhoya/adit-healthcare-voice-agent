# Required account setup

The assessment uses external voice, telephone, recording and evaluation services. The historical account setup below supports local development. The owner additionally requested public reviewer hosting; follow [deployment.md](deployment.md) for Render, LiveKit Cloud, and the shared Supabase database.

Current setup progress, 2026-09-15:

- LiveKit project `Adit`: a dedicated `adit-assessment-local` key was created with the owner's approval and saved in private `.env`. API authentication and local worker registration succeeded.
- Opik workspace `rahul-rachhoya`, private project `adit-healthcare`: the existing account key was saved locally. A labeled setup trace was written, read back through the running application and opened in Opik.
- Docker PostgreSQL, the dashboard and the registered voice worker are running. The clean locked Python installation passed 93 tests, Ruff and migration checks. Fifteen running-app checks passed. Calls are enabled for the one approved recipient.
- Vobiz is configured and verified with an actual telephone call. The account showed completed KYC, an active trial caller ID and ₹25 credit. The completed call used ₹0.76, saved a simulated booking, produced a playable recording and received an automatic Opik score of 1.0.
- The owner selected Opik's `gpt-5-nano (free)` judge. The versioned online rule is created and enabled; synthetic validation is recorded in [evaluation.md](evaluation.md).
- Cartesia Sonic-3/Jacqueline generated a 7.58-second synthetic sample, and Deepgram Nova-3 transcribed it through LiveKit. The tested voice ID is saved in private `.env` and loaded by the refreshed application containers.
- Supabase project `adit-assessment` is healthy in the free `Adit Assessment` organization, in Tokyo (`ap-northeast-1`). The owner created the S3 key and approved saving it and the existing server key in private `.env`. S3 upload, exact-content private playback, denied public access and an actual 16.22-second synthetic LiveKit recording are verified.
- Plivo signup is complete. Its India account shows ₹1,000 trial credit expiring on September 29, 2026, and access to outbound SIP setup. No outbound trunk exists yet. The phone-number page requires business KYC before obtaining an India number; a usable caller ID and an eligible free calling route are not verified.
- The owner created a Twilio account after the Google signup error. Onboarding selected Voice, Conversational AI, coding and the 30-day free trial. The dashboard shows 75 free Programmable Voice minutes, but opening Elastic SIP Trunking requires an upgrade with added funds. No funds were added, trunk created, number purchased or call placed.
- The owner's Gemini key is saved privately and loaded by both application containers. `gemini-2.5-flash` was rejected for this key; the provider-recommended `gemini-3.6-flash` passed streaming/tool selection, synthetic metric/slot reporting and structured post-call analysis. Initial capacity errors are preserved in the verification artifacts. Replace any key shared in chat before final use.
- The real call's analysis succeeded with `gemini-3.5-flash-lite` after 3.6 Flash capacity/rate-limit failures. `GEMINI_ANALYSIS_MODEL` selects it separately from the voice model.

See [dated verification evidence](testing.md). API authentication is not proof of a working telephone route or completed assessment.

## Accounts needed

| Service | Purpose | Information used by the application |
|---|---|---|
| LiveKit | Voice sessions, outbound SIP connection, speech inference and Egress | Project URL, API key/secret, outbound trunk ID and supported voice |
| Eligible SIP provider | Connect the call to a real telephone | Provider endpoint/authentication and authorized caller ID, configured in LiveKit |
| Google AI Studio / Gemini | Conversation and post-call analysis | API key and supported model |
| Supabase Storage | Store the private call recording | Project URL, server-side Storage credential and S3 settings |
| Opik | Trace and automatic online evaluation | Workspace/project, API key and the built-in free judge |

The PostgreSQL database runs in local Docker. A Render account and hosted database are unnecessary.

## LiveKit

Continue with the existing project instead of creating another one. Verify usable credentials, available SIP/inference/Egress allocation, expiry and any route-specific region restrictions. Put the credentials in `.env`; keep them out of chat and source.

## Telephone provider

Use the verified Vobiz connection described in [external services](external-services.md).
The paragraphs below preserve the reasons the earlier providers were not used.

Neither Twilio nor Plivo is a PDF requirement. Twilio was selected from its public SIP-trial documentation, but the actual new account does not provide the required free access. Opening **Communications → Elastic SIP Trunking → Trunks** displays an account-upgrade dialog that requires adding funds.

The account's 75 free Programmable Voice minutes do not establish access to Elastic SIP Trunking. This was an account restriction, not a missing API key. No upgrade was made; Vobiz provided the verified alternative.

Plivo remains unconfigured because the account's India phone-number page requires business KYC that the owner cannot currently complete. Its account and trial credit do not prove telephone access.

After signup, verify:

1. Outbound SIP access.
2. Available trial credit and expiry.
3. Authorized caller ID or usable voice number covered by the allowed credit.
4. Supported destination country and any required recipient verification.
5. No mandatory payment or automatic top-up.

A trial advertisement does not establish those account-specific permissions. The account owner completes identity checks and accepts provider terms. Do not invent a company/country or purchase access.

## Private configuration

The existing `.env` contains local login/database settings and the verified LiveKit and Opik credentials. Fill the remaining fields locally; do not overwrite that file with a fresh example. Both Docker containers load it with `--env-file`, overriding only the database host for the Docker network. Keep values unquoted for Docker compatibility.

- Keep `LIVE_CALLS_ENABLED=false` and `FREE_TRIAL_VERIFIED=false` during setup.
- Use [configuration.md](configuration.md) for the exact field names.
- The example phone number is fictional and must not be used as a test destination.
- The selected Opik judge uses the workspace's built-in free provider; it does not require a separate OpenAI or Gemini key. `GOOGLE_API_KEY` is still needed for the voice agent and post-call analysis.

## Connection order

1. Verify LiveKit and telephone-provider eligibility.
2. Configure the matching SIP trunks and consenting destination.
3. Configure private recording storage and check model access.
4. Configure Opik's online rule and validate its rubric.
5. Start the local application and worker.
6. Enable the bounded demonstration call only after the account checks pass.
7. Verify the recording, outcome, analysis, trace and automatic evaluation.

Follow [external-services.md](external-services.md) for the technical setup and [demo-guide.md](demo-guide.md) for the required evidence.
