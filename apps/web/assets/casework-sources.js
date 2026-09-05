"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const node = (tag, text) => { const e = document.createElement(tag); e.textContent = text; return e; };
  let token = "", epoch = 0, busy = false;
  const session = `sources_${crypto.randomUUID().replaceAll("-", "")}`;
  const pending = new Map();
  function reset() {
    epoch++; token = ""; pending.clear();
    for (const id of ["source-catalog", "dossier-cards", "impact-nodes", "source-id"]) $(id).replaceChildren();
    for (const id of ["dossier-json", "partner-result", "impact-edges", "source-status", "mission-result"]) $(id).textContent = "";
    for (const id of ["mission-id", "bundle-root", "partner-plan", "source-case", "source-resource", "source-queries", "source-reviewer", "partner-report", "partner-job", "impact-task"]) $(id).value = "";
    $("source-force").checked = false;
    $("source-identity").textContent = "Disconnected";
  }
  async function api(path, body, expected = epoch) {
    if (!token) throw new Error("Connect with a scoped credential first.");
    const headers = { Authorization: `Bearer ${token}` };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const r = await fetch(path, { method: body === undefined ? "GET" : "POST", headers,
      body: body === undefined ? undefined : JSON.stringify(body), cache: "no-store" });
    const data = await r.json();
    if (expected !== epoch) throw new Error("Operator changed. Stale response discarded.");
    if (!r.ok) throw new Error(`${r.status} ${data.error || "Request failed"}`);
    return data;
  }
  async function command(path, fields) {
    const e = epoch;
    const snapshot = await api("/api/v2/casework", undefined, e);
    const key = path + JSON.stringify(fields);
    if (!pending.has(key)) pending.set(key, `sourcecmd_${crypto.randomUUID().replaceAll("-", "")}`);
    const body = { ...fields, session_id: session, idempotency_key: pending.get(key), expected_revision: snapshot.revision };
    try {
      const response = await api(path, body, e);
      pending.delete(key);
      return response;
    } catch (error) {
      if (String(error.message).includes("REVISION_CONFLICT")) pending.delete(key);
      throw error;
    }
  }
  const casePath = () => `/api/v2/cases/${encodeURIComponent($("source-case").value.trim())}`;
  function renderDossier(data) {
    $("dossier-cards").replaceChildren();
    for (const r of data.receipts || []) {
      const card = node("article", ""); card.className = "card";
      card.append(node("h3", r.source_id), node("p", r.provenance), node("code", r.receipt_root), node("p", `Expires: ${r.expires_at}`));
      $("dossier-cards").append(card);
    }
    $("bundle-root").value = data.bundle_root || "";
    $("dossier-json").textContent = JSON.stringify(data, null, 2);
  }
  function bind(id, action) {
    $(id).addEventListener("click", async () => {
      if (busy) return;
      busy = true; $(id).disabled = true;
      const e = epoch;
      try { await action(); if (e === epoch) $("source-status").textContent = "Operation finished. Inspect the recorded result and its evidence limits."; }
      catch (error) { if (e === epoch) $("source-status").textContent = error.message; }
      finally { busy = false; $(id).disabled = false; }
    });
  }
  bind("source-connect", async () => {
    const next = $("source-token").value.trim(); $("source-token").value = "";
    reset(); token = next;
    const snapshot = await api("/api/v2/casework");
    $("source-identity").textContent = `${snapshot.principal.actor_id} · ${snapshot.principal.role} · revision ${snapshot.revision}`;
    const config = await api("/api/v2/integrations");
    for (const s of config.sources) {
      const option = node("option", `${s.source_id} · ${s.kind}`); option.value = s.source_id; $("source-id").append(option);
      const card = node("article", ""); card.className = "card";
      card.append(node("h3", s.source_id), node("p", `${s.kind} · TTL ${s.ttl_seconds}s · declared group ${s.independence_group}`));
      $("source-catalog").append(card);
    }
  });
  $("source-logout").addEventListener("click", () => { reset(); $("source-token").value = ""; });
  bind("source-fetch", async () => {
    const result = await command(casePath() + "/sources", { source_id: $("source-id").value,
      resource: $("source-resource").value.trim(), force_refresh: $("source-force").checked });
    $("partner-result").textContent = JSON.stringify(result, null, 2);
    renderDossier(await api(casePath() + "/dossier"));
  });
  bind("source-dossier", async () => renderDossier(await api(casePath() + "/dossier")));
  bind("source-mission", async () => {
    const fields = { queries: JSON.parse($("source-queries").value) };
    if ($("source-reviewer").value.trim()) fields.reviewer_id = $("source-reviewer").value.trim();
    const result = await command(casePath() + "/mission", fields);
    $("partner-result").textContent = JSON.stringify(result, null, 2);
    if (result.mission_id) $("mission-id").value = result.mission_id;
    if (result.report?.report?.report_id) $("partner-report").value = result.report.report.report_id;
    renderDossier(await api(casePath() + "/dossier"));
  });
  bind("partner-prepare", async () => {
    const result = await command(casePath() + "/partner-review", {report_id: $("partner-report").value.trim()});
    $("partner-plan").value = result.plan.plan_id; $("partner-result").textContent = JSON.stringify(result, null, 2);
  });
  bind("partner-verify", async () => {
    const result = await command(`/api/v2/partner-reviews/${encodeURIComponent($("partner-plan").value.trim())}/verify`, {job_id: $("partner-job").value.trim()});
    $("partner-result").textContent = JSON.stringify(result, null, 2);
  });
  bind("impact-load", async () => {
    const data = await api(`/api/v2/tasks/${encodeURIComponent($("impact-task").value.trim())}/impact`);
    $("impact-nodes").replaceChildren();
    for (const n of data.nodes) { const card = node("article", ""); card.className = "card";
      card.append(node("code", n.task_id), node("h3", n.effective_verdict), node("p", n.proof_invalid_reasons?.join(", ") || "Current proof")); $("impact-nodes").append(card); }
    $("impact-edges").textContent = data.edges.map(e => `${e.from} → ${e.to}`).join("\n");
  });
  bind("mission-list", async () => {
    const data = await api("/api/v2/missions");
    $("mission-result").textContent = JSON.stringify(data, null, 2);
    if (data.missions.length) $("mission-id").value = data.missions[0].mission_id;
  });
  bind("mission-inspect", async () => {
    const id = encodeURIComponent($("mission-id").value.trim());
    $("mission-result").textContent = JSON.stringify(await api(`/api/v2/missions/${id}`), null, 2);
  });
  bind("mission-resume", async () => {
    const id = encodeURIComponent($("mission-id").value.trim());
    const result = await command(`/api/v2/missions/${id}/resume`, {});
    $("mission-result").textContent = JSON.stringify(result, null, 2);
  });
})();
