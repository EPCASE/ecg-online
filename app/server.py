"""
server.py — API Flask autonome de l'ECG lecture.

Endpoints :
  GET  /                      -> frontend (index.html)
  GET  /curation             -> interface de curation du barème (enseignant)
  GET  /api/health            -> statut + présence clé OpenAI
  GET  /api/cases             -> index léger des 75 cas
  GET  /api/families          -> familles + compteurs
  GET  /api/themes            -> thèmes larges (≥5 cas) pour l'accueil, non-spoiler
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

  -- Golden d'extraction (annotation, cf. GOLDEN_EXTRACTION.md) --
  GET  /annotation                     -> page d'annotation (protégée, enseignant/expert)
  GET  /api/annotation/overview        -> liste des items à annoter + statut
  GET  /api/annotation/<item_id>       -> texte + extraction pipeline + concepts déjà annotés
  POST /api/annotation/<item_id>       -> enregistre l'annotation experte {concepts, annotateur, slot}

  -- Golden conceptuel de scoring V2 — annotation solo + second avis IA
     (P1.3 simplifié, cf. audit_doc/roadmap_scientifique_2026.md §P1.3) --
  GET  /scoring-review                          -> page d'annotation (protégée)
  GET  /api/scoring-review/overview             -> liste des 10 cas pilote + statut
  GET  /api/scoring-review/<case_id>             -> cas ECG (image, texte) + critères + avis IA
  POST /api/scoring-review/<case_id>/<slot>      -> enregistre l'annotation du relecteur (slot=expert_1)
  POST /api/scoring-review/<case_id>/ai-review   -> génère/régénère le second avis GPT
  POST /api/scoring-review/<case_id>/ai-suggest  -> génère des critères candidats (premier jet IA à relire/valider)

Lancement local :  python -m app.server   (ou via run.py)
Prod (Scalingo)  :  gunicorn "app.server:create_app()"
"""
from __future__ import annotations

import os
import uuid

from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS

