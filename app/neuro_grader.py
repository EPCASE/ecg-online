"""
neuro_grader.py — Adaptateur : pipeline RAG neurosymbolique  →  format `Correction`.
====================================================================================
Branche l'interface `ecg-online` sur le PIPELINE NEUROSYMBOLIQUE (ARCHITECTURE.md,
Partie A : les 6 briques) au lieu du grader GPT-4o direct (Partie B).

Principe (cf. golden_config.py, « le pont sémantique ») :
  1. `golden_config.golden_for_scorer(num)` fournit le CONTRAT golden du cas
     (validants + descripteurs, chacun mappé à un concept_id ontologique + statut).
  2. On appelle `generate_candidate_report(texte, golden_ids, golden_names,
     golden_roles, diagnostic_principal)` — le cœur des briques 2→6.
  3. On mappe le `CandidateReport` (scoring V3 déterministe) vers le même dict que
     `grader.Correction.to_dict()` pour que le frontend n'ait RIEN à changer.

Le pipeline est VENDORÉ dans `ecg-online/rag_pipeline/` (modules + index + onto)
→ l'app reste autonome et déployable sur Scalingo.

Robustesse : si le pipeline est indisponible (dépendance manquante, index absent,
pas de golden mappé, erreur API), `available()` renvoie False et l'appelant peut
se rabattre sur le grader GPT-4o. Aucune exception ne remonte à l'API HTTP.
"""
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from . import golden_config

if TYPE_CHECKING:
    from .grader import Correction

# ── Localisation du pipeline vendoré ────────────────────────────────────────
_PIPELINE_DIR = Path(__file__).resolve().parent.parent / "rag_pipeline"

# Les modules du pipeline s'importent à plat (`from ner_extractor import …`),
# donc le dossier doit être sur sys.path.
if _PIPELINE_DIR.exists() and str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))

_lock = threading.Lock()
_import_error: Optional[str] = None
_generate = None  # type: ignore
_engine = None    # HybridSearchEngine préchargé (singleton)


def _try_import() -> bool:
    """Importe le pipeline (paresseux, une seule fois). True si disponible."""
    global _generate, _import_error
    if _generate is not None:
        return True
    if _import_error is not None:
        return False
    try:
        from candidate_report import generate_candidate_report  # type: ignore
        _generate = generate_candidate_report
        return True
    except Exception as ex:  # dépendance manquante (numpy/rank_bm25), index, etc.
        _import_error = f"{type(ex).__name__}: {ex}"
        return False


def _get_engine():
    """Précharge le HybridSearchEngine (index en RAM) une seule fois."""
    global _engine
    if _engine is None:
        from hybrid_search import HybridSearchEngine  # type: ignore
        _engine = HybridSearchEngine()
    return _engine


def available() -> bool:
    """Le pipeline neurosymbolique est-il utilisable (modules + index + onto + clé) ?"""
    if not _PIPELINE_DIR.exists():
        return False
    if not _try_import():
        return False
    if not golden_config.onto_available():
        return False
    return bool(os.environ.get("OPENAI_API_KEY"))


def status() -> dict:
    """Diagnostic pour /api/health."""
    _try_import()
    return {
        "pipeline_dir": str(_PIPELINE_DIR),
        "pipeline_present": _PIPELINE_DIR.exists(),
        "importable": _generate is not None,
        "import_error": _import_error,
        "onto_available": golden_config.onto_available(),
        "openai_key": bool(os.environ.get("OPENAI_API_KEY")),
        "available": available(),
    }


# ── Mapping CandidateReport → format Correction (frontend) ───────────────────
def _rang_of(entry: dict) -> str:
    r = str(entry.get("rang") or "?").upper()
    return r if r in ("A", "B", "C") else "?"


def _has_mapped_validant(num: int) -> bool:
    g = golden_config.golden_for_scorer(num)
    return bool(g.get("validants"))


