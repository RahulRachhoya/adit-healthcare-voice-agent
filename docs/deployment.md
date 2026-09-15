# Public reviewer deployment

The application needs a web process, a continuously available agent service, and shared PostgreSQL. This guide extends the PDF submission with the owner's requested public reviewer access.

## Hosting decision

Provider documentation checked on September 15, 2026:

| Service | Role / suitability | Free-plan limitation |
|---|---|---|
| GitHub repository | Public source, README, version history | Never commit secrets, real recipient information, or recordings |
| GitHub Actions | Tests, container builds, deployment automation | Hosted jobs have a six-hour execution limit; it is not an application host |
| GitHub Pages | Static sites only | Cannot run FastAPI, PostgreSQL, or the Python voice worker |
| Render Free | Selected dashboard host | Sleeps after 15 minutes without inbound traffic; workspace shares 750 free instance hours/month; filesystem is ephemeral |
| LiveKit Cloud Build | Selected voice-worker host | Includes 1,000 agent session minutes and limited inference/SIP allowances; verify remaining quota |
| Supabase Free | Selected shared PostgreSQL and private recording storage | Storage/database quotas and inactivity pausing apply |
| Railway Free/Trial | Alternative container host | Trial is $5 for up to 30 days, then $1/month free credit; resource usage and trial verification determine usefulness |

Render's free PostgreSQL expires after 30 days, so it is not used here. The existing Supabase project provides the shared database. The existing Vobiz SIP trial remains the telephone provider; hosting credits do not replace telephone credits.

Do not add a card, upgrade, enable automatic top-up, or intentionally consume paid overages for this deployment. Inspect account-specific usage before testing. Other Render services share the same free-hour allowance and are not modified by this project.

## Deployment topology

```mermaid
flowchart LR
  GitHub[Public GitHub repository] --> CI[GitHub Actions checks]
  CI --> Render[Render FastAPI dashboard]
  CI --> Deploy[Automatic agent deploy on main]
  Deploy --> LiveKit[LiveKit Cloud worker]
  Render --> DB[(Supabase PostgreSQL)]
  LiveKit --> DB
  Render --> LiveKit
  LiveKit --> SIP[Vobiz / approved recipient]
  LiveKit --> Storage[Private Supabase recording bucket]
  LiveKit --> Opik[Opik trace and online evaluation]
```

The local workstation is not part of the hosted runtime. Local development uses a different dispatch name and its own Docker PostgreSQL database. See [deployment-evidence.md](deployment-evidence.md) for the actual hosted address, verified checks, and the distinction between local call evidence and hosted infrastructure verification.

## 1. Prepare the database

In Supabase, open **Connect → Direct → Session pooler** and copy the actual project connection details. The session pooler supports IPv4 and prepared statements. Use its port **5432**, not transaction-pooler port 6543.

For SQLAlchemy, the connection string has this shape:

```text
postgresql+psycopg://postgres.PROJECT_REF:ENCODED_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require
```

Use the pooler hostname shown by Supabase; do not guess its cluster index. Percent-encode special password characters. Keep the URL in private configuration. The web service and worker must receive the same URL.

From a configured private deployment environment:

```shell
uv run alembic upgrade head
uv run alembic check
uv run adit-seed
uv run adit-check --database
```

These commands create/migrate the assessment tables and add future synthetic appointment slots. They do not dial. Do not point the destructive PostgreSQL test fixtures at this shared deployment database.

Application tables have row-level security enabled and no anonymous Data API policies. The server connection requires the documented database-owner privileges. Browser JavaScript never receives database or service credentials.

## 2. Deploy the dashboard

Use `render.yaml` as the configuration reference or create its Blueprint. Select the free Docker web service and `Dockerfile.web`.

Set:

| Setting | Value |
|---|---|
| `APP_ENV` | `production` |
| `APP_BASE_URL` | Actual public `https://...onrender.com` address |
| `ALLOWED_HOSTS` | Exact public hostname, without scheme or path |
| `COOKIE_SECURE` | `true` |
| `DATABASE_URL` | Private Supabase session-pooler URL |
| `SESSION_SECRET` | A generated secret, never committed |
| `ADMIN_PASSWORD_HASH` | Hash produced by `uv run adit-password` |
| `LIVEKIT_AGENT_NAME` | `adit-healthcare-cloud` |
| `LIVE_CALLS_ENABLED` / `FREE_TRIAL_VERIFIED` | `false` during deployment checks |

Supply the remaining LiveKit, Gemini, storage, and Opik settings from [configuration.md](configuration.md). `render.yaml` marks private values with `sync: false`; it contains no working credentials. Render provides the `PORT` value consumed by the Docker start command.

The blueprint waits for successful GitHub checks before automatic redeployment. GitHub integration is required for that behavior. A service created from a public repository URL can be deployed manually before an integration is connected.

Database migrations are an explicit operator step. The free service does not depend on a paid pre-deploy command or shell. To apply future migrations, use the same private deployment environment before deploying compatible application code.

## 3. Deploy the agent

Install the official LiveKit CLI. In this repository, `Dockerfile` builds the worker and downloads its required assets without embedding credentials.

Authenticate to the intended LiveKit project:

```shell
lk cloud auth
```

