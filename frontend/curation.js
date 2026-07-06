/* curation.js — édition du barème « validant / complémentaire » + mapping ontologique */
const API = "";
let OVERVIEW = [];
let ONTO_AVAILABLE = false;
let CURRENT = null;        // { num, titre, concepts: [...] }
let DIRTY = false;         // rôles/suppressions non enregistrés
let MAP_DIRTY = false;     // mapping ontologique non enregistré

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, html) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
};

/* ─────────── Bootstrap ─────────── */
async function init() {
  await loadOverview();
  wireGlobal();
}

async function loadOverview() {
  const data = await fetch(`${API}/api/curation`).then((r) => r.json());
  // Nouveau contrat : { onto_available, cases:[...] }. Rétro-compat si tableau nu.
  OVERVIEW = Array.isArray(data) ? data : (data.cases || []);
  ONTO_AVAILABLE = Array.isArray(data) ? false : !!data.onto_available;
  $("#cases-count").textContent = `${OVERVIEW.length} cas`;
  renderCaseList();
}

/* ─────────── Liste des cas ─────────── */
function renderCaseList() {
  const list = $("#case-list");
  list.innerHTML = "";
  OVERVIEW.forEach((c) => {
    const item = el("li", "case-item" + (CURRENT && CURRENT.num === c.num ? " active" : ""));
    item.innerHTML =
      `<span class="n">${c.num}</span>` +
      `<div><div class="t">${escapeHtml(c.titre || "Cas ECG")}</div>` +
      `<div class="fam">${escapeHtml(c.famille || "")}</div></div>` +
      `<div class="cur-meta">` +
        `<span class="valcount">${c.nb_validants}✓</span>` +
        (c.nb_removed ? `<span class="rmcount" title="${c.nb_removed} diagnostic(s) supprimé(s)">${c.nb_removed}🗑</span>` : "") +
        mappingPill(c) +
        `<span class="cfg ${c.configured ? "" : "off"}" title="${c.configured ? "configuré" : "défauts"}"></span>` +
      `</div>`;
    item.onclick = () => openCase(c.num);
    list.appendChild(item);
  });
}

/* Pastille de progression du mapping ontologique (n mappés / n concepts). */
function mappingPill(c) {
  if (!ONTO_AVAILABLE) return "";
  const total = c.nb_concepts != null ? c.nb_concepts : 0;
  const mapped = c.nb_mapped != null ? c.nb_mapped : 0;
  if (!total) return "";
  const done = mapped >= total;
  const cls = done ? "map-full" : (mapped > 0 ? "map-part" : "map-none");
  return `<span class="mapcount ${cls}" title="${mapped}/${total} concepts mappés vers l'ontologie">🔗${mapped}/${total}</span>`;
}

