# -*- coding: utf-8 -*-
"""_test_coherence_log_2026_08_11.py — P4.3c étape 0 : test instrumentation passive."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
LOG = os.path.join(ROOT, "_test_pairs_log.jsonl")
os.environ["COHERENCE_LOG_PATH"] = LOG
if os.path.exists(LOG):
    os.remove(LOG)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

from app import neuro_grader

OK, KO = "\u2705", "\u274c"
fails = []


def check(label, cond, detail=""):
    print(f"{OK if cond else KO} {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        fails.append(label)


# chal_02 : DEFAULT actif → doit être loggé avec spans, note inchangée.
c = neuro_grader.grade_neuro(
    49, "Fibrillation atriale avec rythme parfaitement régulier à QRS fins, "
        "fréquence 75/min normale.")
d = c.to_dict()
check("score inchangé (100) malgré la paire loggée", d["score"] == 100,
      f"score={d['score']}")

check("fichier JSONL créé", os.path.exists(LOG))
entries = [json.loads(line) for line in open(LOG, encoding="utf-8")] if os.path.exists(LOG) else []
check("1 paire loggée", len(entries) == 1, f"n={len(entries)}")
if entries:
    e = entries[0]
    check("concepts corrects", {e["concept_a"], e["concept_b"]}
          == {"FIBRILLATION_ATRIALE", "RYTHME_REGULIER"})
    check("kind/status corrects", e["kind"] == "conflicts_by_default"
          and e["status"] == "active")
    check("spans_a non vides", bool(e["spans_a"]), str(e["spans_a"])[:70])
    check("spans_b non vides", bool(e["spans_b"]), str(e["spans_b"])[:70])
    check("pipeline_version présent", e["pipeline_version"] == neuro_grader.PIPELINE_VERSION)

# Contrôle négatif : réponse cohérente → rien de plus dans le log.
c2 = neuro_grader.grade_neuro(
    49, "Fibrillation atriale : rythme irrégulièrement irrégulier, absence "
        "d'ondes P, trémulation de la ligne de base.")
entries2 = [json.loads(line) for line in open(LOG, encoding="utf-8")]
check("contrôle négatif : pas de nouvelle ligne", len(entries2) == len(entries),
      f"n={len(entries2)}")

os.remove(LOG)
print("=" * 50)
if fails:
    print(f"{KO} {len(fails)} échec(s) : {fails}")
    sys.exit(1)
print(f"{OK} Instrumentation passive OK.")
