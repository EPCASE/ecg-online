#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_constraints_coherence.py — P4.3b étape F (garde-fou CI).

Vérifie la cohérence STRUCTURELLE des contraintes de l'ontologie runtime
(`rag_pipeline/data/ontology_v2.json`), après la migration
excludes→conflicts_by_default. Règles (design P4.3b §5) :

  F1. Aucune paire déclarée à la fois `excludes` ET `conflicts_by_default`
      (une paire est HARD ou DEFAULT, jamais les deux).
  F2. Toutes les cibles de excludes / conflicts_by_default / excludes_families
      / allowed_cooccurrences / negation_of existent dans `concepts`.
  F3. Aucune `allowed_cooccurrences` ne neutralise une paire HARD (excludes) :
      un HARD n'est jamais levé silencieusement.
  F4. Aucun golden de cas n'accepte (present) LES DEUX pôles d'une paire HARD
      → sinon data_inconsistency garantie (à corriger côté données).
  F5. Symétrie informative : les excludes HARD doivent être déclarés dans les
      deux sens (warning seulement — le registre canonicalise de toute façon).

Sortie : exit 0 si aucun échec (F1-F4), exit 1 sinon. F5 = warnings.

Usage : python scripts/verify_constraints_coherence.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ONTO_PATH = ROOT / "rag_pipeline" / "data" / "ontology_v2.json"
GOLDEN_PATH = ROOT / "data" / "cases_golden.json"

errors: list[str] = []
warnings: list[str] = []


def _canon(a: str, b: str):
    return tuple(sorted((a, b)))


def main() -> int:
    onto = json.loads(ONTO_PATH.read_text(encoding="utf-8"))
    concepts = onto["concepts"]

    hard_pairs = set()      # paires canoniques excludes
    default_pairs = set()   # paires canoniques conflicts_by_default

    # ── Collecte + F2 (cibles existantes) ────────────────────────────────
    rel_keys = ("excludes", "conflicts_by_default", "excludes_families",
                "allowed_cooccurrences", "negation_of")
    for cid, c in concepts.items():
        for key in rel_keys:
            val = c.get(key)
            if not val:
                continue
            targets = val if isinstance(val, list) else [val]
            for t in targets:
                if t not in concepts:
                    errors.append(f"F2: {cid}.{key} → cible inconnue « {t} »")
        for t in c.get("excludes", []):
            hard_pairs.add(_canon(cid, t))
        for t in c.get("conflicts_by_default", []):
            default_pairs.add(_canon(cid, t))

    # ── F1 : paire à la fois HARD et DEFAULT ─────────────────────────────
    for pair in sorted(hard_pairs & default_pairs):
        errors.append(f"F1: paire déclarée excludes ET conflicts_by_default : {pair}")

    # ── F3 : allowed_cooccurrences sur une paire HARD ────────────────────
    for cid, c in concepts.items():
        for t in c.get("allowed_cooccurrences", []):
            if _canon(cid, t) in hard_pairs:
                errors.append(
                    f"F3: allowed_cooccurrences ({cid} ↔ {t}) neutraliserait un "
                    f"excludes HARD — interdit (un HARD n'est jamais levé)")

    # ── F4 : golden acceptant les 2 pôles d'un HARD ──────────────────────
    if GOLDEN_PATH.exists():
        golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
        cases = golden.get("cases", golden) if isinstance(golden, dict) else {}
        for num, case in cases.items():
            mapping = (case or {}).get("mapping") or {}
            present = set()
            for m in mapping.values():
                if not isinstance(m, dict):
                    continue
                gid = m.get("golden_id")
                statut = (m.get("statut") or "present").lower()
                if gid and statut == "present":
                    present.add(gid)
            for a, b in hard_pairs:
                if a in present and b in present:
                    errors.append(
                        f"F4: cas {num} — le golden accepte les 2 pôles du "
                        f"HARD ({a} ↔ {b}) → data_inconsistency garantie")
    else:
        warnings.append(f"F4: {GOLDEN_PATH} introuvable — vérification sautée")

    # ── F5 : symétrie des excludes (informatif) ──────────────────────────
    for a, b in sorted(hard_pairs):
        if b not in concepts.get(a, {}).get("excludes", []):
            warnings.append(f"F5: excludes non symétrique : {b} → {a} déclaré, "
                            f"mais pas {a} → {b}")
        if a not in concepts.get(b, {}).get("excludes", []):
            warnings.append(f"F5: excludes non symétrique : {a} → {b} déclaré, "
                            f"mais pas {b} → {a}")

    # ── Rapport ──────────────────────────────────────────────────────────
    print(f"Ontologie : {ONTO_PATH}")
    print(f"Paires HARD (excludes) : {len(hard_pairs)} | "
          f"DEFAULT (conflicts_by_default) : {len(default_pairs)}")
    for w in warnings:
        print(f"⚠️  {w}")
    for e in errors:
        print(f"❌ {e}")
    if errors:
        print(f"\n❌ {len(errors)} erreur(s) structurelle(s).")
        return 1
    print(f"\n✅ Contraintes cohérentes ({len(warnings)} warning(s) F5/info).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
