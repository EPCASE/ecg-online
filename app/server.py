"""
server.py — API Flask autonome de l'ECG lecture.

Endpoints :
  GET  /                      -> frontend (index.html)
  GET  /api/health            -> statut + présence clé OpenAI
  GET  /api/cases             -> index léger des 75 cas
  GET  /api/families          -> familles + compteurs
  GET  /api/case/<num>        -> énoncé public d'un cas (sans correction)
  GET  /api/case/<num>/full   -> cas complet (correction incluse) [debug/enseignant]
  POST /api/grade             -> {num, answer} -> correction GPT (score + commentaire)
  GET  /images/<file>         -> tracés ECG (PNG)

Lancement local :  python -m app.server   (ou via run.py)
Prod (Scalingo)  :  gunicorn "app.server:create_app()"
"""
from __future__ import annotations

import os

from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS

from . import cases_repo
from .grader import grade, DEFAULT_MODEL

FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend"))


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

    # ---- Santé ----------------------------------------------------------
    @app.get("/api/health")
    def health():
        return jsonify({
            "status": "ok",
            "cases": len(cases_repo.all_cases()),
            "model": DEFAULT_MODEL,
            "openai_key": bool(os.environ.get("OPENAI_API_KEY")),
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

    # ---- Correction ouverte (GPT) --------------------------------------
    @app.post("/api/grade")
    def grade_answer():
        payload = request.get_json(silent=True) or {}
        num = payload.get("num")
        answer = payload.get("answer", "")
        if num is None:
            abort(400, description="Champ 'num' requis.")
        case = _require_case(num)
        corr = grade(case, answer)
        result = corr.to_dict()
        # On joint la référence APRÈS correction (l'étudiant a le droit de voir).
        result["reference"] = {
            "interpretation_ref": case.get("interpretation_ref", ""),
            "commentaires": case.get("commentaires", ""),
            "titre": case.get("titre", ""),
        }
        status = 200 if not corr.error else 502
        return jsonify(result), status

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
