#!/usr/bin/env python
"""
build_extraction_golden_sample.py — Construit l'échantillon du golden d'extraction.
=====================================================================================
Cf. GOLDEN_EXTRACTION.md pour la méthodologie complète (§1-§3).

Étapes :
  1. Récupère les réponses réelles (Google Sheet `reponses`, via le même
     mécanisme que `scripts/audit_golden_impact.py::_fetch_reponses`).
  2. Sélectionne 100 réponses par tirage STRATIFIÉ déterministe (seed=42) :
       a. >= 1 réponse par cas couvert (jusqu'à 47), en priorisant une
          longueur proche de la médiane du cas (évite les réponses dégénérées).
       b. Complète jusqu'à 100 en piochant dans les cas à fort volume,
          plafond de 5 réponses/cas.
       c. Marque 20% des items sélectionnés (seed fixe) en double annotation
          (pour le calcul du Kappa de Cohen).
  3. Pour chaque item sélectionné, rejoue le pipeline actuel
     (`candidate_report.generate_candidate_report`) via le contrat golden du
     cas (`golden_config.golden_for_scorer`) pour PRÉ-REMPLIR `pipeline_extraction`
     (l'annotateur corrige, ne repart pas de zéro).
  4. Écrit `data/extraction_golden.json` (cf. `app/extraction_golden.py`).

Usage :
    python scripts/build_extraction_golden_sample.py
    python scripts/build_extraction_golden_sample.py --n 100 --secrets <path>
    python scripts/build_extraction_golden_sample.py --no-prefill   # squelette seul, rapide
"""
from __future__ import annotations

import argparse
import io
import json
import os
import random
import sys
from pathlib import Path
from statistics import median
from typing import Dict, List

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

DEFAULT_SECRETS_PATH = Path(r"C:\Users\Administrateur\ECG collector\.streamlit\secrets.toml")
SEED = 42
DEFAULT_N = 100
DOUBLE_ANNOTATION_FRACTION = 0.20
CAP_PER_CASE = 5

OUTPUT_PATH = os.path.join(ROOT_DIR, "data", "extraction_golden.json")


def _load_secrets(path: Path) -> dict:
    if not path.exists():
        print(f"❌ Secrets introuvables ({path}) — impossible de récupérer les "
              f"réponses réelles. Abandon.", file=sys.stderr)
        sys.exit(1)
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore
    with open(path, "rb") as f:
        return tomllib.load(f)


def _fetch_reponses(secrets: dict) -> List[dict]:
    """Identique à audit_golden_impact.py::_fetch_reponses (dupliqué pour
    garder ce script autonome et sans dépendance croisée fragile)."""
    import gspread
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_info(
        secrets["google_sheets"],
        scopes=["https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"],
    )
    client = gspread.authorize(creds)
    sh = client.open_by_key(secrets["google_sheet_id"])
    ws = sh.worksheet("reponses")
    values = ws.get_all_values()
    header = values[0]
    idx = {h: i for i, h in enumerate(header)}
    rows = []
    for r in values[1:]:
        txt = r[idx.get("reponse", -1)].strip() if "reponse" in idx else ""
        if not txt:
            continue
        cas_raw = r[idx.get("cas", -1)] if "cas" in idx else ""
        if not str(cas_raw).isdigit():
            continue
        rows.append({"cas": int(cas_raw), "reponse": txt})
    return rows


def stratified_sample(rows: List[dict], n: int, seed: int = SEED,
                       cap_per_case: int = CAP_PER_CASE) -> List[dict]:
    """Tirage stratifié : >=1 réponse/cas (proche médiane), puis complément
    plafonné par cas dans les volumes restants. Déterministe (seed fixe)."""
    rng = random.Random(seed)
    by_case: Dict[int, List[dict]] = {}
    for r in rows:
        by_case.setdefault(r["cas"], []).append(r)

    selected: List[dict] = []
    remaining_by_case: Dict[int, List[dict]] = {}

    # Passe 1 : une réponse par cas couvert, proche de la longueur médiane.
    for cas, items in by_case.items():
        items_sorted = sorted(items, key=lambda x: len(x["reponse"]))
        med_len = median(len(x["reponse"]) for x in items)
        # réponse la plus proche de la médiane (déterministe : tie-break sur le texte)
        pick = min(items_sorted, key=lambda x: (abs(len(x["reponse"]) - med_len), x["reponse"]))
        selected.append(pick)
        rest = [x for x in items if x is not pick]
        rng.shuffle(rest)
        remaining_by_case[cas] = rest

    # Passe 2 : compléter jusqu'à n, en piochant proportionnellement au volume
    # restant, plafonné à cap_per_case par cas (déjà 1 pris en passe 1).
    taken_count = {cas: 1 for cas in by_case}
    pool = []
    for cas, rest in remaining_by_case.items():
        for item in rest:
            pool.append((cas, item))
    rng.shuffle(pool)

    i = 0
    while len(selected) < n and i < len(pool):
        cas, item = pool[i]
        i += 1
        if taken_count[cas] >= cap_per_case:
            continue
        selected.append(item)
        taken_count[cas] += 1

    if len(selected) < n:
        print(f"⚠️  Seulement {len(selected)} réponses disponibles sous contrainte "
              f"de plafond {cap_per_case}/cas (demandé : {n}). "
              f"Relâchement du plafond pour compléter.", file=sys.stderr)
        i = 0
        while len(selected) < n and i < len(pool):
            cas, item = pool[i]
            i += 1
            if item in selected:
                continue
            selected.append(item)

    return selected[:n]


