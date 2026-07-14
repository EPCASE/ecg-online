const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const Core = require("../frontend/edu-ecg-core.js");
const Store = require("../frontend/edu-ecg-store.js");

const module0 = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "edu_ecg", "modules", "module_00.json"), "utf8"));
const module1 = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "edu_ecg", "modules", "module_01.json"), "utf8"));
const module2 = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "edu_ecg", "modules", "module_02.json"), "utf8"));

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

function completeDraftAnswer(item) {
  const response = item.response || {};
  switch (item.activity_type) {
    case "single_choice": case "image_comparison": {
      const option = (response.options || [])[0];
      if (Number(response.cases) > 1) {
        return { choices: Array.from({ length: Number(response.cases) }, () => Core.optionValue(option, 0)) };
      }
      return { choice: Core.optionValue(option, 0) };
    }
    case "short_answer": return { text: "Réponse qualitative de test" };
    case "card_sorting": return {
      assignments: Object.fromEntries((response.cards || []).map((card) => [card.id, card.category || response.categories[0]])),
    };
    case "ordering_cards": return response.cards?.length
      ? { order: response.cards.map((card) => card.id) }
      : { text: "Ordre proposé dans le prototype" };
    case "matching_pairs": return {
      pairs: Object.fromEntries((response.left_items || []).map((left) => [left, response.right_items[0]])),
    };
    case "image_hotspot_labeling": return {
      labels: Object.fromEntries((response.targets || []).map((target, index) => {
        const id = typeof target === "object" ? target.id : String(target || index);
        return [id, "annotation"];
      })),
    };
    case "integrated_assessment": {
      if (!Array.isArray(response.tasks) || response.tasks.some((task) => typeof task !== "object")) {
        return { text: "Réponse globale au test réservé" };
      }
      return {
        tasks: Object.fromEntries(response.tasks.map((task) => [task.id, { text: "Réponse qualitative" }])),
      };
    }
    case "micro_lesson": return { continued: true };
    default: return {};
  }
}

(function testM1AndM2DraftModulesCanBeCompletedWithoutFabricatedAssets() {
  for (const module of [module1, module2]) {
    for (const item of module.activities) {
      const answer = completeDraftAnswer(item);
      assert.equal(Core.isComplete(item, answer), true, `${item.id} must not block progression`);
      if (item.phase === "test") {
        assert.deepEqual(item.hints, []);
        assert.equal(item.asset_policy.reserved_for_test, true);
      }
    }
  }
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
