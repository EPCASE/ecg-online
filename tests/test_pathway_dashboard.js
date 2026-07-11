const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const Dashboard = require("../frontend/pathway-dashboard-core.js");
const Core = require("../frontend/pathway-core.js");
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
  assert.equal(catalog.pathways.length, 5);
  assert.equal(catalog.default_id, "bav-foundations");
  assert.equal(new Set(catalog.pathways.map((item) => item.id)).size, catalog.pathways.length);
  assert.deepEqual(catalog.curriculum_levels.map((item) => item.id), [1, 2, 3]);
  assert.equal(new Set(catalog.curriculum_levels.map((item) => item.id)).size, 3);

  const pathwayIds = new Set(catalog.pathways.map((item) => item.id));
  const catalogById = new Map(catalog.pathways.map((item) => [item.id, item]));
  const levelIds = new Set(catalog.curriculum_levels.map((item) => item.id));
  const groupedCounts = catalog.pathways.reduce((counts, entry) => {
    counts.set(entry.curriculum_level, (counts.get(entry.curriculum_level) || 0) + 1);
    return counts;
  }, new Map());
  assert.deepEqual([1, 2, 3].map((level) => groupedCounts.get(level) || 0), [2, 2, 1]);

  for (const entry of catalog.pathways) {
    assert.ok(levelIds.has(entry.curriculum_level));
    assert.ok(Array.isArray(entry.recommended_after));
    assert.equal(new Set(entry.recommended_after).size, entry.recommended_after.length);
    assert.ok(typeof entry.competency_label === "string" && entry.competency_label.trim());
    for (const prerequisiteId of entry.recommended_after) {
      assert.ok(pathwayIds.has(prerequisiteId));
      assert.notEqual(prerequisiteId, entry.id);
      assert.ok(catalogById.get(prerequisiteId).curriculum_level < entry.curriculum_level);
    }
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
    for (const field of ["required_answer_concepts", "required_result_concepts"]) {
      const requiredConcepts = config.mastery[field] || [];
      assert.ok(Array.isArray(requiredConcepts));
      for (const alternatives of requiredConcepts) {
        assert.ok(Array.isArray(alternatives) && alternatives.length > 0);
        for (const alternative of alternatives) {
          if (Array.isArray(alternative)) {
            assert.ok(alternative.length > 0 && alternative.every((term) => typeof term === "string" && term.trim()));
          } else {
            assert.ok(typeof alternative === "string" && alternative.trim());
          }
        }
      }
    }
    const masteryRoles = scoringConfig.cases[String(mastery[0].num)].roles;
    assert.equal(Object.values(masteryRoles).filter((role) => role === "validant").length, 1);
    for (const item of config.cases.filter((caseDef) => caseDef.allow_hints)) {
      assert.equal(item.hints.length, 3);
    }
    for (const item of config.cases.filter((caseDef) => caseDef.image_crop)) {
      assert.ok(item.image_crop.top_percent > 0 && item.image_crop.top_percent < 100);
      assert.ok(item.image_crop.aspect_ratio > 0);
    }
    if (config.remediation) {
      assert.ok(config.remediation.step_id);
      assert.ok(availableCaseNums.has(config.remediation.num));
      assert.ok(!config.cases.some((item) => item.step_id === config.remediation.step_id));
    }
  }

  const visiting = new Set();
  const visited = new Set();
  function visit(pathwayId) {
    if (visiting.has(pathwayId)) assert.fail(`Cycle de recommandation détecté : ${pathwayId}`);
    if (visited.has(pathwayId)) return;
    visiting.add(pathwayId);
    catalogById.get(pathwayId).recommended_after.forEach(visit);
    visiting.delete(pathwayId);
    visited.add(pathwayId);
  }
  catalog.pathways.forEach((entry) => visit(entry.id));
})();

