/* pathway-core.js — logique pure du micro-parcours ECG, testable sans navigateur. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.ECGPathwayCore = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const STATE_VERSION = 1;

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
    };
  }

  function sanitizeState(raw, pathwayId) {
    if (!raw || typeof raw !== "object" || raw.pathwayId !== pathwayId) {
      return initialState(pathwayId);
    }
    return {
      version: STATE_VERSION,
      pathwayId,
      startedAt: raw.startedAt || null,
      completedAt: raw.completedAt || null,
      currentIndex: Number.isInteger(raw.currentIndex) && raw.currentIndex >= 0 ? raw.currentIndex : 0,
      remediationActive: Boolean(raw.remediationActive),
      attempts: raw.attempts && typeof raw.attempts === "object" ? raw.attempts : {},
      mastery: raw.mastery && typeof raw.mastery === "object" ? raw.mastery : null,
    };
  }

  function sequence(config, state) {
    const base = Array.isArray(config.cases) ? config.cases.slice() : [];
    if (state && state.remediationActive && config.remediation) base.push(config.remediation);
    return base;
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

  function evaluateMastery(result, config) {
    const threshold = Number((config.mastery && config.mastery.diagnostic_threshold) || 75);
    const score = diagnosticScore(result);
    const unsafe = hasUnsafeError(result, config);
    return {
      passed: score >= threshold && !unsafe,
      diagnosticScore: score,
      threshold,
      unsafe,
    };
  }

  function recordAttempt(state, caseDef, payload) {
    const copy = sanitizeState(state, state.pathwayId);
    const key = String(caseDef.num);
    const previous = Array.isArray(copy.attempts[key]) ? copy.attempts[key].slice() : [];
    previous.push({
      at: nowIso(),
      phase: caseDef.phase,
      initialAnswer: String(payload.initialAnswer || ""),
      finalAnswer: String(payload.finalAnswer || payload.initialAnswer || ""),
      confidence: Number(payload.confidence || 0),
      hintsUsed: Number(payload.hintsUsed || 0),
      score: Number(payload.score || 0),
      diagnosticScore: Number(payload.diagnosticScore || payload.score || 0),
      correspondence: String(payload.correspondence || ""),
      errorType: String(payload.errorType || ""),
      changedAfterInitial: String(payload.finalAnswer || "").trim() !== String(payload.initialAnswer || "").trim(),
    });
    copy.attempts[key] = previous;
    return copy;
  }

  function completedBaseCases(state, config) {
    const nums = (config.cases || []).map((item) => String(item.num));
    return nums.filter((num) => Array.isArray(state.attempts[num]) && state.attempts[num].length > 0).length;
  }

  function progress(state, config) {
    const seq = sequence(config, state);
    const done = seq.filter((item) => {
      const attempts = state.attempts[String(item.num)];
      return Array.isArray(attempts) && attempts.length > 0;
    }).length;
    return {
      done,
      total: seq.length,
      percent: seq.length ? Math.round((done / seq.length) * 100) : 0,
    };
  }

  function nextIndex(state, config) {
    const seq = sequence(config, state);
    for (let index = 0; index < seq.length; index += 1) {
      const attempts = state.attempts[String(seq[index].num)];
      if (!Array.isArray(attempts) || attempts.length === 0) return index;
    }
    return seq.length;
  }

  function unlockRemediation(state) {
    return { ...state, remediationActive: true, completedAt: null, mastery: null };
  }

  function markMastery(state, evaluation) {
    return {
      ...state,
      mastery: { ...evaluation, evaluatedAt: nowIso() },
      completedAt: evaluation.passed ? nowIso() : null,
    };
  }

  return {
    STATE_VERSION,
    initialState,
    sanitizeState,
    sequence,
    diagnosticScore,
    hasUnsafeError,
    evaluateMastery,
    recordAttempt,
    completedBaseCases,
    progress,
    nextIndex,
    unlockRemediation,
    markMastery,
  };
});
