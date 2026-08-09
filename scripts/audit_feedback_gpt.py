#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_feedback_gpt.py — Étape 2 : juge GPT de la qualité rédactionnelle du feedback IA
========================================================================================
Prend le fichier produit par `audit_feedback_quality.py` (100 triplets
{score, réponse étudiant, commentaire IA généré}) et soumet CHAQUE item à un
juge GPT (par défaut un modèle de raisonnement fort, ex. "gpt-5" si
disponible — configurable) pour évaluer la qualité RÉDACTIONNELLE (pas la
justesse du score, déjà auditée ailleurs) :

  - adaptation : le commentaire est-il cohérent avec ce que l'étudiant a
    réellement écrit (pas de contresens, pas de réponse générique hors-sol) ?
  - incohérence : y a-t-il une contradiction interne (ex : féliciter puis
    dire que le concept est manqué, ou l'inverse) ?
  - redondance : le texte répète-t-il inutilement les mêmes informations
    entre les sections "Référence au cours" et "Votre interprétation" ?
  - clarté pédagogique : le ton et le niveau sont-ils adaptés (interne en
    médecine) ?

Sortie : un JSON avec, pour chaque item, un verdict structuré (scores 1-5 sur
chaque axe + liste de problèmes détectés + suggestion d'amélioration), plus
un résumé agrégé (fréquence des problèmes) exploitable pour l'audit humain.

Usage :
    python scripts/audit_feedback_gpt.py --in data/audit_feedback_2026-08-05.json \
        --out data/audit_feedback_gpt_verdict_2026-08-05.json --model gpt-4o

Prérequis : OPENAI_API_KEY dans .env.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

ECG_ONLINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ECG_ONLINE_DIR))

from dotenv import load_dotenv  # type: ignore
load_dotenv(ECG_ONLINE_DIR / ".env")

from openai import OpenAI  # type: ignore

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY absente.")
        _client = OpenAI(api_key=api_key)
    return _client


JUDGE_SYSTEM_PROMPT = """Tu es un expert en pédagogie médicale ET en cardiologie (lecture d'ECG),
chargé d'auditer la QUALITÉ RÉDACTIONNELLE d'un feedback généré par IA pour
un étudiant en médecine après correction automatique de son interprétation
ECG en texte libre.

Tu ne réévalues PAS si le score numérique est juste (un autre audit s'en
charge). Tu juges UNIQUEMENT si le TEXTE du feedback est :
  1. adapté à ce que l'étudiant a réellement écrit (pas de contresens, pas
     de generic/hors-sol, ne prétend pas que l'étudiant a dit quelque chose
     qu'il n'a pas dit, ne l'accuse pas d'avoir manqué quelque chose qu'il a
     en fait mentionné avec d'autres mots) ;
  2. interne cohérent (pas de contradiction entre les sections, pas de
     paradoxe entre le ton "félicitations" et un score bas, ou l'inverse) ;
  3. non redondant (les 2 sections n'répètent pas la même info sans valeur
     ajoutée) ;
  4. cliniquement exact (aucune affirmation médicale fausse ou trompeuse) ;
  5. bien calibré en ton/longueur pour un interne en médecine.

Réponds UNIQUEMENT via l'outil `rendre_verdict`."""

JUDGE_TOOL = {
    "type": "function",
    "function": {
        "name": "rendre_verdict",
        "description": "Verdict structuré sur la qualité rédactionnelle d'un feedback IA.",
        "parameters": {
            "type": "object",
            "properties": {
                "adaptation_score": {"type": "integer", "minimum": 1, "maximum": 5,
                    "description": "1=complètement inadapté/contresens, 5=parfaitement adapté à la réponse réelle de l'étudiant"},
                "coherence_score": {"type": "integer", "minimum": 1, "maximum": 5,
                    "description": "1=contradictions internes flagrantes, 5=parfaitement cohérent"},
                "redondance_score": {"type": "integer", "minimum": 1, "maximum": 5,
                    "description": "1=très redondant (répète la même chose), 5=aucune redondance inutile"},
                "exactitude_clinique_score": {"type": "integer", "minimum": 1, "maximum": 5,
                    "description": "1=erreur médicale manifeste, 5=parfaitement exact"},
                "ton_pedagogique_score": {"type": "integer", "minimum": 1, "maximum": 5,
                    "description": "1=ton inadapté (trop dur/trop mou/déplacé), 5=ton bien calibré"},
                "problemes_detectes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Liste courte des problèmes concrets identifiés (vide si aucun)."
                },
                "verdict_global": {
                    "type": "string",
                    "enum": ["excellent", "acceptable", "problematique", "inadapte"],
                    "description": "Synthèse globale de la qualité rédactionnelle."
                },
                "suggestion_amelioration": {
                    "type": "string",
                    "description": "Une phrase concrète pour améliorer ce feedback (vide si aucun problème)."
                },
            },
            "required": ["adaptation_score", "coherence_score", "redondance_score",
                          "exactitude_clinique_score", "ton_pedagogique_score",
                          "problemes_detectes", "verdict_global", "suggestion_amelioration"],
        },
    },
}


