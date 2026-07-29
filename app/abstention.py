"""
abstention.py — États explicites de résolution d'une correction (Palier 2).
=============================================================================
Cf. `audit_doc/FEUILLE_DE_ROUTE_ALIGNEE.md` §2 (Palier 2, semaine 1-2) et le
document de cadrage stratégique (Décision B, §4.3) : remplacer le repli
neuro→GPT silencieux par des états explicites, pour que chaque réponse
`/api/grade` porte une étiquette honnête sur la fiabilité de la correction.

États (volontairement minimal — pas de file de curation humaine pour l'instant,
`HUMAN_REVIEW` viendra quand cette file existera) :

  SUCCESS         Le pipeline neurosymbolique a produit une correction normale.
  LOW_CONFIDENCE  Correction produite (neuro ou GPT), mais un signal de faible
                  fiabilité existe (ex. peu de concepts résolus par le NER).
  FALLBACK_GPT    Repli sur le grader GPT-4o direct (pipeline neuro indisponible
                  ou non applicable à ce cas) — pas une erreur, mais une
                  correction moins déterministe/traçable que le scoring V3.
  TECHNICAL_ERROR Le pipeline (neuro OU gpt) a levé une exception / erreur API.
  ABSTAIN         Réservé (non déclenché aujourd'hui) : aucune correction fiable
                  n'a pu être produite par aucun des deux backends. Préparé
                  pour une future condition (ex. GPT échoue aussi après repli).

Ce module ne CHANGE PAS le comportement utilisateur (la correction est
toujours renvoyée) : il ne fait qu'ATTACHER une étiquette honnête + une raison,
dérivées de signaux déjà calculés ailleurs (neuro_grader.last_skip_reason(),
`Correction.error`, nombre de concepts résolus).
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .grader import Correction

# Seuil (nombre de concepts résolus par le NER) sous lequel on qualifie la
# correction de LOW_CONFIDENCE même si elle a "réussi" techniquement. Valeur
# volontairement prudente : à ajuster une fois qu'on aura des données réelles
# de distribution (Palier 3 golden 2+ experts).
MIN_RESOLVED_CONCEPTS_FOR_CONFIDENCE = 1


def classify(
    *,
    backend_used: str,
    primary_backend: str,
    corr: Optional["Correction"],
    skip_reason: Optional[str],
) -> dict:
    """Détermine l'état de résolution d'une correction pour /api/grade.

    Renvoie {status, reason, primary_backend, used_backend} — le même format
    que le champ `resolution` introduit au Palier 1, désormais enrichi d'un
    statut plus fin que juste "OK"/"FALLBACK_GPT".
    """
    reason = skip_reason
    used_backend = backend_used

    # 1) Erreur technique explicite (le backend utilisé a lui-même échoué).
    if corr is not None and getattr(corr, "error", None):
        return {
            "status": "TECHNICAL_ERROR",
            "reason": reason or str(corr.error),
            "primary_backend": primary_backend,
            "used_backend": used_backend,
        }

    # 2) Repli neuro -> GPT tracé (Palier 1) : ce n'est pas une erreur mais un
    #    changement de backend, à signaler comme tel.
    if primary_backend == "neuro" and used_backend == "gpt":
        return {
            "status": "FALLBACK_GPT",
            "reason": reason or "raison_inconnue",
            "primary_backend": primary_backend,
            "used_backend": used_backend,
        }

    # 3) Confiance faible : peu/pas de concepts résolus par le NER (signal
    #    dérivé, pas un score inventé — cf. `_concepts_for_review`).
    if corr is not None and backend_used == "neuro":
        concepts = getattr(corr, "concepts_detectes", None) or []
        nb_resolved = sum(1 for c in concepts if c.get("resolu"))
        if nb_resolved < MIN_RESOLVED_CONCEPTS_FOR_CONFIDENCE:
            return {
                "status": "LOW_CONFIDENCE",
                "reason": "peu_ou_aucun_concept_resolu_par_ner",
                "primary_backend": primary_backend,
                "used_backend": used_backend,
            }

    # 4) Cas nominal.
    return {
        "status": "SUCCESS",
        "reason": None,
        "primary_backend": primary_backend,
        "used_backend": used_backend,
    }
