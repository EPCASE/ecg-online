"""Audit des réponses étudiantes reçues depuis le 13/08/2026 (neuro-v1.3).

Usage : python scripts/_audit_new_responses_2026_10_26.py [--since 2026-08-13] [--all]
Lit ecg-online/_sheet_reponses.json (dump de l'onglet `reponses`).
"""
import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "_sheet_reponses.json"


def load(since: str):
    d = json.loads(SRC.read_text(encoding="utf-8"))
    h = d["header"]
    rows = [dict(zip(h, r + [""] * (len(h) - len(r)))) for r in d["rows"]]
    rows = [r for r in rows if (r.get("reponse") or "").strip()]
    return [r for r in rows if (r.get("horodatage") or "") > since]


def score(r):
    try:
        return float(r.get("score"))
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-08-13")
    ap.add_argument("--all", action="store_true", help="lister toutes les copies, pas seulement les zéros")
    a = ap.parse_args()
    new = load(a.since)
    print(f"Copies depuis {a.since} : {len(new)}")
    print("status :", dict(collections.Counter(r.get("resolution_status") for r in new)))
    print("reason :", collections.Counter(r.get("resolution_reason") for r in new).most_common(12))
    print("mode   :", dict(collections.Counter(r.get("mode") for r in new)))
    print("refait :", dict(collections.Counter(r.get("refait") for r in new)))

    sc = [s for s in (score(r) for r in new) if s is not None]
    bins = collections.Counter(int(s // 10) * 10 if s < 100 else 100 for s in sc)
    print("distribution :", {k: bins[k] for k in sorted(bins)})
    print(f"moyenne {statistics.mean(sc):.1f}  médiane {statistics.median(sc)}")

    # par cas
    per_cas = collections.defaultdict(list)
    for r in new:
        s = score(r)
        if s is not None:
            per_cas[r["cas"]].append(s)
    print("\n=== Par cas (n, moyenne, %zéro) ===")
    for cas, v in sorted(per_cas.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 999):
        z = sum(1 for s in v if s == 0)
        print(f"cas {cas:>3}: n={len(v):2d} moy={statistics.mean(v):5.1f} zero={z}/{len(v)}")

    sel = new if a.all else [r for r in new if score(r) == 0]
    print(f"\n=== Détail ({'toutes' if a.all else 'zéros'}: {len(sel)}) ===")
    for r in sorted(sel, key=lambda r: (int(r["cas"]) if str(r["cas"]).isdigit() else 999, r["horodatage"])):
        print(
            f"[{r['horodatage'][:16]} {r['session']} cas {r['cas']}] score={r['score']} len={r['longueur']} "
            f"status={r['resolution_status']} reason={r['resolution_reason'][:50]!r}"
        )
        print(f"   REP : {r['reponse'][:220]!r}")
        print(f"   CORR: {r['correspondance'][:200]!r}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
