"""Rejoue localement des réponses précises (neuro-v1.3) et affiche le détail du verdict.

Usage : python scripts/_replay_zeros_2026_10_26.py
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
sys.stdout.reconfigure(encoding="utf-8")

CASES = [
    (1, "Rythme sinusal régulier, qrs fin normoaxe, pas de trouble de la conduction, pas de trouble du rythme, qt < 450"),
    (1, "rythme sinusal regulier \naxe hyperdroit \npas de bradycardie ni de tachycardie \nonde P normale \ninterval PR normal\nQRS fin \npas de troubles de la repolarisation\n pas de onde Q \nQT normal \nAvr psitif \ninvertion avr et D1"),
    (3, "rythme sinusal régulier à 50 bpm, normoaxé bas gauche, pas de BAV, pas de bloc de branche, pas de signe d'hypertrophie, pas de signe d'ischémie, bradycardie physiologique"),
    (3, "fréquence à 60bpm, rythme sinusal et régulier, normo axé, pas de trouble de la conduction pr <200ms et QRS fins, pas d'hypertrophie ventriculaire ou atriale, pas de signes d'ischémie pas de toruble de la repolarisation"),
    (8, "bradycardie sinusale physiologique à 50 bpm, coeur normo axé, sinusale et régulier, sans signe d'ischémie, pas de BAV ni de bloc de branche"),
    (26, "Fréquence 43bpm, rythme irrégulier, sinusal , normoaxé, BAV3, QRS fins, dissociation onde P et QRS,  pas de trouble de la repolarisation"),
    (26, "fréquence à 43 bpm (braycardie) , rythme sinsusal et irrégulier, normo axé, BAV complet avec un complexe QRS conduit pour deux ondes P, QRS fins, pas hypertrophie pas de trouble de la repolarisation, pas de signes d'isch"),
    (26, "bradycardie sinusale"),
    (42, "fréquence à 160 bpm, rythme non sinusal et régulier, normoaxé, QRS fins et PR court, onde P retrograde en inférieur, tachycardie jonctionnelle pas réentrée intranodale, onde delta,"),
    (42, "pas d'onde P, QRS fins, rythme non sinusal à 160 bpm, FA"),
    (40, "bloc de branche droite, hémibloc antéro gauche, bloc bifasciculaire"),
    (14, "Rythme sinusal irrégulier, QRS élargit bloc de branche gauche complet"),
    (24, "Bradycardie sinusale et régulière, allongement du PR, QRS fins, QT normal, BAV 1 avec bloque et repos compensatoire, pas d'hypertrophie, axe droit, pas de séquelles d'infarctus"),
    (55, "Rythme sinusal régulier à 80 bpm, déviation axiale gauche, hémibloc antérieur gauche, PR normal, sus décalage ST diffus avec sous décalage en V1, pas d'onde Q"),
    (63, "Torsade de pointe"),
]


def main():
    from app import neuro_grader

    out = []
    for cas, texte in CASES:
        print("=" * 100)
        print(f"CAS {cas} :: {texte[:110]!r}")
        try:
            r = neuro_grader.grade_neuro(cas, texte)
        except Exception as e:  # noqa: BLE001
            print("   ERREUR:", e)
            continue
        r = r.to_dict() if hasattr(r, "to_dict") else (r or {"error": "None (repli GPT)"})
        out.append({"cas": cas, "texte": texte, "result": r})
        for k in ("score", "score_adequation", "score_securite", "correspondance", "type_erreur", "error", "diagnostic_retenu"):
            if k in r:
                print(f"   {k} = {r[k]}")
        for k in ("safety_events", "elements_errones", "elements_manques", "elements_trouves", "concepts_detectes"):
            if r.get(k):
                print(f"   {k} = {json.dumps(r[k], ensure_ascii=False)[:700]}")
    (ROOT / "_replay_zeros_2026_10_26.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