/* ─────────── Ouverture d'un cas ─────────── */
async function openCase(num) {
  if ((DIRTY || MAP_DIRTY) && !confirm("Des changements ne sont pas enregistrés. Continuer ?")) return;
  const data = await fetch(`${API}/api/curation/${num}`).then((r) => r.json());
  CURRENT = data;
  DIRTY = false;
  MAP_DIRTY = false;
  setSaveBadge("idle");
  renderCaseList();

  $("#welcome").classList.add("hidden");
  const view = $("#case-view");
  view.classList.remove("hidden");

  $("#case-family").textContent = data.famille || "";
  $("#case-title").textContent = data.titre || "Cas ECG";
  $("#case-num").textContent = "#" + data.num;
  const ctx = [data.patient, data.contexte].filter(Boolean).join("\n").trim();
  $("#case-context").textContent = ctx || "—";
  $("#case-interp").textContent = data.interpretation_ref || "—";

  renderConcepts();
  view.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ─────────── Rendu des concepts ─────────── */
function renderConcepts() {
  const list = $("#concept-list");
  list.innerHTML = "";
  (CURRENT.concepts || []).forEach((c, idx) => {
    const isVal = c.role === "validant";
    const isRemoved = c.role === "removed";
    const li = el("li", "concept-item"
      + (isVal ? " is-validant" : "")
      + (isRemoved ? " is-removed" : "")
      + (c.source === "custom" ? " custom" : ""));
    const rang = (c.rang || "?").toUpperCase();

    if (isRemoved) {
      // Concept supprimé : affiché barré, avec bouton restaurer.
      li.innerHTML =
        `<span class="rang-badge ${rang}">${rang}</span>` +
        `<span class="c-label">${escapeHtml(c.label)}</span>` +
        `<span class="removed-tag">supprimé</span>` +
        `<button class="restore-btn" title="Restaurer ce concept">↩ Restaurer</button>`;
      li.querySelector(".restore-btn").onclick = () => restoreConcept(idx);
    } else {
      li.innerHTML =
        `<span class="rang-badge ${rang}">${rang}</span>` +
        `<span class="c-label">${escapeHtml(c.label)}</span>` +
        `<span class="role-switch">` +
          `<button class="val ${isVal ? "active" : ""}" data-role="validant">Validant</button>` +
          `<button class="comp ${!isVal ? "active" : ""}" data-role="complementaire">Complément.</button>` +
        `</span>` +
        `<button class="del-btn" title="${c.source === "custom" ? "Supprimer ce concept ajouté" : "Retirer ce diagnostic attendu"}">🗑</button>`;

      li.querySelectorAll(".role-switch button").forEach((b) => {
        b.onclick = () => setRole(idx, b.dataset.role);
      });
      li.querySelector(".del-btn").onclick = () => removeConcept(idx);

      // Ligne de mapping ontologique (le « pont sémantique »).
      if (ONTO_AVAILABLE) li.appendChild(renderMapRow(c, idx));
    }
    list.appendChild(li);
  });
  updateCounts();
}

/* Ligne « → concept ontologique » sous chaque concept curé. */
function renderMapRow(c, idx) {
  const row = el("div", "map-row");
  if (c.golden_id && c.golden_valid) {
    const isAbsent = c.golden_statut === "absent";
    if (isAbsent) row.classList.add("is-absent");
    const cat = c.golden_categorie ? `<span class="map-cat">${escapeHtml(c.golden_categorie)}</span>` : "";
    const by = c.golden_by === "gpt"
      ? `<span class="map-by gpt" title="Proposé par GPT — à valider">GPT</span>`
      : `<span class="map-by human" title="Validé à la main">✓</span>`;
    // Bascule present / absent (polarité du concept, alignée sur le NER onto).
    const statutSwitch =
      `<span class="statut-switch" title="Le concept est-il affirmé ou nié/écarté ?">` +
        `<button class="pres ${!isAbsent ? "active" : ""}" data-statut="present">présent</button>` +
        `<button class="abs ${isAbsent ? "active" : ""}" data-statut="absent">absent</button>` +
      `</span>`;
    row.innerHTML =
      `<span class="map-arrow">${isAbsent ? "�" : "�🔗"}</span>` +
      `<span class="map-concept" title="${escapeHtml(c.golden_id)}">` +
        `${escapeHtml(c.golden_name || c.golden_id)}` +
        `<code>${escapeHtml(c.golden_id)}</code>` +
      `</span>${cat}${statutSwitch}${by}` +
      `<button class="map-edit" title="Changer le concept">modifier</button>` +
      `<button class="map-clear" title="Retirer le mapping">✕</button>`;
    row.querySelectorAll(".statut-switch button").forEach((b) => {
      b.onclick = () => setStatut(idx, b.dataset.statut);
    });
    row.querySelector(".map-edit").onclick = () => openPicker(idx);
    row.querySelector(".map-clear").onclick = () => clearMapping(idx);
  } else if (c.golden_id && !c.golden_valid) {
    // ID enregistré mais absent de l'ontologie (périmé).
    row.innerHTML =
      `<span class="map-arrow warn">⚠</span>` +
      `<span class="map-concept stale">ID inconnu : <code>${escapeHtml(c.golden_id)}</code></span>` +
      `<button class="map-edit" title="Choisir un concept valide">corriger</button>`;
    row.querySelector(".map-edit").onclick = () => openPicker(idx);
  } else {
    row.classList.add("unmapped");
    row.innerHTML =
      `<span class="map-arrow">🔗</span>` +
      `<button class="map-add" title="Rattacher à un concept de l'ontologie">＋ mapper vers l'ontologie</button>`;
    row.querySelector(".map-add").onclick = () => openPicker(idx);
  }
  return row;
}

/* Bascule la polarité present/absent d'un concept mappé. */
function setStatut(idx, statut) {
  const c = CURRENT.concepts[idx];
  c.golden_statut = statut === "absent" ? "absent" : "present";
  markMapDirty();
  renderConcepts();
}

function setRole(idx, role) {
  CURRENT.concepts[idx].role = role;
  markDirty();
  renderConcepts();
}

function removeConcept(idx) {
  const c = CURRENT.concepts[idx];
  if (c.source === "custom") {
    // Concept ajouté à la main : on l'enlève purement et simplement.
    CURRENT.concepts.splice(idx, 1);
  } else {
    // Diagnostic attendu de la référence : on le marque « supprimé »
    // (restaurable), il n'est plus utilisé pour la note ni la description.
    c.role = "removed";
  }
  markDirty();
  renderConcepts();
}

function restoreConcept(idx) {
  const c = CURRENT.concepts[idx];
  // Retour au rôle par défaut selon le rang (A ⇒ validant, sinon complément.).
  c.role = (c.rang || "").toUpperCase() === "A" ? "validant" : "complementaire";
  markDirty();
  renderConcepts();
}

function addConcept() {
  const input = $("#add-input");
  const label = input.value.trim();
  if (!label) { input.focus(); return; }
  CURRENT.concepts.push({ label, rang: "A", role: "validant", source: "custom", configured: true });
  input.value = "";
  markDirty();
  renderConcepts();
}

function allComplementaire() {
  (CURRENT.concepts || []).forEach((c) => {
    if (c.role !== "removed") c.role = "complementaire";
  });
  markDirty();
  renderConcepts();
}

function updateCounts() {
  const concepts = CURRENT.concepts || [];
  const val = concepts.filter((c) => c.role === "validant").length;
  const comp = concepts.filter((c) => c.role === "complementaire").length;
  $("#count-val").textContent = val;
  $("#count-comp").textContent = comp;
  updateMapCounts();
}

function updateMapCounts() {
  const box = $("#count-map");
  if (!box) return;
  if (!ONTO_AVAILABLE) { box.parentElement.classList.add("hidden"); return; }
  box.parentElement.classList.remove("hidden");
  const active = (CURRENT.concepts || []).filter((c) => c.role !== "removed");
  const mapped = active.filter((c) => c.golden_id && c.golden_valid).length;
  box.textContent = `${mapped}/${active.length}`;
}

/* ─────────── Mapping ontologique ─────────── */
function clearMapping(idx) {
  const c = CURRENT.concepts[idx];
  c.golden_id = null;
  c.golden_name = null;
  c.golden_categorie = null;
  c.golden_valid = false;
  c.golden_by = null;
  markMapDirty();
  renderConcepts();
}

let PICKER_IDX = null;
let PICKER_TIMER = null;

function openPicker(idx) {
  PICKER_IDX = idx;
  const c = CURRENT.concepts[idx];
  $("#picker-label").textContent = c.label;
  const input = $("#picker-input");
  input.value = c.golden_name || "";
  $("#picker-results").innerHTML =
    `<li class="picker-hint">Tape un terme (ex. « PR normal », « BAV »)…</li>`;
  $("#picker-modal").classList.remove("hidden");
  input.focus();
  input.select();
  if (input.value.trim()) runPickerSearch(input.value);
}

function closePicker() {
  $("#picker-modal").classList.add("hidden");
  PICKER_IDX = null;
}

function onPickerInput(e) {
  clearTimeout(PICKER_TIMER);
  const q = e.target.value;
  PICKER_TIMER = setTimeout(() => runPickerSearch(q), 180);
}

async function runPickerSearch(q) {
  q = (q || "").trim();
  const ul = $("#picker-results");
  if (q.length < 2) {
    ul.innerHTML = `<li class="picker-hint">Tape au moins 2 caractères…</li>`;
    return;
  }
  ul.innerHTML = `<li class="picker-hint">Recherche…</li>`;
  try {
    const data = await fetch(`${API}/api/onto/search?q=${encodeURIComponent(q)}&limit=25`)
      .then((r) => r.json());
    const results = data.results || [];
    if (!results.length) {
      ul.innerHTML = `<li class="picker-hint">Aucun concept trouvé pour « ${escapeHtml(q)} ».</li>`;
      return;
    }
    ul.innerHTML = "";
    results.forEach((r) => {
      const li = el("li", "picker-item");
      li.innerHTML =
        `<div class="pi-main"><span class="pi-name">${escapeHtml(r.name)}</span>` +
        `<code class="pi-id">${escapeHtml(r.id)}</code></div>` +
        `<div class="pi-meta"><span class="pi-cat">${escapeHtml(r.categorie || "")}</span>` +
        `<span class="pi-score">${r.score}</span></div>`;
      li.onclick = () => choosePickerConcept(r);
      ul.appendChild(li);
    });
  } catch (e) {
    ul.innerHTML = `<li class="picker-hint">Erreur de recherche : ${escapeHtml(e.message)}</li>`;
  }
}

function choosePickerConcept(r) {
  if (PICKER_IDX == null) return;
  const c = CURRENT.concepts[PICKER_IDX];
  const hadStatut = c.golden_id && c.golden_statut;  // on garde le statut si on ne fait que changer de concept
  c.golden_id = r.id;
  c.golden_name = r.name;
  c.golden_categorie = r.categorie;
  c.golden_valid = true;
  c.golden_by = "humain";  // choix humain explicite
  // Statut : conserve l'existant, sinon auto-détecte une négation dans le label.
  c.golden_statut = hadStatut ? c.golden_statut
                              : (looksNegated(c.label) ? "absent" : "present");
  markMapDirty();
  closePicker();
  renderConcepts();
}

/* Heuristique : le label exprime-t-il une négation / une exclusion ? */
function looksNegated(label) {
  const s = " " + (label || "").toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "") + " ";
  return /(^|\s)(pas de|pas d'|absence|absent|sans |eliminer|elimine|ne pas|ni |negati|ecarter|exclure|aucun)/.test(s);
}

function markMapDirty() {
  MAP_DIRTY = true;
  setSaveBadge("dirty");
}

/* Enregistre le mapping label→concept_id (indépendant des rôles). */
async function saveMapping() {
  if (!CURRENT) return;
  const mapping = {};
  (CURRENT.concepts || []).forEach((c) => {
    if (c.role === "removed") return;
    if (c.golden_id && c.golden_valid) {
      mapping[c.label] = {
        golden_id: c.golden_id,
        statut: c.golden_statut === "absent" ? "absent" : "present",
        valide_par: c.golden_by === "gpt" ? "gpt" : "humain",
      };
    }
  });
  const btn = $("#save-map-btn");
  if (btn) btn.disabled = true;
  setSaveBadge("saving");
  try {
    const r = await fetch(`${API}/api/curation/${CURRENT.num}/mapping`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mapping, diagnostic_principal: CURRENT.diagnostic_principal || "" }),
    });
    const data = await r.json();
    if (data.error) throw new Error(data.error);
    CURRENT.concepts = data.concepts;
    MAP_DIRTY = false;
    setSaveBadge("saved");
    await loadOverview();
    renderConcepts();
  } catch (e) {
    setSaveBadge("error", e.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

function markDirty() {
  DIRTY = true;
  setSaveBadge("dirty");
}

/* ─────────── Sauvegarde ─────────── */
async function saveCurrent() {
  if (!CURRENT) return;
  const roles = {};
  const extra = [];
  const removed = [];
  (CURRENT.concepts || []).forEach((c) => {
    if (c.role === "removed") {
      // Seuls les concepts de référence peuvent être « supprimés » (restaurables).
      if (c.source !== "custom") removed.push(c.label);
      return;
    }
    if (c.source === "custom") {
      if (c.role === "validant") extra.push(c.label);
    } else {
      roles[c.label] = c.role;
    }
  });

  const btn = $("#save-btn");
  btn.disabled = true;
  btn.querySelector(".spinner").classList.remove("hidden");
  setSaveBadge("saving");
  try {
    const r = await fetch(`${API}/api/curation/${CURRENT.num}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ roles, extra_validants: extra, removed }),
    });
    const data = await r.json();
    if (data.error) throw new Error(data.error);
    CURRENT.concepts = data.concepts;
    DIRTY = false;
    setSaveBadge("saved");
    await loadOverview();
    renderConcepts();
  } catch (e) {
    setSaveBadge("error", e.message);
  } finally {
    btn.disabled = false;
    btn.querySelector(".spinner").classList.add("hidden");
  }
}

async function resetCurrent() {
  if (!CURRENT) return;
  if (!confirm("Réinitialiser ce cas aux rôles par défaut (rang A = validant) ?")) return;
  const data = await fetch(`${API}/api/curation/${CURRENT.num}/reset`, { method: "POST" })
    .then((r) => r.json());
  CURRENT.concepts = data.concepts;
  DIRTY = false;
  setSaveBadge("idle");
  await loadOverview();
  renderConcepts();
}

function setSaveBadge(state, msg) {
  const b = $("#save-badge");
  const map = {
    idle: ["badge badge-muted", CURRENT ? "à jour" : "—"],
    dirty: ["badge badge-bad", "non enregistré"],
    saving: ["badge badge-saving", "enregistrement…"],
    saved: ["badge badge-saved", "✓ enregistré"],
    error: ["badge badge-bad", msg ? `erreur : ${msg}` : "erreur"],
  };
  const [cls, text] = map[state] || map.idle;
  b.className = cls;
  b.textContent = text;
}

/* ─────────── Divers ─────────── */
function wireGlobal() {
  $("#save-btn").onclick = saveCurrent;
  $("#reset-btn").onclick = resetCurrent;
  $("#all-comp-btn").onclick = allComplementaire;
  $("#add-btn").onclick = addConcept;
  $("#add-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") addConcept();
  });
  const mapBtn = $("#save-map-btn");
  if (mapBtn) mapBtn.onclick = saveMapping;
  // Picker (modal de recherche de concept ontologique)
  const pInput = $("#picker-input");
  if (pInput) pInput.addEventListener("input", onPickerInput);
  const pClose = $("#picker-close");
  if (pClose) pClose.onclick = closePicker;
  const pBack = $("#picker-modal");
  if (pBack) pBack.addEventListener("click", (e) => {
    if (e.target === pBack) closePicker();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !$("#picker-modal").classList.contains("hidden")) closePicker();
    if (e.key === "s" && e.ctrlKey) { e.preventDefault(); saveCurrent(); }
  });
  window.addEventListener("beforeunload", (e) => {
    if (DIRTY || MAP_DIRTY) { e.preventDefault(); e.returnValue = ""; }
  });
}

function escapeHtml(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

init();
