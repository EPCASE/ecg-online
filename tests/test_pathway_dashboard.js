const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const Dashboard = require("../frontend/pathway-dashboard-core.js");
const catalog = require("../frontend/pathways.json");
const caseBank = require("../data/cases.json");
const scoringConfig = require("../data/scoring_config.json");
const availableCaseNums = new Set(caseBank.cases.map((item) => item.num));

function loadConfig(entry) {
  const filename = path.basename(entry.config_url);
  return JSON.parse(fs.readFileSync(path.join(__dirname, "..", "frontend", filename), "utf8"));
}

(function testCatalogContracts() {
  assert.equal(catalog.schema_version, 1);
  assert.equal(catalog.pathways.length, 3);
  assert.equal(catalog.default_id, "bav-foundations");
  assert.equal(new Set(catalog.pathways.map((item) => item.id)).size, catalog.pathways.length);

  for (const entry of catalog.pathways) {
    const config = loadConfig(entry);
    assert.equal(config.id, entry.id);
    assert.equal(config.schema_version, 1);
    assert.ok(config.cases.length >= 4 && config.cases.length <= 6);
    assert.equal(new Set(config.cases.map((item) => item.num)).size, config.cases.length);
    assert.equal(new Set(config.cases.map((item) => item.step_id)).size, config.cases.length);
    assert.ok(config.cases.every((item) => item.step_id && availableCaseNums.has(item.num)));
    const mastery = config.cases.filter((item) => item.phase === "mastery");
    assert.equal(mastery.length, 1);
    assert.equal(config.cases.at(-1).phase, "mastery");
    assert.equal(mastery[0].allow_hints, false);
    assert.deepEqual(mastery[0].hints, []);
    assert.equal(Boolean(mastery[0].formative_only), false);
    const masteryRoles = scoringConfig.cases[String(mastery[0].num)].roles;
    assert.equal(Object.values(masteryRoles).filter((role) => role === "validant").length, 1);
    for (const item of config.cases.filter((caseDef) => caseDef.allow_hints)) {
      assert.equal(item.hints.length, 3);
    }
    if (config.remediation) {
      assert.ok(config.remediation.step_id);
      assert.ok(availableCaseNums.has(config.remediation.num));
      assert.ok(!config.cases.some((item) => item.step_id === config.remediation.step_id));
    }
  }
})();

(function testStatuses() {
  const config = loadConfig(catalog.pathways[0]);
  assert.equal(Dashboard.pathwayStatus(null, config).code, "not-started");

  const started = { pathwayId: config.id, startedAt: "2026-01-01", attempts: {} };
  assert.equal(Dashboard.pathwayStatus(started, config).code, "in-progress");

  const failed = { ...started, mastery: { passed: false } };
  assert.equal(Dashboard.pathwayStatus(failed, config).code, "consolidate");
  assert.equal(Dashboard.pathwayStatus(failed, config).cta, "Faire la consolidation");

  const remediationPending = { ...failed, remediationActive: true };
  assert.equal(Dashboard.pathwayStatus(remediationPending, config).cta, "Reprendre la consolidation");

  const remediationDone = {
    ...remediationPending,
    attempts: { [config.remediation.step_id]: [{}] },
  };
  assert.equal(Dashboard.pathwayStatus(remediationDone, config).cta, "Voir le bilan");

  const mastered = { ...started, completedAt: "2026-01-02", mastery: { passed: true } };
  assert.equal(Dashboard.pathwayStatus(mastered, config).code, "mastered");

  const otherPathway = { ...mastered, pathwayId: "other" };
  assert.equal(Dashboard.pathwayStatus(otherPathway, config).code, "not-started");

  const legacyAssisted = { ...mastered, remediationActive: true, mastery: { passed: true } };
  assert.equal(Dashboard.pathwayStatus(legacyAssisted, config).code, "consolidate");
})();

(function testPathwayStatesAreIsolated() {
  const first = loadConfig(catalog.pathways[0]);
  const second = loadConfig(catalog.pathways[1]);
  const firstState = {
    pathwayId: first.id,
    startedAt: "2026-01-01",
    mastery: { passed: true },
    attempts: {},
  };
  assert.equal(Dashboard.pathwayStatus(firstState, first).code, "mastered");
  assert.equal(Dashboard.pathwayStatus(firstState, second).code, "not-started");
})();

(function testLegacyRouteAndGenericEngineContracts() {
  const pathwayScript = fs.readFileSync(path.join(__dirname, "..", "frontend", "pathway.js"), "utf8");
  assert.match(pathwayScript, /DEFAULT_PATHWAY_ID = "bav-foundations"/);
  assert.match(pathwayScript, /catalog\.default_id/);
  assert.doesNotMatch(pathwayScript, /Wenckebach|Mobitz II|échappement distal/);
})();

(function testClinicallyConstrainedSequences() {
  const faFlutter = loadConfig(catalog.pathways.find((item) => item.id === "fa-flutter"));
  assert.deepEqual(faFlutter.cases.map((item) => item.num), [37, 39, 42, 41]);
  assert.equal(faFlutter.cases.at(-1).hide_secondary_images, true);
  assert.equal(faFlutter.remediation.num, 38);
  assert.equal(Dashboard.pathwayStatus({ pathwayId: faFlutter.id, mastery: { passed: true }, attempts: {} }, faFlutter).label, "Flutter typique acquis");

  const narrow = loadConfig(catalog.pathways.find((item) => item.id === "regular-narrow-tachycardias"));
  assert.deepEqual(narrow.cases.map((item) => item.num), [37, 42, 43, 44, 40]);
  assert.deepEqual(narrow.cases.filter((item) => item.formative_only).map((item) => item.num), [42, 43, 44]);
  assert.equal(narrow.cases.at(-1).num, 40);
  assert.equal(narrow.remediation.num, 39);
  assert.equal(Dashboard.pathwayStatus({ pathwayId: narrow.id, mastery: { passed: true }, attempts: {} }, narrow).label, "Première orientation acquise");
})();

(function testProgressAndRecommendation() {
  const configs = catalog.pathways.map(loadConfig);
  const state = {
    pathwayId: configs[0].id,
    startedAt: "2026-01-01",
    attempts: { [String(configs[0].cases[0].num)]: [{}] },
  };
  assert.equal(Dashboard.pathwayProgress(state, configs[0]).done, 1);

  const items = configs.map((config, index) => ({ config, state: index === 0 ? state : null }));
  assert.equal(Dashboard.recommendedIndex(items), 0);
  const summary = Dashboard.summarize(items);
  assert.equal(summary.total, 3);
  assert.equal(summary.inProgress, 1);
  assert.equal(summary.notStarted, 2);
})();

console.log("pathway-dashboard: all tests passed");
