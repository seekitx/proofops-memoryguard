"use strict";
(async () => {
  const $ = (id) => document.getElementById(id);
  try {
    const response = await fetch("/api/v2/public-evidence", { cache: "no-store" });
    if (!response.ok) throw new Error(`Evidence endpoint returned ${response.status}`);
    const data = await response.json();
    $("capture-state").textContent = data.state.replaceAll("_", " ");
    $("capture-scope").textContent = data.scope;
    $("current-commit").textContent = data.current_build_commit || "Module not enabled";
    $("capture-commit").textContent = data.capture?.build_commit || "Not recorded";
    $("source-match").textContent = data.source_matches ? "MATCH" : "NOT MATCHED";
    $("capture-meta").textContent = data.capture
      ? `${data.capture.backend} · ${data.capture.process_count} observed processes · ${data.capture.captured_at} · synthetic data`
      : "No current v2 capture has been published. This is not a claim that no private recording exists.";
    for (const [name, passed] of Object.entries(data.capture?.checks || {})) {
      const card = document.createElement("article"); card.className = "card";
      const title = document.createElement("h3"); title.textContent = name.replaceAll("_", " ");
      const label = document.createElement("p"); label.textContent = passed ? "Recorded as passed" : "Recorded as failed";
      card.append(title, label); $("capture-checks").append(card);
    }
    $("evidence-json").textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    $("capture-state").textContent = "EVIDENCE UNAVAILABLE";
    $("capture-scope").textContent = error.message;
  }
})();

(async () => {
  const el = document.getElementById("source-experiment");
  if (!el) return;
  try {
    const response = await fetch("/api/v2/public-source-experiment", {cache: "no-store"});
    if (!response.ok) throw new Error("Not available");
    const data = await response.json();
    el.textContent = JSON.stringify(data, null, 2);
    document.getElementById("source-summary").textContent = data.state === "NOT_RECORDED"
      ? "No experiment record published here. No pass is claimed."
      : `Published status: ${String(data.state || "UNKNOWN").replaceAll("_", " ")}.`;
  } catch (_) {
    el.textContent = "Source experiment not available. No completed test is claimed.";
    document.getElementById("source-summary").textContent = "Record unavailable. No pass is claimed.";
  }
})();

(async () => {
  const target = document.getElementById("release-gate");
  if (!target) return;
  try {
    const response = await fetch("/api/v2/public-release", {cache:"no-store"});
    if (!response.ok) throw new Error("Release record unavailable");
    const data = await response.json();
    target.textContent = JSON.stringify(data, null, 2);
    document.getElementById("release-summary").textContent = data.state === "CURRENT_LOCAL_PASSED"
      ? "Published local checks passed for this build. This does not establish contest readiness."
      : `Published status: ${String(data.state || "UNKNOWN").replaceAll("_", " ")}. A current full pass is not established.`;
    for (const stage of data.stages || []) {
      const card = document.createElement("article"); card.className = "card";
      const name = document.createElement("h3"); name.textContent = String(stage.name).replaceAll("_", " ");
      const state = document.createElement("p"); state.textContent = String(stage.state);
      card.append(name, state); document.getElementById("release-stages").append(card);
    }
  } catch (_) {
    target.textContent = "Release gate not recorded. No pass is claimed.";
    document.getElementById("release-summary").textContent = "Record unavailable. No pass is claimed.";
  }
})();
