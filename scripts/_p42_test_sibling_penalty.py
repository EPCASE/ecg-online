# -*- coding: utf-8 -*-
"""P4.2 — test pénalité graduée exclusion-A frère-du-golden (S047/S134 vs S123)."""
import json, sys, os
BASE = r"c:\Users\Administrateur\bmad\ECG lecture\ecg-online"
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "rag_pipeline"))
os.chdir(BASE)

corpus_items = json.load(open(os.path.join(BASE, "data", "p42_corpus_rescored.json"), encoding="utf-8"))["items"]
corpus = {it["key"]: it for it in corpus_items}
key = {e["sample_id"]: e for e in json.load(open(os.path.join(BASE, "data", "p42_annotation_key.json"), encoding="utf-8"))["entries"]}

def find(sid):
    e = key.get(sid)
    return corpus.get(e["key"]) if e else None

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE, ".env"))
from app import neuro_grader as ng

for sid in ("S047", "S134", "S123"):
    it = find(sid)
    if not it:
        print(f"{sid}: introuvable dans le corpus"); continue
    num = it["cas"]
    texte = it["texte"]
    corr = ng.grade_neuro(num, texte)
    if corr is None:
        print(f"{sid}: corr=None (skip: {ng.last_skip_reason()})"); continue
    print(f"\n=== {sid} (cas {num}) ===")
    print(f"ancien : score={it.get('score')} adequation={it.get('score_adequation')} securite={it.get('score_securite')}")
    print(f"nouveau : score={corr.score} adequation={getattr(corr,'score_adequation',None)} securite={getattr(corr,'score_securite',None)}")
    for ev in (getattr(corr, "safety_events", None) or []):
        print(f"  event: {ev}")
