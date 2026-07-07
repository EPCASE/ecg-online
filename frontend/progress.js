/* progress.js — Suivi de progression LOCAL et anonyme (Sprint 1 UX).
 *
 * Tout est stocké dans le navigateur (localStorage) : aucune donnée nominative,
 * aucune dépendance serveur. On y conserve :
 *   • un identifiant de session anonyme (pour tracer l'usage côté recueil) ;
 *   • pour chaque cas : nb de tentatives, meilleur score, dernière corresp. ;
 *   • une série de jours consécutifs d'entraînement (streak, douce, sans pénalité).
 *
 * Objectif pédagogique (cf. note UX §4, §8, §13) : transformer une banque de cas
 * en boucle d'entraînement — savoir où on en est et quoi faire ensuite.
 *
 * L'API est volontairement minimale et synchrone : lire/écrire du JSON local.
 */
const Progress = (() => {
  const KEY = "ecg.progress.v1";
  const SESSION_KEY = "ecg.session.v1";

  /* ---- Utilitaires date (jour civil local, sans l'heure) ---- */
  const dayStamp = (d = new Date()) => {
    // AAAA-MM-JJ en heure locale (pas UTC) pour une « série de jours » naturelle.
    const z = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
  };
  const daysBetween = (a, b) => {
    // Différence entière en jours entre deux stamps AAAA-MM-JJ.
    const da = new Date(a + "T00:00:00");
    const db = new Date(b + "T00:00:00");
    return Math.round((db - da) / 86400000);
  };

  /* ---- Identifiant de session anonyme (stable, non nominatif) ---- */
  function sessionId() {
    let sid = localStorage.getItem(SESSION_KEY);
    if (!sid) {
      const rnd = (crypto && crypto.randomUUID)
        ? crypto.randomUUID()
        : "s-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
      sid = rnd;
      localStorage.setItem(SESSION_KEY, sid);
    }
    return sid;
  }

  /* ---- Lecture / écriture de l'état ---- */
  function _load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return _empty();
      const s = JSON.parse(raw);
      s.cases = s.cases || {};
      return s;
    } catch {
      return _empty();
    }
  }
  function _empty() {
    return { cases: {}, streak: 0, lastActiveDay: null, totalGraded: 0 };
  }
  function _save(s) {
    try { localStorage.setItem(KEY, JSON.stringify(s)); } catch { /* quota : on ignore */ }
  }

  /* ---- Enregistrer un résultat de correction ---- */
  function recordResult(num, score, correspondance, titre) {
    const s = _load();
    const key = String(num);
    const prev = s.cases[key] || { attempts: 0, best: 0, corr: "", firstDay: null, lastDay: null };
    const today = dayStamp();
    const sc = Number.isFinite(score) ? Math.round(score) : 0;

    prev.attempts += 1;
    prev.best = Math.max(prev.best || 0, sc);
    prev.corr = correspondance || prev.corr || "";
    // Titre RÉEL révélé après correction (P1) : mémorisé pour lever
    // l'anonymisation de la liste sur les cas DÉJÀ faits (révision).
    // L'étudiant l'a déjà vu — aucune fuite. Repli sur l'ancien si absent.
    if (titre && String(titre).trim()) prev.titre = String(titre).trim();
    prev.firstDay = prev.firstDay || today;
    prev.lastDay = today;
    s.cases[key] = prev;
    s.totalGraded = (s.totalGraded || 0) + 1;

    // Série de jours : +1 si hier, inchangée si aujourd'hui, sinon réamorcée à 1.
    if (s.lastActiveDay) {
      const gap = daysBetween(s.lastActiveDay, today);
      if (gap === 1) s.streak = (s.streak || 0) + 1;
      else if (gap > 1) s.streak = 1;
      // gap === 0 : déjà actif aujourd'hui, on ne touche pas la série.
    } else {
      s.streak = 1;
    }
    s.lastActiveDay = today;

    _save(s);
    return s;
  }

  /* ---- Accès pratiques ---- */
  function caseStat(num) {
    const s = _load();
    return s.cases[String(num)] || null;
  }
  function isDone(num) {
    return !!caseStat(num);
  }
  function doneCount() {
    return Object.keys(_load().cases).length;
  }
  function averageBest() {
    const cs = Object.values(_load().cases);
    if (!cs.length) return null;
    const sum = cs.reduce((a, c) => a + (c.best || 0), 0);
    return Math.round(sum / cs.length);
  }
  function streak() {
    const s = _load();
    if (!s.lastActiveDay) return 0;
    // Une série « expire » si le dernier jour actif n'est ni aujourd'hui ni hier.
    const gap = daysBetween(s.lastActiveDay, dayStamp());
    return gap <= 1 ? (s.streak || 0) : 0;
  }
  function summary() {
    return {
      done: doneCount(),
      totalGraded: _load().totalGraded || 0,
      average: averageBest(),
      streak: streak(),
    };
  }

  /* ---- Recommandation de cas ----
   * allNums : liste ordonnée des numéros de cas connus (ordre du parcours).
   * Renvoie le prochain cas NON fait après `fromNum` (bouclage), sinon le
   * moins bien réussi (pour consolider), sinon null. */
  function nextCase(allNums, fromNum) {
    if (!allNums || !allNums.length) return null;
    const done = new Set(Object.keys(_load().cases).map(Number));
    const idx = fromNum != null ? allNums.indexOf(Number(fromNum)) : -1;

    // 1) prochain NON fait en avançant dans l'ordre (depuis la position courante)
    for (let step = 1; step <= allNums.length; step++) {
      const cand = allNums[(idx + step + allNums.length) % allNums.length];
      if (!done.has(cand)) return cand;
    }
    // 2) tout est fait : proposer le cas au meilleur score le plus faible (à revoir)
    const cs = _load().cases;
    let worst = null, worstScore = 101;
    for (const n of allNums) {
      const st = cs[String(n)];
      const sc = st ? (st.best || 0) : 0;
      if (n !== Number(fromNum) && sc < worstScore) { worstScore = sc; worst = n; }
    }
    return worst;
  }

  /* Un cas non-fait au hasard (hors `exceptNum`), sinon n'importe lequel.
   * `globalCounts` (optionnel) : {num: nbSoumissionsPromo} → tirage PONDÉRÉ
   * (note UX §5.4) qui suréchantillonne les cas peu lus pour équilibrer le
   * corpus. Poids = 1/(1+count)² : un cas jamais lu pèse 9× plus qu'un cas
   * lu 2 fois. Sans compteurs → hasard uniforme (comportement historique). */
  function randomCase(allNums, exceptNum, globalCounts) {
    if (!allNums || !allNums.length) return null;
    const done = new Set(Object.keys(_load().cases).map(Number));
    const pool = allNums.filter((n) => n !== Number(exceptNum) && !done.has(n));
    const src = pool.length ? pool : allNums.filter((n) => n !== Number(exceptNum));
    if (!src.length) return null;
    if (globalCounts && typeof globalCounts === "object") {
      const weights = src.map((n) => {
        const c = Number(globalCounts[String(n)] ?? globalCounts[n] ?? 0);
        return 1 / Math.pow(1 + Math.max(0, c), 2);
      });
      const total = weights.reduce((a, w) => a + w, 0);
      if (total > 0) {
        let r = Math.random() * total;
        for (let i = 0; i < src.length; i++) {
          r -= weights[i];
          if (r <= 0) return src[i];
        }
        return src[src.length - 1];   // garde-fou arrondi flottant
      }
    }
    return src[Math.floor(Math.random() * src.length)];
  }

  /* Cas « du jour » : déterministe par date → tout le monde a le même chaque jour,
   * mais il change chaque jour et couvre progressivement la banque. */
  function dailyCase(allNums) {
    if (!allNums || !allNums.length) return null;
    const epochDay = Math.floor(Date.parse(dayStamp() + "T00:00:00") / 86400000);
    return allNums[epochDay % allNums.length];
  }

  function reset() {
    localStorage.removeItem(KEY);
  }

  return {
    sessionId, recordResult, caseStat, isDone, doneCount,
    summary, nextCase, randomCase, dailyCase, reset,
  };
})();

// Exposé global (chargé avant app.js).
window.Progress = Progress;
