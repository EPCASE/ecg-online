"""Validateur du schéma scoring_v2 (P1.1 / P1.2).

Usage:
    python scripts/validate_scoring_v2.py data/scoring_pilot_v2.json

Vérifie, pour chaque critère de chaque cas pilote :
- présence des champs obligatoires ;
- valeurs autorisées (enums) ;
- cohérence group_logic / group_min_n ;
- cohérence alternative_group (si role == "alternative", alternative_group
  ne doit pas être null) ;
- unicité des criterion_id.

Ne dépend d'aucune librairie externe (pas de jsonschema requis) pour rester
utilisable immédiatement sans installation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED_FIELDS = [
    "criterion_id", "concept_id", "label", "role", "expected_status",
    "importance", "error_severity", "group_logic", "expert_confidence",
    "evidence_source",
]

ENUMS = {
    "role": {"required", "alternative", "optional", "exclusion"},
    "expected_status": {"present", "absent", "hypothesis_acceptable"},
    "importance": {"major", "intermediate", "minor"},
    "error_severity": {"none", "minor", "major", "dangerous"},
    "group_logic": {"ANY", "ALL", "AT_LEAST_N"},
    "expert_confidence": {"high", "medium", "low"},
    "evidence_source": {
        "expert_consensus", "single_expert", "gpt_assisted_reviewed", "literature",
        # Ajoutés le 2026-08-10 : origines réelles utilisées par la migration
        # bareme_v1 -> scoring_v2 (scripts/merge_bareme_into_pilot_v2.py,
        # scripts/bootstrap_pilot_v2_all_cases.py), absentes de l'enum initial
        # P1.1 alors que 483 critères sur les 75 cas les utilisent déjà.
        "bareme_v1_migre", "bareme_v1_valide",
    },
    "minimum_specificity": {"exact_only", "child_ok", "parent_ok", "any_related"},
}


def validate_criterion(crit: dict, case_id: str, idx: int, errors: list[str]) -> None:
    where = f"case {case_id}, critère #{idx} (criterion_id={crit.get('criterion_id')!r})"

    for field in REQUIRED_FIELDS:
        if field not in crit:
            errors.append(f"{where}: champ obligatoire manquant '{field}'")

    for field, allowed in ENUMS.items():
        if field in crit and crit[field] not in allowed:
            errors.append(
                f"{where}: valeur invalide pour '{field}' = {crit[field]!r} "
                f"(attendu parmi {sorted(allowed)})"
            )

    if crit.get("group_logic") == "AT_LEAST_N" and not crit.get("group_min_n"):
        errors.append(f"{where}: group_logic=AT_LEAST_N nécessite group_min_n renseigné")

    if crit.get("role") == "alternative" and not crit.get("alternative_group"):
        errors.append(f"{where}: role=alternative nécessite alternative_group non nul")

    if crit.get("role") == "exclusion" and crit.get("expected_status") != "absent":
        errors.append(
            f"{where}: role=exclusion devrait normalement avoir expected_status=absent "
            f"(trouvé: {crit.get('expected_status')!r}) — vérifier la logique clinique"
        )


def validate_file(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    seen_ids: set[str] = set()

    cases = data.get("cases", data)
    for case_id, criteria in cases.items():
        if not isinstance(criteria, list):
            errors.append(f"case {case_id}: attendu une liste de critères")
            continue
        for idx, crit in enumerate(criteria, start=1):
            validate_criterion(crit, case_id, idx, errors)
            cid = crit.get("criterion_id")
            if cid:
                if cid in seen_ids:
                    errors.append(f"case {case_id}: criterion_id dupliqué '{cid}'")
                seen_ids.add(cid)

    if errors:
        print(f"❌ {len(errors)} erreur(s) trouvée(s) dans {path.name} :\n")
        for e in errors:
            print(" -", e)
        return 1

    n_cases = len(cases)
    n_criteria = sum(len(v) for v in cases.values() if isinstance(v, list))
    print(f"✅ {path.name} valide : {n_cases} cas, {n_criteria} critères, 0 erreur.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(validate_file(Path(sys.argv[1])))
