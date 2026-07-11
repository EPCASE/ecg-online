const assert = require("node:assert/strict");
const Core = require("../frontend/pathway-core.js");
const config = require("../frontend/pedagogy-bav.json");

(function testInitialStateAndSequence() {
  const state = Core.initialState(config.id);
  assert.equal(state.pathwayId, config.id);
  assert.equal(Core.sequence(config, state).length, 5);
  assert.equal(Core.progress(state, config).percent, 0);
})();

(function testAttemptRecording() {
  let state = Core.initialState(config.id);
  state = Core.recordAttempt(state, config.cases[0], {
    initialAnswer: "BAV I",
    finalAnswer: "BAV du premier degré",
    confidence: 70,
    hintsUsed: 1,
    score: 82,
    diagnosticScore: 90,
    correspondence: "exacte",
    errorType: "aucune",
  });
  assert.equal(state.attempts["23"].length, 1);
  assert.equal(state.attempts["23"][0].changedAfterInitial, true);
  assert.equal(Core.progress(state, config).done, 1);
  assert.equal(Core.nextIndex(state, config), 1);
})();

(function testMasteryPassesOnlyWithoutClinicalError() {
  const good = Core.evaluateMastery({ score_diagnostic: 80, type_erreur: "aucune" }, config);
  assert.equal(good.passed, true);

  const unsafe = Core.evaluateMastery({ score_diagnostic: 90, type_erreur: "etudiant" }, config);
  assert.equal(unsafe.passed, false);
  assert.equal(unsafe.unsafe, true);

  const low = Core.evaluateMastery({ score_diagnostic: 70, type_erreur: "aucune" }, config);
  assert.equal(low.passed, false);
})();

(function testRemediationAddsOneCaseOnly() {
  const state = Core.unlockRemediation(Core.initialState(config.id));
  const seq = Core.sequence(config, state);
  assert.equal(seq.length, 6);
  assert.equal(seq[5].num, 29);
})();

(function testSanitizeRejectsAnotherPathway() {
  const state = Core.sanitizeState({ pathwayId: "other", currentIndex: 99 }, config.id);
  assert.equal(state.pathwayId, config.id);
  assert.equal(state.currentIndex, 0);
})();

console.log("pathway-core: all tests passed");
