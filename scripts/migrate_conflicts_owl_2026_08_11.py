#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""migrate_conflicts_owl_2026_08_11.py — P4.3b étape B (volet OWL).

1. Déclare une nouvelle ObjectProperty `conflit_par_defaut`
   (IRI stable : http://webprotege.stanford.edu/conflitParDefaut_edu_ecg).
2. Déplace les 24 restrictions `exclut` classées DEFAULT par l'arbitrage
   P4.3a (docs/P4.3a_audit_excludes_2026_08_11.md) vers cette propriété
   (changement du rdf:resource de owl:onProperty dans le bloc Restriction).
3. Ajoute les 3 réciproques HARD manquantes (HYPONATREMIE→HYPERNATREMIE,
   MICROVOLTAGE→VOLTAGE_DU_QRS_NORMAL, ONDE_DELTA→LGL) — nécessaires tant
   que _check_excludes est directionnel.

Usage :
    python scripts/migrate_conflicts_owl_2026_08_11.py --dry-run
    python scripts/migrate_conflicts_owl_2026_08_11.py
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
CONFLICT_PROP = PREFIX + "conflitParDefaut_edu_ecg"

# 24 relations DEFAULT (directionnelles, telles que déclarées dans l'OWL)
DEFAULT_PAIRS = [
    ("BRADYCARDIE", "TACHYCARDIE"),
    ("TACHYCARDIE", "BRADYCARDIE"),
    ("IRREGULIER", "RYTHME_REGULIER"),
    ("BLOC_DE_BRANCHE", "QRS_FINS"),
    ("BLOC_DE_BRANCHE_DROIT", "BLOC_DE_BRANCHE_GAUCHE"),
    ("BLOC_DE_BRANCHE_GAUCHE", "BLOC_DE_BRANCHE_DROIT"),
    ("BLOC_FASCICULAIRE", "AXE_NORMAL_DU_QRS"),
    ("BLOC_FASCICULAIRE_ANTERIEUR_GAUCHE", "BLOC_FASCICULAIRE_POSTERIEUR_GAUCHE"),
    ("BLOC_FASCICULAIRE_POSTERIEUR_GAUCHE", "BLOC_FASCICULAIRE_ANTERIEUR_GAUCHE"),
    ("BAV_COMPLET", "PR_NORMAL"),
    ("PR_ALLONGE", "PR_NORMAL"),
    ("QRS_NORMAL", "ONDE_EPSILON"),
    ("QRS_NORMAL", "TROUBLE_DE_CONDUCTION_INTRAVENTRICULAIRE"),
    ("TROUBLE_DE_CONDUCTION_INTRAVENTRICULAIRE", "QRS_NORMAL"),
    ("VOLTAGE_DU_QRS_NORMAL", "HYPERTROPHIE_VENTRICULAIRE_GAUCHE"),
    ("DESORGANISEE", "ORGANISEE"),
    ("TACHYCARDIE_ATRIALE", "DESORGANISEE"),
    ("TACHYCARDIE_ATRIALE_FOCALE", "DESORGANISEE"),
    ("FLUTTER_ATRIAL_ATYPIQUE", "FIBRILLATION_ATRIALE"),
    ("FLUTTER_ATRIAL_ATYPIQUE", "FLUTTER_DROIT_TYPIQUE"),
    ("TACHYCARDIE_VENTRICULAIRE_BIDIRECTIONNELLE", "MONOMORPHE"),
    # NB : TACHYCARDIE_VENTRICULAIRE_(NON_)SOUTENUE n'existent PAS dans
    # l'OWL (concepts de la couche d'enrichissement JSON uniquement) —
    # leur migration est faite par le script de sync JSON.
    ("ABSENCE_D_ONDE_P", "ONDE_P_NORMALE"),
]

# Réciproques HARD manquantes à AJOUTER en `exclut`
HARD_RECIPROCALS = [
    ("HYPONATREMIE", "HYPERNATREMIE"),
    ("MICROVOLTAGE", "VOLTAGE_DU_QRS_NORMAL"),
    ("ONDE_DELTA", "SYNDROME_DE_LOWN_GANONG_ET_LEVINE"),
]

PROP_DECL = f"""    <!-- {CONFLICT_PROP} -->
    <owl:ObjectProperty rdf:about="{CONFLICT_PROP}">
        <rdfs:subPropertyOf rdf:resource="http://www.w3.org/2002/07/owl#topObjectProperty"/>
        <rdfs:label xml:lang="fr">conflit_par_defaut</rdfs:label>
        <rdfs:comment xml:lang="fr">Incompatibilit\u00e9 clinique habituelle (P4.3a 2026-08-11) : A et B sont normalement incompatibles pour le m\u00eame objet clinique au m\u00eame instant, mais des m\u00e9canismes (aberration, intermittence, \u00e9chappement...) peuvent les rendre coexistants. Override par le golden du cas.</rdfs:comment>
    </owl:ObjectProperty>
"""


def restriction_block(prop_iri: str, target_iri: str) -> str:
    return (f"        <rdfs:subClassOf>\n"
            f"            <owl:Restriction>\n"
            f"                <owl:onProperty rdf:resource=\"{prop_iri}\"/>\n"
            f"                <owl:someValuesFrom rdf:resource=\"{target_iri}\"/>\n"
            f"            </owl:Restriction>\n"
            f"        </rdfs:subClassOf>\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    iri_map = json.load(open(IRI_PATH, encoding="utf-8"))
    iri_map = {k: (v if str(v).startswith("http") else PREFIX + str(v))
               for k, v in iri_map.items()}

    owl = OWL_PATH.read_text(encoding="utf-8")
    migrated, added = 0, 0

    # 1) Déclaration de la propriété (si absente), insérée après la prop exclut
    if CONFLICT_PROP not in owl:
        anchor = re.search(
            r'(<owl:ObjectProperty rdf:about="' + re.escape(EXCLUT_PROP) + r'">.*?</owl:ObjectProperty>\n)',
            owl, re.S)
        if not anchor:
            print("⛔ Ancre ObjectProperty exclut introuvable"); return
        owl = owl.replace(anchor.group(1), anchor.group(1) + PROP_DECL, 1)
        print("  + ObjectProperty conflit_par_defaut déclarée")

    # 2) Migration des 24 restrictions DEFAULT
    for src, dst in DEFAULT_PAIRS:
        iri_src, iri_dst = iri_map.get(src), iri_map.get(dst)
        if not iri_src or not iri_dst:
            print(f"  [!] IRI manquant : {src}/{dst}"); continue
        cls_pat = re.compile(
            r'(<owl:Class rdf:about="' + re.escape(iri_src) + r'">.*?</owl:Class>)', re.S)
        m = cls_pat.search(owl)
        if not m:
            print(f"  [!] classe {src} introuvable"); continue
        block = m.group(1)
        restr_pat = re.compile(
            r'(<owl:onProperty rdf:resource=")' + re.escape(EXCLUT_PROP) + r'("/>\s*'
            r'<owl:someValuesFrom rdf:resource="' + re.escape(iri_dst) + r'"/>)')
        new_block, n = restr_pat.subn(r'\g<1>' + CONFLICT_PROP + r'\g<2>', block)
        if n == 0:
            print(f"  [!] restriction exclut {src} -> {dst} introuvable"); continue
        owl = owl.replace(block, new_block, 1)
        migrated += n
        print(f"  ~ migré : {src} -conflit_par_defaut-> {dst}")

    # 3) Réciproques HARD manquantes
    for src, dst in HARD_RECIPROCALS:
        iri_src, iri_dst = iri_map.get(src), iri_map.get(dst)
        if not iri_src or not iri_dst:
            print(f"  [!] IRI manquant : {src}/{dst}"); continue
        cls_pat = re.compile(
            r'(<owl:Class rdf:about="' + re.escape(iri_src) + r'">)(.*?)(</owl:Class>)', re.S)
        m = cls_pat.search(owl)
        if not m:
            print(f"  [!] classe {src} introuvable"); continue
        if re.search(re.escape(EXCLUT_PROP) + r'"/>\s*<owl:someValuesFrom rdf:resource="'
                     + re.escape(iri_dst), m.group(2)):
            print(f"  = réciproque déjà présente : {src} -> {dst}"); continue
        insertion = m.group(1) + "\n" + restriction_block(EXCLUT_PROP, iri_dst) + m.group(2).lstrip("\n")
        owl = owl.replace(m.group(1) + m.group(2), insertion, 1)
        added += 1
        print(f"  + réciproque HARD ajoutée : {src} -exclut-> {dst}")

    print(f"\nBilan : {migrated}/{len(DEFAULT_PAIRS)} migrées, {added}/3 réciproques ajoutées.")
    if args.dry_run:
        print("[DRY-RUN] Rien écrit."); return
    if migrated != len(DEFAULT_PAIRS) or added > 3:
        print("⛔ Bilan incomplet — rien n'est écrit."); return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = OWL_PATH.with_suffix(f".owl.bak_{ts}")
    shutil.copy2(OWL_PATH, bak)
    OWL_PATH.write_text(owl, encoding="utf-8")
    print(f"Backup : {bak}\n✅ OWL migré.")


if __name__ == "__main__":
    main()
