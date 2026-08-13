# -*- coding: utf-8 -*-
"""P4.2 — inspection S014 + test 'hypothèse écartée puis conclusion' (arbitrage TV/FA)."""
import json, os, sys
BASE = r"c:\Users\Administrateur\bmad\ECG lecture\ecg-online"
sys.path.insert(0, BASE); sys.path.insert(0, os.path.join(BASE, "rag_pipeline")); os.chdir(BASE)

key = {e["sample_id"]: e for e in json.load(open(r"data\p42_annotation_key.json", encoding="utf-8"))["entries"]}
corpus = {it["key"]: it for it in json.load(open(r"data\p42_corpus_rescored.json", encoding="utf-8"))["items"]}
it = corpus[key["S014"]["key"]]
print("=== S014, cas", it["cas"], "===")
print("texte:", it["texte"])
print("score:", it["score"], "| adequation:", it["score_adequation"], "| securite:", it["score_securite"])
for c in it.get("concepts", []):
    print(f"  {c.get('terme','')!r} -> {c.get('id','')} [{c.get('statut','')}]")

print("\n=== Test raisonnement : hypothèse TV écartée, conclusion FA+BBG (cas 31) ===")
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE, ".env"))
from app import neuro_grader as ng
texte = ("Cette tachycardie à QRS large peut évoquer une TV mais en présence "
         "d'une irrégularité et d'un aspect de BBG, je conclus FA avec BBG.")
corr = ng.grade_neuro(31, texte)
if corr is None:
    print("corr=None:", ng.last_skip_reason()); sys.exit(1)
print("score:", corr.score, "| adequation:", getattr(corr, "score_adequation", None),
      "| securite:", getattr(corr, "score_securite", None))
for ev in (getattr(corr, "safety_events", None) or []):
    print("  event:", ev.get("kind"), ev.get("concept_ids"), ev.get("status"), "penalty", ev.get("penalty"))
