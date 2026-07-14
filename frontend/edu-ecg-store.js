(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.EduEcgStore = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const KEY = "edu-ecg:introduction:v2";
  const LEGACY_KEY = "edu-ecg:introduction:v1";

  function makeId() {
    if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") return globalThis.crypto.randomUUID();
    return `edu-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
  }

  function fresh(courseVersion) {
    return {
      version: 2,
      sessionId: makeId(),
      courseVersion: courseVersion || "unknown",
      startedAt: null,
      activeModuleId: null,
      activeIndex: 0,
      modules: {},
      events: [],
    };
  }

  function migrate(parsed) {
    if (parsed && parsed.version === 2 && parsed.sessionId) return parsed;
    const next = fresh(parsed?.courseVersion);
    if (!parsed || typeof parsed !== "object") return next;
    next.activeModuleId = parsed.activeModuleId || null;
    next.activeIndex = Number(parsed.activeIndex || 0);
    for (const [moduleId, moduleRecord] of Object.entries(parsed.modules || {})) {
      next.modules[moduleId] = { completed: Boolean(moduleRecord.completed), activities: {} };
      for (const [activityId, record] of Object.entries(moduleRecord.activities || {})) {
        const hintCount = Number(record.hintsUsed || 0);
        next.modules[moduleId].activities[activityId] = {
          ...record,
          attemptId: record.attemptId || makeId(),
          hintsUsed: Array.isArray(record.hintsUsed)
            ? record.hintsUsed
            : Array.from({ length: hintCount }, (_item, index) => index),
          revisions: Array.isArray(record.revisions) ? record.revisions : [],
        };
      }
    }
    return next;
  }

  function load(storage) {
    try {
      const current = storage.getItem(KEY);
      if (current) return migrate(JSON.parse(current));
      const legacy = storage.getItem(LEGACY_KEY);
      return legacy ? migrate(JSON.parse(legacy)) : fresh();
    } catch (_) {
      return fresh();
    }
  }

  function configure(state, courseVersion) {
    state.courseVersion = courseVersion || state.courseVersion || "unknown";
    return state;
  }

  function save(storage, state) {
    storage.setItem(KEY, JSON.stringify(state));
    return state;
  }

  function activityRecord(state, moduleId, activityId) {
    state.modules[moduleId] ||= { activities: {}, completed: false };
    state.modules[moduleId].activities[activityId] ||= {
      attemptId: makeId(),
      openedAt: new Date().toISOString(),
      openedAtMs: Date.now(),
      firstActionAt: null,
      initialAnswer: null,
      initialSubmittedAt: null,
      revisedAnswer: null,
      revisions: [],
      confidence: null,
      hintsUsed: [],
      locked: false,
      result: null,
    };
    return state.modules[moduleId].activities[activityId];
  }

  function event(state, eventName, context, payload) {
    const data = context || {};
    const item = {
      event_name: eventName,
      timestamp: new Date().toISOString(),
      session_id: state.sessionId,
      course_version: state.courseVersion,
    };
    if (data.attemptId) item.attempt_id = data.attemptId;
    if (data.moduleId) item.module_id = data.moduleId;
    if (data.activityId) item.activity_id = data.activityId;
    if (data.competencyIds) item.competency_ids = data.competencyIds;
    if (Number.isFinite(data.elapsedMs)) item.elapsed_ms = Math.max(0, Math.round(data.elapsedMs));
    if (payload && Object.keys(payload).length) item.payload = payload;
    state.events.push(item);
    if (state.events.length > 500) state.events.splice(0, state.events.length - 500);
    return item;
  }

  function context(record, moduleId, activityId, competencyIds) {
    return {
      attemptId: record?.attemptId,
      moduleId,
      activityId,
      competencyIds,
      elapsedMs: record?.openedAtMs ? Date.now() - record.openedAtMs : 0,
    };
  }

  function startCourse(state) {
    if (state.startedAt) return false;
    state.startedAt = new Date().toISOString();
    event(state, "course_started");
    return true;
  }

  function recordFirstAction(state, moduleId, activityId, competencyIds) {
    const record = activityRecord(state, moduleId, activityId);
    if (record.firstActionAt) return record;
    record.firstActionAt = new Date().toISOString();
    event(state, "first_action", context(record, moduleId, activityId, competencyIds));
    return record;
  }

  function lockInitial(state, moduleId, activityId, answer, confidence, competencyIds) {
    const record = activityRecord(state, moduleId, activityId);
    if (record.initialAnswer !== null) return record;
    record.initialAnswer = JSON.parse(JSON.stringify(answer));
    record.firstActionAt ||= new Date().toISOString();
    record.initialSubmittedAt = new Date().toISOString();
    record.confidence = confidence == null ? null : String(confidence);
    record.locked = true;
    const common = context(record, moduleId, activityId, competencyIds);
    event(state, "initial_answer_submitted", common);
    if (record.confidence !== null) {
      event(state, "confidence_submitted", common, { confidence: record.confidence });
    }
    return record;
  }

  function useHint(state, moduleId, activityId, hintIndex, competencyIds) {
    const record = activityRecord(state, moduleId, activityId);
    if (!record.hintsUsed.includes(hintIndex)) record.hintsUsed.push(hintIndex);
    event(
      state,
      "hint_opened",
      context(record, moduleId, activityId, competencyIds),
      { hint_index: hintIndex },
    );
    return record;
  }

  function setResult(state, moduleId, activityId, answer, result, competencyIds) {
    const record = activityRecord(state, moduleId, activityId);
    const isRevision = record.result !== null
      || (record.initialAnswer !== null && record.hintsUsed.length > 0)
      || (record.initialAnswer !== null
        && JSON.stringify(record.initialAnswer) !== JSON.stringify(answer));
    if (isRevision) {
      record.revisedAnswer = JSON.parse(JSON.stringify(answer));
      record.revisions.push({ at: new Date().toISOString(), answer: record.revisedAnswer });
      event(state, "revised_answer_submitted", context(record, moduleId, activityId, competencyIds));
    }
    record.finalAnswer = JSON.parse(JSON.stringify(answer));
    record.result = result;
    record.completedAt = new Date().toISOString();
    const common = context(record, moduleId, activityId, competencyIds);
    for (const error of result.criticalErrors || []) {
      event(state, "critical_error_detected", common, { error_id: error });
    }
    event(state, "activity_completed", common, {
      evaluated: result.evaluated,
      percent: result.percent,
      revised: isRevision,
    });
    return record;
  }

  return {
    KEY, LEGACY_KEY, makeId, fresh, migrate, load, configure, save,
    activityRecord, event, context, startCourse, recordFirstAction,
    lockInitial, useHint, setResult,
  };
});
