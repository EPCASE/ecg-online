"""
map_bareme_to_ontology.py — Étape 1 du « pont sémantique » (GPT-5.5).
====================================================================
Pour chaque cas, traduit les `points_cles` du barème (labels libres rédigés par
Pierre) en **concepts de l'ontologie** (`golden_id`) via un appel GPT-5.5 guidé.

Ce n'est PAS de la génération libre : c'est de l'**annotation contrainte** — on
donne à GPT le catalogue des 346 concepts (+ des candidats pré-mâchés par
matching naïf) et il choisit, pour chaque label, le meilleur `golden_id` ou
`null` s'il n'y a pas de correspondance honnête.

Sortie : data/cases_golden.json — AU FORMAT EXACT que `app/golden_config.py` lit :
  {
    "version": 1, "updated": "...", "model": "gpt-5.5",
    "cases": {
      "1": {
        "diagnostic_principal": "Inversion des électrodes des deux bras",
        "mapping": {
          "<label exact du point_cle>": {
            "golden_id": "INVERSION_ELECTRODES_BRAS",
            "concept_name": "Inversion des électrodes des bras",
            "confiance": 0.94, "valide_par": "gpt",
            "justification": "..."
          }
        }
      }
    }
  }

Le champ `valide_par` vaut "gpt" → l'UI /curation les affiche en jaune « GPT »,
à valider/corriger à la main (pastille verte « ✓ » une fois validé).

Résilient : reprise automatique (skip des cas déjà mappés sans erreur),
parallélisé, retries. On NE TOUCHE PAS aux cas déjà validés à la main.

Usage :
    python scripts/map_bareme_to_ontology.py                 # tous les cas restants
    python scripts/map_bareme_to_ontology.py --only 1,8,15   # sous-ensemble
    python scripts/map_bareme_to_ontology.py --workers 4
    python scripts/map_bareme_to_ontology.py --force         # re-mappe tout (GPT)
    python scripts/map_bareme_to_ontology.py --dry-run       # 1 cas, sans écrire
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

# Charge la clé OPENAI_API_KEY depuis .env (ecg-online/.env, puis parent) si dispo.
try:
    from dotenv import load_dotenv
    for _envp in (os.path.join(ROOT, ".env"),
                  os.path.join(os.path.dirname(ROOT), ".env")):
        if os.path.exists(_envp):
            load_dotenv(_envp)
            break
except ImportError:
    pass

REF_JSON = os.path.join(ROOT, "data", "cases_reference.json")
OUT_JSON = os.path.join(ROOT, "data", "cases_golden.json")

ONTO_CANDIDATES = [
    os.path.join(ROOT, "data", "ontology_v2.json"),
    r"C:\Users\Administrateur\bmad\ECG lecture\data\ontology_v2.json",
    r"C:\Users\Administrateur\bmad\RAG ontologique\data\ontology_v2.json",
]

MODEL = os.environ.get("ECG_MAPPING_MODEL", "gpt-5.5")

_client: OpenAI | None = None


def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


# ─────────────────────────── Ontologie ───────────────────────────
def canon(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "").strip())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def load_onto() -> dict:
    for p in ONTO_CANDIDATES:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("concepts", data)
    raise FileNotFoundError("ontology_v2.json introuvable dans " + " | ".join(ONTO_CANDIDATES))


def build_search_index(onto: dict):
    """rows: [{id, name, categorie, keys:[canon...]}] pour candidats naïfs."""
    rows = []
    for cid, c in onto.items():
        names = [c.get("concept_name", ""), c.get("concept_name_en", "")]
        names += c.get("synonymes", []) or []
        keys = [canon(n) for n in names if n]
        rows.append({
            "id": cid, "name": c.get("concept_name", ""),
            "categorie": c.get("categorie", ""), "keys": [k for k in keys if k],
        })
    return rows


def build_catalog(onto: dict) -> str:
    """Catalogue compact des 346 concepts, groupé par catégorie, pour le prompt.
    Une ligne = `ID · nom (· syn: s1; s2)`. Concis mais informatif."""
    by_cat: dict = {}
    for cid, c in onto.items():
        by_cat.setdefault(c.get("categorie", "AUTRE"), []).append((cid, c))
    order = ["DIAGNOSTIC_URGENT", "DIAGNOSTIC_MAJEUR", "DIAGNOSTIC_MOYEN",
             "DESCRIPTION_ECG", "TOPOGRAPHIE", "QUALIFICATEUR"]
    cats = order + [k for k in by_cat if k not in order]
    lines = []
    for cat in cats:
        rows = by_cat.get(cat)
        if not rows:
            continue
        lines.append(f"\n### {cat} ({len(rows)})")
        for cid, c in sorted(rows, key=lambda x: x[1].get("concept_name", "")):
            syn = c.get("synonymes", []) or []
            syn_s = f"  · syn: {'; '.join(syn[:4])}" if syn else ""
            lines.append(f"- {cid} · {c.get('concept_name','')}{syn_s}")
    return "\n".join(lines)


def naive_candidates(label: str, rows, k: int = 6):
    """Top-k concepts par matching lexical, pour orienter GPT (hints)."""
    ck = canon(label)
    toks = set(ck.split())
    scored = []
    for r in rows:
        best = 0
        for key in r["keys"]:
            if key == ck:
                best = max(best, 100)
            elif key in ck or ck in key:
                best = max(best, 70)
            else:
                kt = set(key.split())
                ov = toks & kt
                if ov:
                    best = max(best, 20 + len(ov) * 10)
        if best > 0:
            scored.append((best, r))
    scored.sort(key=lambda x: (-x[0], len(x[1]["name"])))
    return [r for _, r in scored[:k]]


# ─────────────────────────── Prompt ───────────────────────────
SYSTEM = """\
Tu es cardiologue expert ET ontologiste ECG. On te donne, pour un cas ECG :
- le corrigé de référence (texte),
- la liste des POINTS-CLÉS du barème (labels libres, avec rang EDN A/B/C),
- le CATALOGUE des concepts d'une ontologie ECG (identifiants + noms + synonymes).

