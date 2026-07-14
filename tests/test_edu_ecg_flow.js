const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const Core = require("../frontend/edu-ecg-core.js");
const Store = require("../frontend/edu-ecg-store.js");

const module0 = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "edu_ecg", "modules", "module_00.json"), "utf8"));

(function testCompleteModuleZeroContract() {
  assert.equal(module0.id, "M0");
  assert.equal(module0.activities.length, 5);
  assert.deepEqual(module0.activities.map((item) => item.phase), ["prime", "probe", "attach", "strengthen", "test"]);
  const test = module0.activities.find((item) => item.phase === "test");
  assert.deepEqual(test.hints, []);
  assert.equal(test.attempt_policy.allow_revision_after_hint, false);
  assert.equal(test.attempt_policy.max_submissions_before_explanation, 1);
  assert.equal(test.asset_policy.reserved_for_test, true);
})();

(function simulateACompleteResumableModuleZeroRun() {
  let persisted = null;
  const storage = {
    getItem: (key) => key === Store.KEY ? persisted : null,
    setItem: (_key, value) => { persisted = value; },
  };
  const state = Store.fresh("1.0-draft");
  Store.startCourse(state);
  Store.event(state, "module_started", { moduleId: module0.id });

  const answers = {
    M0_PRIME_01: { choice: "different" },
    M0_PROBE_02: { choice: "check", secondary: "ligne de base" },
    M0_ATTACH_03: { continued: true },
    M0_STRENGTHEN_04: { choice: "left" },
    M0_TEST_05: {
      tasks: {
        quality: { choice: "à vérifier" },
        cause: { choice: "mouvement/tremblement" },
        action: { choice: "corriger puis réenregistrer" },
      },
    },
  };

  for (const activity of module0.activities) {
    const answer = answers[activity.id];
    assert.equal(Core.isComplete(activity, answer), true, activity.id);
    Store.recordFirstAction(state, module0.id, activity.id, activity.competency_ids);
    Store.lockInitial(state, module0.id, activity.id, answer, activity.collect_confidence ? "moyenne" : null, activity.competency_ids);
    if (activity.hints.length) {
      assert.notEqual(activity.phase, "test");
      Store.useHint(state, module0.id, activity.id, 0, activity.competency_ids);
    }
    const result = Core.evaluate(activity, answer);
    Store.setResult(state, module0.id, activity.id, answer, result, activity.competency_ids);
  }
  state.modules.M0.completed = true;
  Store.event(state, "module_completed", { moduleId: "M0" });
  Store.save(storage, state);

  const restored = Store.load(storage);
  assert.equal(Object.values(restored.modules.M0.activities).filter((item) => item.completedAt).length, 5);
  assert.deepEqual(restored.modules.M0.activities.M0_PRIME_01.initialAnswer, { choice: "different" });
  assert.deepEqual(restored.modules.M0.activities.M0_TEST_05.hintsUsed, []);
  assert.equal(restored.modules.M0.activities.M0_TEST_05.result.evaluated, false);
  assert.ok(restored.events.some((item) => item.event_name === "confidence_submitted"));
  assert.ok(restored.events.some((item) => item.event_name === "hint_opened"));
  assert.ok(restored.events.some((item) => item.event_name === "module_completed"));
})();

(function testLegacyProgressMigrationPreservesInitialAnswer() {
  const migrated = Store.migrate({
    version: 1,
    activeModuleId: "M0",
    activeIndex: 1,
    modules: {
      M0: {
        activities: {
          M0_PROBE_02: {
            initialAnswer: { choice: "check" },
            hintsUsed: 1,
            revisions: [{ answer: { choice: "repeat" } }],
          },
        },
      },
    },
  });
  const record = migrated.modules.M0.activities.M0_PROBE_02;
  assert.deepEqual(record.initialAnswer, { choice: "check" });
  assert.deepEqual(record.hintsUsed, [0]);
  assert.ok(record.attemptId);
})();

console.log("edu-ecg-flow: all tests passed");
