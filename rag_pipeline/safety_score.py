# -*- coding: utf-8 -*-
"""
safety_score.py — P4.1 : score de sécurité clinique (SafetyEvent → 0-100).
===========================================================================
Design : docs/P4.1_design_adequation_securite_2026_08_11.md (validé expert).

Principe : deux mesures PRIMAIRES exposées séparément —
  • score_adequation : couverture du golden (score V3, calculé ailleurs) ;
  • score_securite   : part de 100 diminuée par les fautes de sécurité.
Le score global n'est plus qu'une combinaison produit :
    score = round(adequation × securite / 100)

Ce module est le CONSOMMATEUR du format pivot `SafetyEvent` : les détecteurs
(`neuro_grader` aujourd'hui : exclusions golden + cohérence P4.3b ; le juge
contextuel P4.3c demain) PRODUISENT des événements, et `compute_safety_score`
est la seule fonction qui les transforme en nombre. P4.1 ne connaît donc pas
P4.3b directement — ajouter une source (`llm_contextual_judge`) ou passer un
status à `waived` ne modifie jamais le calcul.

Règles de calcul :
  • seuls les événements `status == "active"` pèsent ;
  • DÉDUPLICATION obligatoire : une même erreur clinique détectée par
    plusieurs canaux (ex. exclusion golden ET contradiction HARD sur les
    mêmes concepts) n'est pénalisée qu'UNE fois, avec la pénalité la plus
    sévère. Clé : frozenset(concept_ids). Tous les événements restent
    conservés pour la traçabilité — seule la pénalité est dédupliquée ;
  • score_securite = max(0, 100 - somme des pénalités dédupliquées).

Les pénalités nominales vivent dans `scoring_thresholds.py` (valeurs de
transition NON calibrées, à ré-estimer en P4.2).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

# Statuts d'un SafetyEvent
STATUS_ACTIVE = "active"
STATUS_OVERRIDDEN = "overridden"
STATUS_WAIVED = "waived"                      # futur P4.3c (juge contextuel)
STATUS_DATA_INCONSISTENCY = "data_inconsistency"


@dataclass
class SafetyEvent:
    """Un fait de sécurité clinique détecté dans la réponse de l'étudiant.

    Format pivot P4.1/P4.3c : les détecteurs produisent, compute_safety_score
    consomme. `penalty` est la pénalité NOMINALE (appliquée seulement si
    status == "active", après déduplication).
    """
    kind: str                     # golden_exclusion_A | golden_exclusion_B
    #                             # | hard_contradiction | default_conflict
    #                             # | excluded_match | data_inconsistency
    severity: str                 # error | warning | info
    concept_ids: Tuple[str, ...]
    source: str                   # golden_exclusion | symbolic | llm_contextual_judge
    status: str                   # active | overridden | waived | data_inconsistency
    penalty: int
    reason: str = ""
    arbitration: Optional[str] = None   # futur P4.3c : verdict du juge
    confidence: Optional[float] = None  # futur P4.3c

    def to_dict(self) -> dict:
        d = asdict(self)
        d["concept_ids"] = list(self.concept_ids)
        return d


def compute_safety_score(events: List[SafetyEvent]) -> int:
    """score_securite = max(0, 100 - somme des pénalités dédupliquées).

    Seuls les événements ACTIVE pèsent. Une même erreur clinique (même
    ensemble de concepts) n'est comptée qu'une fois, à la pénalité MAX.
    """
    by_key: Dict[frozenset, int] = {}
    for ev in events:
        if ev.status != STATUS_ACTIVE or ev.penalty <= 0:
            continue
        key = frozenset(ev.concept_ids)
        by_key[key] = max(by_key.get(key, 0), ev.penalty)
    return max(0, 100 - sum(by_key.values()))


def combine_scores(score_adequation: int, score_securite: int) -> int:
    """Score global = produit explicite des deux mesures primaires.

    Remplace les min() d'écrêtage : gradue au lieu d'écraser (adéquation 40
    + faute grave ≠ adéquation 100 + même faute).

    Arrondi demi-supérieur (12.5 → 13) et non l'arrondi bancaire de round()
    (12.5 → 12) : plus prévisible pour une note, et jamais défavorable à
    l'étudiant sur le demi-point.
    """
    return int(score_adequation * score_securite / 100.0 + 0.5)
