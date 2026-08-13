# -*- coding: utf-8 -*-
"""P4.2 point c — audit sécurité (2026-08-13).
FN : grave selon expert mais score_securite=100 (rien détecté).
FP : score_securite<100 mais pas grave selon expert.
Affiche texte, diag du cas, commentaire expert, safety_events, exclusions golden."""
import csv
import json
import sys

DATA = r"c:\Users\Administrateur\bmad\ECG lecture\ecg-online\data"
FN = ["S014", "S017", "S046", "S049", "S077", "S083", "S087", "S116"]
FP = ["S030", "S047", "S074", "S123", "S134"]

with open(DATA + r"\p42_annotation_key.json", encoding="utf-8") as f:
    key = {e["sample_id"]: e for e in json.load(f)["entries"]}
with open(DATA + r"\p42_corpus_rescored.json", encoding="utf-8") as f:
    corpus = {it["key"]: it for it in json.load(f)["items"]}
with open(DATA + r"\p42_annotation_blind.csv", encoding="utf-8-sig") as f:
    ann = {r["sample_id"]: r for r in csv.DictReader(f, delimiter=";")}

sys.path.insert(0, r"c:\Users\Administrateur\bmad\ECG lecture\ecg-online")
from app import golden_config

def show(sids, titre):
    print("#" * 78)
    print("#", titre)
    for sid in sids:
        k = key[sid]
        it = corpus[k["key"]]
        a = ann.get(sid, {})
        g = golden_config.golden_for_scorer(it["cas"])
        print("=" * 78)
        print(f"{sid} cas {it['cas']} — machine={k['score_machine']} secu={k.get('score_securite')} "
              f"expert={a.get('note_expert_0_100')} grave={a.get('q_erreur_grave')}")
        print(f"diag cas : {g['diagnostic_principal'][:80]}")
        print(f"texte    : {it['texte'][:220]!r}")
        print(f"expert   : {a.get('q_commentaire','')!r}")
        print(f"exclusions golden : {[(e['concept_id'], e['rang']) for e in g['exclusions']]}")
        evs = it.get("safety_events") or []
        print(f"safety_events ({len(evs)}) :")
        for ev in evs:
            print(f"   [{ev.get('status')}] {ev.get('kind','?')} {ev.get('concept_a','')}/{ev.get('concept_b','')} "
                  f"penalite={ev.get('penalty', ev.get('penalite'))} {str(ev)[:120]}")

show(FN, "FAUX NÉGATIFS — grave expert, secu=100")
show(FP, "FAUX POSITIFS — secu<100, pas grave expert")
