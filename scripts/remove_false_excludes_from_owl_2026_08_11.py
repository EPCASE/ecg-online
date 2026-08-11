#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""remove_false_excludes_from_owl_2026_08_11.py — P4.3a-bis étape 1.

Supprime du .owl source (BrYOzRZIu7jQTwmfcGsi35.owl) les 12 relations
`exclut` jugées FAUSSES par l'arbitrage expert du 2026-08-11
(docs/P4.3a_audit_excludes_2026_08_11.md, section SUPPRIMER) :

  ces relations portent sur des dimensions cliniques différentes ou sont
  contredites par des situations classiques (infarctus non-Q, bloc
  bifasciculaire, préexcitation non manifeste, etc.). Elles ne relèvent
  ni de `excludes` (HARD) ni de `conflicts_by_default`.

Le patch retire les blocs :
    <rdfs:subClassOf>
        <owl:Restriction>
            <owl:onProperty rdf:resource=".../Rgkbf3QYLEo9sJtKMJFyFW"/>  (exclut)
            <owl:someValuesFrom rdf:resource="IRI_CIBLE"/>
        </owl:Restriction>
    </rdfs:subClassOf>
dans le bloc <owl:Class> du concept source.

Usage :
    python scripts/remove_false_excludes_from_owl_2026_08_11.py --dry-run
    python scripts/remove_false_excludes_from_owl_2026_08_11.py

Après application : régénérer ontology_v2.json depuis l'OWL patché
(cf. RUNBOOK_REBUILD_ONTOLOGIE.md — rebuild_ontology_from_owl.py).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\Administrateur\bmad\ECG lecture")
OWL_PATH = ROOT / "BrYOzRZIu7jQTwmfcGsi35.owl"
IRI_PATH = ROOT / "data" / "id_to_iri.json"
PREFIX = "http://webprotege.stanford.edu/"
EXCLUT_PROP = PREFIX + "Rgkbf3QYLEo9sJtKMJFyFW"

# Les 12 relations fausses (arbitrage expert 2026-08-11, #5 8 18 26 28 31 34 40 42 46 48 49)
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    iri_map = json.load(open(IRI_PATH, encoding="utf-8"))
    iri_map = {k: (v if str(v).startswith("http") else PREFIX + str(v))
               for k, v in iri_map.items()}

    owl = OWL_PATH.read_text(encoding="utf-8")
    original = owl
    removed = 0

    for src, dst in PAIRS:
        iri_src, iri_dst = iri_map.get(src), iri_map.get(dst)
        if not iri_src or not iri_dst:
            print(f"[!] IRI manquant : {src} ou {dst} — relation ignorée")
            continue
        # localiser le bloc de classe source (jusqu'au </owl:Class> suivant)
        cls_pat = re.compile(
            r'(<owl:Class rdf:about="' + re.escape(iri_src) + r'">.*?</owl:Class>)',
            re.S)
        m = cls_pat.search(owl)
        if not m:
            print(f"[!] classe {src} introuvable")
            continue
        block = m.group(1)
        restr_pat = re.compile(
            r'\s*<rdfs:subClassOf>\s*<owl:Restriction>\s*'
            r'<owl:onProperty rdf:resource="' + re.escape(EXCLUT_PROP) + r'"/>\s*'
            r'<owl:someValuesFrom rdf:resource="' + re.escape(iri_dst) + r'"/>\s*'
            r'</owl:Restriction>\s*</rdfs:subClassOf>')
        new_block, n = restr_pat.subn("", block)
        if n == 0:
            print(f"[!] restriction {src} -exclut-> {dst} introuvable dans le bloc")
            continue
        owl = owl.replace(block, new_block, 1)
        removed += n
        print(f"  - retiré : {src} -exclut-> {dst}")

    print(f"\nTotal : {removed}/12 restrictions retirées.")

    if args.dry_run:
        print("[DRY-RUN] Aucun fichier écrit.")
        return
    if removed != 12:
        print("⛔ Retrait incomplet — rien n'est écrit. Vérifier manuellement.")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = OWL_PATH.with_suffix(f".owl.bak_{ts}")
    shutil.copy2(OWL_PATH, bak)
    OWL_PATH.write_text(owl, encoding="utf-8")
    print(f"Backup : {bak}")
    print("✅ OWL patché. Étape suivante : régénérer ontology_v2.json "
          "(RUNBOOK_REBUILD_ONTOLOGIE.md).")


if __name__ == "__main__":
    main()
