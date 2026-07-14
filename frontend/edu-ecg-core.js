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
    const critical = criticalMap[selected] ? [criticalMap[selected]] : [];
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
    const response = activity.response || {};
    const expected = response.expected_concepts || response.accepted_answers;
    if (!Array.isArray(expected) || !expected.length) return result(activity, false);
    const value = normalized((answer || {}).text);
    const hits = expected.filter((concept) => value.includes(normalized(concept))).length;
    return result(activity, true, hits, expected.length,
      `${hits}/${expected.length} concept${expected.length > 1 ? "s" : ""} explicite${expected.length > 1 ? "s" : ""} retrouvé${hits > 1 ? "s" : ""}.`);
  }

  function evaluateCards(activity, answer) {
    const cards = (activity.response || {}).cards || [];
    if (!cards.length || cards.some((card) => card.category == null)) return result(activity, false);
    const assignments = (answer || {}).assignments || {};
    const earned = cards.filter((card) => assignments[card.id] === card.category).length;
    return result(activity, true, earned, cards.length);
  }

  function evaluateOrder(activity, answer) {
    const response = activity.response || {};
    const key = response.correct_order;
    if (!Array.isArray(key) || !key.length) return result(activity, false);
    const order = (answer || {}).order || [];
    const earned = key.filter((item, index) => String(order[index]) === String(item)).length;
    return result(activity, true, earned, key.length);
  }

  function evaluatePairs(activity, answer) {
    const correct = (activity.response || {}).correct_pairs;
    if (!Array.isArray(correct) || !correct.length) return result(activity, false);
    const pairs = (answer || {}).pairs || {};
    const earned = correct.filter(([left, right]) => pairs[left] === right).length;
    return result(activity, true, earned, correct.length);
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
    return result(activity, true, earned, entries.length);
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
    switch (activity.activity_type) {
      case "single_choice": case "image_comparison": return Boolean(answer && (answer.choice || (answer.choices || []).length || answer.text));
      case "multiple_choice": return Boolean(answer && answer.choices && answer.choices.length);
      case "short_answer": return Boolean(answer && String(answer.text || "").trim());
      case "card_sorting": return response.cards && response.cards.every((card) => answer && answer.assignments && answer.assignments[card.id]);
      case "ordering_cards": return Boolean(answer && answer.order && answer.order.length);
      case "matching_pairs": return response.left_items && response.left_items.every((item) => answer && answer.pairs && answer.pairs[item]);
      case "image_hotspot_labeling": return Boolean(answer && answer.labels && Object.keys(answer.labels).length);
      case "sequence_checklist": return Boolean(answer && answer.checked && answer.checked.length);
      case "integrated_assessment": {
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

  return { SUPPORTED_TYPES, normalized, equalSets, optionValue, evaluate, isComplete };
});
