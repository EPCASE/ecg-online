"""
compile_ecg_pdf.py — Compile les 75 tracés ECG du livre « ECG 12.pdf »
=====================================================================
Le PDF (307 p.) est le manuel complet mis en page. Chaque cas commence par
un titre « CAS N » (police 20pt). On segmente le PDF par ces marqueurs, on
rend la 1re page image de chaque cas (le tracé 12-dérivations pleine page)
en PNG haute definition, et on aligne le tout sur la banque textuelle
(cases_bank_raw.json, titres issus du docx).

Sortie :
  data/ecg_images/cas_NN.png        (tracé principal, 200 DPI)
  data/ecg_images/cas_NN_p2.png     (2e tracé éventuel : "second tracé")
  data/pdf_case_map.json            (num -> pages, titre PDF, titre docx)

Usage : python scripts/compile_ecg_pdf.py
"""
from __future__ import annotations

import glob
import json
import os
import re
import unicodedata

import fitz  # PyMuPDF

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
DATA = os.path.join(PROJECT, "data")
OUT_IMG = os.path.join(DATA, "ecg_images")
BANK = os.path.join(DATA, "cases_bank_raw.json")

_PDF = glob.glob(r"C:\Users\Administrateur\Desktop\Articles\relecture ECG Pierre\*.pdf")
PDF = _PDF[0] if _PDF else ""

DPI = 200
# Titre de cas : « CAS 12 » seul, ou « CAS 13 BLOC DE BRANCHE... » (num + titre
# sur la meme ligne), parfois « CAS 21 : ... ». On capture le numero.
CAS_RE = re.compile(r"^\s*CAS\s+(\d{1,2})\b", re.IGNORECASE)


def deacc(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def find_case_starts(doc):
    """num_cas -> page index (0-based) du titre 'CAS N' (police >=20pt)."""
    starts = {}
    for i in range(doc.page_count):
        d = doc[i].get_text("dict")
        for b in d.get("blocks", []):
            for l in b.get("lines", []):
                line = "".join(s.get("text", "") for s in l.get("spans", [])).strip()
                mx = max([s["size"] for s in l.get("spans", [])], default=0)
                m = CAS_RE.match(line)
                if m and mx >= 19:
                    num = int(m.group(1))
                    if num not in starts:      # 1re occurrence = debut du cas
                        starts[num] = i
    return starts


def biggest_image_on_page(doc, pidx):
    """Retourne (xref, width, height) de la plus grande image de la page."""
    best = None
    for im in doc[pidx].get_images(full=True):
        xref = im[0]
        try:
            info = doc.extract_image(xref)
        except Exception:
            continue
        px = info.get("width", 0) * info.get("height", 0)
        if best is None or px > best[3]:
            best = (xref, info.get("width", 0), info.get("height", 0), px)
    return best


def render_page_region(doc, pidx, out_path, dpi=DPI):
    """Rend la page entiere en PNG (le tracé occupe l'essentiel de la page)."""
    page = doc[pidx]
    zoom = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    pix.save(out_path)
    return pix.width, pix.height


def main():
    if not PDF:
        raise SystemExit("PDF introuvable.")
    os.makedirs(OUT_IMG, exist_ok=True)
    doc = fitz.open(PDF)

    starts = find_case_starts(doc)
    nums = sorted(starts)
    print(f"PDF: {doc.page_count} pages — cas 'CAS N' detectes: {len(nums)} "
          f"(min={nums[0] if nums else '-'}, max={nums[-1] if nums else '-'})")
    missing = [n for n in range(1, 76) if n not in starts]
    if missing:
        print(f"  /!\\ cas sans marqueur 'CAS N': {missing}")

    # banque textuelle (titres docx) pour alignement
    bank = {}
    if os.path.exists(BANK):
        for c in json.load(open(BANK, encoding="utf-8"))["cases"]:
            bank[c["num"]] = c["titre"]

    # bornes de page par cas : [start_n, start_{n+1})
    ordered = sorted(starts.items(), key=lambda kv: kv[1])
    bounds = {}
    for idx, (num, pstart) in enumerate(ordered):
        pend = ordered[idx + 1][1] if idx + 1 < len(ordered) else doc.page_count
        bounds[num] = (pstart, pend)

    case_map = []
    for num in range(1, 76):
        if num not in bounds:
            case_map.append({"num": num, "pages": None, "images": [],
                             "titre_docx": bank.get(num, "")})
            continue
        p0, p1 = bounds[num]
        # Score chaque page du cas par la surface image totale (pixels). Le tracé
        # 12-derivations est l'element le plus volumineux ; le "second tracé"
        # (quand il existe) est la 2e page la mieux dotee. Seuil bas + fallback :
        # on retient les pages > 0.15 MP, sinon la meilleure page du cas.
        page_scores = []
        for p in range(p0, p1):
            total = 0
            for im in doc[p].get_images(full=True):
                try:
                    info = doc.extract_image(im[0])
                    total += info.get("width", 0) * info.get("height", 0)
                except Exception:
                    pass
            page_scores.append((p, total))
        strong = [p for p, s in page_scores if s >= 150_000]
        if not strong and page_scores:
            best_p = max(page_scores, key=lambda ps: ps[1])
            if best_p[1] > 0:
                strong = [best_p[0]]
        # ordre document, au plus 2 tracés (principal + second tracé)
        trace_pages = sorted(strong)[:2]
        imgs = []
        for k, p in enumerate(trace_pages, 1):
            suffix = "" if k == 1 else f"_p{k}"
            fname = f"cas_{num:02d}{suffix}.png"
            render_page_region(doc, p, os.path.join(OUT_IMG, fname))
            imgs.append(fname)
        case_map.append({
            "num": num, "pages": [p0 + 1, p1],  # 1-based inclusive-exclusive
            "trace_pages": [p + 1 for p in trace_pages],
            "images": imgs,
            "titre_docx": bank.get(num, ""),
        })
        print(f"  CAS {num:2d}  p{p0+1:3d}-{p1:3d}  tracés={len(imgs)}  {bank.get(num,'')[:40]}")

    with open(os.path.join(DATA, "pdf_case_map.json"), "w", encoding="utf-8") as f:
        json.dump({"pdf": os.path.basename(PDF), "dpi": DPI,
                   "n_cases": len(case_map), "cases": case_map},
                  f, ensure_ascii=False, indent=2)

    n_img = sum(len(c["images"]) for c in case_map)
    no_img = [c["num"] for c in case_map if not c["images"]]
    print(f"\nOK : {n_img} tracés PNG -> data/ecg_images/")
    print(f"     map -> data/pdf_case_map.json")
    if no_img:
        print(f"     /!\\ cas sans tracé rendu: {no_img}")


if __name__ == "__main__":
    main()
