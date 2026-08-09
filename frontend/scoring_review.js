/* scoring_review.js — page d'annotation solo + second avis IA du golden
 * conceptuel de scoring V2 (P1.3 simplifié, cf.
 * audit_doc/roadmap_scientifique_2026.md §P1.3). Un seul relecteur humain
 * valide/corrige les critères de chaque cas ECG (tracé + texte de référence
 * affichés), puis peut demander un second avis GPT qui signale les points
 * douteux directement sur les critères concernés — pas de second relecteur
 * humain ni d'étape d'adjudication séparée. */
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

let OVERVIEW = [];
let CURRENT = null;       // {case_id, pilot_criteria, expert_1, ai_review, ai_suggested_criteria, ecg}
let CURRENT_ID = null;
let CRITERIA = [];        // état de travail (critères du relecteur)
let ONTO_CACHE = new Map(); // query -> [{id, name, categorie}] (autocomplétion concept_id)

async function init() {
  await loadOverview();
  $("#save-btn").addEventListener("click", saveCurrent);
  $("#ai-review-btn").addEventListener("click", requestAiReview);
  $("#ai-suggest-btn").addEventListener("click", requestAiSuggest);
  $("#add-criterion-btn").addEventListener("click", () => addCriterion());
}

async function loadOverview() {
  const data = await apiFetch(`${API}/api/scoring-review/overview`).then((r) => r.json());
  OVERVIEW = data.cases || [];
  $("#items-count").textContent = `${OVERVIEW.length} cas`;
  renderItemList();
}

function statusIcon(status) {
  if (status === "reviewed") return '<span class="status-reviewed">✓</span>';
  if (status === "annotated") return '<span class="status-annotated">✎</span>';
  return '<span class="status-pending">○</span>';
}

function renderItemList() {
  const list = $("#item-list");
  list.innerHTML = "";
  OVERVIEW.forEach((it) => {
    const li = el("li", CURRENT_ID === it.case_id ? "active" : "");
    const alertBadge = it.n_alertes
      ? `<span class="alert-badge" title="${it.n_alertes} alerte(s) IA">🤖 ${it.n_alertes}</span> `
      : "";
    li.innerHTML = `${statusIcon(it.status)} <b>Cas ${it.case_id}</b> ` +
      `${alertBadge}<br>` +
      `<span class="muted" style="font-size:.75rem">${escapeHtml(it.label)} · ${it.n_criteria_pilot} critères</span>`;
    li.addEventListener("click", () => selectItem(it.case_id));
    list.appendChild(li);
  });
}

async function selectItem(caseId) {
  CURRENT_ID = caseId;
  const data = await apiFetch(`${API}/api/scoring-review/${caseId}`).then((r) => r.json());
  CURRENT = data;
  renderItemList();
  renderItem();
}

function criteriaForWork() {
  const existing = CURRENT.expert_1;
  if (existing && Array.isArray(existing.criteria)) {
    return existing.criteria.map((c) => Object.assign({}, c));
  }
  // Pré-remplissage : le pilote solo P1.2, à confirmer/corriger.
  return (CURRENT.pilot_criteria || []).map((c) => Object.assign({}, c));
}

function renderEcgPanel() {
  const ecg = CURRENT.ecg || {};
  const imgBox = $("#ecg-img-box");
  imgBox.innerHTML = (ecg.images || []).map((name) =>
    `<img src="/images/${encodeURIComponent(name)}" alt="Tracé ECG cas ${CURRENT_ID}">`
  ).join("") || '<p class="muted">Aucun tracé disponible pour ce cas.</p>';
  $("#ecg-patient").textContent = ecg.titre || `Cas ${CURRENT_ID}`;
  $("#ecg-contexte").textContent = [ecg.patient, ecg.contexte].filter(Boolean).join(" — ");
  $("#ecg-interpretation").textContent = ecg.interpretation_ref || "(non disponible)";
}

