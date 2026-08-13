# -*- coding: utf-8 -*-
"""Test rapide golden override cas 3 / cas 8 (P4.2, 2026-08-12)."""
import sys
sys.path.insert(0, r"c:\Users\Administrateur\bmad\ECG lecture\ecg-online")
from app.neuro_grader import grade_neuro

TESTS = [
    (3, "rythme sinusal proche de 60 bpm, arythmie sinusale physiologique "
        "respiratoire, pas de trouble de conduction ni de repolarisation, "
        "pas d'hypertrophie ventriculaire, QRS fins, axe normal, ECG normal"),
    (8, "Ryhtme sinusal régulier à 54 bpm, normoaxé, PR normal, QRS fins, "
        "onde T négative en V2 et V3, pas de séquelle de nécrose"),
]

for num, txt in TESTS:
    r = grade_neuro(num, txt)
    print(f"cas {num}: score={r.score}")
    print("  manques :", [m.get("label") for m in (r.elements_manques or [])])
    print("  errones :", [(x.get("label") or "")[:80] for x in (r.elements_errones or [])])
