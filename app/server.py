"""
server.py — API Flask autonome de l'ECG lecture.

Endpoints :
  GET  /                      -> frontend (index.html)
  GET  /curation             -> interface de curation du barème (enseignant)
  GET  /api/health            -> statut + présence clé OpenAI
  GET  /api/cases             -> index léger des 75 cas
  GET  /api/families          -> familles + compteurs
  GET  /api/case/<num>        -> énoncé public d'un cas (sans correction)
  GET  /api/case/<num>/full   -> cas complet (correction incluse) [debug/enseignant]
  GET  /api/case/<num>/qcm    -> QCM public d'un cas (question + options, sans solution)
  POST /api/case/<num>/qcm    -> {selected:[...]} -> correction du QCM
  POST /api/grade             -> {num, answer} -> correction GPT (score + commentaire)
  GET  /api/curation          -> vue d'ensemble de la curation des 75 cas
  GET  /api/curation/<num>    -> concepts d'un cas + rôles (validant/complémentaire)
  POST /api/curation/<num>    -> enregistre les rôles choisis
  POST /api/curation/<num>/reset -> réinitialise un cas (retour aux défauts)
  GET  /api/onto/search?q=    -> recherche de concepts ontologiques (picker)
  GET  /api/onto/concept/<id> -> détail d'un concept ontologique
  POST /api/curation/<num>/mapping -> enregistre le mapping label->concept_id
  GET  /api/curation/<num>/golden  -> contrat golden (validants/descripteurs) pour le scorer
  GET  /images/<file>         -> tracés ECG (PNG)

Lancement local :  python -m app.server   (ou via run.py)
Prod (Scalingo)  :  gunicorn "app.server:create_app()"
"""
from __future__ import annotations

import os

from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS

from . import cases_repo
from . import scoring_config
from . import golden_config
from . import neuro_grader
from . import collector
from .grader import grade, DEFAULT_MODEL

FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend"))

# Backend de correction : "neuro" (pipeline neurosymbolique V3, défaut) ou "gpt"
# (grader GPT-4o direct). "neuro" se rabat automatiquement sur "gpt" s'il est
# indisponible (dépendance/index manquant, cas non mappé, pas de clé API).
GRADER_BACKEND = os.environ.get("ECG_GRADER_BACKEND", "neuro").strip().lower()

# Jeton de protection du barème (curation). Réservé à l'enseignant.
#   • Vide (défaut)  -> /curation et l'édition du barème sont OUVERTS (dev local).
#   • Défini         -> la page /curation et TOUTE écriture du barème exigent le
#                       jeton, fourni via ?key=… (page) ou l'en-tête
#                       X-Curation-Token (API). Un étudiant qui tape /curation
#                       sans le jeton reçoit un 403.
CURATION_TOKEN = os.environ.get("CURATION_TOKEN", "").strip()


