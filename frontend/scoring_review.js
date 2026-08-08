/* scoring_review.js — page de double annotation indépendante du golden
 * conceptuel de scoring V2 (P1.3, cf. audit_doc/roadmap_scientifique_2026.md).
 * Réplique le pattern déjà validé par annotation.js (golden d'extraction),
 * appliqué cette fois aux critères structurés scoring_v2 (pas des concepts
 * extraits d'une réponse libre). */
const API = "";
const CURATION_KEY = new URLSearchParams(location.search).get("key") || "";

function apiFetch(url, opts = {}) {
  const headers = Object.assign({}, opts.headers || {});
  if (CURATION_KEY) headers["X-Curation-Token"] = CURATION_KEY;
  return fetch(url, Object.assign({}, opts, { headers }));
}

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, html) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
};
function escapeHtml(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

// Enums du schéma scoring_v2 (cf. data/scoring_schema_v2.json,
// scripts/validate_scoring_v2.py) — tenus synchronisés manuellement.
const ENUMS = {
  role: ["required", "alternative", "optional", "exclusion"],
  expected_status: ["present", "absent", "hypothesis_acceptable"],
  importance: ["major", "intermediate", "minor"],
  error_severity: ["none", "minor", "major", "dangerous"],
  group_logic: ["ANY", "ALL", "AT_LEAST_N"],
  minimum_specificity: ["exact_only", "child_ok", "parent_ok", "any_related"],
  expert_confidence: ["high", "medium", "low"],
  evidence_source: ["expert_consensus", "single_expert", "gpt_assisted_reviewed", "literature"],
};
const COMPARED_FIELDS = [
  "concept_id", "label", "role", "expected_status", "importance",
  "error_severity", "alternative_group", "group_logic", "group_min_n",
  "sufficient_alone", "minimum_specificity",
];

let OVERVIEW = [];
let CURRENT = null;       // {case_id, pilot_criteria, expert_1, expert_2, adjudication}
let CURRENT_ID = null;
let CRITERIA = [];        // état de travail pour le slot actif
let ACTIVE_SLOT = "expert_1";
let DISAGREEMENTS = [];   // désaccords calculés côté serveur, pour l'onglet adjudication

async function init() {
  await loadOverview();
  $("#save-btn").addEventListener("click", saveCurrent);
  $("#slot-1").addEventListener("click", () => switchSlot("expert_1"));
  $("#slot-2").addEventListener("click", () => switchSlot("expert_2"));
  $("#slot-adj").addEventListener("click", () => switchSlot("adjudication"));
  $("#compute-disagree-btn").addEventListener("click", computeDisagreements);
}

async function loadOverview() {
  const data = await apiFetch(`${API}/api/scoring-review/overview`).then((r) => r.json());
  OVERVIEW = data.cases || [];
  $("#items-count").textContent = `${OVERVIEW.length} cas`;
  renderItemList();
}

function statusIcon(status) {
  if (status === "adjudicated") return '<span class="status-adjudicated">✓</span>';
  if (status === "ready_for_adjudication") return '<span class="status-ready">👥</span>';
  if (status === "partial") return '<span class="status-partial">½</span>';
  return '<span class="status-pending">○</span>';
}

function renderItemList() {
  const list = $("#item-list");
  list.innerHTML = "";
  OVERVIEW.forEach((it) => {
    const li = el("li", CURRENT_ID === it.case_id ? "active" : "");
    const disagreeBadge = it.n_disagreements
      ? `<span class="disagree-badge" title="${it.n_disagreements} désaccord(s)">⚠️ ${it.n_disagreements}</span> `
      : "";
    li.innerHTML = `${statusIcon(it.status)} <b>Cas ${it.case_id}</b> ` +
      `${disagreeBadge}<br>` +
      `<span class="muted" style="font-size:.75rem">${escapeHtml(it.label)} · ${it.n_criteria_pilot} critères</span>`;
    li.addEventListener("click", () => selectItem(it.case_id));
    list.appendChild(li);
  });
}

async function selectItem(caseId) {
  CURRENT_ID = caseId;
  ACTIVE_SLOT = "expert_1";
  DISAGREEMENTS = [];
  const data = await apiFetch(`${API}/api/scoring-review/${caseId}`).then((r) => r.json());
  CURRENT = data;
  renderItemList();
  renderItem();
}

function switchSlot(slot) {
  if (slot === "adjudication" && (!CURRENT.expert_1 || !CURRENT.expert_2)) {
    $("#save-status").textContent = "⏳ Les deux relecteurs doivent d'abord terminer leur annotation.";
    return;
  }
  ACTIVE_SLOT = slot;
  renderItem();
}

function criteriaForSlot() {
  if (ACTIVE_SLOT === "adjudication") {
    const adj = CURRENT.adjudication;
    if (adj && Array.isArray(adj.criteria)) return adj.criteria.map((c) => Object.assign({}, c));
    // Pré-remplissage adjudication : part de expert_1, l'adjudicateur corrige
    // les champs en désaccord en s'appuyant sur la liste calculée.
    const e1 = CURRENT.expert_1;
    return (e1 && Array.isArray(e1.criteria) ? e1.criteria : []).map((c) => Object.assign({}, c));
  }
  const existing = CURRENT[ACTIVE_SLOT];
  if (existing && Array.isArray(existing.criteria)) {
    return existing.criteria.map((c) => Object.assign({}, c));
  }
  // Pré-remplissage neutre : le pilote solo P1.2, à confirmer/corriger
  // indépendamment (pas de recopie d'un relecteur vers l'autre).
  return (CURRENT.pilot_criteria || []).map((c) => Object.assign({}, c));
}

function renderItem() {
  $("#welcome").classList.add("hidden");
  $("#item-view").classList.remove("hidden");
  const meta = OVERVIEW.find((o) => o.case_id === CURRENT_ID) || {};
  $("#item-title").textContent = `Cas ${CURRENT_ID}`;
  $("#item-label").textContent = meta.label || "";

  $("#slot-1").classList.toggle("active", ACTIVE_SLOT === "expert_1");
  $("#slot-2").classList.toggle("active", ACTIVE_SLOT === "expert_2");
  $("#slot-adj").classList.toggle("active", ACTIVE_SLOT === "adjudication");
  $("#slot-adj").classList.toggle("locked", !(CURRENT.expert_1 && CURRENT.expert_2));

  const existing = ACTIVE_SLOT === "adjudication" ? CURRENT.adjudication : CURRENT[ACTIVE_SLOT];
  const who = ACTIVE_SLOT === "adjudication" ? (existing && existing.adjudicateur)
    : (existing && existing.annotateur);
  $("#annotateur-name").value = who || "";
  $("#item-status").textContent = existing
    ? `${ACTIVE_SLOT === "adjudication" ? "adjugé" : "annoté"} par ${who || "?"}`
    : "en attente";

  $("#compute-disagree-btn").classList.toggle("hidden", ACTIVE_SLOT !== "adjudication");

  CRITERIA = criteriaForSlot();
  renderAdjudicationBanner();
  renderDisagreeBox();
  renderCriteriaList();
}

function renderAdjudicationBanner() {
  const banner = $("#adjudication-banner");
  if (ACTIVE_SLOT !== "adjudication") { banner.classList.add("hidden"); return; }
  banner.classList.remove("hidden");
  banner.innerHTML = CURRENT.adjudication
    ? `✅ Version consensuelle déjà enregistrée par <b>${escapeHtml(CURRENT.adjudication.adjudicateur || "?")}</b> le ${escapeHtml(CURRENT.adjudication.adjudicated_at || "")}.`
    : `🧭 Pré-rempli depuis Relecteur 1. Clique « Calculer les désaccords » pour voir les champs divergents avec Relecteur 2, puis corrige les critères ci-dessous avant d'enregistrer la version consensuelle.`;
}

function renderDisagreeBox() {
  const box = $("#disagree-box");
  if (ACTIVE_SLOT !== "adjudication" || !DISAGREEMENTS.length) {
    box.classList.add("hidden");
    box.innerHTML = "";
    return;
  }
  box.classList.remove("hidden");
  box.innerHTML = `<div class="disagree-title">⚠️ ${DISAGREEMENTS.length} désaccord(s) détecté(s) — les désaccords constituent eux-mêmes un résultat scientifique (roadmap §P1.3), corrige ci-dessous en connaissance de cause :</div>` +
    DISAGREEMENTS.map((d) => `
      <div class="disagree-row">
        <span class="cid">${escapeHtml(d.criterion_id)}</span>
        <span class="field">${escapeHtml(d.field)}</span>
        <span class="val">R1: ${escapeHtml(JSON.stringify(d.expert_1_value))}</span>
        <span class="val">R2: ${escapeHtml(JSON.stringify(d.expert_2_value))}</span>
      </div>`).join("");
}

function divergingFieldsFor(criterionId) {
  if (ACTIVE_SLOT !== "adjudication") return new Set();
  return new Set(
    DISAGREEMENTS.filter((d) => d.criterion_id === criterionId).map((d) => d.field)
  );
}

function selectHtml(field, value, idx) {
  const options = ENUMS[field].map((v) =>
    `<option value="${v}" ${v === value ? "selected" : ""}>${v}</option>`
  ).join("");
  return `<select data-i="${idx}" data-field="${field}">${options}</select>`;
}

function renderCriteriaList() {
  const box = $("#crit-list");
  box.innerHTML = "";
  CRITERIA.forEach((c, i) => {
    const diverging = divergingFieldsFor(c.criterion_id);
    const card = el("div", "crit-card" + (diverging.size ? " disagree" : ""));
    const cls = (f) => diverging.has(f) ? "diverging-field" : "";
    card.innerHTML = `
      <div class="crit-head">
        <span class="cid">${escapeHtml(c.criterion_id)}</span>
        <span class="label">${escapeHtml(c.label)}</span>
      </div>
      <div class="crit-grid">
        <div class="crit-field ${cls("concept_id")}"><label>Concept ID</label>
          <input type="text" data-i="${i}" data-field="concept_id" value="${escapeHtml(c.concept_id)}"></div>
        <div class="crit-field ${cls("role")}"><label>Rôle</label>${selectHtml("role", c.role, i)}</div>
        <div class="crit-field ${cls("expected_status")}"><label>Statut attendu</label>${selectHtml("expected_status", c.expected_status, i)}</div>
        <div class="crit-field ${cls("importance")}"><label>Importance</label>${selectHtml("importance", c.importance, i)}</div>
        <div class="crit-field ${cls("error_severity")}"><label>Gravité erreur</label>${selectHtml("error_severity", c.error_severity, i)}</div>
        <div class="crit-field ${cls("group_logic")}"><label>Logique groupe</label>${selectHtml("group_logic", c.group_logic, i)}</div>
        <div class="crit-field ${cls("alternative_group")}"><label>Groupe alternatif</label>
          <input type="text" data-i="${i}" data-field="alternative_group" value="${escapeHtml(c.alternative_group || "")}"></div>
        <div class="crit-field ${cls("group_min_n")}"><label>Seuil (AT_LEAST_N)</label>
          <input type="number" min="1" data-i="${i}" data-field="group_min_n" value="${c.group_min_n == null ? "" : c.group_min_n}"></div>
        <div class="crit-field ${cls("minimum_specificity")}"><label>Spécificité min.</label>${selectHtml("minimum_specificity", c.minimum_specificity, i)}</div>
        <div class="crit-field checkbox ${cls("sufficient_alone")}">
          <input type="checkbox" id="suf-${i}" data-i="${i}" data-field="sufficient_alone" ${c.sufficient_alone ? "checked" : ""}>
          <label for="suf-${i}">Suffit seul</label></div>
        <div class="crit-field"><label>Confiance experte</label>${selectHtml("expert_confidence", c.expert_confidence, i)}</div>
        <div class="crit-field"><label>Origine (evidence_source)</label>${selectHtml("evidence_source", c.evidence_source, i)}</div>
      </div>
      <div class="crit-comment">
        <label style="font-size:.7rem;text-transform:uppercase;color:#64748b;font-weight:700">Commentaire</label>
        <textarea data-i="${i}" data-field="comment" rows="2">${escapeHtml(c.comment || "")}</textarea>
      </div>`;

    card.querySelectorAll("select, input[type=text], input[type=number], textarea").forEach((input) => {
      const evt = input.tagName === "TEXTAREA" || input.type === "text" || input.type === "number" ? "input" : "change";
      input.addEventListener(evt, (e) => {
        const idx = Number(e.target.dataset.i);
        const field = e.target.dataset.field;
        let val = e.target.value;
        if (field === "group_min_n") val = val === "" ? null : Number(val);
        CRITERIA[idx][field] = val;
      });
    });
    card.querySelector(`#suf-${i}`).addEventListener("change", (e) => {
      CRITERIA[i].sufficient_alone = e.target.checked;
    });
    box.appendChild(card);
  });
}

async function computeDisagreements() {
  const data = await apiFetch(`${API}/api/scoring-review/${CURRENT_ID}/disagreements`).then((r) => r.json());
  DISAGREEMENTS = data.disagreements || [];
  renderDisagreeBox();
  renderCriteriaList();
  await loadOverview();
  renderItemList();
}

async function saveCurrent() {
  const who = $("#annotateur-name").value.trim();
  $("#save-status").textContent = "Enregistrement…";
  try {
    let res;
    if (ACTIVE_SLOT === "adjudication") {
      res = await apiFetch(`${API}/api/scoring-review/${CURRENT_ID}/adjudication`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ criteria: CRITERIA, disagreements: DISAGREEMENTS, adjudicateur: who }),
      });
    } else {
      res = await apiFetch(`${API}/api/scoring-review/${CURRENT_ID}/${ACTIVE_SLOT}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ criteria: CRITERIA, annotateur: who }),
      });
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || err.description || `HTTP ${res.status}`);
    }
    const data = await res.json();
    if (ACTIVE_SLOT === "adjudication") CURRENT.adjudication = data.adjudication;
    else CURRENT[ACTIVE_SLOT] = data[ACTIVE_SLOT];
    $("#save-status").textContent = "✅ Enregistré.";
    await loadOverview();
    renderItemList();
  } catch (ex) {
    $("#save-status").textContent = `❌ ${ex.message}`;
  }
}

init();
