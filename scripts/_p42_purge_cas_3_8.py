# -*- coding: utf-8 -*-
"""Purge ciblée des cas 3 et 8 dans p42_corpus_rescored.json (P4.2, 2026-08-12)
avant re-rejeu avec le golden override (variante 2 + golden enrichi).
Les items retirés seront rejoués par p42_ingest_and_rescore --resume."""
import json
import shutil

P = r"c:\Users\Administrateur\bmad\ECG lecture\ecg-online\data\p42_corpus_rescored.json"
shutil.copy2(P, P + ".bak_avant_override")

with open(P, encoding="utf-8") as f:
    d = json.load(f)

before = len(d["items"])
d["items"] = [it for it in d["items"] if it.get("cas") not in (3, 8)]
d["n_items"] = len(d["items"])

with open(P, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=1)
print(f"purge: {before - len(d['items'])} copies cas 3/8 retirées "
      f"({before} → {len(d['items'])})")