def _build_user_prompt(item: Dict) -> str:
    parts = [
        f"## Cas ECG n°{item.get('num_cas')} — diagnostic attendu : {item.get('diagnostic_principal_golden', '?')}",
        f"\n### Réponse de l'étudiant (texte libre) :\n« {item.get('reponse_etudiant', '')} »",
        f"\n### Score attribué par le pipeline : {item.get('score_regenere')}/100",
    ]
    vd = item.get("validant_details") or []
    if vd:
        parts.append("\n### Concepts validants (rang A) — trouvé/manqué :")
        for v in vd:
            statut = "✓ trouvé" if v.get("found") else "✗ manqué"
            parts.append(f"  - {v.get('golden_name')} : {statut} ({v.get('score_pct')}%)")
    dd = item.get("descripteur_details") or []
    if dd:
        parts.append("\n### Descripteurs (indicatifs) :")
        for d in dd:
            statut = "✓ trouvé" if d.get("found") else "✗ manqué"
            parts.append(f"  - {d.get('golden_name')} : {statut}")
    dec = item.get("decouvertes") or []
    if dec:
        parts.append("\n### Découvertes (concepts vrais hors barème) :")
        for x in dec:
            parts.append(f"  - {x.get('concept_name')}")
    parts.append(f"\n### Feedback IA généré (à auditer) :\n{item.get('commentaire_ia', '(absent)')}")
    return "\n".join(parts)


def judge_item(item: Dict, model: str) -> Dict:
    if item.get("erreur") or not item.get("commentaire_ia"):
        return {"skipped": True, "reason": item.get("erreur") or "pas_de_commentaire_ia"}

    client = get_client()
    user_prompt = _build_user_prompt(item)

    kwargs: Dict = dict(
        model=model,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        tools=[JUDGE_TOOL],  # type: ignore[arg-type]
        tool_choice={"type": "function", "function": {"name": "rendre_verdict"}},
    )
    # Les modèles "reasoning" (ex: gpt-5.x) n'acceptent pas temperature, et
    # exigent reasoning_effort="none" pour utiliser le function-calling en
    # /v1/chat/completions.
    is_reasoning_model = model.startswith("gpt-5") or model.startswith("o1") or model.startswith("o3")
    if is_reasoning_model:
        kwargs["reasoning_effort"] = "none"
    else:
        kwargs["temperature"] = 0.0

    resp = client.chat.completions.create(**kwargs)
    tool_calls = resp.choices[0].message.tool_calls or []
    if not tool_calls:
        return {"skipped": True, "reason": "pas_de_tool_call"}
    args = json.loads(tool_calls[0].function.arguments)  # type: ignore[union-attr]
    return args


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="in_path", type=str, required=True)
    parser.add_argument("--out", type=str, default=None)
    parser.add_argument("--model", type=str, default="gpt-4o-2024-08-06")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    in_path = Path(args.in_path)
    data = json.load(open(in_path, encoding="utf-8"))
    items = data.get("items", [])
    if args.limit:
        items = items[:args.limit]

    if not args.out:
        args.out = str(in_path.parent / f"{in_path.stem}_gpt_verdict.json")

    print(f"🔎 Audit GPT ({args.model}) de {len(items)} feedbacks...")
    verdicts = []
    t0 = time.time()
    for i, item in enumerate(items, 1):
        try:
            v = judge_item(item, args.model)
        except Exception as ex:
            v = {"skipped": True, "reason": f"exception: {type(ex).__name__}: {ex}"}
        verdicts.append({
            "code": item.get("code"),
            "num_cas": item.get("num_cas"),
            "score_regenere": item.get("score_regenere"),
            "verdict": v,
        })
        tag = v.get("verdict_global", "SKIPPED") if not v.get("skipped") else f"SKIPPED({v.get('reason')})"
        print(f"[{i}/{len(items)}] {item.get('code')} cas {item.get('num_cas')} → {tag}")

    elapsed = time.time() - t0
    print(f"\n⏱️  Terminé en {elapsed:.1f}s")

    # ── Résumé agrégé ────────────────────────────────────────────────────
    valid_verdicts = [v["verdict"] for v in verdicts if not v["verdict"].get("skipped")]
    n_valid = len(valid_verdicts)
    summary: Dict = {"n_items": len(items), "n_valid": n_valid, "n_skipped": len(items) - n_valid}
    if n_valid:
        for axis in ["adaptation_score", "coherence_score", "redondance_score",
                     "exactitude_clinique_score", "ton_pedagogique_score"]:
            vals = [v[axis] for v in valid_verdicts if axis in v]
            summary[f"{axis}_moyenne"] = round(sum(vals) / len(vals), 2) if vals else None
        from collections import Counter
        verdict_counts = Counter(v.get("verdict_global") for v in valid_verdicts)
        summary["verdict_global_distribution"] = dict(verdict_counts)
        all_problems = []
        for v in valid_verdicts:
            all_problems.extend(v.get("problemes_detectes") or [])
        summary["n_total_problemes_detectes"] = len(all_problems)
        summary["exemples_problemes"] = all_problems[:20]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "judge_model": args.model,
            "source_file": str(in_path),
            "summary": summary,
            "verdicts": verdicts,
        }, f, ensure_ascii=False, indent=2)
    print(f"💾 Verdicts écrits dans : {out_path}")
    print(f"\n📊 Résumé : {json.dumps(summary, ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    main()
