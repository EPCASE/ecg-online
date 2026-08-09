#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_feedback_quality.py — Audit qualité rédactionnelle du feedback IA
=========================================================================
Contexte : des étudiantes signalent que le texte de correction affiché après
le score est INADAPTÉ à ce qu'elles ont écrit, avec des incohérences.

⚠️ IMPORTANT (découvert le 2026-08-05) : l'app EN PRODUCTION que les
étudiantes utilisent réellement est `ECG collector` (Streamlit, 15 cas
historiques, référentiel `ECG collector/corrections/golden.json`) — PAS
`ecg-online` (nouveau projet en développement, 75 cas curriculum, golden
différent). Utiliser le golden de `ecg-online` sur des réponses de
`ECG collector` produit des faux résultats (numérotation de cas différente,
diagnostics différents). Ce script utilise donc :
  - Le golden RÉEL de production : `ECG collector/corrections/golden.json`
    (15 cas, `diagnostic_principal` + `annotations` avec `annotation_role`
    "🎯 Diagnostic validant" / "📝 Description").
  - Le pipeline canonique `ECG lecture/rag_pipeline/candidate_report.py`
    (version dont dérive le vendoring dans `ecg-online`), qui correspond à
    `RAG Neurosymbolique v1.1 (C1+C2)` — la version indiquée dans les JSON
    étudiants les plus récents.

Ce script :
  1. Sélectionne les N dernières réponses étudiantes RÉELLES (par défaut 100),
     depuis `ECG collector/corrections/students/*.json` (triées par
     `generated_at` décroissant).
  2. Convertit le golden de chaque cas (`golden.json`) en contrat
     golden_ids/golden_names/golden_roles via l'ontologie (`semantic_layer`).
  3. Rejoue le pipeline de correction ACTUEL
     (`candidate_report.generate_candidate_report(with_feedback=True)`
     → `pedagogical_feedback.generate_pedagogical_feedback`) pour régénérer
     un feedback texte FRAIS.
  4. Sauvegarde un fichier plat {score, cas, reponse_etudiant, feedback_texte,
     elements_trouves, elements_manques, erreur} exploitable pour audit humain
     ou pour soumission à un juge LLM (étape 2 : audit_feedback_gpt.py).

Usage :
    python scripts/audit_feedback_quality.py --limit 100
    python scripts/audit_feedback_quality.py --limit 100 --out data/audit_feedback_2026-08-05.json

Prérequis : OPENAI_API_KEY dans .env (le feedback pédagogique + la résolution
LLM des termes ambigus nécessitent des appels API — coût et latence réels,
~10-15s par réponse).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# ── Chemins ──────────────────────────────────────────────────────────────
ECG_ONLINE_DIR = Path(__file__).resolve().parent.parent
STUDENTS_DIR = Path(r"C:\Users\Administrateur\ECG collector\corrections\students")
GOLDEN_PATH = Path(r"C:\Users\Administrateur\ECG collector\corrections\golden.json")
# Pipeline CANONIQUE (pas le vendoré ecg-online, dont le golden ne correspond
# pas aux mêmes cas) — c'est celui utilisé pour générer les students/*.json.
PIPELINE_DIR = Path(r"C:\Users\Administrateur\bmad\ECG lecture\rag_pipeline")

sys.path.insert(0, str(PIPELINE_DIR))

from dotenv import load_dotenv  # type: ignore
# La clé API vit dans ecg-online/.env (vérifié présente) — on la charge d'ici.
load_dotenv(ECG_ONLINE_DIR / ".env")

import candidate_report  # type: ignore  # noqa: E402
from hybrid_search import HybridSearchEngine  # type: ignore  # noqa: E402
from semantic_layer import get_concept, normalize_key, _get_ontology_v2  # type: ignore  # noqa: E402


# ── Construction du golden (concept_name → ontology_id) ─────────────────────
def _build_name_to_id_index() -> Dict[str, str]:
    onto = _get_ontology_v2()
    concepts = onto.get("concepts", onto)
    idx: Dict[str, str] = {}
    for cid, c in concepts.items():
        name = str(c.get("concept_name", "")).strip().lower()
        if name:
            idx[name] = cid
    return idx


_NAME_TO_ID = _build_name_to_id_index()


def golden_for_case(golden_data: dict, num: str) -> Optional[Dict]:
    """Convertit l'entrée `golden.json[num]` en contrat golden_ids/names/roles
    pour `generate_candidate_report`. Retourne None si le concept validant
    principal n'est pas résolvable dans l'ontologie (cas à ignorer)."""
    entry = golden_data.get(str(num))
    if not entry:
        return None
    golden_ids, golden_names, golden_roles = [], [], []
    unresolved = []
    for ann in entry.get("annotations", []):
        concept_name = str(ann.get("concept", "")).strip()
        cid = _NAME_TO_ID.get(concept_name.lower())
        if not cid:
            unresolved.append(concept_name)
            continue
        role_raw = str(ann.get("annotation_role", ""))
        role = "validant" if "validant" in role_raw.lower() else "descripteur"
        golden_ids.append(cid)
        golden_names.append(concept_name)
        golden_roles.append(role)
    if not any(r == "validant" for r in golden_roles):
        return None  # rien à noter
    return {
        "golden_ids": golden_ids,
        "golden_names": golden_names,
        "golden_roles": golden_roles,
        "diagnostic_principal": entry.get("diagnostic_principal", ""),
        "commentaire_correcteur": entry.get("commentaire_correcteur", ""),
        "unresolved": unresolved,
    }


_ENGINE: Optional["HybridSearchEngine"] = None


