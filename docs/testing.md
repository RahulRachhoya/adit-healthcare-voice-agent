# Verification and testing

## Actual Vobiz call, full report and clean installation — 2026-09-15

- Created the Vobiz outbound trunk and corresponding LiveKit trunk after the
  owner supplied credentials privately. The account displayed completed KYC,
  an active trial caller ID and ₹25 credit. India routing was configured.
- One real consenting call completed, discussed the supplied synthetic metrics
  and saved a simulated appointment. Vobiz recorded the completed call and
  charged ₹0.76 of trial credit, leaving ₹24.24. No payment or redial occurred.
- The actual OGG recording returned HTTP 200 and decoded to **133.56 seconds**,
  **1,847,976 bytes**. The authenticated recording API also returned playable
  OGG data.
- Gemini 3.6 Flash encountered rate-limit errors during conversation and
  availability errors during analysis. The same saved call was subsequently
  analyzed by **Gemini 3.5 Flash-Lite**, with booking/evidence validation intact.
  `GEMINI_ANALYSIS_MODEL` now selects analysis independently.
- Opik trace `01a0a60e-c6d1-7830-847c-3f0c8e5fe251` contains the actual variables,
  transcript, all four tool results, permanent audio reference and analysis.
  All required fields and **six child spans** were read back.
- Its online rule returned **1.0**, explicitly labeled `online_scoring`.
  Finalization is complete. The score was not written by the application.
- Regression tests first reproduced rejection of natural confirmation and
  unavailable playback during an analysis outage. The fixes normalize
  confirmation punctuation/phrasing and complete recording before analysis.
  Negation, uncertainty and stale consent remain rejected.
- A new isolated environment at `.cache/clean-vobiz-env` was installed from the
  unchanged lockfile. The offline attempt correctly reported missing cached
  wheels; the online install then completed. In that clean environment:
  **93 tests passed**, including PostgreSQL cases; **Ruff passed**;
  **`adit-check --database` passed**; **`alembic check` found no new operations**.
  Two third-party test-client deprecation warnings remain.
- **15 running-application checks passed**, covering login, authorization,
  CSRF, rendering, playback, persisted real booking and an identical resubmission
  reusing the original call. After the final restart, the API also returned the
  completed analysis, exported trace and automatic score. The attempt counter
  remained **one**.
- Both Docker application images were refreshed from their existing locked
  dependency images and recreated. The database volume was preserved.
  This is distinct from the fresh Python installation; no uncached Docker
  dependency build is claimed.

Evidence and identifiers: [verified call](call-evidence.md). Test output:
`.cache/vobiz-clean-checks.xml`. The two conversation/finalization fixes were
tested after the call; they were not exercised through a second telephone call.

