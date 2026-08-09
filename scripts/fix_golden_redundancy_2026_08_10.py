"""
fix_golden_redundancy_2026_08_10.py — Corrige 3 incohérences ponctuelles dans
data/cases_golden.json (golden V1, en production), suite à des signalements
étudiants (Google Sheets, feedback du 2026-08-09) :

1. Cas 25 : BAV_COMPLET marqué "present" alors que la justification GPT
   elle-même dit "risque évolutif futur" (pas un constat sur l'ECG actuel).
   Erreur d'annotation golden (confusion risque/diagnostic présent).
   -> Suppression de l'entrée.

2. Cas 41 : FLUTTER_ATRIAL_ANTIHORAIRE (role=complementaire) est redondant
   avec FLUTTER_DROIT_TYPIQUE (role=validant, déjà présent) — le sens de
   rotation est une précision du même diagnostic, pas un critère séparé.
   Signalé explicitement par l'étudiant ("doublon comme si la réponse
   attendue avait plusieurs réponses").
   -> Suppression de l'entrée FLUTTER_ATRIAL_ANTIHORAIRE.

3. Cas 49 : FIBRILLATION_ATRIALE ET TACHYCARDIE_SUPRA_VENTRICULAIRE sont
   TOUS LES DEUX marqués role=validant — double-comptage réel (le parent
   générique ne devrait pas être validant en plus du diagnostic spécifique).
   -> Rétrogradation de TACHYCARDIE_SUPRA_VENTRICULAIRE en complementaire
      dans scoring_config.json (le mapping golden reste inchangé, seul le
      rôle change).

Usage :
    python scripts/fix_golden_redundancy_2026_08_10.py --dry-run
    python scripts/fix_golden_redundancy_2026_08_10.py
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
GOLDEN_PATH = os.path.join(ROOT, "data", "cases_golden.json")
SCORING_CONFIG_PATH = os.path.join(ROOT, "data", "scoring_config.json")


def backup(path: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = f"{path}.bak_{ts}"
    shutil.copy2(path, dst)
    return dst


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(GOLDEN_PATH, encoding="utf-8") as f:
        golden = json.load(f)
    with open(SCORING_CONFIG_PATH, encoding="utf-8") as f:
        scoring_config = json.load(f)

    changes = []

    # --- 1. Cas 25 : retirer BAV_COMPLET (risque futur, pas un présent) ---
    case25 = golden["cases"]["25"]["mapping"]
    label_25 = "Risque élevé d’évolution vers BAV complet, indication de stimulateur selon le texte pédagogique"
    if label_25 in case25 and case25[label_25].get("golden_id") == "BAV_COMPLET":
        del case25[label_25]
        changes.append("Cas 25: BAV_COMPLET retiré du mapping (risque évolutif, pas un diagnostic présent).")
    else:
        print("⚠️  Cas 25: label BAV_COMPLET non trouvé tel quel — vérifier manuellement.")

    # --- 2. Cas 41 : retirer FLUTTER_ATRIAL_ANTIHORAIRE (redondant) ---
    case41 = golden["cases"]["41"]["mapping"]
    label_41 = "Origine oreillette droite, macro-réentrée passant par l’isthme cavo-tricuspide, sens antihoraire"
    if label_41 in case41 and case41[label_41].get("golden_id") == "FLUTTER_ATRIAL_ANTIHORAIRE":
        del case41[label_41]
        changes.append("Cas 41: FLUTTER_ATRIAL_ANTIHORAIRE retiré du mapping (redondant avec FLUTTER_DROIT_TYPIQUE déjà validant).")
    else:
        print("⚠️  Cas 41: label FLUTTER_ATRIAL_ANTIHORAIRE non trouvé tel quel — vérifier manuellement.")

    # Retirer aussi le rôle correspondant dans scoring_config.json (cas 41)
    roles_41 = scoring_config["cases"].get("41", {}).get("roles", {})
    if label_41 in roles_41:
        del roles_41[label_41]
        changes.append("Cas 41 (scoring_config): rôle du label FLUTTER_ATRIAL_ANTIHORAIRE retiré.")

    # --- 3. Cas 49 : rétrograder TACHYCARDIE_SUPRA_VENTRICULAIRE (double validant) ---
    roles_49 = scoring_config["cases"].get("49", {}).get("roles", {})
    label_49 = "Comprendre que les QRS larges sont liés au bloc de branche associé dans une tachycardie supraventriculaire"
    if roles_49.get(label_49) == "validant":
        roles_49[label_49] = "complementaire"
        changes.append("Cas 49: rôle de TACHYCARDIE_SUPRA_VENTRICULAIRE rétrogradé validant -> complementaire (double-comptage avec FIBRILLATION_ATRIALE).")
    else:
        print(f"⚠️  Cas 49: rôle actuel = {roles_49.get(label_49)!r} — vérifier manuellement.")

    print("\n".join(f"- {c}" for c in changes))
    print(f"\nTotal: {len(changes)} changement(s).")

    if args.dry_run:
        print("\n[DRY-RUN] Aucun fichier écrit.")
        return

    b1 = backup(GOLDEN_PATH)
    b2 = backup(SCORING_CONFIG_PATH)
    print(f"Backups créés: {b1}, {b2}")

    golden["updated"] = datetime.now().isoformat()
    with open(GOLDEN_PATH, "w", encoding="utf-8") as f:
        json.dump(golden, f, ensure_ascii=False, indent=2)

    scoring_config["updated"] = datetime.now().isoformat()
    with open(SCORING_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(scoring_config, f, ensure_ascii=False, indent=2)

    print("✅ Fichiers mis à jour.")


if __name__ == "__main__":
    main()
