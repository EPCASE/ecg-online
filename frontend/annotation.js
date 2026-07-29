/* annotation.js — page de re-annotation du golden d'extraction (cf. GOLDEN_EXTRACTION.md) */
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
  return String(s || "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

let OVERVIEW = [];
let CURRENT = null;      // item complet (texte, pipeline_extraction, annotation_expert[_2])
let CURRENT_ID = null;
let CONCEPTS = [];       // état de travail : [{ontology_id, concept_name, statut, source}]
let ACTIVE_SLOT = "annotation_expert";

async function init() {
  await loadOverview();
  $("#add-concept-input").addEventListener("input", onSearchInput);
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".add-concept-box")) {
      $("#add-concept-results").classList.add("hidden");
    }
  });
  $("#save-btn").addEventListener("click", saveAnnotation);
  $("#slot-1").addEventListener("click", () => switchSlot("annotation_expert"));
  $("#slot-2").addEventListener("click", () => switchSlot("annotation_expert_2"));
}

async function loadOverview() {
  const data = await apiFetch(`${API}/api/annotation/overview`).then((r) => r.json());
  OVERVIEW = data.items || [];
  $("#items-count").textContent = `${OVERVIEW.length} items`;
  renderItemList();
}

function statusIcon(status) {
  if (status === "done") return '<span class="status-done">✓</span>';
  if (status === "partial") return '<span class="status-partial">½</span>';
  return '<span class="status-pending">○</span>';
}

function renderItemList() {
  const list = $("#item-list");
  list.innerHTML = "";
  OVERVIEW.forEach((it) => {
    const li = el("li", CURRENT_ID === it.item_id ? "active" : "");
    const alertBadge = it.n_alertes_review
      ? `<span class="alert-badge" title="${it.n_alertes_review} alerte(s) de relecture GPT-5.6">⚠️ ${it.n_alertes_review}</span> `
      : "";
    li.innerHTML = `${statusIcon(it.status)} <b>${it.item_id}</b> ` +
      `${it.double_annotation ? "👥 " : ""}${alertBadge}` +
      `<span class="muted">(${it.n_concepts_pipeline})</span><br>` +
      `<span class="muted" style="font-size:.75rem">${escapeHtml(it.preview)}…</span>`;
    li.addEventListener("click", () => selectItem(it.item_id));
    list.appendChild(li);
  });
}

async function selectItem(itemId) {
  CURRENT_ID = itemId;
  ACTIVE_SLOT = "annotation_expert";
  const data = await apiFetch(`${API}/api/annotation/${itemId}`).then((r) => r.json());
  CURRENT = data;
  renderItemList();
  renderItem();
}

function switchSlot(slot) {
  ACTIVE_SLOT = slot;
  renderItem();
}

function conceptsForSlot() {
  const existing = CURRENT[ACTIVE_SLOT];
  if (existing && Array.isArray(existing.concepts)) {
    return existing.concepts.map((c) => Object.assign({}, c));
  }
  // Pré-remplissage depuis l'extraction pipeline (source="confirme_pipeline" par défaut).
  return (CURRENT.pipeline_extraction || []).map((c) => ({
    ontology_id: c.ontology_id,
    concept_name: c.concept_name,
    statut: c.statut || "present",
    source: "confirme_pipeline",
  }));
}

// Suggestions GPT-5.6 (second avis indépendant, cf. GOLDEN_EXTRACTION.md §5bis) :
// affichées séparément, PAS pré-cochées (l'expert doit les valider une à une).
function gpt56Suggestions() {
  const already = new Set(CONCEPTS.map((c) => (c.concept_name || "").toLowerCase()));
  return (CURRENT.gpt56_extraction || []).filter(
    (s) => !already.has((s.concept || "").toLowerCase())
  );
}

function renderItem() {
  $("#welcome").classList.add("hidden");
  $("#item-view").classList.remove("hidden");
  $("#item-title").textContent = `Cas ${CURRENT.cas} — ${CURRENT_ID}`;
  $("#item-double").textContent = CURRENT.double_annotation ? "👥 double annotation" : "";
  $("#item-double").classList.toggle("hidden", !CURRENT.double_annotation);
  $("#item-texte").textContent = CURRENT.reponse_texte || "";

  const toggle = $("#slot-toggle");
  toggle.classList.toggle("hidden", !CURRENT.double_annotation);
  $("#slot-1").classList.toggle("active", ACTIVE_SLOT === "annotation_expert");
  $("#slot-2").classList.toggle("active", ACTIVE_SLOT === "annotation_expert_2");

  const existing = CURRENT[ACTIVE_SLOT];
  $("#annotateur-name").value = (existing && existing.annotateur) || "";
  $("#item-status").textContent = existing ? `annoté par ${existing.annotateur || "?"}` : "en attente";

  CONCEPTS = conceptsForSlot();
  renderConceptList();
  renderGpt56Suggestions();
  renderReviewAlerts();
}