Clean-install commands used from the assessment directory:

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.cache/clean-vobiz-env'
uv sync --frozen --link-mode copy
$env:TEST_DATABASE_URL = 'postgresql+psycopg://adit:local-development-only@127.0.0.1:5432/adit_test'
.\.cache\clean-vobiz-env\Scripts\python.exe -m pytest -q
.\.cache\clean-vobiz-env\Scripts\python.exe -m ruff check .
.\.cache\clean-vobiz-env\Scripts\adit-check.exe --database
.\.cache\clean-vobiz-env\Scripts\alembic.exe check
```

The existing private configuration and local database were reused; the Python
environment and installed packages were new. Earlier dated sections below are
historical snapshots and do not supersede this result.

## Gemini integration and restored local runtime — 2026-09-15

- Saved the owner-supplied Gemini credential only in private `.env` and verified that both recreated application containers load it. A credential shared in chat should be replaced privately before final use; no rotation is claimed.
- The first actual analysis request exposed an SDK schema mismatch: the legacy `response_schema` field rejected `additionalProperties`. The implementation now sends the Pydantic JSON schema through `response_json_schema`, retaining application validation.
- A regression test exercises the real Google SDK serializer through an isolated HTTP transport. It failed before the fix and passes after it; ordinary automated tests do not contact Google.
- Google rejected `gemini-2.5-flash` as unavailable to new users and recommended `gemini-3.6-flash`. The application default and private configuration now use 3.6 Flash. Initial timeout/HTTP 503 results, including a 3.8 Flash availability check, are retained as failures.
- A subsequent check **inside the Docker agent container passed**: the actual LiveKit Google plugin selected `get_available_slots`, and the actual `GeminiAnalyzer` correctly classified synthetic refusal with no invented booking. This initial tool turn took 21.94 seconds.
- A two-turn Gemini 3.6 Flash check using minimal thinking then returned the availability tool in **3.01 seconds** and a reply to its synthetic result in **1.79 seconds**. The reply accurately gave HbA1c 5.8%, its supplied date, Dr. Demo, September 18 at 10:00 Asia/Kolkata, and asked for booking confirmation. No booking was executed. The worker uses the SDK's minimal-thinking default for Gemini 3 Flash.
- Docker PostgreSQL is healthy. Both application images were refreshed with current source using existing images whose `uv.lock` matched the workspace exactly. Fresh dependency builds were cancelled because downloads were very slow; this was an incremental build, not a new clean-install verification.
- The dashboard runs at `http://127.0.0.1:8001`. The refreshed worker registered with LiveKit in India South. Registration identifiers are retained in the local runtime artifact.
- **86 tests passed, zero skipped**, including PostgreSQL concurrency checks, the recording regression and the Google request-format regression. **Ruff passed**. **Nine HTTP checks passed**, including login, authorization, CSRF, disabled calling, static assets and the existing saved synthetic booking after container recreation.
- The persisted telephone-attempt counter remains **zero**. `LIVE_CALLS_ENABLED=false` and `FREE_TRIAL_VERIFIED=false`. SIP eligibility and a consenting destination remain unresolved.

Evidence: [Docker Gemini result](../artifacts/gemini-docker-2026-09-15.json), [tool-result roundtrip](../artifacts/gemini-tool-roundtrip-2026-09-15.json), [initial schema failure](../artifacts/gemini-verification-initial-2026-09-15.json), [earlier model checks](../artifacts/gemini-verification-2026-09-15.json), and [local runtime](../artifacts/local-gemini-setup-2026-09-15.json). Automated results are in `.cache/gemini-checks.xml`. These are synthetic integration checks, not telephone-call evidence.

The entries below preserve earlier verification states; the latest section above supersedes their pending Docker/Gemini status.

## Recording integration and Twilio account check — 2026-09-15

- The owner completed Twilio signup. Onboarding selected Voice, Conversational AI, coding and the 30-day free trial. The account shows **75 free Programmable Voice minutes**.
- Opening **Communications → Elastic SIP Trunking → Trunks** displays “Upgrade your account to keep building” and requires adding funds. This confirms that the current account's free trial does not provide the needed SIP access. No funds were added, trunk created, phone number purchased or telephone call placed.
- The owner created the Supabase S3 key and explicitly approved saving it and the existing server credential in private `.env`, and using the S3 key for LiveKit recording uploads.
- The private bucket accepted a 363,870-byte synthetic WAV upload. Its signed playback URL returned byte-for-byte identical content; the public URL was denied with HTTP 400.
- LiveKit Egress `EG_MtWHmdKkANiG` recorded a synthetic audio track and stored **123,140 bytes of OGG audio**, decoded duration **16.22 seconds**, in private Supabase Storage.
- The first application check reported an empty file because the Cloud response populated `file` while `file_results` was empty. The recording-completion method now accepts both SDK response forms and clears a previous error after recovery.
- The new regression reproduced that failure before the fix. After correction, the same cloud recording was recovered through the application method, downloaded via its signed URL and decoded successfully. No second room, recording or telephone call was needed; the temporary room was deleted.
- **17 focused tests passed**, covering recording response formats, finalization and SDK contracts. Ruff passed for source and tests. Existing Windows temp/cache directories initially denied access; the successful run used a fresh checked path under the workspace's `.cache`. Test result: `.cache/recording-checks.xml`.
- Docker was stopped. Two startup attempts failed with an insufficient-system-resources error during its WSL socket-forwarder startup. No reset or volume deletion was performed. The app images have not been rebuilt or restarted with the recording fix and new credentials; restore Docker first.
- `GOOGLE_API_KEY`, an eligible telephone route and an approved test destination are still missing. `LIVE_CALLS_ENABLED` and `FREE_TRIAL_VERIFIED` remain false.

