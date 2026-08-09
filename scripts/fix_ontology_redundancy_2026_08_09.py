#!/usr/bin/env python3
"""Corrige 2 incohérences repérées lors de la relecture de l'ontologie du
2026-08-09 (concepts créés le même jour) :

  - FLUTTER_ATRIAL : le champ 'children' pointait vers 4 sous-types qui ont
    déjà leur propre 'parents' vers TACHYCARDIE_ATRIALE/FLUTTER_DROIT_TYPIQUE
    -> double hiérarchie incohérente. On retire 'children' (le concept reste
    utilisable seul, pour une exclusion générique). 'requires' retiré aussi
    (redondant avec son propre parent TACHYCARDIE_ATRIALE).
  - BLOC_DE_BRANCHE_ALTERNANT : 'requires'=[BLOC_DE_BRANCHE] redondant avec
    son propre parent -> retiré.
"""
import json

PATHS = [
    r"C:\Users\Administrateur\bmad\ECG lecture\data\ontology_v2.json",
    r"C:\Users\Administrateur\bmad\ECG lecture\ecg-online\rag_pipeline\data\ontology_v2.json",
    r"C:\Users\Administrateur\bmad\ECG lecture\rag_pipeline\data\ontology_v2.json",
]

COMMENT_FLUTTER = (
    "Concept générique de flutter atrial, utilisé pour une exclusion large "
    "sans choisir de sous-type précis. Les sous-types spécifiques "
    "(FLUTTER_DROIT_TYPIQUE, FLUTTER_ATRIAL_ATYPIQUE, etc.) restent "
    "rattachés à TACHYCARDIE_ATRIALE, pas à ce concept générique, pour ne "
    "pas créer de double hiérarchie. Cf. relecture 2026-08-09, cas 65."
)

for path in PATHS:
    onto = json.load(open(path, encoding="utf-8"))
    c = onto["concepts"]
    c["FLUTTER_ATRIAL"].pop("children", None)
    c["FLUTTER_ATRIAL"].pop("requires", None)
    c["FLUTTER_ATRIAL"]["comment"] = COMMENT_FLUTTER
    c["BLOC_DE_BRANCHE_ALTERNANT"].pop("requires", None)
    json.dump(onto, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("fixed", path)
