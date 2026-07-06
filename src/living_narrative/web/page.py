"""Single static HTML page for the web UI (docs/issues/020 skeleton, 021-022 story pane +
controls, 023 intervention input).

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
  select, button, input, textarea { font-size: 1rem; padding: 0.3rem 0.6rem; margin-right: 0.5rem; }
  input[type=number] { width: 4rem; }
  textarea { font-family: inherit; vertical-align: top; }
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
  .badge-accepted { background: #2e7d32; }
  .badge-rejected { background: #c62828; }
  .intervention-panel { border: 1px solid #ddd; border-radius: 6px; padding: 0.75rem 1rem;
    margin: 0.75rem 0; }
  .intervention-panel h3 { margin-top: 0; }
  .intervention-panel .group { margin-bottom: 0.5rem; flex-wrap: wrap; }
  #intervention-freetext { width: 100%; box-sizing: border-box; margin-bottom: 0.4rem; }
  .intervention-entry { padding: 0.3rem 0; font-size: 0.9rem; }
  .intervention-entry .badge { margin-right: 0.4rem; }
  .badge-gm_only { background: #4a148c; }
  .badge-canon { background: #01579b; }
  .badge-character { background: #00695c; }
  .badge-scene { background: #ef6c00; }
  .badge-reader { background: #2e7d32; }
  #gm-panel { display: none; border: 1px solid #ddd; border-radius: 6px; padding: 0.75rem 1rem;
    margin: 0.75rem 0; }
  #gm-panel.open { display: block; }
  #gm-panel h3 { margin-top: 1rem; margin-bottom: 0.3rem; }
  #gm-panel h3:first-child { margin-top: 0; }
  .gm-char-card { border: 1px solid #ddd; border-radius: 6px; padding: 0.5rem 0.75rem;
    margin-bottom: 0.5rem; }
  .gm-char-card .emotion { font-size: 0.85rem; color: #444; margin-right: 0.5rem; }
  .gm-secret { font-size: 0.85rem; color: #6a1b9a; }
  .gm-threat { padding: 0.3rem 0; font-size: 0.9rem; }
  .gm-scene, .gm-thread { border-bottom: 1px solid #eee; padding: 0.4rem 0; font-size: 0.9rem; }
  .gm-timeline-entry { padding: 0.3rem 0; font-size: 0.85rem; }
  .gm-timeline-entry .badge { margin-right: 0.3rem; }
  #gm-turn-detail pre { white-space: pre-wrap; font-size: 0.8rem; background: #f5f5f5;
    padding: 0.5rem; border-radius: 4px; }
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
  <div class="group">
    <button id="gm-toggle-button" disabled>GMビュー</button>
  </div>
</div>
<div class="intervention-panel">
  <h3>介入</h3>
  <div class="group">
    <textarea id="intervention-freetext" rows="2" placeholder="自由文で介入を記述"></textarea>
  </div>
  <div class="group">
    <button id="intervention-freetext-button" disabled>介入して次ターン</button>
  </div>
  <div class="group">
    <select id="intervention-type"></select>
    <select id="intervention-target-kind">
      <option value="world">world</option>
      <option value="character">character</option>
      <option value="scene">scene</option>
      <option value="reader_state">reader_state</option>
      <option value="canon">canon</option>
      <option value="gm_vault">gm_vault</option>
      <option value="relationship">relationship</option>
      <option value="roll">roll</option>
    </select>
    <input id="intervention-target-id" type="text" placeholder="target id(省略可)">
    <input id="intervention-content" type="text" placeholder="内容">
    <select id="intervention-visibility">
      <option value="gm_only">gm_only</option>
      <option value="canon">canon</option>
      <option value="character">character</option>
      <option value="scene">scene</option>
      <option value="reader">reader</option>
    </select>
    <button id="intervention-draft-button" disabled>構造化介入で次ターン</button>
  </div>
  <div id="intervention-history"></div>
</div>
<p id="status"></p>
<div id="characters"></div>
<h2>Story</h2>
<div id="story"></div>
<div id="gm-panel">
  <h3>キャラクター(GM視点)</h3>
  <div id="gm-characters"></div>
  <h3>世界・脅威</h3>
  <div id="gm-world"></div>
  <h3>シーン</h3>
  <div id="gm-scenes"></div>
  <h3>未解決スレッド</h3>
  <div id="gm-threads"></div>
  <h3>タイムライン</h3>
  <div id="gm-timeline"></div>
  <h3>ターン詳細</h3>
  <div class="group">
    <input id="gm-turn-input" type="number" min="1" value="1">
    <button id="gm-turn-button">取得</button>
  </div>
  <div id="gm-turn-detail"></div>
</div>
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
const interventionFreetextInput = document.getElementById("intervention-freetext");
const interventionFreetextButton = document.getElementById("intervention-freetext-button");
const interventionTypeSelect = document.getElementById("intervention-type");
const interventionTargetKindSelect = document.getElementById("intervention-target-kind");
const interventionTargetIdInput = document.getElementById("intervention-target-id");
const interventionContentInput = document.getElementById("intervention-content");
const interventionVisibilitySelect = document.getElementById("intervention-visibility");
const interventionDraftButton = document.getElementById("intervention-draft-button");
const interventionHistoryEl = document.getElementById("intervention-history");
const gmToggleButton = document.getElementById("gm-toggle-button");
const gmPanelEl = document.getElementById("gm-panel");
const gmCharactersEl = document.getElementById("gm-characters");
const gmWorldEl = document.getElementById("gm-world");
const gmScenesEl = document.getElementById("gm-scenes");
const gmThreadsEl = document.getElementById("gm-threads");
const gmTimelineEl = document.getElementById("gm-timeline");
const gmTurnInput = document.getElementById("gm-turn-input");
const gmTurnButton = document.getElementById("gm-turn-button");
const gmTurnDetailEl = document.getElementById("gm-turn-detail");

let pollHandle = null;
let gmOpen = false;

function currentProject() {
  return select.value;
}

function statusBadge(status) {
  const cls = status ? `badge-${status}` : "badge-unknown";
  return `<span class="badge ${cls}">${status || "unknown"}</span>`;
}

function renderInterventionEntry(entry, accepted) {
  const badge = accepted
    ? '<span class="badge badge-accepted">accepted</span>'
    : '<span class="badge badge-rejected">rejected</span>';
  const detail = accepted
    ? `${entry.type} → ${entry.target ? entry.target.kind : ""}` +
      `${entry.target && entry.target.id ? ":" + entry.target.id : ""} — ${entry.content || ""}`
    : `${entry.type} — ${entry.requested_user_mode}には未許可` +
      ` (許可: ${(entry.allowed_user_modes || []).join(", ") || "なし"})`;
  return `<div class="intervention-entry">${badge}${detail}</div>`;
}

function renderInterventionHistory(interventionsData) {
  const lastTurn = interventionsData.last_turn;
  if (!lastTurn) {
    interventionHistoryEl.innerHTML = "<p>介入履歴なし</p>";
    return;
  }
  const accepted = (lastTurn.interventions || []).map((e) => renderInterventionEntry(e, true));
  const rejected = (lastTurn.rejections || []).map((e) => renderInterventionEntry(e, false));
  const body = accepted.concat(rejected).join("") || "<p>介入なし</p>";
  interventionHistoryEl.innerHTML = `<h4>直近ターン(turn ${lastTurn.turn})の介入</h4>${body}`;
}

function visibilityBadge(visibility) {
  const cls = visibility ? `badge-${visibility}` : "badge-unknown";
  return `<span class="badge ${cls}">${visibility || "unknown"}</span>`;
}

function renderGmCharacters(characters) {
  gmCharactersEl.innerHTML = characters
    .map((c) => {
      const emotions = Object.entries(c.emotions || {})
        .map((entry) => {
          const [name, value] = entry;
          const baseline = (c.emotions_baseline || {})[name];
          const baselineNote = baseline !== undefined ? ` (baseline ${baseline})` : "";
          return `<span class="emotion">${name}: ${value}${baselineNote}</span>`;
        })
        .join("");
      const secrets = (c.secrets || [])
        .map((s) => `<div class="gm-secret">secret: ${s}</div>`)
        .join("");
      const privateMind = (c.private_mind || [])
        .map((p) => `<div class="gm-secret">private_mind: ${p}</div>`)
        .join("");
      const relationships = (c.relationships || [])
        .map(
          (r) =>
            `<div class="emotion">→ ${r.to}: trust=${r.trust} affection=${r.affection} ` +
            `tension=${r.tension} suspicion=${r.suspicion}</div>`
        )
        .join("");
      return `<div class="gm-char-card">
        <strong>${c.name}</strong> [${c.status}]
        <div>${emotions}</div>
        ${secrets}${privateMind}${relationships}
      </div>`;
    })
    .join("");
}

function renderGmWorld(world) {
  const threats = (world.threats || [])
    .map((t) => {
      const next = t.next_stage
        ? `次の閾値: ${t.next_stage.at} — ${t.next_stage.text}`
        : "全ての閾値を超過";
      return (
        `<div class="gm-threat"><strong>${t.name}</strong> ` +
        `pressure=${t.pressure} — ${next}</div>`
      );
    })
    .join("");
  gmWorldEl.innerHTML = `<p>${world.world.name}: ${world.world.summary}</p>${threats}`;

  gmScenesEl.innerHTML = (world.scenes || [])
    .map((s) => {
      const hidden = (s.hidden_facts || [])
        .map((f) => `<div class="gm-secret">${visibilityBadge(f.visibility)} ${f.text}</div>`)
        .join("");
      return `<div class="gm-scene">
        <strong>${s.location}</strong> [${s.status}] ${s.mood}
        <div>${s.summary || ""}</div>
        ${hidden}
      </div>`;
    })
    .join("");
}

function renderGmThreads(data) {
  const threads = (data.threads || [])
    .map(
      (t) =>
        `<div class="gm-thread"><strong>${t.description}</strong> [${t.status}] ` +
        `related_events=${t.related_event_count}` +
        (t.opened_turn !== null && t.opened_turn !== undefined
          ? ` opened@turn ${t.opened_turn}`
          : "") +
        `</div>`
    )
    .join("");
  const summaries = (data.memory_summaries || [])
    .map((m) => `<div class="gm-thread">up_to_turn ${m.up_to_turn}: ${m.text}</div>`)
    .join("");
  gmThreadsEl.innerHTML = (threads || "<p>未解決スレッドなし</p>") + summaries;
}

function renderGmTimeline(entries) {
  gmTimelineEl.innerHTML = entries
    .map((entry) => {
      const events = (entry.events || [])
        .map(
          (e) =>
            `<div class="gm-timeline-entry">${visibilityBadge(e.visibility)} ${e.text}</div>`
        )
        .join("");
      return `<div><strong>turn ${entry.turn}</strong>${events}</div>`;
    })
    .reverse()
    .join("");
}

function renderGmTurnDetail(detail) {
  gmTurnDetailEl.innerHTML = `<pre>${JSON.stringify(detail, null, 2).replace(/</g, "&lt;")}</pre>`;
}

async function loadGm() {
  const name = currentProject();
  if (!name || !gmOpen) return;
  const [charsRes, worldRes, threadsRes, timelineRes] = await Promise.all([
    fetch(`/api/project/${encodeURIComponent(name)}/gm/characters`),
    fetch(`/api/project/${encodeURIComponent(name)}/gm/world`),
    fetch(`/api/project/${encodeURIComponent(name)}/gm/threads`),
    fetch(`/api/project/${encodeURIComponent(name)}/gm/timeline`),
  ]);
  renderGmCharacters(await charsRes.json());
  renderGmWorld(await worldRes.json());
  renderGmThreads(await threadsRes.json());
  renderGmTimeline(await timelineRes.json());
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
  gmToggleButton.disabled = !hasProjects;
  if (hasProjects) await refresh();
}

async function refresh() {
  const name = currentProject();
  if (!name) return;
  const [statusRes, turnsRes, runStatusRes, permissionsRes, interventionsRes] = await Promise.all([
    fetch(`/api/project/${encodeURIComponent(name)}/status`),
    fetch(`/api/project/${encodeURIComponent(name)}/turns`),
    fetch(`/api/project/${encodeURIComponent(name)}/run_status`),
    fetch(`/api/project/${encodeURIComponent(name)}/permissions`),
    fetch(`/api/project/${encodeURIComponent(name)}/interventions`),
  ]);
  const status = await statusRes.json();
  const turns = await turnsRes.json();
  const runStatus = await runStatusRes.json();
  const permissions = await permissionsRes.json();
  const interventionsData = await interventionsRes.json();

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

  const selectedType = interventionTypeSelect.value;
  interventionTypeSelect.innerHTML = permissions.allowed_types
    .map((t) => `<option value="${t}">${t}</option>`)
    .join("");
  if (permissions.allowed_types.includes(selectedType)) {
    interventionTypeSelect.value = selectedType;
  }
  const interventionBlocked = runStatus.running || reviewPending;
  interventionFreetextButton.disabled = interventionBlocked;
  interventionDraftButton.disabled = interventionBlocked || permissions.allowed_types.length === 0;
  renderInterventionHistory(interventionsData);

  if (gmOpen) await loadGm();

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

interventionFreetextButton.addEventListener("click", async () => {
  const name = currentProject();
  const freeText = interventionFreetextInput.value.trim();
  if (!name || !freeText) return;
  interventionFreetextButton.disabled = true;
  try {
    await fetch(`/api/project/${encodeURIComponent(name)}/turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ free_text: freeText }),
    });
    interventionFreetextInput.value = "";
    await refresh();
  } finally {
    interventionFreetextButton.disabled = false;
  }
});

interventionDraftButton.addEventListener("click", async () => {
  const name = currentProject();
  const content = interventionContentInput.value.trim();
  if (!name || !content) return;
  const targetId = interventionTargetIdInput.value.trim();
  const draft = {
    type: interventionTypeSelect.value,
    target: { kind: interventionTargetKindSelect.value, ...(targetId ? { id: targetId } : {}) },
    content,
    visibility: interventionVisibilitySelect.value,
  };
  interventionDraftButton.disabled = true;
  try {
    await fetch(`/api/project/${encodeURIComponent(name)}/turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ drafts: [draft] }),
    });
    interventionContentInput.value = "";
    interventionTargetIdInput.value = "";
    await refresh();
  } finally {
    interventionDraftButton.disabled = false;
  }
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

gmToggleButton.addEventListener("click", async () => {
  gmOpen = !gmOpen;
  gmPanelEl.classList.toggle("open", gmOpen);
  if (gmOpen) await loadGm();
});

gmTurnButton.addEventListener("click", async () => {
  const name = currentProject();
  const turn = parseInt(gmTurnInput.value, 10) || 1;
  if (!name) return;
  const res = await fetch(`/api/project/${encodeURIComponent(name)}/gm/turn/${turn}`);
  if (res.status === 404) {
    gmTurnDetailEl.innerHTML = `<p>turn ${turn} は見つかりません</p>`;
    return;
  }
  renderGmTurnDetail(await res.json());
});

loadProjects();
</script>
</body>
</html>
"""