def grade_neuro(num: int, texte_etudiant: str) -> Optional["Correction"]:
    """Corrige via le pipeline neurosymbolique. Retourne un objet compatible
    `grader.Correction` (méthode `.to_dict()` + attribut `.error`), ou None si
    le pipeline n'est pas applicable (l'appelant se rabat alors sur GPT-4o).
    """
    from .grader import Correction  # import local (évite cycle au chargement)

    if not available():
        return None
    g = golden_config.golden_for_scorer(num)
    validants = g.get("validants") or []
    descripteurs = g.get("descripteurs") or []
    if not validants:
        # Sans concept validant mappé, le scorer onto n'a rien à mesurer.
        return None

    # Contrat pour le pipeline : ids + names + roles alignés.
    golden_ids: List[str] = []
    golden_names: List[str] = []
    golden_roles: List[str] = []
    for v in validants:
        golden_ids.append(v["concept_id"]); golden_names.append(v["concept_name"])
        golden_roles.append("validant")
    for d in descripteurs:
        golden_ids.append(d["concept_id"]); golden_names.append(d["concept_name"])
        golden_roles.append("descripteur")

    diag = g.get("diagnostic_principal") or (validants[0]["concept_name"] if validants else "")

    try:
        with _lock:  # HybridSearchEngine/BM25 : sérialise les appels (thread-safe).
            report = _generate(  # type: ignore[misc]
                texte_etudiant=texte_etudiant,
                golden_ids=golden_ids,
                golden_names=golden_names,
                golden_roles=golden_roles,
                diagnostic_principal=diag,
                moteur=_get_engine(),
                with_feedback=True,
            )
    except Exception as ex:
        return Correction(
            score=0, verdict="Erreur du pipeline neurosymbolique.",
            diagnostic_retenu="", commentaire="", model="neuro-pipeline",
            error=f"{type(ex).__name__}: {ex}")

    if getattr(report, "erreur", None):
        return Correction(
            score=0, verdict="Erreur du pipeline neurosymbolique.",
            diagnostic_retenu="", commentaire="", model="neuro-pipeline",
            error=str(report.erreur))

    return _report_to_correction(report, num)


def _report_to_correction(report, num: int):
    """Traduit un CandidateReport (scoring V3) en `Correction` (format frontend)."""
    from .grader import Correction

    score = int(round(getattr(report, "score_final_pct", 0.0)))

    # ── Éléments trouvés / manqués (validants → note ; descripteurs → indicatif)
    elements_trouves: List[dict] = []
    elements_manques: List[dict] = []
    for vd in getattr(report, "validant_details", []):
        label = vd.golden_name or vd.golden_id
        if vd.found:
            elements_trouves.append({"label": label, "rang": "A"})
        else:
            elements_manques.append({
                "label": label, "rang": "A",
                "importance": _explain_validant(vd),
            })
    for dd in getattr(report, "descripteur_details", []):
        label = dd.golden_name or dd.golden_id
        if dd.found:
            elements_trouves.append({"label": label, "rang": "B"})
        else:
            elements_manques.append({"label": label, "rang": "B",
                                     "importance": "descripteur (indicatif, sans impact)"})

    # ── Découvertes (concepts vrais hors barème) → trouvés rang C
    for dec in getattr(report, "decouvertes", []):
        nom = getattr(dec, "concept_name", "") or getattr(dec, "ontology_id", "")
        if nom:
            elements_trouves.append({"label": nom, "rang": "C"})

    # ── Éléments erronés : concepts extraits résolus mais hors golden et hors
    #    découvertes « vraies » → on reste prudent : le scoring V3 ne qualifie pas
    #    un extrait de « faux ». On n'invente donc pas d'erreurs ici (liste vide),
    #    sauf verdict « excluded » sur un validant (concept incompatible présent).
    elements_errones: List[dict] = []
    for vd in getattr(report, "validant_details", []):
        if getattr(vd, "match_type", "") == "excluded" and getattr(vd, "excluded_by", ""):
            elements_errones.append({
                "label": f"Incompatible : {vd.excluded_by}",
                "correction": f"écarte « {vd.golden_name} »",
            })

    # ── Sous-scores : diagnostic = score V3 (piloté par les validants) ;
    #    descriptif = taux de descripteurs trouvés.
    nb_desc_att = getattr(report, "nb_descripteurs_attendus", 0) or 0
    nb_desc_found = getattr(report, "nb_descripteurs_trouves", 0) or 0
    score_descriptif = int(round(100 * nb_desc_found / nb_desc_att)) if nb_desc_att else score
    score_diagnostic = score

    # ── Correspondance / type d'erreur (dérivés du score, cohérents avec le front)
    nb_val_att = getattr(report, "nb_validants_attendus", 0) or 0
    nb_val_found = getattr(report, "nb_validants_trouves", 0) or 0
    correspondance, type_erreur = _classify(score, nb_val_found, nb_val_att)

    # ── Diagnostic retenu : 1er validant trouvé, sinon le concept extrait dominant
    diagnostic_retenu = _guess_retained_dx(report)

    # ── Commentaire : feedback pédagogique GPT si dispo, sinon synthèse V3.
    commentaire = _build_comment(report, score, nb_val_found, nb_val_att)

    verdict = _verdict(score, nb_val_found, nb_val_att)

    return Correction(
        score=score,
        verdict=verdict,
        diagnostic_retenu=diagnostic_retenu,
        score_diagnostic=score_diagnostic,
        score_descriptif=score_descriptif,
        correspondance=correspondance,
        type_erreur=type_erreur,
        elements_trouves=elements_trouves,
        elements_manques=elements_manques,
        elements_errones=elements_errones,
        commentaire=commentaire,
        model="neuro-pipeline-v3",
    )


