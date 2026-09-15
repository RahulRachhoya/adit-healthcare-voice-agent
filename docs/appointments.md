# Appointment availability and call closing

The assessment uses persisted simulated appointments. Doctor names are fictional:
Dr. Meera Shah, Dr. Arjun Rao and Dr. Kavya Menon. The agent explains that the
appointment is simulated separately from the doctor's name.

## Upcoming dates

`src/adit_voice_agent/data/appointment_slots.json` is the single schedule
definition included in both application packages. When the agent requests
availability, the service computes dates 4, 8 and 12 days after the current
calendar day in the clinic timezone, `Asia/Kolkata`.

For example, if it is September 16 in India, the options are September 20 at
10:00 AM, September 24 at 2:30 PM, and September 28 at 11:00 AM. On September 17,
the generated dates become September 21, 25 and 29. Month and year changes are
handled using calendar arithmetic.

Each date/time has a stable database ID. Repeated requests and concurrent
refreshes reuse that row. Booked options are excluded, and no past option is
offered. Previously generated rows remain unchanged so an offered slot can
still be booked across midnight and existing bookings keep their confirmed
doctor and date. The service never moves an existing appointment forward.

`uv run adit-seed` prepares this same schedule for setup; daily manual reseeding
is unnecessary. Edit the packaged definition to change future scheduling rules.
Historical rows are not renamed by editing the definition.

## Patient timezone

The dashboard's **Patient location / timezone** dropdown defaults to India.
Choose where the patient will attend. It changes how appointments are presented,
not when the underlying appointment occurs.

Available options, the booking result and the spoken confirmation use the
selected local time. UTC storage stays unchanged. Named IANA zones apply
daylight-saving rules for the appointment date; fixed UTC offsets are not used.
The API also accepts other valid IANA timezone names.

## Confirmation and disconnection

After explicit recipient confirmation and a successful database booking, the
booking tool reads the saved doctor, date, time and timezone. It then says
“Thank you. Goodbye, and take care.”

The farewell is uninterruptible. After playback completes, the agent suppresses
the automatic model reply to that tool result and drains the session. The worker
receives the close event, deletes the telephone room, preserves final transcript
and tool results, and runs recording/analysis/Opik finalization.

A failed booking keeps the conversation open to choose another slot or retry.
Refusal and wrong-recipient endings use `finish_call`, which speaks its own
farewell and follows the same shutdown path. Internal booking IDs are not read
aloud.

## Verification

Automated tests cover:

- India date rollover while UTC is still on the previous day, month/year
  boundaries, repeated availability, and unchanged saved bookings.
- Different doctor names, occupied-slot exclusion and PostgreSQL insert races.
- Selected timezone propagation through the actual appointment tool, daylight
  saving, and matching offer/booking/report timestamps.
- Waiting for farewell playback before shutdown, booking failure/retry, and
  duplicate tool execution.
- A real LiveKit SDK session with a scripted model: one model turn, one spoken
  farewell, preserved successful tool output, and a close event. This test
  creates no room, uses no provider credit and places no telephone call.

These tests verify implementation behavior. A fresh recipient-observed telephone
test is still needed to verify the final farewell and carrier disconnection
after deploying this change; previous call evidence is preserved separately.
