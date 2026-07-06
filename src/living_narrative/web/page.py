"""Single static HTML page for the web UI skeleton (docs/issues/020, step 3.5).

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
  body { font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; }
  select, button { font-size: 1rem; padding: 0.3rem 0.6rem; margin-right: 0.5rem; }
  pre { white-space: pre-wrap; background: #f4f4f4; padding: 1rem; border-radius: 4px; }
  #status { font-size: 0.9rem; color: #444; }
  .char { display: inline-block; margin-right: 0.75rem; }
</style>
</head>
<body>
<h1>Living Narrative Engine</h1>
<div>
  <select id="project-select"></select>
  <button id="turn-button" disabled>次のターン</button>
</div>
<p id="status"></p>
<div id="characters"></div>
<h2>Narration</h2>
<pre id="narration"></pre>
<script>
const select = document.getElementById("project-select");
const turnButton = document.getElementById("turn-button");
const statusEl = document.getElementById("status");
const charactersEl = document.getElementById("characters");
const narrationEl = document.getElementById("narration");

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
  turnButton.disabled = projects.length === 0;
  if (projects.length > 0) await refresh();
}

async function refresh() {
  const name = select.value;
  if (!name) return;
  const [statusRes, narrationRes] = await Promise.all([
    fetch(`/api/project/${encodeURIComponent(name)}/status`),
    fetch(`/api/project/${encodeURIComponent(name)}/narration`),
  ]);
  const status = await statusRes.json();
  statusEl.textContent =
    `turn ${status.current_turn}` +
    (status.scene ? ` — ${status.scene.location} (${status.scene.mood})` : "") +
    (status.pending_review ? " — レビュー待ち" : "");
  charactersEl.innerHTML = status.characters
    .map((c) => `<span class="char">${c.name} [${c.status}]</span>`)
    .join("");
  narrationEl.textContent = await narrationRes.text();
}

select.addEventListener("change", refresh);
turnButton.addEventListener("click", async () => {
  const name = select.value;
  if (!name) return;
  turnButton.disabled = true;
  try {
    await fetch(`/api/project/${encodeURIComponent(name)}/turn`, { method: "POST" });
    await refresh();
  } finally {
    turnButton.disabled = false;
  }
});

loadProjects();
</script>
</body>
</html>
"""
