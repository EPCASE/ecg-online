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
from .grader import grade, DEFAULT_MODEL

FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend"))

# Backend de correction : "neuro" (pipeline neurosymbolique V3, défaut) ou "gpt"
# (grader GPT-4o direct). "neuro" se rabat automatiquement sur "gpt" s'il est
# indisponible (dépendance/index manquant, cas non mappé, pas de clé API).
GRADER_BACKEND = os.environ.get("ECG_GRADER_BACKEND", "neuro").strip().lower()


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
        result["reference"] = {
            "interpretation_ref": case.get("interpretation_ref", ""),
            "commentaires": case.get("commentaires", ""),
            "titre": case.get("titre", ""),
            "reponse_attendue": (ref or {}).get("reponse_attendue", ""),
            "points_cles": (ref or {}).get("points_cles", []),
            "fiche_secours": (ref or {}).get("fiche_secours", {}),
        }
        result["scoring"] = scoring
        status = 200 if not corr.error else 502
        return jsonify(result), status

    # ---- Curation du barème (validant / complémentaire) ----------------
    @app.get("/api/curation")
    def curation_overview():
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
