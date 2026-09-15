# Assessment requirements and evidence

Source: the supplied one-page **Adit Assignment.pdf**. The PDF is assessment material; it is not permission to contact people, spend money, or publish credentials. The owner approved implementation with synthetic data, consenting testers, and a zero-payment budget.

| PDF requirement | Implementation | Required demonstration evidence | Current verification |
|---|---|---|---|
| Outbound voice agent using LiveKit | `agent/worker.py`, `services/calls.py` | Answered telephone call, LiveKit room/dispatch identity | Real Vobiz call completed; room, dispatch, trunk and provider charge recorded |
| Patient name, phone and biomarkers supplied as variables | `schemas.py`, dashboard form, agent prompt | Agent reads the submitted values accurately | Input validation and form verified locally |
| Discuss health information and try to book a consultation | `healthcare_agent.py`, versioned prompt | Actual conversation offering consultation | Real call accurately discussed glucose 110 mg/dL and HbA1c 5.8%, then offered consultation |
| Simulated scheduling function | `agent/tools.py`, `services/booking.py` | Saved appointment ID and matching tool output | Actual call saved booking `09e3f45f-f83a-41b8-af0c-fb494fd30b33`; it survived container recreation |
| Post-call analysis | `services/post_call.py` | Saved analysis matching authoritative booking | Gemini 3.5 Flash-Lite analyzed the actual call; booking and evidence validation passed |
| Complete Opik trace | `integrations/opik_integration.py` | Metadata, variables, transcript, tools, audio reference, analysis | All required fields and six child spans read back from the actual completed-call trace |
| Automatic online evaluation | `evaluations/`, configuration CLI | Real call trace scored automatically by active Opik rule | Actual call scored 1.0 with source `online_scoring`; separate five synthetic cases remain recorded |
| Standalone, reusable Opik integration | Single integration module with ordinary dictionary interface | Copy module into another project | Copy/import independence tested |
| Working code and clear README | Repository, lockfile, migrations, docs, tests | Clean install and reproducible commands | Fresh locked Python installation, 93 tests, Ruff and migration check passed |
| Full demonstration and explanation | `demo-guide.md`, `architecture.md` | Walkthrough, actual call/trace/evaluation identifiers and explanation of the implementation | Real call audio/report/trace/score available; separate narrated screen walkthrough remains |

The PDF's final deliverable bullet is incomplete. The implementation follows its earlier explicit modular integration requirement rather than inventing additional obligations.

## Scope boundary

The PDF defines the functional assessment. The owner additionally requested a public GitHub repository and hosted reviewer access. The web form remains the entry point for patient variables and call evidence. Public deployment uses Render, LiveKit Cloud, and shared Supabase PostgreSQL; local development remains available.

Public hosting is an owner-requested delivery enhancement, not a PDF requirement. See [deployment.md](deployment.md). Future telephone scheduling is a separate planned enhancement and is not yet implemented. The PDF's consultation scheduling refers to the implemented simulated doctor booking. The PDF requires a complete demonstration but does not mandate a narrated-video format.

Login, recipient restrictions, time/attempt limits, saved booking records, retries and tests support the required call demonstration and the existing zero-payment constraint. They are not additional product workflows. There are no real calendar/EHR integrations, messaging, clinical decisions or retrieval features.

## Completion gate

The implemented telephone workflow and its required evidence are verified.
See [the actual call](call-evidence.md) for identifiers, recording and automatic
score. A separate narrated screen walkthrough remains before a submission
claim covering that deliverable. Public deployment is not a completion gate.
