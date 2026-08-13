# -*- coding: utf-8 -*-
"""P4.2 (2026-08-13) — rejeu CIBLÉ des copies portant un golden_exclusion_A actif,
après introduction de SAFETY_PENALTY_EXCLUSION_A_SIBLING (50 au lieu de 75 quand
le concept exclu affirmé est un frère ontologique direct d'un validant golden).
Met à jour p42_corpus_rescored.json en place (backup .bak_avant_sibling)."""
import json, os, shutil, sys, time

BASE = r"c:\Users\Administrateur\bmad\ECG lecture\ecg-online"
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "rag_pipeline"))
os.chdir(BASE)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE, ".env"))
from app import neuro_grader as ng

PATH = os.path.join(BASE, "data", "p42_corpus_rescored.json")
shutil.copyfile(PATH, PATH + ".bak_avant_sibling")

data = json.load(open(PATH, encoding="utf-8"))
targets = [it for it in data["items"]
           if any(ev.get("kind") == "golden_exclusion_A" and ev.get("status") == "active"
                  for ev in (it.get("safety_events") or []))]
print(f"{len(targets)} copies à rejouer (golden_exclusion_A actif)")

changed = 0
for i, it in enumerate(targets, 1):
    corr = ng.grade_neuro(it["cas"], it["texte"])
    if corr is None:
        print(f"  [{i}] {it['key']}: SKIP ({ng.last_skip_reason()})"); continue
    old = (it.get("score"), it.get("score_securite"))
    it["score"] = corr.score
    it["score_adequation"] = getattr(corr, "score_adequation", None)
    it["score_securite"] = getattr(corr, "score_securite", None)
    it["correspondance"] = getattr(corr, "correspondance", it.get("correspondance"))
    it["type_erreur"] = getattr(corr, "type_erreur", it.get("type_erreur"))
    ev = getattr(corr, "safety_events", None)
    if ev is not None:
        it["safety_events"] = ev
    new = (it["score"], it["score_securite"])
    flag = " <-- CHANGÉ" if old != new else ""
    if old != new:
        changed += 1
    print(f"  [{i}/{len(targets)}] cas{it['cas']:>2} score {old[0]}→{new[0]} secu {old[1]}→{new[1]}{flag}")
    time.sleep(0.2)

json.dump(data, open(PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n{changed} copies modifiées. Corpus sauvegardé → {PATH}")