(function testStatuses() {
  const config = loadConfig(catalog.pathways[0]);
  assert.equal(Dashboard.pathwayStatus(null, config).code, "not-started");

  const started = { pathwayId: config.id, startedAt: "2026-01-01", attempts: {} };
  assert.equal(Dashboard.pathwayStatus(started, config).code, "in-progress");

  const failed = { ...started, mastery: { passed: false } };
  assert.equal(Dashboard.pathwayStatus(failed, config).code, "consolidate");
  assert.equal(Dashboard.pathwayStatus(failed, config).cta, "Faire la consolidation");
  assert.equal(Dashboard.consolidationNeedsAction(failed, config), true);

  const remediationPending = { ...failed, remediationActive: true };
  assert.equal(Dashboard.pathwayStatus(remediationPending, config).cta, "Reprendre la consolidation");

  const remediationDone = {
    ...remediationPending,
    attempts: { [config.remediation.step_id]: [{}] },
  };
  assert.equal(Dashboard.pathwayStatus(remediationDone, config).cta, "Voir le bilan");
  assert.equal(Dashboard.remediationCompleted(remediationDone, config), true);
  assert.equal(Dashboard.consolidationNeedsAction(remediationDone, config), false);

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
  assert.match(pathwayScript, /secondary\.length/);
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

  const wideSinus = loadConfig(catalog.pathways.find((item) => item.id === "wide-qrs-sinus"));
  assert.deepEqual(wideSinus.cases.map((item) => item.num), [8, 9, 13, 10, 14]);
  assert.equal(wideSinus.cases.at(-1).num, 14);
  assert.equal(wideSinus.cases.at(-1).image_crop.top_percent, 29);
  assert.equal(wideSinus.remediation.num, 15);
  assert.equal(Dashboard.pathwayStatus({ pathwayId: wideSinus.id, mastery: { passed: true }, attempts: {} }, wideSinus).label, "Morphologies conductives acquises");
  assert.equal(
    Core.evaluateMastery(
      { score_diagnostic: 100, type_erreur: "aucune" },
      wideSinus,
      "Bloc de branche droit isolé",
    ).passed,
    false,
  );

  const wideTachy = loadConfig(catalog.pathways.find((item) => item.id === "wide-complex-tachycardias"));
  assert.deepEqual(wideTachy.cases.map((item) => item.num), [49, 45, 47, 46, 48]);
  assert.deepEqual(wideTachy.cases.filter((item) => item.formative_only).map((item) => item.num), [45, 46]);
  assert.equal(wideTachy.cases.at(-1).num, 48);
  assert.equal(wideTachy.remediation.num, 35);
  assert.equal(Dashboard.pathwayStatus({ pathwayId: wideTachy.id, mastery: { passed: true }, attempts: {} }, wideTachy).label, "Orientation sécurisée acquise");
  const perfectDiagnosticOnly = { score_diagnostic: 100, type_erreur: "aucune" };
  assert.equal(Core.evaluateMastery(perfectDiagnosticOnly, wideTachy, "Tachycardie ventriculaire").passed, false);
  const withDissociation = { ...perfectDiagnosticOnly, elements_trouves: [{ label: "Dissociation atrio-ventriculaire" }] };
  assert.equal(Core.evaluateMastery(withDissociation, wideTachy, "Tachycardie probablement ventriculaire avec ondes P dissociées des QRS").passed, true);
  const withCapture = { ...perfectDiagnosticOnly, concepts_detectes: [{ concept: "Capture supraventriculaire", id: "CAPTURE_SUPRAVENTRICULAIRE", statut: "present" }] };
  assert.equal(Core.evaluateMastery(withCapture, wideTachy, "Tachycardie d’allure ventriculaire avec un complexe atypique").passed, true);
})();

