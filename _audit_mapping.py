"""
_audit_mapping.py — Étape 0 : recouvrement barème (points_cles) ↔ ontologie V2
==============================================================================
Lecture seule. Pour chacun des points_cles des 75 cas, cherche le meilleur
concept ontologique par : (1) égalité normalisée, (2) synonyme exact,
(3) inclusion (substring). Sort un taux de couverture « facile » — borne BASSE
de ce que GPT-5.5 fera (lui gère la sémantique, les reformulations, etc.).

But : décider si le mapping est faisable à ~90 % auto, ou s'il faut d'abord
enrichir l'ontologie.

Usage : python _audit_mapping.py
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REF_PATH = os.path.join(HERE, "data", "cases_reference.json")
ONTO_CANDIDATES = [
    os.path.join(HERE, "data", "ontology_v2.json"),
    r"C:\Users\Administrateur\bmad\ECG lecture\data\ontology_v2.json",
]


def canon(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "").strip())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def load_onto():
    for p in ONTO_CANDIDATES:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f), p
    raise FileNotFoundError("ontology_v2.json introuvable")


def build_index(onto: dict):
    """Map canon(texte) -> concept_id, à partir des noms + synonymes."""
    idx = {}
    concepts = onto.get("concepts", onto)
    for cid, c in concepts.items():
        names = [c.get("concept_name", ""), c.get("concept_name_en", "")]
        names += c.get("synonymes", []) or []
        for n in names:
            k = canon(n)
            if k and k not in idx:
                idx[k] = cid
    return idx, concepts


def best_match(label: str, idx: dict):
    """(concept_id, method) ou (None, 'aucun')."""
    k = canon(label)
    if not k:
        return None, "vide"
    if k in idx:
        return idx[k], "exact"
    # substring : le label contient un terme onto, ou l'inverse
    best = None
    for term, cid in idx.items():
        if len(term) < 5:
            continue
        if term in k or k in term:
            # préfère le terme le plus long (plus spécifique)
            if best is None or len(term) > best[2]:
                best = (cid, "inclusion", len(term))
    if best:
        return best[0], best[1]
    return None, "aucun"


def main():
    onto, onto_path = load_onto()
    idx, concepts = build_index(onto)
    refs = json.load(open(REF_PATH, encoding="utf-8")).get("references", [])

    print("=" * 70)
    print("  AUDIT recouvrement barème ↔ ontologie (borne BASSE, sans GPT)")
    print(f"  Ontologie : {onto_path}")
    print(f"  Concepts  : {len(concepts)} | clés d'index (noms+synonymes) : {len(idx)}")
    print(f"  Cas       : {len(refs)}")
    print("=" * 70)

    methods = Counter()
    total_pts = 0
    non_matches = []
    per_rang = {"A": Counter(), "B": Counter(), "C": Counter(), "?": Counter()}

    for r in refs:
        for p in r.get("points_cles", []) or []:
            label = p.get("label", "")
            rang = (p.get("rang") or "?").upper()
            if rang not in per_rang:
                rang = "?"
            total_pts += 1
            cid, method = best_match(label, idx)
            methods[method] += 1
            per_rang[rang][method] += 1
            if cid is None:
                non_matches.append((r.get("num"), rang, label))

    matched = methods["exact"] + methods["inclusion"]
    print(f"\nTotal points_cles : {total_pts}")
    print(f"  exact       : {methods['exact']:4d}  ({methods['exact']/total_pts:5.1%})")
    print(f"  inclusion   : {methods['inclusion']:4d}  ({methods['inclusion']/total_pts:5.1%})")
    print(f"  AUCUN       : {methods['aucun']:4d}  ({methods['aucun']/total_pts:5.1%})")
    print(f"  → couverture 'facile' (borne basse) : {matched/total_pts:5.1%}")

    print("\nPar rang EDN (matched / total) :")
    for rg in ["A", "B", "C", "?"]:
        c = per_rang[rg]
        tot = sum(c.values())
        if tot:
            m = c["exact"] + c["inclusion"]
            print(f"  rang {rg} : {m:3d}/{tot:3d}  ({m/tot:5.1%})")

    print(f"\nExemples NON mappés (borne basse — GPT en récupérera une partie) :")
    for num, rang, label in non_matches[:20]:
        print(f"  [cas {num:>2} · {rang}] {label[:70]}")
    print(f"  … {len(non_matches)} non mappés au total (matching naïf).")

    # Sauvegarde pour exploitation ultérieure
    out = os.path.join(HERE, "data", "_audit_mapping.json")
    json.dump({
        "total_points": total_pts,
        "methods": dict(methods),
        "couverture_facile_pct": round(matched / total_pts * 100, 1),
        "non_matches": [{"num": n, "rang": rg, "label": l} for n, rg, l in non_matches],
    }, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n💾 Détail écrit : {out}")


if __name__ == "__main__":
    main()