Prepare a private secrets file outside tracked source. Give the agent the shared database URL, public application URL, production configuration, `LIVEKIT_AGENT_NAME=adit-healthcare-cloud`, SIP, Gemini, storage, and Opik settings. LiveKit Cloud injects its own `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`; omit those three from the agent secrets file.

```shell
lk agent create --region ap-south --secrets-file /PRIVATE/PATH/agent.env
```

The CLI creates `livekit.toml`. Commit that deployment-identifier file after creation. Verify the agent is healthy and its dispatch name matches the dashboard. Do not register the local worker with the cloud dispatch name against the local database.

For later updates:

```shell
lk agent deploy
lk agent status
lk agent logs
```

Store runtime secret updates through LiveKit's secret-management command or dashboard. Do not add private `.env` files to the Docker build context.

For Windows workspaces with inaccessible generated folders, deploy from a clean checkout or an export of committed source. LiveKit CLI 2.18.6 traversed a denied local test-cache directory despite `.dockerignore`; deploying a clean source export succeeded. Keep the secrets file outside that export and use its absolute path. If a failed `create` already allocated an agent, use `lk agent list`, then `lk agent config --id EXISTING_AGENT_ID` and `lk agent deploy` to reuse it. Do not create duplicate agents or change unrelated folder permissions.

## 4. GitHub Actions

`checks.yml` runs on pushes and pull requests:

1. Install the locked Python environment.
2. Run Ruff, migrations, migration-drift checks, and automated tests.
3. Build both Docker images without credentials.

Tests use fake voice/model/storage services and a dedicated disposable PostgreSQL service. They never make telephone calls.

After both check jobs pass, `checks.yml` calls the reusable `deploy-agent.yml` automatically for a `push` to `main`. Merging a branch into `main` produces that same push event. Pull requests and other branches run checks only. The pinned checkout deploys the caller's tested commit, rather than checking out a newer branch head. Production runs finish in sequence instead of being cancelled during rollout. Render's `checksPass` setting then deploys the successful main commit.

The agent workflow uses a pinned official LiveKit deployment action and the GitHub environment named `production`. Set these GitHub Actions secrets:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`

Runtime database, model, recording, and Opik credentials remain in LiveKit/Render. The deployment workflow requires an existing committed `livekit.toml`; it does not create accounts or place calls. Normal releases invoke it through the required check jobs. Its optional manual entry point is for operator recovery after checking the same commit; it is not needed for pushes or merges. This repository's `production` environment has the three approved deployment secrets and permits deployments from `main` only. Forks must configure their own environment and deployment identifiers.

## 5. Verify before sharing

- Public HTTPS `/healthz` and `/login` respond.
- Unauthenticated call/API access is rejected.
- Login works with secure cookies and a private operator password.
- The dashboard connects to the shared migrated database.
- The cloud worker is healthy and uses the matching dispatch name.
- Allowed recipients, quota, attempt limit, and recording storage are correct.
- A restart preserves saved records.
- A separately authorized real call demonstrates booking, recording, analysis, and Opik online scoring from the hosted application.

Keep calling disabled until the cloud checks and available trial credit are confirmed. Enabling the configured call gate does not authorize an agent-driven test call. The operator explicitly starts each demonstration call.

## Reviewer expectations and recovery

Render's first page load after sleeping can be slow. An external HTTP monitor can check the public `/healthz` endpoint every five minutes, which should prevent the normal 15-minute idle timeout. For this deployment, use `https://adit-healthcare-dashboard.onrender.com/healthz`, friendly name `Adit assessment dashboard`, the free five-minute interval, and no authentication. UptimeRobot's free monitor uses HEAD; the application supports both GET and HEAD on this endpoint. It returns only application liveness and does not start telephone calls.

Monitoring does not guarantee continuous availability. Render's 750 free instance hours are shared across the workspace; one continuously running service uses 720 hours in a 30-day month or 744 hours in a 31-day month. Other free services can exhaust the remaining allowance. Provider outages, deployments, and quota suspension can still interrupt access. Once dispatched, the conversation runs on LiveKit independently of the web service.

After prolonged inactivity, check whether Supabase needs to be resumed. Refresh synthetic appointment slots before the demonstration. Provider credits and model quotas can run out independently.

The historical local call evidence remains private. A new cloud database starts without that local history unless an explicit data migration is performed. Do not present historical local verification as a successful cloud call.

For failed finalization, run `adit-retry CALL_ID` using the shared cloud configuration. It never redials. An uncertain live dispatch must be reconciled before another call is attempted.

## Official references

- [GitHub Actions limits](https://docs.github.com/en/actions/reference/limits)
- [GitHub Pages scope](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)
- [Render Free](https://render.com/docs/free) and [Blueprint specification](https://render.com/docs/blueprint-spec)
- [LiveKit pricing](https://livekit.io/pricing) and [agent deployment](https://docs.livekit.io/deploy/agents/start/)
- [LiveKit build requirements](https://docs.livekit.io/deploy/agents/builds/) and [deployment automation](https://docs.livekit.io/deploy/agents/managing-deployments/)
- [Supabase connections](https://supabase.com/docs/guides/database/connecting-to-postgres) and [pricing](https://supabase.com/pricing)
- [Railway plans](https://docs.railway.com/reference/pricing/plans) and [trial](https://docs.railway.com/reference/pricing/free-trial)
