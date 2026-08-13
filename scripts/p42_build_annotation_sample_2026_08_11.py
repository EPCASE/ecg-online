# -*- coding: utf-8 -*-
"""
p42_build_annotation_sample_2026_08_11.py — P4.2 étape B : échantillonnage
stratifié + CSV d'annotation EN AVEUGLE.

Entrée : data/p42_corpus_rescored.json (étape A, rejeu neuro-v1.2).
Sorties :
  - data/p42_annotation_blind.csv    → pour l'expert (SANS score machine)
  - data/p42_annotation_key.json     → clé secrète (sample_id → key, score
                                        machine, strate) — NE PAS OUVRIR
                                        avant la fin de l'annotation.

Schéma validé (option b) : pour chaque cas ayant ≥ 5 copies calibrables
(rescore ok, backend ≠ gpt), tirer 5 copies par strates de score machine :
  1 basse (tercile inférieur) / 2 moyennes (tercile central) /
  1 haute (tercile supérieur) / 1 aléatoire parmi les restantes.
Tirage déterministe (seed fixe) pour reproductibilité.

Colonnes du CSV expert :
  sample_id ; cas ; texte ; note_expert_0_100 ;
  q_diag_principal_ok (O/N/partiel) ; q_erreur_grave (O/N) ;
  q_commentaire (libre)

Usage :
    python scripts/p42_build_annotation_sample_2026_08_11.py
"""
from __future__ import annotations

import csv
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
IN_PATH = os.path.join(DATA, "p42_corpus_rescored.json")
CSV_PATH = os.path.join(DATA, "p42_annotation_blind.csv")
KEY_PATH = os.path.join(DATA, "p42_annotation_key.json")

SEED = 20260811
PER_CASE = 5
MIN_PER_CASE = 5


def main() -> int:
    with open(IN_PATH, encoding="utf-8") as f:
        payload = json.load(f)
    items = [it for it in payload["items"]
             if it.get("rescore_status") == "ok"
             and not it.get("excluded_from_calibration")]

    by_case: dict[int, list[dict]] = {}
    for it in items:
        by_case.setdefault(it["cas"], []).append(it)

    rng = random.Random(SEED)
    sample: list[dict] = []
    for cas in sorted(by_case):
        pool = by_case[cas]
        if len(pool) < MIN_PER_CASE:
            continue
        pool = sorted(pool, key=lambda it: (it.get("score") or 0, it["key"]))
        n = len(pool)
        t1, t2 = n // 3, (2 * n) // 3
        low, mid, high = pool[:max(t1, 1)], pool[t1:t2] or pool, pool[t2:] or pool
        chosen: list[tuple[str, dict]] = []
        used: set[str] = set()

        def pick(bucket: list[dict], strate: str, k: int) -> None:
            cands = [it for it in bucket if it["key"] not in used]
            for it in rng.sample(cands, min(k, len(cands))):
                used.add(it["key"])
                chosen.append((strate, it))

        pick(low, "basse", 1)
        pick(mid, "moyenne", 2)
        pick(high, "haute", 1)
        pick(pool, "aleatoire", 1)
        # complément si strates trop petites
        while len(chosen) < min(PER_CASE, n):
            pick(pool, "complement", 1)
        for strate, it in chosen:
            sample.append({"strate": strate, **it})

    # Ordre aveugle : mélange global, sample_id opaque
    rng.shuffle(sample)
    rows, key = [], []
    for i, it in enumerate(sample, 1):
        sid = f"S{i:03d}"
        rows.append({"sample_id": sid, "cas": it["cas"], "texte": it["texte"],
                     "note_expert_0_100": "", "q_diag_principal_ok": "",
                     "q_erreur_grave": "", "q_commentaire": ""})
        key.append({"sample_id": sid, "key": it["key"], "cas": it["cas"],
                    "strate": it["strate"], "score_machine": it.get("score"),
                    "score_adequation": it.get("score_adequation"),
                    "score_securite": it.get("score_securite")})

    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(rows)
    with open(KEY_PATH, "w", encoding="utf-8") as f:
        json.dump({"seed": SEED, "n": len(key), "entries": key},
                  f, ensure_ascii=False, indent=1)

    n_cases = len({r["cas"] for r in rows})
    print(f"[sample] {len(rows)} copies sur {n_cases} cas → {CSV_PATH}")
    print(f"[key]    clé aveugle → {KEY_PATH} (ne pas consulter avant annotation)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