(function testProgressRecommendationAndProfile() {
  const configs = new Map(catalog.pathways.map((entry) => [entry.id, loadConfig(entry)]));
  const ids = catalog.pathways.map((entry) => entry.id);
  const started = (id) => ({ pathwayId: id, startedAt: "2026-01-01", attempts: {} });
  const consolidate = (id) => ({ ...started(id), mastery: { passed: false } });
  const mastered = (id) => ({ ...started(id), mastery: { passed: true } });
  const makeItems = (states = {}) => catalog.pathways.map((entry) => ({
    catalog: entry,
    config: configs.get(entry.id),
    state: Object.prototype.hasOwnProperty.call(states, entry.id) ? states[entry.id] : null,
  }));

  assert.equal(Dashboard.STORAGE_PREFIX, "ecg_pathway_v1_");
  const historicalBav = {
    ...started(ids[0]),
    attempts: { [String(configs.get(ids[0]).cases[0].num)]: [{}] },
  };
  assert.equal(Dashboard.pathwayProgress(historicalBav, configs.get(ids[0])).done, 1);

  let items = makeItems();
  assert.deepEqual(Dashboard.recommendation(items), { index: 0, reason: "fundamental" });
  assert.equal(Dashboard.recommendedIndex(items), 0);

  items = makeItems({
    [ids[0]]: consolidate(ids[0]),
    [ids[3]]: started(ids[3]),
  });
  assert.deepEqual(Dashboard.recommendation(items), { index: 3, reason: "resume" });

  items = makeItems({ [ids[4]]: consolidate(ids[4]) });
  assert.deepEqual(Dashboard.recommendation(items), { index: 4, reason: "consolidate" });

  const completedRemediation = {
    ...consolidate(ids[0]),
    remediationActive: true,
    attempts: { [configs.get(ids[0]).remediation.step_id]: [{}] },
  };
  items = makeItems({ [ids[0]]: completedRemediation });
  assert.deepEqual(Dashboard.recommendation(items), { index: 1, reason: "fundamental" });

  items = makeItems({
    [ids[0]]: mastered(ids[0]),
    [ids[1]]: mastered(ids[1]),
  });
  assert.deepEqual(Dashboard.recommendation(items), { index: 2, reason: "recommendations-met" });

  items = makeItems({
    [ids[0]]: mastered(ids[0]),
    [ids[1]]: mastered(ids[1]),
    [ids[2]]: mastered(ids[2]),
  });
  assert.deepEqual(Dashboard.recommendation(items), { index: 3, reason: "recommendations-met" });
  const wideTachyReadiness = Dashboard.recommendedAfterState(items[4], items);
  assert.equal(wideTachyReadiness.met, false);
  assert.deepEqual(wideTachyReadiness.missing, [ids[3]]);

  items = makeItems({
    [ids[0]]: mastered(ids[0]),
    [ids[1]]: mastered(ids[1]),
    [ids[2]]: mastered(ids[2]),
    [ids[3]]: mastered(ids[3]),
  });
  assert.deepEqual(Dashboard.recommendation(items), { index: 4, reason: "recommendations-met" });

  const openChoiceItem = makeItems()[4];
  assert.deepEqual(Dashboard.recommendation([openChoiceItem]), { index: 0, reason: "open-choice" });

  const allMasteredStates = Object.fromEntries(ids.map((id) => [id, mastered(id)]));
  items = makeItems(allMasteredStates);
  assert.deepEqual(Dashboard.recommendation(items), { index: 4, reason: "review" });
  assert.deepEqual(Dashboard.recommendation([]), { index: -1, reason: "none" });

  const emptyProfile = Dashboard.competencyProfile(makeItems());
  assert.equal(emptyProfile.mastered, 0);
  assert.equal(emptyProfile.total, 5);
  assert.equal(emptyProfile.percent, 0);
  assert.ok(emptyProfile.competencies.every((item) => item.statusLabel === "Non évaluée"));

  const mixedItems = makeItems({
    [ids[0]]: mastered(ids[0]),
    [ids[1]]: started(ids[1]),
    [ids[2]]: consolidate(ids[2]),
  });
  const mixedProfile = Dashboard.competencyProfile(mixedItems);
  assert.equal(mixedProfile.mastered, 1);
  assert.equal(mixedProfile.percent, 20);
  assert.deepEqual(mixedProfile.competencies.map((item) => item.code), [
    "mastered",
    "in-progress",
    "consolidate",
    "not-started",
    "not-started",
  ]);
  assert.equal(mixedProfile.competencies[0].statusLabel, "Validée sans aide");

  const completedProfile = Dashboard.competencyProfile(items);
  assert.equal(completedProfile.mastered, 5);
  assert.equal(completedProfile.percent, 100);

  const summary = Dashboard.summarize(mixedItems);
  assert.equal(summary.total, 5);
  assert.equal(summary.mastered, 1);
  assert.equal(summary.inProgress, 1);
  assert.equal(summary.consolidate, 1);
  assert.equal(summary.notStarted, 2);
})();

