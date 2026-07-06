#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Génère une galerie HTML de relecture des 75 corrigés-types + fiches de secours.

Pour chaque cas : tracé(s) ECG + réponse attendue (GPT-5.5) + points clés +
fiche de secours (diagnostic, critères, pièges, item, citation source).

L'expert (Pierre) peut ainsi valider les 75 références AVANT mise en production.

Sortie : ecg-online/references_review.html  (fichier unique, styles inline).
Les images sont référencées en chemin relatif vers data/ecg_images/.

Usage :
    .\.venv\Scripts\python.exe scripts/build_references_review.py
    .\.venv\Scripts\python.exe scripts/build_references_review.py --open
"""
from __future__ import annotations

import argparse
import html
import json
import os
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
CASES_PATH = os.path.join(DATA, "cases.json")
REF_PATH = os.path.join(DATA, "cases_reference.json")
OUT_PATH = os.path.join(ROOT, "references_review.html")

RANG_COLORS = {"A": "#dc2626", "B": "#d97706", "C": "#2563eb"}


def esc(x) -> str:
    return html.escape(str(x or ""))


def _load() -> tuple[list[dict], dict]:
    cases = json.load(open(CASES_PATH, encoding="utf-8"))["cases"]
    refs_raw = json.load(open(REF_PATH, encoding="utf-8"))["references"]
    refs = {str(r["num"]): r for r in refs_raw}
    return cases, refs


def _rang_badge(rang) -> str:
    r = str(rang or "?").strip().upper()
    color = RANG_COLORS.get(r, "#64748b")
    return (f'<span class="rang" style="background:{color}">'
            f'Rang {esc(r)}</span>')


def _points_cles_html(points: list[dict]) -> str:
    if not points:
        return ""
    lis = "".join(
        f"<li>{_rang_badge(p.get('rang'))} {esc(p.get('label'))}</li>"
        for p in points)
    return f'<ul class="points">{lis}</ul>'


def _fiche_html(fs: dict) -> str:
    if not fs:
        return '<p class="muted">Pas de fiche de secours.</p>'
    crit = "".join(
        f"<li>{_rang_badge(c.get('rang'))} {esc(c.get('label'))}</li>"
        for c in fs.get("criteres_indispensables", []))
    pieges = "".join(f"<li>{esc(p)}</li>" for p in fs.get("pieges", []))
    citation = esc(fs.get("citation_source", ""))
    return f"""
      <div class="fiche">
        <div class="fiche-diag">🎯 {esc(fs.get('diagnostic_principal'))}</div>
        <p class="resume">{esc(fs.get('resume'))}</p>
        <div class="grid2">
          <div>
            <h4>Critères indispensables</h4>
            <ul class="crit">{crit or '<li class="muted">—</li>'}</ul>
          </div>
          <div>
            <h4>Pièges classiques</h4>
            <ul class="pieges">{pieges or '<li class="muted">—</li>'}</ul>
          </div>
        </div>
        <div class="item">📚 {esc(fs.get('references_item'))}</div>
        {f'<blockquote>« {citation} »</blockquote>' if citation else ''}
      </div>
    """


def _case_html(case: dict, ref: dict | None) -> str:
    num = case.get("num")
    imgs = "".join(
        f'<img src="data/ecg_images/{esc(i)}" alt="cas {esc(num)}" loading="lazy">'
        for i in case.get("images", []))
    imgs_block = imgs or '<p class="muted">(pas d&rsquo;image)</p>'
    if ref is None:
        body = '<p class="muted">⚠️ Aucune référence générée pour ce cas.</p>'
    else:
        body = f"""
          <h3>✅ Réponse attendue (corrigé-type)</h3>
          <div class="reponse">{esc(ref.get('reponse_attendue')).replace(chr(10), '<br>')}</div>
          {_points_cles_html(ref.get('points_cles', []))}
          <h3>🧭 Fiche de secours</h3>
          {_fiche_html(ref.get('fiche_secours', {}))}
        """
    return f"""
    <section class="case" id="cas-{esc(num)}">
      <header class="case-head">
        <span class="num">Cas {esc(num)}</span>
        <span class="titre">{esc(case.get('titre'))}</span>
        <span class="fam">{esc(case.get('famille'))}</span>
      </header>
      <div class="case-body">
        <div class="col-img">{imgs_block}</div>
        <div class="col-txt">
          <h3>👨‍⚕️ Contexte</h3>
          <p class="ctx">{esc(case.get('patient'))} — {esc(case.get('contexte'))}</p>
          <h3>📝 Interprétation enseignant (source Pierre)</h3>
          <div class="ref-ens">{esc(case.get('interpretation_ref')).replace(chr(10), '<br>')}</div>
          {body}
        </div>
      </div>
    </section>
    """


def _nav_html(cases: list[dict]) -> str:
    links = "".join(
        f'<a href="#cas-{esc(c.get("num"))}">{esc(c.get("num"))}</a>'
        for c in cases)
    return f'<nav class="toc">{links}</nav>'


CSS = """
* { box-sizing: border-box; }
body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
       margin: 0; background: #f1f5f9; color: #0f172a; line-height: 1.55; }
