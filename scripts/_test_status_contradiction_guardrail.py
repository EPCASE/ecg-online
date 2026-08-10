# -*- coding: utf-8 -*-
"""
_test_status_contradiction_guardrail.py — Test de non-régression pour le
garde-fou déterministe anti-contradiction de statut ajouté le 2026-08-10
dans `rag_pipeline/pedagogical_feedback.py`
(`_detect_status_contradiction` / `_neutralize_status_contradiction`).

Contexte : un audit du challenge set P3.3 a mesuré que ~13% des
générations de feedback pédagogique sur des concepts crédités via un
match_type indirect (qualifier/requires/support) produisaient une
contradiction de formulation ("mentionné explicitement" ET "sans le
nommer explicitement" pour un même concept), sans que le juge LLM de
validation clinique existant ne la détecte (son périmètre cible les
inventions cliniques non fondées par le cours, pas ce type précis
d'incohérence). Voir `docs/P3.3_challenge_set_results_2026_08_10.md`.

Ce test vérifie :
1. Le détecteur (`_detect_status_contradiction`) reconnaît correctement
   un texte contradictoire (positif) et ne déclenche pas de faux positif
   sur un texte cohérent (négatif).
2. Le pipeline complet (génération réelle de feedback sur les items du
   challenge set connus pour être à risque) ne produit plus AUCUNE
   contradiction résiduelle dans le texte final, sur un nombre de runs
   suffisant pour être significatif (protège contre une régression
   future du correctif ou du prompt système).

Usage :
    python scripts/_test_status_contradiction_guardrail.py
"""
from __future__ import annotations

import json
import os
import sys

ROOT = r"c:\Users\Administrateur\bmad\ECG lecture"
sys.path.insert(0, os.path.join(ROOT, "ecg-online"))
sys.path.insert(0, os.path.join(ROOT, "rag_pipeline"))

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, "ecg-online", ".env"))

from app import golden_config
from candidate_report import generate_candidate_report
import pedagogical_feedback as pf

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")
CHALLENGE_PATH = os.path.join(DATA_DIR, "challenge_set_v1.json")

# Items connus pour produire un match_type indirect (qualifier/requires/
# support) sur au moins un concept validant — les plus à risque pour la
# contradiction de statut (cf. mesure du 2026-08-10).
AT_RISK_ITEM_IDS = [
    "chal_01_redundant_alternative_credit",
    "chal_07_diagnostic_juste_sans_justification",
    "chal_14_bav2_mobitz2_qualifier",
    "chal_16_hyperkaliemie_menacante_qualifier",
]

N_RUNS_PER_ITEM = 3  # coût LLM raisonnable pour un test de CI ponctuel


def test_detector_unit():
    """Vérifie le détecteur regex isolément, sans appel LLM."""
    contradictory = (
        "Vous avez mentionné explicitement le flutter atrial typique, "
        "cependant votre réponse évoque cet élément sans le nommer explicitement."
    )
    coherent_positive = (
        "Vous avez mentionné explicitement le flutter atrial typique, "
        "ce qui est excellent."
    )
    coherent_negative = (
        "Vous n'avez pas mentionné le flutter atrial typique dans votre réponse."
    )
    assert pf._detect_status_contradiction(contradictory) is True, \
        "Le détecteur doit reconnaître une contradiction explicite."
    assert pf._detect_status_contradiction(coherent_positive) is False, \
        "Le détecteur ne doit pas déclencher de faux positif sur un texte cohérent positif."
    assert pf._detect_status_contradiction(coherent_negative) is False, \
        "Le détecteur ne doit pas déclencher de faux positif sur un texte cohérent négatif."
    print("✅ test_detector_unit : OK")


def _run_item_once(item: dict) -> str:
    case_id = item["case_id"]
    texte = item["texte_etudiant"]
    contract = golden_config.golden_for_scorer(case_id)
    validants = contract.get("validants", [])
    descripteurs = contract.get("descripteurs", [])
    all_pts = validants + descripteurs
    report = generate_candidate_report(
        texte,
        golden_names=[p["concept_name"] for p in all_pts],
        golden_ids=[p["concept_id"] for p in all_pts],
        golden_roles=["validant"] * len(validants) + ["descripteur"] * len(descripteurs),
        diagnostic_principal=contract.get("diagnostic_principal", ""),
        with_feedback=False,
    )
    fb = pf.generate_pedagogical_feedback(report)
    return fb.texte


def test_no_residual_contradiction_end_to_end():
    """
    Vérifie, sur le pipeline complet (génération réelle), qu'aucune
    contradiction de statut ne survit dans le texte FINAL livré à
    l'étudiant, sur les items connus pour être à risque.

    Coûte des appels LLM réels — à ne pas lancer en boucle serrée, mais
    adapté à une exécution ponctuelle de non-régression (ex: avant une
    modification du prompt système ou du garde-fou).
    """
    with open(CHALLENGE_PATH, encoding="utf-8") as f:
        challenge = json.load(f)
    items = {it["id"]: it for it in challenge["items"]}

    failures = []
    total = 0
    for item_id in AT_RISK_ITEM_IDS:
        item = items[item_id]
        for i in range(N_RUNS_PER_ITEM):
            total += 1
            texte = _run_item_once(item)
            if pf._detect_status_contradiction(texte):
                failures.append((item_id, i + 1, texte))

    if failures:
        print(f"\n❌ {len(failures)}/{total} génération(s) avec contradiction résiduelle :")
        for item_id, run_n, texte in failures:
            print(f"\n--- {item_id} run {run_n} ---\n{texte}")
        raise AssertionError(
            f"{len(failures)}/{total} génération(s) contiennent encore une "
            f"contradiction de statut malgré le garde-fou déterministe — "
            f"régression détectée (cf. docs/P3.3_challenge_set_results_2026_08_10.md)."
        )

    print(f"✅ test_no_residual_contradiction_end_to_end : OK ({total} générations, 0 contradiction résiduelle)")


if __name__ == "__main__":
    test_detector_unit()
    test_no_residual_contradiction_end_to_end()
    print("\n✅ Tous les tests du garde-fou anti-contradiction sont passés.")