function renderItem() {
  $("#welcome").classList.add("hidden");
  $("#item-view").classList.remove("hidden");
  const meta = OVERVIEW.find((o) => o.case_id === CURRENT_ID) || {};
  $("#item-title").textContent = `Cas ${CURRENT_ID}`;
  $("#item-label").textContent = meta.label || "";

  const existing = CURRENT.expert_1;
  $("#annotateur-name").value = (existing && existing.annotateur) || "";
  $("#item-status").textContent = existing
    ? `annoté par ${existing.annotateur || "?"}`
    : "en attente d'annotation";

  renderEcgPanel();
  CRITERIA = criteriaForWork();
  renderAiBox();
  renderSuggestBox();
  renderCriteriaList();
}

function alertsForCriterion(criterionId) {
  const ai = CURRENT.ai_review;
  if (!ai || !Array.isArray(ai.alertes)) return [];
  return ai.alertes.filter((a) => a.criterion_id === criterionId);
}

// Alertes IA non rattachées à un critère existant (omissions notamment :
// criterion_id vide car le critère n'existe pas encore) — sinon elles ne
// s'affichent nulle part puisqu'aucune carte ne correspond.
function unattachedAlerts() {
  const ai = CURRENT.ai_review;
  if (!ai || !Array.isArray(ai.alertes)) return [];
  const knownIds = new Set(CRITERIA.map((c) => c.criterion_id));
  return ai.alertes.filter((a) => !a.criterion_id || !knownIds.has(a.criterion_id));
}

function blankCriterion() {
  return {
    criterion_id: `case_${CURRENT_ID}_nouveau_${Date.now().toString(36)}`,
    concept_id: "",
    label: "",
    role: "optional",
    expected_status: "present",
    importance: "intermediate",
    error_severity: "minor",
    alternative_group: null,
    group_logic: "ALL",
    group_min_n: null,
    sufficient_alone: false,
    minimum_specificity: "exact_only",
    expert_confidence: "medium",
    evidence_source: "single_expert",
    comment: "",
  };
}

function addCriterion(prefill) {
  const c = Object.assign(blankCriterion(), prefill || {});
  CRITERIA.push(c);
  renderCriteriaList();
  renderAiBox();
  renderSuggestBox();
  const cards = document.querySelectorAll(".crit-card");
  const last = cards[cards.length - 1];
  if (last) last.scrollIntoView({ behavior: "smooth", block: "center" });
}

// ─────────────── Passe IA "premier jet" : génère des critères candidats
// directement depuis le texte de référence, à relire/valider un par un.
async function requestAiSuggest() {
  if (!CURRENT_ID) return;
  $("#save-status").textContent = "🤖 L'IA propose des critères à partir du texte de référence…";
  try {
    const res = await apiFetch(`${API}/api/scoring-review/${CURRENT_ID}/ai-suggest`, { method: "POST" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || err.description || `HTTP ${res.status}`);
    }
    const data = await res.json();
    CURRENT.ai_suggested_criteria = data.ai_suggested_criteria;
    renderSuggestBox();
    $("#save-status").textContent = "✅ Critères candidats générés — relis et ajoute ceux qui te semblent pertinents.";
    await loadOverview();
    renderItemList();
  } catch (ex) {
    $("#save-status").textContent = `❌ ${ex.message}`;
  }
}

function knownCriterionKeys() {
  // concept_id + label, pour éviter de proposer un doublon déjà ajouté.
  return new Set(CRITERIA.map((c) => `${c.concept_id}|${c.label}`));
}

function suggestionKey(c) {
  // Les suggestions non résolues n'ont pas encore de concept_id -> on clé
  // sur le nom clinique proposé par l'IA, stable tant que non traité.
  return `${c.concept_name_propose || c.concept_id}|${c.label}`;
}

