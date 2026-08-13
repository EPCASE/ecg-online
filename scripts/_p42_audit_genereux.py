# -*- coding: utf-8 -*-
"""P4.2 point b — audit des copies « machine trop généreuse » (2026-08-12).
S049/S041/S101/S107 (+S022/S139) : machine 100, expert 20-50.
Affiche golden du cas, concepts détectés et commentaire expert."""
import csv
import json

DATA = r"c:\Users\Administrateur\bmad\ECG lecture\ecg-online\data"
SIDS = ["S049", "S041", "S101", "S107", "S022", "S139", "S053"]

with open(DATA + r"\p42_annotation_key.json", encoding="utf-8") as f:
    key = {e["sample_id"]: e for e in json.load(f)["entries"]}
with open(DATA + r"\p42_corpus_rescored.json", encoding="utf-8") as f:
    corpus = {it["key"]: it for it in json.load(f)["items"]}
with open(DATA + r"\p42_annotation_blind.csv", encoding="utf-8-sig") as f:
    ann = {r["sample_id"]: r for r in csv.DictReader(f, delimiter=";")}

import sys
sys.path.insert(0, r"c:\Users\Administrateur\bmad\ECG lecture\ecg-online")
from app import golden_config
from app.neuro_grader import grade_neuro

for sid in SIDS:
    k = key[sid]
    it = corpus[k["key"]]
    a = ann.get(sid, {})
    g = golden_config.golden_for_scorer(it["cas"])
    print("=" * 78)
    print(f"{sid} cas {it['cas']} — machine={k['score_machine']} "
          f"(adeq={k.get('score_adequation')}, secu={k.get('score_securite')}) "
          f"expert={a.get('note_expert_0_100')} grave={a.get('q_erreur_grave')}")
    print(f"diag principal du cas : {g['diagnostic_principal']}")
    print(f"texte : {it['texte'][:250]!r}")
    print(f"commentaire expert : {a.get('q_commentaire','')!r}")
    print("validants golden :", [(v['concept_id'], v['rang']) for v in g['validants']])
    r = grade_neuro(it["cas"], it["texte"])
    d = r.to_dict() if r else {}
    print(f"score rejoué : {d.get('score')} (adeq={d.get('score_adequation')})")
    print("concepts detectes :")
    for c in d.get("concepts_detectes", []):
        print(f"   {c.get('id')} [{c.get('statut')}] {(c.get('concept') or '')[:45]}")
