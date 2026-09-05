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
    el.textContent = JSON.stringify(await response.json(), null, 2);
  } catch (_) { el.textContent = "Source experiment not available. No completed test is claimed."; }
})();