function renderSuggestBox() {
  const box = $("#suggest-box");
  const sug = CURRENT.ai_suggested_criteria;
  if (!sug || !Array.isArray(sug.criteria) || !sug.criteria.length) {
    box.classList.add("hidden");
    box.innerHTML = "";
    return;
  }
  const known = knownCriterionKeys();
  const remaining = sug.criteria.filter((c) => !known.has(`${c.concept_id}|${c.label}`));
  if (!remaining.length) {
    box.classList.add("hidden");
    box.innerHTML = "";
    return;
  }
  box.classList.remove("hidden");
  box.innerHTML = `<div class="suggest-title">💡 Critères candidats proposés par l'IA (${escapeHtml(sug.model || "")}) — chaque concept est vérifié contre l'ontologie ; à relire et valider :</div>` +
    remaining.map((c, idx) => {
      const candidates = c.onto_candidates || [];
      const resolvedBadge = c.resolved
        ? `<span class="onto-badge onto-badge-ok">✅ ${escapeHtml(c.concept_id)} (dans l'ontologie)</span>`
        : `<span class="onto-badge onto-badge-warn">⚠️ absent de l'ontologie — à discuter</span>`;
      const candidatesHtml = !c.resolved && candidates.length ? `
        <div class="onto-candidates">
          <label style="font-size:.7rem;color:#64748b;font-weight:700">Concept proposé par l'IA : « ${escapeHtml(c.concept_name_propose || "")} » — piste la plus proche trouvée dans l'ontologie :</label>
          <select class="onto-candidate-select" data-idx="${idx}">
            <option value="">— aucune piste ne convient, créer un nouveau concept —</option>
            ${candidates.map((m) => `<option value="${escapeHtml(m.id)}">${escapeHtml(m.name)} (${escapeHtml(m.id)}, score ${m.score}${m.categorie ? ", " + escapeHtml(m.categorie) : ""})</option>`).join("")}
          </select>
        </div>` : (!c.resolved ? `
        <div class="onto-candidates">
          <label style="font-size:.7rem;color:#64748b;font-weight:700">Aucune piste trouvée dans l'ontologie pour « ${escapeHtml(c.concept_name_propose || "")} ».</label>
        </div>` : "");
      const newIdHtml = !c.resolved ? `
        <div class="onto-candidates">
          <label style="font-size:.7rem;color:#64748b;font-weight:700">…ou nouvel identifiant à créer dans l'ontologie (à discuter avant ajout définitif) :</label>
          <input type="text" class="onto-new-id" data-idx="${idx}" placeholder="ex. NOUVEAU_CONCEPT_ID" value="">
        </div>` : "";
      return `
      <div class="suggest-row" data-idx="${idx}">
        <div class="suggest-row-main">
          <b>${escapeHtml(c.label)}</b>
          <span class="muted" style="font-size:.75rem">role=${escapeHtml(c.role)} · importance=${escapeHtml(c.importance)}</span>
          <div>${resolvedBadge}</div>
          ${candidatesHtml}
          ${newIdHtml}
          <p class="muted" style="font-size:.78rem;margin:4px 0 0">${escapeHtml(c.comment || "")}</p>
        </div>
        <div class="suggest-row-actions">
          <button type="button" class="btn-primary btn-accept-suggestion" data-idx="${idx}">✅ Ajouter</button>
          <button type="button" class="btn-ghost btn-reject-suggestion" data-idx="${idx}">✕ Ignorer</button>
        </div>
      </div>`;
    }).join("");

  box.querySelectorAll(".btn-accept-suggestion").forEach((btn) => {
    btn.addEventListener("click", () => {
      const idx = Number(btn.dataset.idx);
      const c = remaining[idx];
      const row = box.querySelector(`.suggest-row[data-idx="${idx}"]`);
      let concept_id = c.concept_id;
      if (!c.resolved) {
        const sel = row.querySelector(".onto-candidate-select");
        const newIdInput = row.querySelector(".onto-new-id");
        const chosen = (sel && sel.value) || "";
        const typed = (newIdInput && newIdInput.value.trim()) || "";
        concept_id = chosen || typed;
        if (!concept_id) {
          alert("Choisis une piste ontologique ou saisis un nouvel identifiant avant d'ajouter ce critère (concept absent de l'ontologie — à trancher).");
          return;
        }
      }
      addCriterion(Object.assign({}, c, {
        concept_id,
        criterion_id: `case_${CURRENT_ID}_${concept_id.toLowerCase()}`,
      }));
    });
  });
  box.querySelectorAll(".btn-reject-suggestion").forEach((btn) => {
    btn.addEventListener("click", () => {
      const c = remaining[Number(btn.dataset.idx)];
      // Marque comme "connu" localement pour la masquer sans la supprimer
      // du stockage serveur (traçabilité de ce qui a été proposé).
      const key = suggestionKey(c);
      CURRENT.ai_suggested_criteria.criteria = CURRENT.ai_suggested_criteria.criteria
        .filter((x) => suggestionKey(x) !== key);
      renderSuggestBox();
    });
  });
}

