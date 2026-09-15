"""Normalize the final SDK history without inventing missing tool results."""

import json
from datetime import UTC, datetime


def timestamp(value):
    return datetime.fromtimestamp(value, UTC).isoformat()


def history_evidence(items, ended_at):
    transcript = []
    tools = []
    outputs = {item.call_id: item for item in items if item.type == "function_call_output"}
    for item in items:
        if item.type == "message" and item.role in {"user", "assistant"} and item.text_content:
            transcript.append({
                "id": item.id, "speaker": item.role, "text": item.text_content,
                "timestamp": timestamp(item.created_at), "interrupted": item.interrupted,
            })
        elif item.type == "function_call":
            output = outputs.get(item.call_id)
            try:
                arguments = json.loads(item.arguments)
            except (TypeError, ValueError):
                arguments = {"invalid_arguments": True}
            try:
                result = json.loads(output.output) if output else {
                    "status": "unknown", "error": "No tool output was captured before hangup.",
                }
            except (TypeError, ValueError):
                result = {"output": str(output.output), "is_error": output.is_error}
            tools.append({
                "id": item.call_id, "name": item.name, "arguments": arguments,
                "result": result if isinstance(result, dict) else {"output": result},
                "started_at": timestamp(item.created_at),
                "ended_at": timestamp(output.created_at) if output else ended_at,
            })
    return sorted(transcript, key=lambda t: (t["timestamp"], t["id"])), tools
