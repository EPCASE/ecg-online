"""
Dérive automatiquement les champs pédagogiques `required_concepts` /
`unsafe_errors` (format curriculum, cf. `docs/ECG_Online_curriculum_75_ECG_feedback_IA_2026-07-31.md`
§11) à partir des critères déjà validés du schéma `scoring_v2`
(`data/scoring_schema_v2.json`, pilote : `data/scoring_pilot_v2.json`).

Règle de dérivation (P1.2 → curriculum) :

- `required_concepts` = concepts dont un critère a :
    role == "required" ET expected_status == "present"
  (le "ANY" d'un alternative_group est aplati : tous les concepts du
  groupe sont candidats, l'auteur du parcours choisit lequel citer si
  besoin d'un intitulé unique).

- `unsafe_errors` = concepts dont un critère a :
    role == "exclusion" ET error_severity in ("major", "dangerous")
  (les exclusions de sévérité "none"/"minor" ne sont PAS remontées :
  ce sont des nuances de scoring, pas des erreurs dangereuses au sens
  pédagogique du curriculum).

Usage :
    python scripts/derive_curriculum_objectives.py [chemin_pilote.json]

Sortie : JSON sur stdout, un objet par cas :
{
  "<case_id>": {
    "required_concepts": [...],
    "unsafe_errors": [...],
    "source_criteria": {"required_concepts": [...criterion_id...],
                         "unsafe_errors": [...criterion_id...]}
  },
  ...
}

Ce script ne modifie aucun fichier existant. Il ne fait qu'exposer,
sous forme dérivée, ce qui existe déjà dans le golden de scoring — il
n'invente aucun contenu pédagogique nouveau. Les objectifs narratifs
("objective", "phase", indices) restent de la responsabilité humaine
(cf. Phase 2 du curriculum, §12).
"""

import json
import sys
from pathlib import Path

DANGEROUS_EXCLUSION_SEVERITIES = {"major", "dangerous"}


def derive_case(criteria: list[dict]) -> dict:
    required_concepts: list = []
    unsafe_errors: list = []
    req_criteria: list = []
    unsafe_criteria: list = []

    for crit in criteria:
        role = crit.get("role")
        concept_id = crit.get("concept_id")
        if role == "required" and crit.get("expected_status") == "present":
            if concept_id not in required_concepts:
                required_concepts.append(concept_id)
                req_criteria.append(crit.get("criterion_id"))
        elif role == "exclusion" and crit.get("error_severity") in DANGEROUS_EXCLUSION_SEVERITIES:
            if concept_id not in unsafe_errors:
                unsafe_errors.append(concept_id)
                unsafe_criteria.append(crit.get("criterion_id"))

    return {
        "required_concepts": required_concepts,
        "unsafe_errors": unsafe_errors,
        "source_criteria": {
            "required_concepts": req_criteria,
            "unsafe_errors": unsafe_criteria,
        },
    }


def derive_file(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases", data)
    return {case_id: derive_case(criteria) for case_id, criteria in cases.items()}


def main() -> None:
    default_path = Path(__file__).resolve().parent.parent / "data" / "scoring_pilot_v2.json"
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path
    result = derive_file(path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