def _engine() -> "HybridSearchEngine":
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = HybridSearchEngine()
    return _ENGINE



def collect_recent_real_answers(limit: int) -> List[Dict]:
    """Retourne les `limit` dernières réponses étudiantes réelles non vides,
    triées par `generated_at` décroissant, dédupliquées par (code, num_cas).
    """
    items = []
    for f in glob.glob(str(STUDENTS_DIR / "*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        code = d.get("code", os.path.basename(f))
        gen_at = d.get("generated_at", "")
        for num, case in (d.get("cases") or {}).items():
            txt = (case.get("student_text") or "").strip()
            if not txt or txt.lower() == "nan":
                continue
            rep = case.get("report") or {}
            items.append({
                "code": code,
                "num_cas": int(num) if str(num).isdigit() else num,
                "student_text": txt,
                "generated_at": gen_at,
                "score_pipeline_batch": rep.get("score_final_pct"),
            })
    items.sort(key=lambda x: x["generated_at"], reverse=True)
    # Dédupliquer (garder la version la plus récente d'un même (code, num_cas))
    seen = set()
    deduped = []
    for it in items:
        key = (it["code"], it["num_cas"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)
    return deduped[:limit]


def regenerate_feedback(item: Dict, golden_data: dict) -> Dict:
    """Rejoue le pipeline de correction actuel sur (num_cas, student_text) et
    retourne un dict plat prêt pour l'audit."""
    num = item["num_cas"]
    texte = item["student_text"]
    out = {
        "code": item["code"],
        "num_cas": num,
        "reponse_etudiant": texte,
        "score_pipeline_batch_ancien": item.get("score_pipeline_batch"),
        "generated_at_original": item.get("generated_at"),
    }

    g = golden_for_case(golden_data, num)
    if g is None:
        out["erreur"] = f"golden_non_resoluble_pour_cas_{num}"
        return out
    if g["unresolved"]:
        out["golden_unresolved"] = g["unresolved"]  # avertissement, pas bloquant

    try:
        report = candidate_report.generate_candidate_report(
            texte_etudiant=texte,
            golden_ids=g["golden_ids"],
            golden_names=g["golden_names"],
            golden_roles=g["golden_roles"],
            diagnostic_principal=g["diagnostic_principal"],
            moteur=_engine(),
            with_feedback=True,
            commentaire_correcteur=g["commentaire_correcteur"],
        )
    except Exception as ex:
        out["erreur"] = f"exception_appel: {type(ex).__name__}: {ex}"
        return out

    if getattr(report, "erreur", None):
        out["erreur"] = str(report.erreur)
        return out

    out["score_regenere"] = getattr(report, "score_final_pct", None)
    out["diagnostic_principal_golden"] = g["diagnostic_principal"]
    fb = getattr(report, "feedback_pedagogique", None)
    if fb is not None:
        out["commentaire_ia"] = getattr(fb, "texte", None)  # ← LE texte affiché après le score
        if getattr(fb, "erreur", None):
            out["feedback_erreur"] = fb.erreur
    else:
        out["commentaire_ia"] = None
        out["feedback_erreur"] = "pas_de_feedback_pedagogique_genere"

    out["validant_details"] = [
        {"golden_name": vd.golden_name, "found": vd.found, "score_pct": vd.score_pct}
        for vd in getattr(report, "validant_details", [])
    ]
    out["descripteur_details"] = [
        {"golden_name": dd.golden_name, "found": dd.found}
        for dd in getattr(report, "descripteur_details", [])
    ]
    out["decouvertes"] = [
        {"concept_name": getattr(dec, "concept_name", None)}
        for dec in getattr(report, "decouvertes", [])
    ]
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--out", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true",
                         help="N'appelle pas le pipeline, affiche juste la sélection.")
    args = parser.parse_args()

    if not args.out:
        stamp = time.strftime("%Y-%m-%d")
        args.out = str(ECG_ONLINE_DIR / "data" / f"audit_feedback_{stamp}.json")

    print(f"📥 Recherche des {args.limit} dernières réponses réelles dans {STUDENTS_DIR}")
    items = collect_recent_real_answers(args.limit)
    print(f"   → {len(items)} réponses trouvées "
          f"(de {items[-1]['generated_at'] if items else '?'} "
          f"à {items[0]['generated_at'] if items else '?'})")

    if args.dry_run:
        for it in items[:10]:
            print(f"  [{it['generated_at']}] {it['code']} cas {it['num_cas']} : "
                  f"{it['student_text'][:60]!r}")
        return

    golden_data = json.load(open(GOLDEN_PATH, encoding="utf-8"))

    results = []
    n_errors = 0
    t0 = time.time()
    for i, item in enumerate(items, 1):
        r = regenerate_feedback(item, golden_data)
        results.append(r)
        status = "❌" if r.get("erreur") else "✅"
        if r.get("erreur"):
            n_errors += 1
        print(f"[{i}/{len(items)}] {status} {item['code']} cas {item['num_cas']} "
              f"— score={r.get('score_regenere')}"
              + (f" — ERREUR: {r['erreur']}" if r.get("erreur") else ""))

    elapsed = time.time() - t0
    print(f"\n⏱️  Terminé en {elapsed:.1f}s ({n_errors} erreurs / {len(results)})")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pipeline_version": "RAG Neurosymbolique v1.1 (C1+C2) — rejoué depuis ECG lecture/rag_pipeline",
            "golden_source": str(GOLDEN_PATH),
            "n_items": len(results),
            "n_errors": n_errors,
            "items": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"💾 Rapport écrit dans : {out_path}")


if __name__ == "__main__":
    main()
