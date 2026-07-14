(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.EduEcgStore = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const KEY = "edu-ecg:introduction:v1";

  function fresh() {
    return { version: 1, activeModuleId: null, activeIndex: 0, modules: {}, events: [] };
  }

  function load(storage) {
    try {
      const parsed = JSON.parse(storage.getItem(KEY));
      return parsed && parsed.version === 1 ? parsed : fresh();
    } catch (_) {
      return fresh();
    }
  }

  function save(storage, state) {
    storage.setItem(KEY, JSON.stringify(state));
    return state;
  }

  function activityRecord(state, moduleId, activityId) {
    state.modules[moduleId] ||= { activities: {}, completed: false };
    state.modules[moduleId].activities[activityId] ||= {
      openedAt: new Date().toISOString(), firstActionAt: null, initialAnswer: null,
      revisions: [], confidence: null, hintsUsed: 0, locked: false, result: null,
    };
    return state.modules[moduleId].activities[activityId];
  }

  function event(state, type, data) {
    state.events.push({ type, at: new Date().toISOString(), ...(data || {}) });
    if (state.events.length > 500) state.events.splice(0, state.events.length - 500);
  }

  function lockInitial(state, moduleId, activityId, answer, confidence) {
    const record = activityRecord(state, moduleId, activityId);
    if (record.initialAnswer === null) {
      record.initialAnswer = JSON.parse(JSON.stringify(answer));
      record.firstActionAt ||= new Date().toISOString();
      record.confidence = confidence == null ? null : Number(confidence);
    }
    record.revisions.push({ at: new Date().toISOString(), answer: JSON.parse(JSON.stringify(answer)) });
    record.locked = true;
    event(state, "initial_response_locked", { moduleId, activityId, confidence: record.confidence });
    return record;
  }

  function useHint(state, moduleId, activityId) {
    const record = activityRecord(state, moduleId, activityId);
    record.hintsUsed += 1;
    event(state, "hint_opened", { moduleId, activityId, hintNumber: record.hintsUsed });
    return record;
  }

  function setResult(state, moduleId, activityId, answer, result) {
    const record = activityRecord(state, moduleId, activityId);
    record.revisions.push({ at: new Date().toISOString(), answer: JSON.parse(JSON.stringify(answer)) });
    record.result = result;
    record.completedAt = new Date().toISOString();
    event(state, "activity_completed", { moduleId, activityId, evaluated: result.evaluated, percent: result.percent });
    return record;
  }

  return { KEY, fresh, load, save, activityRecord, event, lockInitial, useHint, setResult };
});