Evidence: [recording verification](../artifacts/recording-verification-2026-09-15.json), [initial failure](../artifacts/recording-verification-initial-2026-09-15.json), [synthetic OGG recording](../artifacts/recording-synthetic-2026-09-15.ogg) and [Twilio restriction](../artifacts/telephony-eligibility-2026-09-15.json). These are setup checks, not a recipient conversation or a completed assessment call.

## Initial storage and telephone account checks — 2026-09-15

- Supabase project `adit-assessment` (`nduakesowbousnzvgtpr`) is healthy in the free `Adit Assessment` organization, region `ap-northeast-1`.
- Created the `call-recordings` bucket with public access disabled; the resulting bucket list shows zero access policies.
- Read the exact S3 endpoint and region from Storage settings and saved the four non-secret recording settings in private `.env`. The running containers have not been refreshed with these partial settings.
- The S3 access-key creation form is prepared but not submitted. It warns that these keys bypass RLS and grant access to all buckets in the project. Storage credentials and an Egress upload/playback test are still pending.
- Plivo is signed in to its India region. The home page shows ₹1,000 trial credit, expiring on September 29, 2026.
- The outbound trunk list is empty. Its creation form supports LiveKit Cloud, but the authentication credential list is empty.
- The phone-number page requires business KYC before obtaining an India number. No credential, trunk or telephone number was created, and no payment or call was made.
- Gemini remains required by the existing dialogue and analysis code; its API key is not configured. The model provider was not changed.

## Speech service verification — 2026-09-15

- The PDF was re-read and the outbound telephone flow retained. No browser-only voice mode was implemented.
- LiveKit's Build plan and fixed project limits were visible in the account, with a next invoice of `$0.00`. No paid plan, top-up or telephone operation was enabled.
- Cartesia `sonic-3`, voice Jacqueline (`9626c31c-bec5-4cca-baa8-f8ba9e84c8bc`), returned **7.58 seconds of nonempty audio** through LiveKit Inference.
- Deepgram `nova-3` through LiveKit returned the test transcript, including the synthetic-test and no-telephone-call statements. It recognized the project name “Adit” as “audit”; transcription is not assumed word-perfect.
- Initial bulk-input probes timed out with incomplete final transcripts. The verified probe used the audio's actual sample rate, real-time pacing, trailing silence and explicit stream cleanup after the final transcript.
- The tested voice was saved in private `.env` and loaded into both application containers. An initial automatic approval service connection failure prevented the first refresh attempt; after read-only safety checks, the same refresh succeeded on retry.
- Worker `AW_moUzPXyhPtKA` registered in India South at `2026-09-15T09:10:05.235303+00:00`. The worker confirmed the voice is loaded, Opik configuration is preserved, and calls remain disabled.
- The refreshed dashboard passed all **9 HTTP checks**, including disabled calling and its persisted synthetic booking.

Evidence: [speech verification JSON](../artifacts/speech-verification-2026-09-15.json) and [generated WAV sample](../artifacts/tts-synthetic-2026-09-15.wav). These ignored files prove standalone speech-service access, not SIP connectivity, a patient conversation or a cloud call recording.

## Online judge verification — 2026-09-15

