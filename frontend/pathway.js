/* pathway.js — interface autonome du micro-parcours BAV. */
(() => {
  "use strict";

  const API = "";
  const CONFIG_URL = "/static/pedagogy-bav.json";
  const STORAGE_PREFIX = "ecg_pathway_v1_";
  const SESSION_KEY = "ecg_pathway_session";
  const Core = window.ECGPathwayCore;

  let config = null;
  let state = null;
  let currentDefinition = null;
  let currentCase = null;
  let openedAt = 0;
  let initialLockedAt = 0;
  let hintsUsed = 0;

  const $ = (selector) => document.querySelector(selector);

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function simpleMarkdown(value) {
    const safe = escapeHtml(value || "");
    return safe
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/^[-•]\s+(.+)$/gm, "<li>$1</li>")
      .replace(/(?:<li>.*<\/li>\n?)+/g, (block) => `<ul>${block}</ul>`)
      .replace(/\n/g, "<br>");
  }

  function storageKey() {
    return STORAGE_PREFIX + config.id;
  }

  function saveState() {
    localStorage.setItem(storageKey(), JSON.stringify(state));
  }

  function loadState() {
    let raw = null;
    try {
      raw = JSON.parse(localStorage.getItem(storageKey()) || "null");
    } catch {
      raw = null;
    }
    state = Core.sanitizeState(raw, config.id);
  }

  function sessionId() {
    let id = localStorage.getItem(SESSION_KEY);
    if (!id) {
      id = (window.crypto && crypto.randomUUID)
        ? crypto.randomUUID()
        : `path-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
      localStorage.setItem(SESSION_KEY, id);
    }
    return id;
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, options);
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    if (!response.ok) {
      const message = payload && (payload.description || payload.error);
      throw new Error(message || `Erreur HTTP ${response.status}`);
    }
    return payload;
  }

  async function init() {
    if (!Core) {
      showFatal("Le module de progression n’a pas été chargé.");
      return;
    }
    try {
      config = await fetchJson(CONFIG_URL);
      loadState();
      wireGlobalActions();
      renderShell();
    } catch (error) {
      showFatal(error.message || "Impossible de charger le parcours.");
    }
  }

  function showFatal(message) {
    const root = $("#pathway-root");
    root.innerHTML = `<div class="fatal"><h2>Parcours indisponible</h2><p>${escapeHtml(message)}</p></div>`;
  }

  function wireGlobalActions() {
    $("#reset-pathway").addEventListener("click", () => {
      const confirmed = window.confirm("Réinitialiser la progression de ce parcours sur cet appareil ?");
      if (!confirmed) return;
      state = Core.initialState(config.id);
      saveState();
      renderShell();
    });
  }

  function renderShell() {
    renderHeaderProgress();
    const next = Core.nextIndex(state, config);
    const seq = Core.sequence(config, state);

    if (!state.startedAt) {
      renderIntro();
      return;
    }
    if (state.completedAt && state.mastery && state.mastery.passed) {
      renderCompletion(true);
      return;
    }
    if (next >= seq.length) {
      renderCompletion(Boolean(state.mastery && state.mastery.passed));
      return;
    }
    openStep(next);
  }

  function renderHeaderProgress() {
    const p = Core.progress(state, config);
    $("#pathway-title").textContent = config.title;
    $("#progress-label").textContent = `${p.done} / ${p.total} ECG`;
    $("#progress-fill").style.width = `${p.percent}%`;
  }

  function renderIntro() {
    const root = $("#pathway-root");
    root.innerHTML = `
      <section class="intro-card">
        <div class="eyebrow">Micro-parcours guidé</div>
        <h1>${escapeHtml(config.title)}</h1>
        <p class="lead">${escapeHtml(config.subtitle)}</p>
        <div class="intro-grid">
          <div><strong>${config.cases.length}</strong><span>ECG de base</span></div>
          <div><strong>~${config.estimated_minutes}</strong><span>minutes</span></div>
          <div><strong>1</strong><span>test autonome</span></div>
        </div>
        <div class="principle">
          <strong>Principe pédagogique</strong>
          <p>Tu produis d’abord une interprétation sans aide. Les indices ne deviennent accessibles qu’après cet engagement initial. Le dernier ECG est réalisé sans indice.</p>
        </div>
        <h2>Objectifs</h2>
        <ul class="objectives">${config.learning_objectives.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        <button id="start-pathway" class="primary-action">Commencer le parcours</button>
        <p class="privacy-note">La progression est enregistrée localement sur cet appareil. Les réponses corrigées suivent le recueil déjà configuré dans l’application.</p>
      </section>`;
    $("#start-pathway").addEventListener("click", () => {
      state.startedAt = new Date().toISOString();
      state.currentIndex = 0;
      saveState();
      renderShell();
    });
  }

  async function openStep(index) {
    const seq = Core.sequence(config, state);
    currentDefinition = seq[index];
    state.currentIndex = index;
    saveState();
    openedAt = Date.now();
    initialLockedAt = 0;
    hintsUsed = 0;

    const root = $("#pathway-root");
    root.innerHTML = `<div class="loading-card">Chargement du tracé…</div>`;

    try {
      currentCase = await fetchJson(`${API}/api/case/${currentDefinition.num}`);
      renderCase(index, seq.length);
    } catch (error) {
      root.innerHTML = `<div class="fatal"><h2>Impossible de charger ce cas</h2><p>${escapeHtml(error.message)}</p><button id="retry-load" class="secondary-action">Réessayer</button></div>`;
      $("#retry-load").addEventListener("click", () => openStep(index));
    }
  }

  function phaseName(phase) {
    return {
      foundation: "Fondation",
      guided: "Apprentissage guidé",
      contrast: "Discrimination",
      mastery: "Évaluation autonome",
      remediation: "Consolidation",
    }[phase] || "Apprentissage";
  }

  function primaryImage(images) {
    const all = Array.isArray(images) ? images : [];
    return all.find((name) => !/_p\d+\.[a-z0-9]+$/i.test(name)) || all[0] || "";
  }

  function secondaryImages(images) {
    const first = primaryImage(images);
    return (Array.isArray(images) ? images : []).filter((name) => name !== first);
  }

  function renderCase(index, total) {
    const root = $("#pathway-root");
    const isMastery = currentDefinition.phase === "mastery";
    const image = primaryImage(currentCase.images);
    const context = [currentCase.patient, currentCase.contexte].filter(Boolean).join("\n");

    root.innerHTML = `
      <article class="case-card">
        <header class="step-header">
          <div>
            <span class="phase-badge ${escapeHtml(currentDefinition.phase)}">${escapeHtml(phaseName(currentDefinition.phase))}</span>
            <h1>${escapeHtml(currentDefinition.step_title)}</h1>
            <p>${escapeHtml(currentDefinition.objective)}</p>
          </div>
          <div class="step-number">${index + 1}<span>/${total}</span></div>
        </header>

        ${isMastery ? `<div class="mastery-banner"><strong>Test sans aide</strong><span>Aucun indice ni QCM ne sera proposé avant la correction.</span></div>` : ""}

        <section class="clinical-context">
          <h2>Contexte</h2>
          <p>${escapeHtml(context || "Aucun contexte supplémentaire.").replace(/\n/g, "<br>")}</p>
        </section>

        <figure class="ecg-frame">
          ${image ? `<img id="ecg-image" src="${API}/images/${encodeURIComponent(image)}" alt="Tracé ECG du cas ${currentDefinition.num}">` : `<div class="missing-image">Tracé indisponible</div>`}
          <figcaption>Clique sur le tracé pour l’agrandir.</figcaption>
        </figure>

        <section id="response-stage" class="response-stage">
          <div class="stage-marker"><span>1</span><div><strong>Première lecture</strong><small>Sans aide et avant toute correction</small></div></div>
          <label for="initial-answer">Ton interprétation structurée</label>
          <textarea id="initial-answer" rows="6" placeholder="Rythme, fréquence, activité atriale, relation P–QRS, PR, largeur des QRS, diagnostic et gravité éventuelle."></textarea>

          <div class="confidence-block">
            <div class="confidence-heading"><label for="confidence">Niveau de confiance</label><output id="confidence-output">50 %</output></div>
            <input id="confidence" type="range" min="0" max="100" step="10" value="50">
            <div class="confidence-scale"><span>Très incertain</span><span>Très certain</span></div>
          </div>

          <button id="lock-initial" class="primary-action">${isMastery ? "Valider et corriger" : "Valider ma première lecture"}</button>
          <p class="stage-note">Après validation, cette réponse initiale est conservée pour mesurer le raisonnement autonome.</p>
        </section>

        <section id="guided-stage" class="guided-stage hidden"></section>
        <section id="result-stage" class="result-stage hidden"></section>
      </article>`;

    $("#confidence").addEventListener("input", (event) => {
      $("#confidence-output").textContent = `${event.target.value} %`;
    });
    $("#lock-initial").addEventListener("click", lockInitialAnswer);
    if ($("#ecg-image")) $("#ecg-image").addEventListener("click", openLightbox);
  }

  async function lockInitialAnswer() {
    const answer = $("#initial-answer").value.trim();
    if (!answer) {
      $("#initial-answer").focus();
      return;
    }
    const confidence = Number($("#confidence").value);
    initialLockedAt = Date.now();
    $("#initial-answer").disabled = true;
    $("#confidence").disabled = true;
    $("#lock-initial").disabled = true;

    if (currentDefinition.phase === "mastery") {
      await gradeAnswer(answer, answer, confidence);
      return;
    }
    renderGuidedStage(answer, confidence);
  }

  function renderGuidedStage(initialAnswer, confidence) {
    const stage = $("#guided-stage");
    stage.classList.remove("hidden");
    const hintsAvailable = currentDefinition.allow_hints && currentDefinition.hints.length > 0;
    stage.innerHTML = `
      <div class="stage-marker"><span>2</span><div><strong>Révision guidée</strong><small>Les indices orientent l’attention sans donner d’emblée la réponse.</small></div></div>
      <div class="locked-answer"><strong>Ta première lecture</strong><p>${escapeHtml(initialAnswer).replace(/\n/g, "<br>")}</p><span>Confiance initiale : ${confidence} %</span></div>
      ${hintsAvailable ? `
        <div class="hints-panel">
          <div class="hints-heading"><strong>Indices progressifs</strong><span id="hint-counter">0 / ${currentDefinition.hints.length}</span></div>
          <div id="hints-list" class="hints-list"></div>
          <button id="next-hint" class="secondary-action">Afficher l’indice 1</button>
        </div>` : ""}
      <label for="final-answer">Réponse finale</label>
      <textarea id="final-answer" rows="6">${escapeHtml(initialAnswer)}</textarea>
      <button id="grade-final" class="primary-action">Corriger ma réponse finale</button>`;

    if (hintsAvailable) $("#next-hint").addEventListener("click", revealNextHint);
    $("#grade-final").addEventListener("click", async () => {
      const finalAnswer = $("#final-answer").value.trim();
      if (!finalAnswer) {
        $("#final-answer").focus();
        return;
      }
      await gradeAnswer(initialAnswer, finalAnswer, confidence);
    });
    stage.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function revealNextHint() {
    if (hintsUsed >= currentDefinition.hints.length) return;
    const hint = currentDefinition.hints[hintsUsed];
    hintsUsed += 1;
    const item = document.createElement("div");
    item.className = "hint-item";
    item.innerHTML = `<span>${hintsUsed}</span><p>${escapeHtml(hint)}</p>`;
    $("#hints-list").appendChild(item);
    $("#hint-counter").textContent = `${hintsUsed} / ${currentDefinition.hints.length}`;
    const button = $("#next-hint");
    if (hintsUsed >= currentDefinition.hints.length) {
      button.disabled = true;
      button.textContent = "Tous les indices ont été utilisés";
    } else {
      button.textContent = `Afficher l’indice ${hintsUsed + 1}`;
    }
  }

  async function gradeAnswer(initialAnswer, finalAnswer, confidence) {
    const button = currentDefinition.phase === "mastery" ? $("#lock-initial") : $("#grade-final");
    if (button) {
      button.disabled = true;
      button.dataset.original = button.textContent;
      button.textContent = "Correction en cours…";
    }
    const totalSeconds = Math.round((Date.now() - openedAt) / 1000);
    const autonomousSeconds = Math.round(((initialLockedAt || Date.now()) - openedAt) / 1000);

    try {
      const result = await fetchJson(`${API}/api/grade`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          num: currentDefinition.num,
          answer: finalAnswer,
          session: sessionId(),
          meta: {
            mode: "parcours",
            parcours: config.id,
            phase: currentDefinition.phase,
            position: state.currentIndex + 1,
            confiance_initiale: confidence,
            indices_utilises: hintsUsed,
            reponse_initiale: initialAnswer,
            reponse_modifiee: initialAnswer.trim() !== finalAnswer.trim(),
            t_reflexion_s: autonomousSeconds,
            t_total_s: totalSeconds,
            longueur: finalAnswer.length,
            tentative: ((state.attempts[String(currentDefinition.num)] || []).length + 1),
            refait: Boolean(state.attempts[String(currentDefinition.num)]),
          },
        }),
      });

      state = Core.recordAttempt(state, currentDefinition, {
        initialAnswer,
        finalAnswer,
        confidence,
        hintsUsed,
        score: result.score,
        diagnosticScore: Core.diagnosticScore(result),
        correspondence: result.correspondance,
        errorType: result.type_erreur,
      });

      if (currentDefinition.phase === "mastery" || currentDefinition.phase === "remediation") {
        const evaluation = Core.evaluateMastery(result, config);
        state = Core.markMastery(state, evaluation);
      }
      saveState();
      renderHeaderProgress();
      renderResult(result);
    } catch (error) {
      if (button) {
        button.disabled = false;
        button.textContent = button.dataset.original || "Corriger";
      }
      window.alert(`Correction impossible : ${error.message}`);
    }
  }

  function renderResult(result) {
    const stage = $("#result-stage");
    stage.classList.remove("hidden");
    const diagnostic = Core.diagnosticScore(result);
    const found = (result.elements_trouves || []).map((item) => `<li>${escapeHtml(item.label)}</li>`).join("") || "<li>Aucun élément validant identifié.</li>";
    const missed = (result.elements_manques || []).map((item) => `<li>${escapeHtml(item.label)}</li>`).join("") || "<li>Aucun élément majeur manquant.</li>";
    const wrong = (result.elements_errones || []).map((item) => `<li><strong>${escapeHtml(item.label)}</strong>${item.correction ? ` — ${escapeHtml(item.correction)}` : ""}</li>`).join("") || "<li>Aucune affirmation factuelle erronée.</li>";
    const secondary = secondaryImages(currentCase.images);
    const isAssessment = currentDefinition.phase === "mastery" || currentDefinition.phase === "remediation";
    const evaluation = isAssessment ? Core.evaluateMastery(result, config) : null;

    stage.innerHTML = `
      <div class="stage-marker"><span>3</span><div><strong>Correction</strong><small>Compare ton raisonnement initial, ta réponse finale et la référence.</small></div></div>
      <div class="score-panel">
        <div class="score-main"><span>${Math.round(result.score || 0)}</span><small>/100 global</small></div>
        <div class="score-secondary"><strong>${Math.round(diagnostic)}</strong><span>/100 diagnostic</span></div>
        <div class="verdict"><strong>${escapeHtml(result.verdict || "Correction terminée")}</strong><span>Diagnostic retenu : ${escapeHtml(result.diagnostic_retenu || "—")}</span></div>
      </div>
      ${evaluation ? `<div class="mastery-result ${evaluation.passed ? "passed" : "not-passed"}"><strong>${evaluation.passed ? "Compétence acquise sur ce test" : "Compétence à consolider"}</strong><span>Seuil diagnostique : ${evaluation.threshold}/100, sans erreur clinique repérée.</span></div>` : ""}
      <div class="feedback-grid">
        <section><h3>Éléments trouvés</h3><ul>${found}</ul></section>
        <section><h3>À compléter</h3><ul>${missed}</ul></section>
        <section><h3>À corriger</h3><ul>${wrong}</ul></section>
      </div>
      <section class="teacher-comment"><h3>Commentaire pédagogique</h3><div>${simpleMarkdown(result.commentaire || "")}</div></section>
      <details class="reference-panel"><summary>Voir l’interprétation de référence</summary><div>${simpleMarkdown((result.reference && result.reference.interpretation_ref) || "")}</div></details>
      ${secondary.length ? `<section class="secondary-traces"><h3>Tracé complémentaire révélé après correction</h3>${secondary.map((name) => `<img src="${API}/images/${encodeURIComponent(name)}" alt="Tracé complémentaire du cas ${currentDefinition.num}">`).join("")}</section>` : ""}
      <div id="continuation-actions" class="continuation-actions"></div>`;

    stage.querySelectorAll(".secondary-traces img").forEach((img) => img.addEventListener("click", openLightbox));
    renderContinuation(evaluation);
    stage.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderContinuation(evaluation) {
    const box = $("#continuation-actions");
    const isAssessment = currentDefinition.phase === "mastery" || currentDefinition.phase === "remediation";

    if (isAssessment) {
      if (evaluation && evaluation.passed) {
        box.innerHTML = `<button id="finish-pathway" class="primary-action">Voir mon bilan</button>`;
        $("#finish-pathway").addEventListener("click", () => {
          state.completedAt = state.completedAt || new Date().toISOString();
          saveState();
          renderCompletion(true);
        });
      } else if (!state.remediationActive && config.remediation) {
        box.innerHTML = `
          <div class="remediation-offer"><strong>Un ECG supplémentaire est proposé</strong><p>Il cible le même diagnostic avec un échappement plus distal. Le parcours reste limité à six ECG au maximum.</p></div>
          <button id="start-remediation" class="primary-action">Faire l’ECG de consolidation</button>
          <button id="see-balance" class="secondary-action">Voir le bilan sans refaire de cas</button>`;
        $("#start-remediation").addEventListener("click", () => {
          state = Core.unlockRemediation(state);
          state.currentIndex = Core.sequence(config, state).length - 1;
          saveState();
          renderShell();
        });
        $("#see-balance").addEventListener("click", () => renderCompletion(false));
      } else {
        box.innerHTML = `<button id="see-balance" class="primary-action">Voir mon bilan</button>`;
        $("#see-balance").addEventListener("click", () => renderCompletion(false));
      }
      return;
    }

    box.innerHTML = `<button id="next-step" class="primary-action">Passer à l’ECG suivant</button>`;
    $("#next-step").addEventListener("click", () => {
      state.currentIndex = Core.nextIndex(state, config);
      saveState();
      renderShell();
    });
  }

  function renderCompletion(passed) {
    const root = $("#pathway-root");
    const p = Core.progress(state, config);
    const attempts = Object.values(state.attempts).flat();
    const averageDiagnostic = attempts.length
      ? Math.round(attempts.reduce((sum, item) => sum + Number(item.diagnosticScore || 0), 0) / attempts.length)
      : 0;
    const averageConfidence = attempts.length
      ? Math.round(attempts.reduce((sum, item) => sum + Number(item.confidence || 0), 0) / attempts.length)
      : 0;
    const totalHints = attempts.reduce((sum, item) => sum + Number(item.hintsUsed || 0), 0);

    const canRemediate = !passed && !state.remediationActive && Boolean(config.remediation);
    root.innerHTML = `
      <section class="completion-card ${passed ? "passed" : "not-passed"}">
        <div class="completion-status">${passed ? "Acquis" : "À consolider"}</div>
        <h1>${escapeHtml(config.title)}</h1>
        <p>${passed ? "Le test final a été réussi sans aide." : "Le parcours est terminé, mais le seuil de maîtrise autonome n’a pas encore été atteint."}</p>
        <div class="summary-grid">
          <div><strong>${p.done}</strong><span>ECG réalisés</span></div>
          <div><strong>${averageDiagnostic}</strong><span>score diagnostique moyen</span></div>
          <div><strong>${averageConfidence} %</strong><span>confiance moyenne</span></div>
          <div><strong>${totalHints}</strong><span>indices utilisés</span></div>
        </div>
        <div class="next-learning"><strong>Message pédagogique</strong><p>${passed ? "Tu sais distinguer les principaux degrés de BAV et reconnaître une dissociation auriculoventriculaire. La réactivation différée reste nécessaire pour confirmer la rétention." : "Reprends surtout la relation entre les ondes P et les QRS, puis la dynamique de l’intervalle PR. Une nouvelle tentative différée sera plus informative qu’une répétition immédiate en boucle."}</p></div>
        <div class="completion-actions">
          ${canRemediate ? `<button id="completion-remediation" class="primary-action">Faire l’ECG de consolidation</button>` : `<a class="primary-action link-button" href="/">Retour à la banque des 75 ECG</a>`}
          <button id="restart-completion" class="secondary-action">Recommencer ce parcours</button>
          ${canRemediate ? `<a class="secondary-action link-button" href="/">Retour à la banque libre</a>` : ""}
        </div>
      </section>`;
    if (canRemediate) {
      $("#completion-remediation").addEventListener("click", () => {
        state = Core.unlockRemediation(state);
        state.currentIndex = Core.sequence(config, state).length - 1;
        saveState();
        renderShell();
      });
    }
    $("#restart-completion").addEventListener("click", () => {
      state = Core.initialState(config.id);
      state.startedAt = new Date().toISOString();
      saveState();
      renderShell();
    });
    renderHeaderProgress();
  }

  function openLightbox(event) {
    const src = event.currentTarget.src;
    $("#lightbox-image").src = src;
    $("#pathway-lightbox").classList.remove("hidden");
  }

  document.addEventListener("DOMContentLoaded", () => {
    $("#pathway-lightbox").addEventListener("click", () => $("#pathway-lightbox").classList.add("hidden"));
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") $("#pathway-lightbox").classList.add("hidden");
    });
    init();
  });
})();
