# HTTP API

All `/api/*` endpoints require the operator's signed session cookie. Obtain the session by signing in through the dashboard. Mutations also require the `X-CSRF-Token` value embedded in the authenticated page's meta tag. Login/logout forms use the hidden `csrf` field.

Responses are JSON. Authentication failure returns `401`; CSRF or destination rejection `403`; missing call `404`; conflict `409`; invalid input/key `422`; attempt limit `429`; unavailable setup/provider `503`. Validation errors use FastAPI's `detail` array; service errors use a `detail` string. Public OpenAPI/Swagger routes are disabled.

| Method/path | Contract |
|---|---|
| `GET /healthz`, `HEAD /healthz` | Public liveness. GET returns `{"status":"ok"}`; HEAD returns HTTP 200 with an empty body for uptime monitors. Does not prove provider or database readiness. |
| `GET /api/readiness` | Configuration presence, missing variable names, manual trial attestation and limits; no values/secrets |
| `POST /api/calls` | Header `Idempotency-Key` (1–100 chars), patient body; `202` with persisted call detail |
| `GET /api/calls` | `{"calls":[...]}`; most recent 50 summaries |
| `GET /api/calls/{id}` | Transcript, tool events, booking, evidence/processing states, analysis, trace URL and evaluation |
| `POST /api/calls/{id}/end` | Empty body permitted; terminate room and return updated call detail |
| `GET /api/calls/{id}/recording` | `{"url":"temporary-signed-url","expires_in":300}` when ready; `409` while unavailable |

## Create-call body

```json
{
  "name": "Alex Synthetic",
  "phone": "+12025550123",
  "timezone": "Asia/Kolkata",
  "biomarkers": [
    {"name": "HbA1c", "value": "5.8", "unit": "%", "measured_at": "2026-09-10"}
  ],
  "recipient_consented": true
}
```

This is an illustrative fictional number, **not an approved test destination**. Use a real consenting, trial-permitted number in private configuration. Metric values must be finite, nonnegative numbers with at most four decimal places; units and measurement dates are required; future dates and unknown fields are rejected.

## Idempotency and dispatch

An identical key/body reuses the saved call without another dispatch or attempt increment. Reusing a key for changed input returns `409`. Save the original key when retrying an HTTP request.

The endpoint awaits bounded dispatch acceptance/reconciliation (up to approximately 25 seconds), never the conversation. If dispatch is uncertain, the response may contain `status: "dispatch_unknown"`. Inspect/end that original call before intentionally creating a new attempt.

## Independent states

`status` describes the voice lifecycle: queued, preparing, dialing, active, dispatch_unknown, or a terminal completed/unanswered/failed/cancelled/disconnected value. A completed voice session does **not** mean an appointment was booked.

`booking.status` and its persisted appointment are authoritative. `evidence_complete`, `analysis_status`, `recording.status`, `export_status`, `finalization_status`, and `evaluation.status` report independent processing. A successful booking can coexist with a pending recording or unavailable evaluation.

Details mask the destination except its last four digits. No S3 keys, bucket credentials or raw `.env` data are returned. The recording endpoint issues a temporary URL only to an authenticated operator; possession of that URL grants playback until expiry.
