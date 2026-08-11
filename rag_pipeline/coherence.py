#!/usr/bin/env python3
"""
Module cohérence — contraintes intra-réponse avec override golden
==================================================================
P4.3b (design : docs/P4.3b_design_moteur_coherence_2026_08_11.md).

Détecte les contradictions entre concepts AFFIRMÉS (statut=present) dans
une même réponse étudiante, à partir des relations déclaratives de
l'ontologie, avec levée contextuelle par le golden du cas.

Trois sources de contraintes (toutes symétriques, canonicalisées) :
    excludes               contradiction absolue        severity=error
    conflicts_by_default   incompatibilité habituelle   severity=warning
    excludes_families      famille entière exclue       severity=error

Trois états de contradiction :
    active               le conflit s'applique
    overridden           levé par le golden (DEFAULT uniquement)
    data_inconsistency   golden accepte les 2 pôles d'un HARD →
                         incohérence ontologie↔golden (alerte audit,
                         étudiant NON pénalisé)

Invariants :
    - le Python ne connaît aucune cardiologie ;
    - absence du golden ≠ fausseté (UNKNOWN ne déclenche aucun cap) ;
    - un HARD n'est JAMAIS levé silencieusement.

Auteur : BMad Team — Date : 2026-08-11
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from semantic_layer import _get_ontology_v2, normalize_key

logger = logging.getLogger(__name__)

# Statuts golden
ACCEPTED = "ACCEPTED"
FORBIDDEN = "FORBIDDEN"
UNKNOWN = "UNKNOWN"

# États de contradiction
ACTIVE = "active"
OVERRIDDEN = "overridden"
DATA_INCONSISTENCY = "data_inconsistency"


@dataclass(frozen=True)
class Constraint:
    pair: Tuple[str, str]   # tuple(sorted((A, B))) — canonique
    kind: str               # "excludes" | "conflicts_by_default" | "excludes_families"
    severity: str           # "error" | "warning"


@dataclass
class Contradiction:
    concept_a: str
    concept_b: str
    kind: str       # excludes | conflicts_by_default | excludes_families
    severity: str   # error | warning
    status: str     # active | overridden | data_inconsistency
    detail: str     # golden_accepts_both | allowed_cooccurrence
    #               # | confirmed_by_golden_forbidden | ""


# ---------------------------------------------------------------------------
# Registry (cache module-level, même pattern que _NEGATION_MAP)
# ---------------------------------------------------------------------------

_REGISTRY: Optional[Dict[Tuple[str, str], Constraint]] = None


def _canon(a: str, b: str) -> Tuple[str, str]:
    return tuple(sorted((a, b)))  # type: ignore[return-value]


def _get_all_children(concept_id: str, concepts: dict, max_depth: int = 3) -> Set[str]:
    result: Set[str] = set()

    def _walk(cid: str, depth: int):
        if depth > max_depth:
            return
        for child in concepts.get(cid, {}).get("children", []):
            if child not in result:
                result.add(child)
                _walk(child, depth + 1)

    _walk(concept_id, 0)
    return result


def build_constraint_registry() -> Dict[Tuple[str, str], Constraint]:
    """Parcourt l'ontologie une fois ; canonicalise et déduplique.

    Si une paire est déclarée à la fois excludes ET conflicts_by_default
    (erreur de données), on garde la plus sévère (excludes) + log warning.
    """
    global _REGISTRY
    if _REGISTRY is not None:
        return _REGISTRY

    onto = _get_ontology_v2()
    concepts = onto["concepts"]
    registry: Dict[Tuple[str, str], Constraint] = {}

    def _add(a: str, b: str, kind: str, severity: str):
        pair = _canon(a, b)
        prev = registry.get(pair)
        if prev is not None and prev.kind != kind:
            # conflit de déclaration : la plus sévère gagne
            if prev.severity == "error":
                logger.warning("Constraint %s déclarée %s ET %s — garde %s",
                               pair, prev.kind, kind, prev.kind)
                return
            logger.warning("Constraint %s déclarée %s ET %s — garde %s",
                           pair, prev.kind, kind, kind)
        registry[pair] = Constraint(pair=pair, kind=kind, severity=severity)

    for cid, c in concepts.items():
        for x in c.get("excludes") or []:
            _add(cid, x, "excludes", "error")
        for x in c.get("conflicts_by_default") or []:
            _add(cid, x, "conflicts_by_default", "warning")
        # excludes_families : la contrainte porte sur la famille ET ses
        # descendants (profondeur 3, même politique que scoring_v3)
        for fam in c.get("excludes_families") or []:
            _add(cid, fam, "excludes_families", "error")
            for child in _get_all_children(fam, concepts):
                _add(cid, child, "excludes_families", "error")

    _REGISTRY = registry
    logger.info("Constraint registry: %d paires", len(registry))
    return registry


def reset_registry_cache() -> None:
    """Pour les tests."""
    global _REGISTRY
    _REGISTRY = None


# ---------------------------------------------------------------------------
# Statut golden
# ---------------------------------------------------------------------------

def _extract_golden_statuses(case_golden: dict) -> Dict[str, str]:
    """Retourne {concept_id: ACCEPTED|FORBIDDEN} depuis le golden d'un cas.

    Formats supportés (V1 production) :
        case_golden["mapping"] = {label: {"golden_id": ID, "statut": "present"|"absent", ...}}
    Format V2 (role-based) :
        entrées avec "role": "exclusion" → FORBIDDEN.

    ACCEPTED = present EXPLICITE uniquement (pas de fermeture hiérarchique
    — décision expert §6.3 du design).
    """
    statuses: Dict[str, str] = {}
    mapping = case_golden.get("mapping") or {}
    for _label, entry in mapping.items():
        gid = normalize_key(entry.get("golden_id") or "")
        if not gid:
            continue
        statut = (entry.get("statut") or "present").lower()
        role = (entry.get("role") or "").lower()
        if statut == "absent" or role == "exclusion":
            statuses[gid] = FORBIDDEN
        elif statut in ("present", ""):
            # ne pas écraser un FORBIDDEN déjà posé
            statuses.setdefault(gid, ACCEPTED)
    return statuses


def golden_status(concept_id: str, case_golden: dict) -> str:
    """ACCEPTED | FORBIDDEN | UNKNOWN — UNKNOWN ≠ faux (monde ouvert)."""
    return _extract_golden_statuses(case_golden).get(
        normalize_key(concept_id), UNKNOWN)


def _allowed_cooccurrences(case_golden: dict) -> Set[Tuple[str, str]]:
    out: Set[Tuple[str, str]] = set()
    for pair in case_golden.get("allowed_cooccurrences") or []:
        if len(pair) == 2:
            out.add(_canon(normalize_key(pair[0]), normalize_key(pair[1])))
    return out


# ---------------------------------------------------------------------------
# Vérification intra-réponse
# ---------------------------------------------------------------------------

def check_response_coherence(
    found_present: Set[str],
    case_golden: Optional[dict] = None,
) -> List[Contradiction]:
    """Contradictions entre concepts AFFIRMÉS d'une même réponse.

    Args:
        found_present: IDs des concepts extraits avec statut="present"
                       UNIQUEMENT (les absent/hypothese ne contredisent rien).
        case_golden:   golden du cas (dict avec "mapping", et éventuellement
                       "allowed_cooccurrences"). None = pas de contexte
                       (tous les conflits sont évalués sans override).

    Returns:
        Liste de Contradiction (y compris overridden / data_inconsistency,
        traçables mais sans effet sur le score étudiant).
    """
    registry = build_constraint_registry()
    case_golden = case_golden or {}
    statuses = _extract_golden_statuses(case_golden)
    allowed = _allowed_cooccurrences(case_golden)

    ids = sorted(normalize_key(x) for x in found_present)
    out: List[Contradiction] = []

    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            c = registry.get(_canon(a, b))
            if c is None:
                continue
            st_a = statuses.get(a, UNKNOWN)
            st_b = statuses.get(b, UNKNOWN)
            both_accepted = st_a == ACCEPTED and st_b == ACCEPTED

            if c.kind in ("excludes", "excludes_families"):
                # HARD : jamais levé silencieusement
                if both_accepted:
                    status, detail = DATA_INCONSISTENCY, "golden_accepts_both"
                    logger.error(
                        "DATA INCONSISTENCY: golden accepte les 2 pôles du "
                        "HARD (%s, %s) — auditer ontologie/golden", a, b)
                else:
                    status, detail = ACTIVE, ""
            else:
                # DEFAULT
                if both_accepted:
                    status, detail = OVERRIDDEN, "golden_accepts_both"
                elif _canon(a, b) in allowed:
                    status, detail = OVERRIDDEN, "allowed_cooccurrence"
                elif FORBIDDEN in (st_a, st_b):
                    # la pénalité vient déjà du circuit d'exclusion golden
                    status, detail = ACTIVE, "confirmed_by_golden_forbidden"
                else:
                    status, detail = ACTIVE, ""  # warning UNKNOWN : pas de cap

            out.append(Contradiction(
                concept_a=a, concept_b=b,
                kind=c.kind, severity=c.severity,
                status=status, detail=detail,
            ))

    return out


# ---------------------------------------------------------------------------
# Formulations feedback (design §3.2)
# ---------------------------------------------------------------------------

def format_contradiction_feedback(contra: Contradiction,
                                  name_a: str = "", name_b: str = "") -> str:
    """Formulation étudiant — catégorique pour HARD, prudente pour DEFAULT."""
    a = name_a or contra.concept_a
    b = name_b or contra.concept_b
    if contra.kind in ("excludes", "excludes_families"):
        return (f"Contradiction : vous affirmez à la fois « {a} » et « {b} », "
                f"qui ne peuvent pas décrire simultanément le même élément du tracé.")
    return (f"À vérifier : vous décrivez à la fois « {a} » et « {b} ». "
            f"Cette association est habituellement incohérente s'ils décrivent "
            f"le même élément ou la même séquence du tracé, mais peut être "
            f"possible dans certains contextes.")
