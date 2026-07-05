"""
Construction de la banque de cas exploitable par l'app.
=======================================================
Transforme data/cases_bank_raw.json (texte brut du docx) + data/pdf_case_map.json
(tracés PNG du PDF) en data/cases.json : une banque propre, indexee par numero,
prete a servir l'API et le front.

Chaque cas de sortie :
  {
    "num": 3,
    "titre": "ECG normal",
    "famille": "normal",
    "patient": "...", "contexte": "...",
    "qcm": {"question": "...", "options": [...], "reponses": "A"},
    "interpretation_ref": "...",   # GOLD ouvert (interpretation ECOS)
    "commentaires": "...",
    "referentiel": "...",
    "images": ["cas_03.png", ...]  # chemins relatifs a data/ecg_images/
  }

Usage : python scripts/build_cases_json.py
"""
from __future__ import annotations

import json
import os
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
DATA = os.path.join(PROJECT, "data")


def deacc(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def famille(titre):
    t = deacc(titre)
    table = [
        ("normal", "normal"),
        ("bloc de branche", "conduction"), ("bav", "conduction"),
        ("hemibloc", "conduction"), ("bloc ", "conduction"),
        ("sino-auriculaire", "conduction"), ("stimulateur", "conduction"),
        ("stimulation", "conduction"),
        ("fibrillation", "rythme"), ("flutter", "rythme"),
        ("tachycardie", "rythme"), ("extrasystole", "rythme"),
        ("bradycard", "rythme"), ("dysfonction sinusale", "rythme"),
        ("torsade", "rythme"), ("arythmie", "rythme"), ("pause", "rythme"),
        ("maladie de l", "rythme"), ("salve", "rythme"),
        ("coronarien", "ischemie"), ("sca", "ischemie"),
        ("prinzmetal", "ischemie"), ("necrose", "ischemie"),
        ("tronc commun", "ischemie"), ("anevrisme", "ischemie"),
        ("takotsubo", "ischemie"), ("riva", "ischemie"),
        ("hypertrophie", "hypertrophie"),
        ("hyperkali", "metabolique"), ("hypokali", "metabolique"),
        ("amylose", "infiltratif"),
        ("brugada", "genetique"), ("wolff", "genetique"),
        ("pericard", "pericarde"), ("epanchement", "pericarde"),
        ("myocardite", "pericarde"),
        ("embolie", "embolie"),
        ("inversion", "technique"), ("tremblement", "technique"),
    ]
    for key, val in table:
        if key in t:
            return val
    return "autre"


def main():
    raw = json.load(open(os.path.join(DATA, "cases_bank_raw.json"), encoding="utf-8"))
    pmap = {c["num"]: c for c in
            json.load(open(os.path.join(DATA, "pdf_case_map.json"), encoding="utf-8"))["cases"]}

    cases = []
    for c in raw["cases"]:
        num = c["num"]
        pm = pmap.get(num, {})
        cases.append({
            "num": num,
            "titre": c.get("titre", "").strip(),
            "famille": famille(c.get("titre", "")),
            "patient": c.get("patient", "").strip(),
            "contexte": c.get("contexte", "").strip(),
            "qcm": {
                "question": c.get("qcm_question", "").strip(),
                "options": c.get("qcm_options", []),
                "reponses": c.get("qcm_reponses", "").strip(),
            },
            "interpretation_ref": c.get("interpretation_ecos", "").strip(),
            "second_trace": c.get("second_trace", "").strip(),
            "commentaires": c.get("commentaires", "").strip(),
            "referentiel": c.get("referentiel", "").strip(),
            "images": pm.get("images", []),
        })

    out = {
        "source": raw.get("source", ""),
        "n_cases": len(cases),
        "cases": sorted(cases, key=lambda x: x["num"]),
    }
    path = os.path.join(DATA, "cases.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    n_img = sum(1 for c in cases if c["images"])
    n_interp = sum(1 for c in cases if c["interpretation_ref"])
    from collections import Counter
    fams = Counter(c["famille"] for c in cases)
    print(f"OK -> data/cases.json  ({len(cases)} cas)")
    print(f"   avec tracé : {n_img}/{len(cases)}   avec interprétation : {n_interp}/{len(cases)}")
    print(f"   familles : {dict(fams)}")


if __name__ == "__main__":
    main()
