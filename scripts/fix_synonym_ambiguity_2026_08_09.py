#!/usr/bin/env python3
"""Corrige des ambiguïtés de synonymes créées par l'ajout de concepts le
2026-08-09 : le parent générique TACHYCARDIE_VENTRICULAIRE gardait des
synonymes ("TVNS", "TV soutenue", "tachycardie ventriculaire soutenue") qui
désignent maintenant explicitement ses 2 nouveaux enfants spécifiques
(TACHYCARDIE_VENTRICULAIRE_NON_SOUTENUE / _SOUTENUE) -> ambiguïté de
résolution retirée en gardant ces synonymes UNIQUEMENT sur les enfants.

Idem pour EXTENSION_VENTRICULE_DROIT : le synonyme "infarctus inférieur avec
extension au ventricule droit" est une phrase-diagnostic complète qui
appartient au concept SCA ST+ (déjà présent dans ses propres synonymes),
pas au simple finding EXTENSION_VENTRICULE_DROIT -> retiré du finding pour
ne garder que des synonymes décrivant le signe lui-même.
"""
import json

PATHS = [
    r"C:\Users\Administrateur\bmad\ECG lecture\data\ontology_v2.json",
    r"C:\Users\Administrateur\bmad\ECG lecture\ecg-online\rag_pipeline\data\ontology_v2.json",
    r"C:\Users\Administrateur\bmad\ECG lecture\rag_pipeline\data\ontology_v2.json",
]

REMOVE_FROM_TV_PARENT = {"tvns", "tachycardie ventriculaire soutenue", "tv soutenue"}

for path in PATHS:
    onto = json.load(open(path, encoding="utf-8"))
    c = onto["concepts"]

    tv = c["TACHYCARDIE_VENTRICULAIRE"]
    before = tv.get("synonymes") or []
    tv["synonymes"] = [s for s in before if s.strip().lower() not in REMOVE_FROM_TV_PARENT]
    print(f"[{path.split(chr(92))[-1]}] TACHYCARDIE_VENTRICULAIRE synonymes: "
          f"{len(before)} -> {len(tv['synonymes'])}")

    ext = c["EXTENSION_VENTRICULE_DROIT"]
    before2 = ext.get("synonymes") or []
    ext["synonymes"] = [s for s in before2
                         if s.strip().lower() != "infarctus inférieur avec extension au ventricule droit"]
    print(f"[{path.split(chr(92))[-1]}] EXTENSION_VENTRICULE_DROIT synonymes: "
          f"{len(before2)} -> {len(ext['synonymes'])}")

    # Le nouveau concept générique FLUTTER_ATRIAL porte désormais le terme
    # générique "flutter atrial" (cf. son comment) ; on retire ce doublon
    # littéral des concepts plus spécifiques qui le portaient aussi, en
    # gardant toutes leurs autres synonymes propres intacts.
    for cid in ("FLUTTER_DROIT_TYPIQUE", "TACHYCARDIE_ATRIALE"):
        concept = c[cid]
        before3 = concept.get("synonymes") or []
        concept["synonymes"] = [s for s in before3 if s.strip().lower() != "flutter atrial"]
        print(f"[{path.split(chr(92))[-1]}] {cid} synonymes: "
              f"{len(before3)} -> {len(concept['synonymes'])}")

    json.dump(onto, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