.topbar { position: sticky; top: 0; z-index: 20; background: #0f172a;
          color: #f8fafc; padding: 14px 24px; box-shadow: 0 2px 8px rgba(0,0,0,.2); }
.topbar h1 { margin: 0; font-size: 20px; }
.topbar .sub { font-size: 13px; opacity: .75; }
.toc { position: sticky; top: 56px; z-index: 15; background: #e2e8f0;
       padding: 8px 16px; display: flex; flex-wrap: wrap; gap: 4px;
       border-bottom: 1px solid #cbd5e1; }
.toc a { font-size: 12px; min-width: 26px; text-align: center; padding: 2px 6px;
         background: #fff; border-radius: 5px; text-decoration: none;
         color: #334155; border: 1px solid #cbd5e1; }
.toc a:hover { background: #2563eb; color: #fff; }
.wrap { max-width: 1200px; margin: 0 auto; padding: 20px; }
.case { background: #fff; border-radius: 14px; margin-bottom: 26px;
        box-shadow: 0 1px 4px rgba(0,0,0,.08); overflow: hidden; }
.case-head { display: flex; align-items: center; gap: 14px;
             background: linear-gradient(90deg,#1e3a8a,#2563eb); color: #fff;
             padding: 12px 20px; }
.case-head .num { font-weight: 700; font-size: 18px; }
.case-head .titre { font-size: 16px; flex: 1; }
.case-head .fam { font-size: 12px; background: rgba(255,255,255,.2);
                  padding: 3px 10px; border-radius: 20px; }
.case-body { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding: 20px; }
@media (max-width: 900px){ .case-body{ grid-template-columns: 1fr; } }
.col-img img { width: 100%; border: 1px solid #e2e8f0; border-radius: 8px;
               margin-bottom: 10px; cursor: zoom-in; }
.col-img img:hover { box-shadow: 0 0 0 3px #93c5fd; }
h3 { font-size: 14px; text-transform: uppercase; letter-spacing: .04em;
     color: #1e40af; margin: 16px 0 6px; border-bottom: 1px solid #e2e8f0;
     padding-bottom: 4px; }
h4 { font-size: 13px; margin: 8px 0 4px; color: #334155; }
.ctx { font-style: italic; color: #475569; }
.ref-ens { background: #f8fafc; border-left: 3px solid #94a3b8; padding: 8px 12px;
           border-radius: 4px; font-size: 14px; }
.reponse { background: #ecfdf5; border-left: 3px solid #10b981; padding: 10px 14px;
           border-radius: 4px; font-size: 14px; }
.points { list-style: none; padding: 0; margin: 8px 0; }
.points li { padding: 3px 0; font-size: 14px; }
.rang { color: #fff; font-size: 10px; font-weight: 700; padding: 1px 6px;
        border-radius: 4px; margin-right: 6px; vertical-align: middle; }
.fiche { background: #fffbeb; border: 1px solid #fde68a; border-radius: 10px;
         padding: 14px; }
.fiche-diag { font-weight: 700; font-size: 16px; color: #b45309; }
.resume { font-size: 14px; margin: 6px 0 10px; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
@media (max-width: 600px){ .grid2{ grid-template-columns: 1fr; } }
.crit, .pieges { margin: 0; padding-left: 4px; list-style: none; }
.crit li, .pieges li { font-size: 13px; padding: 2px 0; }
.pieges li::before { content: "⚠️ "; }
.item { margin-top: 10px; font-size: 13px; color: #7c2d12; font-weight: 600; }
blockquote { margin: 10px 0 0; padding: 8px 12px; background: #fff7ed;
             border-left: 3px solid #fb923c; font-size: 13px; color: #7c2d12;
             font-style: italic; border-radius: 4px; }
.muted { color: #94a3b8; }
/* Lightbox */
#lb { position: fixed; inset: 0; background: rgba(0,0,0,.9); display: none;
      align-items: center; justify-content: center; z-index: 100; cursor: zoom-out; }
#lb img { max-width: 96%; max-height: 96%; border-radius: 6px; }
"""

JS = """
document.addEventListener('click', e => {
  if (e.target.tagName === 'IMG' && e.target.closest('.col-img')) {
    const lb = document.getElementById('lb');
    lb.querySelector('img').src = e.target.src;
    lb.style.display = 'flex';
  }
});
document.getElementById('lb').addEventListener('click', () => {
  document.getElementById('lb').style.display = 'none';
});
"""


def build(open_after: bool = False) -> str:
    cases, refs = _load()
    cases = sorted(cases, key=lambda c: c.get("num", 0))
    n_ref = sum(1 for c in cases if str(c.get("num")) in refs)
    body = "\n".join(_case_html(c, refs.get(str(c.get("num")))) for c in cases)
    doc = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Relecture — 75 corrigés-types ECG</title>
<style>{CSS}</style></head>
<body>
  <div class="topbar">
    <h1>🩺 Relecture des corrigés-types ECG</h1>
    <div class="sub">{len(cases)} cas · {n_ref} références générées ·
      modèle GPT-5.5 · à valider par l'expert avant mise en production</div>
  </div>
  {_nav_html(cases)}
  <div class="wrap">
    {body}
  </div>
  <div id="lb"><img src="" alt=""></div>
  <script>{JS}</script>
</body></html>"""
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(doc)
    size_kb = os.path.getsize(OUT_PATH) / 1024
    print(f"✅ Galerie écrite : {OUT_PATH}  ({size_kb:.0f} KB, "
          f"{len(cases)} cas, {n_ref} références)")
    if open_after:
        webbrowser.open(f"file:///{OUT_PATH.replace(os.sep, '/')}")
    return OUT_PATH


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--open", action="store_true",
                    help="Ouvrir la galerie dans le navigateur après génération.")
    args = ap.parse_args()
    build(open_after=args.open)
