# Verified telephone demonstration — September 15, 2026

One consenting recipient answered an actual outbound Vobiz telephone call.
LiveKit ran the conversation with synthetic patient data, saved a simulated
appointment, recorded the audio, and exported the completed report to Opik.
Opik's enabled online rule automatically returned a score of **1.0**.

## Evidence

| Item | Observed result |
|---|---|
| Call | `932d9cf2-878b-48ad-87c1-337829af0e2f` |
| LiveKit room | `adit-932d9cf2-878b-48ad-87c1-337829af0e2f` |
| Agent dispatch | `AD_uyVcNVxccZQ7` |
| Outbound trunk | `ST_zi5qzsFjP8Xx`, Vobiz, India routing |
| Start | September 15, 2026, 22:43 IST |
| Synthetic values | Blood glucose 110 mg/dL and HbA1c 5.8%, measured September 10 |
| Booking | `09e3f45f-f83a-41b8-af0c-fb494fd30b33` |
| Appointment | Dr. Jordan (demo), September 16, 2026, 11:00 Asia/Kolkata |
| Recording | LiveKit Egress `EG_k8Q4r6EyPzpw`; 133.56 decoded seconds, Opus/OGG, 1,847,976 bytes |
| Analysis | Gemini `gemini-3.5-flash-lite`; validated against the saved booking and evidence IDs |
| Opik trace | `01a0a60e-c6d1-7830-847c-3f0c8e5fe251` |
| Online rule | `booking_outcome_correctness`, `01a0a433-fd54-7300-a45c-d92fb6f0affa` |
| Automatic score | `1.0`, returned with source `online_scoring` |
| Trial usage | ₹0.76 deducted from Vobiz's ₹25 credit; observed balance ₹24.24 |
| Telephone attempts | Exactly one; finalization retries did not redial |

The judge reported that the final analysis, saved appointment, booking tool
result and recipient confirmation agree. This is an actual call score;
the separate five synthetic judge cases remain labeled as synthetic.

## Inspect locally

1. Start the local services and sign in at `http://127.0.0.1:8001`.
2. Open `/calls/932d9cf2-878b-48ad-87c1-337829af0e2f`.
3. Inspect the transcript, failed and successful tool attempts, saved booking,
   analysis and recording. The recording endpoint returned playable OGG data.
4. Open the trace from the call page and inspect its input, output and online
   score. The trace includes the private recording's permanent storage identity
   and the authenticated local playback page.

Opik trace URL:

```text
https://www.comet.com/opik/rahul-rachhoya/projects/01a0a426-dd20-720f-b6a4-f5e278a7c2db/traces?traces=01a0a60e-c6d1-7830-847c-3f0c8e5fe251
```

These files are private, ignored artifacts on the demonstration workstation:

- [Call and saved report](../artifacts/vobiz-call-2026-09-15.json)
- [Actual telephone recording](../artifacts/vobiz-call-2026-09-15.ogg)
- [Recording verification](../artifacts/vobiz-recording-2026-09-15.json)
- [Opik readback and automatic evaluation](../artifacts/vobiz-opik-2026-09-15.json)
- [Provider connection and credit evidence](../artifacts/vobiz-connection-2026-09-15.json)
- [Running application checks](../artifacts/vobiz-http-checks-2026-09-15.json)

## Issues observed and corrected

The first call rejected two confirmation phrases before accepting a final
“Yes.” One rejected phrase was “Yes. You can book the appointment.” The
confirmation check now normalizes punctuation and accepts that explicit
sentence. It still rejects negation, uncertainty and stale confirmation.
The original tool history is preserved.

Gemini 3.6 Flash handled the conversation but encountered rate-limit errors.
Its post-call analysis attempts also returned availability errors. The completed
call was subsequently analyzed successfully with the free Gemini 3.5 Flash-Lite
model. `GEMINI_ANALYSIS_MODEL` now selects that separate model; no new telephone
call was needed.

Recording completion now precedes analysis so a model outage does not prevent
playback. Regression tests reproduced the confirmation and recording failures
before the fixes. The tested changes were made after this call; a second
telephone call was not placed.

The [narrated walkthrough script](demo-guide.md) is ready. A separate screen
recording of that walkthrough has not been captured. Share the actual call
audio and account access only with the intended reviewer.
