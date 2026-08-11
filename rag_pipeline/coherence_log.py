# -*- coding: utf-8 -*-
"""
coherence_log.py — P4.3c étape 0 : instrumentation PASSIVE des paires candidates.
==================================================================================
Journalise en JSONL chaque contradiction potentielle détectée par le moteur de
cohérence (P4.3b), avec les spans textuels des deux concepts. AUCUN effet sur
le scoring — pur enregistrement, pour :
  1. mesurer la fréquence réelle des paires candidates sur les copies réelles
     (critère d'abandon P4.3c : < ~1 % → le juge contextuel ne vaut pas le coût) ;
  2. constituer le corpus d'arbitrage (juge LLM offline + annotation expert,
     étapes 1-2 du protocole docs/P4.3c_brainstorm_juge_contextuel_2026_08_11.md).

Format d'une ligne :
    {"ts": "...", "case": 49, "concept_a": "...", "concept_b": "...",
     "kind": "conflicts_by_default", "severity": "warning", "status": "active",
     "detail": "", "spans_a": ["phrase 1"], "spans_b": ["phrase 2"],
     "pipeline_version": "neuro-v1.2"}

Le chemin est surchargeable par COHERENCE_LOG_PATH (utile en test/deploy).
Robustesse : ne lève JAMAIS (l'instrumentation ne doit pas casser une note).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "coherence_pairs_log.jsonl"


def log_candidate_pairs(case_num, contradictions, spans_by_concept,
                        pipeline_version: str = "") -> None:
    """Append une ligne JSONL par contradiction (tous états confondus).

    `spans_by_concept` : dict {ontology_id: [contexte_phrase, ...]} — toutes
    les occurrences, pas le max agrégé (cas limite n°6 du brainstorm).
    """
    if not contradictions:
        return
    try:
        path = Path(os.environ.get("COHERENCE_LOG_PATH", str(_DEFAULT_PATH)))
        path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with open(path, "a", encoding="utf-8") as f:
            for ct in contradictions:
                f.write(json.dumps({
                    "ts": ts,
                    "case": case_num,
                    "concept_a": ct.concept_a,
                    "concept_b": ct.concept_b,
                    "kind": ct.kind,
                    "severity": ct.severity,
                    "status": ct.status,
                    "detail": ct.detail,
                    "spans_a": spans_by_concept.get(ct.concept_a, []),
                    "spans_b": spans_by_concept.get(ct.concept_b, []),
                    "pipeline_version": pipeline_version,
                }, ensure_ascii=False) + "\n")
    except Exception:
        pass  # l'instrumentation ne casse jamais une correction
