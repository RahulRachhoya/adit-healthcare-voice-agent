# Reviewer demonstration

## Before recording the walkthrough

Complete the external-service preflight and live tests. Start local PostgreSQL, the web app and voice worker, seed fresh slots, confirm free balance, and arrange one consenting recipient. Use synthetic medical values. Hide account billing details, credentials and full recipient numbers from the recording.

The [September 15 call](call-evidence.md) has verified telephone audio, a saved
booking, analysis and a real Opik online score. Use that existing evidence for
review without redialing. The sequence below is the script for a separate
reviewer walkthrough. It may be presented live or recorded; the PDF does not require a narrated video. For public review, first complete [deployment verification](deployment.md) and provide login credentials privately. Historical local evidence must remain labeled as local evidence.

## Suggested walkthrough

1. **Explain the task.** “This is an outbound LiveKit healthcare demonstration. It relays supplied values and attempts a simulated appointment.”
2. **Show architecture briefly.** Web and voice worker run independently and share PostgreSQL; recording storage is private; Opik is a standalone adapter.
3. **Sign in.** Show the local input/results page and service readiness. Explain that readiness checks configuration; the live call supplies actual proof.
4. **Enter synthetic context.** Name, allowed recipient, patient timezone, metric/value/unit/date, and recorded-demo consent.
5. **Start one real call.** Show the call ID. The recipient answers a telephone, confirms identity and agrees to continue.
6. **Discuss metrics.** Agent reads supplied data without making a diagnosis or inventing values.
7. **Attempt scheduling.** Fetch slots, choose one, repeat date/time/timezone, explicitly confirm “yes,” and run the tool.
8. **Show the saved result.** Appointment ID, tool arguments/result and matching confirmation. Explain that a successful database booking is authoritative.
9. **End and inspect.** Wait for analysis/recording/export; show incomplete states honestly if a dependency is delayed.
10. **Play the real recording.** Use the authenticated playback control and verify audible recipient plus agent.
11. **Open Opik.** Show the real root trace, variables, full transcript, tools, private playback reference, analysis and child spans.
12. **Show automatic scoring.** Display the active online rule, its mapping and the actual score/reason on this trace. Distinguish honest refusal from failure to book.
13. **Explain reuse and checks.** Show the single Opik module, test result and limitations.

A three-minute voice call may be surrounded by a longer narrated walkthrough. Do not substitute a browser microphone conversation, JSON fixture or fabricated screenshot for the actual telephone/Opik evidence.

## Reviewer evidence record

Record locally under ignored `artifacts/`:

```text
Date/time:
Source revision or archive identifier:
Local application URL:
LiveKit project / worker dispatch name:
Call ID / room / dispatch:
Telephone ringing and answer observed:
Saved booking ID or honest non-booked outcome:
Recording object identity and playback verified:
Opik trace ID / link:
Online rule ID / score / reason:
Known limitations:
Walkthrough recording path:
```

Share operator access privately. Do not place password hashes, API keys or full phone numbers in the README. Before submission, update `requirements.md` with links to actual proof and replace pending checks only after they pass.
