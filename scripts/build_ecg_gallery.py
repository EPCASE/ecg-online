"""
build_ecg_gallery.py — Galerie compilee des 75 tracés ECG (banque de cas)
=========================================================================
Assemble un seul HTML autonome montrant, pour chacun des 75 cas :
  - le(s) tracé(s) ECG 12-derivations rendu(s) du livre (data/ecg_images/)
  - le titre / diagnostic, le contexte patient, le QCM EDN + reponses
  - l'interpretation ECOS de reference (= GOLD ouvert) et les commentaires

Source :
  data/cases_bank_raw.json   (texte des 75 cas, extrait du docx)
  data/pdf_case_map.json     (mapping cas -> images tracés, extrait du PDF)

Sortie : ecg_gallery_75.html  (a la racine du projet, images en chemin relatif)

Usage : python scripts/build_ecg_gallery.py
"""
from __future__ import annotations

import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
DATA = os.path.join(PROJECT, "data")
OUT = os.path.join(PROJECT, "ecg_gallery_75.html")


def esc(x):
    return html.escape(str(x if x is not None else ""))


def para(txt):
    """Texte multi-ligne -> paragraphes HTML."""
    txt = (txt or "").strip()
    if not txt:
        return '<span class="muted">—</span>'
    parts = [p.strip() for p in txt.split("\n") if p.strip()]
    return "".join(f"<p>{esc(p)}</p>" for p in parts)


def main():
    bank = {c["num"]: c for c in json.load(open(os.path.join(DATA, "cases_bank_raw.json"),
                                                encoding="utf-8"))["cases"]}
    pmap = {c["num"]: c for c in json.load(open(os.path.join(DATA, "pdf_case_map.json"),
                                                encoding="utf-8"))["cases"]}

    cards = []
    n_img_total = 0
    for num in range(1, 76):
        c = bank.get(num, {})
        pm = pmap.get(num, {})
        titre = c.get("titre", "") or pm.get("titre_docx", "")
        imgs = pm.get("images", [])
        n_img_total += len(imgs)

        img_html = ""
        for k, im in enumerate(imgs):
            rel = f"data/ecg_images/{im}"
            label = "Tracé principal" if k == 0 else "Second tracé"
            img_html += (f'<figure><img loading="lazy" src="{esc(rel)}" '
                         f'alt="ECG cas {num}"><figcaption>{label}</figcaption></figure>')
        if not img_html:
            img_html = '<div class="muted noimg">— tracé non disponible —</div>'

        # QCM
        qcm = ""
        if c.get("qcm_question") or c.get("qcm_options"):
            opts = "".join(f"<li>{esc(o)}</li>" for o in c.get("qcm_options", []))
            qcm = (f'<div class="qcm"><b>QCM EDN.</b> {esc(c.get("qcm_question"))}'
                   f'<ul>{opts}</ul>'
                   f'<div class="rep">✔ Réponse(s) : <b>{esc(c.get("qcm_reponses"))}</b></div></div>')

        # famille (pour filtre) : mot-cle grossier depuis le titre
        t = (titre or "").lower()
        fam = "autre"
        for key, val in [
            ("bloc de branche", "conduction"), ("bav", "conduction"),
            ("hémibloc", "conduction"), ("bloc ", "conduction"),
            ("fibrillation", "rythme"), ("flutter", "rythme"),
            ("tachycardie", "rythme"), ("extrasystole", "rythme"),
            ("bradycard", "rythme"), ("sinusal", "rythme"),
            ("dysfonction sinusale", "rythme"), ("torsade", "rythme"),
            ("coronarien", "ischemie"), ("sca", "ischemie"),
            ("prinzmetal", "ischemie"), ("nécrose", "ischemie"),
            ("hypertrophie", "hypertrophie"),
            ("hyperkali", "metabolique"), ("hypokali", "metabolique"),
            ("brugada", "genetique"), ("wolff", "genetique"),
            ("péricard", "pericarde"), ("embolie", "embolie"),
            ("normal", "normal"),
        ]:
            if key in t:
                fam = val
                break

        cards.append(f'''
<article class="case" data-num="{num}" data-fam="{fam}">
  <header class="chead">
    <span class="cnum">CAS {num}</span>
    <span class="ctitle">{esc(titre)}</span>
    <span class="cfam">{esc(fam)}</span>
    <span class="cpages">p.{esc((pm.get("pages") or ["?"])[0])}</span>
  </header>
  <div class="cbody">
    <div class="ctraces">{img_html}</div>
    <div class="ctext">
      <div class="sec"><h4>👤 Patient / contexte</h4>{para(c.get("patient"))}{para(c.get("contexte"))}</div>
      {qcm}
      <div class="sec gold"><h4>🏅 Interprétation de référence (ECOS)</h4>{para(c.get("interpretation_ecos"))}</div>
      <details><summary>💬 Commentaires pédagogiques</summary>{para(c.get("commentaires"))}</details>
      <details><summary>📘 Que dit le référentiel</summary>{para(c.get("referentiel"))}</details>
    </div>
  </div>
</article>''')

    fams = ["all", "normal", "rythme", "conduction", "ischemie", "hypertrophie",
            "metabolique", "embolie", "pericarde", "genetique", "autre"]
    fam_btn = "".join(
        '<button data-f="{}"{}>{}</button>'.format(
            f, " class='active'" if f == "all" else "", esc(f))
        for f in fams)

    doc = f'''<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Banque ECG — 75 tracés compilés</title>
<style>{CSS}</style></head><body>
<header class="top">
  <h1>🫀 Banque ECG — {len([1 for n in range(1,76) if pmap.get(n,{}).get("images")])}/75 cas · {n_img_total} tracés compilés</h1>
  <div class="toolbar">{fam_btn}
    <input id="q" placeholder="🔎 filtrer (diagnostic, texte…)">
    <span id="stat" class="stat"></span>
  </div>
</header>
<main>{''.join(cards)}</main>
<script>{JS}</script>
</body></html>'''

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"OK -> {OUT}")
    print(f"   75 cas, {n_img_total} tracés")


