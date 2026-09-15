# Hosted deployment evidence

Verified on **September 15, 2026 (UTC)**. These checks establish the hosted infrastructure and authentication. The real telephone recording documented in [call-evidence.md](call-evidence.md) came from the local deployment; no telephone call was placed during cloud deployment.

## Reviewer entry points

- [Hosted dashboard](https://adit-healthcare-dashboard.onrender.com)
- [Public source repository](https://github.com/RahulRachhoya/adit-healthcare-voice-agent)
- [Automated checks](https://github.com/RahulRachhoya/adit-healthcare-voice-agent/actions/workflows/checks.yml)
- [Manual agent deployment workflow](https://github.com/RahulRachhoya/adit-healthcare-voice-agent/actions/workflows/deploy-agent.yml)
- [Reviewer walkthrough](demo-guide.md)

The login is private. Telephone calls require an explicitly submitted form, recipient consent, and a configured allowed destination. Opening the website does not place a call.

## Verified deployment

| Component | Observed result |
|---|---|
| Render dashboard | Free Docker service in Singapore; deployment succeeded |
| Public HTTPS | `/healthz` and `/login` returned HTTP 200 |
| Authentication | Valid login returned HTTP 303; authenticated dashboard and call API returned HTTP 200 |
| Access protection | Call API returned HTTP 401 before login and after logout |
| Session cookie | `Secure`, `HttpOnly`, `SameSite=Strict`, one-hour lifetime |
| Shared database | Supabase PostgreSQL session pooler; client TLS verified |
| Database schema | Initial revision `0003`; revision `0004` subsequently added durable session-failure reasons, with migration and drift checks passed |
| Initial cloud data | Three synthetic appointment slots; zero calls and bookings |
| Voice worker | LiveKit Cloud agent `CA_KoZoY2W4BTpV`, region `ap-south`, status `Running` |
| Dispatch identity | `adit-healthcare-cloud`; separate from the local worker |
| Integration configuration | LiveKit, models, recording storage, and Opik settings present |
| Repository checks | Initial public commit `c9a7df1` passed lint, migrations, tests, and both clean Linux container builds |
| Credential handling | Runtime credentials saved in private host settings; GitHub deployment credentials saved in the `production` environment |

The initial GitHub checks are recorded in [run 35009225565](https://github.com/RahulRachhoya/adit-healthcare-voice-agent/actions/runs/35009225565). Workflow pages above show subsequent runs and their exact source commits.

The shared database starts fresh. Historical local calls, private reports, and audio were not copied into the public repository or presented as new hosted evidence.

## Subsequent hosted-call failure

The owner's hosted test reached the recipient and captured the greeting and spoken consent, but the conversation model returned HTTP 429 after exhausting the `gemini-3.6-flash` free daily limit of 20 requests. The recording and analysis completed; no appointment was offered or booked. Successful post-call processing did not make the conversation successful.

The repair selects `gemini-3.5-flash-lite`, checks model capacity before dialing, handles unrecoverable session errors with a spoken failure notice, and stores `session_error` separately from processing errors. Flash-Lite passed a real text-only response and appointment-slot tool check. No replacement telephone call was placed during this repair.

## Remaining live verification

A separately authorized call from the hosted dashboard must still confirm the full hosted path: recipient answers, agent discusses submitted metrics, simulated appointment result is saved, recording plays, analysis completes, and Opik online scoring appears. Configuration presence and worker registration alone do not prove that telephone path.

No paid plan, payment, automatic top-up, or telephone call was initiated during deployment. Free hosting, model, recording, and telephone allowances are separate and must be checked before a demonstration.

Render may sleep between reviews. Open the site ahead of the demonstration and follow the [deployment runbook](deployment.md) for quota checks, refreshed appointment slots, redeployment, and recovery.
