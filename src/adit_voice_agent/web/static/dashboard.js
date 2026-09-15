"use strict";
const csrf = document.querySelector('meta[name="csrf-token"]').content;
const page = document.querySelector("[data-page]");
const terminalStates = new Set(["completed", "unanswered", "failed", "cancelled", "disconnected"]);
const readable = value => String(value || "pending").replaceAll("_", " ");
const timeLabel = value => value ? new Date(value).toLocaleString() : "—";
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function message(text, error = false) {
  const node = document.getElementById("page-message");
  if (!node) return;
  node.textContent = text;
  node.className = `notice${error ? " error" : ""}${text ? "" : " hidden"}`;
}
async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options,
    headers: {"Content-Type": "application/json", "X-CSRF-Token": csrf, ...options.headers},
  });
  if (response.status === 401) {
    location.assign("/login");
    throw new Error("Sign in to continue.");
  }
  const data = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map(item => `${item.loc.slice(1).join(".")}: ${item.msg}`).join("; ")
      : data.detail;
    throw new Error(detail || `Request failed (${response.status}).`);
  }
  return data;
}
function badge(text, good = false) {
  return el("span", readable(text), `badge ${good ? "success" : "neutral"}`);
}
function empty(target, title, description) {
  const wrapper = el("div", undefined, "empty-state");
  wrapper.append(el("strong", title), el("p", description));
  target.replaceChildren(wrapper);
}
function pair(label, value) {
  const node = el("div", undefined, "key-value");
  node.append(el("strong", label), el("span", String(value ?? "—")));
  return node;
}

if (page?.dataset.page === "dashboard") {
  const form = document.getElementById("call-form");
  const start = document.getElementById("start-call");
  let enabled = false;
  let lastPayload = "";
  let requestKey = "";
  function addMetric(name = "", value = "", unit = "") {
    const container = document.getElementById("biomarkers");
    if (container.children.length >= 10) return;
    const row = el("div", undefined, "metric-row");
    const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
    for (const [key, title, type, initial] of [
      ["name", "Metric", "text", name],
      ["value", "Value", "number", value],
      ["unit", "Unit", "text", unit],
      ["measured_at", "Measured on", "date", yesterday],
    ]) {
      const label = el("label", title);
      const input = document.createElement("input");
      input.dataset.key = key;
      input.type = type;
      input.value = initial;
      input.required = true;
      if (type === "number") { input.min = "0"; input.step = "0.0001"; }
      if (type === "date") input.max = new Date().toISOString().slice(0, 10);
      label.append(input);
      row.append(label);
    }
    const remove = el("button", "×", "button subtle remove-metric");
    remove.type = "button";
    remove.setAttribute("aria-label", "Remove metric");
    remove.addEventListener("click", () => {
      if (container.children.length > 1) row.remove();
    });
    row.append(remove);
    container.append(row);
  }
  addMetric("Blood glucose", "110", "mg/dL");
  addMetric("HbA1c", "5.8", "%");
  document.getElementById("add-metric").addEventListener("click", () => addMetric());

  async function refresh() {
    try {
      const [ready, listing] = await Promise.all([api("/api/readiness"), api("/api/calls")]);
      enabled = ready.calls_enabled;
      start.disabled = !enabled;
      const indicator = document.getElementById("readiness-badge");
      indicator.textContent = enabled ? "Calling enabled" : "Setup required";
      indicator.className = `badge ${enabled ? "success" : "warning"}`;
      const readiness = document.getElementById("service-readiness");
      readiness.replaceChildren();
      for (const [name, state] of Object.entries(ready.configuration)) {
        const row = el("div", undefined, "service-row");
        row.append(el("span", name), badge(state.configured ? "Configured" : "Needs setup", state.configured));
        readiness.append(row);
      }
      const backup = el("div", undefined, "service-row");
      backup.append(el("span", "Model backup"), badge(ready.model_fallback?.configured ? "Groq configured" : "Not configured", ready.model_fallback?.configured));
      readiness.append(backup);
      if (!enabled) message("Live calling is disabled until the service accounts, approved number, and free-trial checks are ready.");
      const list = document.getElementById("call-list");
      if (!listing.calls.length) {
        empty(list, "Your first conversation starts here", "Completed calls and their outcomes will appear in this workspace.");
      } else {
        list.replaceChildren();
        for (const call of listing.calls) {
          const row = el("div", undefined, "history-row");
          const title = el("div");
          title.append(el("strong", call.name), el("small", timeLabel(call.created_at)));
          const link = el("a", "Review call →");
          link.href = `/calls/${encodeURIComponent(call.id)}`;
          row.append(title, badge(call.status, call.status === "completed"),
            el("span", `Analysis: ${readable(call.analysis_status)}`, "muted history-processing"), link);
          list.append(row);
        }
      }
    } catch (error) { message(error.message, true); }
  }
  document.getElementById("refresh-calls").addEventListener("click", refresh);
  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (!enabled || !form.reportValidity()) return;
    const data = new FormData(form);
    const biomarkers = [...document.querySelectorAll(".metric-row")].map(row =>
      Object.fromEntries([...row.querySelectorAll("input")].map(input => [input.dataset.key, input.value]))
    );
    const payload = JSON.stringify({
      name: data.get("name"), phone: data.get("phone"), timezone: data.get("timezone"),
      biomarkers, recipient_consented: data.get("recipient_consented") === "on",
    });
    if (payload !== lastPayload) { requestKey = crypto.randomUUID(); lastPayload = payload; }
    start.disabled = true;
    start.textContent = "Starting call…";
    message("The call request is being prepared. Please do not resubmit.");
    try {
      const call = await api("/api/calls", {
        method: "POST", body: payload, headers: {"Idempotency-Key": requestKey},
      });
      location.assign(`/calls/${encodeURIComponent(call.id)}`);
    } catch (error) {
      message(error.message, true);
      start.disabled = !enabled;
      start.textContent = "Start test call ↗";
    }
  });
  refresh();
}

