/* app.js — logique front de l'ECG Lecture */
const API = "";                      // même origine
let CASES = [];
let ACTIVE_FAMILY = "all";
let CURRENT = null;
let CURRENT_QCM = null;              // QCM du cas courant (question + options)
let QCM_SELECTED = new Set();        // lettres cochées

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

  // Réinitialise le mode + charge le QCM du cas
  setMode("free");
  await loadQcm(c.num);

  view.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ─────────── Bascule de mode (libre / QCM) ─────────── */
function setMode(mode) {
  const isQcm = mode === "qcm";
  $("#mode-free").classList.toggle("active", !isQcm);
  $("#mode-qcm").classList.toggle("active", isQcm);
  $("#free-block").classList.toggle("hidden", isQcm);
  $("#result").classList.toggle("hidden", isQcm || $("#result").innerHTML === "");
  $("#qcm-block").classList.toggle("hidden", !isQcm);
}

async function loadQcm(num) {
  CURRENT_QCM = null;
  QCM_SELECTED = new Set();
  const btn = $("#mode-qcm");
  try {
    const r = await fetch(`${API}/api/case/${num}/qcm`);
    if (!r.ok) throw new Error("no qcm");
    CURRENT_QCM = await r.json();
    btn.disabled = false;
    btn.title = "";
    renderQcm();
  } catch {
    // Pas de QCM pour ce cas : on désactive le bouton
    btn.disabled = true;
    btn.title = "Pas de QCM pour ce cas";
    $("#qcm-question").textContent = "";
    $("#qcm-options").innerHTML = "";
  }
}

function renderQcm() {
  if (!CURRENT_QCM) return;
  $("#qcm-question").textContent = CURRENT_QCM.question || "Sur ce tracé :";
  const hint = CURRENT_QCM.multiple
    ? "Plusieurs réponses possibles."
    : "Une seule réponse.";
  const list = $("#qcm-options");
  list.innerHTML = "";
  (CURRENT_QCM.options || []).forEach((opt, i) => {
    const letter = CURRENT_QCM.letters[i];
    const li = el("li", "qcm-option");
    li.dataset.letter = letter;
    li.innerHTML =
      `<span class="qcm-check">${QCM_SELECTED.has(letter) ? "✓" : ""}</span>` +
      `<span class="qcm-text">${escapeHtml(stripLetter(opt))}</span>` +
      `<span class="qcm-letter">${letter}</span>`;
    li.classList.toggle("selected", QCM_SELECTED.has(letter));
    li.onclick = () => toggleQcm(letter);
    list.appendChild(li);
  });
  $("#qcm-result").classList.add("hidden");
  $("#qcm-result").innerHTML = "";
  const q = $("#qcm-question");
  q.dataset.hint = hint;
}

function stripLetter(opt) {
  return String(opt).replace(/^\s*[A-Ea-e]\s*[.)-]\s*/, "");
}

function toggleQcm(letter) {
  if (QCM_SELECTED.has(letter)) QCM_SELECTED.delete(letter);
  else QCM_SELECTED.add(letter);
  renderQcm();
}

