# -*- coding: utf-8 -*-
"""
p42_analyze_calibration_2026_08_12.py — P4.2 étape D : analyse machine vs expert.

Entrées : data/p42_annotation_blind.csv (annoté), data/p42_annotation_key.json,
          data/p42_corpus_rescored.json.
Sorties : data/p42_calibration_report.json + affichage console.

Métriques : Spearman, Pearson, Lin CCC, MAE, biais ; top-20 des résidus ;
analyse des « erreurs graves » vs score_securite machine.
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def spearman(x, y):
    def rank(v):
        s = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(s):
            j = i
            while j + 1 < len(s) and v[s[j + 1]] == v[s[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[s[k]] = avg
            i = j + 1
        return r
    return pearson(rank(x), rank(y))


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y)) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x) / n)
    sy = math.sqrt(sum((b - my) ** 2 for b in y) / n)
    return cov / (sx * sy) if sx and sy else 0.0


def lin_ccc(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    vx = sum((a - mx) ** 2 for a in x) / n
    vy = sum((b - my) ** 2 for b in y) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y)) / n
    return (2 * cov) / (vx + vy + (mx - my) ** 2) if (vx + vy + (mx - my) ** 2) else 0.0


def main() -> int:
    with open(os.path.join(DATA, "p42_annotation_blind.csv"), encoding="utf-8-sig") as f:
        annotations = {r["sample_id"]: r for r in csv.DictReader(f, delimiter=";")}
    with open(os.path.join(DATA, "p42_annotation_key.json"), encoding="utf-8") as f:
        key = {e["sample_id"]: e for e in json.load(f)["entries"]}
    with open(os.path.join(DATA, "p42_corpus_rescored.json"), encoding="utf-8") as f:
        corpus = {it["key"]: it for it in json.load(f)["items"]}

    pairs = []
    for sid, ann in annotations.items():
        v = (ann.get("note_expert_0_100") or "").strip()
        if not v:
            continue
        expert = float(v.replace(",", "."))
        k = key[sid]
        it = corpus.get(k["key"], {})
        qd_raw = (ann.get("q_diag_principal_ok") or "").strip()
        qd = qd_raw if qd_raw in ("0", "1") else "partiel"
        qg = (ann.get("q_erreur_grave") or "").strip()
        pairs.append({
            "sample_id": sid, "cas": k["cas"], "strate": k["strate"],
            "machine": float(k["score_machine"] or 0),
            "adequation": k.get("score_adequation"),
            "securite": k.get("score_securite"),
            "expert": expert,
            "q_diag": qd, "q_diag_raw": qd_raw, "q_grave": qg,
            "commentaire": (ann.get("q_commentaire") or "").strip(),
            "texte": it.get("texte", "")[:200],
            "safety_events": it.get("safety_events", []),
        })

    m = [p["machine"] for p in pairs]
    e = [p["expert"] for p in pairs]
    n = len(pairs)
    res = {
        "n": n,
        "spearman": round(spearman(m, e), 3),
        "pearson": round(pearson(m, e), 3),
        "lin_ccc": round(lin_ccc(m, e), 3),
        "mae": round(sum(abs(a - b) for a, b in zip(m, e)) / n, 1),
        "biais_machine_moins_expert": round(sum(a - b for a, b in zip(m, e)) / n, 1),
        "moy_machine": round(sum(m) / n, 1),
        "moy_expert": round(sum(e) / n, 1),
    }
    print(json.dumps(res, indent=1, ensure_ascii=False))

    # Résidus les plus élevés
    top = sorted(pairs, key=lambda p: -abs(p["machine"] - p["expert"]))[:20]
    print("\n=== TOP 20 ÉCARTS |machine - expert| ===")
    for p in top:
        print(f"{p['sample_id']} cas{p['cas']:>2} machine={p['machine']:>5.0f} "
              f"expert={p['expert']:>5.0f} diff={p['machine']-p['expert']:>+6.0f} "
              f"secu={p['securite']} grave={p['q_grave']} | {p['texte'][:80]!r}")

    # Sécurité : erreurs graves expert vs machine
    graves = [p for p in pairs if p["q_grave"] == "1"]
    print(f"\n=== ERREURS GRAVES (expert) : {len(graves)} copies ===")
    for p in graves:
        n_ev = len([ev for ev in (p["safety_events"] or []) if ev.get("status") == "active"])
        print(f"{p['sample_id']} cas{p['cas']:>2} machine={p['machine']:>5.0f} secu={p['securite']} "
              f"safety_events_actifs={n_ev} expert={p['expert']:>5.0f}")
    # Faux négatifs sécurité : grave selon expert mais securite=100
    fn = [p for p in graves if (p["securite"] or 100) == 100]
    # Faux positifs : securite<100 mais pas grave selon expert
    fp = [p for p in pairs if (p["securite"] or 100) < 100 and p["q_grave"] == "0"]
    print(f"\nFaux négatifs sécurité (grave expert, secu machine=100) : {len(fn)} → {[p['sample_id'] for p in fn]}")
    print(f"Faux positifs sécurité (secu<100, pas grave expert)       : {len(fp)} → {[p['sample_id'] for p in fp]}")

    # par strate
    print("\n=== PAR STRATE ===")
    for s in ("basse", "moyenne", "haute", "aleatoire", "complement"):
        sub = [p for p in pairs if p["strate"] == s]
        if not sub:
            continue
        mm = sum(p["machine"] for p in sub) / len(sub)
        ee = sum(p["expert"] for p in sub) / len(sub)
        print(f"{s:<10} n={len(sub):>3} machine_moy={mm:>5.1f} expert_moy={ee:>5.1f}")

    out = os.path.join(DATA, "p42_calibration_report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"metrics": res, "pairs": pairs}, f, ensure_ascii=False, indent=1)
    print(f"\n[out] {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
