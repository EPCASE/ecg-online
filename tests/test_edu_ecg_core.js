const assert = require("node:assert/strict");
const Core = require("../frontend/edu-ecg-core.js");
const Store = require("../frontend/edu-ecg-store.js");

function activity(type, response, scoring = {}) {
  return { id: `TEST_${type}`, activity_type: type, response, scoring };
}

(function testEveryDeclaredTypeIsSupported() {
  assert.deepEqual(Core.SUPPORTED_TYPES, [
    "single_choice", "multiple_choice", "short_answer", "card_sorting",
    "ordering_cards", "matching_pairs", "image_comparison",
    "image_hotspot_labeling", "sequence_checklist", "integrated_assessment",
    "micro_lesson",
  ]);
})();

(function testDeterministicEvaluators() {
  assert.equal(Core.evaluate(activity("single_choice", { correct_option_id: "b" }), { choice: "b" }).percent, 100);
  assert.equal(Core.evaluate(activity("multiple_choice", { correct_option_ids: ["a", "c"] }), { choices: ["c", "a"] }).correct, true);
  assert.equal(Core.evaluate(activity("short_answer", { expected_concepts: ["temps horizontal", "amplitude verticale"] }), { text: "Temps horizontal et amplitude verticale" }).percent, 100);
  assert.equal(Core.evaluate(activity("card_sorting", { cards: [{ id: "v1", category: "horizontal" }] }), { assignments: { v1: "horizontal" } }).correct, true);
  assert.equal(Core.evaluate(activity("ordering_cards", { correct_order: ["a", "b"] }), { order: ["a", "b"] }).correct, true);
  assert.equal(Core.evaluate(activity("matching_pairs", { correct_pairs: [["P", "oreillettes"]] }), { pairs: { P: "oreillettes" } }).correct, true);
  assert.equal(Core.evaluate(activity("image_comparison", { correct_option_id: "right" }), { choice: "left" }).percent, 0);
  assert.equal(Core.evaluate(activity("image_hotspot_labeling", { correct_labels: { p: "P" } }), { labels: { p: "P" } }).correct, true);
  assert.equal(Core.evaluate(activity("sequence_checklist", { checklist: ["identité", "qualité"] }), { checked: ["qualité", "identité"] }).correct, true);
  assert.equal(Core.evaluate(activity("integrated_assessment", { tasks: [{ id: "q", type: "single_choice", correct_option_id: "oui" }] }), { tasks: { q: { choice: "oui" } } }).correct, true);
  assert.equal(Core.evaluate(activity("micro_lesson", { type: "continue" }), { continued: true }).evaluated, false);
})();

(function testMissingAnswerKeyNeverCreatesAMedicalCorrection() {
  const result = Core.evaluate(activity("single_choice", { options: ["interpréter", "refaire"] }), { choice: "refaire" });
  assert.equal(result.evaluated, false);
  assert.equal(result.correct, null);
  assert.equal(result.percent, null);
})();

(function testCriticalErrorNeedsAnExplicitAnswerMapping() {
  const unsafeWithoutMapping = Core.evaluate(
    activity("single_choice", { correct_option_id: "safe" }, { non_compensable_errors: ["unsafe"] }),
    { choice: "other" },
  );
  assert.deepEqual(unsafeWithoutMapping.criticalErrors, []);

  const unsafeMapped = Core.evaluate(
    activity("single_choice", { correct_option_id: "safe" }, { critical_error_options: { other: "unsafe" } }),
    { choice: "other" },
  );
  assert.deepEqual(unsafeMapped.criticalErrors, ["unsafe"]);
})();

(function testFirstAnswerIsImmutableAndRevisionsRemainAvailable() {
  const state = Store.fresh();
  Store.lockInitial(state, "M0", "M0_PRIME_01", { choice: "same" }, 2);
  Store.lockInitial(state, "M0", "M0_PRIME_01", { choice: "different" }, 4);
  const record = state.modules.M0.activities.M0_PRIME_01;
  assert.deepEqual(record.initialAnswer, { choice: "same" });
  assert.deepEqual(record.revisions.at(-1).answer, { choice: "different" });
  assert.equal(record.confidence, 2);
})();

console.log("edu-ecg-core: all tests passed");
