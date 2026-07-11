/* pathway-core.js — logique pure du micro-parcours ECG, testable sans navigateur. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.ECGPathwayCore = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const STATE_VERSION = 2;

  function nowIso() {
    return new Date().toISOString();
  }

  function initialState(pathwayId) {
    return {
      version: STATE_VERSION,
      pathwayId,
      startedAt: null,
      completedAt: null,
      currentIndex: 0,
      remediationActive: false,
      attempts: {},
      mastery: null,
      pendingAttempt: null,
    };
  }

  function sanitizeState(raw, pathwayId) {
    if (!raw || typeof raw !== "object" || raw.pathwayId !== pathwayId) {
      return initialState(pathwayId);
    }
    const remediationActive = Boolean(raw.remediationActive);
    let mastery = raw.mastery && typeof raw.mastery === "object" ? raw.mastery : null;
    let completedAt = raw.completedAt || null;
    // Les versions antérieures pouvaient valider à tort une remédiation aidée.
    // Or une remédiation n'était activée qu'après l'échec du test autonome.
    if (remediationActive && mastery && mastery.sourcePhase !== "mastery") {
      mastery = {
        ...mastery,
        passed: false,
        diagnosticScore: null,
        migratedFromAssistedRemediation: true,
      };
      completedAt = null;
    }
    return {
      version: STATE_VERSION,
      pathwayId,
      startedAt: raw.startedAt || null,
      completedAt,
      currentIndex: Number.isInteger(raw.currentIndex) && raw.currentIndex >= 0 ? raw.currentIndex : 0,
      remediationActive,
      attempts: raw.attempts && typeof raw.attempts === "object" ? raw.attempts : {},
      mastery,
      pendingAttempt: raw.pendingAttempt && typeof raw.pendingAttempt === "object"
        ? raw.pendingAttempt
        : null,
    };
  }

  function caseKey(caseDef) {
    return String(caseDef.step_id || caseDef.num);
  }

  function attemptHistory(state, caseDef) {
    const attempts = (state && state.attempts) || {};
    const primary = attempts[caseKey(caseDef)];
    if (Array.isArray(primary)) return primary;
    const legacy = attempts[String(caseDef.num)];
    return Array.isArray(legacy) ? legacy : [];
  }

  function sequence(config, state) {
    const base = Array.isArray(config.cases) ? config.cases.slice() : [];
    if (state && state.remediationActive && config.remediation) base.push(config.remediation);
    return base;
  }

  function selectCatalogEntry(catalog, requestedId, fallbackId) {
    const pathways = catalog && Array.isArray(catalog.pathways) ? catalog.pathways : [];
    const selectedId = requestedId || (catalog && catalog.default_id) || fallbackId;
    return pathways.find((item) => item.id === selectedId) || null;
  }

  function diagnosticScore(result) {
    const candidate = result && result.score_diagnostic;
    if (Number.isFinite(candidate)) return Number(candidate);
    if (result && Number.isFinite(result.score)) return Number(result.score);
    return 0;
  }

  function hasUnsafeError(result, config) {
    const unsafeTypes = (config.mastery && config.mastery.unsafe_error_types) || ["etudiant"];
    return unsafeTypes.includes(String((result && result.type_erreur) || ""));
  }

  function normalizeAnswer(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, " ")
      .trim();
  }

  function patternTokens(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9*]+/g, " ")
      .trim()
      .split(" ")
      .filter(Boolean);
  }

  function tokenMatches(word, pattern) {
    if (pattern.endsWith("*")) return word.startsWith(pattern.slice(0, -1));
    return word === pattern;
  }

  function occurrenceIsNegated(words, start, end) {
    const before = words.slice(Math.max(0, start - 3), start);
    const after = words.slice(end, Math.min(words.length, end + 3));
    const precedingNegations = new Set([
      "aucun", "aucune", "absence", "exclu", "exclue", "exclure",
      "elimine", "eliminee", "ni", "non", "pas", "sans",
    ]);
    if (before.some((word) => precedingNegations.has(word))) return true;
    if (after.some((word) => /^(absen|dout|ecart|elimin|exclu|improbabl|rejet)/.test(word))) return true;
    return after[0] === "non" && /^(certain|confirm|observ|present|retrouv|reten|visible)/.test(after[1] || "");
  }

  function answerTermMatches(answer, term) {
    const words = normalizeAnswer(answer).split(" ").filter(Boolean);
    const expected = patternTokens(term);
    if (!words.length || !expected.length) return false;
    for (let start = 0; start <= words.length - expected.length; start += 1) {
      const matches = expected.every((pattern, offset) => tokenMatches(words[start + offset], pattern));
      if (matches && !occurrenceIsNegated(words, start, start + expected.length)) return true;
    }
    return false;
  }

  function answerAlternativeMatches(answer, alternative) {
    if (Array.isArray(alternative)) {
      return alternative.length > 0 && alternative.every((term) => answerTermMatches(answer, term));
    }
    return answerTermMatches(answer, alternative);
  }

  function requiredAnswerConceptsMatched(answer, config) {
    const concepts = config && config.mastery && config.mastery.required_answer_concepts;
    if (!Array.isArray(concepts) || concepts.length === 0) return true;
    return concepts.every((alternatives) => (
      Array.isArray(alternatives)
      && alternatives.length > 0
      && alternatives.some((alternative) => answerAlternativeMatches(answer, alternative))
    ));
  }

  function resultConceptTexts(result) {
    const found = Array.isArray(result && result.elements_trouves) ? result.elements_trouves : [];
    const detected = Array.isArray(result && result.concepts_detectes) ? result.concepts_detectes : [];
    const affirmed = detected.filter((item) => String((item && item.statut) || "present") === "present");
    return [
      ...found.map((item) => item && item.label),
      ...affirmed.flatMap((item) => [
        item && item.label,
        item && item.concept,
        item && item.id,
        item && item.terme,
      ]),
    ].filter((value) => typeof value === "string" && value.trim());
  }

  function requiredResultConceptsMatched(result, config) {
    const concepts = config && config.mastery && config.mastery.required_result_concepts;
    if (!Array.isArray(concepts) || concepts.length === 0) return true;
    const texts = resultConceptTexts(result);
    return concepts.every((alternatives) => (
      Array.isArray(alternatives)
      && alternatives.length > 0
      && alternatives.some((alternative) => (
        texts.some((value) => answerAlternativeMatches(value, alternative))
      ))
    ));
  }

  function evaluateMastery(result, config, answer) {
    const threshold = Number((config.mastery && config.mastery.diagnostic_threshold) || 75);
    const score = diagnosticScore(result);
    const unsafe = hasUnsafeError(result, config);
    const requiredAnswerMatched = requiredAnswerConceptsMatched(answer, config);
    const requiredResultMatched = requiredResultConceptsMatched(result, config);
    const requiredCriteriaMatched = requiredAnswerMatched && requiredResultMatched;
    return {
      passed: score >= threshold && !unsafe && requiredCriteriaMatched,
      diagnosticScore: score,
      threshold,
      unsafe,
      requiredAnswerMatched,
      requiredResultMatched,
      requiredCriteriaMatched,
    };
  }

  function canValidateMastery(caseDef, hintsUsed) {
    return Boolean(
      caseDef
      && caseDef.phase === "mastery"
      && caseDef.allow_hints === false
      && Number(hintsUsed || 0) === 0,
    );
  }

  function lockPendingAttempt(state, caseDef, payload) {
    const copy = sanitizeState(state, state.pathwayId);
    copy.pendingAttempt = {
      caseKey: caseKey(caseDef),
      caseNum: Number(caseDef.num),
      phase: String(caseDef.phase || ""),
      initialAnswer: String(payload.initialAnswer || ""),
      confidence: Number(payload.confidence || 0),
      hintsUsed: 0,
      openedAt: Number(payload.openedAt || Date.now()),
      lockedAt: Number(payload.lockedAt || Date.now()),
    };
    return copy;
  }

  function recordPendingHint(state) {
    const copy = sanitizeState(state, state.pathwayId);
    if (!copy.pendingAttempt) return copy;
    copy.pendingAttempt = {
      ...copy.pendingAttempt,
      hintsUsed: Number(copy.pendingAttempt.hintsUsed || 0) + 1,
    };
    return copy;
  }

  function clearPendingAttempt(state) {
    const copy = sanitizeState(state, state.pathwayId);
    copy.pendingAttempt = null;
    return copy;
  }

  function recordAttempt(state, caseDef, payload) {
    const copy = sanitizeState(state, state.pathwayId);
    const key = caseKey(caseDef);
    const previous = attemptHistory(copy, caseDef).slice();
    const diagnostic = Number.isFinite(payload.diagnosticScore)
      ? Number(payload.diagnosticScore)
      : Number(payload.score || 0);
    previous.push({
      at: nowIso(),
      phase: caseDef.phase,
      initialAnswer: String(payload.initialAnswer || ""),
      finalAnswer: String(payload.finalAnswer || payload.initialAnswer || ""),
      confidence: Number(payload.confidence || 0),
      hintsUsed: Number(payload.hintsUsed || 0),
      score: Number(payload.score || 0),
      diagnosticScore: diagnostic,
      correspondence: String(payload.correspondence || ""),
      errorType: String(payload.errorType || ""),
      formativeOnly: Boolean(payload.formativeOnly),
      changedAfterInitial: String(payload.finalAnswer || "").trim() !== String(payload.initialAnswer || "").trim(),
    });
    copy.attempts[key] = previous;
    if (key !== String(caseDef.num)) delete copy.attempts[String(caseDef.num)];
    copy.pendingAttempt = null;
    return copy;
  }

  function completedBaseCases(state, config) {
    return (config.cases || []).filter((item) => attemptHistory(state, item).length > 0).length;
  }

  function progress(state, config) {
    const seq = sequence(config, state);
    const done = seq.filter((item) => attemptHistory(state, item).length > 0).length;
    return {
      done,
      total: seq.length,
      percent: seq.length ? Math.round((done / seq.length) * 100) : 0,
    };
  }

  function nextIndex(state, config) {
    const seq = sequence(config, state);
    for (let index = 0; index < seq.length; index += 1) {
      if (attemptHistory(state, seq[index]).length === 0) return index;
    }
    return seq.length;
  }

  function unlockRemediation(state) {
    return { ...state, remediationActive: true, completedAt: null };
  }

  function markMastery(state, evaluation) {
    return {
      ...state,
      mastery: { ...evaluation, sourcePhase: "mastery", evaluatedAt: nowIso() },
      completedAt: evaluation.passed ? nowIso() : null,
    };
  }

  return {
    STATE_VERSION,
    initialState,
    sanitizeState,
    caseKey,
    attemptHistory,
    sequence,
    selectCatalogEntry,
    diagnosticScore,
    hasUnsafeError,
    normalizeAnswer,
    patternTokens,
    answerTermMatches,
    requiredAnswerConceptsMatched,
    resultConceptTexts,
    requiredResultConceptsMatched,
    evaluateMastery,
    canValidateMastery,
    lockPendingAttempt,
    recordPendingHint,
    clearPendingAttempt,
    recordAttempt,
    completedBaseCases,
    progress,
    nextIndex,
    unlockRemediation,
    markMastery,
  };
});