CSS = """
:root{--bg:#0e1116;--card:#161b22;--line:#232b36;--txt:#e6edf3;--mut:#8b98a5;
--gold:#f0b429;--accent:#58a6ff;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);
font:14px/1.5 -apple-system,Segoe UI,Roboto,Arial,sans-serif}
header.top{position:sticky;top:0;z-index:10;background:#0b0e13ee;backdrop-filter:blur(6px);
border-bottom:1px solid var(--line);padding:10px 16px}
header.top h1{margin:0 0 8px;font-size:17px}
.toolbar{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.toolbar button{background:#1c2330;color:var(--txt);border:1px solid var(--line);
border-radius:14px;padding:4px 12px;cursor:pointer;font-size:12px;text-transform:capitalize}
.toolbar button.active{border-color:#3d5a99;background:#243250}
.toolbar input{background:#1c2330;border:1px solid var(--line);color:var(--txt);
border-radius:6px;padding:5px 10px;min-width:220px}
.stat{color:var(--mut);font-size:12px;margin-left:auto}
main{padding:16px;display:flex;flex-direction:column;gap:16px;max-width:1500px;margin:auto}
.case{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.chead{display:flex;gap:10px;align-items:center;padding:10px 14px;border-bottom:1px solid var(--line);flex-wrap:wrap}
.cnum{font-weight:800;color:var(--accent);font-size:15px}
.ctitle{font-weight:600;font-size:15px;text-transform:capitalize}
.cfam{font-size:11px;color:var(--mut);background:#1c2330;padding:1px 8px;border-radius:10px;text-transform:capitalize}
.cpages{margin-left:auto;font-size:11px;color:var(--mut)}
.cbody{display:grid;grid-template-columns:1.35fr 1fr;gap:0}
.ctraces{padding:12px;border-right:1px solid var(--line);background:#0b0e13}
.ctraces figure{margin:0 0 12px}
.ctraces img{width:100%;border:1px solid var(--line);border-radius:6px;background:#fff;cursor:zoom-in}
.ctraces img.zoom{position:fixed;inset:2vh 2vw;width:96vw;height:96vh;object-fit:contain;
z-index:99;background:#fff;cursor:zoom-out;box-shadow:0 0 0 100vmax #000c}
figcaption{font-size:11px;color:var(--mut);margin-top:3px;text-align:center}
.noimg{padding:40px;text-align:center}
.ctext{padding:12px 16px}
.sec{margin-bottom:12px}
.sec h4{margin:0 0 5px;font-size:12px;text-transform:uppercase;letter-spacing:.4px;color:var(--mut)}
.sec.gold{border-left:3px solid var(--gold);padding-left:10px;background:#1a1710;border-radius:0 6px 6px 0;padding:8px 10px}
.sec.gold h4{color:var(--gold)}
.ctext p{margin:0 0 6px}
.qcm{background:#101722;border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin:10px 0;font-size:13px}
.qcm ul{margin:6px 0;padding-left:20px}
.qcm .rep{color:#7ee08e;margin-top:4px}
details{margin:6px 0;border-top:1px dashed var(--line);padding-top:6px}
summary{cursor:pointer;color:var(--accent);font-size:13px}
details p{color:#c3ccdd;font-size:13px}
.muted{color:var(--mut)}
.hidden{display:none!important}
@media(max-width:980px){.cbody{grid-template-columns:1fr}.ctraces{border-right:0;border-bottom:1px solid var(--line)}}
"""

JS = """
const cases=[...document.querySelectorAll('.case')];
const stat=document.getElementById('stat');
let q='',f='all';
function apply(){let n=0;cases.forEach(c=>{
  let ok=(f==='all')||c.dataset.fam===f;
  if(q){ok=ok&&(c.textContent||'').toLowerCase().includes(q);}
  c.classList.toggle('hidden',!ok);if(ok)n++;});
  stat.textContent=n+' / '+cases.length+' cas';}
document.querySelectorAll('.toolbar button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('.toolbar button').forEach(x=>x.classList.remove('active'));
  b.classList.add('active');f=b.dataset.f;apply();});
document.getElementById('q').oninput=e=>{q=e.target.value.toLowerCase().trim();apply();};
// zoom tracés
document.addEventListener('click',e=>{if(e.target.tagName==='IMG')e.target.classList.toggle('zoom');});
apply();
"""


if __name__ == "__main__":
    main()
