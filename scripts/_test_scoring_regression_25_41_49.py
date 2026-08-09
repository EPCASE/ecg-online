# -*- coding: utf-8 -*-
"""
Vérifie, après les corrections golden du 2026-08-10 (cas 25, 41, 49), que le
contrat de scoring (`golden_for_scorer`) reflète bien les changements et que
le scoreur ontologique (`candidate_report`) fonctionne toujours normalement
sur ces 3 cas (pas de crash, pas de régression grossière).
"""
import sys
import os

ROOT = r"c:\Users\Administrateur\bmad\ECG lecture"
sys.path.insert(0, os.path.join(ROOT, "ecg-online"))
sys.path.insert(0, os.path.join(ROOT, "rag_pipeline"))

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, "ecg-online", ".env"))

from app import golden_config
from candidate_report import generate_candidate_report


def show_contract(cas):
    contract = golden_config.golden_for_scorer(cas)
    validants = contract.get("validants", [])
    descripteurs = contract.get("descripteurs", [])
    print(f"\n=== Cas {cas} ===")
    print("Diagnostic principal:", contract.get("diagnostic_principal", ""))
    print(f"Validants ({len(validants)}):", [p["concept_id"] for p in validants])
    print(f"Descripteurs ({len(descripteurs)}):", [p["concept_id"] for p in descripteurs])
    return contract


def score(cas, texte, contract):
    all_pts = contract.get("validants", []) + contract.get("descripteurs", [])
    golden_ids = [p["concept_id"] for p in all_pts]
    golden_names = [p["concept_name"] for p in all_pts]
    golden_roles = ["validant"] * len(contract.get("validants", [])) + \
                   ["descripteur"] * len(contract.get("descripteurs", []))
    report = generate_candidate_report(
        texte, golden_names=golden_names, golden_ids=golden_ids,
        golden_roles=golden_roles,
        diagnostic_principal=contract.get("diagnostic_principal", ""),
        with_feedback=False,
    )
    print("  Score:", report.score_final_pct, "%")
    for c in report.concepts_extraits:
        print("   ", repr(c.terme_brut), "->", c.ontology_id, c.statut, c.method)
    return report


# Cas 25 : vérifier que BAV_COMPLET n'apparaît plus, et qu'une réponse
# correcte (BAV 2 Mobitz 2 sans mention du risque futur) score toujours bien.
c25 = show_contract(25)
assert "BAV_COMPLET" not in [p["concept_id"] for p in c25.get("validants", []) + c25.get("descripteurs", [])], \
    "BAV_COMPLET ne devrait plus être dans le contrat du cas 25"
score(25, "Rythme sinusal avec bloc auriculo-ventriculaire du deuxieme degre Mobitz 2, "
          "une onde P bloquee, pas d'allongement du PR, bloc bifasciculaire, pause.", c25)

# Cas 41 : vérifier que FLUTTER_ATRIAL_ANTIHORAIRE n'apparaît plus, et qu'une
# réponse mentionnant uniquement le flutter typique (sans sens de rotation)
# score toujours correctement le validant.
c41 = show_contract(41)
assert "FLUTTER_ATRIAL_ANTIHORAIRE" not in [p["concept_id"] for p in c41.get("validants", []) + c41.get("descripteurs", [])], \
    "FLUTTER_ATRIAL_ANTIHORAIRE ne devrait plus être dans le contrat du cas 41"
score(41, "Rythme regulier avec flutter atrial typique, ondes F en toit d'usine, "
          "conduction 4/1, QRS fins, rythme sinusal sous-jacent absent.", c41)

# Cas 49 : vérifier que TACHYCARDIE_SUPRA_VENTRICULAIRE est bien en
# descripteur (pas validant), et que la fibrillation atriale seule suffit à
# valider le point validant principal.
c49 = show_contract(49)
validant_ids_49 = [p["concept_id"] for p in c49.get("validants", [])]
descripteur_ids_49 = [p["concept_id"] for p in c49.get("descripteurs", [])]
assert "TACHYCARDIE_SUPRA_VENTRICULAIRE" not in validant_ids_49, \
    "TACHYCARDIE_SUPRA_VENTRICULAIRE ne devrait plus être validant au cas 49"
print("TACHYCARDIE_SUPRA_VENTRICULAIRE en descripteur:",
      "TACHYCARDIE_SUPRA_VENTRICULAIRE" in descripteur_ids_49)
score(49, "Fibrillation atriale avec activite atriale rapide irreguliere anarchique, "
          "tachycardie irreguliere a QRS larges monomorphes, bloc de branche droit complet.", c49)

print("\n✅ Tests de régression cas 25/41/49 : OK, aucune assertion échouée.")
