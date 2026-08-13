# -*- coding: utf-8 -*-
"""Met à jour p42_annotation_key.json avec les scores machine actuels du
corpus rescoré (après re-rejeu cas 3/8 avec golden override, P4.2 2026-08-12).
La strate d'origine est CONSERVÉE (elle documente l'échantillonnage initial)."""
import json
import shutil

DATA = r"c:\Users\Administrateur\bmad\ECG lecture\ecg-online\data"
KEY = DATA + r"\p42_annotation_key.json"
CORPUS = DATA + r"\p42_corpus_rescored.json"

with open(CORPUS, encoding="utf-8") as f:
    corpus = {it["key"]: it for it in json.load(f)["items"]}
with open(KEY, encoding="utf-8") as f:
    key = json.load(f)

shutil.copy2(KEY, KEY + ".bak_avant_override")
changed = 0
for e in key["entries"]:
    it = corpus.get(e["key"])
    if not it or it.get("rescore_status") != "ok":
        continue
    if e.get("score_machine") != it.get("score"):
        print(f"{e['sample_id']} cas{e['cas']:>2} : {e.get('score_machine')} → {it.get('score')}")
        changed += 1
    e["score_machine"] = it.get("score")
    e["score_adequation"] = it.get("score_adequation")
    e["score_securite"] = it.get("score_securite")

with open(KEY, "w", encoding="utf-8") as f:
    json.dump(key, f, ensure_ascii=False, indent=1)
print(f"\n{changed} scores mis à jour dans la clé")
