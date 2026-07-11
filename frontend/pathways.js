/* pathways.js — tableau de progression des micro-parcours. */
(() => {
  "use strict";

  const CATALOG_URL = "/static/pathways.json";
  const Dashboard = window.ECGPathwayDashboard;

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  async function fetchJson(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Erreur HTTP ${response.status}`);
    return response.json();
  }

  function loadState(pathwayId) {
    try {
      return JSON.parse(localStorage.getItem(Dashboard.STORAGE_PREFIX + pathwayId) || "null");
    } catch {
      return null;
    }
  }

  function renderSummary(items) {
    const summary = Dashboard.summarize(items);
    document.querySelector("#summary-mastered").textContent = summary.mastered;
    document.querySelector("#summary-active").textContent = summary.inProgress;
    document.querySelector("#summary-consolidate").textContent = summary.consolidate;
    document.querySelector("#summary-total").textContent = summary.total;
  }

  function renderCard(item, recommended) {
    const status = Dashboard.pathwayStatus(item.state, item.config);
    const progress = Dashboard.pathwayProgress(item.state, item.config);
    const masteryCase = item.config.cases.find((caseDef) => caseDef.phase === "mastery");
    const href = `/static/pathway.html?id=${encodeURIComponent(item.config.id)}`;
    const recommendedBadge = recommended ? `<span class="recommended-badge">Recommandé</span>` : "";

    return `
      <article class="pathway-card accent-${escapeHtml(item.catalog.accent)} ${recommended ? "recommended" : ""}">
        <div class="card-topline">
          <div class="pathway-icon">${escapeHtml(item.catalog.icon)}</div>
          <div class="card-badges">
            ${recommendedBadge}
            <span class="status-badge status-${status.code}">${escapeHtml(status.label)}</span>
          </div>
        </div>
        <div class="card-copy">
          <span class="card-eyebrow">${escapeHtml(item.catalog.eyebrow)} · ${escapeHtml(item.catalog.level)}</span>
          <h3>${escapeHtml(item.config.title)}</h3>
          <p>${escapeHtml(item.config.subtitle)}</p>
        </div>
        <div class="card-meta">
          <span>${item.config.cases.length} ECG</span>
          <span>~${item.config.estimated_minutes} min</span>
          <span>${masteryCase ? "Test autonome" : "Pratique guidée"}</span>
        </div>
        <div class="card-progress">
          <div><span>Progression</span><strong>${progress.done} / ${progress.total}</strong></div>
          <div class="progress-track" role="progressbar" aria-label="Progression — ${escapeHtml(item.config.title)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${progress.percent}"><div style="width:${progress.percent}%"></div></div>
        </div>
        <a class="card-action" href="${href}"><span>${escapeHtml(status.cta)}</span><b>→</b></a>
      </article>`;
  }

  async function init() {
    const grid = document.querySelector("#pathway-grid");
    if (!Dashboard) {
      grid.innerHTML = `<div class="catalog-error">Le module de progression n’a pas été chargé.</div>`;
      return;
    }
    try {
      const catalog = await fetchJson(CATALOG_URL);
      if (catalog.schema_version !== 1) throw new Error("Version de catalogue non prise en charge.");
      const items = await Promise.all((catalog.pathways || []).map(async (entry) => {
        const config = await fetchJson(entry.config_url);
        if (config.id !== entry.id || config.schema_version !== 1) throw new Error(`Configuration incohérente : ${entry.id}`);
        return { catalog: entry, config, state: loadState(entry.id) };
      }));
      const recommended = Dashboard.recommendedIndex(items);
      renderSummary(items);
      grid.innerHTML = items.map((item, index) => renderCard(item, index === recommended)).join("");
    } catch (error) {
      grid.innerHTML = `<div class="catalog-error"><strong>Impossible de charger les parcours.</strong><span>${escapeHtml(error.message)}</span></div>`;
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
