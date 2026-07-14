(function () {
  "use strict";
  const Core = window.EduEcgCore;
  const Store = window.EduEcgStore;
  const app = document.querySelector("#app");
  let state = Store.load(window.localStorage);
  let course = null;
  let moduleData = null;
  let currentAnswer = null;

  const phaseLabels = {
    prime: "Observer", probe: "Se positionner", point: "Comprendre",
    attach: "Relier", strengthen: "Consolider", test: "Test autonome",
    review: "Bilan", optional_extension: "Pour aller plus loin",
  };

  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>'"]/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
    })[char]);
  }

  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function persist() { Store.save(window.localStorage, state); }
  function moduleRecord(id) { return state.modules[id] || { activities: {} }; }

  function latestAnswer(record) {
    if (record?.finalAnswer) return clone(record.finalAnswer);
    if (record && record.revisions && record.revisions.length) return clone(record.revisions[record.revisions.length - 1].answer);
    return record && record.initialAnswer ? clone(record.initialAnswer) : null;
  }

  function moduleProgress(summary) {
    const records = moduleRecord(summary.id).activities || {};
    const done = Object.values(records).filter((item) => item.completedAt).length;
    return { done, percent: Math.round((done / summary.activity_count) * 100) };
  }

  function renderHome() {
    moduleData = null;
    state.activeModuleId = null;
    persist();
    app.innerHTML = `
      <section class="hero">
        <div class="hero-copy">
          <span class="eyebrow">Parcours d’introduction</span>
          <h1>Voir le signal.<br><em>Comprendre le regard.</em></h1>
          <p>Un apprentissage actif pour acquérir les réflexes techniques qui précèdent toute interprétation ECG : décider, expliquer, puis vérifier.</p>
        </div>
        <aside class="hero-map" aria-label="Boucle pédagogique">
          <div>
            <h2>Une boucle courte et explicite</h2>
            <div class="learning-loop">
              <div class="loop-step active"><b>1</b><span>Répondre sans aide</span></div>
              <div class="loop-step"><b>2</b><span>Estimer sa confiance</span></div>
              <div class="loop-step"><b>3</b><span>Recevoir un indice gradué</span></div>
              <div class="loop-step"><b>4</b><span>Consolider puis tester</span></div>
            </div>
          </div>
          <p class="privacy-note">Votre première réponse et votre progression restent dans ce navigateur. Aucun score n’est calculé par une IA.</p>
        </aside>
      </section>
      <div class="section-heading">
        <div><span class="eyebrow">Choisir un point de départ</span><h2>Modules disponibles</h2></div>
        <p>${escapeHtml(course.available_modules.length)} prototype${course.available_modules.length > 1 ? "s" : ""}</p>
      </div>
      <section class="module-grid">
        ${course.available_modules.map((item) => {
          const progress = moduleProgress(item);
          const isPartial = item.implementation_status === "partial";
          return `<article class="module-card">
            <div class="module-meta"><span class="module-number">${escapeHtml(item.id)}</span><span class="module-status">${isPartial ? "Extrait" : "Prototype complet"}</span></div>
            <h3>${escapeHtml(item.title)}</h3>
            <p>${escapeHtml(item.terminal_objective)}</p>
            <div class="module-footer">
              <div class="module-progress" aria-label="${progress.percent}% terminé"><i style="width:${progress.percent}%"></i></div>
              <button class="primary-button module-start" data-module="${escapeHtml(item.id)}">${progress.done ? "Continuer" : "Commencer"}</button>
            </div>
          </article>`;
        }).join("")}
      </section>`;
    app.querySelectorAll(".module-start").forEach((button) => button.addEventListener("click", () => startModule(button.dataset.module)));
  }

  async function startModule(moduleId) {
    app.innerHTML = `<section class="loading-card"><span class="loader"></span><p>Préparation du module…</p></section>`;
    const response = await fetch(`/api/edu-ecg/modules/${encodeURIComponent(moduleId)}`);
    if (!response.ok) throw new Error("Module indisponible.");
    moduleData = await response.json();
    state.activeModuleId = moduleId;
    const records = moduleRecord(moduleId).activities || {};
    const firstPending = moduleData.activities.findIndex((activity) => !records[activity.id]?.completedAt);
    state.activeIndex = firstPending < 0 ? 0 : firstPending;
    Store.event(state, "module_started", { moduleId });
    persist();
    renderActivity();
  }

  function choiceOptions(options, name, selected, multiple) {
    return (options || []).map((option, index) => {
      const value = Core.optionValue(option, index);
      const label = typeof option === "object" && option !== null ? option.label : option;
      const checked = multiple ? (selected || []).includes(value) : selected === value;
      return `<label class="${multiple ? "check-label" : "choice-label"}"><input type="${multiple ? "checkbox" : "radio"}" name="${escapeHtml(name)}" value="${escapeHtml(value)}" ${checked ? "checked" : ""}><span>${escapeHtml(label)}</span></label>`;
    }).join("");
  }

  function renderSimpleResponse(activity, answer, prefix) {
    const response = activity.response || {};
    const name = prefix || "answer";
    const effectiveType = activity.activity_type === "image_comparison" ? (response.type || "single_choice") : activity.activity_type;
    if (effectiveType === "single_choice_per_image") {
      return (activity.assets || []).map((_asset, index) => `<fieldset><legend>Image ${index + 1}</legend>${choiceOptions(response.options, `${name}-image-${index}`, answer.choices?.[index] || "", false)}</fieldset>`).join("");
    }
    if ((response.cause_options || []).length && (response.action_options || []).length) {
      return `<fieldset><legend>Cause probable</legend>${choiceOptions(response.cause_options, `${name}-cause`, answer.cause || "", false)}</fieldset><fieldset><legend>Action corrective</legend>${choiceOptions(response.action_options, `${name}-action`, answer.action || "", false)}</fieldset>`;
    }
    if (Array.isArray(response.cases)) {
      return response.cases.map((item, index) => `<fieldset><legend>${escapeHtml(item.case || `Cas ${index + 1}`)}</legend>${choiceOptions(item.options, `${name}-case-${index}`, answer.cases?.[index] || "", false)}</fieldset>`).join("");
    }
    if (["single_choice", "multiple_choice"].includes(effectiveType) && !(response.options || []).length) {
      return `<div class="draft-notice"><span>◈</span><span>Les choix de cet écran ne sont pas encore spécifiés. Votre réponse est conservée sans notation automatique.</span></div><label class="field-label">Votre analyse<textarea name="${escapeHtml(name)}-note" placeholder="Décrivez les éléments que vous avez repérés…">${escapeHtml(answer.text || "")}</textarea></label>`;
    }
    if (effectiveType === "multiple_choice") return choiceOptions(response.options, name, answer.choices || [], true);
    if (effectiveType === "short_answer") return `<label class="field-label">Votre réponse<textarea name="${escapeHtml(name)}" placeholder="Formulez votre raisonnement…">${escapeHtml(answer.text || "")}</textarea></label>`;
    if (effectiveType === "single_choice" && Number(response.cases) > 1) {
      return Array.from({ length: Number(response.cases) }, (_, index) => `<fieldset><legend>Cas ${index + 1}</legend>${choiceOptions(response.options, `${name}-case-${index}`, answer.choices?.[index] || "", false)}</fieldset>`).join("");
    }
    return choiceOptions(response.options, name, answer.choice || "", false) + (response.secondary_prompt ? `
      <label class="field-label">${escapeHtml(response.secondary_prompt)}
        <select name="${escapeHtml(name)}-secondary"><option value="">Choisir…</option>${(response.secondary_options || []).map((item) => `<option ${answer.secondary === item ? "selected" : ""}>${escapeHtml(item)}</option>`).join("")}</select>
      </label>` : "");
  }

  function renderTask(task, answer, prefix) {
    if (task.type === "single_choice" && Array.isArray(task.options) && task.options.length) {
      return `<fieldset><legend>${escapeHtml(task.label || task.prompt || task.id)}</legend>${choiceOptions(task.options, prefix, answer.choice || "", false)}</fieldset>`;
    }
    if (task.type === "short_answer") return `<label class="field-label">${escapeHtml(task.label || task.prompt || task.id)}<textarea name="${escapeHtml(prefix)}">${escapeHtml(answer.text || "")}</textarea></label>`;
    return `<section class="fallback-response"><div class="draft-notice"><span>◈</span><span>Sous-tâche « ${escapeHtml(task.type)} » : le contenu interactif ou son corrigé reste à valider. Votre réponse est conservée sans notation automatique.</span></div><label class="field-label">${escapeHtml(task.label || task.prompt || task.id)}<textarea name="${escapeHtml(prefix)}" placeholder="Décrivez votre réponse…">${escapeHtml(answer.text || "")}</textarea></label></section>`;
  }

  function responseMarkup(activity, answer) {
    const response = activity.response || {};
    switch (activity.activity_type) {
      case "single_choice": case "multiple_choice": case "short_answer": case "image_comparison":
        return renderSimpleResponse(activity, answer);
      case "card_sorting":
        return `<div class="card-grid">${(response.cards || []).map((card) => `<label class="sort-card"><b>${escapeHtml(card.label)}</b><select name="card-${escapeHtml(card.id)}"><option value="">À classer…</option>${(response.categories || []).map((category) => `<option value="${escapeHtml(category)}" ${answer.assignments?.[card.id] === category ? "selected" : ""}>${escapeHtml(category)}</option>`).join("")}</select></label>`).join("")}</div>`;
      case "ordering_cards": {
        const cards = response.cards || [];
        if (!cards.length) return `<div class="draft-notice"><span>◈</span><span>Les cartes ou images de cette activité sont encore réservées. Votre réponse est conservée sans notation automatique.</span></div><label class="field-label">Votre proposition<textarea name="ordering-note" placeholder="Décrivez l’ordre que vous proposeriez…">${escapeHtml(answer.text || "")}</textarea></label>`;
        const order = answer.order?.length ? answer.order : cards.map((card) => card.id);
        const byId = Object.fromEntries(cards.map((card) => [card.id, card]));
        return `<div class="order-list">${order.map((id, index) => { const label = byId[id]?.label || id; return `<div class="order-item"><span class="order-number">${index + 1}</span><span>${escapeHtml(label)}</span><span class="order-buttons"><button type="button" data-move="${index}" data-direction="-1" aria-label="Monter ${escapeHtml(label)}" ${index === 0 ? "disabled" : ""}>↑</button><button type="button" data-move="${index}" data-direction="1" aria-label="Descendre ${escapeHtml(label)}" ${index === order.length - 1 ? "disabled" : ""}>↓</button></span></div>`; }).join("")}</div>`;
      }
      case "matching_pairs":
        return `<div class="answer-form">${(response.left_items || []).map((left) => `<label class="field-label">${escapeHtml(left)}<select name="pair-${escapeHtml(left)}"><option value="">Associer à…</option>${(response.right_items || []).map((right) => `<option ${answer.pairs?.[left] === right ? "selected" : ""}>${escapeHtml(right)}</option>`).join("")}</select></label>`).join("")}</div>`;
      case "image_hotspot_labeling": {
        const targets = Array.isArray(response.targets) ? response.targets : [response.target].filter(Boolean);
        return `<div class="answer-form">${targets.map((target, index) => { const id = typeof target === "object" ? target.id : String(target || index); const label = typeof target === "object" ? target.label : target; return `<label class="field-label">Repère : ${escapeHtml(label)}<input type="text" name="hotspot-${escapeHtml(id)}" value="${escapeHtml(answer.labels?.[id] || "")}" placeholder="Votre annotation"></label>`; }).join("")}</div>`;
      }
      case "sequence_checklist": {
        const items = response.checklist || [];
        if (response.free_checklist || response.mode === "free_checklist") return `<label class="field-label">Votre checklist<textarea name="free-sequence" placeholder="Un contrôle par ligne…">${escapeHtml(answer.text || "")}</textarea></label>`;
        return items.map((item) => `<label class="check-label"><input type="checkbox" name="checklist" value="${escapeHtml(item)}" ${(answer.checked || []).includes(item) ? "checked" : ""}><span>${escapeHtml(item)}</span></label>`).join("");
      }
      case "integrated_assessment":
        if (Array.isArray(response.tasks_per_case) && (activity.assets || []).length) {
          return (activity.assets || []).map((_asset, caseIndex) => `<fieldset class="case-response"><legend>Cas ${caseIndex + 1}</legend>${response.tasks_per_case.map((task) => `<label class="field-label">${escapeHtml(task)}<textarea name="integrated-case-${caseIndex}-${escapeHtml(task)}">${escapeHtml(answer.cases?.[caseIndex]?.[task] || "")}</textarea></label>`).join("")}</fieldset>`).join("");
        }
        if (!Array.isArray(response.tasks) || response.tasks.some((task) => typeof task !== "object")) return `<div class="draft-notice">La structure du test est réservée, mais ses sous-tâches ne sont pas encore spécifiées. Le test restera non évalué.</div><label class="field-label">Votre réponse<textarea name="integrated-note">${escapeHtml(answer.text || "")}</textarea></label>`;
        return response.tasks.map((task) => renderTask(task, answer.tasks?.[task.id] || {}, `task-${task.id}`)).join("");
      case "micro_lesson": {
        const explanation = activity.explanation || {};
        const sections = explanation.sections || (explanation.text ? [{ title: "À retenir", text: explanation.text }] : []);
        return `<div class="lesson">${sections.map((section) => `<article class="lesson-section"><h3>${escapeHtml(section.title)}</h3><p>${escapeHtml(section.text)}</p></article>`).join("")}</div>`;
      }
      default: return `<div class="draft-notice">Type d’activité non rendu.</div>`;
    }
  }

  function assetMarkup(activity) {
    if (!activity.assets || !activity.assets.length) return "";
    return `<div class="asset-grid">${activity.assets.map((asset) => `<figure class="asset-frame"><button type="button" class="asset-zoom" data-zoom-src="/api/edu-ecg/assets/${escapeHtml(asset)}" data-zoom-alt="${escapeHtml(`${activity.title} — ${activity.prompt}`)}" aria-label="Agrandir le support visuel : ${escapeHtml(activity.title)}"><img data-src="/api/edu-ecg/assets/${escapeHtml(asset)}" alt="${escapeHtml(`${activity.title}. ${activity.prompt}`)}"></button><div class="asset-placeholder hidden"><b>Visuel en attente de validation</b><small>Emplacement de développement : ${escapeHtml(asset)}. Aucun ECG médical n’a été généré pour le remplacer.</small></div></figure>`).join("")}</div>`;
  }

  function confidenceMarkup(activity, record) {
    if (!activity.collect_confidence) return "";
    const levels = [["faible", "Faible"], ["moyenne", "Moyenne"], ["forte", "Forte"]];
    return `<fieldset class="confidence"><legend>${record.locked ? "Confiance déclarée avec la première réponse" : "Avant la correction, quel est votre niveau de confiance ?"}</legend><div class="confidence-options">${levels.map(([value, label]) => `<label><input type="radio" name="confidence" value="${value}" ${record.confidence === value ? "checked" : ""} ${record.locked ? "disabled" : ""}>${label}</label>`).join("")}</div></fieldset>`;
  }

  function explanationText(explanation) {
    explanation ||= {};
    if (explanation.text) return explanation.text;
    return (explanation.sections || []).map((section) => `${section.title} — ${section.text}`).join(" ");
  }

  function feedbackMarkup(activity, record) {
    if (!record.result) return "";
    const result = record.result;
    const kind = !result.evaluated ? "pending" : result.correct ? "correct" : "wrong";
    const title = !result.evaluated ? "Réponse enregistrée — validation en attente" : result.correct ? "Réponse correcte" : "À consolider";
    const score = result.evaluated ? `<span class="score">${result.earned}/${result.possible} · ${result.percent}%</span> — ` : "";
    const explanation = explanationText(result.explanation);
    return `<section class="feedback feedback--${kind}" aria-live="polite"><h3>${title}</h3><p>${score}${escapeHtml(result.detail)}</p>${explanation ? `<p class="explanation">${escapeHtml(explanation)}</p>` : ""}${result.criticalErrors?.length ? `<p class="critical-note"><strong>Erreur critique détectée :</strong> ${escapeHtml(result.criticalErrors.join(", "))}. Le domaine concerné ne peut pas être validé.</p>` : ""}</section>`;
  }

  function hintMarkup(activity, record) {
    const hints = (record.hintsUsed || []).map((index) => activity.hints?.[index]).filter(Boolean);
    if (!hints.length) return "";
    return `<div class="hint-stack" aria-live="polite">${hints.map((hint, index) => `<div class="hint-box"><b>Indice ${index + 1}</b><br>${escapeHtml(hint)}</div>`).join("")}</div>`;
  }

  function renderRail(activity, index) {
    return `<aside class="course-rail"><div class="rail-card"><a href="#" class="rail-back">← Tous les modules</a><h2>${escapeHtml(moduleData.title)}</h2><p>${escapeHtml(moduleData.terminal_objective)}</p><div class="step-list">${moduleData.activities.map((item, itemIndex) => `<div class="step-dot ${itemIndex === index ? "active" : ""} ${moduleRecord(moduleData.id).activities?.[item.id]?.completedAt ? "done" : ""}"><i></i><span>${escapeHtml(phaseLabels[item.phase] || item.phase)}</span></div>`).join("")}</div></div><div class="rail-card"><span class="eyebrow">Règle du parcours</span><p>La première réponse est conservée. Les indices apparaissent seulement après son verrouillage et restent absents du test autonome.</p></div></aside>`;
  }

  function renderActivity(answerOverride) {
    const index = state.activeIndex || 0;
    const activity = moduleData.activities[index];
    const record = Store.activityRecord(state, moduleData.id, activity.id);
    if (!record.viewedAt) {
      record.viewedAt = new Date().toISOString();
      Store.event(state, "activity_viewed", Store.context(record, moduleData.id, activity.id, activity.competency_ids));
    }
    currentAnswer = answerOverride || latestAnswer(record) || {};
    if (activity.activity_type === "ordering_cards" && !currentAnswer.order) currentAnswer.order = (activity.response.cards || []).map((card) => card.id);
    persist();
    const isTest = activity.phase === "test";
    const hintsUsed = record.hintsUsed || [];
    const hintAvailable = record.locked && !record.result && !isTest && hintsUsed.length < (activity.hints || []).length;
    const maxSubmissions = Number(activity.attempt_policy?.max_submissions_before_explanation || 1);
    const submissions = record.initialAnswer === null ? 0 : 1 + (record.revisions || []).length;
    const canSubmitRevision = record.locked && !record.result && !isTest
      && activity.attempt_policy?.allow_revision_after_hint !== false
      && hintsUsed.length > 0 && submissions < maxSubmissions;
    const showSubmit = !record.locked || canSubmitRevision;
    const submitLabel = activity.activity_type === "micro_lesson"
      ? "J’ai compris"
      : record.locked ? "Valider ma révision" : "Valider ma réponse";
    const previousAllowed = index > 0 && activity.display?.allow_back_navigation !== false;
    app.innerHTML = `<div class="course-layout">${renderRail(activity, index)}<article class="activity-panel"><header class="activity-top"><div class="activity-topline"><span class="phase-pill">${escapeHtml(phaseLabels[activity.phase] || activity.phase)}</span><span>Activité ${index + 1} / ${moduleData.activities.length}</span></div><div class="activity-progress"><i style="width:${((index + 1) / moduleData.activities.length) * 100}%"></i></div></header><div class="activity-body"><span class="eyebrow">${escapeHtml(activity.competency_ids.join(" · "))}</span><h1>${escapeHtml(activity.title)}</h1><p class="prompt">${escapeHtml(activity.prompt)}</p>${activity.content_status !== "approved" ? `<div class="draft-notice"><span>◈</span><span>Contenu « ${escapeHtml(activity.content_status)} » : à relire avant un usage pédagogique validé.</span></div>` : ""}${assetMarkup(activity)}<form id="answer-form" class="answer-form">${responseMarkup(activity, currentAnswer)}${confidenceMarkup(activity, record)}${hintMarkup(activity, record)}<div class="activity-actions">${previousAllowed ? `<button id="previous-activity" type="button" class="secondary-button">Précédent</button>` : ""}${showSubmit ? `<button type="submit" class="primary-button">${submitLabel}</button>` : ""}${hintAvailable ? `<button id="show-hint" type="button" class="hint-button">Voir l’indice ${hintsUsed.length + 1}</button>` : ""}${record.completedAt ? `<button id="next-activity" type="button" class="secondary-button">${index === moduleData.activities.length - 1 ? "Voir mon bilan" : "Continuer"}</button>` : ""}<span id="activity-error" class="activity-error" role="alert"></span></div></form>${feedbackMarkup(activity, record)}</div></article></div>`;
    wireActivity(activity, record);
  }

  function collectTask(form, task) {
    const prefix = `task-${task.id}`;
    if (task.type === "short_answer" || task.type !== "single_choice" || !task.options?.length) {
      return { text: form.elements[prefix]?.value || "" };
    }
    return { choice: form.querySelector(`[name="${CSS.escape(prefix)}"]:checked`)?.value || "" };
  }

  function collectAnswer(activity, form) {
    const response = activity.response || {};
    const effectiveType = activity.activity_type === "image_comparison" ? (response.type || "single_choice") : activity.activity_type;
    if (effectiveType === "single_choice_per_image") {
      return { choices: (activity.assets || []).map((_asset, index) => form.querySelector(`[name="answer-image-${index}"]:checked`)?.value || "") };
    }
    if ((response.cause_options || []).length && (response.action_options || []).length) {
      return {
        cause: form.querySelector('[name="answer-cause"]:checked')?.value || "",
        action: form.querySelector('[name="answer-action"]:checked')?.value || "",
      };
    }
    if (Array.isArray(response.cases)) {
      return { cases: response.cases.map((_item, index) => form.querySelector(`[name="answer-case-${index}"]:checked`)?.value || "") };
    }
    if (["single_choice", "multiple_choice"].includes(effectiveType) && !(response.options || []).length) {
      return { text: form.elements["answer-note"]?.value || "" };
    }
    if (effectiveType === "multiple_choice") return { choices: [...form.querySelectorAll('[name="answer"]:checked')].map((input) => input.value) };
    if (effectiveType === "short_answer") return { text: form.elements.answer?.value || "" };
    if (effectiveType === "single_choice" && Number(response.cases) > 1) {
      return { choices: Array.from({ length: Number(response.cases) }, (_, index) => form.querySelector(`[name="answer-case-${index}"]:checked`)?.value || "") };
    }
    switch (activity.activity_type) {
      case "single_choice": case "image_comparison": return { choice: form.querySelector('[name="answer"]:checked')?.value || "", secondary: form.elements["answer-secondary"]?.value || "" };
      case "card_sorting": return { assignments: Object.fromEntries((response.cards || []).map((card) => [card.id, form.elements[`card-${card.id}`]?.value || ""])) };
      case "ordering_cards": return (response.cards || []).length
        ? { order: clone(currentAnswer.order || []) }
        : { text: form.elements["ordering-note"]?.value || "" };
      case "matching_pairs": return { pairs: Object.fromEntries((response.left_items || []).map((left) => [left, form.elements[`pair-${left}`]?.value || ""])) };
      case "image_hotspot_labeling": { const targets = Array.isArray(response.targets) ? response.targets : [response.target].filter(Boolean); return { labels: Object.fromEntries(targets.map((target, index) => { const id = typeof target === "object" ? target.id : String(target || index); return [id, form.elements[`hotspot-${id}`]?.value || ""]; })) }; }
      case "sequence_checklist": return response.free_checklist || response.mode === "free_checklist" ? { text: form.elements["free-sequence"]?.value || "" } : { checked: [...form.querySelectorAll('[name="checklist"]:checked')].map((input) => input.value) };
      case "integrated_assessment": {
        if (Array.isArray(response.tasks_per_case) && (activity.assets || []).length) {
          return { cases: (activity.assets || []).map((_asset, caseIndex) => Object.fromEntries(response.tasks_per_case.map((task) => [task, form.elements[`integrated-case-${caseIndex}-${task}`]?.value || ""]))) };
        }
        return Array.isArray(response.tasks) && response.tasks.every((task) => typeof task === "object") ? { tasks: Object.fromEntries(response.tasks.map((task) => [task.id, collectTask(form, task)])) } : { text: form.elements["integrated-note"]?.value || "" };
      }
      case "micro_lesson": return { continued: true };
      default: return {};
    }
  }

  async function evaluateAnswer(activity, answer) {
    const response = await fetch(
      `/api/edu-ecg/modules/${encodeURIComponent(moduleData.id)}/activities/${encodeURIComponent(activity.id)}/evaluate`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answer }),
      },
    );
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || "La correction n’est pas disponible.");
    return { ...payload.result, explanation: payload.explanation || {} };
  }

  function wireActivity(activity, record) {
    app.querySelector(".rail-back").addEventListener("click", (event) => { event.preventDefault(); renderHome(); });
    app.querySelectorAll("[data-move]").forEach((button) => button.addEventListener("click", () => {
      Store.recordFirstAction(state, moduleData.id, activity.id, activity.competency_ids);
      const index = Number(button.dataset.move); const target = index + Number(button.dataset.direction);
      const order = currentAnswer.order;
      if (!Array.isArray(order) || target < 0 || target >= order.length) return;
      [order[index], order[target]] = [order[target], order[index]];
      persist();
      renderActivity(currentAnswer);
    }));
    app.querySelectorAll(".asset-frame img").forEach((image) => {
      image.addEventListener("error", () => {
        image.parentElement.classList.add("hidden"); image.parentElement.nextElementSibling.classList.remove("hidden");
      });
      image.src = image.dataset.src;
    });
    app.querySelectorAll(".asset-zoom").forEach((button) => button.addEventListener("click", () => {
      const dialog = document.querySelector("#edu-image-dialog");
      const image = dialog.querySelector("img");
      image.src = button.dataset.zoomSrc;
      image.alt = button.dataset.zoomAlt;
      dialog.querySelector("p").textContent = button.dataset.zoomAlt;
      dialog.showModal();
    }));
    app.querySelector("#previous-activity")?.addEventListener("click", () => {
      state.activeIndex -= 1; persist(); renderActivity(); window.scrollTo({ top: 0, behavior: "smooth" });
    });
    app.querySelector("#show-hint")?.addEventListener("click", () => {
      Store.useHint(state, moduleData.id, activity.id, record.hintsUsed.length, activity.competency_ids);
      persist(); renderActivity(currentAnswer);
    });
    app.querySelector("#next-activity")?.addEventListener("click", () => {
      if (state.activeIndex >= moduleData.activities.length - 1) renderResults();
      else { state.activeIndex += 1; persist(); renderActivity(); window.scrollTo({ top: 0, behavior: "smooth" }); }
    });
    const form = app.querySelector("#answer-form");
    const firstAction = () => {
      Store.recordFirstAction(state, moduleData.id, activity.id, activity.competency_ids);
      persist();
    };
    form.addEventListener("input", firstAction, { once: true });
    form.addEventListener("change", firstAction, { once: true });
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const answer = collectAnswer(activity, event.currentTarget);
      const error = app.querySelector("#activity-error");
      if (!Core.isComplete(activity, answer)) { error.textContent = "Complétez votre réponse avant de continuer."; return; }
      const confidenceInput = event.currentTarget.querySelector('[name="confidence"]:checked');
      if (activity.collect_confidence && !confidenceInput && record.confidence == null) { error.textContent = "Indiquez votre niveau de confiance."; return; }
      const confidence = confidenceInput ? confidenceInput.value : record.confidence;
      const initialSubmission = !record.locked;
      Store.recordFirstAction(state, moduleData.id, activity.id, activity.competency_ids);
      if (initialSubmission) {
        Store.lockInitial(state, moduleData.id, activity.id, answer, confidence, activity.competency_ids);
        currentAnswer = answer;
        persist();
        const stagedRevision = activity.phase !== "test"
          && activity.attempt_policy?.allow_revision_after_hint !== false
          && (activity.hints || []).length > 0;
        if (stagedRevision) { renderActivity(answer); return; }
      }
      const submit = event.currentTarget.querySelector('[type="submit"]');
      if (submit) submit.disabled = true;
      error.textContent = "";
      try {
        const evaluation = await evaluateAnswer(activity, answer);
        Store.setResult(state, moduleData.id, activity.id, answer, evaluation, activity.competency_ids);
        currentAnswer = answer; persist(); renderActivity(answer);
      } catch (evaluationError) {
        if (submit) submit.disabled = false;
        error.textContent = evaluationError.message;
      }
    });
  }

  function renderResults() {
    const records = moduleRecord(moduleData.id).activities || {};
    const completed = moduleData.activities.map((activity) => records[activity.id]).filter((record) => record?.completedAt);
    const evaluated = completed.filter((record) => record.result?.evaluated);
    const average = evaluated.length ? Math.round(evaluated.reduce((sum, record) => sum + record.result.percent, 0) / evaluated.length) : null;
    const hints = completed.reduce((sum, record) => sum + (record.hintsUsed || []).length, 0);
    const criticalErrors = completed.flatMap((record) => record.result?.criticalErrors || []);
    const domains = Core.domainResults(moduleData, records);
    const hasDomainMap = Object.keys(moduleData.domain_competency_ids || {}).length > 0;
    const wasCompleted = state.modules[moduleData.id].completed;
    state.modules[moduleData.id].completed = completed.length === moduleData.activities.length;
    if (!wasCompleted && state.modules[moduleData.id].completed) {
      Store.event(state, "module_completed", { moduleId: moduleData.id }, {
        evaluated_activities: evaluated.length,
        average_percent: average,
        critical_error_count: criticalErrors.length,
      });
    }
    if (!state.completedAt && course.available_modules.every((item) => state.modules[item.id]?.completed)) {
      state.completedAt = new Date().toISOString();
      Store.event(state, "course_completed", {}, { available_modules: course.available_modules.length });
    }
    persist();
    app.innerHTML = `<section class="result-panel"><span class="eyebrow">Bilan du module ${escapeHtml(moduleData.id)}</span><h1>Première étape enregistrée.</h1><p>Le bilan distingue les réponses évaluables des contenus encore en validation. Une activité sans corrigé explicite ne contribue jamais au score.</p><div class="result-stats"><div class="result-stat"><b>${completed.length}/${moduleData.activities.length}</b><span>activités terminées</span></div><div class="result-stat"><b>${average == null ? "—" : `${average}%`}</b><span>moyenne évaluée</span></div><div class="result-stat"><b>${hints}</b><span>indices consultés</span></div></div>${criticalErrors.length ? `<div class="critical-summary"><strong>${criticalErrors.length} erreur${criticalErrors.length > 1 ? "s" : ""} critique${criticalErrors.length > 1 ? "s" : ""}</strong><span>Le statut « acquis » est bloqué par cette erreur.</span></div>` : ""}<span class="eyebrow">Résultats par domaine</span><div class="domain-list">${domains.map((domain) => `<div class="domain-row"><span>${escapeHtml(domain.label)}</span><span class="domain-status domain-status--${domain.status === "acquis" ? "acquired" : domain.status === "à consolider" ? "review" : "pending"}">${escapeHtml(domain.status)}${domain.percent == null ? "" : ` · ${domain.percent}%`}</span></div>`).join("")}</div><div class="draft-notice"><span>◈</span><span>${hasDomainMap ? "La maîtrise par domaine repose sur le test autonome. Tant que son corrigé explicite n’est pas validé, le statut reste « non évalué »." : "Aucune correspondance entre domaines et compétences n’est encore fournie pour ce module. Aucun rattachement médical n’est déduit automatiquement."}</span></div><div class="activity-actions"><button id="back-home" class="primary-button">Retour aux modules</button><button id="retry-module" class="secondary-button">Revoir le module</button></div></section>`;
    app.querySelector("#back-home").addEventListener("click", renderHome);
    app.querySelector("#retry-module").addEventListener("click", () => { state.activeIndex = 0; persist(); renderActivity(); });
  }

  function fatal(error) {
    app.innerHTML = `<section class="fatal"><span class="eyebrow">Edu-ECG indisponible</span><h1>Le parcours n’a pas pu être chargé.</h1><p>${escapeHtml(error.message || error)}</p><a class="text-button" href="/">Revenir aux 75 cas</a></section>`;
  }

  document.querySelector("#reset-progress").addEventListener("click", () => {
    if (!window.confirm("Effacer la progression Edu-ECG enregistrée sur cet appareil ?")) return;
    window.localStorage.removeItem(Store.KEY);
    window.localStorage.removeItem(Store.LEGACY_KEY);
    state = Store.fresh(course?.version); Store.startCourse(state); persist(); renderHome();
  });

  window.addEventListener("pagehide", () => {
    if (!state.startedAt || !course) return;
    const completed = course.available_modules.every((item) => state.modules[item.id]?.completed);
    if (!completed) {
      Store.event(state, "course_abandoned", {}, { active_module_id: state.activeModuleId });
      persist();
    }
  });

  fetch("/api/edu-ecg/course").then((response) => {
    if (!response.ok) throw new Error("Le parcours est désactivé.");
    return response.json();
  }).then((payload) => {
    course = payload;
    Store.configure(state, course.version);
    Store.startCourse(state);
    persist();
    renderHome();
  }).catch(fatal);
})();