function renderAiBox() {
  const box = $("#ai-box");
  const ai = CURRENT.ai_review;
  if (!ai) {
    box.classList.add("hidden");
    box.innerHTML = "";
    return;
  }
  box.classList.remove("hidden");
  const nAlertes = (ai.alertes || []).length;
  const unattached = unattachedAlerts();
  box.innerHTML = `<div class="ai-title">🤖 Second avis IA (${escapeHtml(ai.model || "")}, ${escapeHtml(ai.generated_at || "")})</div>` +
    `<p>${escapeHtml(ai.synthese || "")}</p>` +
    (nAlertes
      ? `<p>${nAlertes} alerte(s) — repérées ci-dessous, sur les cartes concernées (surlignées en rouge). Corrige si tu es convaincu, sinon ignore.</p>`
      : `<p class="ai-empty">Aucune alerte : l'IA n'a rien trouvé à signaler sur ces critères.</p>`) +
    (unattached.length
      ? `<div class="ai-omissions">` +
        unattached.map((a, idx) => `
          <div class="ai-omission-row">
            <b>${escapeHtml(a.type_probleme)}</b> — ${escapeHtml(a.commentaire)}
            ${a.type_probleme === "omission"
              ? `<button type="button" class="btn-ghost btn-add-omission" data-idx="${idx}">➕ Créer ce critère${a.label_suggere ? ` : « ${escapeHtml(a.label_suggere)} »` : ""}</button>`
              : ""}
          </div>`).join("") +
        `</div>`
      : "");

  box.querySelectorAll(".btn-add-omission").forEach((btn) => {
    btn.addEventListener("click", () => {
      const a = unattached[Number(btn.dataset.idx)];
      addCriterion({
        concept_id: a.concept_suggere || "",
        label: a.label_suggere || a.commentaire || "",
        comment: `Ajouté suite à une alerte IA (omission) : ${a.commentaire}`,
      });
    });
  });
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
    const alerts = alertsForCriterion(c.criterion_id);
    const card = el("div", "crit-card" + (alerts.length ? " has-alert" : ""));
    card.innerHTML = `
      <div class="crit-head">
        <span class="cid">${escapeHtml(c.criterion_id)}</span>
        <span class="label">${escapeHtml(c.label)}</span>
      </div>
      <div class="crit-grid">
        <div class="crit-field"><label>Concept ID (ontologie)</label>
          <input type="text" data-i="${i}" data-field="concept_id" class="concept-search" list="onto-list-${i}"
                 value="${escapeHtml(c.concept_id)}" placeholder="Tape pour chercher…" autocomplete="off">
          <datalist id="onto-list-${i}"></datalist></div>
        <div class="crit-field"><label>Rôle</label>${selectHtml("role", c.role, i)}</div>
        <div class="crit-field"><label>Statut attendu</label>${selectHtml("expected_status", c.expected_status, i)}</div>
        <div class="crit-field"><label>Importance</label>${selectHtml("importance", c.importance, i)}</div>
        <div class="crit-field"><label>Gravité erreur</label>${selectHtml("error_severity", c.error_severity, i)}</div>
        <div class="crit-field"><label>Logique groupe</label>${selectHtml("group_logic", c.group_logic, i)}</div>
        <div class="crit-field"><label>Groupe alternatif</label>
          <input type="text" data-i="${i}" data-field="alternative_group" value="${escapeHtml(c.alternative_group || "")}"></div>
        <div class="crit-field"><label>Seuil (AT_LEAST_N)</label>
          <input type="number" min="1" data-i="${i}" data-field="group_min_n" value="${c.group_min_n == null ? "" : c.group_min_n}"></div>
        <div class="crit-field"><label>Spécificité min.</label>${selectHtml("minimum_specificity", c.minimum_specificity, i)}</div>
        <div class="crit-field checkbox">
          <input type="checkbox" id="suf-${i}" data-i="${i}" data-field="sufficient_alone" ${c.sufficient_alone ? "checked" : ""}>
          <label for="suf-${i}">Suffit seul</label></div>
        <div class="crit-field"><label>Confiance experte</label>${selectHtml("expert_confidence", c.expert_confidence, i)}</div>
        <div class="crit-field"><label>Origine (evidence_source)</label>${selectHtml("evidence_source", c.evidence_source, i)}</div>
      </div>
      <div class="crit-comment">
        <label style="font-size:.7rem;text-transform:uppercase;color:#64748b;font-weight:700">Commentaire</label>
        <textarea data-i="${i}" data-field="comment" rows="2">${escapeHtml(c.comment || "")}</textarea>
      </div>
      ${alerts.map((a) => `<div class="crit-alert"><b>${escapeHtml(a.type_probleme)}</b> — ${escapeHtml(a.commentaire)}</div>`).join("")}`;

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
    wireConceptAutocomplete(card.querySelector(".concept-search"), i);
    box.appendChild(card);
  });
}

