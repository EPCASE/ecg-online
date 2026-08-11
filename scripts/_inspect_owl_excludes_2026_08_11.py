# -*- coding: utf-8 -*-
"""Inspection : forme des axiomes `exclut` dans l'OWL pour les 12 relations à supprimer."""
import json
import re
from pathlib import Path

ROOT = Path(r"C:\Users\Administrateur\bmad\ECG lecture")
OWL = ROOT / "BrYOzRZIu7jQTwmfcGsi35.owl"
IRI = json.load(open(ROOT / "data" / "id_to_iri.json", encoding="utf-8"))
PREFIX = "http://webprotege.stanford.edu/"
IRI = {k: (v if str(v).startswith("http") else PREFIX + str(v)) for k, v in IRI.items()}

EXCLUT_PROP = "Rgkbf3QYLEo9sJtKMJFyFW"

owl = OWL.read_text(encoding="utf-8")

PAIRS = [
    ("PRESENCE_DE_QRS", "ABSENCE_DE_QRS"),
    ("SEQUELLE_DE_NECROSE", "ABSENCE_D_ONDE_Q_PATHOLOGIQUE"),
    ("BLOC_DE_BRANCHE", "BLOC_FASCICULAIRE"),
    ("QRS_NORMAL", "FAISCEAU_ACCESSOIRE_A_CONDUCTION_ANTEROGRADE"),
    ("QRS_NORMAL", "PREEXCITATION_VENTRICULAIRE_PAR_FIBRE_DE_MAHAIM"),
    ("ABSENCE_D_ONDE_Q_PATHOLOGIQUE", "MORPHOLOGIE_ANORMALE_DU_QRS"),
    ("VOLTAGE_DU_QRS_NORMAL", "TROUBLE_DE_CONDUCTION_INTRAVENTRICULAIRE"),
    ("FLUTTER_ATRIAL_ATYPIQUE", "TOIT_D_USINE"),
    ("TACHYCARDIE_VENTRICULAIRE_POLYMORPHE", "ORGANISEE"),
    ("ARYTHMIE_SINUSALE", "ONDE_P_ANORMALE"),
    ("TROUBLE_DE_REPOLARISATION", "ONDE_U_NORMALE"),
    ("TROUBLE_DE_REPOLARISATION", "ST_NORMAL"),
]

for src, dst in PAIRS:
    iri_src, iri_dst = IRI.get(src), IRI.get(dst)
    if not iri_src or not iri_dst:
        print(f"[!] IRI manquant : {src}={iri_src} / {dst}={iri_dst}")
        continue
    # bloc de classe source
    m = re.search(
        r'<owl:Class rdf:about="' + re.escape(iri_src) + r'">(.*?)</owl:Class>',
        owl, re.S)
    if not m:
        print(f"[!] classe {src} introuvable")
        continue
    block = m.group(1)
    # restriction exclut → dst dans ce bloc ?
    pat = (r'<rdfs:subClassOf>\s*<owl:Restriction>\s*'
           r'<owl:onProperty rdf:resource="http://webprotege\.stanford\.edu/'
           + EXCLUT_PROP + r'"/>\s*'
           r'<owl:someValuesFrom rdf:resource="' + re.escape(iri_dst) + r'"/>\s*'
           r'</owl:Restriction>\s*</rdfs:subClassOf>')
    found = re.search(pat, block)
    print(f"{'OK ' if found else 'KO '} {src} -exclut-> {dst}")
