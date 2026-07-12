const assert = require("node:assert/strict");
const Timing = require("../frontend/timing.js");

let current = 1000;
const tracker = Timing.createTracker({ now: () => current, startedAt: current, visible: true });
current = 4000;
tracker.markFirstInput();
current = 6000;
tracker.setVisibility(false);
current = 11000;
tracker.setVisibility(true);
current = 16000;
const total = tracker.snapshot();

assert.equal(total.elapsedMs, 15000);
assert.equal(total.backgroundMs, 5000);
assert.equal(total.activeMs, 10000);
assert.equal(total.backgroundCount, 1);
assert.equal(total.firstInputElapsedMs, 3000);
assert.equal(total.firstInputActiveMs, 3000);

const meta = Timing.metrics(tracker.snapshot(6000), total, { brouillon_restaure: true });
assert.equal(meta.t_autonome_s, 5);
assert.equal(meta.t_total_s, 15);
assert.equal(meta.t_total_actif_s, 10);
assert.equal(meta.t_hors_app_s, 5);
assert.equal(meta.brouillon_restaure, true);

assert.deepEqual(
  Timing.environment({ width: 390, height: 844, touch: true }),
  { appareil: "telephone", largeur_vue: 390, hauteur_vue: 844, orientation: "portrait" },
);

console.log("timing: all tests passed");