- Assessment rule `01a0a433-fd54-7300-a45c-d92fb6f0affa` is enabled in `adit-healthcare` with 100% sampling and the exact `healthcare_outbound_call` name filter.
- The owner chose Opik's built-in `gpt-5-nano (free)` model; API model ID: `opik-free-model`.
- All five fixtures ran automatically in separate private project `adit-evaluation-checks`. Returned scores identify their source as `online_scoring`; no score was supplied by the application.
- Initial result: **4/5**. The judge confused a recipient's consent to attempt booking with an assistant's claim of booking success. The rubric now explicitly distinguishes those concepts and explains the no-saved-appointment status.
- The entire set was rerun: **5/5 matched** — refusal `1`, invented booking `0`, honest failure `1`, correct booking `1`, wrong appointment details `0`.
- Both existing rules were updated to the same final rubric. The production rule's model, enabled state, sampling, filter, messages, mapping and score name were read back.
- Focused Opik tests: **6 passed**. Ruff: **passed**.
- Both application images were rebuilt and their containers recreated with the saved rule ID. All **9 HTTP checks passed again**. The running web container authenticated to LiveKit and retrieved the actual automatic score for the honest-failure fixture.
- The refreshed worker registered in India South as `AW_6LyVQD9wiJpF` at `2026-09-15T08:42:32.233673+00:00`. Calls remain disabled. Runtime evidence: `.cache/container-integration-verification.json`.
- Documentation check: **46 local links, zero missing**. Configured provider credentials were absent from source, examples, evaluation fixtures and documentation.

The ignored [evaluation evidence](../artifacts/opik-evaluation-2026-09-15.json) preserves the initial failure, final trace identifiers, returned reasons, timestamps and rule/fixture hashes. These are actual cloud evaluations of synthetic text; no telephone, audio or Gemini conversation was involved. See [evaluation.md](evaluation.md).

## API integration verification — 2026-09-15

- LiveKit project `Adit` (`p_28lw7548gpt`): authenticated room-list request succeeded, returning zero rooms at the check.
- Local Docker worker `adit-assessment-agent-local` registered as `adit-healthcare` in India South. Worker ID: `AW_HkFC946PwMjS`; registration time: `2026-09-15T08:24:28.786521+00:00`.
- Opik workspace `rahul-rachhoya`: private project `adit-healthcare` was created and its setup trace was written and read back successfully.
- Setup trace ID: `01a0a426-b054-7a7d-a331-d9a19520b89f`; name: `assessment_api_connection_check`; tags: `setup-check`, `synthetic`, `not-a-call`. Its payload explicitly records `telephone_call=false` and `evaluation_performed=false`.
- Both authenticated API checks also passed from the running web container. The application's evaluation-read method correctly returned pending for the unscored setup trace.
- The trace opened successfully in Opik. Its `/traces` link redirected to the current `/logs` view; no adapter link change was necessary.
- All **9 local HTTP checks passed again** after loading the provider credentials, including disabled calling and the existing synthetic booking.
- Credentials are stored only in private `.env`. The prior LiveKit key was retained, and the existing Opik account key was reused.
- At this checkpoint, only the setup trace existed. The online judge was configured and verified in the later record above.

Ignored evidence records: `.cache/livekit-api-verification.json` and `.cache/opik-api-verification.json`. These contain setup results, not credentials. No telephone, speech/model, recording or judge request was made during those API checks. The setup trace is not a completed-call submission artifact.

## Cleanup verification — 2026-09-15

- **80 tests passed, zero skipped**, including PostgreSQL concurrency tests.
- Ruff: **passed**.
- Regression checks cover shared error responses for missing calls and disabled calling, plus malformed/non-object tool results in the shared evidence converter.
- The Opik test double no longer implements `end()`; export succeeds using the complete initial trace payload and read-back.
- `adit-check`, `adit-seed` and `adit-retry` remain available after removing their duplicate script wrappers.
- Both Docker images rebuilt successfully; the local web container now uses the cleaned code.
- All **9 running-container HTTP checks passed**, including persisted synthetic booking data.
- The rebuilt worker imports and loads Silero VAD with networking disabled.
- No database migration or provider-setting changes were needed. Calling is disabled, the attempt count is zero, and no active call was interrupted.
- Two existing third-party test-client deprecation warnings remain.

Machine-readable result: `.cache/cleanup-results.xml`.

## Scope-alignment verification — 2026-09-15

Verified after aligning the implementation and documentation with the PDF:

