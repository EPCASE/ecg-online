const assert = require("node:assert/strict");
const Core = require("../frontend/pathway-core.js");
const config = require("../frontend/pedagogy-bav.json");
const catalog = require("../frontend/pathways.json");

(function testInitialStateAndSequence() {
  const state = Core.initialState(config.id);
  assert.equal(state.pathwayId, config.id);
  assert.equal(Core.sequence(config, state).length, 5);
  assert.equal(Core.progress(state, config).percent, 0);
})();

(function testCatalogSelectionKeepsLegacyDefaultAndRejectsUnknownIds() {
  assert.equal(Core.selectCatalogEntry(catalog, null, "fallback").id, "bav-foundations");
  assert.equal(Core.selectCatalogEntry(catalog, "fa-flutter", "fallback").id, "fa-flutter");
  assert.equal(Core.selectCatalogEntry(catalog, "unknown", "fallback"), null);
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
  const key = Core.caseKey(config.cases[0]);
  assert.equal(state.attempts[key].length, 1);
  assert.equal(state.attempts[key][0].changedAfterInitial, true);
  assert.equal(Core.progress(state, config).done, 1);
  assert.equal(Core.nextIndex(state, config), 1);
})();

(function testDiagnosticZeroIsPreserved() {
  let state = Core.initialState(config.id);
  state = Core.recordAttempt(state, config.cases[0], {
    initialAnswer: "Réponse erronée",
    finalAnswer: "Réponse erronée",
    score: 80,
    diagnosticScore: 0,
  });
  assert.equal(Core.attemptHistory(state, config.cases[0])[0].diagnosticScore, 0);
})();

(function testPendingAttemptSurvivesSanitization() {
  let state = Core.initialState(config.id);
  state = Core.lockPendingAttempt(state, config.cases[0], {
    initialAnswer: "Lecture initiale",
    confidence: 60,
    openedAt: 100,
    lockedAt: 200,
  });
  state = Core.recordPendingHint(state);
  state = Core.recordPendingHint(state);
  const restored = Core.sanitizeState(JSON.parse(JSON.stringify(state)), config.id);
  assert.equal(restored.pendingAttempt.initialAnswer, "Lecture initiale");
  assert.equal(restored.pendingAttempt.hintsUsed, 2);
  assert.equal(restored.pendingAttempt.lockedAt, 200);

  const completed = Core.recordAttempt(restored, config.cases[0], {
    initialAnswer: "Lecture initiale",
    finalAnswer: "Lecture finale",
    hintsUsed: 2,
    diagnosticScore: 75,
  });
  assert.equal(completed.pendingAttempt, null);
})();

(function testLegacyNumericAttemptKeysRemainReadable() {
  const state = Core.initialState(config.id);
  state.attempts["23"] = [{ diagnosticScore: 75 }];
  assert.equal(Core.attemptHistory(state, config.cases[0]).length, 1);
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
  const failed = Core.markMastery(Core.initialState(config.id), { passed: false, diagnosticScore: 40 });
  const state = Core.unlockRemediation(failed);
  const seq = Core.sequence(config, state);
  assert.equal(seq.length, 6);
  assert.equal(seq[5].num, 29);
  assert.equal(state.mastery.passed, false);
  assert.equal(Core.canValidateMastery(config.remediation, 0), false);
  assert.equal(Core.canValidateMastery(config.cases.at(-1), 0), true);
})();

(function testSanitizeRejectsAnotherPathway() {
  const state = Core.sanitizeState({ pathwayId: "other", currentIndex: 99 }, config.id);
  assert.equal(state.pathwayId, config.id);
  assert.equal(state.currentIndex, 0);
})();

(function testLegacyAssistedRemediationCannotRemainMastered() {
  const migrated = Core.sanitizeState({
    pathwayId: config.id,
    remediationActive: true,
    completedAt: "2026-01-01",
    mastery: { passed: true, diagnosticScore: 90 },
    attempts: {},
  }, config.id);
  assert.equal(migrated.mastery.passed, false);
  assert.equal(migrated.mastery.diagnosticScore, null);
  assert.equal(migrated.mastery.migratedFromAssistedRemediation, true);
  assert.equal(migrated.completedAt, null);

  const migratedFailure = Core.sanitizeState({
    pathwayId: config.id,
    remediationActive: true,
    mastery: { passed: false, diagnosticScore: 30 },
    attempts: {},
  }, config.id);
  assert.equal(migratedFailure.mastery.passed, false);
  assert.equal(migratedFailure.mastery.diagnosticScore, null);
  assert.equal(migratedFailure.mastery.migratedFromAssistedRemediation, true);
})();

console.log("pathway-core: all tests passed");
