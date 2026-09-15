# Setup

Commands run from the **Assessment** directory. Python 3.12 is required; `uv` selects it from `.python-version`. Commands below use PowerShell. Keep `.env` and provider secrets local.

## 1. Install the locked environment

```powershell
uv sync --frozen
Copy-Item .env.example .env
uv run adit-password
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the prompted password hash and generated session secret into `.env`. Choose your own operator password; it must contain at least 12 characters. Run the copy command only when `.env` does not already contain your configuration.

The repository has no default production password. Shell output from secret generation is for local entry only; do not include it in screenshots, commits or the demo.

## 2. Database

Preferred local integration environment:

```powershell
docker compose up -d postgres
```

Use the development connection declared in `compose.yaml`:

```dotenv
DATABASE_URL=postgresql+psycopg://adit:local-development-only@127.0.0.1:5432/adit
```

Both local web and agent processes must use this same database. Supabase is used only for recording storage in this setup; a hosted database is unnecessary.

```powershell
uv run alembic upgrade head
uv run alembic check
uv run adit-seed
uv run adit-check --database
```

Seeding adds explicitly synthetic future appointments; it does not create calls. Re-running it preserves existing slots. Run it again before a later demonstration so slots are still in the future.

The supplied migration turns on PostgreSQL row-level security with no public policies. The local application uses the database owner created by Compose.

### Local preview without a database service

Set `DATABASE_URL=sqlite:///./.cache/local.db`, create `.cache` if needed, and run the same migrations and seed command. Keep `APP_ENV=development` and `LIVE_CALLS_ENABLED=false`. The code deliberately prohibits live calls with SQLite.

```powershell
New-Item -ItemType Directory -Force .cache
```

## 3. Start the dashboard

```powershell
uv run uvicorn adit_voice_agent.web.app:create_app --factory --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` and sign in with your operator credentials. Missing providers appear as **Needs setup**. That is a valid preview state, not a verified integration.

## 4. Provision external services

Complete [configuration](configuration.md) and [external services](external-services.md):

1. LiveKit project with agent, inference, SIP and Egress access.
2. Vobiz or another compatible outbound SIP trunk, permitted caller ID, destination country and eligible trial balance.
3. Supabase private bucket and S3 credentials.
4. Gemini API access; configure voice and analysis models using the verified settings in `.env.example`.
5. Opik workspace/project with `gpt-5-nano (free)` available; create the online rule.
6. Approved recipient number and recipient's agreement to the recorded demonstration.

Check the account-specific balance, expiry, destination permissions, phone rental and overage behavior. A free signup is insufficient. If payment is required, stop that integration setup and record the blocker. Do not enter payment information or enable auto-top-up to make this assessment work.

## 5. Start the agent locally

```powershell
uv run adit-agent download-files
uv run adit-agent dev
```

Run this in a second terminal using the same `.env`. `dev` connects to LiveKit and may consume service quota. Keep both processes and the database running during the demonstration.

On the configured workstation, `adit-assessment-agent-local` already runs the worker in Docker. Stop that container before starting `dev`, or keep using the containers described in [testing.md](testing.md). Do not start duplicate workers with the same dispatch name.

Only after the preflight succeeds, set `FREE_TRIAL_VERIFIED=true`, `LIVE_CALLS_ENABLED=true`, and the exact `ALLOWED_PHONE_NUMBERS`. Restart both services after configuration changes. The check command never places a call:

```powershell
uv run adit-check --database
```

## 6. First real test

Use synthetic patient values and a real allowlisted consenting recipient. Start one call through the dashboard. Record the call/room IDs and whether it actually rang and was answered. Follow the evidence steps in [demo-guide.md](demo-guide.md).

## Troubleshooting

| Symptom | Action |
|---|---|
| Dashboard refuses to start | Set a session secret of at least 32 characters and a generated Argon2 hash |
| `503` when starting | Inspect readiness, PostgreSQL connection, trial flag and all missing configuration |
| `403` starting call | Check approved destination and CSRF/session |
| Persistent active-call reservation | Open the original call and use End call; verify room termination |
| PostgreSQL unavailable | Check the service/SSL/session-pooler connection; use SQLite only for preview |
| Agent does not answer dispatch | Check worker status, dispatch name and shared database |
| No audio object | Inspect Egress status, private bucket, S3 region/endpoint and credential permissions |
| Finalization pending | Read individual processing states; use `uv run adit-retry CALL_ID` after fixing the dependency |
| Evidence incomplete | Recover real final session history; ordinary retry cannot reconstruct lost speech |
| Opik has no score | Check rule ID, enabled status, exact trace-name filter, model credential and quota |