def _prefill_pipeline_extraction(cas: int, texte: str) -> List[dict]:
    """Rejoue le pipeline actuel pour pré-remplir les concepts extraits.
    Renvoie [] si le pipeline est indisponible (dégradation propre)."""
    pipeline_dir = os.path.join(ROOT_DIR, "rag_pipeline")
    if pipeline_dir not in sys.path:
        sys.path.insert(0, pipeline_dir)
    try:
        from app import golden_config  # type: ignore
        from candidate_report import generate_candidate_report  # type: ignore
    except Exception as ex:
        print(f"⚠️  Pipeline indisponible ({ex}) — pré-remplissage ignoré.", file=sys.stderr)
        return []

    try:
        contract = golden_config.golden_for_scorer(cas)
        all_pts = contract.get("validants", []) + contract.get("descripteurs", [])
        golden_ids = [p["concept_id"] for p in all_pts]
        golden_names = [p["concept_name"] for p in all_pts]
        golden_roles = ["validant"] * len(contract.get("validants", [])) + \
            ["descripteur"] * len(contract.get("descripteurs", []))
        report = generate_candidate_report(
            texte,
            golden_names=golden_names,
            golden_ids=golden_ids,
            golden_roles=golden_roles,
            diagnostic_principal=contract.get("diagnostic_principal", ""),
            with_feedback=False,
        )
        out = []
        for c in getattr(report, "concepts_extraits", []) or []:
            out.append({
                "terme_brut": getattr(c, "terme_brut", ""),
                "ontology_id": getattr(c, "ontology_id", ""),
                "concept_name": getattr(c, "concept_name", ""),
                "statut": getattr(c, "statut", "present"),
                "method": getattr(c, "method", ""),
            })
        return out
    except Exception as ex:
        print(f"⚠️  Erreur pipeline pour cas {cas}: {ex}", file=sys.stderr)
        return []


def _prefill_gpt56_extraction(texte: str) -> List[dict]:
    """Second avis indépendant via GPT-5.6 (cf. GOLDEN_EXTRACTION.md §5bis).
    Ne voit JAMAIS la sortie du pipeline (pas de circularité). Dégradation
    propre (liste vide) si le modèle/la clé sont indisponibles."""
    try:
        from app import gpt_annotator  # type: ignore
    except Exception as ex:
        print(f"⚠️  gpt_annotator indisponible ({ex}) — second avis ignoré.", file=sys.stderr)
        return []
    return gpt_annotator.annotate(texte)


def build(n: int, secrets_path: Path, prefill: bool, gpt56: bool) -> dict:
    secrets = _load_secrets(secrets_path)
    print("📥 Récupération des réponses réelles (Google Sheet 'reponses')...")
    rows = _fetch_reponses(secrets)
    print(f"   {len(rows)} réponses non vides récupérées "
          f"({len(set(r['cas'] for r in rows))} cas couverts).")

    print(f"🎯 Tirage stratifié de {n} réponses (seed={SEED})...")
    selected = stratified_sample(rows, n, seed=SEED)
    print(f"   {len(selected)} réponses sélectionnées.")

    # Double annotation : 20% des items, tirage déterministe.
    rng = random.Random(SEED)
    idxs = list(range(len(selected)))
    rng.shuffle(idxs)
    n_double = round(len(selected) * DOUBLE_ANNOTATION_FRACTION)
    double_idxs = set(idxs[:n_double])

    items: Dict[str, dict] = {}
    per_case_counter: Dict[int, int] = {}
    for i, row in enumerate(selected):
        cas = row["cas"]
        per_case_counter[cas] = per_case_counter.get(cas, 0) + 1
        item_id = f"{cas}-{per_case_counter[cas]:02d}"
        pipeline_extraction = []
        if prefill:
            pipeline_extraction = _prefill_pipeline_extraction(cas, row["reponse"])
        gpt56_extraction = []
        if gpt56:
            gpt56_extraction = _prefill_gpt56_extraction(row["reponse"])
        items[item_id] = {
            "cas": cas,
            "reponse_texte": row["reponse"],
            "double_annotation": i in double_idxs,
            "pipeline_extraction": pipeline_extraction,
            "gpt56_extraction": gpt56_extraction,
            "annotation_expert": None,
            "annotation_expert_2": None if i in double_idxs else None,
        }
        if prefill:
            print(f"   [{i+1}/{len(selected)}] cas {cas} ({item_id}) : "
                  f"{len(pipeline_extraction)} concepts pré-extraits"
                  + (f", {len(gpt56_extraction)} suggestions GPT-5.6" if gpt56 else ""))

    from datetime import datetime
    data = {
        "version": 1,
        "created": datetime.now().isoformat(timespec="seconds"),
        "updated": datetime.now().isoformat(timespec="seconds"),
        "seed": SEED,
        "n_total": len(items),
        "n_double_annotation": n_double,
        "items": items,
    }
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=DEFAULT_N)
    ap.add_argument("--secrets", type=Path, default=DEFAULT_SECRETS_PATH)
    ap.add_argument("--no-prefill", action="store_true",
                     help="Ne pas rejouer le pipeline (squelette seul, rapide).")
    ap.add_argument("--gpt56", action="store_true",
                     help="Active le second avis indépendant GPT-5.6 (cf. §5bis). "
                          "Coûteux en appels API : à utiliser une fois l'échantillon stabilisé.")
    ap.add_argument("--out", type=Path, default=Path(OUTPUT_PATH))
    args = ap.parse_args()

    data = build(args.n, args.secrets, prefill=not args.no_prefill, gpt56=args.gpt56)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Écrit {args.out} — {data['n_total']} items "
          f"({data['n_double_annotation']} en double annotation).")


if __name__ == "__main__":
    main()
