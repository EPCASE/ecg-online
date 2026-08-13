# -*- coding: utf-8 -*-
"""P4.2 point b — fix cas 14 (arbitrage expert 2026-08-13).

« pour le cas 14 : bloc alternant, et mettre en alternative BBD + BBG complet »

1. cases_golden.json : le label validant « Décrire l'alternance BBD/BBG… »
   passe de BLOC_DE_BRANCHE (parent générique — créditait un simple BBG,
   cf. S022/S049/S139) à BLOC_DE_BRANCHE_ALTERNANT (spécifique).
2. ontology_v2.json (3 copies) : BLOC_DE_BRANCHE_ALTERNANT.requires =
   [BLOC_DE_BRANCHE_DROIT, BLOC_DE_BRANCHE_GAUCHE] → un étudiant qui nomme
   LES DEUX blocs (y compris leurs formes complètes, enfants) obtient le
   crédit plein via la logique requires ; un seul bloc → 50 %.

Backups .bak_p42_cas14. Idempotent.
"""
import json
import shutil

GOLDEN = r"c:\Users\Administrateur\bmad\ECG lecture\ecg-online\data\cases_golden.json"
ONTOS = [
    r"c:\Users\Administrateur\bmad\ECG lecture\data\ontology_v2.json",
    r"c:\Users\Administrateur\bmad\ECG lecture\rag_pipeline\data\ontology_v2.json",
    r"c:\Users\Administrateur\bmad\ECG lecture\ecg-online\rag_pipeline\data\ontology_v2.json",
]

# 1) golden cas 14
shutil.copy2(GOLDEN, GOLDEN + ".bak_p42_cas14")
with open(GOLDEN, encoding="utf-8") as f:
    g = json.load(f)
mp = g["cases"]["14"]["mapping"]
label = next(l for l in mp if l.startswith("Décrire l’alternance"))
old = mp[label]["golden_id"]
mp[label].update({
    "golden_id": "BLOC_DE_BRANCHE_ALTERNANT",
    "concept_name": "Bloc de branche alternant",
    "valide_par": "humain",
    "justification": "P4.2 2026-08-13 — le parent générique BLOC_DE_BRANCHE créditait "
                     "un simple BBG/BBD isolé (S022/S049/S139). Le validant est le bloc "
                     "ALTERNANT ; alternative BBD+BBG via requires ontologique.",
})
with open(GOLDEN, "w", encoding="utf-8") as f:
    json.dump(g, f, ensure_ascii=False, indent=2)
print(f"[golden] cas 14 : {old} → BLOC_DE_BRANCHE_ALTERNANT")

# 2) ontologie : requires sur BLOC_DE_BRANCHE_ALTERNANT
REQ = ["BLOC_DE_BRANCHE_DROIT", "BLOC_DE_BRANCHE_GAUCHE"]
for p in ONTOS:
    shutil.copy2(p, p + ".bak_p42_cas14")
    with open(p, encoding="utf-8") as f:
        onto = json.load(f)
    c = onto["concepts"]["BLOC_DE_BRANCHE_ALTERNANT"]
    before = c.get("requires")
    c["requires"] = REQ
    with open(p, "w", encoding="utf-8") as f:
        json.dump(onto, f, ensure_ascii=False, indent=2)
    print(f"[onto] {p.split(chr(92))[-3]}\\...\\ontology_v2.json : requires {before} → {REQ}")
