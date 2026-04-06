const settingsKey = "interactive-seminar-settings";

const state = {
  manifest: null,
  selectedBlockId: null,
  mode: "seminar",
};

function loadSettings() {
  try {
    return JSON.parse(localStorage.getItem(settingsKey) || "{}");
  } catch {
    return {};
  }
}

function saveSettings(settings) {
  localStorage.setItem(settingsKey, JSON.stringify(settings));
}

function getSettings() {
  return {
    apiKey: document.getElementById("api-key").value,
    model: document.getElementById("model-name").value || "GigaChat",
  };
}

function persistCurrentSettings() {
  saveSettings(getSettings());
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function blockLookup() {
  const map = new Map();
  for (const part of state.manifest.parts) {
    for (const block of part.blocks) {
      map.set(block.id, block);
    }
  }
  return map;
}

function findBlock(blockId) {
  return blockLookup().get(blockId);
}

function renderNavigation() {
  const root = document.getElementById("navigation");
  root.innerHTML = "";
  for (const part of state.manifest.parts) {
    const partEl = document.createElement("section");
    partEl.className = "nav-part";
    partEl.innerHTML = `<h3>${escapeHtml(part.title)}</h3>`;
    for (const block of part.blocks) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `nav-button${block.id === state.selectedBlockId ? " active" : ""}`;
      button.textContent = block.title;
      button.addEventListener("click", () => {
        state.selectedBlockId = block.id;
        renderNavigation();
        renderBlock();
      });
      partEl.appendChild(button);
    }
    root.appendChild(partEl);
  }
}

function renderBlock() {
  const block = findBlock(state.selectedBlockId);
  if (!block) {
    return;
  }

  const content = document.getElementById("block-content");
  content.innerHTML = `
    <p class="eyebrow">${escapeHtml(block.kind)}</p>
    <h2>${escapeHtml(block.title)}</h2>
    <div class="instructions">${block.instructions_html || "<p>No instructions for this block.</p>"}</div>
  `;

  const runner = document.getElementById("block-runner");
  const editableFields = (block.editable_fields || [])
    .map(
      (field) => `
        <div class="field-group">
          <label class="field-label" for="field-${escapeHtml(field.name)}">
            <span>${escapeHtml(field.name)}</span>
            <span class="field-type">editable</span>
          </label>
          <textarea id="field-${escapeHtml(field.name)}" data-field="${escapeHtml(field.name)}" rows="6">${escapeHtml(field.value || "")}</textarea>
        </div>
      `
    )
    .join("");

  const readonlyFields = (block.readonly_fields || [])
    .map(
      (field) => `
        <details>
          <summary>${escapeHtml(field.name)}</summary>
          <div class="output-block">${escapeHtml(field.value || "")}</div>
        </details>
      `
    )
    .join("");

  runner.innerHTML = `
    <h2>Runner</h2>
    ${editableFields || "<p>No editable fields for this block.</p>"}
    <button id="run-block" type="button">Run Block</button>
    ${readonlyFields ? `<div class="readonly-card"><h3>Read-only Context</h3>${readonlyFields}</div>` : ""}
    ${
      block.hint
        ? `<div class="hint-card"><h3>Hint</h3><div class="instructions">${block.hint_html || ""}</div></div>`
        : ""
    }
    ${
      block.solution
        ? `<div class="solution-card"><h3>Possible Solution</h3><div class="instructions">${block.solution_html || ""}</div></div>`
        : ""
    }
    <div id="run-result"></div>
  `;

  document.getElementById("run-block").addEventListener("click", () => runCurrentBlock(block));
}