(function testCurriculumDashboardMarkup() {
  const html = fs.readFileSync(path.join(__dirname, "..", "frontend", "pathways.html"), "utf8");
  const script = fs.readFileSync(path.join(__dirname, "..", "frontend", "pathways.js"), "utf8");
  assert.match(html, /id="next-recommendation"/);
  assert.match(html, /id="pathway-grid"/);
  assert.match(html, /id="competency-profile"/);
  assert.equal((script.match(/Dashboard\.recommendation\(items\)/g) || []).length, 1);
  assert.match(script, /renderLevels\(catalog, items, recommendation\)/);
  assert.match(script, /renderProfile\(items\)/);
  assert.match(script, /window\.addEventListener\("pageshow"/);
  assert.match(script, /window\.addEventListener\("storage"/);
  assert.match(script, /generation !== renderGeneration/);
  assert.doesNotMatch(script, /item\.config\.subtitle/);
  assert.doesNotMatch(script, /Accessible directement/);
  assert.doesNotMatch(`${html}\n${JSON.stringify(catalog)}`, /défi mixte/i);
})();

(function testUxContracts() {
  const homeHtml = fs.readFileSync(path.join(__dirname, "..", "frontend", "index.html"), "utf8");
  const homeCss = fs.readFileSync(path.join(__dirname, "..", "frontend", "style.css"), "utf8");
  const themeCss = fs.readFileSync(path.join(__dirname, "..", "frontend", "theme.css"), "utf8");
  const appScript = fs.readFileSync(path.join(__dirname, "..", "frontend", "app.js"), "utf8");
  const pathwayHtml = fs.readFileSync(path.join(__dirname, "..", "frontend", "pathway.html"), "utf8");
  const pathwaysHtml = fs.readFileSync(path.join(__dirname, "..", "frontend", "pathways.html"), "utf8");
  const curationHtml = fs.readFileSync(path.join(__dirname, "..", "frontend", "curation.html"), "utf8");
  const pathwayScript = fs.readFileSync(path.join(__dirname, "..", "frontend", "pathway.js"), "utf8");

  assert.match(homeHtml, /<body class="home-mode">/);
  assert.match(themeCss, /--ecg-canvas: #0f1720/);
  assert.match(themeCss, /--ecg-coral: #ff5a6e/);
  assert.match(homeCss, /--bg: var\(--ecg-canvas\)/);
  for (const [html, pageStylesheet] of [
    [homeHtml, "/static/style.css"],
    [pathwaysHtml, "/static/pathways.css"],
    [pathwayHtml, "/static/pathway.css"],
    [curationHtml, "/static/style.css"],
  ]) {
    assert.ok(html.indexOf("/static/theme.css") >= 0);
    assert.ok(html.indexOf("/static/theme.css") < html.indexOf(pageStylesheet));
  }
  assert.match(homeHtml, /<a id="action-pathway"[^>]+href="\/static\/pathways\.html"/);
  assert.match(homeHtml, /id="action-explore"/);
  assert.match(homeHtml, /class="home-free-practice"/);
  for (const id of ["action-daily", "action-resume", "action-random"]) {
    assert.match(homeHtml, new RegExp(`id="${id}"`));
  }
  assert.ok(homeHtml.indexOf("/static/pathway-dashboard-core.js") < homeHtml.indexOf("/static/app.js"));
  assert.match(homeCss, /body\.home-mode \.sidebar \{ display: none; \}/);
  assert.doesNotMatch(homeCss, /body\.case-mode \.sidebar \{ display: none; \}/);
  assert.match(appScript, /function setAppMode\(mode\)/);
  assert.match(appScript, /Dashboard\.recommendation\(items\)/);
  assert.match(appScript, /function openBank\(/);
  assert.match(appScript, /pushState\(\{ view: "bank" \}, "", "\/\?view=bank"\)/);
  assert.match(appScript, /\?view=case&case=/);
  assert.match(appScript, /openCase\(requested\.caseNum, \{ updateHistory: false \}\)/);
  assert.match(appScript, /window\.addEventListener\("popstate"/);
  assert.match(appScript, /const item = el\("button", "case-item"/);
  assert.match(appScript, /caseTitle\.focus\(\{ preventScroll: true \}\)/);
  assert.match(pathwayHtml, /href="\/\?view=bank">Banque libre/);
  assert.match(pathwaysHtml, /href="\/\?view=bank">Explorer les 75 cas/);
  assert.doesNotMatch(appScript, /localStorage\.setItem\(Dashboard\.STORAGE_PREFIX/);

  const lockNote = pathwayScript.indexOf("En continuant, tu enregistres cette première lecture");
  const lockButton = pathwayScript.indexOf("Enregistrer ma première lecture");
  assert.ok(lockNote >= 0 && lockNote < lockButton);
  assert.match(pathwayScript, /Soumettre pour correction/);
  assert.match(pathwayScript, /Afficher 1 · Observer/);
  assert.match(pathwayScript, /Évolution de ta réponse/);
  assert.match(pathwayScript, /Commentaire du correcteur/);
  assert.match(pathwayScript, /Voir la suite conseillée/);
  assert.match(pathwayScript, /La consolidation n’effacera pas ta première performance/);
})();

console.log("pathway-dashboard: all tests passed");
