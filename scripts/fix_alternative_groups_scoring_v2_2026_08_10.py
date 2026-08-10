#!/usr/bin/env python3
"""
fix_alternative_groups_scoring_v2_2026_08_10.py — Corrige la cohérence des
critères role="alternative" dans data/scoring_v2_review.json (75 cas), suite
à l'audit du 2026-08-10 qui a trouvé 17 cas où alternative_group était null
(erreur de structure empêchant tout futur moteur de savoir quels critères
sont liés).

Décisions validées avec l'expert (session du 2026-08-10) :

PATTERN A — concept générique alternative <-> concept spécifique déjà
"required" (même diagnostic, niveau de précision différent). On NE démote
PAS en "optional" (ça perdrait le lien sémantique et risquerait de dupliquer
un commentaire dans le futur retour pédagogique) : on GARDE role="alternative"
et on relie les deux critères par un alternative_group commun + group_logic
"ANY", pour qu'un futur moteur puisse déduire "si le critère required est
validé, l'alternatif est considéré comme couvert aussi" sans le compter
deux fois.
    Cas 9  : BLOC_DE_BRANCHE_DROIT <-> BLOC_DE_BRANCHE_DROIT_COMPLET
    Cas 13 : BLOC_DE_BRANCHE_GAUCHE <-> BLOC_DE_BRANCHE_GAUCHE_COMPLET
    Cas 41 : FLUTTER_ATRIAL_ANTIHORAIRE <-> FLUTTER_DROIT_TYPIQUE
    Cas 51 : TACHYCARDIE_VENTRICULAIRE_POLYMORPHE <-> TORSADE_DE_POINTES
    Cas 50 : TACHYCARDIE_VENTRICULAIRE_POLYMORPHE <-> FIBRILLATION_VENTRICULAIRE
             (reclassé pattern A : diagnostic alternatif à part entière)

PATTERN B — vrai diagnostic différentiel entre 2 hypothèses cliniques
distinctes (toutes deux déjà "required" par ailleurs) : création d'un
alternative_group OR, group_logic="ANY", sans changer les rôles.
    Cas 21 : BLOC_SINO_ATRIAL <-> DYSFONCTION_SINUSALE
             + BLOC_SINO_ATRIAL passe expected_status="hypothesis_acceptable"
             (le libellé dit "possible, sans nécessité de trancher")
    Cas 46 : TACHYCARDIE_VENTRICULAIRE <-> TJ_ANTIDROMIQUE_UTILISANT_UNE_VOIE_ACCESSOIRE
    Cas 73 : TACHYCARDIE_VENTRICULAIRE <-> HYPERKALIEMIE

PATTERN C — reformulation/preuve à l'appui d'un diagnostic déjà couvert
ailleurs (pas un diagnostic concurrent) : repasse role="optional".
    Cas 5  : ONDE_P_AMPLE
    Cas 6  : INDICE_DE_SOKOLOW__35_MM
    Cas 29 : REPONSE_VENTRICULAIRE_LENTE
    Cas 55 : MIROIR

CAS PARTICULIERS :
    Cas 27 : HYPERKALIEMIE — reste "required" (étiologie à mentionner) mais
             expected_status passe à "hypothesis_acceptable" (évoquée comme
             cause probable, pas certaine à 100% dans le texte de référence).
    Cas 43 : TJ_ORTHODROMIQUE_UTILISANT_UNE_VOIE_ACCESSOIRE — passe de
             "alternative" à "required" : c'est la conclusion diagnostique
             finale du cas, pas une alternative parmi d'autres.
    Cas 31 : MALADIE_RYTHMIQUE_OREILLETTE — passe de "alternative" à
             "required" : c'est un diagnostic MÉTA (synthèse des 2 tracés),
             au même titre que FIBRILLATION_ATRIALE et BRADYCARDIE_SINUSALE
             (les 2 déjà "required" séparément) — les 3 sont impératifs et
             constituent le cœur de la note de ce cas (confirmé par
             l'expert, 2026-08-10). PAS un OR avec DYSFONCTION_SINUSALE
             (qui reste "optional", critère distinct et non équivalent).

DEUXIÈME PASSE (même session, 2026-08-10) — incohérences role=exclusion :
12 critères marqués role="exclusion" avaient expected_status="present" alors
que leur libellé dit explicitement "Ne pas conclure à..."/"...écarté"/
"Éliminer..." (contradiction : un critère qu'on ne doit PAS conclure doit
avoir expected_status="absent", pas "present"). Corrigés en masse (cf.
EXCLUSION_STATUS_FIXES ci-dessous) sur les cas 14, 16, 25, 26, 28, 38, 44,
47, 49 (x2), 75... SAUF 2 cas particuliers où le problème est en réalité le
"role" et non le "expected_status" :
    Cas 14 STIMULATION : le libellé ("Conclure à un ECG préoccupant...
             nécessitant hospitalisation") est une RECOMMANDATION POSITIVE,
             pas une exclusion — role passe à "required" (expected_status
             "present" reste correct tel quel).
    Cas 75 VOLTAGE_DU_QRS_NORMAL : le libellé ("Absence de microvoltage
             précordial : QRS > 10mm en V3-V4") décrit un vrai finding
             PRÉSENT (contraste avec MICROVOLTAGE déjà required sur les
             dérivations périphériques — pattern classique de l'amylose,
             cf. les autres critères du cas) — role passe à "optional"
             (descripteur de soutien, expected_status "present" reste
             correct).
    Cas 10 : BLOC_BIFASCICULAIRE — passe à "optional" : c'est une synthèse
             de 2 critères déjà "required" (BBD complet + hémibloc antérieur
             gauche), pas un vrai diagnostic concurrent (pas d'alternative_group
             pertinent, un simple "optional" suffit à documenter que c'est une
             reformulation valorisée mais non bloquante).

Ne touche jamais cases_golden.json / scoring_config.json (V1, en production).

Usage :
    python scripts/fix_alternative_groups_scoring_v2_2026_08_10.py            # dry-run
    python scripts/fix_alternative_groups_scoring_v2_2026_08_10.py --write    # applique
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
PATH = os.path.join(ROOT, "data", "scoring_v2_review.json")


def backup(path: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = f"{path}.bak_{ts}"
    shutil.copy2(path, dst)
    return dst


# --- PATTERN A + reclassés : paires (concept alternative, concept required lié) ---
PAIR_GROUPS = {
    "9": [("BLOC_DE_BRANCHE_DROIT", "BLOC_DE_BRANCHE_DROIT_COMPLET", "case_9_bbd")],
    "13": [("BLOC_DE_BRANCHE_GAUCHE", "BLOC_DE_BRANCHE_GAUCHE_COMPLET", "case_13_bbg")],
    "41": [("FLUTTER_ATRIAL_ANTIHORAIRE", "FLUTTER_DROIT_TYPIQUE", "case_41_flutter")],
    "51": [("TACHYCARDIE_VENTRICULAIRE_POLYMORPHE", "TORSADE_DE_POINTES", "case_51_tv_poly")],
    "50": [("TACHYCARDIE_VENTRICULAIRE_POLYMORPHE", "FIBRILLATION_VENTRICULAIRE", "case_50_tv_poly_fv")],
    # Pattern B : vrais différentiels
    "21": [("BLOC_SINO_ATRIAL", "DYSFONCTION_SINUSALE", "case_21_diag")],
    "46": [("TACHYCARDIE_VENTRICULAIRE", "TJ_ANTIDROMIQUE_UTILISANT_UNE_VOIE_ACCESSOIRE", "case_46_diag")],
    "73": [("TACHYCARDIE_VENTRICULAIRE", "HYPERKALIEMIE", "case_73_diag")],
}

# Cas 21 : le critère BLOC_SINO_ATRIAL doit aussi passer en hypothesis_acceptable
EXPECTED_STATUS_OVERRIDES = {
    ("21", "BLOC_SINO_ATRIAL"): "hypothesis_acceptable",
    ("27", "HYPERKALIEMIE"): "hypothesis_acceptable",
}

# --- PATTERN C : repasse en "optional" ---
DEMOTE_TO_OPTIONAL = {
    ("5", "ONDE_P_AMPLE"),
    ("6", "INDICE_DE_SOKOLOW__35_MM"),
    ("29", "REPONSE_VENTRICULAIRE_LENTE"),
    ("55", "MIROIR"),
    ("10", "BLOC_BIFASCICULAIRE"),
}

# --- Cas particuliers : changement de role direct ---
ROLE_OVERRIDES = {
    ("27", "HYPERKALIEMIE"): "required",  # déjà required, inchangé mais explicite
    ("43", "TJ_ORTHODROMIQUE_UTILISANT_UNE_VOIE_ACCESSOIRE"): "required",
    ("31", "MALADIE_RYTHMIQUE_OREILLETTE"): "required",  # diag méta, pas une alternative
    # Deuxième passe (exclusion mal posée, cf. docstring) :
    ("14", "STIMULATION"): "required",   # recommandation positive, pas une exclusion
    ("75", "VOLTAGE_DU_QRS_NORMAL"): "optional",  # descripteur de soutien, pas une exclusion
}

# --- Deuxième passe : exclusion + expected_status=present -> absent ---
# (concepts qu'on ne doit PAS conclure -> le statut attendu doit être "absent")
EXCLUSION_STATUS_FIXES = [
    ("14", "BAV_COMPLET"),
    ("16", "HYPERTROPHIE_VENTRICULAIRE_GAUCHE"),
    ("16", "HYPERTROPHIE_VENTRICULAIRE_DROITE"),
    ("25", "DYSFONCTION_SINUSALE"),
    ("26", "BAV_COMPLET"),
    ("28", "DYSFONCTION_SINUSALE"),
    ("38", "BAV_COMPLET"),
    ("44", "TACHYCARDIE_VENTRICULAIRE"),
    ("47", "CAPTURE_SUPRAVENTRICULAIRE"),
    ("49", "TACHYCARDIE_VENTRICULAIRE"),
    ("49", "TORSADE_DE_POINTES"),
]


def find_criterion(crits, concept_id):
    for cr in crits:
        if cr["concept_id"] == concept_id:
            return cr
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    data = json.load(open(PATH, encoding="utf-8"))
    cases = data["cases"]
    changes = []

    # 1. Groupes (pattern A + B)
    for case_id, pairs in PAIR_GROUPS.items():
        crits = cases[case_id]["expert_1"]["criteria"]
        for alt_concept, req_concept, group_name in pairs:
            alt_cr = find_criterion(crits, alt_concept)
            req_cr = find_criterion(crits, req_concept)
            if not alt_cr or not req_cr:
                print(f"⚠️  Cas {case_id}: {alt_concept} ou {req_concept} introuvable — vérifier manuellement.")
                continue
            alt_cr["alternative_group"] = group_name
            alt_cr["group_logic"] = "ANY"
            req_cr["alternative_group"] = group_name
            req_cr["group_logic"] = "ANY"
            changes.append(f"Cas {case_id}: groupe '{group_name}' = {{{alt_concept} (alternative), {req_concept} ({req_cr['role']})}}")

    # 2. Overrides expected_status
    for (case_id, concept_id), new_status in EXPECTED_STATUS_OVERRIDES.items():
        crits = cases[case_id]["expert_1"]["criteria"]
        cr = find_criterion(crits, concept_id)
        if cr:
            old = cr["expected_status"]
            if old != new_status:
                cr["expected_status"] = new_status
                changes.append(f"Cas {case_id}: {concept_id} expected_status {old!r} -> {new_status!r}")

    # 3. Démotions en optional (pattern C)
    for case_id, concept_id in DEMOTE_TO_OPTIONAL:
        crits = cases[case_id]["expert_1"]["criteria"]
        cr = find_criterion(crits, concept_id)
        if cr:
            old_role = cr["role"]
            cr["role"] = "optional"
            cr["alternative_group"] = None
            if old_role != "optional":
                changes.append(f"Cas {case_id}: {concept_id} role {old_role!r} -> 'optional'")

    # 4. Overrides de role directs (cas particuliers)
    for (case_id, concept_id), new_role in ROLE_OVERRIDES.items():
        crits = cases[case_id]["expert_1"]["criteria"]
        cr = find_criterion(crits, concept_id)
        if cr:
            old_role = cr["role"]
            cr["role"] = new_role
            if old_role == "alternative" and new_role != "alternative":
                cr["alternative_group"] = None
            if old_role != new_role:
                changes.append(f"Cas {case_id}: {concept_id} role {old_role!r} -> {new_role!r}")

    # 5. Deuxième passe : exclusion + expected_status=present -> absent
    for case_id, concept_id in EXCLUSION_STATUS_FIXES:
        crits = cases[case_id]["expert_1"]["criteria"]
        cr = find_criterion(crits, concept_id)
        if not cr:
            print(f"⚠️  Cas {case_id}: {concept_id} introuvable — vérifier manuellement.")
            continue
        if cr["role"] != "exclusion":
            print(f"⚠️  Cas {case_id}: {concept_id} n'est plus 'exclusion' (role={cr['role']!r}) — skip.")
            continue
        old = cr["expected_status"]
        if old != "absent":
            cr["expected_status"] = "absent"
            changes.append(f"Cas {case_id}: {concept_id} expected_status {old!r} -> 'absent' (cohérence avec role=exclusion)")

    print("\n".join(f"- {c}" for c in changes))
    print(f"\nTotal: {len(changes)} changement(s).")

    if not args.write:
        print("\n[DRY-RUN] Aucun fichier écrit. Relancer avec --write pour appliquer.")
        return

    b = backup(PATH)
    print(f"Backup créé: {b}")
    data["updated"] = datetime.now().isoformat()
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("✅ Fichier mis à jour.")


if __name__ == "__main__":
    main()
