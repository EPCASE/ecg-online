#!/usr/bin/env python
"""
audit_golden_impact.py — Phase 0.2 : impact réel des anomalies golden.
========================================================================
Complète `scripts/audit_golden.py` (Phase 0.1, détection statique) en
croisant les concepts dupliqués (validant/descripteur) avec les réponses
RÉELLES d'étudiants (Google Sheet ECG Collector, feuille `reponses`), pour
prioriser : quels concepts dupliqués causent VRAIMENT une contradiction
visible (label à la fois « trouvé » et « manqué »), vs lesquels sont
inoffensifs en pratique (jamais déclenchés, ou déjà couverts par le
garde-fou de `neuro_grader._report_to_correction`).

Principe : rejoue chaque réponse « libre » de la banque 75 cas avec le
moteur ACTUEL (donc APRÈS le fix `_validant_manque_ids` déjà en prod) et
mesure :
  1. Contradictions résiduelles (label présent à la fois dans
     elements_trouves ET elements_manques) → doivent être à 0 (non-régression).
  2. Dérive de score significative (>= `--drift-threshold`, défaut 25 points)
     vs le score historique enregistré dans la feuille → à trier
     manuellement (peut être une amélioration du fix, ou un signal de
     nouvelle régression).
  3. Fréquence par cas des concepts dupliqués identifiés par
     `audit_golden.py` (pour prioriser Phase 1 : quels cas corriger dans
     `cases_golden.json` en premier).

Nécessite les credentials Google Sheets (`.streamlit/secrets.toml` du
projet ECG collector) — se dégrade proprement (message clair) si absents.

Usage :
    python scripts/audit_golden_impact.py
    python scripts/audit_golden_impact.py --drift-threshold 30 --json impact.json
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

# Force UTF-8 partout (évite le crash cp1252 sur les émojis du commentaire
# pédagogique quand la sortie est redirigée/capturée par un outil tiers).
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

DEFAULT_SECRETS_PATH = Path(r"C:\Users\Administrateur\ECG collector\.streamlit\secrets.toml")


@dataclass
class CaseImpact:
    cas: int
    nb_reponses: int = 0
    nb_contradictions: int = 0
    nb_drift: int = 0
    duplicated_concepts_triggered: Dict[str, int] = field(default_factory=dict)


def _load_secrets(path: Path) -> Optional[dict]:
    if not path.exists():
        print(f"⚠️  Secrets introuvables ({path}) — étape ignorée, "
              f"seule l'analyse statique golden reste disponible.", file=sys.stderr)
        return None
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore
    with open(path, "rb") as f:
        return tomllib.load(f)


def _fetch_reponses(secrets: dict) -> List[dict]:
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
        score_raw = r[idx.get("score", -1)] if "score" in idx else ""
        rows.append({
            "cas": int(cas_raw),
            "reponse": txt,
            "old_score": int(score_raw) if str(score_raw).isdigit() else None,
        })
    return rows


def _duplicated_concepts_by_case() -> Dict[int, List[str]]:
    """Réutilise le check statique de audit_golden.py pour savoir quels
    concepts sont dupliqués (validant/descripteur) dans chaque cas."""
    from scripts.audit_golden import _load_golden, check_duplicate_concept_role  # type: ignore
    golden = _load_golden()
    findings = check_duplicate_concept_role(golden)
    out: Dict[int, List[str]] = {}
    for f in findings:
        if f.case is None:
            continue
        out.setdefault(int(f.case), []).append(f.detail["concept_id"])
    return out


def run_impact(drift_threshold: int, secrets_path: Path) -> dict:
    dup_by_case = _duplicated_concepts_by_case()
    result = {
        "nb_reponses_total": 0,
        "nb_ok": 0,
        "nb_contradictions": 0,
        "nb_exceptions": 0,
        "nb_drift": 0,
        "contradictions_detail": [],
        "drift_detail": [],
        "cases": {},
    }

    secrets = _load_secrets(secrets_path)
    if secrets is None:
        return result

    rows = _fetch_reponses(secrets)
    result["nb_reponses_total"] = len(rows)

    from app import neuro_grader  # import tardif (charge l'index RAG, coûteux)

    per_case: Dict[int, CaseImpact] = {}

    for i, row in enumerate(rows):
        cas = row["cas"]
        ci = per_case.setdefault(cas, CaseImpact(cas=cas))
        ci.nb_reponses += 1

        try:
            corr = neuro_grader.grade_neuro(cas, row["reponse"])
        except Exception as ex:
            result["nb_exceptions"] += 1
            continue
        if corr is None:
            continue

        d = corr.to_dict()
        lbl_trouves = {e.get("label") for e in d.get("elements_trouves", [])}
        lbl_manques = {e.get("label") for e in d.get("elements_manques", [])}
        dup_labels = lbl_trouves & lbl_manques

        if dup_labels:
            result["nb_contradictions"] += 1
            ci.nb_contradictions += 1
            result["contradictions_detail"].append({
                "row": i, "cas": cas, "labels": sorted(dup_labels),
            })
        else:
            result["nb_ok"] += 1

        new_score = d.get("score")
        old_score = row["old_score"]
        if old_score is not None and new_score is not None and abs(new_score - old_score) >= drift_threshold:
            result["nb_drift"] += 1
            ci.nb_drift += 1
            result["drift_detail"].append({
                "row": i, "cas": cas, "old_score": old_score, "new_score": new_score,
            })

        for cid in dup_by_case.get(cas, []):
            ci.duplicated_concepts_triggered[cid] = ci.duplicated_concepts_triggered.get(cid, 0) + 1

    result["cases"] = {str(c): asdict(ci) for c, ci in sorted(per_case.items())}
    return result


def print_report(result: dict) -> None:
    print("=" * 78)
    print("AUDIT IMPACT GOLDEN — Phase 0.2 (réponses réelles)")
    print("=" * 78)
    if result["nb_reponses_total"] == 0:
        print("⚠️  Aucune réponse traitée (secrets manquants ou feuille vide).")
        return

    print(f"Réponses analysées : {result['nb_reponses_total']}")
    print(f"  ✅ OK (sans contradiction)   : {result['nb_ok']}")
    print(f"  🔴 Contradictions           : {result['nb_contradictions']}")
    print(f"  ⚠️  Exceptions (crash)       : {result['nb_exceptions']}")
    print(f"  🟡 Dérive de score notable  : {result['nb_drift']}")

    if result["contradictions_detail"]:
        print("\n🔴 Détail des contradictions (label trouvé ET manqué) :")
        for c in result["contradictions_detail"][:20]:
            print(f"   ligne {c['row']} / cas {c['cas']} : {c['labels']}")

    if result["drift_detail"]:
        print("\n🟡 Dérives de score notables :")
        for c in result["drift_detail"][:20]:
            print(f"   ligne {c['row']} / cas {c['cas']} : {c['old_score']} → {c['new_score']}")

    print("\n" + "-" * 78)
    print("Priorisation Phase 1 (concepts dupliqués réellement sollicités par cas) :")
    ranked = sorted(result["cases"].items(),
                     key=lambda kv: -sum(kv[1]["duplicated_concepts_triggered"].values()))
    for cas, ci in ranked[:15]:
        triggers = ci["duplicated_concepts_triggered"]
        if not triggers:
            continue
        print(f"   cas {cas} ({ci['nb_reponses']} réponses, "
              f"{ci['nb_contradictions']} contradiction(s)) : {triggers}")
    print("-" * 78)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--drift-threshold", type=int, default=25,
                         help="Écart de score (points) considéré comme une dérive notable.")
    parser.add_argument("--secrets", default=str(DEFAULT_SECRETS_PATH),
                         help="Chemin vers secrets.toml (credentials Google Sheets).")
    parser.add_argument("--json", metavar="FILE", help="Écrit le rapport structuré en JSON.")
    args = parser.parse_args()

    result = run_impact(args.drift_threshold, Path(args.secrets))
    print_report(result)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n📄 Rapport JSON écrit : {args.json}")

    return 1 if result["nb_contradictions"] or result["nb_exceptions"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
