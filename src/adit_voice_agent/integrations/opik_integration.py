"""Standalone Opik adapter.

Copy this single file into another application and install ``opik``. The adapter
accepts plain dictionaries and does not import this application's models.
Only this file imports the Opik SDK.
"""

import hashlib
from datetime import UTC, datetime
from urllib.parse import quote
from uuid import UUID


def timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def stable_id(call_id: str, started_at: str, label="call") -> str:
    """Stable UUIDv7 identities make retries upsert the same trace and spans."""
    milliseconds = int(timestamp(started_at).timestamp() * 1000)
    entropy = int.from_bytes(hashlib.sha256(f"{call_id}:{label}".encode()).digest()[:10], "big")
    bits = (milliseconds << 80) | (7 << 76) | ((entropy >> 64 & 0xFFF) << 64)
    bits |= (2 << 62) | (entropy & ((1 << 62) - 1))
    return str(UUID(int=bits))


class OpikIntegration:
    def __init__(self, *, api_key="", workspace="", project_name="adit-healthcare",
                 host="https://www.comet.com/opik/api", web_url="https://www.comet.com/opik",
                 client=None):
        self.api_key = api_key
        self.workspace = workspace
        self.project_name = project_name
        self.host = host
        self.web_url = web_url
        self._client = client

    def client(self):
        if self._client is None:
            if not self.api_key or not self.workspace:
                raise ValueError("Opik API key and workspace must be configured.")
            import opik
            self._client = opik.Opik(
                api_key=self.api_key, workspace=self.workspace, project_name=self.project_name,
                host=self.host, batching=True,
            )
        return self._client

    def publish_completed_call(self, report: dict) -> dict:
        required = {"call_id", "started_at", "ended_at", "metadata", "variables", "transcript",
                    "tool_events", "booking", "recording", "analysis", "call_status"}
        if required - report.keys():
            raise ValueError(f"Incomplete call report: {sorted(required - report.keys())}")
        if report["recording"].get("status") != "ready":
            raise ValueError("A completed-call trace requires a ready recording.")
        client = self.client()
        trace_id = stable_id(report["call_id"], report["started_at"])
        trace = client.trace(
            id=trace_id, name="healthcare_outbound_call",
            start_time=timestamp(report["started_at"]), project_name=self.project_name,
            end_time=timestamp(report["metadata"].get("finalized_at", report["ended_at"])),
            output={"analysis": report["analysis"], "call_status": report["call_status"]},
            tags=["assessment", "completed-call"],
            input={key: report[key] for key in ["variables", "transcript", "tool_events", "booking", "recording"]},
            metadata={**report["metadata"], "call_id": report["call_id"], "schema_version": 1},
        )
        for tool in report["tool_events"]:
            trace.span(
                id=stable_id(report["call_id"], report["started_at"], tool["id"]),
                name=tool["name"], type="tool",
                start_time=timestamp(tool["started_at"]), end_time=timestamp(tool["ended_at"]),
                input=tool["arguments"], output=tool["result"],
            )
        if report["transcript"]:
            trace.span(
                id=stable_id(report["call_id"], report["started_at"], "conversation"),
                name="conversation", start_time=timestamp(report["transcript"][0]["timestamp"]),
                end_time=timestamp(report["ended_at"]), output={"transcript": report["transcript"]},
            )
        timing = report["metadata"].get("analysis_timing")
        if timing:
            trace.span(
                id=stable_id(report["call_id"], report["started_at"], "analysis"),
                name="post_call_analysis", type="llm",
                start_time=timestamp(timing["started_at"]), end_time=timestamp(timing["ended_at"]),
                input={"booking": report["booking"]}, output=report["analysis"],
                model=timing.get("model"), provider="google_ai",
            )
        if not client.flush(timeout=20):
            raise TimeoutError("Opik did not flush within the deadline.")
        # Read-back confirms server persistence rather than merely an SDK enqueue.
        remote = client.get_trace_content(trace_id)
        if not remote or remote.id != trace_id:
            raise RuntimeError("Opik trace read-back did not match.")
        if not remote.output or remote.output.get("analysis") != report["analysis"]:
            raise RuntimeError("Opik has not persisted the completed analysis yet.")
        project_id = remote.project_id
        url = (
            f"{self.web_url.rstrip('/')}/{quote(self.workspace, safe='')}"
            f"/projects/{project_id}/traces?traces={trace_id}"
        )
        return {"trace_id": trace_id, "url": url, "evaluation_status": "pending"}

    def get_evaluation(self, trace_id: str) -> dict:
        remote = self.client().get_trace_content(trace_id)
        scores = [
            score.model_dump(mode="json") if hasattr(score, "model_dump") else dict(score)
            for score in (remote.feedback_scores or [])
        ]
        matching = [s for s in scores if s.get("name") == "booking_outcome_correctness"]
        return {"status": "completed" if matching else "pending", "scores": matching}

    def configure_evaluation(self, rule_config: dict) -> dict:
        """Create the versioned rule using a model available in the Opik workspace."""
        from opik.rest_api.client import OpikApi
        from opik.rest_api.types.automation_rule_evaluator_write import (
            AutomationRuleEvaluatorWrite_LlmAsJudge,
        )

        api = OpikApi(base_url=self.host, api_key=self.api_key, workspace_name=self.workspace, timeout=20)
        projects = api.projects.find_projects(name=self.project_name)
        project = next((p for p in (projects.content or []) if p.name == self.project_name), None)
        if project is None:
            api.projects.create_project(name=self.project_name, visibility="private")
            projects = api.projects.find_projects(name=self.project_name)
            project = next(p for p in projects.content if p.name == self.project_name)
        rules = api.automation_rule_evaluators.find_evaluators(project_id=project.id, name=rule_config["name"])
        existing = next((r for r in (rules.content or []) if r.name == rule_config["name"]), None)
        if existing:
            return {"rule_id": existing.id, "status": "existing", "note": "Review existing settings in Opik; no changes were made."}
        request = AutomationRuleEvaluatorWrite_LlmAsJudge.model_validate({
            **rule_config, "project_id": project.id,
        })
        api.automation_rule_evaluators.create_automation_rule_evaluator(request=request)
        rules = api.automation_rule_evaluators.find_evaluators(project_id=project.id, name=rule_config["name"])
        created = next(r for r in rules.content if r.name == rule_config["name"])
        return {"rule_id": created.id, "status": "created"}
