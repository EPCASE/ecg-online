/* app.js — logique front de l'ECG Lecture */
const API = "";                      // même origine
let CASES = [];
let ACTIVE_FAMILY = "all";
let CURRENT = null;

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, html) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
};

/* ─────────── Bootstrap ─────────── */
async function init() {
  await checkHealth();
  await loadCases();
  wireGlobal();
}

async function checkHealth() {
  const badge = $("#health-badge");
  try {
    const r = await fetch(`${API}/api/health`);
    const h = await r.json();
    if (h.openai_key) {
      badge.textContent = `IA prête · ${h.model.replace("gpt-", "GPT-")}`;
      badge.className = "badge badge-ok";
    } else {
      badge.textContent = "Clé OpenAI absente";
      badge.className = "badge badge-bad";
    }
  } catch {
    badge.textContent = "hors ligne";
    badge.className = "badge badge-bad";
  }
}

async function loadCases() {
  const [cases, fams] = await Promise.all([
    fetch(`${API}/api/cases`).then((r) => r.json()),
    fetch(`${API}/api/families`).then((r) => r.json()),
  ]);
  CASES = cases;
  $("#cases-count").textContent = `${cases.length} cas`;
  renderFilters(fams);
  renderCaseList();
}

/* ─────────── Filtres familles ─────────── */
function renderFilters(fams) {
  const box = $("#family-filters");
  box.innerHTML = "";
  const mkChip = (label, value, count) => {
    const c = el("button", "filter-chip" + (value === ACTIVE_FAMILY ? " active" : ""),
      `${label}${count != null ? ` <b>${count}</b>` : ""}`);
    c.onclick = () => { ACTIVE_FAMILY = value; renderFilters(fams); renderCaseList(); };
    return c;
  };
  box.appendChild(mkChip("Tous", "all", CASES.length));
  fams.forEach((f) => box.appendChild(mkChip(f.famille, f.famille, f.count)));
}

/* ─────────── Liste des cas ─────────── */
function renderCaseList() {
  const list = $("#case-list");
  list.innerHTML = "";
  const filtered = CASES.filter((c) => ACTIVE_FAMILY === "all" || c.famille === ACTIVE_FAMILY);
  filtered.forEach((c) => {
    const item = el("li", "case-item" + (CURRENT && CURRENT.num === c.num ? " active" : ""));
    item.innerHTML =
      `<span class="n">${c.num}</span>` +
      `<div><div class="t">${escapeHtml(c.titre || "Cas ECG")}</div>` +
      `<div class="fam">${c.famille || ""}</div></div>`;
    item.onclick = () => openCase(c.num);
    list.appendChild(item);
  });
}

/* ─────────── Ouverture d'un cas ─────────── */
async function openCase(num) {
  const c = await fetch(`${API}/api/case/${num}`).then((r) => r.json());
  CURRENT = c;
  renderCaseList();
  $("#welcome").classList.add("hidden");
  const view = $("#case-view");
  view.classList.remove("hidden");

  $("#case-family").textContent = c.famille || "";
  $("#case-title").textContent = c.titre || "Cas ECG";
  $("#case-num").textContent = "#" + c.num;
  const ctx = [c.patient, c.contexte].filter(Boolean).join("\n").trim();
  $("#case-context").textContent = ctx || "—";

  const gal = $("#case-images");
  gal.innerHTML = "";
  (c.images || []).forEach((img) => {
    const im = el("img");
    im.src = `${API}/images/${img}`;
    im.alt = `Tracé ECG cas ${c.num}`;
    im.loading = "lazy";
    im.onclick = () => openLightbox(im.src);
    gal.appendChild(im);
  });

  $("#answer").value = "";
  $("#result").classList.add("hidden");
  $("#result").innerHTML = "";
  view.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ─────────── Correction ─────────── */
async function gradeCurrent() {
  if (!CURRENT) return;
  const answer = $("#answer").value.trim();
  if (!answer) { $("#answer").focus(); return; }

  const btn = $("#grade-btn");
  btn.disabled = true;
  btn.querySelector(".btn-label").textContent = "Correction en cours…";
  btn.querySelector(".spinner").classList.remove("hidden");

  try {
    const r = await fetch(`${API}/api/grade`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ num: CURRENT.num, answer }),
    });
    const data = await r.json();
    if (data.error) throw new Error(data.error);
    renderResult(data);
  } catch (e) {
    $("#result").classList.remove("hidden");
    $("#result").innerHTML =
      `<div class="result-top"><div class="verdict"><h3 class="badge-error">Erreur</h3>` +
      `<p>${escapeHtml(e.message || "correction impossible")}</p></div></div>`;
  } finally {
    btn.disabled = false;
    btn.querySelector(".btn-label").textContent = "Corriger ma réponse";
    btn.querySelector(".spinner").classList.add("hidden");
  }
}