function wireConceptAutocomplete(input, idx) {
  if (!input) return;
  let timer = null;
  input.addEventListener("input", (e) => {
    const q = e.target.value.trim();
    if (timer) clearTimeout(timer);
    if (q.length < 2) return;
    timer = setTimeout(() => fillOntoDatalist(q, idx), 250);
  });
}

async function fillOntoDatalist(q, idx) {
  let results;
  if (ONTO_CACHE.has(q)) {
    results = ONTO_CACHE.get(q);
  } else {
    try {
      const res = await apiFetch(`/api/onto/search?q=${encodeURIComponent(q)}&limit=15`);
      results = (res && res.available && res.results) ? res.results : [];
    } catch (err) {
      results = [];
    }
    ONTO_CACHE.set(q, results);
  }
  const dl = document.getElementById(`onto-list-${idx}`);
  if (!dl) return;
  dl.innerHTML = results.map((r) =>
    `<option value="${escapeHtml(r.id)}">${escapeHtml(r.name || "")} ${r.categorie ? "(" + escapeHtml(r.categorie) + ")" : ""}</option>`
  ).join("");
}

async function saveCurrent() {
  const who = $("#annotateur-name").value.trim();
  $("#save-status").textContent = "Enregistrement…";
  try {
    const res = await apiFetch(`${API}/api/scoring-review/${CURRENT_ID}/expert_1`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ criteria: CRITERIA, annotateur: who }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || err.description || `HTTP ${res.status}`);
    }
    const data = await res.json();
    CURRENT.expert_1 = data.expert_1;
    $("#save-status").textContent = "✅ Enregistré.";
    await loadOverview();
    renderItemList();
  } catch (ex) {
    $("#save-status").textContent = `❌ ${ex.message}`;
  }
}

async function requestAiReview() {
  if (!CURRENT || !CURRENT.expert_1) {
    $("#save-status").textContent = "⏳ Enregistre d'abord ton annotation avant de demander un avis IA.";
    return;
  }
  $("#save-status").textContent = "🤖 L'IA relit tes critères…";
  try {
    const res = await apiFetch(`${API}/api/scoring-review/${CURRENT_ID}/ai-review`, { method: "POST" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || err.description || `HTTP ${res.status}`);
    }
    const data = await res.json();
    CURRENT.ai_review = data.ai_review;
    renderAiBox();
    renderCriteriaList();
    $("#save-status").textContent = "✅ Avis IA reçu.";
    await loadOverview();
    renderItemList();
  } catch (ex) {
    $("#save-status").textContent = `❌ ${ex.message}`;
  }
}

init();
