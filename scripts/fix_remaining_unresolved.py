#!/usr/bin/env python3
"""Corrige les concept_id invalides restants + comble les labels vides des
critères ajoutés manuellement, suite à la relecture complète du 2026-08-09."""
import json
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
REVIEW_PATH = os.path.join(DATA, "scoring_v2_review.json")

rev = json.load(open(REVIEW_PATH, encoding="utf-8"))


def find(cid, crit_id):
    for c in rev["cases"][cid]["expert_1"]["criteria"]:
        if c["criterion_id"] == crit_id:
            return c
    raise KeyError(f"{cid}/{crit_id} introuvable")


FIXES = [
    ("11", "case_11_bav_complet", {"label": "Contexte de syncopes : risque de BAV complet infrahissien/paroxystique"}),
    ("11", "case_11_nouveau_mslopudl", {"label": "Fréquence cardiaque normale", "comment": "Ajout manuel du relecteur (label manquant)."}),
    ("14", "case_14_nouveau_msloruii", {"concept_id": "BLOC_DE_BRANCHE_ALTERNANT",
        "label": "Alternance bloc de branche droit / bloc de branche gauche sur les tracés successifs",
        "comment": "Concept BLOC_DE_BRANCHE_ALTERNANT créé dans l'ontologie le 2026-08-09."}),
    ("14", "case_14_nouveau_mslos9gq", {"label": "Bloc de branche gauche (second tracé de l'alternance)",
        "comment": "Ajout manuel du relecteur (label manquant)."}),
    ("14", "case_14_nouveau_mslosy1t", {"label": "Ne pas conclure à un BAV complet (le trouble est un bloc de branche alternant, pas un BAV)",
        "comment": "Ajout manuel du relecteur (label manquant)."}),
    ("44", "case_44_morphologie_de_l_onde_p_non_sinusale", {"concept_id": "ONDE_P_RETROGRADE",
        "comment": "Concept ONDE_P_RETROGRADE créé dans l'ontologie le 2026-08-09."}),
    ("44", "case_44_qrs_fins", {"concept_id": "TACHYCARDIE_VENTRICULAIRE",
        "comment": "Correction typo concept_id (TACHYCARDIE_VENTIRCULAIRE -> TACHYCARDIE_VENTRICULAIRE)."}),
    ("47", "case_47_onde_p", {"concept_id": "ABSENCE_D_ONDE_P",
        "comment": "Correction concept_id (ABSENCE_ONDE_P -> ABSENCE_D_ONDE_P, nom exact de l'ontologie)."}),
    ("47", "case_47_nouveau_mslt7s84", {"concept_id": "CAPTURE_SUPRAVENTRICULAIRE",
        "label": "Absence de complexe de capture supraventriculaire",
        "comment": "Correction concept_id (CAPTURE_VENTRICULAIRE inexistant -> CAPTURE_SUPRAVENTRICULAIRE, concept réel le plus proche)."}),
    ("49", "case_49_nouveau_mslt9yo2", {"concept_id": "TORSADE_DE_POINTES",
        "label": "Ne pas conclure à une torsade de pointes",
        "comment": "Correction typo concept_id (TORSADE_DE_POINTE -> TORSADE_DE_POINTES)."}),
    ("53", "case_53_nouveau_msltfot4", {"concept_id": "S1Q3",
        "label": "Aspect S1Q3 (McGinn-White), signe évocateur de cœur pulmonaire aigu",
        "comment": "Concept S1Q3 créé dans l'ontologie le 2026-08-09."}),
    ("54", "case_54_nouveau_msltgwpr", {"concept_id": "S1Q3",
        "label": "Aspect S1Q3T3 (McGinn-White), signe évocateur de cœur pulmonaire aigu",
        "comment": "Concept S1Q3 créé dans l'ontologie le 2026-08-09."}),
    ("55", "case_55_nouveau_msltivks", {"label": "Absence d'image en miroir (diffus, non systématisé)",
        "comment": "Ajout manuel du relecteur (label manquant)."}),
    ("55", "case_55_nouveau_msltj8ru", {"concept_id": "SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_AVEC_SUS_DECALAGE_DU_SEGMENT_ST",
        "label": "Ne pas conclure à un SCA ST+ (sus-décalage diffus non systématisé, pas de miroir)",
        "comment": "Correction concept_id (SYNDROME_CORONARIEN générique inexistant -> concept réel SCA ST+)."}),
    ("60", "case_60_conduction", {"concept_id": "ONDE_P_RETROGRADE",
        "comment": "Concept ONDE_P_RETROGRADE créé dans l'ontologie le 2026-08-09 (correction typo ONDE_P_RETOGRADE)."}),
    ("65", "case_65_nouveau_mslty5jz", {"concept_id": "FLUTTER_ATRIAL",
        "label": "Ne pas conclure à un flutter atrial",
        "comment": "Concept FLUTTER_ATRIAL (générique) créé dans l'ontologie le 2026-08-09."}),
    ("73", "case_73_nouveau_mslu5k4s", {"concept_id": "TACHYCARDIE_VENTRICULAIRE",
        "label": "Diagnostic différentiel : tachycardie ventriculaire (à écarter, QRS larges liés à l'hyperkaliémie)",
        "comment": "Correction typo concept_id (TACHYDARDIE_VENTRICULAIRE -> TACHYCARDIE_VENTRICULAIRE)."}),
]

for cid, crit_id, updates in FIXES:
    c = find(cid, crit_id)
    c.update(updates)
    print(f"[case {cid}] {crit_id} -> {updates}")

json.dump(rev, open(REVIEW_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("\nWritten.")
