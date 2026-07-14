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
  assert.deepEqual(module0.activities.find((item) => item.phase === "test").hints, []);
})();

(function simulateAResumableModuleZeroRun() {
  let persisted = null;
  const storage = {
    getItem: () => persisted,
    setItem: (_key, value) => { persisted = value; },
  };
  const state = Store.fresh();
  const first = module0.activities[0];
  Store.lockInitial(state, module0.id, first.id, { choice: "same" }, 1);
  Store.setResult(state, module0.id, first.id, { choice: "different" }, Core.evaluate(first, { choice: "different" }));
  Store.save(storage, state);

  const restored = Store.load(storage);
  const record = restored.modules.M0.activities[first.id];
  assert.deepEqual(record.initialAnswer, { choice: "same" });
  assert.deepEqual(record.revisions.at(-1).answer, { choice: "different" });
  assert.equal(record.result.correct, true);

  const draftProbe = module0.activities[1];
  const draftResult = Core.evaluate(draftProbe, { choice: "check" });
  assert.equal(draftResult.evaluated, false);
})();

console.log("edu-ecg-flow: all tests passed");