Ta tâche : pour CHAQUE point-clé, choisir le concept de l'ontologie qui le
représente le mieux, en renvoyant son `golden_id` EXACT (copié tel quel depuis
le catalogue) + un `statut` (present/absent), ou `null` si AUCUN concept ne
correspond honnêtement.

## Règles de mapping
1. Choisis l'identifiant le PLUS SPÉCIFIQUE qui reste fidèle au sens clinique.
   Ex. « PR normal » → PR_NORMAL (pas « CONDUCTION_AV » trop général).
2. Le label peut être une PHRASE composite (« Rythme sinusal, PR normal, QRS
   fins »). Dans ce cas, mappe vers le concept-clé PRINCIPAL du label (souvent
   le diagnostic ou l'anomalie centrale). Ne mappe pas plusieurs concepts pour
   un même label : un seul `golden_id` (le plus important).
3. ⭐ NÉGATIONS — utilise le champ `statut` :
   - Concept AFFIRMÉ (présent sur le tracé) → `statut: "present"` (défaut).
   - Concept NIÉ / à ÉCARTER (« pas de sus-décalage ST », « éliminer une FA »,
     « ne pas retenir un flutter », « absence de BAV ») → mappe QUAND MÊME vers
     le concept central (SUS_DECALAGE_ST, FIBRILLATION_ATRIALE, FLUTTER…) mais
     avec `statut: "absent"`. NE renvoie PAS `null` pour une négation d'un
     concept qui EXISTE dans le catalogue.
   - `null` seulement si le concept central n'existe PAS dans le catalogue.
4. N'INVENTE JAMAIS d'identifiant. Utilise UNIQUEMENT ceux du catalogue, copiés
   au caractère près. Si tu hésites entre deux, prends le plus spécifique et
   baisse ta confiance.
5. `confiance` ∈ [0,1] : 0.9+ = évident, 0.6-0.8 = plausible, <0.5 = douteux.
6. `diagnostic_principal` : le diagnostic retenu du cas, en toutes lettres
   (ou « ECG normal »). C'est le cœur de la note.

Réponds UNIQUEMENT via l'outil `rendre_mapping`. Renvoie EXACTEMENT autant
d'entrées `mappings` qu'il y a de points-clés, dans le même ordre, avec le
`label` recopié à l'identique.
"""

TOOL = {
    "type": "function",
    "function": {
        "name": "rendre_mapping",
        "description": "Retourne le diagnostic principal et le mapping label→concept_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "diagnostic_principal": {
                    "type": "string",
                    "description": "Diagnostic retenu du cas (ou 'ECG normal').",
                },
                "mappings": {
                    "type": "array",
                    "description": "Un objet par point-clé, dans l'ordre fourni.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string",
                                      "description": "Label recopié à l'identique."},
                            "golden_id": {"type": ["string", "null"],
                                          "description": "ID ontologique exact, ou null."},
                            "statut": {"type": "string", "enum": ["present", "absent"],
                                       "description": "present = concept affirmé ; absent = concept nié/à écarter."},
                            "confiance": {"type": "number"},
                            "justification": {"type": "string",
                                              "description": "Courte raison (≤ 120 car.)."},
                        },
                        "required": ["label", "golden_id", "statut", "confiance"],
                    },
                },
            },
            "required": ["diagnostic_principal", "mappings"],
        },
    },
}


def build_prompt(ref: dict, catalog: str, rows) -> str:
    pts = ref.get("points_cles", []) or []
    parts = [
        f"# CAS {ref.get('num')} — {ref.get('titre','')}",
        f"Famille : {ref.get('famille','')}",
        "",
        "## Corrigé de référence",
        ref.get("reponse_attendue", "") or "(non fourni)",
        "",
        "## Points-clés à mapper (dans l'ordre)",
    ]
    for i, p in enumerate(pts, 1):
        label = p.get("label", "")
        rang = p.get("rang", "?")
        cands = naive_candidates(label, rows)
        hint = "  ".join(f"[{r['id']}]" for r in cands) or "(aucun candidat évident)"
        parts.append(f"{i}. ({rang}) {label}")
        parts.append(f"    candidats possibles : {hint}")
    parts += [
        "",
        "## CATALOGUE ONTOLOGIQUE (choisis les golden_id ICI, à l'identique)",
        catalog,
        "",
        "Mappe chaque point-clé via `rendre_mapping`.",
    ]
    return "\n".join(parts)


# ─────────────────────────── Appel ───────────────────────────
def _align(labels: list, gpt_list: list) -> list:
    """Aligne les mappings renvoyés par GPT sur les labels ORIGINAUX.

    GPT tronque/paraphrase fréquemment le champ `label` → on ne peut PAS matcher
    par égalité de texte. Stratégie :
      1. si le nombre de mappings == nombre de labels → alignement par POSITION
         (le prompt impose « même ordre, même nombre ») — robuste et simple ;
      2. sinon, repli flou : pour chaque label, on prend le mapping GPT dont le
         label (tronqué) est préfixe / sous-chaîne / meilleur chevauchement de
         tokens, sans réutiliser deux fois le même.

    Renvoie une liste de la même longueur que `labels` (None si pas de match).
    """
    n = len(labels)
    if len(gpt_list) == n:
        return list(gpt_list)

    # Repli flou (comptes différents) — appariement glouton sans réutilisation.
    used = set()
    out = []
    canon_labels = [canon(l) for l in labels]
    canon_gpt = [canon(m.get("label", "")) for m in gpt_list]
    for i, cl in enumerate(canon_labels):
        best_j, best_score = None, 0
        ltoks = set(cl.split())
        for j, cg in enumerate(canon_gpt):
            if j in used or not cg:
                continue
            if cl == cg:
                score = 100
            elif cl.startswith(cg) or cg.startswith(cl) or cg in cl or cl in cg:
                score = 80
            else:
                ov = ltoks & set(cg.split())
                score = len(ov) * 10
            if score > best_score:
                best_j, best_score = j, score
        if best_j is not None and best_score >= 20:
            used.add(best_j)
            out.append(gpt_list[best_j])
        else:
            out.append(None)
    return out


def map_one(ref: dict, catalog: str, rows, onto: dict, retries: int = 3) -> dict:
    num = ref.get("num")
    pts = ref.get("points_cles", []) or []
    labels = [p.get("label", "") for p in pts]
    prompt = build_prompt(ref, catalog, rows)
    last = None
    for attempt in range(retries):
        try:
            resp = client().chat.completions.create(
                model=MODEL,
                temperature=1,  # gpt-5.x
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": prompt}],
                tools=[TOOL],  # type: ignore[arg-type]
                tool_choice={"type": "function",
                             "function": {"name": "rendre_mapping"}},
            )
            calls = resp.choices[0].message.tool_calls or []
            if not calls:
                raise ValueError("pas d'appel d'outil")
            data = json.loads(calls[0].function.arguments)  # type: ignore[union-attr]
            gpt_list = data.get("mappings", []) or []

            # GPT tronque/paraphrase souvent les labels → on NE se fie PAS au texte
            # renvoyé. On aligne par POSITION (contrat : même ordre, même nombre),
            # avec repli flou (canon / préfixe) si le compte diffère.
            aligned = _align(labels, gpt_list)

            mapping = {}
            n_ok = 0
            for label, m in zip(labels, aligned):
                if not m:
                    continue
                cid = (m.get("golden_id") or "").strip()
                if not cid or cid not in onto:
                    continue  # null ou ID halluciné → non mappé
                statut = "absent" if str(m.get("statut", "")).strip().lower() == "absent" else "present"
                mapping[label] = {
                    "golden_id": cid,
                    "concept_name": onto[cid].get("concept_name", ""),
                    "statut": statut,
                    "confiance": round(float(m.get("confiance", 0.7)), 2),
                    "valide_par": "gpt",
                    "justification": (m.get("justification") or "")[:200],
                }
                n_ok += 1
            return {
                "num": num,
                "diagnostic_principal": data.get("diagnostic_principal", ""),
                "mapping": mapping,
                "n_points": len(labels), "n_mapped": n_ok,
                "error": None,
            }
        except Exception as ex:  # noqa: BLE001
            last = f"{type(ex).__name__}: {ex}"
            time.sleep(2 * (attempt + 1))
    return {"num": num, "diagnostic_principal": "", "mapping": {},
            "n_points": len(labels), "n_mapped": 0, "error": last}


# ─────────────────────────── I/O golden ───────────────────────────
def load_golden() -> dict:
    if os.path.exists(OUT_JSON):
        try:
            with open(OUT_JSON, encoding="utf-8") as f:
                d = json.load(f)
            d.setdefault("cases", {})
            return d
        except (json.JSONDecodeError, OSError):
            pass
    return {"version": 1, "updated": None, "model": MODEL, "cases": {}}


def has_human_edits(case: dict) -> bool:
    """Un cas contient-il au moins un mapping validé/corrigé à la main ?"""
    for m in (case.get("mapping", {}) or {}).values():
        if m.get("valide_par") in ("humain", "manuel"):
            return True
    return False


def save_golden(golden: dict) -> None:
    golden["updated"] = datetime.now().isoformat(timespec="seconds")
    golden["model"] = MODEL
    tmp = OUT_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(golden, f, ensure_ascii=False, indent=2)
    os.replace(tmp, OUT_JSON)


# ─────────────────────────── main ───────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="nums séparés par des virgules")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--force", action="store_true",
                    help="re-mappe même les cas déjà faits (GPT) — préserve les éditions humaines")
    ap.add_argument("--dry-run", action="store_true", help="1 cas, affiche, n'écrit rien")
    args = ap.parse_args()

    onto = load_onto()
    rows = build_search_index(onto)
    catalog = build_catalog(onto)
    refs = json.load(open(REF_JSON, encoding="utf-8")).get("references", [])
    print(f"Ontologie : {len(onto)} concepts · barème : {len(refs)} cas · modèle : {MODEL}")

    if args.only:
        wanted = {int(x) for x in args.only.split(",") if x.strip()}
        refs = [r for r in refs if int(r.get("num")) in wanted]

    golden = load_golden()

    if args.dry_run:
        r = refs[0]
        print(f"\n--- DRY RUN cas {r.get('num')} - {r.get('titre')} ---")
        res = map_one(r, catalog, rows, onto)
        print(f"diagnostic_principal : {res['diagnostic_principal']}")
        print(f"mappes : {res['n_mapped']}/{res['n_points']}"
              + (f"  ERREUR: {res['error']}" if res["error"] else ""))
        for label, m in res["mapping"].items():
            tag = "ABSENT" if m.get("statut") == "absent" else "presnt"
            print(f"  [{tag}] {label[:52]:52s} -> {m['golden_id']}  ({m['confiance']})")
        return

    # File d'attente : skip les cas déjà mappés (sauf --force), jamais écraser l'humain.
    todo = []
    for r in refs:
        num = str(r.get("num"))
        existing = golden["cases"].get(num)
        if existing and has_human_edits(existing):
            continue  # cas validé humain : intouchable
        if existing and existing.get("mapping") and not args.force:
            continue  # déjà mappé par GPT : on garde (relancer avec --force pour refaire)
        todo.append(r)

    print(f"À mapper : {len(todo)}/{len(refs)} cas (workers={args.workers})"
          + (" [FORCE]" if args.force else ""))
    if not todo:
        print("Rien à faire. --force pour re-mapper via GPT (les éditions humaines restent protégées).")
        _summary(golden, refs)
        return

    t0 = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(map_one, r, catalog, rows, onto): r for r in todo}
        for fut in as_completed(futs):
            res = fut.result()
            num = str(res["num"])
            golden["cases"][num] = {
                "diagnostic_principal": res["diagnostic_principal"],
                "mapping": res["mapping"],
            }
            save_golden(golden)  # écriture incrémentale (reprise sûre)
            done += 1
            flag = "OK " if not res["error"] else "ERR"
            print(f"  [{done}/{len(todo)}] {flag} cas {res['num']:>2} — "
                  f"{res['n_mapped']}/{res['n_points']} mappés"
                  + (f"  ({res['error']})" if res["error"] else ""))
    print(f"Terminé en {time.time()-t0:.0f}s → {OUT_JSON}")
    _summary(golden, refs)


def _summary(golden: dict, refs: list) -> None:
    tot_pts = tot_map = 0
    for r in refs:
        num = str(r.get("num"))
        pts = r.get("points_cles", []) or []
        mp = (golden["cases"].get(num, {}) or {}).get("mapping", {}) or {}
        tot_pts += len(pts)
        tot_map += len(mp)
    if tot_pts:
        print(f"Couverture mapping : {tot_map}/{tot_pts} points ({tot_map/tot_pts:.1%})")


if __name__ == "__main__":
    main()
