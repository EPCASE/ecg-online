/* pathways.js — tableau de progression des micro-parcours. */
(() => {
  "use strict";

  const CATALOG_URL = "/static/pathways.json";
  const Dashboard = window.ECGPathwayDashboard;
  let renderGeneration = 0;
  const RECOMMENDATION_COPY = {
    resume: {
      kicker: "À reprendre",
      message: "Continue là où tu t’es arrêté pour préserver la continuité du raisonnement.",
    },
    consolidate: {
      kicker: "À consolider",
      message: "Le test autonome reste fragile : une consolidation ciblée est disponible.",
    },
    fundamental: {
      kicker: "Prochaine compétence recommandée",
      message: "Commence par ce socle avant de combiner plusieurs branches du raisonnement ECG.",
    },
    "recommendations-met": {
      kicker: "Prochaine compétence recommandée",
      message: "Les repères conseillés en amont sont validés : tu peux passer à l’étape suivante.",
    },
    "open-choice": {
      kicker: "Parcours accessible",
      message: "Les prérequis sont conseillés, jamais bloquants : tu peux commencer ce parcours maintenant.",
    },
    review: {
      kicker: "Curriculum complété",
      message: "Les cinq tests autonomes sont réussis. Reviens sur le parcours intégratif pour entretenir la synthèse.",
    },
  };

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

  function pathwayName(items, pathwayId) {
    const item = items.find((candidate) => candidate.config.id === pathwayId);
    if (!item) return pathwayId;
    return item.catalog.competency_label || item.config.title;
  }

  function renderRecommendedAfter(item, items) {
    const guidance = Dashboard.recommendedAfterState(item, items);
    if (guidance.ids.length === 0) {
      return `<div class="card-guidance guidance-open"><span>✓</span>Accessible directement</div>`;
    }
    if (guidance.met) {
      return `<div class="card-guidance guidance-ready"><span>✓</span>Repères conseillés validés</div>`;
    }
    const missing = guidance.missing.map((id) => pathwayName(items, id)).join(" et ");
    return `<div class="card-guidance guidance-advised"><span>↗</span>Conseillé après : ${escapeHtml(missing)} · accès libre</div>`;
  }

  function renderCard(item, recommended, items) {
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
        ${renderRecommendedAfter(item, items)}
        <div class="card-progress">
          <div><span>Progression</span><strong>${progress.done} / ${progress.total}</strong></div>
          <div class="progress-track" role="progressbar" aria-label="Progression — ${escapeHtml(item.config.title)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${progress.percent}"><div style="width:${progress.percent}%"></div></div>
        </div>
        <a class="card-action" href="${href}"><span>${escapeHtml(status.cta)}</span><b>→</b></a>
      </article>`;
  }

  function renderRecommendation(items, recommendation) {
    const container = document.querySelector("#next-recommendation");
    if (!container) return;
    if (!recommendation || recommendation.index < 0 || !items[recommendation.index]) {
      container.innerHTML = `<div class="catalog-error">Aucune recommandation disponible.</div>`;
      return;
    }
    const item = items[recommendation.index];
    const copy = RECOMMENDATION_COPY[recommendation.reason] || RECOMMENDATION_COPY["open-choice"];
    const status = Dashboard.pathwayStatus(item.state, item.config);
    const href = `/static/pathway.html?id=${encodeURIComponent(item.config.id)}`;
    container.className = `next-recommendation accent-${escapeHtml(item.catalog.accent)}`;
    container.innerHTML = `
      <div class="next-recommendation-icon">${escapeHtml(item.catalog.icon)}</div>
      <div class="next-recommendation-copy">
        <span>${escapeHtml(copy.kicker)}</span>
        <h2>${escapeHtml(item.config.title)}</h2>
        <p>${escapeHtml(copy.message)}</p>
        <div class="next-recommendation-meta">
          <span>Niveau ${Dashboard.curriculumLevel(item)}</span>
          <span>${item.config.cases.length} ECG</span>
          <span>~${item.config.estimated_minutes} min</span>
        </div>
      </div>
      <a class="next-recommendation-action" href="${href}">${escapeHtml(status.cta)} <b>→</b></a>`;
  }

  function renderLevels(catalog, items, recommendation) {
    const container = document.querySelector("#pathway-grid");
    const definitions = Array.isArray(catalog.curriculum_levels) && catalog.curriculum_levels.length
      ? catalog.curriculum_levels
      : [{ id: 1, title: "Parcours", description: "Progression par compétences." }];
    const recommendedId = recommendation && recommendation.index >= 0
      ? items[recommendation.index].config.id
      : "";

    container.innerHTML = definitions.map((level) => {
      const levelItems = items.filter((item) => Dashboard.curriculumLevel(item) === Number(level.id));
      if (levelItems.length === 0) return "";
      return `
        <section class="curriculum-level" data-curriculum-level="${escapeHtml(level.id)}" aria-labelledby="curriculum-level-${level.id}">
          <div class="curriculum-level-heading">
            <div class="curriculum-level-number">${escapeHtml(level.id)}</div>
            <div>
              <span>Niveau ${escapeHtml(level.id)}</span>
              <h3 id="curriculum-level-${level.id}">${escapeHtml(level.title)}</h3>
              <p>${escapeHtml(level.description)}</p>
            </div>
          </div>
          <div class="pathway-grid">
            ${levelItems.map((item) => renderCard(item, item.config.id === recommendedId, items)).join("")}
          </div>
        </section>`;
    }).join("");
  }

  function renderProfile(items) {
    const container = document.querySelector("#competency-profile");
    if (!container) return;
    const profile = Dashboard.competencyProfile(items);
    const segments = profile.competencies.map((item) => (
      `<span class="profile-segment segment-${item.code}" aria-hidden="true"></span>`
    )).join("");
    container.innerHTML = `
      <div class="profile-overview">
        <div><strong>${profile.mastered}/${profile.total}</strong><span>compétences validées sans aide</span></div>
        <div class="profile-track" role="progressbar" aria-label="Compétences validées sans aide" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${profile.percent}">${segments}</div>
      </div>
      <div class="profile-list">
        ${profile.competencies.map((competency) => `
          <a class="competency-row" href="/static/pathway.html?id=${encodeURIComponent(competency.id)}">
            <span class="competency-marker marker-${competency.code}"></span>
            <span class="competency-copy"><strong>${escapeHtml(competency.label)}</strong><small>Niveau ${competency.curriculumLevel}</small></span>
            <span class="competency-status status-${competency.code}">${escapeHtml(competency.statusLabel)}</span>
            <b>→</b>
          </a>`).join("")}
      </div>`;
  }

  function renderError(container, error) {
    if (!container) return;
    container.innerHTML = `<div class="catalog-error"><strong>Impossible de charger les parcours.</strong><span>${escapeHtml(error.message)}</span></div>`;
  }

  async function init() {
    const generation = ++renderGeneration;
    const grid = document.querySelector("#pathway-grid");
    const recommendationContainer = document.querySelector("#next-recommendation");
    const profileContainer = document.querySelector("#competency-profile");
    if (!Dashboard) {
      const error = new Error("Le module de progression n’a pas été chargé.");
      renderError(grid, error);
      renderError(recommendationContainer, error);
      renderError(profileContainer, error);
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
      if (generation !== renderGeneration) return;
      const recommendation = Dashboard.recommendation(items);
      renderSummary(items);
      renderRecommendation(items, recommendation);
      renderLevels(catalog, items, recommendation);
      renderProfile(items);
    } catch (error) {
      if (generation !== renderGeneration) return;
      renderError(grid, error);
      renderError(recommendationContainer, error);
      renderError(profileContainer, error);
    }
  }

  document.addEventListener("DOMContentLoaded", init);
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) init();
  });
  window.addEventListener("storage", (event) => {
    if (event.key === null || (Dashboard && event.key.startsWith(Dashboard.STORAGE_PREFIX))) init();
  });
})();
