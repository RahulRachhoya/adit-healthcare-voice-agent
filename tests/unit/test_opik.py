import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from adit_voice_agent.integrations.opik_integration import OpikIntegration, stable_id


class SDKDouble:
    def __init__(self):
        self.trace_inputs = []
        self.spans = []
        self.flush_ok = True
        self.read_count = 0
        self.output = None

    def trace(self, **kwargs):
        self.trace_inputs.append(kwargs)
        self.output = kwargs["output"]
        return self

    def span(self, **kwargs):
        self.spans.append(kwargs)

    def flush(self, **kwargs):
        return self.flush_ok

    def get_trace_content(self, trace_id):
        self.read_count += 1
        return SimpleNamespace(id=trace_id, output=self.output, project_id="test-project", feedback_scores=[])


def fixture_report():
    return json.loads(Path("examples/completed_call.synthetic.json").read_text(encoding="utf-8"))


def test_stable_identifiers_are_uuid7():
    first = stable_id("same-call", "2026-09-14T10:00:00+00:00")
    assert UUID(first).version == 7
    assert first == stable_id("same-call", "2026-09-14T10:00:00+00:00")
    assert first != stable_id("same-call", "2026-09-14T10:00:00+00:00", "tool1")


def test_complete_data_is_present_on_initial_trace_write():
    sdk = SDKDouble()
    adapter = OpikIntegration(client=sdk, workspace="test")
    report = fixture_report()
    result = adapter.publish_completed_call(report)
    logged = sdk.trace_inputs[0]
    assert logged["output"]["analysis"] == report["analysis"]
    assert logged["end_time"] is not None
    for key in ["transcript", "tool_events", "booking", "recording", "variables"]:
        assert logged["input"][key] == report[key]
    assert sdk.read_count == 1
    assert result["trace_id"] == logged["id"]
    adapter.publish_completed_call(report)
    assert sdk.trace_inputs[0]["id"] == sdk.trace_inputs[1]["id"]


def test_flush_failure_is_not_success():
    sdk = SDKDouble()
    sdk.flush_ok = False
    with pytest.raises(TimeoutError):
        OpikIntegration(client=sdk).publish_completed_call(fixture_report())
    assert sdk.read_count == 0


def test_missing_recording_does_not_produce_completed_trace():
    sdk = SDKDouble()
    report = fixture_report()
    report["recording"]["status"] = "pending"
    with pytest.raises(ValueError, match="ready recording"):
        OpikIntegration(client=sdk).publish_completed_call(report)
    assert sdk.trace_inputs == []


def test_adapter_can_be_imported_as_a_single_copied_file(tmp_path):
    import adit_voice_agent.integrations.opik_integration as original
    copied = tmp_path / "portable_opik.py"
    copied.write_text(Path(original.__file__).read_text(encoding="utf-8"), encoding="utf-8")
    spec = importlib.util.spec_from_file_location("portable_opik", copied)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.OpikIntegration(client=SDKDouble()).get_evaluation("test")["status"] == "pending"


def test_versioned_rule_matches_installed_opik_schema():
    # The application isolation rule does not apply to SDK compatibility tests.
    import importlib
    model = importlib.import_module("opik.rest_api.types.automation_rule_evaluator_write")
    rule = json.loads(Path("evaluations/booking_outcome_correctness.json").read_text(encoding="utf-8"))
    parsed = model.AutomationRuleEvaluatorWrite_LlmAsJudge.model_validate(rule)
    assert parsed.sampling_rate == 1.0
    assert parsed.code.variables["analysis"] == "output.analysis"
    assert parsed.code.schema_[0].name == "booking_outcome_correctness"