def _explain_validant(vd) -> str:
    mt = getattr(vd, "match_type", "")
    pct = getattr(vd, "score_pct", 0.0)
    base = {
        "requires": "critères partiels reconnus",
        "qualifier": "qualifiant proche reconnu",
        "support": "élément de support reconnu",
        "excluded": "écarté par un concept incompatible",
        "missed": "non identifié dans la réponse",
    }.get(mt, "non identifié")
    return f"{base} ({pct:.0f}%)" if pct else base


def _classify(score: int, found: int, attendus: int):
    """(correspondance, type_erreur) alignés sur l'enum du frontend."""
    if attendus and found >= attendus and score >= 85:
        return "exacte", "aucune"
    if score >= 70:
        return "acceptable", "incomplet"
    if score >= 40:
        return "partielle", "incomplet"
    return "incorrecte", "etudiant"


def _verdict(score: int, found: int, attendus: int) -> str:
    if attendus and found >= attendus and score >= 85:
        return "Diagnostic principal identifié — très bonne lecture."
    if score >= 70:
        return "Bonne interprétation, diagnostic principal reconnu."
    if score >= 40:
        return "Réponse partielle : le diagnostic n'est pas complet."
    return "Le diagnostic principal attendu n'a pas été identifié."


def _guess_retained_dx(report) -> str:
    for vd in getattr(report, "validant_details", []):
        if vd.found:
            return vd.golden_name or vd.golden_id
    # sinon : concept extrait present de plus fort poids clinique
    concepts = [c for c in getattr(report, "concepts_extraits", [])
                if getattr(c, "ontology_id", "NONE") != "NONE"
                and getattr(c, "statut", "present") == "present"]
    if concepts:
        return concepts[0].concept_name or concepts[0].terme_brut
    return "aucun"


def _build_comment(report, score: int, found: int, attendus: int) -> str:
    """Commentaire markdown : feedback pédagogique GPT si présent, sinon synthèse."""
    fb = getattr(report, "feedback_pedagogique", None)
    if fb is not None and getattr(fb, "texte", "") and not getattr(fb, "erreur", None):
        return fb.texte

    # Synthèse déterministe (repli) — jamais vide.
    lines = []
    if attendus:
        lines.append(f"**Validants reconnus : {found}/{attendus}.**")
    trouves = [vd.golden_name for vd in getattr(report, "validant_details", []) if vd.found]
    manques = [vd.golden_name for vd in getattr(report, "validant_details", []) if not vd.found]
    if trouves:
        lines.append("✓ Bien identifié : " + ", ".join(trouves) + ".")
    if manques:
        lines.append("◐ À compléter : " + ", ".join(manques) + ".")
    if score >= 85:
        lines.append("Excellente réponse, continue ainsi.")
    elif score >= 50:
        lines.append("Réponse partielle : nomme explicitement le diagnostic principal.")
    else:
        lines.append("Reprends la démarche : rythme, fréquence, axe, conduction, "
                     "repolarisation, puis conclus par le diagnostic.")
    return "\n\n".join(lines)