def _curation_authorized(req) -> bool:
    """Le jeton fourni correspond-il ? Toujours vrai si aucun jeton n'est configuré."""
    if not CURATION_TOKEN:
        return True
    supplied = (req.headers.get("X-Curation-Token")
                or req.args.get("key") or "").strip()
    return supplied == CURATION_TOKEN


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    CORS(app)

    def _require_case(num) -> dict:
        c = cases_repo.get_case(int(num))
        if not c:
            abort(404, description=f"Cas {num} introuvable.")
            raise RuntimeError("unreachable")  # aide le type-checker
        return c

    # ---- Frontend -------------------------------------------------------
    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/static/<path:filename>")
    def frontend_static(filename):
        return send_from_directory(FRONTEND_DIR, filename)

    @app.get("/curation")
    def curation_page():
        # Page enseignant : protégée si CURATION_TOKEN est défini (accès via
        # /curation?key=…). Sinon un 403 « discret » (pas d'indice pour l'élève).
        if not _curation_authorized(request):
            abort(403, description="Accès réservé.")
        return send_from_directory(FRONTEND_DIR, "curation.html")

    # ---- Santé ----------------------------------------------------------
    @app.get("/api/health")
    def health():
        return jsonify({
            "status": "ok",
            "cases": len(cases_repo.all_cases()),
            "model": DEFAULT_MODEL,
            "openai_key": bool(os.environ.get("OPENAI_API_KEY")),
            "grader_backend": GRADER_BACKEND,
            "neuro": neuro_grader.status(),
            "collector": collector.status(),
            "anonymize": cases_repo.anonymize_enabled(),
        })

    # ---- Banque de cas --------------------------------------------------
    @app.get("/api/cases")
    def list_cases():
        return jsonify(cases_repo.public_index())

    @app.get("/api/families")
    def list_families():
        return jsonify(cases_repo.families())

    @app.get("/api/case/<int:num>")
    def one_case(num: int):
        c = _require_case(num)
        return jsonify(cases_repo.public_case(c))

    @app.get("/api/case/<int:num>/full")
    def one_case_full(num: int):
        if not CURATION_TOKEN or not _curation_authorized(request):
            abort(403, description="Accès réservé.")
        c = _require_case(num)
        return jsonify(c)

    # ---- QCM ------------------------------------------------------------
    @app.get("/api/case/<int:num>/qcm")
    def one_case_qcm(num: int):
        _require_case(num)
        qcm = cases_repo.get_qcm_public(num)
        if not qcm:
            abort(404, description=f"Aucun QCM pour le cas {num}.")
        return jsonify(qcm)

    @app.post("/api/case/<int:num>/qcm")
    def check_case_qcm(num: int):
        _require_case(num)
        payload = request.get_json(silent=True) or {}
        selected = payload.get("selected", [])
        if not isinstance(selected, list):
            abort(400, description="Champ 'selected' doit être une liste de lettres.")
        res = cases_repo.check_qcm(num, selected)
        if res is None:
            abort(404, description=f"Aucun QCM pour le cas {num}.")
        return jsonify(res)

    # ---- Correction ouverte (GPT) --------------------------------------
    @app.post("/api/grade")
    def grade_answer():
        payload = request.get_json(silent=True) or {}
        num = payload.get("num")
        answer = payload.get("answer", "")
        if num is None:
            abort(400, description="Champ 'num' requis.")
        try:
            num_i = int(num)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            abort(400, description="Champ 'num' invalide.")
            raise RuntimeError("unreachable")
        case = _require_case(num_i)
        ref = cases_repo.get_reference(num_i)
        scoring = scoring_config.split_for_grader(num_i)

        # Choix du backend : neurosymbolique (défaut) avec repli GPT-4o.
        backend_used = "gpt"
        corr = None
        if GRADER_BACKEND == "neuro":
            corr = neuro_grader.grade_neuro(num_i, answer)
            if corr is not None and not corr.error:
                backend_used = "neuro"
            else:
                corr = None  # repli GPT-4o (cas non mappé ou erreur pipeline)
        if corr is None:
            corr = grade(case, answer, reference=ref, scoring=scoring)
            backend_used = "gpt"

        result = corr.to_dict()
        result["backend"] = backend_used
        # On joint la référence APRÈS correction (l'étudiant a le droit de voir).
        # `titre` = diagnostic réel + `famille` : révélés post-correction (note
        # UX §12 : « révéler l'objectif pédagogique » une fois la réponse rendue).
        result["reference"] = {
            "interpretation_ref": case.get("interpretation_ref", ""),
            "commentaires": case.get("commentaires", ""),
            "titre": case.get("titre", ""),
            "famille": case.get("famille", ""),
            "reponse_attendue": (ref or {}).get("reponse_attendue", ""),
            "points_cles": (ref or {}).get("points_cles", []),
            "fiche_secours": (ref or {}).get("fiche_secours", {}),
        }
        result["scoring"] = scoring

        # Recueil optionnel (Google Sheets) — non bloquant, no-op si non configuré.
        # On archive le titre RÉEL (côté serveur), jamais la version anonymisée.
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
        collector.collect_answer(
            num_i,
            case.get("titre", ""),
            answer,
            score=result.get("score"),
            correspondance=result.get("correspondance", ""),
            backend=backend_used,
            session=str(payload.get("session", "")),
            meta=meta,
        )

        status = 200 if not corr.error else 502
        return jsonify(result), status

    # ---- Signalement d'un problème (version pré-alpha) ------------------
    @app.post("/api/feedback")
    def feedback():
        payload = request.get_json(silent=True) or {}
        message = str(payload.get("message", "")).strip()
        if not message:
            abort(400, description="Message vide.")
        cas = payload.get("cas")
        categorie = str(payload.get("categorie", "")).strip()[:60]
        contexte = str(payload.get("contexte", "")).strip()[:500]
        session = str(payload.get("session", "")).strip()[:80]
        user_agent = str(request.headers.get("User-Agent", ""))[:300]
        saved = collector.collect_feedback(
            message[:2000], session=session, cas=cas,
            categorie=categorie, contexte=contexte, user_agent=user_agent,
        )
        # `saved=False` => recueil non configuré : le front proposera un repli mail.
        return jsonify({"ok": True, "saved": saved})

    # ---- Validation de concepts par l'étudiant (curation P5) -----------
    @app.post("/api/concept-review")
    def concept_review():
        """Vote 👍/👎 sur les concepts que le pipeline a extraits de la réponse.

        Alimente l'inbox de curation golden/NER : chaque vote dit si le système
        a bien COMPRIS ce que l'étudiant a écrit. Non bloquant, no-op si le
        recueil n'est pas configuré (`saved=False`).
        """
        payload = request.get_json(silent=True) or {}
        raw = payload.get("concepts")
        if not isinstance(raw, list) or not raw:
            abort(400, description="Champ 'concepts' (liste) requis.")
            raise RuntimeError("unreachable")
        rows = []
        for item in raw[:50]:
            if not isinstance(item, dict):
                continue
            vote = str(item.get("vote", "")).strip().lower()
            if vote not in ("ok", "ko"):
                continue
            rows.append({
                "terme": str(item.get("terme", ""))[:200],
                "concept": str(item.get("concept", ""))[:200],
                "id": str(item.get("id", ""))[:60],
                "statut": str(item.get("statut", ""))[:20],
                "vote": vote,
            })
        if not rows:
            abort(400, description="Aucun vote valide ('ok'/'ko').")
        cas = payload.get("cas")
        session = str(payload.get("session", "")).strip()[:80]
        saved = collector.collect_concept_review(rows, session=session, cas=cas)
        return jsonify({"ok": True, "saved": saved, "count": len(rows)})

    # ---- Compteurs de lecture par cas (randomisation pondérée §5.4) -----
    @app.get("/api/case-stats")
    def case_stats():
        """{counts: {num: n}, available: bool} — nb de soumissions par cas.

        Sert au tirage pondéré côté client (suréchantillonner les cas peu lus,
        pour équilibrer le corpus de réponses). Cache serveur 10 min.
        `available=False` (recueil non configuré) → le front garde son hasard
        uniforme. Ne divulgue RIEN du contenu des cas (juste des compteurs).
        """
        counts = collector.case_counts()
        if counts is None:
            return jsonify({"available": False, "counts": {}})
        return jsonify({"available": True,
                        "counts": {str(k): v for k, v in counts.items()}})

    # ---- Curation du barème (validant / complémentaire) ----------------
    @app.get("/api/curation")
    def curation_overview():
        if not _curation_authorized(request):
            abort(403, description="Accès réservé.")
        rows = scoring_config.overview()
        status = golden_config.overview_status()
        onto_ok = golden_config.onto_available()
        for r in rows:
            st = status.get(r["num"], {})
            r["nb_mapped"] = st.get("nb_mapped", 0)
            r["nb_human"] = st.get("nb_human", 0)
        return jsonify({"onto_available": onto_ok, "cases": rows})

    @app.get("/api/curation/<int:num>")
    def curation_case(num: int):
        if not _curation_authorized(request):
            abort(403, description="Accès réservé.")
        c = _require_case(num)
        concepts = scoring_config.curated_points(num, include_removed=True)
        golden_config.attach_mapping(num, concepts)
        return jsonify({
            "num": num,
            "titre": c.get("titre"),
            "famille": c.get("famille"),
            "patient": c.get("patient", ""),
            "contexte": c.get("contexte", ""),
            "images": c.get("images", []),
            "interpretation_ref": c.get("interpretation_ref", ""),
            "concepts": concepts,
            "configured": scoring_config.get_case_config(num) is not None,
            "diagnostic_principal": golden_config.get_case_diag(num),
            "onto_available": golden_config.onto_available(),
        })

    @app.post("/api/curation/<int:num>")
    def curation_save(num: int):
        if not _curation_authorized(request):
            abort(403, description="Accès réservé.")
        _require_case(num)
        payload = request.get_json(silent=True) or {}
        roles = payload.get("roles", {})
        extra = payload.get("extra_validants", [])
        removed = payload.get("removed", [])
        if not isinstance(roles, dict):
            abort(400, description="Champ 'roles' doit être un objet {label: role}.")
        saved = scoring_config.save_case_config(num, roles, extra, removed)
        concepts = scoring_config.curated_points(num, include_removed=True)
        golden_config.attach_mapping(num, concepts)
        return jsonify({"num": num, "saved": saved, "concepts": concepts})

    @app.post("/api/curation/<int:num>/reset")
    def curation_reset(num: int):
        if not _curation_authorized(request):
            abort(403, description="Accès réservé.")
        _require_case(num)
        scoring_config.reset_case_config(num)
        concepts = scoring_config.curated_points(num, include_removed=True)
        golden_config.attach_mapping(num, concepts)
        return jsonify({"num": num, "reset": True, "concepts": concepts})

    # ---- Mapping ontologique (le « pont sémantique ») ------------------
    @app.get("/api/onto/search")
    def onto_search():
        q = request.args.get("q", "")
        try:
            limit = min(50, max(1, int(request.args.get("limit", 20))))
        except (TypeError, ValueError):
            limit = 20
        return jsonify({
            "available": golden_config.onto_available(),
            "results": golden_config.search_concepts(q, limit=limit),
        })

    @app.get("/api/onto/concept/<cid>")
    def onto_concept(cid: str):
        info = golden_config.resolve_concept(cid)
        if not info:
            abort(404, description=f"Concept '{cid}' introuvable dans l'ontologie.")
        return jsonify(info)

    @app.post("/api/curation/<int:num>/mapping")
    def curation_save_mapping(num: int):
        if not _curation_authorized(request):
            abort(403, description="Accès réservé.")
        _require_case(num)
        payload = request.get_json(silent=True) or {}
        mapping = payload.get("mapping", {})
        diag = payload.get("diagnostic_principal")
        if not isinstance(mapping, dict):
            abort(400, description="Champ 'mapping' doit être un objet {label: golden_id}.")
        golden_config.save_case_mapping(num, mapping, diagnostic_principal=diag)
        concepts = scoring_config.curated_points(num, include_removed=True)
        golden_config.attach_mapping(num, concepts)
        return jsonify({
            "num": num,
            "concepts": concepts,
            "golden": golden_config.golden_for_scorer(num),
            "diagnostic_principal": golden_config.get_case_diag(num),
        })

    @app.get("/api/curation/<int:num>/golden")
    def curation_golden(num: int):
        _require_case(num)
        return jsonify(golden_config.golden_for_scorer(num))

    # ---- Images ECG -----------------------------------------------------
    @app.get("/images/<path:filename>")
    def ecg_image(filename):
        return send_from_directory(cases_repo.IMAGES_DIR, filename)

    # ---- Erreurs JSON ---------------------------------------------------
    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(502)
    def _json_error(err):
        return jsonify({"error": getattr(err, "description", str(err))}), \
            getattr(err, "code", 500)

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
