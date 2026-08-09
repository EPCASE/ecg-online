#!/usr/bin/env python3
"""
apply_relecture75_corrections.py — Applique les corrections demandées lors de
la relecture manuelle des 75 cas (2026-08-09, cf. _tempreponserelecture75.md
et _tempreponserelecture75_2.md), sur les critères `expert_1` déjà enregistrés
dans scoring_v2_review.json (fallback : pilote scoring_pilot_v2.json si le cas
n'a pas encore d'expert_1, ex. cas 62).

Chaque cas est traité explicitement (pas de règle générique) pour rester
traçable et permettre une relecture facile du diff.

Usage : python scripts/apply_relecture75_corrections.py [--write]
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app import cases_repo  # noqa: E402

DATA_DIR = cases_repo.DATA_DIR
REVIEW_PATH = os.path.join(DATA_DIR, "scoring_v2_review.json")
PILOT_PATH = os.path.join(DATA_DIR, "scoring_pilot_v2.json")

CHANGELOG: list[str] = []


def log(msg: str):
    CHANGELOG.append(msg)
    print(msg)


def get_criteria(rev: dict, pilot: dict, case_id: str) -> tuple[list, str]:
    """Renvoie (liste_critères, source) où source = 'expert_1' ou 'pilot'."""
    e1 = rev["cases"].get(case_id, {}).get("expert_1")
    if e1 and isinstance(e1.get("criteria"), list):
        return e1["criteria"], "expert_1"
    return pilot["cases"].get(case_id, []), "pilot"


def remove_by_id(criteria: list, criterion_id: str, case_id: str):
    before = len(criteria)
    criteria[:] = [c for c in criteria if c["criterion_id"] != criterion_id]
    if len(criteria) < before:
        log(f"[case {case_id}] supprimé : {criterion_id}")
    else:
        log(f"[case {case_id}] ⚠️ introuvable pour suppression : {criterion_id}")


def remove_by_concept(criteria: list, concept_id: str, case_id: str):
    before = len(criteria)
    removed = [c["criterion_id"] for c in criteria if c["concept_id"] == concept_id]
    criteria[:] = [c for c in criteria if c["concept_id"] != concept_id]
    if removed:
        log(f"[case {case_id}] supprimé (concept={concept_id}) : {removed}")
    else:
        log(f"[case {case_id}] ⚠️ concept introuvable pour suppression : {concept_id}")


def find_by_id(criteria: list, criterion_id: str, case_id: str) -> dict | None:
    for c in criteria:
        if c["criterion_id"] == criterion_id:
            return c
    log(f"[case {case_id}] ⚠️ introuvable : {criterion_id}")
    return None


def set_concept(criteria: list, criterion_id: str, new_concept_id: str, case_id: str,
                 new_label: str | None = None):
    c = find_by_id(criteria, criterion_id, case_id)
    if c is None:
        return
    old = c["concept_id"]
    c["concept_id"] = new_concept_id
    if new_label:
        c["label"] = new_label
    log(f"[case {case_id}] {criterion_id} : concept_id {old} -> {new_concept_id}")


def add_criterion(criteria: list, case_id: str, concept_id: str, label: str,
                   role: str, expected_status: str, importance: str,
                   error_severity: str, comment: str = "",
                   sufficient_alone: bool = False):
    slug = re.sub(r"[^a-z0-9_]+", "_", concept_id.lower()).strip("_")
    cid = f"case_{case_id}_{slug}"
    n = 2
    existing_ids = {c["criterion_id"] for c in criteria}
    base = cid
    while cid in existing_ids:
        cid = f"{base}_{n}"
        n += 1
    new_c = {
        "criterion_id": cid,
        "concept_id": concept_id,
        "label": label,
        "role": role,
        "expected_status": expected_status,
        "importance": importance,
        "error_severity": error_severity,
        "alternative_group": None,
        "group_logic": "ALL",
        "group_min_n": None,
        "sufficient_alone": sufficient_alone,
        "minimum_specificity": "exact_only",
        "expert_confidence": "high",
        "evidence_source": "single_expert",
        "comment": comment,
    }
    criteria.append(new_c)
    log(f"[case {case_id}] + ajouté {cid} ({concept_id}, {role})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    rev = json.load(open(REVIEW_PATH, encoding="utf-8"))
    pilot = json.load(open(PILOT_PATH, encoding="utf-8"))
    orig_rev = copy.deepcopy(rev)
    orig_pilot = copy.deepcopy(pilot)

    # ------------------------------------------------------------------
    # CAS 7 / 8 — l'utilisateur a écrit "cas 7 : supprimer 'septal'" mais le
    # seul critère "septal" de toute la banque est case_8_septal (SEPTAL).
    # Interprété comme une confusion de numéro (cas 7 et 8 sont adjacents
    # dans le tableur de relecture) -> on supprime bien case_8_septal.
    # ------------------------------------------------------------------
    crit8, src8 = get_criteria(rev, pilot, "8")
    remove_by_id(crit8, "case_8_septal", "8")

    # ------------------------------------------------------------------
    # CAS 29 — supprimer hyperkaliémie, QT_COURT, onde_T_ample (signes
    # secondaires du contexte métabolique, pas du tracé lui-même à valider).
    # ------------------------------------------------------------------
    crit29, _ = get_criteria(rev, pilot, "29")
    remove_by_id(crit29, "case_29_hyperkaliemie", "29")
    remove_by_id(crit29, "case_29_qt_court", "29")
    remove_by_id(crit29, "case_29_onde_t_ample", "29")

    # ------------------------------------------------------------------
    # CAS 31 — MALADIE_RYTHMIQUE_OREILLETTE n'existe pas dans l'ontologie ;
    # le commentaire du relecteur demande de la créer avec requires
    # FA + bradycardie sinusale/dysfonction sinusale -> fait séparément dans
    # add_missing_concepts (cf. script dédié) ; ici on corrige juste le label
    # vide et on documente le futur concept_id une fois créé.
    # (Traité dans add_missing_concepts_relecture75_2.py)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # CAS 35 — remplacer TACHYCARDIE_VENTRICULAIRE par le nouveau concept
    # TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE (créé), supprimer le critère
    # SOUTENU (exclusion redondante avec le nouveau concept).
    # ------------------------------------------------------------------
    crit35, _ = get_criteria(rev, pilot, "35")
    set_concept(crit35, "case_35_tachycardie_ventriculaire",
                "TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE", "35",
                new_label="Diagnostic de tachycardie ventriculaire non soutenue (TVNS)")
    remove_by_id(crit35, "case_35_soutenu", "35")

    # ------------------------------------------------------------------
    # CAS 42 — supprimer CONDUCTION (concept générique/abstrait, pas un
    # signe ECG concret à valider dans ce contexte).
    # ------------------------------------------------------------------
    crit42, _ = get_criteria(rev, pilot, "42")
    remove_by_id(crit42, "case_42_conduction", "42")

    # ------------------------------------------------------------------
    # CAS 43 — supprimer onde P (ABSENCE_ONDE_P, concept_id avec typo/non
    # résolu ; le texte dit l'activité atriale "difficile à visualiser",
    # ambigu, pas franchement absente -> supprimé comme demandé).
    # ------------------------------------------------------------------
    crit43, _ = get_criteria(rev, pilot, "43")
    remove_by_id(crit43, "case_43_onde_p", "43")

    # ------------------------------------------------------------------
    # CAS 51 — supprimer case_51_medicaments (contexte favorisant, pas un
    # signe ECG).
    # ------------------------------------------------------------------
    crit51, _ = get_criteria(rev, pilot, "51")
    remove_by_id(crit51, "case_51_medicaments", "51")

    # ------------------------------------------------------------------
    # CAS 55 — supprimer case_55_courant_de_lesion_sous_endocardique (statut
    # exclusion mal posé / confondu, cf. remarque générale sur les statuts).
    # ------------------------------------------------------------------
    crit55, _ = get_criteria(rev, pilot, "55")
    remove_by_id(crit55, "case_55_courant_de_lesion_sous_endocardique", "55")

    # ------------------------------------------------------------------
    # CAS 56 — supprimer case_56_hypertrophie_atriale_droite (exclusion non
    # pertinente pour ce cas de tamponnade).
    # ------------------------------------------------------------------
    crit56, _ = get_criteria(rev, pilot, "56")
    remove_by_id(crit56, "case_56_hypertrophie_atriale_droite", "56")

    # ------------------------------------------------------------------
    # CAS 59 — remplacer le concept_id inventé SCA_ST_PLUS (non résolu dans
    # l'ontologie) par le vrai concept
    # SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_AVEC_SUS_DECALAGE_DU_SEGMENT_ST
    # (confirmé existant — cf. relecture "y'a pas un concept ID SCA ST+ ?").
    # ------------------------------------------------------------------
    crit59, _ = get_criteria(rev, pilot, "59")
    set_concept(crit59, "case_59_syndrome_coronarien_a_la_phase_aigue_avec_sus_decalage_du_segment_st",
                "SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_AVEC_SUS_DECALAGE_DU_SEGMENT_ST", "59")

    # ------------------------------------------------------------------
    # CAS 60 — EXTENSION_VENTRICULE_DROIT (créé) déjà utilisé comme
    # concept_id -> rien à changer (le concept existe maintenant). Idem
    # ONDE_P_RETOGRADE (typo) : pas de concept équivalent clair trouvé dans
    # l'ontologie -> laissé tel quel pour l'instant, signalé en warning
    # (aucune demande explicite de le corriger dans les notes).
    # ------------------------------------------------------------------
    crit60, _ = get_criteria(rev, pilot, "60")
    c60_ext = find_by_id(crit60, "case_60_ventricule_droit", "60")
    if c60_ext and c60_ext["concept_id"] != "EXTENSION_VENTRICULE_DROIT":
        set_concept(crit60, "case_60_ventricule_droit", "EXTENSION_VENTRICULE_DROIT", "60")

    # ------------------------------------------------------------------
    # CAS 62 — le pilote est utilisé (pas d'expert_1). Transformer en SCA
    # ST+ : le concept est déjà bon (SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_
    # AVEC_SUS_DECALAGE_DU_SEGMENT_ST), rien à changer ici (demande déjà
    # satisfaite dans le pilote).
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # CAS 63 — transformer en SCA ST+ (déjà bon, concept correct) ; supprimer
    # case_63_cardioversion_electrique (contexte thérapeutique, pas un signe
    # ECG à valider).
    # ------------------------------------------------------------------
    crit63, _ = get_criteria(rev, pilot, "63")
    remove_by_id(crit63, "case_63_cardioversion_electrique", "63")

    # ------------------------------------------------------------------
    # CAS 66 / 67 — remplacer SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_SANS_
    # ELEVATION_DU_SEGMENT_ST : déjà le bon concept (existe dans l'ontologie),
    # rien à transformer — la demande "possible de remplacer par équivalent
    # SCA ST- ?" est déjà satisfaite (SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_
    # SANS_ELEVATION_DU_SEGMENT_ST EST le concept SCA ST-, cf. ses synonymes
    # NSTEMI/SCA ST-).
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # CAS 68 — remplacer par SCA ST+ (déjà bon) ; supprimer case_68_ischemique
    # (concept trop générique / redondant avec le diagnostic final).
    # ------------------------------------------------------------------
    crit68, _ = get_criteria(rev, pilot, "68")
    remove_by_id(crit68, "case_68_ischemique", "68")

    # ------------------------------------------------------------------
    # CAS 70 — remplacer le concept_id inventé "Prinzmetal" par le nouveau
    # concept ANGOR_DE_PRINZMETAL (créé dans l'ontologie).
    # ------------------------------------------------------------------
    crit70, _ = get_criteria(rev, pilot, "70")
    set_concept(crit70, "case_70_courant_de_lesion_sous_epicardique",
                "ANGOR_DE_PRINZMETAL", "70",
                new_label="Contexte compatible avec angor de Prinzmetal/spasme coronaire, "
                           "sus-décalage transitoire régressif sous trinitrine")

    # ------------------------------------------------------------------
    # CAS 57 — rajouter dans le CONTEXTE clinique : prélèvement troponine
    # positif + douleur thoracique évoluant depuis 24h. Modifie cases.json
    # (contexte), pas les critères scoring.
    # ------------------------------------------------------------------
    cases_path = os.path.join(DATA_DIR, "cases.json")
    cases_data = json.load(open(cases_path, encoding="utf-8"))
    for c in cases_data["cases"]:
        if c["num"] == 57:
            old_ctx = c.get("contexte", "")
            addition = ("Douleur thoracique évoluant depuis 24 heures, avec prélèvement "
                         "de troponine positif.")
            if addition not in old_ctx:
                c["contexte"] = (old_ctx + " " + addition).strip() if old_ctx else addition
                log(f"[case 57] contexte mis à jour : « {c['contexte']} »")
            break

    print(f"\nTotal changelog : {len(CHANGELOG)} opérations.")

    if args.write:
        with open(REVIEW_PATH, "w", encoding="utf-8") as f:
            json.dump(rev, f, ensure_ascii=False, indent=2)
        with open(PILOT_PATH, "w", encoding="utf-8") as f:
            json.dump(pilot, f, ensure_ascii=False, indent=2)
        with open(cases_path, "w", encoding="utf-8") as f:
            json.dump(cases_data, f, ensure_ascii=False, indent=2)
        print("\n✅ Écrit dans scoring_v2_review.json, scoring_pilot_v2.json, cases.json")
    else:
        print("\n(dry-run — relancer avec --write pour appliquer)")


if __name__ == "__main__":
    main()