function scoreColor(s) {
  if (s >= 75) return "var(--good)";
  if (s >= 50) return "var(--warn)";
  return "var(--bad)";
}

function renderResult(d) {
  const box = $("#result");
  box.classList.remove("hidden");

  const found = (d.elements_trouves || []).map(
    (e) => `<li><span class="rang ${e.rang}">${e.rang}</span>${escapeHtml(e.label)}</li>`
  ).join("") || `<li class="empty">Rien de notable relevé.</li>`;

  const missed = (d.elements_manques || []).map(
    (e) => `<li><span class="rang ${e.rang}">${e.rang}</span>${escapeHtml(e.label)}` +
           (e.importance ? ` <span class="corr">— ${escapeHtml(e.importance)}</span>` : "") + `</li>`
  ).join("") || `<li class="empty">Rien d'important n'a été oublié 🎉</li>`;

  const wrong = (d.elements_errones || []).map(
    (e) => `<li><b>${escapeHtml(e.label)}</b> <span class="corr">→ ${escapeHtml(e.correction)}</span></li>`
  ).join("") || `<li class="empty">Aucune erreur factuelle.</li>`;

  const ref = d.reference || {};
  const corresp = d.correspondance || "";
  const typeErr = d.type_erreur || "";
  const correspLabel = {
    exacte: "✓ exacte", acceptable: "≈ acceptable",
    partielle: "◐ partielle", incorrecte: "✗ incorrecte",
  }[corresp] || corresp;
  const typeLabel = {
    aucune: "aucune erreur", etudiant: "erreur clinique",
    incomplet: "réponse incomplète", formulation: "formulation",
  }[typeErr] || typeErr;

  box.innerHTML = `
    <div class="result-top">
      <div class="score-ring" style="--val:${d.score};--ring-color:${scoreColor(d.score)}">
        <div><span>${d.score}</span><small>/ 100</small></div>
      </div>
      <div class="verdict">
        <h3>${escapeHtml(d.verdict || "")}</h3>
        <div class="dx-line">Diagnostic retenu : <b>${escapeHtml(d.diagnostic_retenu || "—")}</b></div>
        <div class="subscores">
          <span class="sub">Diagnostic <b>${d.score_diagnostic ?? "—"}</b></span>
          <span class="sub">Description <b>${d.score_descriptif ?? "—"}</b></span>
          ${corresp ? `<span class="tag tag-${corresp}">${correspLabel}</span>` : ""}
          ${typeErr ? `<span class="tag tag-err-${typeErr}">${typeLabel}</span>` : ""}
        </div>
      </div>
    </div>

    <div class="cards">
      <div class="card found"><h4>✓ Éléments trouvés</h4><ul>${found}</ul></div>
      <div class="card missed"><h4>◐ À compléter</h4><ul>${missed}</ul></div>
      <div class="card wrong"><h4>✗ À corriger</h4><ul>${wrong}</ul></div>
    </div>

    <div class="comment-box">
      <h4>💬 Commentaire de l'enseignant IA</h4>
      <div class="md">${mdToHtml(d.commentaire || "")}</div>
    </div>

    <details class="reference">
      <summary>📖 Voir l'interprétation de référence</summary>
      <div class="ref-body">
        <h5>Interprétation attendue</h5>${escapeHtml(ref.interpretation_ref || "—")}
        ${ref.commentaires ? `\n\n<h5>Commentaires</h5>${escapeHtml(ref.commentaires)}` : ""}
      </div>
    </details>
  `;
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ─────────── Lightbox ─────────── */
function openLightbox(src) {
  $("#lightbox-img").src = src;
  $("#lightbox").classList.remove("hidden");
}

/* ─────────── Divers ─────────── */
function wireGlobal() {
  $("#grade-btn").onclick = gradeCurrent;
  $("#clear-btn").onclick = () => {
    $("#answer").value = "";
    $("#result").classList.add("hidden");
    $("#answer").focus();
  };
  $("#lightbox").onclick = () => $("#lightbox").classList.add("hidden");
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") $("#lightbox").classList.add("hidden");
    if (e.key === "Enter" && e.ctrlKey) gradeCurrent();
  });
}

function escapeHtml(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/* mini markdown : **gras**, *italique*, puces, retours ligne */
function mdToHtml(s) {
  let h = escapeHtml(s);
  h = h.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  h = h.replace(/\*(.+?)\*/g, "<em>$1</em>");
  const lines = h.split("\n");
  let out = "", inList = false;
  for (const ln of lines) {
    if (/^\s*[-•]\s+/.test(ln)) {
      if (!inList) { out += "<ul>"; inList = true; }
      out += "<li>" + ln.replace(/^\s*[-•]\s+/, "") + "</li>";
    } else {
      if (inList) { out += "</ul>"; inList = false; }
      if (ln.trim()) out += "<p>" + ln + "</p>";
    }
  }
  if (inList) out += "</ul>";
  return out;
}

init();
