import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {validate, view, visibleRows, mount, time} from "../../capture/www/status.mjs";

const NOW = Date.parse("2026-10-19T18:00:00Z");
function snapshot(state = "running") {
  const entries = [
    {id: "mc-mage", raid: "mc", class: "Mage", category: "Fire", metric: "dps", faction: "Horde", result: "pending", archives: 0, reason: "Acquiring and saving raid data."},
    {id: "bwl-priest", raid: "bwl", class: "Priest", category: "Holy", metric: "hps", faction: "Alliance", result: "complete", archives: 1, reason: "Capture finished and its archive was verified."},
  ];
  return {version: 1, state, reason: "", heartbeat_utc: new Date(NOW).toISOString(), last_progress_utc: null, next_retry_utc: null, finished_at_utc: null,
    current: {id: "mc-mage", class: "Mage", category: "Fire", raid: "mc", faction: "Horde", metric: "dps", candidate: 1, candidate_count: 3, attempt: 1},
    counts: {complete: 1, partial: 0, refused: 0, pending: 1, deferred: 0, retry: 0}, usable_archives: 1, alerts_pending: 0, alert_failures: 0,
    summary: {universe_runs: 4, scheduled_runs: 2, capture_ready_runs: 2, all_registered_runs: 1, offline_reuse_runs: 1}, entries};
}
test("live running, waiting and attention are distinct", () => {
  assert.equal(view(validate(snapshot()), NOW).active, true);
  assert.equal(view(snapshot("waiting"), NOW).headline, "Waiting for quota");
  assert.equal(view(snapshot("attention"), NOW).headline, "Needs attention");
  assert.equal(view(snapshot("attention"), NOW).active, false);
});
test("ageing snapshot loses its live claim without another fetch", () => {
  const data = snapshot();
  assert.equal(view(data, NOW + 600001).headline, "Worker offline");
  assert.equal(view(data, NOW + 600001).active, false);
  assert.equal(view(data, NOW, false).headline, "Connection unavailable");
  assert.equal(view(null, NOW, false).active, false);
});
test("a finished snapshot can stop its heartbeat only without pending delivery", () => {
  const data = snapshot("finished");
  assert.equal(view(data, NOW + 86400000).headline, "Finished");
  data.alerts_pending = 1;
  assert.equal(view(data, NOW + 86400000).headline, "Worker offline");
  assert.equal(view(data, NOW, false).headline, "Connection unavailable");
});
test("bad counts, duplicate IDs and contradictory reuse are rejected", () => {
  for (const change of [d => d.counts.complete = -1, d => d.entries[1].id = d.entries[0].id, d => d.counts.partial = 1, d => d.summary.offline_reuse_runs = 2, d => d.summary.capture_ready_runs = null]) {
    const data = snapshot(); change(data); assert.throws(() => validate(data));
  }
  const unknown = snapshot(); unknown.summary = {scheduled_runs: 2, universe_runs: null, capture_ready_runs: null, all_registered_runs: null, offline_reuse_runs: null};
  assert.equal(validate(unknown), unknown);
});
test("filters use friendly raid/class/faction labels; active is not a new count", () => {
  const data = snapshot(), model = view(data, NOW);
  assert.equal(visibleRows(data, model, "molten").length, 1);
  assert.equal(visibleRows(data, model, "priest", "complete").length, 1);
  assert.equal(visibleRows(data, model, "", "active")[0].id, "mc-mage");
  assert.equal(visibleRows(data, view(data, NOW + 600001), "", "active").length, 0);
  assert.equal(data.counts.pending, 1);
  assert.equal(time(NOW), "2026-10-19 · 18:00:00 UTC");
});
test("raid-code search accepts MC, BWL and AQ40 regardless of case", () => {
  for (const raid of ["mc", "bwl", "aq40"]) {
    const data = snapshot(); data.entries[0].raid = raid;
    assert.equal(visibleRows(data, view(data, NOW), raid.toUpperCase())[0].id, "mc-mage");
  }
});
class Element {
  constructor() { this.children = []; this._text = ""; this.dataset = {}; this.style = {}; this.value = ""; this.events = {}; this.attributes = {}; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(""); }
  set innerHTML(_) { throw new Error("Untrusted HTML must never be inserted"); }
  append(node) { this.children.push(node); }
  replaceChildren() { this.children = []; this._text = ""; }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener(name, callback) { this.events[name] = callback; }
}
function documentFixture() {
  const markup = readFileSync(new URL("../../capture/www/index.html", import.meta.url), "utf8");
  const elements = Object.fromEntries([...markup.matchAll(/\bid="([^"]+)"/g)].map(match => [match[1], new Element()]));
  elements.filter.value = "all";
  return {getElementById(id) { assert.ok(elements[id], `Missing DOM node ${id}`); return elements[id]; }, createElement() { return new Element(); }};
}
const tick = () => new Promise(resolve => setImmediate(resolve));
test("DOM recovers from failed polling and displays last-known status without asserting live", async () => {
  const doc = documentFixture(); let fail = false, stamp = NOW;
  const controller = mount(doc, async () => { if (fail) throw new Error("offline"); return {ok: true, json: async () => snapshot()}; }, () => stamp);
  try {
    await tick(); assert.equal(doc.getElementById("state").textContent, "Running");
    assert.match(doc.getElementById("reuse").textContent, /2 scheduled.*4 configurations/);
    assert.equal(doc.getElementById("runs").children.length, 2);
    fail = true; await controller.poll();
    assert.equal(doc.getElementById("state").textContent, "Connection unavailable");
    assert.match(doc.getElementById("snapshot-time").textContent, /Last known Running/);
    assert.equal(doc.getElementById("runs").children[0].children[1].textContent, "Pending");
    fail = false; await controller.poll(); assert.equal(doc.getElementById("state").textContent, "Running");
    stamp += 600001; controller.render(); assert.equal(doc.getElementById("state").textContent, "Worker offline");
  } finally { controller.destroy(); }
});
test("DOM treats strings as text and explains empty filter and empty queue", async () => {
  const doc = documentFixture(), data = snapshot(); data.entries[0].reason = '<img src=x onerror="alert(1)">';
  const controller = mount(doc, async () => ({ok: true, json: async () => data}), () => NOW);
  try {
    await tick(); assert.match(doc.getElementById("runs").textContent, /<img src=x/);
    doc.getElementById("search").value = "no matching class"; controller.render();
    assert.equal(doc.getElementById("runs").textContent, "No runs match these filters.");
    doc.getElementById("search").value = "";
    data.entries = []; data.current = null; data.summary = null;
    for (const key of Object.keys(data.counts)) data.counts[key] = 0;
    await controller.poll(); assert.match(doc.getElementById("runs").textContent, /no scheduled runs/);
    assert.equal(doc.getElementById("bar").attributes["aria-valuenow"], "0");
  } finally { controller.destroy(); }
});
