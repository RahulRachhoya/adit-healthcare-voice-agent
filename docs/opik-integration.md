# Standalone Opik integration

`src/adit_voice_agent/integrations/opik_integration.py` is the only application module that imports Opik. It imports no agent, database, FastAPI or booking code. Copy this file into another project and install the version of `opik` pinned by this repository's lockfile.

## Contract

```python
from opik_integration import OpikIntegration

adapter = OpikIntegration(
    api_key=secret_from_environment,
    workspace=workspace_name,
    project_name="adit-healthcare",
)
reference = adapter.publish_completed_call(report)
evaluation = adapter.get_evaluation(reference["trace_id"])
```

`report` is an ordinary JSON-compatible dictionary with `call_id`, start/end timestamps, call status, metadata, supplied variables, transcript, tool events, authoritative booking, recording and analysis. See `examples/completed_call.synthetic.json` for its shape. That fixture is synthetic and contains no working recording.

`publish_completed_call` requires `recording.status == "ready"` and returns a trace ID, browser URL and pending evaluation status. It raises on incomplete reports, upload timeout or read-back mismatch. The application catches those errors and keeps the original booking intact.

`get_evaluation` returns `{"status":"pending","scores":[]}` until the expected score exists; then it returns matching scores with `status: "completed"`. It does not execute an evaluation or invent a score.

## Field mapping

| Application data | Opik location |
|---|---|
| Call identity, room/dispatch, schema version | Root metadata |
| Supplied patient variables, without phone | `input.variables` |
| Complete final transcript with interruptions | `input.transcript`, conversation span |
| Tool arguments/results | `input.tool_events`, individual tool spans |
| Persisted booking | `input.booking` |
| Private storage endpoint, bucket, object key and local authenticated playback page | `input.recording` |
| Structured post-call analysis | `output.analysis`, analysis span |
| Call lifecycle result | `output.call_status` |

Parent trace name: `healthcare_outbound_call`. Tags: `assessment`, `completed-call`.

The trace contains final evidence and its end time in one root payload, so the online rule does not need to wait for child spans. No redundant `trace.end()` update follows the completed trace write. Trace timing includes finalization; individual conversation/tool/analysis spans preserve their own available timestamps.

## Retry semantics

The adapter derives stable UUIDv7 IDs from call identity/start time plus a span label. Repeated exports address the same trace and span IDs. After flushing, it reads the trace back and compares its persisted analysis before declaring export ready. Synthetic tests verify deterministic identity and failure handling; real cloud upsert behavior still needs a live integration check.

The application persists `trace_id` before export. Retry using:

```powershell
uv run adit-retry CALL_ID
```

No telephone call, new booking or repeat analysis is required when only export failed.

## Recording access

The audio remains in a private Supabase bucket. Opik stores `storage_endpoint`, `bucket` and `object_key` to identify the recording, plus a link to the local password-protected call page. The operator signs in and requests a fresh five-minute audio URL. No credentials or expiring playback tokens are exported.

A loopback page URL is only reachable on the machine running the app. During the walkthrough, show the storage reference in Opik and play the audio in the local app. A reviewer can run the documented application with privately supplied access; the recording reference itself does not grant access. Opik's built-in attachment player is not implemented. Do not describe the trace as containing a binary audio attachment.

## Cloud verification

On 2026-09-15, API authentication and setup-trace write/read succeeded in private project `adit-healthcare`, workspace `rahul-rachhoya`, including from the running web container. The setup trace `01a0a426-b054-7a7d-a331-d9a19520b89f` is named `assessment_api_connection_check`, explicitly tagged `not-a-call`, and has no evaluation score. Its browser link opened successfully. See [the verification record](testing.md).

The same workspace's free online judge subsequently produced the expected scores for five synthetic cases in a separate private project; see [evaluation.md](evaluation.md). Actual `publish_completed_call` export with conversation/audio evidence, cloud retry/upsert behavior and the real-call score remain pending.

Confirm all mapped fields, child spans, correct root ID, playable reference and final score in the real project. Open the generated trace link once; its UI route is SDK-independent and may need updating if Opik changes its frontend. Never call export successful merely because an SDK operation was queued.