// Alertes de relecture qualité GPT-5.6 sur l'annotation déjà enregistrée
// (cf. GOLDEN_EXTRACTION.md §5ter) — purement informatif, à trier par l'expert.
function renderReviewAlerts() {
  let box = $("#review-alerts");
  if (!box) {
    box = el("div", "review-box");
    box.id = "review-alerts";
    $("#item-texte").insertAdjacentElement("afterend", box);
  }
  const review = (CURRENT.review || {})[ACTIVE_SLOT];
  if (!review || !review.alertes || !review.alertes.length) {
    box.innerHTML = "";
    box.classList.add("hidden");
    return;
  }
  box.classList.remove("hidden");
  const iconFor = (t) => ({
    omission: "➕", douteux: "❓", statut_a_verifier: "🔄", ok_mais_limite: "🟡",
  }[t] || "•");
  box.innerHTML =
    `<div class="review-title">⚠️ Relecture GPT-5.6 — ${escapeHtml(review.synthese || "")}</div>` +
    `<div class="review-hint">ℹ️ Les noms de concepts sont contraints par l'ontologie : une différence de formulation avec le texte n'est pas forcément une erreur.</div>` +
    review.alertes.map((a) =>
      `<div class="review-alert">${iconFor(a.type_probleme)} <b>${escapeHtml(a.concept)}</b> ` +
      `<span class="muted">[${escapeHtml(a.type_probleme)}]</span> — ${escapeHtml(a.commentaire)}</div>`
    ).join("");
}

function renderConceptList() {
  const box = $("#concept-list");
  box.innerHTML = "";
  CONCEPTS.forEach((c, i) => {
    const rowClass = c.source === "ajoute_gpt56" ? "from-gpt56"
      : c.source === "ajoute_expert" ? "added" : "from-pipeline";
    const row = el("div", "concept-row " + rowClass);
    row.innerHTML =
      `<span class="name">${escapeHtml(c.concept_name || c.ontology_id)}</span>` +
      `<select data-i="${i}" class="statut-select">
         <option value="present" ${c.statut === "present" ? "selected" : ""}>présent</option>
         <option value="absent" ${c.statut === "absent" ? "selected" : ""}>absent</option>
       </select>` +
      `<span class="del" data-i="${i}" title="Supprimer">✕</span>`;
    row.querySelector(".statut-select").addEventListener("change", (e) => {
      CONCEPTS[i].statut = e.target.value;
    });
    row.querySelector(".del").addEventListener("click", () => {
      CONCEPTS.splice(i, 1);
      renderConceptList();
    });
    box.appendChild(row);
  });
}

// Bandeau des suggestions GPT-5.6 (second avis indépendant) : cliquer une
// suggestion l'ajoute à CONCEPTS (source="ajoute_gpt56"), à valider ensuite
// comme n'importe quel concept (statut, suppression possible).
function renderGpt56Suggestions() {
  let box = $("#gpt56-suggestions");
  if (!box) {
    box = el("div", "gpt56-box");
    box.id = "gpt56-suggestions";
    $("#concept-list").insertAdjacentElement("afterend", box);
  }
  const suggestions = gpt56Suggestions();
  if (!suggestions.length) {
    box.innerHTML = "";
    box.classList.add("hidden");
    return;
  }
  box.classList.remove("hidden");
  box.innerHTML = `<div class="muted" style="margin:8px 0 4px">🤖 Suggestions GPT-5.6 (second avis indépendant, non pré-cochées) :</div>`;
  suggestions.forEach((s, i) => {
    const chip = el("span", "gpt56-chip",
      `${escapeHtml(s.concept)} <small>(${escapeHtml(s.statut || "present")})</small> ＋`);
    chip.title = s.justification || "";
    chip.addEventListener("click", () => {
      CONCEPTS.push({
        ontology_id: "",
        concept_name: s.concept,
        statut: s.statut || "present",
        source: "ajoute_gpt56",
      });
      renderConceptList();
      renderGpt56Suggestions();
    });
    box.appendChild(chip);
  });
}

let searchTimer = null;
function onSearchInput(e) {
  const q = e.target.value.trim();
  clearTimeout(searchTimer);
  if (!q) {
    $("#add-concept-results").classList.add("hidden");
    return;
  }
  searchTimer = setTimeout(async () => {
    const data = await apiFetch(`${API}/api/onto/search?q=${encodeURIComponent(q)}`).then((r) => r.json());
    const results = data.results || [];
    const box = $("#add-concept-results");
    box.innerHTML = "";
    if (!results.length) {
      box.classList.add("hidden");
      return;
    }
    results.forEach((r) => {
      const row = el("div", "", `${escapeHtml(r.name)} <span class="muted">(${escapeHtml(r.categorie || "")})</span>`);
      row.addEventListener("click", () => {
        CONCEPTS.push({
          ontology_id: r.id,
          concept_name: r.name,
          statut: "present",
          source: "ajoute_expert",
        });
        renderConceptList();
        $("#add-concept-input").value = "";
        box.classList.add("hidden");
      });
      box.appendChild(row);
    });
    box.classList.remove("hidden");
  }, 200);
}

async function saveAnnotation() {
  const annotateur = $("#annotateur-name").value.trim();
  $("#save-status").textContent = "Enregistrement…";
  try {
    const res = await apiFetch(`${API}/api/annotation/${CURRENT_ID}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ concepts: CONCEPTS, annotateur, slot: ACTIVE_SLOT }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    const data = await res.json();
    CURRENT[ACTIVE_SLOT] = data[ACTIVE_SLOT];
    $("#save-status").textContent = "✅ Enregistré.";
    await loadOverview();
    renderItemList();
  } catch (ex) {
    $("#save-status").textContent = `❌ ${ex.message}`;
  }
}

init();