async function runCurrentBlock(block) {
  const resultRoot = document.getElementById("run-result");
  resultRoot.innerHTML = "<p>Running...</p>";
  const settings = getSettings();
  persistCurrentSettings();

  const overrides = {};
  document.querySelectorAll("[data-field]").forEach((element) => {
    overrides[element.dataset.field] = { __raw__: element.value };
  });

  const response = await fetch(`/api/run/block/${block.id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      credentials: settings.apiKey,
      model: settings.model,
      overrides,
    }),
  });
  const body = await response.json();
  if (!response.ok) {
    resultRoot.innerHTML = `<div class="result-card"><h3>Error</h3><div class="output-block">${escapeHtml(body.detail || "Unknown error")}</div></div>`;
    return;
  }

  const gradeHtml = body.grade
    ? `<div class="grade-pill ${body.grade.passed ? "grade-pass" : "grade-fail"}">${body.grade.passed ? "PASS" : "FAIL"}</div>`
    : "";
  const toolTraceHtml = body.tool_trace
    ? `<div class="tool-card"><h3>Tool Trace</h3><div class="output-block">${escapeHtml(JSON.stringify(body.tool_trace, null, 2))}</div></div>`
    : "";

  resultRoot.innerHTML = `
    <div class="result-card">
      <h3>Execution Result</h3>
      ${gradeHtml}
      <h4>Prompt Preview</h4>
      <div class="output-block">${escapeHtml(body.prompt_preview || "")}</div>
      <h4>Response</h4>
      <div class="output-block">${escapeHtml(body.response || "")}</div>
      <h4>Stdout</h4>
      <div class="output-block">${escapeHtml(body.stdout || "")}</div>
    </div>
    ${toolTraceHtml}
  `;
}

async function testConnection() {
  const status = document.getElementById("connection-status");
  status.textContent = "Testing...";
  const settings = getSettings();
  persistCurrentSettings();

  const response = await fetch("/api/session/test-connection", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      credentials: settings.apiKey,
      model: settings.model,
    }),
  });
  const body = await response.json();
  status.textContent = response.ok ? `OK: ${body.response}` : `Error: ${body.detail}`;
}

async function runSandbox() {
  const output = document.getElementById("sandbox-output");
  output.innerHTML = "<p>Running...</p>";
  const settings = getSettings();
  persistCurrentSettings();
  const stopSequences = document
    .getElementById("sandbox-stop")
    .value.split(",")
    .map((value) => value.trim())
    .filter(Boolean);

  const response = await fetch("/api/run/sandbox", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      credentials: settings.apiKey,
      model: settings.model,
      messages: [
        {
          role: "user",
          content: document.getElementById("sandbox-user").value,
        },
      ],
      system_prompt: document.getElementById("sandbox-system").value,
      prefill: document.getElementById("sandbox-prefill").value,
      stop_sequences: stopSequences,
    }),
  });
  const body = await response.json();
  if (!response.ok) {
    output.innerHTML = `<div class="output-block">${escapeHtml(body.detail || "Unknown error")}</div>`;
    return;
  }
  output.innerHTML = `
    <h3>Response</h3>
    <div class="output-block">${escapeHtml(body.response || "")}</div>
  `;
}

function setMode(mode) {
  state.mode = mode;
  document.getElementById("seminar-view").classList.toggle("hidden", mode !== "seminar");
  document.getElementById("sandbox-view").classList.toggle("hidden", mode !== "sandbox");
  document.getElementById("show-seminar").classList.toggle("active", mode === "seminar");
  document.getElementById("show-sandbox").classList.toggle("active", mode === "sandbox");
}

async function loadManifest() {
  const response = await fetch("/api/manifest");
  state.manifest = await response.json();
  const firstBlock = state.manifest.parts.flatMap((part) => part.blocks)[0];
  state.selectedBlockId = firstBlock ? firstBlock.id : null;
  renderNavigation();
  renderBlock();
}

function hydrateSettings() {
  const settings = loadSettings();
  document.getElementById("api-key").value = settings.apiKey || "";
  document.getElementById("model-name").value = settings.model || "GigaChat";
}

document.addEventListener("DOMContentLoaded", async () => {
  hydrateSettings();
  document.getElementById("test-connection").addEventListener("click", testConnection);
  document.getElementById("run-sandbox").addEventListener("click", runSandbox);
  document.getElementById("show-seminar").addEventListener("click", () => setMode("seminar"));
  document.getElementById("show-sandbox").addEventListener("click", () => setMode("sandbox"));
  document.getElementById("api-key").addEventListener("change", persistCurrentSettings);
  document.getElementById("model-name").addEventListener("change", persistCurrentSettings);
  await loadManifest();
});