- **74 tests passed, zero skipped**, including the three real PostgreSQL concurrency tests. Two third-party test-client deprecation warnings remain.
- Ruff: **passed**.
- PostgreSQL migrations and Alembic metadata consistency: **passed**. The setup check confirms the database is connected and migrated.
- Both updated Docker images: **built successfully** from the committed lockfile.
- Rebuilt voice container: worker import and Silero VAD initialization **passed with network disabled**.
- Updated web container at `http://127.0.0.1:8001`: **9 HTTP checks passed**, including the persisted synthetic call/booking and disabled live calling.
- Unresponsive-database check: a local socket accepted a connection but never answered; the configured driver timeout returned control in **6.3 seconds including interpreter startup**.
- Documentation links: **36 checked, zero broken**.
- The post-call regression check confirms the exported recording includes its storage endpoint, bucket and object key without storage credentials.

Machine-readable result: `.cache/assessment-scope-results.xml`.

Public hosting was excluded at this earlier checkpoint. The owner subsequently requested it; [deployment.md](deployment.md) and the current manifests now cover the reviewer deployment.

At this checkpoint, provider access was still unverified; the later API integration record above supersedes that part of the status. No real telephone call or external model/evaluation request was made by these checks. Local tests are not evidence of a completed assessment call.

## Local verification record — 2026-09-14

- Docker Engine **29.7.2**: running; Compose PostgreSQL **16.15** healthy.
- Python 3.12.14 environment installed from the committed `uv.lock`.
- Ruff: **passed**.
- Pytest: **74 passed, zero skipped**, including all three real PostgreSQL concurrency checks. Two third-party deprecation warnings remain.
- Alembic upgrade to **0003**, metadata consistency and synthetic slot seeding: **passed on PostgreSQL** (also previously on SQLite).
- Both `Dockerfile.web` and `Dockerfile.agent`: **built successfully** from the locked dependencies.
- Web container: runs as the non-root `app` user and connects to the shared local PostgreSQL service.
- Voice container: worker imports and bundled Silero VAD initialization **passed with network disabled**. Its legacy download command emitted a non-fatal SDK deprecation notice.
- Running-container HTTP checks: **9 passed**, covering liveness, authentication, session cookie, disabled calling, database history, packaged assets, CSRF, synthetic call/booking detail, and logout.
- Restart/recreation check: web restarted and PostgreSQL container recreated; original synthetic call and complete appointment details **survived unchanged** in the named database volume.
- Access check: RLS enabled on all four application tables; a temporary unprivileged role saw **zero** of the three stored synthetic appointment slots. Role creation/grants were rolled back.
- Browser: Docker-served login rendered; earlier local UI checks covered dashboard layout and adding/removing metric rows.
- No external telephone/model/recording/Opik requests were made; the persisted telephone-attempt counter remains **zero**.

The previous Docker blocker is resolved. These results verified the local database and containers; see the later records above for API authentication, worker registration and synthetic online scoring. Real SIP calls, Egress playback, Gemini responses and real-call Opik scoring remain unverified. The GitHub workflow has not run remotely.

A clearly labeled `LOCAL CHECK - synthetic persistence record` remains in the local database for review. It is not telephone evidence and carries an explicit warning; there is no audio or Opik score for it.

### Current local dashboard

- Origin: `http://127.0.0.1:8001`
- Operator: `operator`
- Generated password: private ignored file `.cache/local-docker-password.txt`
- Container settings: private ignored `.env`, with `DATABASE_URL` overridden to use the Compose host `postgres`.
- Web container: `adit-assessment-web-local`
- Registered voice worker: `adit-assessment-agent-local`
- PostgreSQL: Compose service `postgres`, database `adit`; isolated concurrency-test database `adit_test`.
- Machine-readable test results: `.cache/local-test-results.xml`.

Recheck the running local web service without dialing:

```powershell
uv run python scripts/check_local_http.py --password-file .cache/local-docker-password.txt
```

Optionally supply `--call-id` with the local synthetic persistence record to verify its booking too. The script accepts loopback addresses only, reads credentials privately and checks that live calls are disabled.

To stop the local services without deleting data:

```powershell
docker stop adit-assessment-agent-local adit-assessment-web-local
docker compose stop postgres
```