async function submitQcm() {
  if (!CURRENT || !CURRENT_QCM) return;
  const selected = [...QCM_SELECTED];
  const btn = $("#qcm-submit");
  btn.disabled = true;
  try {
    const r = await fetch(`${API}/api/case/${CURRENT.num}/qcm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ selected }),
    });
    const data = await r.json();
    if (data.error) throw new Error(data.error);
    renderQcmResult(data);
  } catch (e) {
    $("#qcm-result").classList.remove("hidden");
    $("#qcm-result").innerHTML =
      `<div class="qcm-verdict bad">Erreur : ${escapeHtml(e.message || "correction impossible")}</div>`;
  } finally {
    btn.disabled = false;
  }
}

function renderQcmResult(d) {
  // Colorise chaque option selon son statut
  const statusIcon = { correct: "✓", missed: "◯", wrong: "✕", neutral: "" };
  document.querySelectorAll("#qcm-options .qcm-option").forEach((li) => {
    const letter = li.dataset.letter;
    const po = (d.per_option || []).find((p) => p.letter === letter);
    li.classList.remove("selected");
    li.classList.remove("st-correct", "st-missed", "st-wrong", "st-neutral");
    if (po) {
      li.classList.add("st-" + po.status);
      li.querySelector(".qcm-check").textContent = statusIcon[po.status] || "";
    }
    li.onclick = null;           // fige après validation
  });
  const box = $("#qcm-result");
  box.classList.remove("hidden");
  const scoreCls = d.correct ? "good" : (d.score >= 50 ? "warn" : "bad");
  const title = d.correct
    ? "🎉 Bravo, réponse exacte !"
    : (d.score >= 50 ? "Presque : réponse partielle." : "Réponse incorrecte.");
  box.innerHTML =
    `<div class="qcm-verdict ${scoreCls}">` +
      `<span class="qcm-score">${d.score}<small>/100</small></span>` +
      `<div><b>${title}</b>` +
      `<div class="qcm-expected">Bonnes réponses : <b>${(d.expected || []).join(", ") || "—"}</b></div>` +
      `</div></div>` +
    `<div class="qcm-legend">` +
      `<span><i class="st-correct"></i> juste</span>` +
      `<span><i class="st-missed"></i> oublié</span>` +
      `<span><i class="st-wrong"></i> à tort</span>` +
    `</div>`;
  box.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function resetQcm() {
  QCM_SELECTED = new Set();
  renderQcm();
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
      <summary><span class="ref-ic">📖</span> Voir l'interprétation de référence de l'enseignant</summary>
      <div class="ref-body">
        ${renderReferenceBody(ref)}
      </div>
    </details>
  `;
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ─────────── Mise en page « référence enseignant » ─────────── */
// Découpe un bloc de texte de l'enseignant en lignes/puces lisibles.
function textToBullets(txt) {
  if (!txt) return "";
  const lines = String(txt)
    .split(/\n+/)
    .map((l) => l.trim())
    .filter(Boolean);
  if (lines.length <= 1) {
    // Un seul paragraphe : on le rend tel quel (pas de fausse liste).
    return `<p>${escapeHtml(lines[0] || txt)}</p>`;
  }
  const items = lines.map((l) => `<li>${escapeHtml(l)}</li>`).join("");
  return `<ul class="ref-list">${items}</ul>`;
}

function renderReferenceBody(ref) {
  ref = ref || {};
  const blocks = [];

  // 1) Interprétation attendue (souvent une intro + une liste de constats)
  const interp = (ref.interpretation_ref || "").trim();
  if (interp) {
    // La 1ʳᵉ ligne est en général une phrase d'accroche ("Ce tracé met en évidence :")
    const parts = interp.split(/\n+/).map((s) => s.trim()).filter(Boolean);
    let intro = "", rest = parts;
    if (parts.length > 1 && /:\s*$/.test(parts[0])) {
      intro = parts[0];
      rest = parts.slice(1);
    }
    const body = rest.length > 1
      ? `<ul class="ref-list">${rest.map((l) => `<li>${escapeHtml(l)}</li>`).join("")}</ul>`
      : `<p>${escapeHtml(rest.join(" "))}</p>`;
    blocks.push(
      `<section class="ref-section ref-interp">` +
        `<h5><span class="ref-dot interp"></span> Interprétation attendue</h5>` +
        (intro ? `<p class="ref-intro">${escapeHtml(intro)}</p>` : "") +
        body +
      `</section>`
    );
  }

  // 2) Commentaires pédagogiques (texte dense → paragraphes aérés)
  const comm = (ref.commentaires || "").trim();
  if (comm) {
    const paras = comm.split(/\n+/).map((s) => s.trim()).filter(Boolean)
      .map((p) => `<p>${escapeHtml(p)}</p>`).join("");
    blocks.push(
      `<section class="ref-section ref-comment">` +
        `<h5><span class="ref-dot comment"></span> Pour aller plus loin</h5>` +
        `<div class="ref-prose">${paras}</div>` +
      `</section>`
    );
  }

  return blocks.join("") || `<p class="empty">Référence non disponible.</p>`;
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
  // Bascule de mode
  $("#mode-free").onclick = () => setMode("free");
  $("#mode-qcm").onclick = () => { if (!$("#mode-qcm").disabled) setMode("qcm"); };
  // QCM
  $("#qcm-submit").onclick = submitQcm;
  $("#qcm-reset").onclick = resetQcm;
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
