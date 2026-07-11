/* pathway-dashboard-core.js — état pur du tableau multi-parcours. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.ECGPathwayDashboard = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const STORAGE_PREFIX = "ecg_pathway_v1_";

  function attemptCount(state) {
    if (!state || !state.attempts || typeof state.attempts !== "object") return 0;
    return Object.values(state.attempts).reduce(
      (sum, attempts) => sum + (Array.isArray(attempts) ? attempts.length : 0),
      0,
    );
  }

  function stateForPathway(raw, pathwayId) {
    if (!raw || typeof raw !== "object" || raw.pathwayId !== pathwayId) return null;
    return raw;
  }

  function pathwayStatus(state, config) {
    const safe = stateForPathway(state, config.id);
    const labels = config.status_labels || {};
    const remediationAttempts = safe && config.remediation
      ? ((safe.attempts && safe.attempts[String(config.remediation.step_id || config.remediation.num)])
        || (safe.attempts && safe.attempts[String(config.remediation.num)]))
      : null;
    const remediationDone = Array.isArray(remediationAttempts) && remediationAttempts.length > 0;
    const consolidationCta = !config.remediation
      ? "Voir le bilan"
      : !safe || !safe.remediationActive
        ? "Faire la consolidation"
        : remediationDone
          ? "Voir le bilan"
          : "Reprendre la consolidation";
    if (safe && safe.remediationActive && safe.mastery && safe.mastery.sourcePhase !== "mastery") {
      return { code: "consolidate", label: labels.consolidate || "À consolider", cta: consolidationCta };
    }
    if (safe && safe.mastery && safe.mastery.passed) {
      return { code: "mastered", label: labels.mastered || "Acquis", cta: "Revoir le parcours" };
    }
    if (safe && safe.mastery && safe.mastery.passed === false) {
      return { code: "consolidate", label: labels.consolidate || "À consolider", cta: consolidationCta };
    }
    if (safe && (safe.startedAt || attemptCount(safe) > 0)) {
      return { code: "in-progress", label: labels.in_progress || "En cours", cta: "Reprendre" };
    }
    return { code: "not-started", label: labels.not_started || "Non commencé", cta: "Commencer" };
  }

  function pathwayProgress(state, config) {
    const safe = stateForPathway(state, config.id);
    const sequence = Array.isArray(config.cases) ? config.cases.slice() : [];
    if (safe && safe.remediationActive && config.remediation) sequence.push(config.remediation);
    const attempts = (safe && safe.attempts) || {};
    const done = sequence.filter((item) => {
      const values = attempts[String(item.step_id || item.num)];
      const legacy = attempts[String(item.num)];
      return (Array.isArray(values) && values.length > 0)
        || (Array.isArray(legacy) && legacy.length > 0);
    }).length;
    return {
      done,
      total: sequence.length,
      percent: sequence.length ? Math.round((done / sequence.length) * 100) : 0,
    };
  }

  function summarize(items) {
    const statuses = items.map((item) => pathwayStatus(item.state, item.config).code);
    return {
      total: items.length,
      mastered: statuses.filter((code) => code === "mastered").length,
      inProgress: statuses.filter((code) => code === "in-progress").length,
      consolidate: statuses.filter((code) => code === "consolidate").length,
      notStarted: statuses.filter((code) => code === "not-started").length,
    };
  }

  function recommendedIndex(items) {
    const priority = ["in-progress", "consolidate", "not-started", "mastered"];
    for (const code of priority) {
      const index = items.findIndex((item) => pathwayStatus(item.state, item.config).code === code);
      if (index >= 0) return index;
    }
    return -1;
  }

  return {
    STORAGE_PREFIX,
    attemptCount,
    stateForPathway,
    pathwayStatus,
    pathwayProgress,
    summarize,
    recommendedIndex,
  };
});
