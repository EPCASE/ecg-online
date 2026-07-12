/* timing.js — chronométrage actif, testable dans Node et partagé par les interfaces. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.ECGTiming = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function clampMs(value) {
    const number = Number(value);
    return Number.isFinite(number) && number > 0 ? number : 0;
  }

  function createTracker(options = {}) {
    const now = typeof options.now === "function" ? options.now : Date.now;
    const startedAt = Number(options.startedAt || now());
    let backgroundMs = clampMs(options.backgroundMs);
    let backgroundCount = Math.max(0, Number(options.backgroundCount || 0));
    let hiddenSince = options.visible === false ? Number(options.hiddenSince || now()) : 0;
    let firstInputAt = Number(options.firstInputAt || 0);
    let firstInputActiveMs = Number(options.firstInputActiveMs || 0);

    function snapshot(at = now()) {
      const current = Number(at);
      const ongoingBackground = hiddenSince ? Math.max(0, current - hiddenSince) : 0;
      const elapsedMs = Math.max(0, current - startedAt);
      const totalBackground = Math.min(elapsedMs, backgroundMs + ongoingBackground);
      return {
        startedAt,
        elapsedMs,
        activeMs: Math.max(0, elapsedMs - totalBackground),
        backgroundMs: totalBackground,
        backgroundCount,
        firstInputAt,
        firstInputElapsedMs: firstInputAt ? Math.max(0, firstInputAt - startedAt) : null,
        firstInputActiveMs: firstInputAt ? Math.max(0, firstInputActiveMs) : null,
      };
    }

    function setVisibility(visible, at = now()) {
      const current = Number(at);
      if (!visible && !hiddenSince) {
        hiddenSince = current;
        backgroundCount += 1;
      } else if (visible && hiddenSince) {
        backgroundMs += Math.max(0, current - hiddenSince);
        hiddenSince = 0;
      }
      return snapshot(current);
    }

    function markFirstInput(at = now()) {
      if (!firstInputAt) {
        const current = Number(at);
        const currentSnapshot = snapshot(current);
        firstInputAt = current;
        firstInputActiveMs = currentSnapshot.activeMs;
      }
      return snapshot(at);
    }

    return { snapshot, setVisibility, markFirstInput };
  }

  function seconds(value) {
    return Math.round(clampMs(value) / 1000);
  }

  function environment(view = {}) {
    const width = Number(view.width || (typeof window !== "undefined" ? window.innerWidth : 0));
    const height = Number(view.height || (typeof window !== "undefined" ? window.innerHeight : 0));
    const touch = view.touch != null
      ? Boolean(view.touch)
      : Boolean(typeof navigator !== "undefined" && navigator.maxTouchPoints > 0);
    const device = touch && width > 0 && width <= 767
      ? "telephone"
      : (touch && width <= 1100 ? "tablette" : "ordinateur");
    return {
      appareil: device,
      largeur_vue: width || "",
      hauteur_vue: height || "",
      orientation: width && height ? (width > height ? "paysage" : "portrait") : "",
    };
  }

  function metrics(autonomous, total, extras = {}) {
    const initial = autonomous || total || {};
    const complete = total || initial;
    return {
      t_reflexion_s: initial.firstInputElapsedMs == null ? null : seconds(initial.firstInputElapsedMs),
      t_premiere_saisie_active_s: initial.firstInputActiveMs == null ? null : seconds(initial.firstInputActiveMs),
      t_autonome_s: seconds(initial.elapsedMs),
      t_autonome_actif_s: seconds(initial.activeMs),
      t_total_s: seconds(complete.elapsedMs),
      t_total_actif_s: seconds(complete.activeMs),
      t_hors_app_s: seconds(complete.backgroundMs),
      mises_arriere_plan: Number(complete.backgroundCount || 0),
      ...environment(),
      ...extras,
    };
  }

  return { createTracker, environment, metrics, seconds };
});
