# Live demonstration checklist

These checks are manual and are not part of `pytest`. They require configured
free services, a consenting recipient, and an approved destination.

1. Confirm the provider balance/trial entitlement, allowed destination, number
   verification, LiveKit routing, and recording storage before enabling calls.
2. Start the local application and worker, open the input page and sign in.
3. Start one synthetic call and verify that the intended recipient's phone rings.
4. Have the recipient confirm identity and permission to continue.
5. Discuss supplied metrics, select a slot, and explicitly confirm booking.
6. Inspect the saved appointment; verify doctor, local date/time, and timezone.
7. Close the dashboard during a separate test; the voice worker must continue.
8. End the call and verify transcript, tool results, analysis, and playable audio.
9. Open the matching Opik trace and wait for its automatic score and reason.
10. Repeat a refusal, tool failure, interruption, and unanswered scenario within
    the ten-attempt limit.

Record actual call IDs, trace IDs, outcome, date, and observed results in
`artifacts/verification.md`. Never substitute fixture results for live evidence.
