"""Reviewer metrics derived from saved evidence, without requiring an Opik login."""

from datetime import UTC


def review_metrics(call, booking):
    analysis = call.analysis or {}
    duration = None
    if call.created_at and call.ended_at:
        start = call.created_at.replace(tzinfo=UTC) if call.created_at.tzinfo is None else call.created_at
        end = call.ended_at.replace(tzinfo=UTC) if call.ended_at.tzinfo is None else call.ended_at
        duration = max(0, round((end - start).total_seconds(), 1))
    supplied = {metric["name"].strip().casefold() for metric in call.input_data["biomarkers"]}
    discussed = {name.strip().casefold() for name in analysis.get("metrics_discussed", [])}
    failed_tools = sum(
        bool(event.get("error")) or (
            isinstance(event.get("result"), dict) and event["result"].get("status") == "failed"
        )
        for event in call.tool_events
    )
    return {
        "call_status": call.status,
        "request_duration_seconds": duration,
        "recording_duration_seconds": call.recording.get("duration_seconds"),
        "transcript_turns": len(call.transcript),
        "recipient_turns": sum(turn.get("speaker") == "user" for turn in call.transcript),
        "metrics_discussed": len(supplied & discussed) if call.analysis else None,
        "metrics_supplied": len(supplied),
        "patient_reached": analysis.get("patient_reached"),
        "consultation_offered": analysis.get("consultation_offered"),
        "booking_outcome": "booked" if booking["status"] == "booked" else analysis.get("outcome", "pending"),
        "tool_calls": len(call.tool_events),
        "failed_tool_calls": failed_tools,
        "recording_status": call.recording.get("status", "pending"),
        "analysis_status": call.analysis_status,
        "evaluation_status": call.evaluation.get("status", "pending"),
    }
