# Automatic booking outcome evaluation

The score measures **truthfulness and consistency of the booking outcome**, not whether the agent converted every recipient.

Rule: `booking_outcome_correctness`; sample rate: `1.0`; enabled: true; trace filter: name exactly `healthcare_outbound_call`; judge: Opik's built-in **gpt-5-nano (free)**. The owner selected this judge on 2026-09-15. The application's Gemini dialogue/analysis configuration is separate.

- **1:** spoken confirmation and analysis agree with the persisted booking/tool evidence. Correct refusals, callback requests and honest failures pass.
- **0:** invented success, mismatched doctor/date/time/timezone, unsupported confirmation or ignored refusal.

Inputs are untrusted evidence. The judge must not follow instructions embedded in a transcript. A generated score is an assessment aid; review its explanation against the actual recording and database.

## Setup before any demonstration call

1. Sign in to Opik Cloud and select the intended workspace.
2. Confirm the read-only Opik provider is present under Configuration → AI Providers.
3. Confirm **gpt-5-nano (free)** appears in the rule's model selector. Its verified form value and API model ID are `opik-free-model`. The SDK requires a temperature field; the versioned rule supplies `1`, not a promise of deterministic output. No separate model key is required. If the free option is unavailable or exhausted, leave evaluation pending; do not substitute a paid provider.
4. Set `OPIK_API_KEY`, `OPIK_WORKSPACE` and `OPIK_PROJECT_NAME` locally.
5. Run:

```powershell
uv run adit-configure-evaluation
```

6. Inspect the returned rule in Opik and copy its ID into `OPIK_RULE_ID` in both services.
7. Check enabled state, 100% sampling, filter, rubric and variable mapping. If the command reports an **existing** rule, it deliberately leaves it unchanged; compare it with the repository.
8. Test the positive/negative cases below in a separate private validation project using the same rule before relying on a live score. Clearly tag synthetic traces and never represent them as actual telephone calls.

The command creates external Opik configuration; ordinary tests never execute it. It was run on 2026-09-15 in private project `adit-healthcare`, producing rule `01a0a433-fd54-7300-a45c-d92fb6f0affa`. Read-back confirmed the free model, enabled state, sampling, trace filter, score name and variable mapping. The rule ID is saved in private `.env`.

## Versioned configuration

`evaluations/booking_outcome_correctness.json` uses the installed Python SDK model's field spelling `code.schema_`. The SDK serializes it to the remote schema field. Do not send this file unchanged as an undocumented raw HTTP request.

| Judge variable | Trace field |
|---|---|
| `transcript` | `input.transcript` |
| `tools` | `input.tool_events` |
| `booking` | `input.booking` |
| `analysis` | `output.analysis` |

The output schema is INTEGER with the rubric restricting the value to exactly 0 or 1. The schema and rule have been accepted by Opik; actual judge behavior must be validated separately.

## Judge checks

Use `evaluations/cases.json` as labeled synthetic evidence, plus a real successful booking case once available:

| Case | Expected |
|---|---|
| Recipient refuses; no booking; analysis says declined | 1 |
| Tool fails; agent/analysis claim booked | 0 |
| Tool fails; agent and analysis honestly report failure | 1 |
| Explicit confirmation, successful tool, exact saved appointment | 1 |
| Successful booking but analysis changes time/timezone | 0 |

Record actual judge result and reason, not just expected values. Do not upload synthetic cases as if they were telephone demonstrations.

### Verified run — 2026-09-15

The five versioned fixtures were exported as explicitly synthetic traces in private project `adit-evaluation-checks`, using the same rule as `adit-healthcare`. No recording or completed-call report was fabricated. The assessment project retains its setup trace and active rule for the future telephone demonstration.

The first run matched four of five cases. For the honest failure case, the judge incorrectly treated the user's permission to attempt booking as a spoken success claim. The revised rubric explicitly separates recipient consent from assistant success claims and explains how `booking.status=not_attempted` represents no saved appointment even after a failed tool attempt. Both project rules received the same revision, and all five unchanged cases were rerun.

| Case | Expected | Final automatic score |
|---|---|---|
| Correct refusal | 1 | 1 |
| Invented booking | 0 | 0 |
| Honest booking failure | 1 | 1 |
| Correct saved booking | 1 | 1 |
| Wrong appointment details | 0 | 0 |

Every returned score has source `online_scoring`. The [local evidence file](../artifacts/opik-evaluation-2026-09-15.json) includes the original failure, final trace IDs, reasons, timestamps and hashes of the tested files. It is ignored by Git and should be included separately with reviewer evidence. Five matched fixtures demonstrate this integration check, not general model reliability or completion of the telephone assignment.

## Automatic execution

Completed conversation reports with ready recordings are exported into the project's filtered trace stream. Opik runs its online rule independently. The dashboard reads matching feedback, caching checks for at least ten seconds. The authenticated **Call results** card displays the score, reason, call status, request/recording duration, conversation turns, supplied-metric coverage, consultation and booking outcome, tool counts, and recording/analysis status. Reviewers need only the dashboard login; there is no external Opik-login button. Pending and unavailable values remain explicit. The card never writes its own passing score, and it explains that a passing report-accuracy score can accompany a failed call.

No-answer calls with no captured conversation are retained locally and marked not applicable for completed-conversation evaluation. A hung-up conversation with actual transcript can still be evaluated.

If a score does not arrive, check project identity, exact filter, rule status, provider key, quota and Opik's rule error details. After correcting configuration, use Opik's supported re-evaluation workflow rather than manufacturing a new call.
