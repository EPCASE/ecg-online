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
  assert.equal(Core.evaluate(activity("short_answer", { expected_concepts: ["temps horizontal", "amplitude verticale"] }), { text: "Temps horizontal et amplitude verticale" }).evaluated, false);
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

(function testReservedActivitiesStayUsableWithoutInventedContent() {
  const reservedOrder = activity("ordering_cards", { mode: "order_images" });
  assert.equal(Core.isComplete(reservedOrder, { text: "V1 puis V2" }), true);
  assert.equal(Core.evaluate(reservedOrder, { text: "V1 puis V2" }).evaluated, false);

  const reservedTest = activity("integrated_assessment", {
    tasks: [
      { id: "pairs", type: "matching_pairs" },
      { id: "waves", type: "image_hotspot_labeling" },
    ],
  });
  const answer = { tasks: { pairs: { text: "association" }, waves: { text: "P QRS T" } } };
  assert.equal(Core.isComplete(reservedTest, answer), true);
  assert.equal(Core.evaluate(reservedTest, answer).evaluated, false);
})();

(function testRepeatedSingleChoiceCasesRequireOneAnswerPerCase() {
  const repeated = activity("single_choice", { cases: 3, options: ["positive", "négative", "équiphasique"] });
  assert.equal(Core.isComplete(repeated, { choices: ["positive", "négative"] }), false);
  assert.equal(Core.isComplete(repeated, { choices: ["positive", "négative", "équiphasique"] }), true);
  assert.equal(Core.evaluate(repeated, { choices: ["positive", "négative", "équiphasique"] }).evaluated, false);
})();

(function testNestedCasesAndMissingOptionsHaveExplicitCompletionRules() {
  const nested = activity("single_choice", {
    cases: [
      { case: "peau grasse", options: ["nettoyer", "ignorer"] },
      { case: "peau humide", options: ["sécher", "augmenter"] },
    ],
  });
  assert.equal(Core.isComplete(nested, { cases: ["nettoyer"] }), false);
  assert.equal(Core.isComplete(nested, { cases: ["nettoyer", "sécher"] }), true);
  const unspecified = activity("image_comparison", { type: "multiple_choice" });
  assert.equal(Core.isComplete(unspecified, { text: "erreurs repérées" }), true);
  assert.equal(Core.evaluate(unspecified, { text: "erreurs repérées" }).evaluated, false);
})();

(function testPerImageCauseActionAndMixedCasesAreCompleteOnlyAsASet() {
  const perImage = { ...activity("image_comparison", { type: "single_choice_per_image", options: ["artéfact", "activité"] }), assets: ["a.png", "b.png"] };
  assert.equal(Core.isComplete(perImage, { choices: ["artéfact"] }), false);
  assert.equal(Core.isComplete(perImage, { choices: ["artéfact", "activité"] }), true);

  const causeAction = activity("single_choice", { cause_options: ["contact"], action_options: ["vérifier"] });
  assert.equal(Core.isComplete(causeAction, { cause: "contact" }), false);
  assert.equal(Core.isComplete(causeAction, { cause: "contact", action: "vérifier" }), true);

  const mixed = { ...activity("integrated_assessment", { tasks_per_case: ["identification", "cause", "action"] }), assets: ["a.png", "b.png"] };
  const cases = [
    { identification: "x", cause: "y", action: "z" },
    { identification: "x", cause: "y", action: "z" },
  ];
  assert.equal(Core.isComplete(mixed, { cases: cases.slice(0, 1) }), false);
  assert.equal(Core.isComplete(mixed, { cases }), true);
  assert.equal(Core.evaluate(mixed, { cases }).evaluated, false);
})();

(function testFreeChecklistModeIsRecognized() {
  const checklist = activity("sequence_checklist", { mode: "free_checklist", maximum_items: 10 });
  assert.equal(Core.isComplete(checklist, { text: "" }), false);
  assert.equal(Core.isComplete(checklist, { text: "identité\nplacement\nqualité" }), true);
  assert.equal(Core.evaluate(checklist, { text: "identité\nplacement\nqualité" }).evaluated, false);
})();

(function testMasteryIsCalculatedFromCompletedAutonomousAssessment() {
  const module = {
    mastery_threshold_percent: 80,
    domain_competency_ids: { waves: ["M1.2"], conduction: ["M1.4"] },
    results_domains: [
      { id: "waves", label: "Ondes" },
      { id: "conduction", label: "Conduction" },
    ],
    activities: [
      { id: "TEST", phase: "test", competency_ids: ["M1.2", "M1.4"] },
    ],
  };
  assert.deepEqual(Core.domainResults(module, {}), [
    { id: "waves", label: "Ondes", status: "non évalué", percent: null },
    { id: "conduction", label: "Conduction", status: "non évalué", percent: null },
  ]);
  const acquired = Core.domainResults(module, { TEST: { result: { evaluated: true, earned: 9, possible: 10, criticalErrors: [] } } });
  assert.equal(acquired[0].status, "acquis");
  assert.equal(acquired[0].percent, 90);
  const blocked = Core.domainResults(module, { TEST: { result: { evaluated: true, earned: 9, possible: 10, criticalErrors: ["critical"] } } });
  assert.equal(blocked[1].status, "à consolider");
})();

(function testFirstAnswerIsImmutableAndRevisionsRemainAvailable() {
  const state = Store.fresh();
  Store.lockInitial(state, "M0", "M0_PRIME_01", { choice: "same" }, "faible");
  Store.useHint(state, "M0", "M0_PRIME_01", 0);
  Store.setResult(state, "M0", "M0_PRIME_01", { choice: "different" }, { evaluated: true, criticalErrors: [] });
  const record = state.modules.M0.activities.M0_PRIME_01;
  assert.deepEqual(record.initialAnswer, { choice: "same" });
  assert.deepEqual(record.revisions.at(-1).answer, { choice: "different" });
  assert.equal(record.confidence, "faible");
})();

(function testAnalyticsFollowTheV2EventContract() {
  const state = Store.fresh("2.0-draft");
  Store.startCourse(state);
  Store.recordFirstAction(state, "M0", "M0_PROBE_02", ["M0.1"]);
  Store.lockInitial(state, "M0", "M0_PROBE_02", { choice: "check" }, "moyenne", ["M0.1"]);
  const event = state.events.find((item) => item.event_name === "initial_answer_submitted");
  assert.equal(event.session_id, state.sessionId);
  assert.equal(event.course_version, "2.0-draft");
  assert.equal(event.module_id, "M0");
  assert.equal(event.activity_id, "M0_PROBE_02");
  assert.ok(event.attempt_id);
  assert.ok(Number.isInteger(event.elapsed_ms));
  assert.equal(JSON.stringify(state.events).includes("check"), false);
})();

console.log("edu-ecg-core: all tests passed");
