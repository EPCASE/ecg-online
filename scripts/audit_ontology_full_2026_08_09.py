#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_ontology_full_2026_08_09.py — Relecture complète de fond de
data/ontology_v2.json, post-corrections de la relecture des 75 cas.

Vérifie :
  1. Dangling references (parents/children/requires/supports/excludes/
     has_qualifiers pointant vers un concept_id inexistant)
  2. Cohérence bidirectionnelle parent<->children
  3. Concepts orphelins (aucun parent ET jamais cité comme children d'un autre)
  4. Auto-référence (un concept qui se cite lui-même)
  5. Cycles parent->enfant (A parent de B parent de A)
  6. Collisions de synonymes (un même synonyme sur >=2 concept_id)
  7. requires/excludes contradictoires (un concept qui requires ET excludes
     le même concept_id)
"""
import json
from collections import defaultdict

PATH = r"C:\Users\Administrateur\bmad\ECG lecture\data\ontology_v2.json"

onto = json.load(open(PATH, encoding="utf-8"))
c = onto["concepts"]
ids = set(c.keys())

print("=" * 70)
print(f"TOTAL CONCEPTS: {len(ids)}")
print("=" * 70)

# 1. Dangling references
REL_FIELDS = ["parents", "children", "requires", "supports", "excludes",
              "has_qualifiers", "has_qualifier_families", "excludes_families"]
dangling = []
for cid, concept in c.items():
    for f in REL_FIELDS:
        for target in concept.get(f) or []:
            if target not in ids and f not in ("has_qualifier_families", "excludes_families"):
                dangling.append((cid, f, target))
print(f"\n[1] Dangling references: {len(dangling)}")
for d in dangling[:30]:
    print("   ", d)

# 2. Cohérence bidirectionnelle parent<->children
incoherent = []
for cid, concept in c.items():
    for p in concept.get("parents") or []:
        if p in c:
            if cid not in (c[p].get("children") or []):
                incoherent.append((p, "manque child ->", cid))
    for ch in concept.get("children") or []:
        if ch in c:
            if cid not in (c[ch].get("parents") or []):
                incoherent.append((ch, "manque parent ->", cid))
print(f"\n[2] Incohérences bidirectionnelles parent<->children: {len(incoherent)}")
for i in incoherent[:30]:
    print("   ", i)

# 3. Concepts orphelins (jamais liés à aucune hiérarchie)
all_children_cited = set()
for concept in c.values():
    all_children_cited |= set(concept.get("children") or [])
orphans = [cid for cid, concept in c.items()
           if not (concept.get("parents")) and cid not in all_children_cited]
print(f"\n[3] Concepts sans parent NI jamais cités comme enfant: {len(orphans)}")
for o in orphans[:40]:
    print("   ", o)

# 4. Auto-référence
selfref = []
for cid, concept in c.items():
    for f in REL_FIELDS:
        if cid in (concept.get(f) or []):
            selfref.append((cid, f))
print(f"\n[4] Auto-références: {len(selfref)}")
for s in selfref:
    print("   ", s)

# 5. Cycles parent->children directs (A parent de B ET B parent de A)
cycles = []
for cid, concept in c.items():
    for ch in concept.get("children") or []:
        if ch in c and cid in (c[ch].get("children") or []):
            cycles.append((cid, ch))
print(f"\n[5] Cycles directs A<->B (parent l'un de l'autre): {len(cycles)}")
for cy in cycles:
    print("   ", cy)

# 6. Collisions synonymes (hors nom du concept lui-même)
syn_map = defaultdict(set)
for cid, concept in c.items():
    for s in concept.get("synonymes") or []:
        syn_map[s.strip().lower()].add(cid)
collisions = {k: v for k, v in syn_map.items() if len(v) > 1}
print(f"\n[6] Collisions de synonymes: {len(collisions)}")
for k, v in sorted(collisions.items()):
    print(f"    {k!r} -> {sorted(v)}")

# 7. requires/excludes contradictoires
contradictions = []
for cid, concept in c.items():
    req = set(concept.get("requires") or [])
    exc = set(concept.get("excludes") or [])
    both = req & exc
    if both:
        contradictions.append((cid, sorted(both)))
print(f"\n[7] requires ET excludes le même concept (contradiction): {len(contradictions)}")
for ct in contradictions:
    print("   ", ct)

print("\n" + "=" * 70)
print("RESUME")
print("=" * 70)
print(f"dangling={len(dangling)} incoherent_parent_children={len(incoherent)} "
      f"orphans={len(orphans)} selfref={len(selfref)} cycles={len(cycles)} "
      f"syn_collisions={len(collisions)} req_excl_contradictions={len(contradictions)}")
