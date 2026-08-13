# -*- coding: utf-8 -*-
"""
p42_ingest_and_rescore_2026_08_11.py — P4.2 étape A : ingestion + rejeu.

Entrée  : _sheet_reponses.json (dump de l'onglet `reponses` du Sheet de
          production, via scripts/_read_new_sheets_2026_08_11.py --dump
          2080680074 _sheet_reponses.json). NON COMMITTÉ (données étudiantes).
Sortie  : data/p42_corpus_rescored.json (scores machine neuro-v1.2 par copie)
          + alimentation passive de data/coherence_pairs_log.jsonl (P4.3c ét. 0).

Règles validées par l'expert (2026-08-11) :
  - déduplication « dernière tentative » : pour chaque (session, cas), on ne
    garde que la DERNIÈRE soumission (horodatage max). Lignes sans session :
    conservées individuellement (pas de clé de dédup fiable).
  - backend `gpt` : EXCLU de la calibration (marqué excluded_from_calibration,
    mais rejoué quand même pour le log de cohérence).
  - réponses vides : ignorées.

Usage :
    python scripts/p42_ingest_and_rescore_2026_08_11.py             # tout
    python scripts/p42_ingest_and_rescore_2026_08_11.py --limit 5   # test
    python scripts/p42_ingest_and_rescore_2026_08_11.py --resume    # reprend
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

ROOT = r"c:\Users\Administrateur\bmad\ECG lecture"
sys.path.insert(0, os.path.join(ROOT, "ecg-online"))
sys.path.insert(0, os.path.join(ROOT, "rag_pipeline"))

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, "ecg-online", ".env"))

HERE = os.path.dirname(os.path.abspath(__file__))
ONLINE = os.path.join(HERE, "..")
DUMP_PATH = os.path.join(ONLINE, "_sheet_reponses.json")
OUT_PATH = os.path.join(ONLINE, "data", "p42_corpus_rescored.json")


def load_corpus() -> list[dict]:
    with open(DUMP_PATH, encoding="utf-8") as f:
        d = json.load(f)
    header = d["header"]
    rows = [dict(zip(header, r + [""] * (len(header) - len(r)))) for r in d["rows"]]
    rows = [r for r in rows if (r.get("reponse") or "").strip()]

    # Dédup « dernière tentative » par (session, cas) — sessions vides gardées telles quelles.
    keyed: dict = {}
    no_session: list[dict] = []
    for r in rows:
        sess = (r.get("session") or "").strip()
        cas = (r.get("cas") or "").strip()
        if not sess:
            no_session.append(r)
            continue
        k = (sess, cas)
        prev = keyed.get(k)
        if prev is None or (r.get("horodatage") or "") >= (prev.get("horodatage") or ""):
            keyed[k] = r
    dedup = list(keyed.values()) + no_session
    dedup.sort(key=lambda r: (int(r["cas"]) if str(r.get("cas", "")).isdigit() else 999,
                              r.get("horodatage") or ""))
    return dedup


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    corpus = load_corpus()
    print(f"[ingest] {len(corpus)} copies après dédup dernière-tentative")

    done: dict[str, dict] = {}
    if args.resume and os.path.exists(OUT_PATH):
        purged = 0
        with open(OUT_PATH, encoding="utf-8") as f:
            for item in json.load(f).get("items", []):
                if (item.get("rescore_status") == "ok"
                        and not item.get("correspondance")
                        and not item.get("concepts")):
                    purged += 1  # faux zéro (résultat vide) → à rejouer
                    continue
                done[item["key"]] = item
        print(f"[resume] {len(done)} copies déjà rejouées, {purged} faux zéros purgés (à rejouer)")

    from app import neuro_grader

    items: list[dict] = list(done.values())
    n_new = 0
    t0 = time.time()
    for i, r in enumerate(corpus):
        key = f"{r.get('session','')}|{r.get('cas','')}|{r.get('horodatage','')}"
        if key in done:
            continue
        if args.limit and n_new >= args.limit:
            break
        cas = int(r["cas"]) if str(r.get("cas", "")).isdigit() else None
        if cas is None:
            continue
        texte = r["reponse"].strip()
        entry = {
            "key": key,
            "cas": cas,
            "session": r.get("session", ""),
            "horodatage": r.get("horodatage", ""),
            "backend_original": r.get("backend", ""),
            "score_original": r.get("score", ""),
            "excluded_from_calibration": (r.get("backend", "") == "gpt"),
            "texte": texte,
            "longueur": len(texte),
        }
        try:
            corr = neuro_grader.grade_neuro(cas, texte)
            if corr is None:
                entry["rescore_status"] = "skipped"
                entry["skip_reason"] = neuro_grader.last_skip_reason()
            elif getattr(corr, "error", None):
                # Erreur pipeline (API, timeout…) : NE PAS enregistrer comme
                # un score valide — c'était le bug des « faux zéros » du
                # premier rejeu (89 copies, cas 41-49).
                entry["rescore_status"] = "error"
                entry["error"] = str(corr.error)
            else:
                d = corr.to_dict()
                if not d.get("correspondance") and not (d.get("concepts_detectes") or []):
                    # Résultat structurellement vide = échec silencieux.
                    entry["rescore_status"] = "error"
                    entry["error"] = "resultat_vide (0 concept, correspondance vide)"
                else:
                    entry["rescore_status"] = "ok"
                    entry["score"] = d.get("score")
                    entry["score_adequation"] = d.get("score_adequation")
                    entry["score_securite"] = d.get("score_securite")
                    entry["correspondance"] = d.get("correspondance")
                    entry["type_erreur"] = d.get("type_erreur")
                    entry["safety_events"] = d.get("safety_events", [])
                    entry["concepts"] = [
                        {k2: c.get(k2) for k2 in ("concept_id", "concept_name", "rang", "statut", "match_type")}
                        for c in (d.get("concepts_detectes") or [])
                    ]
        except Exception as e:  # noqa: BLE001
            entry["rescore_status"] = "error"
            entry["error"] = f"{type(e).__name__}: {e}"
        items.append(entry)
        n_new += 1
        if n_new % 10 == 0:
            elapsed = time.time() - t0
            print(f"[rejeu] {n_new} nouvelles copies ({elapsed:.0f}s, {elapsed/max(n_new,1):.1f}s/copie)")
            # checkpoint
            _write(items)
    _write(items)
    ok = sum(1 for it in items if it.get("rescore_status") == "ok")
    err = sum(1 for it in items if it.get("rescore_status") == "error")
    sk = sum(1 for it in items if it.get("rescore_status") == "skipped")
    print(f"[done] total={len(items)} ok={ok} skipped={sk} error={err} → {OUT_PATH}")
    return 0


def _write(items: list[dict]) -> None:
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    from app.neuro_grader import PIPELINE_VERSION
    payload = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "pipeline_version": PIPELINE_VERSION,
        "n_items": len(items),
        "items": items,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.exit(main())
