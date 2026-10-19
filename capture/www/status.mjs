const KEYS = ["complete", "partial", "refused", "pending", "deferred", "retry"];
const NAMES = {complete: "Complete", partial: "Partial", refused: "Refused", pending: "Pending", deferred: "Quota deferred", retry: "Retry backoff", active: "Active"};
const RAIDS = {mc: "Molten Core", bwl: "Blackwing Lair", aq40: "Temple of Ahn’Qiraj", naxxramas: "Naxxramas"};
const HEADLINES = {running: "Running", waiting: "Waiting for quota", attention: "Needs attention", finished: "Finished"};
const STALE_MS = 10 * 60 * 1000;
const integer = value => Number.isSafeInteger(value) && value >= 0;
export function time(value) {
  const stamp = typeof value === "number" ? value : Date.parse(value);
  if (!Number.isFinite(stamp)) return "Not recorded";
  return new Date(stamp).toISOString().replace("T", " · ").replace(/\.\d{3}Z$/, " UTC");
}
export function age(stamp, now) {
  const seconds = Math.max(0, Math.floor((now - Date.parse(stamp)) / 1000));
  if (!Number.isFinite(seconds)) return "unknown";
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}
export function validate(data) {
  if (!data || data.version !== 1 || !HEADLINES[data.state] || !Array.isArray(data.entries)) throw new Error("Invalid status");
  if (!KEYS.every(key => integer(data.counts?.[key]))) throw new Error("Invalid counts");
  if (!Number.isFinite(Date.parse(data.heartbeat_utc))) throw new Error("Missing heartbeat");
  if (!integer(data.usable_archives) || !integer(data.alerts_pending) || !integer(data.alert_failures)) throw new Error("Invalid totals");
  if (data.entries.length !== KEYS.reduce((sum, key) => sum + data.counts[key], 0)) throw new Error("Counts disagree");
  const byResult = Object.fromEntries(KEYS.map(key => [key, 0]));
  const seen = new Set();
  for (const entry of data.entries) {
    if (!entry || typeof entry.id !== "string" || seen.has(entry.id) || !KEYS.includes(entry.result) || !integer(entry.archives)) throw new Error("Invalid entry");
    seen.add(entry.id); byResult[entry.result] += 1;
  }
  if (!KEYS.every(key => byResult[key] === data.counts[key])) throw new Error("Result counts disagree");
  const summary = data.summary;
  if (summary) {
    const reuseKeys = ["universe_runs", "capture_ready_runs", "all_registered_runs", "offline_reuse_runs"];
    const unknown = reuseKeys.every(key => summary[key] === null);
    const known = reuseKeys.every(key => integer(summary[key])) && summary.universe_runs === summary.scheduled_runs + summary.capture_ready_runs && summary.capture_ready_runs === summary.all_registered_runs + summary.offline_reuse_runs;
    if (summary.scheduled_runs !== data.entries.length || (!unknown && !known)) throw new Error("Invalid queue summary");
  }
  return data;
}
export function view(data, now = Date.now(), connected = true) {
  if (!data) return {headline: connected ? "Waiting for status" : "Connection unavailable", tone: "warning", active: false};
  const quiet = data.state === "finished" && data.alerts_pending === 0;
  const stale = !quiet && now - Date.parse(data.heartbeat_utc) > STALE_MS;
  const active = connected && !stale && data.state === "running";
  const headline = !connected ? "Connection unavailable" : stale ? "Worker offline" : HEADLINES[data.state];
  const tone = !connected || stale || data.state === "attention" ? "warning" : data.state === "finished" ? "good" : data.state === "waiting" ? "quiet" : "good";
  const ended = data.counts.complete + data.counts.partial + data.counts.refused;
  return {headline, tone, active, stale, quiet, ended, total: data.entries.length};
}
export function runLabel(entry) {
  return `${entry.category || "Unspecified"} ${entry.class || `Class ${entry.class_id}`}`;
}
export function visibleRows(data, model, query = "", filter = "all") {
  const needle = query.trim().toLocaleLowerCase();
  return data.entries.filter(entry => {
    const result = model.active && data.current?.id === entry.id ? "active" : entry.result;
    return (filter === "all" || result === filter) &&
      `${entry.raid} ${RAIDS[entry.raid] || entry.raid} ${runLabel(entry)} ${entry.metric} ${entry.faction}`.toLocaleLowerCase().includes(needle);
  });
}
export function mount(doc, fetchStatus = fetch, now = Date.now) {
  let data = null, connected = true, polling = false, lastReceived = null, rowsData = null, rowsKey = "";
  const el = id => doc.getElementById(id);
  const text = (id, value) => { if (el(id).textContent !== value) el(id).textContent = value; };
  function renderRows(model) {
    const key = `${el("search").value}|${el("filter").value}|${model.active}|${model.stale}|${connected}`;
    if (data === rowsData && key === rowsKey) return;
    rowsData = data; rowsKey = key;
    const tbody = el("runs"); tbody.replaceChildren();
    if (!data) return;
    const rows = visibleRows(data, model, el("search").value, el("filter").value);
    function cell(parent, content, className = "") {
      const node = doc.createElement("td"); node.textContent = content; node.className = className; parent.append(node); return node;
    }
    for (const entry of rows) {
      const tr = doc.createElement("tr"), first = cell(tr, "");
      const title = doc.createElement("div"); title.className = "run-title"; title.textContent = runLabel(entry); first.append(title);
      const sub = doc.createElement("div"); sub.className = "run-subtitle"; sub.textContent = `${RAIDS[entry.raid] || entry.raid} · ${entry.faction} · ${String(entry.metric).toUpperCase()}`; first.append(sub);
      const result = model.active && data.current?.id === entry.id ? "active" : entry.result;
      const badge = doc.createElement("span"); badge.className = `badge ${result}`; badge.textContent = NAMES[result]; cell(tr, "").append(badge);
      const archives = cell(tr, ""), archiveLabel = doc.createElement("span");
      archiveLabel.className = "mobile-label"; archiveLabel.textContent = "Archives: "; archives.append(archiveLabel);
      const archiveCount = doc.createElement("span"); archiveCount.textContent = String(entry.archives); archives.append(archiveCount);
      const reason = cell(tr, entry.reason || "Not started.", "row-reason");
      if (entry.retry_at_utc) { const retry = doc.createElement("span"); retry.className = "row-retry"; retry.textContent = `Scheduled: ${time(entry.retry_at_utc)}`; reason.append(retry); }
      tbody.append(tr);
    }
    if (!rows.length) { const tr = doc.createElement("tr"), td = cell(tr, data.entries.length ? "No runs match these filters." : "This queue has no scheduled runs.", "empty"); td.colSpan = 4; tbody.append(tr); }
    text("table-summary", `${rows.length} of ${data.entries.length} scheduled runs shown${!connected || model.stale ? " · Last saved snapshot" : ""}.`);
  }
  function render() {
    const currentNow = now(), model = view(data, currentNow, connected);
    text("clock", time(currentNow)); text("state", model.headline); el("state").dataset.tone = model.tone;
    el("connection").dataset.tone = !connected || model.stale ? "warning" : "good";
    text("connection-text", !connected ? "Cannot reach the status feed. Reconnecting automatically." : !data ? "Connecting to the saved status…" : model.stale ? `Worker heartbeat is stale · last reported ${age(data.heartbeat_utc, currentNow)}` : model.quiet ? "Queue ended · last saved completion status" : `Worker reported ${age(data.heartbeat_utc, currentNow)}`);
    text("snapshot-time", data ? `${!connected || model.stale ? `Last known ${HEADLINES[data.state]} · ` : "Snapshot · "}${time(data.heartbeat_utc)}` : "No status received yet");
    if (!data) {
      text("reason", connected ? "The worker has not been checked yet." : "The status feed is unavailable. Capture may still be running; this page cannot confirm it.");
      return;
    }
    text("reason", !connected || model.stale ? "Live capture state cannot be confirmed. Counts below are the last saved snapshot." : data.reason || (model.active ? "Collecting and saving raid evidence. The heartbeat tracks the worker, not analysis progress." : "The saved worker status is shown below."));
    const current = data.current;
    text("target-label", model.active ? "Current run" : current ? "Last reported run" : "Queue state");
    text("target", current ? `${runLabel(current)} · ${RAIDS[current.raid] || current.raid}` : data.state === "finished" ? "All scheduled runs have ended" : data.state === "waiting" ? "No capture running during the scheduled wait" : "No active run recorded");
    text("target-detail", current ? `${current.faction} · ${String(current.metric).toUpperCase()} · Candidate ${current.candidate ?? "?"} of ${current.candidate_count ?? "?"} · Attempt ${current.attempt}` : "Results remain available in the run ledger.");
    const finished = data.state === "finished";
    text("time-label", finished ? "Queue ended at" : "Next scheduled retry");
    text("retry", time(finished ? data.finished_at_utc : data.next_retry_utc));
    text("retry-note", finished ? "Capture attempts ended; evidence review is still separate." : data.next_retry_utc ? "Recorded by the worker · not an estimated finish time." : "No retry time recorded. No finish-time estimate is made.");
    text("progress-time", time(data.last_progress_utc));
    text("ended", `${model.ended} / ${model.total} runs ended`);
    for (const key of KEYS) text(`count-${key}`, String(data.counts[key]));
    for (const key of ["complete", "partial", "refused"]) el(`bar-${key}`).style.width = `${model.total ? data.counts[key] / model.total * 100 : 0}%`;
    el("bar").setAttribute("aria-valuenow", String(model.total ? Math.round(model.ended / model.total * 100) : 0));
    el("bar").setAttribute("aria-valuetext", `${model.ended} of ${model.total} scheduled runs ended`);
    text("archives", `${data.usable_archives} verified archive${data.usable_archives === 1 ? "" : "s"} retained · may include repeated attempts`);
    text("alerts", `${data.alerts_pending} alert${data.alerts_pending === 1 ? "" : "s"} pending · ${data.alert_failures} failed delivery attempt${data.alert_failures === 1 ? "" : "s"}`);
    const summary = data.summary;
    text("reuse", summary && summary.capture_ready_runs !== null ? `${summary.scheduled_runs} scheduled capture runs from ${summary.universe_runs} configurations. ${summary.capture_ready_runs} runs reuse existing evidence: ${summary.all_registered_runs} with all bosses registered, ${summary.offline_reuse_runs} with offline registration or duty review still open. Reuse does not mark cells complete.` : `${model.total} scheduled capture runs. Existing-evidence counts were not supplied and are unknown.`);
    renderRows(model);
  }
  async function poll() {
    if (polling) return;
    polling = true; el("refresh").disabled = true;
    const abort = new AbortController(), timeout = setTimeout(() => abort.abort(), 8000);
    try {
      const response = await fetchStatus("./status.json", {cache: "no-store", signal: abort.signal, credentials: "same-origin"});
      if (!response.ok) throw new Error("Status unavailable");
      const next = validate(await response.json());
      if (Date.parse(next.heartbeat_utc) > now() + 60000) throw new Error("Worker clock is ahead");
      data = next; lastReceived = now(); connected = true;
    } catch { connected = false; }
    finally { clearTimeout(timeout); polling = false; el("refresh").disabled = false; render(); }
  }
  el("refresh").addEventListener("click", poll);
  el("search").addEventListener("input", render); el("filter").addEventListener("change", render);
  const pollTimer = setInterval(poll, 15000), ageTimer = setInterval(render, 1000);
  void poll();
  return {poll, render, snapshot: () => ({data, connected, lastReceived}), destroy() { clearInterval(pollTimer); clearInterval(ageTimer); }};
}
if (typeof document !== "undefined") mount(document);
