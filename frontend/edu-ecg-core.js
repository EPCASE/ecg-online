(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.EduEcgCore = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const SUPPORTED_TYPES = [
    "single_choice", "multiple_choice", "short_answer", "card_sorting",
    "ordering_cards", "matching_pairs", "image_comparison",
    "image_hotspot_labeling", "sequence_checklist", "integrated_assessment",
    "micro_lesson",
  ];

  function normalized(value) {
    return String(value == null ? "" : value)
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("fr").replace(/[^a-z0-9]+/g, " ").trim();
  }

  function equalSets(left, right) {
    const a = [...new Set(left || [])].map(String).sort();
    const b = [...new Set(right || [])].map(String).sort();
    return a.length === b.length && a.every((item, index) => item === b[index]);
  }

  function optionValue(option, index) {
    return typeof option === "object" && option !== null
      ? String(option.id == null ? option.label : option.id)
      : String(option == null ? index : option);
  }

  function choiceKey(activity) {
    const response = activity.response || {};
    const scoring = activity.scoring || {};
    const value = response.correct_option_id ?? response.correct ?? scoring.correct_option_id ?? scoring.correct;
    return value == null ? null : String(value);
  }

  function result(activity, evaluated, earned, possible, detail, criticalErrors) {
    return {
      activityId: activity.id,
      evaluated: Boolean(evaluated),
      correct: evaluated ? possible > 0 && earned === possible : null,
      earned: evaluated ? earned : null,
      possible: evaluated ? possible : null,
      percent: evaluated && possible ? Math.round((earned / possible) * 100) : null,
      detail: detail || (evaluated ? "Évaluation déterministe." : "Contenu à valider : aucun corrigé explicite n’est fourni."),
      criticalErrors: criticalErrors || [],
    };
  }

  function evaluateChoice(activity, answer) {
    const key = choiceKey(activity);
    if (key === null) return result(activity, false);
    const selected = String((answer || {}).choice ?? "");
    const possible = Number((activity.scoring || {}).points || (activity.scoring || {}).decision_points || 1);
    const criticalMap = (activity.scoring || {}).critical_error_options || {};
    const critical = criticalMap[selected]
      ? [criticalMap[selected]]
      : selected !== key && (activity.scoring || {}).critical_error
        ? [(activity.scoring || {}).critical_error]
        : [];
    return result(activity, true, selected === key ? possible : 0, possible, undefined, critical);
  }

  function evaluateMultiple(activity, answer) {
    const response = activity.response || {};
    const scoring = activity.scoring || {};
    const key = response.correct_option_ids || response.correct_options || scoring.correct_option_ids || scoring.correct_options;
    if (!Array.isArray(key)) return result(activity, false);
    const possible = Number(scoring.points || 1);
    return result(activity, true, equalSets((answer || {}).choices, key) ? possible : 0, possible);
  }

  function evaluateShort(activity, answer) {
    return result(activity, false, 0, 0, "Réponse enregistrée sans notation automatique.");
  }

  function evaluateCards(activity, answer) {
    const cards = (activity.response || {}).cards || [];
    if (!cards.length || cards.some((card) => card.category == null)) return result(activity, false);
    const assignments = (answer || {}).assignments || {};
    const earned = cards.filter((card) => assignments[card.id] === card.category).length;
    const criticalCards = new Set((activity.scoring || {}).critical_cards || []);
    const critical = cards
      .filter((card) => criticalCards.has(card.id) && assignments[card.id] !== card.category)
      .map((card) => `critical_card:${card.id}`);
    return result(activity, true, earned, cards.length, undefined, critical);
  }

  function evaluateOrder(activity, answer) {
    const response = activity.response || {};
    const key = response.correct_order;
    if (!Array.isArray(key) || !key.length) return result(activity, false);
    const order = (answer || {}).order || [];
    const earned = key.filter((item, index) => String(order[index]) === String(item)).length;
    const critical = earned !== key.length && (activity.scoring || {}).critical_error
      ? [(activity.scoring || {}).critical_error] : [];
    return result(activity, true, earned, key.length, undefined, critical);
  }

  function evaluatePairs(activity, answer) {
    const correct = (activity.response || {}).correct_pairs;
    if (!Array.isArray(correct) || !correct.length) return result(activity, false);
    const pairs = (answer || {}).pairs || {};
    const earned = correct.filter(([left, right]) => pairs[left] === right).length;
    const criticalPair = (activity.scoring || {}).critical_pair;
    const critical = Array.isArray(criticalPair) && pairs[criticalPair[0]] !== criticalPair[1]
      ? [`critical_pair:${criticalPair[0]}`] : [];
    return result(activity, true, earned, correct.length, undefined, critical);
  }

  function hotspotKey(activity) {
    const response = activity.response || {};
    if (response.correct_labels && typeof response.correct_labels === "object") return response.correct_labels;
    const targets = Array.isArray(response.targets) ? response.targets : [];
    if (targets.length && targets.every((target) => target && typeof target === "object" && (target.correct_label || target.answer))) {
      return Object.fromEntries(targets.map((target) => [target.id, target.correct_label || target.answer]));
    }
    return null;
  }

  function evaluateHotspots(activity, answer) {
    const key = hotspotKey(activity);
    if (!key) return result(activity, false);
    const labels = (answer || {}).labels || {};
    const entries = Object.entries(key);
    const earned = entries.filter(([id, label]) => labels[id] === label).length;
    const critical = earned !== entries.length && (activity.scoring || {}).critical_error
      ? [(activity.scoring || {}).critical_error] : [];
    return result(activity, true, earned, entries.length, undefined, critical);
  }

  function evaluateChecklist(activity, answer) {
    const response = activity.response || {};
    const expected = response.correct_order || response.checklist;
    if (!Array.isArray(expected) || response.free_checklist) return result(activity, false);
    const checked = (answer || {}).checked || [];
    return result(activity, true, equalSets(checked, expected) ? expected.length : expected.filter((item) => checked.includes(item)).length, expected.length);
  }

  function taskAsActivity(parent, task) {
    return {
      id: `${parent.id}:${task.id || "task"}`,
      activity_type: task.type,
      response: task,
      scoring: task.scoring || {},
    };
  }

  function hasStructuredResponse(activity) {
    const response = activity.response || {};
    switch (activity.activity_type) {
      case "single_choice": case "multiple_choice": case "image_comparison":
        if (Array.isArray(response.cause_options) && response.cause_options.length
          && Array.isArray(response.action_options) && response.action_options.length) return true;
        if (Array.isArray(response.cases)) {
          return response.cases.length > 0 && response.cases.every((item) => Array.isArray(item.options) && item.options.length > 0);
        }
        return Array.isArray(response.options) && response.options.length > 0;
      case "short_answer": return true;
      case "card_sorting":
        return Array.isArray(response.cards) && response.cards.length > 0
          && Array.isArray(response.categories) && response.categories.length > 0;
      case "ordering_cards": return Array.isArray(response.cards) && response.cards.length > 0;
      case "matching_pairs":
        return Array.isArray(response.left_items) && response.left_items.length > 0
          && Array.isArray(response.right_items) && response.right_items.length > 0;
      case "image_hotspot_labeling":
        return (Array.isArray(response.targets) && response.targets.length > 0) || Boolean(response.target);
      case "sequence_checklist":
        return response.free_checklist || response.mode === "free_checklist"
          || (Array.isArray(response.checklist) && response.checklist.length > 0);
      default: return false;
    }
  }

  function evaluateIntegrated(activity, answer) {
    const tasks = (activity.response || {}).tasks;
    if (!Array.isArray(tasks) || !tasks.length || tasks.some((task) => typeof task !== "object")) return result(activity, false);
    const answers = (answer || {}).tasks || {};
    const evaluations = tasks.map((task) => evaluate(taskAsActivity(activity, task), answers[task.id] || {}));
    if (evaluations.some((item) => !item.evaluated)) return result(activity, false);
    const earned = evaluations.reduce((sum, item) => sum + item.earned, 0);
    const possible = evaluations.reduce((sum, item) => sum + item.possible, 0);
    const critical = evaluations.flatMap((item) => item.criticalErrors);
    return result(activity, true, earned, possible, undefined, critical);
  }

  function evaluate(activity, answer) {
    switch (activity.activity_type) {
      case "single_choice": return evaluateChoice(activity, answer);
      case "multiple_choice": return evaluateMultiple(activity, answer);
      case "short_answer": return evaluateShort(activity, answer);
      case "card_sorting": return evaluateCards(activity, answer);
      case "ordering_cards": return evaluateOrder(activity, answer);
      case "matching_pairs": return evaluatePairs(activity, answer);
      case "image_comparison":
        return (activity.response || {}).type === "multiple_choice"
          ? evaluateMultiple(activity, answer) : evaluateChoice(activity, answer);
      case "image_hotspot_labeling": return evaluateHotspots(activity, answer);
      case "sequence_checklist": return evaluateChecklist(activity, answer);
      case "integrated_assessment": return evaluateIntegrated(activity, answer);
      case "micro_lesson": return result(activity, false, 0, 0, "Micro-leçon consultée : aucune note attribuée.");
      default: throw new Error(`Type d’activité non pris en charge : ${activity.activity_type}`);
    }
  }

  function isComplete(activity, answer) {
    const response = activity.response || {};
    if (!hasStructuredResponse(activity)
      && activity.activity_type !== "integrated_assessment"
      && activity.activity_type !== "micro_lesson") {
      return Boolean(answer && String(answer.text || "").trim());
    }
    switch (activity.activity_type) {
      case "single_choice": case "image_comparison": {
        if (response.type === "single_choice_per_image") {
          const count = (activity.assets || []).length;
          return count > 0 && Array.isArray(answer?.choices) && answer.choices.length === count && answer.choices.every(Boolean);
        }
        if ((response.cause_options || []).length && (response.action_options || []).length) {
          return Boolean(answer?.cause && answer?.action);
        }
        if (Array.isArray(response.cases)) {
          return Array.isArray(answer?.cases) && answer.cases.length === response.cases.length && answer.cases.every(Boolean);
        }
        const cases = Number(response.cases || 1);
        if (cases > 1) return Array.isArray(answer?.choices) && answer.choices.length === cases && answer.choices.every(Boolean);
        return Boolean(answer && (answer.choice || (answer.choices || []).length || answer.text));
      }
      case "multiple_choice": return Boolean(answer && answer.choices && answer.choices.length);
      case "short_answer": return Boolean(answer && String(answer.text || "").trim());
      case "card_sorting": return response.cards && response.cards.every((card) => answer && answer.assignments && answer.assignments[card.id]);
      case "ordering_cards": return Boolean(answer && answer.order && answer.order.length);
      case "matching_pairs": return response.left_items && response.left_items.every((item) => answer && answer.pairs && answer.pairs[item]);
      case "image_hotspot_labeling": {
        const targets = Array.isArray(response.targets) ? response.targets : [response.target].filter(Boolean);
        return targets.length > 0 && targets.every((target, index) => {
          const id = typeof target === "object" && target !== null ? target.id : String(target || index);
          return Boolean(answer?.labels?.[id]);
        });
      }
      case "sequence_checklist":
        if (response.free_checklist || response.mode === "free_checklist") return Boolean(String(answer?.text || "").trim());
        return Boolean(answer && answer.checked && answer.checked.length);
      case "integrated_assessment": {
        if (Array.isArray(response.tasks_per_case) && (activity.assets || []).length) {
          const cases = answer?.cases;
          return Array.isArray(cases) && cases.length === activity.assets.length
            && cases.every((item) => response.tasks_per_case.every((task) => String(item?.[task] || "").trim()));
        }
        const tasks = response.tasks;
        if (!Array.isArray(tasks) || !tasks.length || tasks.some((task) => typeof task !== "object")) {
          return Boolean(answer && String(answer.text || "").trim());
        }
        return tasks.every((task) => isComplete(taskAsActivity(activity, task), answer?.tasks?.[task.id] || {}));
      }
      case "micro_lesson": return Boolean(answer && answer.continued);
      default: return false;
    }
  }

  function domainResults(module, records) {
    const threshold = Number(module.mastery_threshold_percent ?? 80);
    const domainMap = module.domain_competency_ids || {};
    const activities = Array.isArray(module.activities) ? module.activities : [];
    return (module.results_domains || []).map((domain) => {
      const competencies = new Set(domainMap[domain.id] || []);
      const assessments = activities.filter((activity) =>
        activity.phase === "test"
        && (activity.competency_ids || []).some((id) => competencies.has(id))
      );
      const results = assessments
        .map((activity) => records?.[activity.id]?.result)
        .filter((item) => item && item.evaluated);
      if (!competencies.size || !assessments.length || results.length !== assessments.length) {
        return { ...domain, status: "non évalué", percent: null };
      }
      const earned = results.reduce((sum, item) => sum + Number(item.earned || 0), 0);
      const possible = results.reduce((sum, item) => sum + Number(item.possible || 0), 0);
      const percent = possible > 0 ? Math.round((earned / possible) * 100) : null;
      const criticalErrors = results.flatMap((item) => item.criticalErrors || []);
      const acquired = percent !== null && percent >= threshold && criticalErrors.length === 0;
      return {
        ...domain,
        status: acquired ? "acquis" : "à consolider",
        percent,
        criticalErrors,
      };
    });
  }

  return { SUPPORTED_TYPES, normalized, equalSets, optionValue, evaluate, isComplete, domainResults };
});
