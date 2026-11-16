import json
from pathlib import Path

DATA_JSON = Path("/home/axe/.t3/userdata/providers/antigravity/ac0a3dfd6dddb20962cecff6ee5fe65e19d3923be20e52c5ab52ff877f7e4c32/antigravity-acp/brain/58beaab0-81bd-450c-9797-114f5ec38335/scratch/overview_data.json")
OUT_HTML = Path("/home/axe/misc/gaggiuino/docs/delongui-visual-overview.html")

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>DeLonghi Gaggiuino HMI — Original vs New Visual Overview</title>
<style>
  :root {
    color-scheme: dark light;
    --bg: var(--background, light-dark(#ffffff, #0e131a));
    --fg: var(--foreground, light-dark(#0f172a, #e8edf4));
    --mut: var(--muted-foreground, light-dark(#475569, #94a3b8));
    --crd: var(--card, light-dark(#f8fafc, #141c26));
    --pop: var(--popover, light-dark(#ffffff, #192330));
    --sec: var(--secondary, light-dark(#e2e8f0, #1d2836));
    --bdr: var(--border, light-dark(#cbd5e1, #283546));
    --pri: var(--primary, #0284c7);
    --pri-fg: var(--primary-foreground, #ffffff);
    --acc: var(--warning, #d97706);
    --acc-fg: var(--warning-foreground, #140c02);
    --suc: var(--success, #22c55e);
    --inf: var(--info, #38bdf8);
    --rad: var(--radius, 10px);
    --mono: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace);
    --sans: var(--font-sans, system-ui, -apple-system, Segoe UI, Roboto, sans-serif);
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0;
    padding: 0;
    font-family: var(--sans);
    color: var(--fg);
    line-height: 1.4;
  }
  .root {
    width: 100%;
    max-width: 1120px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    background: var(--crd);
    border: 1px solid var(--bdr);
    border-radius: var(--rad);
    padding: 10px 12px;
  }
  .toolbar-left {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }
  .title-text {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.02em;
  }
  .sub-text {
    font-size: 11px;
    color: var(--mut);
  }
  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
  }
  .btn {
    appearance: none;
    border: 1px solid var(--bdr);
    background: var(--sec);
    color: var(--fg);
    border-radius: 7px;
    padding: 5px 10px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    transition: border-color 0.12s, background 0.12s;
  }
  .btn:hover { border-color: var(--pri); }
  .btn.active {
    background: var(--pri);
    color: var(--pri-fg);
    border-color: var(--pri);
  }
  .toggle-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    color: var(--fg);
    background: var(--sec);
    border: 1px solid var(--bdr);
    border-radius: 7px;
    padding: 4px 9px;
    cursor: pointer;
    user-select: none;
  }
  .toggle-pill input { margin: 0; accent-color: var(--pri); cursor: pointer; }
  .nav-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    background: var(--crd);
    border: 1px solid var(--bdr);
    border-radius: var(--rad);
    padding: 8px;
  }
  .nav-pill {
    appearance: none;
    border: 1px solid var(--bdr);
    background: var(--sec);
    color: var(--fg);
    border-radius: 6px;
    padding: 3px 7px;
    font-size: 11px;
    font-family: var(--mono);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
  .nav-pill:hover { border-color: var(--pri); }
  .nav-pill.active {
    background: var(--pri);
    color: var(--pri-fg);
    border-color: var(--pri);
    font-weight: 700;
  }
  .nav-pill .badge-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--acc);
    display: none;
  }
  .nav-pill.has-notes .badge-dot { display: inline-block; }

  .screen-card {
    background: var(--crd);
    border: 1px solid var(--bdr);
    border-radius: var(--rad);
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .screen-hdr {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    justify-content: space-between;
    gap: 6px;
    border-bottom: 1px solid var(--bdr);
    padding-bottom: 7px;
  }
  .screen-hdr-main {
    display: flex;
    align-items: baseline;
    gap: 8px;
    flex-wrap: wrap;
  }
  .screen-code {
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 5px;
    background: var(--sec);
    border: 1px solid var(--bdr);
    color: var(--pri);
  }
  .screen-title {
    font-size: 14px;
    font-weight: 700;
  }
  .screen-desc {
    font-size: 11px;
    color: var(--mut);
  }
  .pair-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }
  @media (max-width: 620px) {
    .pair-grid { grid-template-columns: 1fr; }
  }
  .side-col {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }
  .side-label {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 11px;
    font-weight: 600;
    color: var(--mut);
  }
  .side-tag {
    font-family: var(--mono);
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 4px;
    border: 1px solid var(--bdr);
    background: var(--sec);
  }
  .side-tag.orig { color: var(--acc); }
  .side-tag.new { color: var(--pri); }

  .stage {
    position: relative;
    width: 100%;
    aspect-ratio: 4 / 3;
    background: #05070a;
    border: 1px solid var(--bdr);
    border-radius: 6px;
    overflow: hidden;
  }
  .stage img {
    display: block;
    width: 100%;
    height: 100%;
    image-rendering: pixelated;
    user-select: none;
    pointer-events: none;
  }
  .hitbox {
    position: absolute;
    border: 1px solid transparent;
    cursor: crosshair;
    transition: background 0.08s, border-color 0.08s;
  }
  .show-boxes .hitbox {
    border-color: rgba(56, 189, 248, 0.25);
  }
  .hitbox:hover, .hitbox.hovered {
    border: 1.5px solid #38bdf8;
    background: rgba(56, 189, 248, 0.18);
    box-shadow: inset 0 0 0 1px rgba(6, 19, 29, 0.65);
  }
  .hitbox.orig-side:hover, .hitbox.orig-side.hovered {
    border-color: #f59e0b;
    background: rgba(245, 158, 11, 0.18);
  }
  .hitbox.noted {
    border: 1.5px dashed #22c55e;
  }
  .id-chip {
    display: none;
    position: absolute;
    left: 1px;
    top: 1px;
    font-family: var(--mono);
    font-size: 8px;
    line-height: 1;
    padding: 1px 3px;
    border-radius: 3px;
    background: rgba(6, 19, 29, 0.88);
    color: #e8edf4;
    border: 1px solid rgba(56, 189, 248, 0.5);
    pointer-events: none;
    white-space: nowrap;
  }
  .show-ids .id-chip { display: block; }
  .hitbox:hover .id-chip, .hitbox.hovered .id-chip {
    display: block;
    background: #0284c7;
    color: #fff;
    border-color: #fff;
  }
  .hitbox.orig-side:hover .id-chip, .hitbox.orig-side.hovered .id-chip {
    background: #d97706;
  }

  .inspector {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    min-height: 44px;
    background: var(--pop);
    border: 1px solid var(--bdr);
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 12px;
  }
  .insp-left {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }
  .insp-id {
    font-family: var(--mono);
    font-weight: 700;
    font-size: 12px;
    padding: 2px 7px;
    border-radius: 5px;
    background: var(--pri);
    color: var(--pri-fg);
  }
  .insp-id.orig {
    background: var(--acc);
    color: #140c02;
  }
  .insp-mono {
    font-family: var(--mono);
    font-size: 11px;
  }
  .insp-meta {
    color: var(--mut);
    font-size: 11px;
  }
  .insp-hint {
    color: var(--mut);
    font-size: 11px;
  }

  .float-tip {
    position: fixed;
    z-index: 9999;
    pointer-events: none;
    display: none;
    background: rgba(14, 19, 26, 0.96);
    color: #f1f5f9;
    border: 1px solid #38bdf8;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 11px;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.45);
    max-width: 280px;
  }
  .float-tip.orig { border-color: #f59e0b; }
  .float-tip .ft-top {
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: var(--mono);
    font-weight: 700;
  }
  .float-tip .ft-sub {
    font-size: 10px;
    color: #94a3b8;
    font-family: var(--mono);
    margin-top: 1px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .feedback-panel {
    background: var(--crd);
    border: 1px solid var(--bdr);
    border-radius: var(--rad);
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .fb-hdr {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .fb-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .fb-row {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 8px;
    background: var(--sec);
    border: 1px solid var(--bdr);
    border-radius: 7px;
    padding: 5px 8px;
  }
  .fb-tag {
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 700;
    color: var(--pri);
    white-space: nowrap;
  }
  .fb-tag.orig { color: var(--acc); }
  .fb-input {
    width: 100%;
    background: var(--pop);
    color: var(--fg);
    border: 1px solid var(--bdr);
    border-radius: 5px;
    padding: 4px 7px;
    font-size: 12px;
    font-family: var(--sans);
  }
  .fb-input:focus { outline: 1px solid var(--pri); border-color: var(--pri); }
  .fb-del {
    appearance: none;
    background: transparent;
    border: 1px solid var(--bdr);
    color: var(--mut);
    border-radius: 5px;
    padding: 3px 7px;
    font-size: 11px;
    cursor: pointer;
  }
  .fb-del:hover { color: #f87171; border-color: #f87171; }
  .toast {
    position: fixed;
    bottom: 14px;
    right: 14px;
    z-index: 10000;
    background: #0284c7;
    color: #fff;
    padding: 6px 12px;
    border-radius: 7px;
    font-size: 12px;
    font-weight: 600;
    display: none;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35);
  }
  .comp-index {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    max-height: 110px;
    overflow-y: auto;
    padding-top: 4px;
  }
  .comp-chip {
    appearance: none;
    border: 1px solid var(--bdr);
    background: var(--sec);
    color: var(--fg);
    border-radius: 5px;
    padding: 2px 6px;
    font-family: var(--mono);
    font-size: 10px;
    cursor: pointer;
  }
  .comp-chip:hover { border-color: var(--pri); }
</style>
</head>
<body>
<div class="root" id="appRoot">
  <div class="toolbar">
    <div class="toolbar-left">
      <div>
        <div class="title-text">DeLonghi Gaggiuino HMI — Original vs New Overview (23 Screens/States)</div>
        <div class="sub-text">Hover any widget to see its Easy ID (e.g. <code>N02-09</code>) &amp; HMI symbol · Click to copy ID &amp; add a review note</div>
      </div>
    </div>
    <div class="controls">
      <button class="btn active" id="btnModeSingle" type="button">Single Screen</button>
      <button class="btn" id="btnModeAll" type="button">All 23 Screens</button>
      <label class="toggle-pill"><input type="checkbox" id="chkShowBoxes" /> Show Outlines</label>
      <label class="toggle-pill"><input type="checkbox" id="chkShowIds" /> Pin IDs</label>
    </div>
  </div>

  <div class="nav-strip" id="navStrip"></div>

  <div id="screensContainer"></div>

  <div class="inspector" id="inspectorBar">
    <div class="insp-left" id="inspContent">
      <span class="insp-hint">Hover over any element in either screen to inspect its Easy ID, Nextion name, coordinates, and text. Click any element to copy its ID and attach a note.</span>
    </div>
    <div class="controls">
      <button class="btn" id="btnPrev" type="button">&larr; Prev</button>
      <button class="btn" id="btnNext" type="button">Next &rarr;</button>
    </div>
  </div>

  <div class="feedback-panel">
    <div class="fb-hdr">
      <div>
        <span class="title-text">Review Feedback Notes</span>
        <span class="sub-text" id="fbCount">(0 notes — click any widget above to add)</span>
      </div>
      <div class="controls">
        <button class="btn active" id="btnCopyAll" type="button">Copy All Feedback (Markdown)</button>
        <button class="btn" id="btnClearAll" type="button">Clear</button>
      </div>
    </div>
    <div class="fb-list" id="fbList"></div>
  </div>
</div>

<div class="float-tip" id="floatTip">
  <div class="ft-top" id="ftTop"></div>
  <div class="ft-sub" id="ftSub"></div>
</div>
<div class="toast" id="toast"></div>

<script>
const SCREENS = __SCREENS_JSON__;
const STORAGE_KEY = "delongui_hmi_feedback_notes_v1";

let viewMode = "single"; // "single" | "all"
let activeIdx = 1; // default to 02 home
let notes = [];
try {
  notes = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]") || [];
} catch (e) {
  notes = [];
}

const appRoot = document.getElementById("appRoot");
const navStrip = document.getElementById("navStrip");
const screensContainer = document.getElementById("screensContainer");
const inspContent = document.getElementById("inspContent");
const floatTip = document.getElementById("floatTip");
const ftTop = document.getElementById("ftTop");
const ftSub = document.getElementById("ftSub");
const toastEl = document.getElementById("toast");
const fbList = document.getElementById("fbList");
const fbCount = document.getElementById("fbCount");

function showToast(msg) {
  toastEl.textContent = msg;
  toastEl.style.display = "block";
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => { toastEl.style.display = "none"; }, 1800);
}

function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text).catch(() => fallbackCopy(text));
  }
  fallbackCopy(text);
  return Promise.resolve();
}

function fallbackCopy(text) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.left = "-9999px";
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand("copy"); } catch (e) {}
  document.body.removeChild(ta);
}

function saveNotes() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(notes)); } catch (e) {}
}

function noteRef(screen, sideKey, comp) {
  return `${comp.easyId} (${screen.page}.${comp.name})`;
}

function renderNav() {
  navStrip.innerHTML = "";
  const notedScreens = new Set(notes.map(n => n.screenKey));
  SCREENS.forEach((s, idx) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "nav-pill" + (idx === activeIdx && viewMode === "single" ? " active" : "") + (notedScreens.has(s.key) ? " has-notes" : "");
    b.innerHTML = `<span class="badge-dot"></span>${s.key} ${s.page}`;
    b.title = s.title;
    b.onclick = () => {
      activeIdx = idx;
      if (viewMode === "all") {
        const el = document.getElementById("screen-" + s.key);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
      } else {
        renderNav();
        renderScreens();
      }
    };
    navStrip.appendChild(b);
  });
}

function buildStage(screen, sideKey, sideData, labelText, tagClass) {
  const col = document.createElement("div");
  col.className = "side-col";

  const lbl = document.createElement("div");
  lbl.className = "side-label";
  lbl.innerHTML = `<span>${labelText}</span><span class="side-tag ${tagClass}">${sideKey === "orig" ? "ORIGINAL" : "NEW"} · ${sideData.components.length} objs</span>`;
  col.appendChild(lbl);

  const stage = document.createElement("div");
  stage.className = "stage";

  const img = document.createElement("img");
  img.src = sideData.img;
  img.alt = `${screen.page} ${sideKey}`;
  stage.appendChild(img);

  // Layer largest containers underneath, smallest foreground controls on top
  const sorted = [...sideData.components].sort((a, b) => {
    const areaA = a.w * a.h;
    const areaB = b.w * b.h;
    if (areaB !== areaA) return areaB - areaA;
    return a.order - b.order;
  });

  const notedIds = new Set(notes.map(n => n.easyId));

  sorted.forEach((c, zIdx) => {
    const box = document.createElement("div");
    box.className = `hitbox ${sideKey === "orig" ? "orig-side" : "new-side"}${notedIds.has(c.easyId) ? " noted" : ""}`;
    box.dataset.easyId = c.easyId;
    box.style.left = (c.x / 320 * 100).toFixed(4) + "%";
    box.style.top = (c.y / 240 * 100).toFixed(4) + "%";
    box.style.width = (c.w / 320 * 100).toFixed(4) + "%";
    box.style.height = (c.h / 240 * 100).toFixed(4) + "%";
    box.style.zIndex = String(10 + zIdx);

    const chip = document.createElement("span");
    chip.className = "id-chip";
    chip.textContent = c.easyId;
    box.appendChild(chip);

    box.addEventListener("mouseenter", () => showHover(screen, sideKey, c));
    box.addEventListener("mousemove", (ev) => moveTip(ev, screen, sideKey, c));
    box.addEventListener("mouseleave", hideTip);
    box.addEventListener("click", (ev) => {
      ev.stopPropagation();
      selectObjectForFeedback(screen, sideKey, c);
    });

    stage.appendChild(box);
  });

  col.appendChild(stage);
  return col;
}

function showHover(screen, sideKey, c) {
  const isOrig = sideKey === "orig";
  inspContent.innerHTML = `
    <span class="insp-id ${isOrig ? "orig" : ""}">${c.easyId}</span>
    <span class="insp-mono"><strong>${screen.page}.${c.name}</strong></span>
    <span class="insp-meta">${c.type} · (${c.x},${c.y}) ${c.w}&times;${c.h}${c.nxId != null ? " · id=" + c.nxId : ""}</span>
    ${c.extra ? `<span class="insp-mono">${escapeHtml(c.extra)}</span>` : ""}
  `;
}

function moveTip(ev, screen, sideKey, c) {
  floatTip.className = "float-tip" + (sideKey === "orig" ? " orig" : "");
  ftTop.textContent = `${c.easyId} · ${screen.page}.${c.name} (${c.type})`;
  ftSub.textContent = `(${c.x},${c.y}) ${c.w}x${c.h}` + (c.extra ? ` · ${c.extra}` : "");
  floatTip.style.display = "block";
  const pad = 12;
  let tx = ev.clientX + pad;
  let ty = ev.clientY + pad;
  if (tx + 290 > window.innerWidth) tx = Math.max(8, ev.clientX - 280);
  if (ty + 56 > window.innerHeight) ty = Math.max(8, ev.clientY - 56);
  floatTip.style.left = tx + "px";
  floatTip.style.top = ty + "px";
}

function hideTip() {
  floatTip.style.display = "none";
}

function selectObjectForFeedback(screen, sideKey, c) {
  const ref = noteRef(screen, sideKey, c);
  copyText(c.easyId + " (" + screen.page + "." + c.name + ")");
  let existing = notes.find(n => n.easyId === c.easyId);
  if (!existing) {
    existing = {
      easyId: c.easyId,
      screenKey: screen.key,
      page: screen.page,
      name: c.name,
      side: sideKey,
      bounds: `(${c.x},${c.y}) ${c.w}x${c.h}`,
      text: "",
    };
    notes.push(existing);
    saveNotes();
    renderFeedback();
    renderNav();
    renderScreens();
  }
  showToast(`Copied ${ref}`);
  setTimeout(() => {
    const inp = document.querySelector(`input[data-note-id="${c.easyId}"]`);
    if (inp) inp.focus();
  }, 30);
}

function renderScreens() {
  screensContainer.innerHTML = "";
  const list = viewMode === "single" ? [SCREENS[activeIdx]] : SCREENS;
  const wrap = document.createElement("div");
  wrap.style.display = "flex";
  wrap.style.flexDirection = "column";
  wrap.style.gap = "12px";

  list.forEach((s) => {
    const card = document.createElement("div");
    card.className = "screen-card";
    card.id = "screen-" + s.key;

    const hdr = document.createElement("div");
    hdr.className = "screen-hdr";
    hdr.innerHTML = `
      <div class="screen-hdr-main">
        <span class="screen-code">${s.key} · ${s.page}</span>
        <span class="screen-title">${escapeHtml(s.title)}</span>
      </div>
      <div class="screen-desc">${escapeHtml(s.desc)}</div>
    `;
    card.appendChild(hdr);

    const grid = document.createElement("div");
    grid.className = "pair-grid";
    grid.appendChild(buildStage(s, "orig", s.orig, "Original HMI", "orig"));
    grid.appendChild(buildStage(s, "new", s.new, "Redesigned HMI", "new"));
    card.appendChild(grid);

    if (viewMode === "single") {
      const det = document.createElement("details");
      const sum = document.createElement("summary");
      sum.style.fontSize = "11px";
      sum.style.color = "var(--mut)";
      sum.style.cursor = "pointer";
      sum.textContent = `All Easy IDs on ${s.page} (${s.new.components.length} New, ${s.orig.components.length} Orig) — click any chip to highlight/note`;
      det.appendChild(sum);
      const chips = document.createElement("div");
      chips.className = "comp-index";
      s.new.components.forEach(c => {
        const ch = document.createElement("button");
        ch.type = "button";
        ch.className = "comp-chip";
        ch.textContent = `${c.easyId} ${c.name}`;
        ch.onmouseenter = () => {
          showHover(s, "new", c);
          const hb = card.querySelector(`.hitbox[data-easy-id="${c.easyId}"]`);
          if (hb) hb.classList.add("hovered");
        };
        ch.onmouseleave = () => {
          const hb = card.querySelector(`.hitbox[data-easy-id="${c.easyId}"]`);
          if (hb) hb.classList.remove("hovered");
        };
        ch.onclick = () => selectObjectForFeedback(s, "new", c);
        chips.appendChild(ch);
      });
      s.orig.components.forEach(c => {
        const ch = document.createElement("button");
        ch.type = "button";
        ch.className = "comp-chip";
        ch.style.color = "var(--acc)";
        ch.textContent = `${c.easyId} ${c.name}`;
        ch.onmouseenter = () => {
          showHover(s, "orig", c);
          const hb = card.querySelector(`.hitbox[data-easy-id="${c.easyId}"]`);
          if (hb) hb.classList.add("hovered");
        };
        ch.onmouseleave = () => {
          const hb = card.querySelector(`.hitbox[data-easy-id="${c.easyId}"]`);
          if (hb) hb.classList.remove("hovered");
        };
        ch.onclick = () => selectObjectForFeedback(s, "orig", c);
        chips.appendChild(ch);
      });
      det.appendChild(chips);
      card.appendChild(det);
    }

    wrap.appendChild(card);
  });

  screensContainer.appendChild(wrap);
}

function renderFeedback() {
  fbCount.textContent = `(${notes.length} note${notes.length === 1 ? "" : "s"} — saved in browser)`;
  fbList.innerHTML = "";
  notes.forEach((n, idx) => {
    const row = document.createElement("div");
    row.className = "fb-row";
    const tag = document.createElement("span");
    tag.className = "fb-tag" + (n.side === "orig" ? " orig" : "");
    tag.textContent = `${n.easyId} (${n.page}.${n.name})`;

    const inp = document.createElement("input");
    inp.type = "text";
    inp.className = "fb-input";
    inp.dataset.noteId = n.easyId;
    inp.placeholder = `Describe requested change for ${n.easyId}...`;
    inp.value = n.text || "";
    inp.oninput = () => {
      notes[idx].text = inp.value;
      saveNotes();
    };

    const del = document.createElement("button");
    del.type = "button";
    del.className = "fb-del";
    del.textContent = "Remove";
    del.onclick = () => {
      notes.splice(idx, 1);
      saveNotes();
      renderFeedback();
      renderNav();
      renderScreens();
    };

    row.appendChild(tag);
    row.appendChild(inp);
    row.appendChild(del);
    fbList.appendChild(row);
  });
}

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

document.getElementById("btnModeSingle").onclick = () => {
  viewMode = "single";
  document.getElementById("btnModeSingle").classList.add("active");
  document.getElementById("btnModeAll").classList.remove("active");
  renderNav();
  renderScreens();
};

document.getElementById("btnModeAll").onclick = () => {
  viewMode = "all";
  document.getElementById("btnModeAll").classList.add("active");
  document.getElementById("btnModeSingle").classList.remove("active");
  renderNav();
  renderScreens();
};

document.getElementById("chkShowBoxes").onchange = (e) => {
  appRoot.classList.toggle("show-boxes", e.target.checked);
};

document.getElementById("chkShowIds").onchange = (e) => {
  appRoot.classList.toggle("show-ids", e.target.checked);
  if (e.target.checked) appRoot.classList.add("show-boxes");
  else if (!document.getElementById("chkShowBoxes").checked) appRoot.classList.remove("show-boxes");
};

document.getElementById("btnPrev").onclick = () => {
  activeIdx = (activeIdx - 1 + SCREENS.length) % SCREENS.length;
  viewMode = "single";
  document.getElementById("btnModeSingle").classList.add("active");
  document.getElementById("btnModeAll").classList.remove("active");
  renderNav();
  renderScreens();
};

document.getElementById("btnNext").onclick = () => {
  activeIdx = (activeIdx + 1) % SCREENS.length;
  viewMode = "single";
  document.getElementById("btnModeSingle").classList.add("active");
  document.getElementById("btnModeAll").classList.remove("active");
  renderNav();
  renderScreens();
};

document.getElementById("btnCopyAll").onclick = () => {
  if (!notes.length) {
    showToast("Click any object first to add a feedback note");
    return;
  }
  const md = notes.map(n => `- **${n.easyId}** (\`${n.page}.${n.name}\`, ${n.side.toUpperCase()} ${n.bounds}): ${n.text || "(no note text)"}`).join("\n");
  copyText(md);
  showToast(`Copied ${notes.length} feedback item(s)!`);
};

document.getElementById("btnClearAll").onclick = () => {
  notes = [];
  saveNotes();
  renderFeedback();
  renderNav();
  renderScreens();
};

renderNav();
renderScreens();
renderFeedback();
</script>
</body>
</html>
"""


def main():
    screens_json = DATA_JSON.read_text(encoding="utf-8")
    html = HTML_TEMPLATE.replace("__SCREENS_JSON__", screens_json)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_HTML} ({OUT_HTML.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
