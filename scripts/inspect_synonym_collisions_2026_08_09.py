#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inspect_synonym_collisions_2026_08_09.py — Affiche le détail complet de
chaque concept impliqué dans les 20 collisions de synonymes pré-existantes,
pour permettre une décision éclairée (quel concept garde quel synonyme).
"""
import json
from collections import defaultdict

PATH = r"C:\Users\Administrateur\bmad\ECG lecture\data\ontology_v2.json"
onto = json.load(open(PATH, encoding="utf-8"))
c = onto["concepts"]

syn_map = defaultdict(set)
for cid, concept in c.items():
    for s in concept.get("synonymes") or []:
        syn_map[s.strip().lower()].add(cid)
collisions = {k: v for k, v in syn_map.items() if len(v) > 1}

for syn, cids in sorted(collisions.items()):
    print("=" * 78)
    print(f"SYNONYME AMBIGU : {syn!r}")
    print("=" * 78)
    for cid in sorted(cids):
        concept = c[cid]
        print(f"\n  [{cid}]")
        print(f"    concept_name : {concept.get('concept_name')}")
        print(f"    type/categorie: {concept.get('type')} / {concept.get('categorie')}")
        print(f"    parents      : {concept.get('parents')}")
        print(f"    children     : {concept.get('children')}")
        print(f"    requires     : {concept.get('requires')}")
        print(f"    synonymes    : {concept.get('synonymes')}")
        if concept.get("comment"):
            print(f"    comment      : {concept.get('comment')}")
    print()