if (page?.dataset.page === "detail") {
  const id = page.dataset.callId;
  let polling = 0;
  let timer;
  async function refresh() {
    clearTimeout(timer);
    try {
      const call = await api(`/api/calls/${encodeURIComponent(id)}`);
      document.getElementById("call-title").textContent = call.patient.name;
      document.getElementById("call-subtitle").textContent = `${call.patient.phone} · ${timeLabel(call.created_at)}`;
      document.getElementById("call-status").textContent = readable(call.status);
      document.getElementById("end-call").classList.toggle("hidden", terminalStates.has(call.status));
      if (call.error) message(call.error, true);
      else message("");
      const transcript = document.getElementById("transcript");
      if (!call.transcript.length) empty(transcript, "No conversation captured yet", "The transcript appears as the recipient and agent speak.");
      else {
        transcript.replaceChildren();
        for (const turn of call.transcript) {
          const item = el("div", undefined, `message ${turn.speaker}`);
          item.append(el("span", `${turn.speaker === "user" ? "RECIPIENT" : "AI ASSISTANT"}${turn.interrupted ? " · interrupted" : ""}`, "message-label"), el("span", turn.text));
          transcript.append(item);
        }
      }
      const booking = document.getElementById("booking");
      booking.replaceChildren();
      if (call.booking.status === "booked") {
        document.getElementById("booking-title").textContent = "Appointment booked";
        const slot = call.booking.slot;
        booking.append(pair("Doctor", slot.doctor), pair("Appointment time", `${slot.local_time} (${slot.timezone})`), pair("Confirmation", call.booking.appointment_id), el("p", "Simulated assessment appointment", "small muted"));
      } else {
        document.getElementById("booking-title").textContent = "No saved appointment";
        booking.append(el("p", call.analysis?.outcome_reason || "A booking will appear only after it has been saved successfully.", "muted"));
      }
      document.getElementById("recording-status").textContent = readable(call.recording.status);
      document.getElementById("load-recording").classList.toggle("hidden", call.recording.status !== "ready");
      const analysis = document.getElementById("analysis");
      analysis.replaceChildren();
      if (call.analysis) {
        analysis.append(el("p", call.analysis.summary),
          pair("Outcome", readable(call.analysis.outcome)),
          pair("Reason", call.analysis.outcome_reason),
          pair("Follow-up needed", call.analysis.follow_up_needed ? "Yes" : "No"));
      } else empty(analysis, readable(call.analysis_status), "Analysis is generated after the call ends.");
      const tools = document.getElementById("tools");
      tools.replaceChildren();
      for (const tool of call.tool_events) {
        const item = el("details", undefined, "tool");
        item.append(el("summary", readable(tool.name)), el("pre", JSON.stringify({arguments: tool.arguments, result: tool.result}, null, 2)));
        tools.append(item);
      }
      if (!call.tool_events.length) empty(tools, "No tool activity", "Appointment tool calls and their results will appear here.");
      const metrics = call.review_metrics || {};
      const review = document.getElementById("review-metrics");
      review.replaceChildren();
      const yesNo = value => value === null || value === undefined ? "Pending" : value ? "Yes" : "No";
      const duration = seconds => {
        if (seconds === null || seconds === undefined) return "Pending";
        const rounded = Math.round(seconds);
        return `${Math.floor(rounded / 60)}m ${rounded % 60}s`;
      };
      for (const [label, value] of [
        ["Call status", readable(call.status)],
        [metrics.recording_duration_seconds != null ? "Recorded audio" : "Request duration · includes setup", duration(metrics.recording_duration_seconds ?? metrics.request_duration_seconds)],
        ["Patient reached", yesNo(metrics.patient_reached)],
        ["Metrics discussed", metrics.metrics_discussed == null ? "Pending" : `${metrics.metrics_discussed} / ${metrics.metrics_supplied}`],
        ["Consultation offered", yesNo(metrics.consultation_offered)],
        ["Booking outcome", readable(metrics.booking_outcome)],
        ["Conversation turns", metrics.transcript_turns ?? "Pending"],
        ["Tool calls · failed", `${metrics.tool_calls ?? 0} · ${metrics.failed_tool_calls ?? 0}`],
        ["Recording", readable(call.recording.status)],
        ["Analysis", readable(call.analysis_status)],
      ]) review.append(pair(label, value));
      const evaluation = document.getElementById("evaluation");
      evaluation.replaceChildren(el("h3", "Report accuracy"));
      for (const score of (call.evaluation.scores || [])) {
        evaluation.append(el("div", `${score.value} / 1`, `score${score.value === 0 ? " fail" : ""}`), el("p", score.reason || "Outcome correctness score."));
      }
      if (!call.evaluation.scores?.length) {
        const status = call.export_status === "not_applicable" ? "No conversation to evaluate" : `Evaluation: ${readable(call.evaluation.status || "pending")}`;
        evaluation.append(el("p", status, "muted"), pair("Evidence export", readable(call.export_status)));
      }
      evaluation.append(el("p", "This score checks whether the report matches the evidence. A passing score does not mean the call or booking succeeded.", "small"));
      const finished = call.finalization_status === "complete" &&
        (call.export_status === "not_applicable" || call.evaluation.status === "completed");
      if (!finished && polling++ < 100) timer = setTimeout(refresh, 3000);
      else if (!finished && !call.error) message("Automatic updates paused after five minutes. Use Refresh to check again.");
    } catch (error) { message(error.message, true); }
  }
  document.getElementById("refresh-detail").addEventListener("click", () => { polling = 0; refresh(); });
  document.getElementById("end-call").addEventListener("click", async event => {
    event.currentTarget.disabled = true;
    try { await api(`/api/calls/${id}/end`, {method: "POST"}); await refresh(); }
    catch (error) { message(error.message, true); }
    finally { document.getElementById("end-call").disabled = false; }
  });
  document.getElementById("load-recording").addEventListener("click", async () => {
    try {
      const recording = await api(`/api/calls/${id}/recording`);
      const audio = document.getElementById("call-audio");
      audio.src = recording.url;
      audio.classList.remove("hidden");
      audio.load();
    } catch (error) { message(error.message, true); }
  });
  refresh();
}