To resume them:

```powershell
docker compose up -d --wait postgres
docker start adit-assessment-web-local adit-assessment-agent-local
```

Docker reads environment values when a container is created. Restarting an existing container does not load edits to `.env`. To apply changes, stop and remove only the two named application containers, then recreate them:

```powershell
docker stop adit-assessment-agent-local adit-assessment-web-local
docker rm adit-assessment-agent-local adit-assessment-web-local
docker run -d --name adit-assessment-web-local --network assessment_default --env-file .env -e DATABASE_URL=postgresql+psycopg://adit:local-development-only@postgres:5432/adit -p 127.0.0.1:8001:8000 adit-assessment-web:local
docker run -d --name adit-assessment-agent-local --network assessment_default --env-file .env -e DATABASE_URL=postgresql+psycopg://adit:local-development-only@postgres:5432/adit adit-assessment-agent:local
```

The PostgreSQL container and named volume are preserved. Do not run a second host-based `adit-agent dev` worker while the Docker worker is active. Keep `.env` values unquoted: Docker preserves surrounding quotes, unlike Python's dotenv reader.

## Commands

```powershell
uv sync --frozen
uv run ruff check .
uv run alembic upgrade head
uv run alembic check
uv run pytest -q
```

On this Windows workstation, the older pytest temp/cache directories can deny access. Use a fresh workspace temp directory if that occurs:

```powershell
$testTemp = Join-Path '.cache' ('pytest-' + [guid]::NewGuid().ToString('N'))
uv run pytest -q -o cache_dir=.cache/pytest --basetemp $testTemp
```

Keep this temp path under the assessment's `.cache`; pytest manages its contents.

For the real PostgreSQL cases, use a dedicated disposable test database:

```powershell
$env:TEST_DATABASE_URL = 'postgresql+psycopg://adit:local-development-only@127.0.0.1:5432/adit_test'
uv run pytest -q -m postgres
```

Each PostgreSQL test creates and removes a unique `assessment_test_*` schema in that database. Never point `TEST_DATABASE_URL` at production. SQLite tests use temporary databases; ordinary tests replace provider calls and never contact telephone numbers.

## Automated coverage

| Area | Checks |
|---|---|
| Input | E.164 shape, allowlist, units, finite values, dates, timezone, required consent |
| Web | Auth, CSRF, secure-cookie configuration, login throttling, rendering and API errors |
| Admission | Persistent budget, one active call, duplicate request, conflicting key, dispatch timeout reconciliation |
| Booking | Available/past/unavailable slots, repeated tools, latest affirmative turn, refusal and missing confirmation |
| Evidence | Final history, interrupted speech, missing tool result, incomplete evidence blocks finalization |
| Analysis | Saved booking consistency, no invented details, evidence references |
| Finalization | Repeat-safe processing, model outage, pending recording, export retry and unanswered call |
| Opik | Standalone import, required fields, stable IDs, flush/read-back failure, score mapping, typed rule schema |
| SDK | Installed AgentSession/tools, SIP/Egress messages and CLI entrypoints |
| PostgreSQL | Concurrent slot race, duplicate request admission, global single-call admission |

## Explicit live workflow

Live tests require a separate operator action and available free quota. See `tests/e2e/README.md`.

| Scenario | Pass evidence |
|---|---|
| Accepts | Successful tool, saved booking ID, spoken details match, correct analysis |
| Declines | No booking, no pressure to continue, accurately reported outcome |
| Booking fails | No invented confirmation; tool error and analysis agree |
| Hangup | Available transcript/tool evidence preserved; partial outcome clearly represented |
| Unanswered | No fabricated conversation or appointment |
| Dashboard closes/restarts | Worker continues; persisted call accessible on return |
| Complete call | Recording plays; trace fields and automatic score are visible |
| Lost provider/recording/export | Independent failure states; retry does not dial again |

Record actual IDs, date, expected/observed behavior and limitations. A fake provider result is never a live-test result. Review original audio as well as transcripts, because recognition mistakes can affect confirmation.
