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

  function remediationCompleted(state, config) {
    const safe = stateForPathway(state, config.id);
    if (!safe || !config.remediation) return false;
    const attempts = (safe.attempts && safe.attempts[String(config.remediation.step_id || config.remediation.num)])
      || (safe.attempts && safe.attempts[String(config.remediation.num)]);
    return Array.isArray(attempts) && attempts.length > 0;
  }

  function pathwayStatus(state, config) {
    const safe = stateForPathway(state, config.id);
    const labels = config.status_labels || {};
    const remediationDone = remediationCompleted(state, config);
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

  function consolidationNeedsAction(state, config) {
    return pathwayStatus(state, config).code === "consolidate"
      && Boolean(config.remediation)
      && !remediationCompleted(state, config);
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

  function itemId(item) {
    return item && item.config && item.config.id
      ? item.config.id
      : item && item.catalog && item.catalog.id
        ? item.catalog.id
        : "";
  }

  function curriculumLevel(item) {
    const raw = item && item.catalog ? Number(item.catalog.curriculum_level) : 1;
    return Number.isInteger(raw) && raw > 0 ? raw : 1;
  }

  function recommendedAfterState(item, items) {
    const ids = item && item.catalog && Array.isArray(item.catalog.recommended_after)
      ? item.catalog.recommended_after.slice()
      : [];
    const itemById = new Map((Array.isArray(items) ? items : []).map((candidate) => [itemId(candidate), candidate]));
    const missing = ids.filter((id) => {
      const prerequisite = itemById.get(id);
      return !prerequisite || pathwayStatus(prerequisite.state, prerequisite.config).code !== "mastered";
    });
    return { ids, missing, met: missing.length === 0 };
  }

  function recommendation(items) {
    if (!Array.isArray(items) || items.length === 0) return { index: -1, reason: "none" };
    const statusAt = (index) => pathwayStatus(items[index].state, items[index].config).code;
    const firstWithStatus = (code) => items.findIndex((item, index) => statusAt(index) === code);

    const inProgress = firstWithStatus("in-progress");
    if (inProgress >= 0) return { index: inProgress, reason: "resume" };

    const consolidate = items.findIndex((item) => consolidationNeedsAction(item.state, item.config));
    if (consolidate >= 0) return { index: consolidate, reason: "consolidate" };

    const fundamental = items.findIndex((item, index) => (
      statusAt(index) === "not-started" && curriculumLevel(item) === 1
    ));
    if (fundamental >= 0) return { index: fundamental, reason: "fundamental" };

    const ready = items
      .map((item, index) => ({ item, index }))
      .filter(({ item, index }) => (
        statusAt(index) === "not-started" && recommendedAfterState(item, items).met
      ))
      .sort((left, right) => (
        curriculumLevel(left.item) - curriculumLevel(right.item) || left.index - right.index
      ))[0];
    if (ready) return { index: ready.index, reason: "recommendations-met" };

    // L’ordre conseillé ne verrouille jamais l’accès à un parcours.
    const openChoice = firstWithStatus("not-started");
    if (openChoice >= 0) return { index: openChoice, reason: "open-choice" };

    let review = -1;
    let highestLevel = -1;
    items.forEach((item, index) => {
      if (statusAt(index) !== "mastered") return;
      const level = curriculumLevel(item);
      if (level >= highestLevel) {
        review = index;
        highestLevel = level;
      }
    });
    return { index: review, reason: review >= 0 ? "review" : "none" };
  }

  function recommendedIndex(items) {
    return recommendation(items).index;
  }

  function competencyStatusLabel(code) {
    return {
      mastered: "Validée sans aide",
      "in-progress": "En cours",
      consolidate: "À consolider",
      "not-started": "Non évaluée",
    }[code] || "Non évaluée";
  }

  function competencyProfile(items) {
    const competencies = (Array.isArray(items) ? items : []).map((item) => {
      const code = pathwayStatus(item.state, item.config).code;
      return {
        id: itemId(item),
        label: (item.catalog && item.catalog.competency_label) || item.config.title,
        code,
        statusLabel: competencyStatusLabel(code),
        curriculumLevel: curriculumLevel(item),
      };
    });
    const mastered = competencies.filter((item) => item.code === "mastered").length;
    return {
      competencies,
      mastered,
      total: competencies.length,
      percent: competencies.length ? Math.round((mastered / competencies.length) * 100) : 0,
    };
  }

  return {
    STORAGE_PREFIX,
    attemptCount,
    stateForPathway,
    remediationCompleted,
    pathwayStatus,
    consolidationNeedsAction,
    pathwayProgress,
    summarize,
    curriculumLevel,
    recommendedAfterState,
    recommendation,
    recommendedIndex,
    competencyStatusLabel,
    competencyProfile,
  };
});
