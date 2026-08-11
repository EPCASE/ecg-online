#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_diff_negation_map_2026_08_11.py — P4.3b étape A.

Rapport de provenance de la negation map actuelle (build_negation_map de
scoring_v3), pour audit expert AVANT la migration excludes→conflicts_by_default.

Pour chaque entrée `absent(X) → Y` de la map, indique :
  - la source : excludes direct / excludes_families (+ concept famille)
  - le DEVENIR après migration : KEPT (relation HARD conservée dans
    excludes), MIGRATED (relation DEFAULT déplacée vers conflicts_by_default
    → l'entrée DISPARAÎTRA de la map si build_negation_map passe à
    negation_of+HARD), FAMILY (inchangé — excludes_families non touché).

Sortie : docs/P4.3b_etapeA_negation_map_provenance.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "rag_pipeline"))

import scoring_v3  # noqa: E402
from scoring_v3 import build_negation_map, _is_normal_concept, _get_all_children_recursive  # noqa: E402
from semantic_layer import _get_ontology_v2  # noqa: E402

# Classification P4.3a (docs/P4.3a_audit_excludes_2026_08_11.md, consolidation)
# Paires HARD restantes dans excludes (13 relations, exprimées canoniquement)
HARD_PAIRS = {
    tuple(sorted(p)) for p in [
        ("ABSENCE_D_ISCHEMIE", "ISCHEMIQUE"),
        ("PAS_D_ANOMALIE_DE_LE_REPOLARISATION", "TROUBLE_DE_REPOLARISATION"),
        ("ANOMALIE_DE_DUREE_DU_QT", "QT_NORMAL"),
        ("HYPERCALCEMIE", "HYPOCALCEMIE"),
        ("HYPERKALIEMIE", "HYPOKALIEMIE"),
        ("HYPERNATREMIE", "HYPONATREMIE"),
        ("VOLTAGE_DU_QRS_NORMAL", "MICROVOLTAGE"),
        ("SYNDROME_DE_LOWN_GANONG_ET_LEVINE", "ONDE_DELTA"),
    ]
}


def main():
    onto = _get_ontology_v2()
    concepts = onto["concepts"]
    neg_map = build_negation_map()

    # Reconstituer la provenance en rejouant la logique de build_negation_map
    provenance = {}  # patho_id -> (normal_id, source, famille_ou_None)
    for nid, nc in concepts.items():
        for x in nc.get("excludes", []):
            if _is_normal_concept(nid) and x not in provenance:
                provenance[x] = (nid, "excludes_direct", None)
    for nid, nc in concepts.items():
        if not _is_normal_concept(nid):
            continue
        for fam in nc.get("excludes_families", []):
            if fam not in provenance:
                provenance[fam] = (nid, "excludes_families", fam)
            for child in _get_all_children_recursive(fam, max_depth=3):
                if child not in provenance:
                    provenance[child] = (nid, "excludes_families", fam)

    rows = []
    for patho, normal in sorted(neg_map.items()):
        src = provenance.get(patho, (normal, "??", None))
        source = src[1]
        fam = src[2]
        if source == "excludes_direct":
            pair = tuple(sorted((patho, normal)))
            devenir = "KEPT (HARD)" if pair in HARD_PAIRS else "**MIGRATED (DEFAULT) → disparaît**"
        elif source == "excludes_families":
            devenir = f"FAMILY (inchangé, famille={fam})"
        else:
            devenir = "?? provenance non retrouvée"
        rows.append((patho, normal, source, devenir))

    n_migrated = sum(1 for r in rows if "MIGRATED" in r[3])
    n_kept = sum(1 for r in rows if r[3].startswith("KEPT"))
    n_family = sum(1 for r in rows if r[3].startswith("FAMILY"))

    lines = [
        "# P4.3b Étape A — Provenance de la negation map (2026-08-11)",
        "",
        f"Map actuelle : **{len(neg_map)} entrées** `absent(patho) → normal`.",
        "",
        f"- KEPT (source excludes HARD conservé) : **{n_kept}**",
        f"- MIGRATED (source excludes DEFAULT → l'entrée disparaîtra si la map passe à negation_of+HARD) : **{n_migrated}**",
        f"- FAMILY (source excludes_families, non touché par la migration) : **{n_family}**",
        "",
        "À AUDITER par l'expert : les lignes MIGRATED. Pour chacune, décider si",
        "la conversion absent→positif qu'elle permettait était légitime (alors la",
        "déclarer via `negation_of`) ou douteuse (alors sa disparition est",
        "souhaitable).",
        "",
        "| absent(patho) | → normal | source | devenir |",
        "|---|---|---|---|",
    ]
    for patho, normal, source, devenir in rows:
        lines.append(f"| {patho} | {normal} | {source} | {devenir} |")

    out = ROOT / "docs" / "P4.3b_etapeA_negation_map_provenance.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(neg_map)} entrées — KEPT={n_kept} MIGRATED={n_migrated} FAMILY={n_family}")
    print(f"Rapport : {out}")


if __name__ == "__main__":
    main()
