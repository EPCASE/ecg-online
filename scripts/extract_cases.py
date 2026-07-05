"""
extract_cases.py — Extraction de la banque de cas ECG depuis le docx de Pierre
==============================================================================
Source : « textes à envoyer.docx » (manuel ECG, 75 cas « Tracé N »)
Sortie : data/cases_bank_raw.json  +  data/images/traceNN_kk.ext

Chaque cas est découpé par ses sections :
    Patient · Contexte · QCM EDN (+réponses) · Interprétation ECOS (= GOLD)
    · Second tracé · Commentaires (= source pédagogie) · Que dit le référentiel
    · Hiérarchisation (tables) · images ECG (rattachées dans l'ordre du document)

On parcourt le corps du document DANS L'ORDRE (paragraphes + tables + images)
pour rattacher chaque élément au bon cas.

Usage : python scripts/extract_cases.py
"""
from __future__ import annotations

import glob
import json
import os
import re
import unicodedata

import docx
from docx.text.paragraph import Paragraph
from docx.table import Table
from docx.oxml.ns import qn

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
OUT_DIR = os.path.join(PROJECT, "data")
IMG_DIR = os.path.join(OUT_DIR, "images")

# Source (poste de Pierre) — résolu par glob pour éviter les soucis d'accents.
_CANDIDATES = glob.glob(r"C:\Users\Administrateur\Desktop\Articles\relecture ECG Pierre\*.docx")
DOCX = _CANDIDATES[0] if _CANDIDATES else ""


def deacc(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


# En-têtes de section (matchés sur version déaccentuée, en début de paragraphe)
SECTION_HEADERS = [
    ("patient", "patient"),
    ("contexte d'enregistrement et interpretation du second", "second_trace"),
    ("contexte", "contexte"),
    ("possible qcm", "qcm"),
    ("qcm edn", "qcm"),
    ("bonnes reponses", "reponses"),
    ("bonne reponse", "reponses"),
    ("interpretation du premier trace", "interpretation_ecos"),
    ("interpretation de ce trace", "interpretation_ecos"),
    ("interpretation du second trace", "second_trace"),
    ("commentaires", "commentaires"),
    ("commentaire", "commentaires"),
    ("que dit le referentiel", "referentiel"),
    ("hierarchisation des connaissances", "hierarchisation"),
]

TRACE_RE = re.compile(r"^\s*Trac[ée]\s*(\d+)\s*:?\s*(.*)$")


def match_section(text: str):
    d = deacc(text)
    if not d:
        return None
    for prefix, key in SECTION_HEADERS:
        if d.startswith(prefix):
            return key
    return None


def element_images(el, doc):
    """(partname, blob) de toutes les images sous un élément XML (para ou table)."""
    out = []
    for blip in el.findall(".//" + qn("a:blip")):
        rid = blip.get(qn("r:embed"))
        if not rid:
            continue
        try:
            part = doc.part.related_parts[rid]
        except KeyError:
            continue
        out.append((part.partname, part.blob))
    return out


def iter_body(doc):
    """Itère les blocs (paragraphes/tables) du corps DANS L'ORDRE du document."""
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield ("p", Paragraph(child, doc))
        elif child.tag == qn("w:tbl"):
            yield ("tbl", Table(child, doc))


def blank_case(num, titre):
    return {
        "num": num, "titre": titre.strip(),
        "patient": "", "contexte": "", "qcm_question": "", "qcm_options": [],
        "qcm_reponses": "", "interpretation_ecos": "", "second_trace": "",
        "commentaires": "", "referentiel": "", "hierarchisation": [],
        "images": [],
    }


def append_text(case, section, text):
    if section == "qcm":
        if re.match(r"^\s*[A-E][\.\)]\s+", text):
            case["qcm_options"].append(text.strip())
        else:
            case["qcm_question"] = (case["qcm_question"] + " " + text).strip()
    elif section == "reponses":
        case["qcm_reponses"] = (case["qcm_reponses"] + " " + text).strip()
    elif section in ("patient", "contexte", "interpretation_ecos", "second_trace",
                     "commentaires", "referentiel"):
        case[section] = (case[section] + "\n" + text).strip() if case[section] else text.strip()


def main():
    if not DOCX:
        raise SystemExit("Source docx introuvable.")
    os.makedirs(IMG_DIR, exist_ok=True)
    doc = docx.Document(DOCX)

    cases = []
    current = None
    section = None
    img_counter = {}

    # Filtrage : les icônes (badges de rang EDN, logos) sont petites et répétées
    # dans les tables de mise en page. Les vrais tracés ECG sont volumineux.
    # -> on déduplique par hash (une même image n'est prise qu'une fois) et on
    #    ne garde que les images >= MIN_IMG_BYTES.
    MIN_IMG_BYTES = 15 * 1024
    import hashlib
    seen_hashes = set()

    def save_images(pairs):
        if current is None:
            return
        for partname, blob in pairs:
            if len(blob) < MIN_IMG_BYTES:
                continue  # icône / badge / puce
            h = hashlib.md5(blob).hexdigest()
            if h in seen_hashes:
                continue  # image déjà rattachée ailleurs (logo répété)
            seen_hashes.add(h)
            ext = str(partname).split(".")[-1].lower()
            n = current["num"]
            img_counter[n] = img_counter.get(n, 0) + 1
            fname = f"trace{n:02d}_{img_counter[n]}.{ext}"
            with open(os.path.join(IMG_DIR, fname), "wb") as f:
                f.write(blob)
            current["images"].append(fname)

    for kind, block in iter_body(doc):
        if kind == "p":
            text = block.text.strip()
            m = TRACE_RE.match(text)
            if m:
                current = blank_case(int(m.group(1)), m.group(2))
                cases.append(current)
                section = None
                continue
            if current is None:
                continue  # préambule théorique avant Tracé 1

            save_images(element_images(block._p, doc))

            if not text:
                continue
            sec = match_section(text)
            if sec is not None:
                section = sec
                continue
            if section is not None:
                append_text(current, section, text)

        elif kind == "tbl" and current is not None:
            # 1) images de layout dans la table -> rattachées au cas courant
            save_images(element_images(block._tbl, doc))
            # 2) contenu textuel de la table (hiérarchisation des connaissances)
            rows = [[c.text.strip() for c in row.cells] for row in block.rows]
            if any(any(cell for cell in r) for r in rows):
                current["hierarchisation"].append(rows)

    clean = [c for c in cases if c["titre"]]
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "cases_bank_raw.json"), "w", encoding="utf-8") as f:
        json.dump({"source": os.path.basename(DOCX), "n_cases": len(clean),
                   "cases": clean}, f, ensure_ascii=False, indent=2)

    n_img = sum(len(c["images"]) for c in clean)
    n_tbl = sum(len(c["hierarchisation"]) for c in clean)
    print(f"OK : {len(clean)} cas -> data/cases_bank_raw.json")
    print(f"     {n_img} images -> data/images/")
    print(f"     {n_tbl} tables de hierarchisation rattachees")
    miss_interp = [c["num"] for c in clean if not c["interpretation_ecos"]]
    miss_img = [c["num"] for c in clean if not c["images"]]
    print(f"     cas sans interpretation ECOS : {miss_interp}")
    print(f"     cas sans image : {miss_img}")


if __name__ == "__main__":
    main()
