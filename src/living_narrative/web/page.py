"""Single static HTML page for the web UI (docs/issues/020 skeleton, 021-022 story pane + controls).

Deliberately no build step / frontend framework: one inline page, vanilla ``fetch``. Whether to
bring in a framework is a call for a later Track B issue once the surface grows.
"""

INDEX_HTML = """\
<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>Living Narrative Engine</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 840px; margin: 2rem auto; padding: 0 1rem; }
  select, button, input { font-size: 1rem; padding: 0.3rem 0.6rem; margin-right: 0.5rem; }
  input[type=number] { width: 4rem; }
  #status { font-size: 0.9rem; color: #444; }
  .char { display: inline-block; margin-right: 0.75rem; }
  .controls { margin: 0.75rem 0; display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; }
  .controls .group { display: flex; align-items: center; gap: 0.2rem; padding-right: 0.75rem;
    border-right: 1px solid #ddd; }
  .controls .group:last-child { border-right: none; }
  .turn-block { border: 1px solid #ddd; border-radius: 6px; padding: 0.75rem 1rem;
    margin-bottom: 0.75rem; }
  .turn-block .head { display: flex; justify-content: space-between; align-items: baseline;
    margin-bottom: 0.4rem; }
  .turn-block pre { white-space: pre-wrap; margin: 0; background: none; padding: 0; }
  .badge { font-size: 0.75rem; padding: 0.1rem 0.5rem; border-radius: 999px; color: white; }
  .badge-applied { background: #2e7d32; }
  .badge-pending_review, .badge-stopped_for_review { background: #ef6c00; }
  .badge-failed { background: #c62828; }
  .badge-unknown { background: #757575; }
</style>
</head>
<body>
<h1>Living Narrative Engine</h1>
<div>
  <select id="project-select"></select>
  <span id="turn-count"></span>
</div>
<div class="controls">
  <div class="group">
    <button id="turn-button" disabled>次のターン</button>
  </div>
  <div class="group">
    <input id="auto-turns" type="number" min="1" value="5">
    <button id="auto-button" disabled>auto実行</button>
    <button id="stop-button" disabled>停止</button>
  </div>
  <div class="group">
    <span>review:</span>
    <button id="review-accept-button" disabled>accept_all</button>
    <button id="review-reject-button" disabled>reject_all</button>
  </div>
</div>
<p id="status"></p>
<div id="characters"></div>
<h2>Story</h2>
<div id="story"></div>
<script>
const select = document.getElementById("project-select");
const turnCountEl = document.getElementById("turn-count");
const turnButton = document.getElementById("turn-button");
const autoTurnsInput = document.getElementById("auto-turns");
const autoButton = document.getElementById("auto-button");
const stopButton = document.getElementById("stop-button");
const reviewAcceptButton = document.getElementById("review-accept-button");
const reviewRejectButton = document.getElementById("review-reject-button");
const statusEl = document.getElementById("status");
const charactersEl = document.getElementById("characters");
const storyEl = document.getElementById("story");

let pollHandle = null;

function currentProject() {
  return select.value;
}

function statusBadge(status) {
  const cls = status ? `badge-${status}` : "badge-unknown";
  return `<span class="badge ${cls}">${status || "unknown"}</span>`;
}

async function loadProjects() {
  const res = await fetch("/api/projects");
  const projects = await res.json();
  select.innerHTML = "";
  for (const p of projects) {
    const opt = document.createElement("option");
    opt.value = p.name;
    opt.textContent = p.title || p.name;
    select.appendChild(opt);
  }
  const hasProjects = projects.length > 0;
  turnButton.disabled = !hasProjects;
  autoButton.disabled = !hasProjects;
  if (hasProjects) await refresh();
}

async function refresh() {
  const name = currentProject();
  if (!name) return;
  const [statusRes, turnsRes, runStatusRes] = await Promise.all([
    fetch(`/api/project/${encodeURIComponent(name)}/status`),
    fetch(`/api/project/${encodeURIComponent(name)}/turns`),
    fetch(`/api/project/${encodeURIComponent(name)}/run_status`),
  ]);
  const status = await statusRes.json();
  const turns = await turnsRes.json();
  const runStatus = await runStatusRes.json();

  turnCountEl.textContent = `(turn ${status.current_turn})`;
  statusEl.textContent =
    `turn ${status.current_turn}` +
    (status.scene ? ` — ${status.scene.location} (${status.scene.mood})` : "") +
    (status.pending_review ? ` — レビュー待ち (turn ${status.pending_review_turn})` : "") +
    (runStatus.running ? " — 実行中..." : "");
  charactersEl.innerHTML = status.characters
    .map((c) => `<span class="char">${c.name} [${c.status}]</span>`)
    .join("");

  storyEl.innerHTML = turns
    .map(
      (t) => `<div class="turn-block">
        <div class="head"><strong>turn ${t.turn}</strong> ${statusBadge(t.status)}</div>
        <pre>${(t.text || "").replace(/</g, "&lt;")}</pre>
      </div>`
    )
    .reverse()
    .join("");

  const reviewPending = status.pending_review;
  reviewAcceptButton.disabled = !reviewPending;
  reviewRejectButton.disabled = !reviewPending;
  turnButton.disabled = runStatus.running || reviewPending;
  autoButton.disabled = runStatus.running || reviewPending;
  stopButton.disabled = !runStatus.running;

  if (runStatus.running && pollHandle === null) {
    pollHandle = setInterval(poll, 1000);
  } else if (!runStatus.running && pollHandle !== null) {
    clearInterval(pollHandle);
    pollHandle = null;
  }
}

async function poll() {
  await refresh();
}

select.addEventListener("change", refresh);

turnButton.addEventListener("click", async () => {
  const name = currentProject();
  if (!name) return;
  turnButton.disabled = true;
  try {
    await fetch(`/api/project/${encodeURIComponent(name)}/turn`, { method: "POST" });
    await refresh();
  } finally {
    turnButton.disabled = false;
  }
});

autoButton.addEventListener("click", async () => {
  const name = currentProject();
  if (!name) return;
  const turns = parseInt(autoTurnsInput.value, 10) || 1;
  await fetch(`/api/project/${encodeURIComponent(name)}/auto`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ turns }),
  });
  await refresh();
});

stopButton.addEventListener("click", async () => {
  const name = currentProject();
  if (!name) return;
  await fetch(`/api/project/${encodeURIComponent(name)}/stop`, { method: "POST" });
  await refresh();
});

async function submitReview(decision) {
  const name = currentProject();
  if (!name) return;
  await fetch(`/api/project/${encodeURIComponent(name)}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision }),
  });
  await refresh();
}

reviewAcceptButton.addEventListener("click", () => submitReview("accept_all"));
reviewRejectButton.addEventListener("click", () => submitReview("reject_all"));

loadProjects();
</script>
</body>
</html>
"""