from . import cases_repo
from . import scoring_config
from . import golden_config
from . import neuro_grader
from . import collector
from . import extraction_golden
from . import scoring_v2_review
from . import abstention
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
            "pipeline_version": neuro_grader.PIPELINE_VERSION,
            "ontology_version": golden_config.ontology_version(),
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

    @app.get("/api/themes")
    def list_themes():
        # Thèmes larges (≥5 cas), TOUJOURS exposés — même en mode anonymisé —
        # car ils ne trahissent qu'une famille de diagnostics possibles, jamais
        # le diagnostic d'un cas précis (cf. NOTE_UX_THEMES_ACCUEIL.md §4).
        return jsonify(cases_repo.themes())

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
        skip_reason = None
        if GRADER_BACKEND == "neuro":
            corr = neuro_grader.grade_neuro(num_i, answer)
            if corr is not None and not corr.error:
                backend_used = "neuro"
            else:
                # Repli GPT-4o (cas non mappé ou erreur pipeline). On trace le
                # motif exact (Palier 1 — FEUILLE_DE_ROUTE_ALIGNEE.md) : un
                # repli silencieux masquait des lacunes de couverture golden.
                skip_reason = neuro_grader.last_skip_reason() or (
                    corr.error if corr is not None else "raison_inconnue"
                )
                corr = None
        if corr is None:
            corr = grade(case, answer, reference=ref, scoring=scoring)
            backend_used = "gpt"

        # État de résolution explicite (Palier 2 — abstention.py) : au lieu
        # d'un simple OK/FALLBACK_GPT, on qualifie aussi TECHNICAL_ERROR et
        # LOW_CONFIDENCE à partir de signaux déjà calculés (aucun changement
        # de comportement utilisateur, uniquement de la traçabilité).
        resolution = abstention.classify(
            backend_used=backend_used,
            primary_backend=GRADER_BACKEND,
            corr=corr,
            skip_reason=skip_reason,
        )

        result = corr.to_dict()
        result["backend"] = backend_used
        result["pipeline_version"] = neuro_grader.PIPELINE_VERSION
        result["ontology_version"] = golden_config.ontology_version()
        result["resolution"] = resolution
        # Identifiants stables (Palier 2) : permettent de relier une réponse
        # HTTP à sa trace de collecte (Google Sheets aujourd'hui, base de
        # données demain) sans dépendre de l'horodatage. `response_id` = cette
        # correction précise ; `prediction_id` = alias explicite pour la
        # littérature ML (même valeur pour l'instant, un cas pourra être noté
        # plusieurs fois → plusieurs response_id/prediction_id distincts).
        response_id = str(uuid.uuid4())
        result["response_id"] = response_id
        result["prediction_id"] = response_id
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
        meta_in = payload.get("meta")
        meta: dict = dict(meta_in) if isinstance(meta_in, dict) else {}
        meta["response_id"] = response_id
        meta["resolution_status"] = resolution["status"]
        meta["resolution_reason"] = resolution.get("reason") or ""
        meta["pipeline_version"] = neuro_grader.PIPELINE_VERSION
        meta["ontology_version"] = golden_config.ontology_version()
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
        # Contenu affiché à l'écran au moment du signalement (audit_doc/
        # roadmap_scientifique_2026.md, demande UX du 07/08/2026) : le
        # commentaire du correcteur IA et les mots-clés NER détectés sont
        # dupliqués dans la feuille « feedback » pour permettre le diagnostic
        # sans avoir à retrouver la session dans le journal « reponses ».
        commentaire_ia = str(payload.get("commentaire_ia", "")).strip()[:4000]
        mots_cles_ner = str(payload.get("mots_cles_ner", "")).strip()[:2000]
        saved = collector.collect_feedback(
            message[:2000], session=session, cas=cas,
            categorie=categorie, contexte=contexte, user_agent=user_agent,
            commentaire_ia=commentaire_ia, mots_cles_ner=mots_cles_ner,
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

    # ---- Golden d'extraction (annotation) — cf. GOLDEN_EXTRACTION.md ----
    @app.get("/annotation")
    def annotation_page():
        # Même protection que /curation : réservée à l'enseignant/expert.
        if not _curation_authorized(request):
            abort(403, description="Accès réservé.")
        return send_from_directory(FRONTEND_DIR, "annotation.html")

    @app.get("/api/annotation/overview")
    def annotation_overview():
        if not _curation_authorized(request):
            abort(403, description="Accès réservé.")
        return jsonify({"items": extraction_golden.overview()})

    @app.get("/api/annotation/<item_id>")
    def annotation_item(item_id: str):
        if not _curation_authorized(request):
            abort(403, description="Accès réservé.")
        item = extraction_golden.get_item(item_id)
        if item is None:
            abort(404, description=f"Item '{item_id}' introuvable.")
            raise RuntimeError("unreachable")
        return jsonify({"item_id": item_id, **item})

    @app.post("/api/annotation/<item_id>")
    def annotation_save(item_id: str):
        if not _curation_authorized(request):
            abort(403, description="Accès réservé.")
        payload = request.get_json(silent=True) or {}
        concepts = payload.get("concepts")
        if not isinstance(concepts, list):
            abort(400, description="Champ 'concepts' (liste) requis.")
            raise RuntimeError("unreachable")
        annotateur = str(payload.get("annotateur", "")).strip()[:80]
        slot = str(payload.get("slot", "annotation_expert")).strip()
        try:
            item = extraction_golden.save_annotation(
                item_id, concepts, annotateur=annotateur, slot=slot)
        except KeyError:
            abort(404, description=f"Item '{item_id}' introuvable.")
            raise RuntimeError("unreachable")
        except ValueError as exc:
            abort(400, description=str(exc))
            raise RuntimeError("unreachable")
        return jsonify({"item_id": item_id, "saved": True, **item})

    # ---- Golden conceptuel de scoring V2 — annotation multi-expert (P1.3) -
    @app.get("/scoring-review")
    def scoring_review_page():
        if not _curation_authorized(request):
            abort(403, description="Accès réservé.")
        return send_from_directory(FRONTEND_DIR, "scoring_review.html")

    @app.get("/api/scoring-review/overview")
    def scoring_review_overview():
        if not _curation_authorized(request):
            abort(403, description="Accès réservé.")
        return jsonify({"cases": scoring_v2_review.overview()})

    @app.get("/api/scoring-review/<case_id>")
    def scoring_review_case(case_id: str):
        if not _curation_authorized(request):
            abort(403, description="Accès réservé.")
        data = scoring_v2_review.get_case(case_id)
        if data is None:
            abort(404, description=f"Cas '{case_id}' introuvable dans le pilote.")
            raise RuntimeError("unreachable")
        return jsonify(data)

    @app.post("/api/scoring-review/<case_id>/<slot>")
    def scoring_review_save(case_id: str, slot: str):
        if not _curation_authorized(request):
            abort(403, description="Accès réservé.")
        payload = request.get_json(silent=True) or {}
        criteria = payload.get("criteria")
        if not isinstance(criteria, list):
            abort(400, description="Champ 'criteria' (liste) requis.")
            raise RuntimeError("unreachable")
        annotateur = str(payload.get("annotateur", "")).strip()[:80]
        try:
            entry = scoring_v2_review.save_expert_annotation(
                case_id, slot, criteria, annotateur=annotateur)
        except KeyError:
            abort(404, description=f"Cas '{case_id}' introuvable.")
            raise RuntimeError("unreachable")
        except ValueError as exc:
            abort(400, description=str(exc))
            raise RuntimeError("unreachable")
        return jsonify({"case_id": case_id, "saved": True, **entry})

    @app.post("/api/scoring-review/<case_id>/ai-review")
    def scoring_review_ai(case_id: str):
        if not _curation_authorized(request):
            abort(403, description="Accès réservé.")
        try:
            entry = scoring_v2_review.generate_ai_review(case_id)
        except KeyError:
            abort(404, description=f"Cas '{case_id}' introuvable.")
            raise RuntimeError("unreachable")
        except ValueError as exc:
            abort(400, description=str(exc))
            raise RuntimeError("unreachable")
        except RuntimeError as exc:
            abort(502, description=str(exc))
            raise RuntimeError("unreachable")
        return jsonify({"case_id": case_id, "saved": True, **entry})

    @app.post("/api/scoring-review/<case_id>/ai-suggest")
    def scoring_review_ai_suggest(case_id: str):
        if not _curation_authorized(request):
            abort(403, description="Accès réservé.")
        try:
            entry = scoring_v2_review.generate_ai_suggested_criteria(case_id)
        except KeyError:
            abort(404, description=f"Cas '{case_id}' introuvable.")
            raise RuntimeError("unreachable")
        except RuntimeError as exc:
            abort(502, description=str(exc))
            raise RuntimeError("unreachable")
        return jsonify({"case_id": case_id, "saved": True, **entry})

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
