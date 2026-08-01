"""
Valide `data/case_curriculum_map.json` (Phase 1 du curriculum, cf.
`docs/ECG_Online_curriculum_75_ECG_feedback_IA_2026-07-31.md` §12) :

- vérifie que les numéros de cas 1 à 75 apparaissent exactement une fois
  au total dans l'ensemble des parcours ;
- signale les doublons (un même `num` affecté à plusieurs parcours/phases) ;
- signale les absences (un `num` de 1 à 75 non affecté à un parcours) ;
- signale les `num` hors de la plage 1-75 (erreur de saisie) ;
- vérifie que chaque parcours a un `id` unique ;
- produit un rapport de couverture par famille clinique (croisé avec
  `data/cases.json`).

Usage :
    python scripts/validate_case_curriculum_map.py [chemin.json]
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

EXPECTED_RANGE = range(1, 76)


def load_case_families(cases_path: Path) -> dict:
    data = json.loads(cases_path.read_text(encoding="utf-8"))
    return {c["num"]: c.get("famille") for c in data["cases"]}


def validate(map_path: Path, cases_path: Path) -> int:
    data = json.loads(map_path.read_text(encoding="utf-8"))
    pathways = data.get("pathways", [])

    errors = []
    warnings = []

    # Unicité des ids de parcours
    ids = [p["id"] for p in pathways]
    id_counts = Counter(ids)
    for pid, count in id_counts.items():
        if count > 1:
            errors.append(f"id de parcours dupliqué : '{pid}' ({count} fois)")

    # Occurrences des num de cas
    occurrences = defaultdict(list)
    for p in pathways:
        for c in p.get("cases", []):
            occurrences[c["num"]].append((p["id"], c.get("phase")))

    for num, locs in occurrences.items():
        if num not in EXPECTED_RANGE:
            errors.append(f"num hors plage 1-75 : {num} (dans {locs})")
        if len(locs) > 1:
            errors.append(f"num {num} affecté à plusieurs parcours/phases : {locs}")

    missing = sorted(set(EXPECTED_RANGE) - set(occurrences.keys()))
    if missing:
        errors.append(f"{len(missing)} cas non affectés à un parcours : {missing}")

    # Couverture par famille clinique
    try:
        families = load_case_families(cases_path)
        covered_families = Counter(
            families.get(num) for num in occurrences if num in families
        )
        total_families = Counter(families.values())
        print("Couverture par famille clinique :")
        for fam, total in sorted(total_families.items()):
            got = covered_families.get(fam, 0)
            marker = "OK" if got == total else "!!"
            print(f"  [{marker}] {fam}: {got}/{total}")
    except FileNotFoundError:
        warnings.append(f"cases.json introuvable ({cases_path}), pas de croisement famille possible")

    print()
    if errors:
        print(f"❌ {len(errors)} erreur(s) :")
        for e in errors:
            print(f"  - {e}")
    else:
        print(f"✅ case_curriculum_map.json valide : {len(pathways)} parcours, "
              f"{len(occurrences)}/75 cas affectés exactement une fois.")

    for w in warnings:
        print(f"⚠️  {w}")

    return 1 if errors else 0


def main() -> None:
    default_map = Path(__file__).resolve().parent.parent / "data" / "case_curriculum_map.json"
    default_cases = Path(__file__).resolve().parent.parent / "data" / "cases.json"
    map_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_map
    sys.exit(validate(map_path, default_cases))


if __name__ == "__main__":
    main()
