/* pathway.js — interface générique des micro-parcours ECG. */
(() => {
  "use strict";

  const API = "";
  const CATALOG_URL = "/static/pathways.json";
  const DEFAULT_PATHWAY_ID = "bav-foundations";
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
  let confidenceTouched = false;
  let stepTimer = null;
  let autonomousTiming = null;
  let draftRestored = false;
  let viewerOpenCount = 0;
  let viewerZoomCount = 0;
  let lightboxScale = 1;
  let lightboxBaseWidth = 0;

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

  function draftKey(kind) {
    if (!config || !currentDefinition) return "";
    return `ecg_pathway_draft_v1_${config.id}_${Core.caseKey(currentDefinition)}_${kind}`;
  }

  function loadDraft(kind) {
    try { return localStorage.getItem(draftKey(kind)) || ""; } catch { return ""; }
  }

  function saveDraft(kind, value) {
    const key = draftKey(kind);
    if (!key) return;
    try {
      if (value) localStorage.setItem(key, value);
      else localStorage.removeItem(key);
    } catch { /* le parcours reste utilisable si le stockage est saturé */ }
  }

  function clearStepDrafts() {
    saveDraft("initial", "");
    saveDraft("final", "");
  }

  function clearPathwayDrafts() {
    const prefix = `ecg_pathway_draft_v1_${config.id}_`;
    try {
      const keys = [];
      for (let index = 0; index < localStorage.length; index += 1) {
        const key = localStorage.key(index);
        if (key && key.startsWith(prefix)) keys.push(key);
      }
      keys.forEach((key) => localStorage.removeItem(key));
    } catch { /* la réinitialisation de progression reste prioritaire */ }
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
      const catalog = await fetchJson(CATALOG_URL);
      if (catalog.schema_version !== 1) throw new Error("Version de catalogue non prise en charge.");
      const requestedId = new URLSearchParams(window.location.search).get("id")
        || catalog.default_id
        || DEFAULT_PATHWAY_ID;
      const catalogEntry = Core.selectCatalogEntry(catalog, requestedId, DEFAULT_PATHWAY_ID);
      if (!catalogEntry) throw new Error("Ce parcours n’existe pas ou n’est plus disponible.");
      config = await fetchJson(catalogEntry.config_url);
      if (config.id !== catalogEntry.id) throw new Error("La configuration de ce parcours est incohérente.");
      if (config.schema_version !== 1) throw new Error("Version de parcours non prise en charge.");
      document.title = `Parcours ECG — ${config.title}`;
      loadState();
      wireGlobalActions();
      renderShell();
    } catch (error) {
      showFatal(error.message || "Impossible de charger le parcours.");
    }
  }

  function showFatal(message) {
    const root = $("#pathway-root");
    root.innerHTML = `<div class="fatal"><h2>Parcours indisponible</h2><p>${escapeHtml(message)}</p><a class="secondary-action link-button" href="/static/pathways.html">Voir les parcours disponibles</a></div>`;
  }

  function wireGlobalActions() {
    $("#reset-pathway").addEventListener("click", () => {
      const confirmed = window.confirm("Réinitialiser la progression de ce parcours sur cet appareil ?");
      if (!confirmed) return;
      clearPathwayDrafts();
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
          <p>Tu produis d’abord une interprétation sans aide. Les indices ne deviennent accessibles qu’après cet engagement initial. Le test de maîtrise est réalisé sans indice.</p>
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
    const pending = state.pendingAttempt && state.pendingAttempt.caseKey === Core.caseKey(currentDefinition)
      ? state.pendingAttempt
      : null;
    state.currentIndex = index;
    saveState();
    openedAt = pending ? Number(pending.openedAt || Date.now()) : Date.now();
    initialLockedAt = pending ? Number(pending.lockedAt || 0) : 0;
    hintsUsed = pending ? Number(pending.hintsUsed || 0) : 0;
    confidenceTouched = Boolean(pending);
    draftRestored = false;
    viewerOpenCount = 0;
    viewerZoomCount = 0;
    autonomousTiming = pending && pending.timing ? pending.timing.autonomous : null;
    if (window.ECGTiming) {
      const savedTiming = pending && pending.timing ? pending.timing : {};
      const resumeGap = pending ? Math.max(0, Date.now() - initialLockedAt) : 0;
      stepTimer = ECGTiming.createTracker({
        startedAt: openedAt,
        visible: !document.hidden,
        backgroundMs: Number(savedTiming.backgroundMs || 0) + resumeGap,
        backgroundCount: Number(savedTiming.backgroundCount || 0) + (resumeGap > 0 ? 1 : 0),
        firstInputAt: Number(savedTiming.firstInputAt || 0),
        firstInputActiveMs: Number(savedTiming.firstInputActiveMs || 0),
      });
    } else {
      stepTimer = null;
    }

    const root = $("#pathway-root");
    root.innerHTML = `<div class="loading-card">Chargement du tracé…</div>`;

    try {
      currentCase = await fetchJson(`${API}/api/case/${currentDefinition.num}`);
      renderCase(index, seq.length);
      if (pending) restorePendingAttempt(pending);
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
    const crop = currentDefinition.image_crop;
    const cropTop = crop && Number.isFinite(Number(crop.top_percent)) ? Number(crop.top_percent) : null;
    const cropRatio = crop && Number.isFinite(Number(crop.aspect_ratio)) ? Number(crop.aspect_ratio) : null;
    const cropEnabled = cropTop !== null && cropRatio !== null && cropTop > 0 && cropRatio > 0;
    const cropStyle = cropEnabled
      ? ` style="--crop-offset:-${cropTop}%;--crop-ratio:${cropRatio}"`
      : "";

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
          ${image ? `<div class="ecg-viewport${cropEnabled ? " cropped" : ""}"${cropStyle}><img id="ecg-image" src="${API}/images/${encodeURIComponent(image)}" alt="Tracé ECG du cas ${currentDefinition.num}"${cropEnabled ? ` data-crop-top="${cropTop}" data-crop-ratio="${cropRatio}"` : ""}></div>` : `<div class="missing-image">Tracé indisponible</div>`}
          <figcaption>Clique sur le tracé pour l’agrandir.</figcaption>
        </figure>

        <section id="response-stage" class="response-stage">
          <div class="stage-marker"><span>1</span><div><strong>Première lecture autonome</strong><small>Sans aide et avant toute correction</small></div></div>
          <label for="initial-answer">Ton interprétation structurée</label>
          <textarea id="initial-answer" rows="6" placeholder="Rythme, fréquence, activité atriale, relation P–QRS, PR, largeur des QRS, diagnostic et gravité éventuelle."></textarea>

          <div class="confidence-block">
            <div class="confidence-heading"><label for="confidence">Niveau de confiance</label><output id="confidence-output" for="confidence">À indiquer</output></div>
            <input id="confidence" type="range" min="0" max="100" step="10" value="50" aria-describedby="confidence-instruction">
            <div class="confidence-scale"><span>Très incertain</span><span>Très certain</span></div>
            <p id="confidence-instruction" class="confidence-instruction">Déplace le curseur pour enregistrer ton estimation.</p>
          </div>

          <p class="stage-note">${isMastery
            ? "Cette réponse sera corrigée telle quelle. Aucun indice ne sera disponible avant le résultat."
            : "En continuant, tu enregistres cette première lecture. Elle ne pourra plus être modifiée ; tu pourras ensuite rédiger une réponse finale séparée."}</p>
          <button id="lock-initial" class="primary-action">${isMastery ? "Soumettre pour correction" : "Enregistrer ma première lecture"}</button>
        </section>

        <section id="guided-stage" class="guided-stage hidden"></section>
        <section id="result-stage" class="result-stage hidden"></section>
      </article>`;

    $("#confidence").addEventListener("input", (event) => {
      confidenceTouched = true;
      $(".confidence-block").classList.remove("needs-input");
      $("#confidence-output").textContent = `${event.target.value} %`;
    });
    const initialAnswer = $("#initial-answer");
    const savedInitial = loadDraft("initial");
    if (savedInitial) {
      initialAnswer.value = savedInitial;
      draftRestored = true;
    }
    initialAnswer.addEventListener("input", () => {
      if (stepTimer) stepTimer.markFirstInput();
      saveDraft("initial", initialAnswer.value);
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
    if (!confidenceTouched) {
      $(".confidence-block").classList.add("needs-input");
      $("#confidence").focus();
      return;
    }
    const confidence = Number($("#confidence").value);
    initialLockedAt = Date.now();
    autonomousTiming = stepTimer ? stepTimer.snapshot(initialLockedAt) : null;
    state = Core.lockPendingAttempt(state, currentDefinition, {
      initialAnswer: answer,
      confidence,
      openedAt,
      lockedAt: initialLockedAt,
      timing: autonomousTiming ? {
        autonomous: autonomousTiming,
        backgroundMs: autonomousTiming.backgroundMs,
        backgroundCount: autonomousTiming.backgroundCount,
        firstInputAt: autonomousTiming.firstInputAt,
        firstInputActiveMs: autonomousTiming.firstInputActiveMs,
      } : null,
    });
    saveDraft("initial", "");
    saveState();
    $("#initial-answer").disabled = true;
    $("#confidence").disabled = true;
    $("#lock-initial").disabled = true;

    if (currentDefinition.phase === "mastery") {
      await gradeAnswer(answer, answer, confidence);
      return;
    }
    renderGuidedStage(answer, confidence);
  }

  function restorePendingAttempt(pending) {
    const initial = $("#initial-answer");
    initial.value = pending.initialAnswer;
    initial.disabled = true;
    $("#confidence").value = String(pending.confidence);
    $("#confidence").disabled = true;
    $("#confidence-output").textContent = `${pending.confidence} %`;
    $("#lock-initial").disabled = true;
    if (pending.timing && pending.timing.firstInputAt && stepTimer) {
      stepTimer.markFirstInput(pending.timing.firstInputAt);
    }

    if (currentDefinition.phase === "mastery") {
      renderMasteryPending(pending);
    } else {
      renderGuidedStage(pending.initialAnswer, pending.confidence, true);
    }
  }

  function renderMasteryPending(pending) {
    const stage = $("#guided-stage");
    stage.classList.remove("hidden");
    stage.innerHTML = `
      <div class="stage-marker"><span>2</span><div><strong>Première lecture enregistrée</strong><small>La correction peut être relancée sans modifier la réponse ni accéder à une aide.</small></div></div>
      <div class="locked-answer"><strong>Ta première lecture</strong><p>${escapeHtml(pending.initialAnswer).replace(/\n/g, "<br>")}</p><span>Confiance initiale : ${pending.confidence} %</span></div>
      <button id="retry-mastery-grade" class="primary-action">Relancer la correction</button>`;
    $("#retry-mastery-grade").addEventListener("click", () => {
      gradeAnswer(pending.initialAnswer, pending.initialAnswer, pending.confidence);
    });
  }

  function renderGuidedStage(initialAnswer, confidence, restoring = false) {
    const stage = $("#guided-stage");
    stage.classList.remove("hidden");
    const hintsAvailable = currentDefinition.allow_hints && currentDefinition.hints.length > 0;
    stage.innerHTML = `
      <div class="stage-marker"><span>2</span><div><strong>Première lecture enregistrée</strong><small>Révise maintenant ta réponse, avec ou sans aide.</small></div></div>
      <div class="locked-answer"><strong>Ta première lecture</strong><p>${escapeHtml(initialAnswer).replace(/\n/g, "<br>")}</p><span>Confiance initiale : ${confidence} %</span></div>
      ${hintsAvailable ? `
        <div class="hints-panel">
          <div class="hints-heading"><strong>Indices progressifs</strong><span id="hint-counter">0 / ${currentDefinition.hints.length}</span></div>
          <div id="hints-list" class="hints-list"></div>
          <p id="hint-help" class="hint-help">Le premier indice attire seulement ton attention vers une zone ou un critère.</p>
          <button id="next-hint" class="secondary-action">Afficher 1 · Observer</button>
        </div>` : ""}
      <label for="final-answer">Réponse finale</label>
      <textarea id="final-answer" rows="6">${escapeHtml(loadDraft("final") || initialAnswer)}</textarea>
      <p id="answer-support-status" class="answer-support-status">Réponse finale sans indice</p>
      <button id="grade-final" class="primary-action">Corriger ma réponse finale</button>`;

    if (hintsAvailable) $("#next-hint").addEventListener("click", revealNextHint);
    if (hintsAvailable && restoring) restoreRevealedHints();
    const finalAnswerInput = $("#final-answer");
    if (loadDraft("final")) draftRestored = true;
    finalAnswerInput.addEventListener("input", () => saveDraft("final", finalAnswerInput.value));
    $("#grade-final").addEventListener("click", async () => {
      const finalAnswer = $("#final-answer").value.trim();
      if (!finalAnswer) {
        $("#final-answer").focus();
        return;
      }
      await gradeAnswer(initialAnswer, finalAnswer, confidence);
    });
    if (!restoring) stage.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function appendHint(hint, number) {
    const item = document.createElement("div");
    item.className = "hint-item";
    item.innerHTML = `<span>${number}</span><p>${escapeHtml(hint)}</p>`;
    $("#hints-list").appendChild(item);
  }

  function updateHintControls() {
    $("#hint-counter").textContent = `${hintsUsed} / ${currentDefinition.hints.length}`;
    const button = $("#next-hint");
    const helper = $("#hint-help");
    const status = $("#answer-support-status");
    const levels = ["Observer", "Comparer", "Orienter"];
    const helperCopy = [
      "Le premier indice attire seulement ton attention vers une zone ou un critère.",
      "Réexamine le tracé avant de demander l’aide suivante, qui propose une comparaison discriminante.",
      "La dernière aide donne une orientation diagnostique explicite.",
    ];
    if (status) status.textContent = hintsUsed === 0
      ? "Réponse finale sans indice"
      : `Réponse accompagnée · ${hintsUsed} indice${hintsUsed > 1 ? "s" : ""}`;
    if (hintsUsed >= currentDefinition.hints.length) {
      button.disabled = true;
      button.textContent = "Tous les indices ont été utilisés";
      if (helper) helper.textContent = "Tu as utilisé toute la progression d’aide disponible pour ce cas.";
    } else {
      const level = levels[Math.min(hintsUsed, levels.length - 1)];
      button.textContent = hintsUsed === 0
        ? `Afficher ${hintsUsed + 1} · ${level}`
        : `J’ai réexaminé le tracé — voir ${hintsUsed + 1} · ${level}`;
      if (helper) helper.textContent = helperCopy[Math.min(hintsUsed, helperCopy.length - 1)];
    }
  }

  function restoreRevealedHints() {
    currentDefinition.hints.slice(0, hintsUsed).forEach((hint, index) => appendHint(hint, index + 1));
    updateHintControls();
  }

  function revealNextHint() {
    if (hintsUsed >= currentDefinition.hints.length) return;
    const hint = currentDefinition.hints[hintsUsed];
    hintsUsed += 1;
    state = Core.recordPendingHint(state);
    saveState();
    appendHint(hint, hintsUsed);
    updateHintControls();
  }

  async function gradeAnswer(initialAnswer, finalAnswer, confidence) {
    const button = currentDefinition.phase === "mastery"
      ? ($("#retry-mastery-grade") || $("#lock-initial"))
      : $("#grade-final");
    if (button) {
      button.disabled = true;
      button.dataset.original = button.textContent;
      button.textContent = "Correction en cours…";
    }
    const now = Date.now();
    const totalSeconds = Math.round((now - openedAt) / 1000);
    const autonomousSeconds = Math.round(((initialLockedAt || Date.now()) - openedAt) / 1000);
    const totalTiming = stepTimer ? stepTimer.snapshot(now) : null;
    const initialTiming = autonomousTiming || totalTiming;

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
            ...(window.ECGTiming && totalTiming ? ECGTiming.metrics(initialTiming, totalTiming, {
              brouillon_restaure: draftRestored,
              ouvertures_visionneuse: viewerOpenCount,
              zooms_visionneuse: viewerZoomCount,
            }) : {}),
            // Compatibilité : cette colonne historique désigne dans un parcours
            // le temps mural jusqu'au verrouillage de la première lecture.
            t_reflexion_s: autonomousSeconds,
            t_total_s: totalSeconds,
            longueur: finalAnswer.length,
            tentative: Core.attemptHistory(state, currentDefinition).length + 1,
            refait: Core.attemptHistory(state, currentDefinition).length > 0,
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
        formativeOnly: currentDefinition.formative_only,
      });
      clearStepDrafts();

      let masteryEvaluation = null;
      if (Core.canValidateMastery(currentDefinition, hintsUsed)) {
        masteryEvaluation = Core.evaluateMastery(result, config, finalAnswer);
        state = Core.markMastery(state, masteryEvaluation);
      }
      saveState();
      renderHeaderProgress();
      renderResult(result, masteryEvaluation, initialAnswer, finalAnswer);
    } catch (error) {
      if (button) {
        button.disabled = false;
        button.textContent = button.dataset.original || "Corriger";
      }
      window.alert(`Correction impossible : ${error.message}`);
    }
  }

  function feedbackItems(value, emptyText) {
    if (!Array.isArray(value)) return "<li>Détail non fourni par le correcteur.</li>";
    if (value.length === 0) return `<li>${escapeHtml(emptyText)}</li>`;
    return value.map((item) => `<li>${escapeHtml(item.label)}</li>`).join("");
  }

  function renderResult(result, masteryEvaluation, initialAnswer, finalAnswer) {
    const stage = $("#result-stage");
    stage.classList.remove("hidden");
    const diagnostic = Core.diagnosticScore(result);
    const found = feedbackItems(result.elements_trouves, "Aucun élément validant identifié.");
    const missed = feedbackItems(result.elements_manques, "Aucun élément majeur manquant.");
    const wrong = Array.isArray(result.elements_errones)
      ? (result.elements_errones.map((item) => `<li><strong>${escapeHtml(item.label)}</strong>${item.correction ? ` — ${escapeHtml(item.correction)}` : ""}</li>`).join("") || "<li>Aucune affirmation factuelle erronée.</li>")
      : "<li>Détail non fourni par le correcteur.</li>";
    const secondary = currentDefinition.hide_secondary_images ? [] : secondaryImages(currentCase.images);
    const isMastery = currentDefinition.phase === "mastery";
    const isRemediation = currentDefinition.phase === "remediation";
    const evaluation = isMastery ? masteryEvaluation : null;
    const teachingPoint = currentDefinition.teaching_point
      ? `<div class="teaching-point"><strong>Point clé expert</strong><p>${escapeHtml(currentDefinition.teaching_point)}</p></div>`
      : "";
    const formativeText = secondary.length
      ? "Le premier tracé n’autorise pas toujours un mécanisme unique. Le score du diagnostic exact est indicatif et ne participe pas à la validation de la maîtrise ; le tracé complémentaire apporte des éléments supplémentaires pour orienter le mécanisme."
      : "Le début du tracé n’autorise pas toujours un mécanisme unique. Le score du diagnostic exact est indicatif et ne participe pas à la validation de la maîtrise ; les modifications observées pendant la manœuvre apportent les éléments d’orientation.";
    const formativeNotice = currentDefinition.formative_only
      ? `<div class="formative-notice"><strong>Cas de raisonnement différentiel</strong><p>${formativeText}</p></div>`
      : "";
    const diagnosticLabel = currentDefinition.formative_only
      ? "/100 diagnostic exact · indicatif"
      : "/100 diagnostic";
    const supportLabel = hintsUsed === 0
      ? "Réponse finale sans indice"
      : `Réponse finale après ${hintsUsed} indice${hintsUsed > 1 ? "s" : ""}`;
    const changed = initialAnswer.trim() !== finalAnswer.trim();
    const comparison = isMastery ? "" : `
      <section class="answer-comparison">
        <div class="answer-comparison-heading"><strong>Évolution de ta réponse</strong><span>${changed ? "Réponse révisée" : "Réponse inchangée après révision"}</span></div>
        <div class="answer-comparison-grid">
          <article><small>Première lecture · sans aide</small><p>${escapeHtml(initialAnswer).replace(/\n/g, "<br>")}</p></article>
          <article><small>${escapeHtml(supportLabel)}</small><p>${escapeHtml(finalAnswer).replace(/\n/g, "<br>")}</p></article>
        </div>
      </section>`;
    const masterySummary = evaluation
      ? `<div class="mastery-result ${evaluation.passed ? "passed" : "not-passed"}"><strong>${evaluation.passed ? "Test autonome réussi" : "À consolider sur ce test"}</strong><span>${evaluation.requiredCriteriaMatched ? `Seuil diagnostique : ${evaluation.threshold}/100, sans erreur clinique repérée.` : "Le diagnostic et les critères indispensables du test doivent être identifiés explicitement."}</span></div>`
      : "";

    stage.innerHTML = `
      <div class="stage-marker"><span>3</span><div><strong>Synthèse de la correction</strong><small>Le verdict et le point clé expert apparaissent avant les scores détaillés.</small></div></div>
      <section class="correction-summary">
        <strong>${escapeHtml(result.verdict || "Correction terminée")}</strong>
        <span>Diagnostic compris dans ta réponse : ${escapeHtml(result.diagnostic_retenu || "—")}</span>
      </section>
      ${masterySummary}
      ${isRemediation ? `<div class="mastery-result remediation-complete"><strong>Consolidation réalisée</strong><span>Cette réponse aidée n’efface pas le résultat du test autonome et ne valide pas à elle seule la maîtrise.</span></div>` : ""}
      ${formativeNotice}
      ${teachingPoint}
      ${comparison}
      <details class="feedback-details">
        <summary>Voir les détails de la correction</summary>
        <div class="feedback-grid">
          <section><h3>À corriger</h3><ul>${wrong}</ul></section>
          <section><h3>À compléter</h3><ul>${missed}</ul></section>
          <section><h3>Bien repéré</h3><ul>${found}</ul></section>
        </div>
        <div class="score-panel">
          <div class="score-main"><span>${Math.round(result.score || 0)}</span><small>/100 global</small></div>
          <div class="score-secondary"><strong>${Math.round(diagnostic)}</strong><span>${diagnosticLabel}</span></div>
        </div>
      </details>
      <details class="teacher-comment"><summary>Commentaire du correcteur</summary><div>${simpleMarkdown(result.commentaire || "Commentaire non disponible.")}</div></details>
      <details class="reference-panel"><summary>Voir l’interprétation de référence</summary><div>${simpleMarkdown((result.reference && result.reference.interpretation_ref) || "")}</div></details>
      ${secondary.length ? `<section class="secondary-traces"><h3>Tracé complémentaire révélé après correction</h3>${secondary.map((name) => `<img src="${API}/images/${encodeURIComponent(name)}" alt="Tracé complémentaire du cas ${currentDefinition.num}">`).join("")}</section>` : ""}
      <div id="continuation-actions" class="continuation-actions"></div>`;

    stage.querySelectorAll(".secondary-traces img").forEach((img) => img.addEventListener("click", openLightbox));
    renderContinuation(evaluation);
    stage.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderContinuation(evaluation) {
    const box = $("#continuation-actions");

    if (currentDefinition.phase === "remediation") {
      box.innerHTML = `<button id="see-balance" class="primary-action">Voir mon bilan</button>`;
      $("#see-balance").addEventListener("click", () => renderCompletion(false));
      return;
    }

    if (currentDefinition.phase === "mastery") {
      if (evaluation && evaluation.passed) {
        box.innerHTML = `<button id="finish-pathway" class="primary-action">Voir mon bilan</button>`;
        $("#finish-pathway").addEventListener("click", () => {
          state.completedAt = state.completedAt || new Date().toISOString();
          saveState();
          renderCompletion(true);
        });
      } else if (!state.remediationActive && config.remediation) {
        const offerTitle = config.remediation.offer_title || "Un ECG supplémentaire est proposé";
        const offerText = config.remediation.offer_text || "Il cible la compétence qui reste fragile. Le parcours reste limité à six ECG au maximum.";
        box.innerHTML = `
          <div class="remediation-offer"><strong>${escapeHtml(offerTitle)}</strong><p>${escapeHtml(offerText)}</p></div>
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
    const attempts = Object.values(state.attempts).flat();
    const guidedAttempts = attempts.filter((item) => item.phase !== "mastery" && !item.formativeOnly);
    const guidedAverage = guidedAttempts.length
      ? Math.round(guidedAttempts.reduce((sum, item) => sum + Number(item.diagnosticScore || 0), 0) / guidedAttempts.length)
      : "—";
    const autonomousScore = state.mastery && Number.isFinite(state.mastery.diagnosticScore)
      ? Math.round(state.mastery.diagnosticScore)
      : "—";
    const totalHints = attempts.reduce((sum, item) => sum + Number(item.hintsUsed || 0), 0);
    const completion = config.completion || {};
    const passedMessage = completion.passed || "La compétence a été validée sur un ECG inédit, sans aide.";
    const notPassedMessage = completion.not_passed || "Reprends les critères discriminants, puis retente un cas différé plutôt que de mémoriser ce tracé.";

    const canRemediate = !passed && !state.remediationActive && Boolean(config.remediation);
    const completionActions = canRemediate
      ? `<button id="completion-remediation" class="primary-action">Faire l’ECG de consolidation</button>
         <a class="secondary-action link-button" href="/static/pathways.html">Retour aux parcours</a>`
      : passed
        ? `<a class="primary-action link-button" href="/static/pathways.html">Voir la suite conseillée</a>
           <button id="restart-completion" class="secondary-action">Revoir ce parcours</button>`
        : `<a class="primary-action link-button" href="/static/pathways.html">Retour aux parcours</a>`;
    root.innerHTML = `
      <section class="completion-card ${passed ? "passed" : "not-passed"}">
        <div class="completion-status">${passed ? "Test autonome réussi" : "À consolider"}</div>
        <h1>${escapeHtml(config.title)}</h1>
        <p>${passed
          ? "Tu as réussi le test autonome de ce parcours. Ce résultat porte sur ce cas et ne constitue pas une validation clinique globale."
          : "Le critère du test autonome n’est pas encore atteint. La consolidation n’effacera pas ta première performance."}</p>
        <div class="summary-grid">
          <div><strong>${guidedAverage}</strong><span>performance accompagnée /100</span></div>
          <div><strong>${autonomousScore}</strong><span>test autonome /100</span></div>
          <div><strong>${totalHints}</strong><span>indices utilisés</span></div>
        </div>
        <div class="next-learning"><strong>${passed ? "Point validé" : "À travailler"}</strong><p>${escapeHtml(passed ? passedMessage : notPassedMessage)}</p></div>
        <div class="completion-actions">${completionActions}</div>
      </section>`;
    if (canRemediate) {
      $("#completion-remediation").addEventListener("click", () => {
        state = Core.unlockRemediation(state);
        state.currentIndex = Core.sequence(config, state).length - 1;
        saveState();
        renderShell();
      });
    }
    const restart = $("#restart-completion");
    if (restart) restart.addEventListener("click", () => {
      const confirmed = window.confirm("Revoir ce parcours depuis le début ? La progression locale de ce parcours sera réinitialisée.");
      if (!confirmed) return;
      clearPathwayDrafts();
      state = Core.initialState(config.id);
      state.startedAt = new Date().toISOString();
      saveState();
      renderShell();
    });
    renderHeaderProgress();
  }

  function openLightbox(event) {
    const src = event.currentTarget.src;
    const stage = $("#lightbox-stage");
    const cropTop = Number(event.currentTarget.dataset.cropTop || 0);
    const cropRatio = Number(event.currentTarget.dataset.cropRatio || 0);
    const cropped = cropTop > 0 && cropRatio > 0;
    viewerOpenCount += 1;
    lightboxScale = 1;
    stage.classList.toggle("cropped", cropped);
    if (cropped) {
      $("#lightbox-image").style.removeProperty("width");
      stage.style.setProperty("--crop-offset", `-${cropTop}%`);
      stage.style.setProperty("--crop-ratio", String(cropRatio));
      stage.style.width = `${Math.min(window.innerWidth * 0.96, window.innerHeight * 0.94 * cropRatio)}px`;
      lightboxBaseWidth = parseFloat(stage.style.width);
    } else {
      stage.style.removeProperty("--crop-offset");
      stage.style.removeProperty("--crop-ratio");
      stage.style.removeProperty("width");
      lightboxBaseWidth = Math.min(event.currentTarget.naturalWidth || window.innerWidth, window.innerWidth * 0.96);
    }
    $("#lightbox-image").src = src;
    updateLightboxScale();
    $("#pathway-lightbox").classList.remove("hidden");
    document.body.classList.add("viewer-open");
  }

  function updateLightboxScale() {
    const stage = $("#lightbox-stage");
    const image = $("#lightbox-image");
    if (!stage || !image) return;
    const width = Math.max(280, lightboxBaseWidth || window.innerWidth * 0.96) * lightboxScale;
    if (stage.classList.contains("cropped")) stage.style.width = `${width}px`;
    else image.style.width = `${width}px`;
    $("#lightbox-reset").textContent = `${Math.round(lightboxScale * 100)} %`;
  }

  function zoomLightbox(delta) {
    const next = Math.min(3, Math.max(0.75, lightboxScale + delta));
    if (next === lightboxScale) return;
    lightboxScale = next;
    viewerZoomCount += 1;
    updateLightboxScale();
  }

  function closeLightbox() {
    $("#pathway-lightbox").classList.add("hidden");
    document.body.classList.remove("viewer-open");
  }

  document.addEventListener("DOMContentLoaded", () => {
    $("#pathway-lightbox").addEventListener("click", (event) => {
      if (event.target === $("#pathway-lightbox")) closeLightbox();
    });
    $("#lightbox-close").addEventListener("click", closeLightbox);
    $("#lightbox-zoom-out").addEventListener("click", () => zoomLightbox(-0.25));
    $("#lightbox-zoom-in").addEventListener("click", () => zoomLightbox(0.25));
    $("#lightbox-reset").addEventListener("click", () => {
      if (lightboxScale !== 1) viewerZoomCount += 1;
      lightboxScale = 1;
      updateLightboxScale();
    });
    document.addEventListener("visibilitychange", () => {
      if (stepTimer) stepTimer.setVisibility(!document.hidden);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeLightbox();
    });
    init();
  });
})();
