"""
build_reference_answers.py — Génère, par cas ECG et via GPT-5.5, deux livrables :

  1. reponse_attendue : le CORRIGÉ-TYPE (réponse idéale attendue d'un étudiant),
     structuré dans l'ordre de lecture de l'ECG, ancré sur l'interprétation de
     référence de Pierre.

  2. fiche_secours : le FILET DE SÉCURITÉ, utilisé si la correction live (grader)
     dérape. Résumé ancré MOT POUR MOT sur le texte de Pierre (commentaires +
     interprétation) avec les critères indispensables et les références d'item EDN.

Sortie :
  - data/reference/<num>.json          (un fichier par cas, resume-safe)
  - data/cases_reference.json          (consolidation finale)

Modèle : gpt-5.5 (temperature forcée à 1 — seule valeur supportée).
Parallélisé (ThreadPoolExecutor), reprise automatique (skip des cas déjà faits).

Usage :
    python scripts/build_reference_answers.py
    python scripts/build_reference_answers.py --only 8,12,58     # sous-ensemble
    python scripts/build_reference_answers.py --workers 4
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
CASES = os.path.join(ROOT, "data", "cases.json")
OUT_DIR = os.path.join(ROOT, "data", "reference")
OUT_JSON = os.path.join(ROOT, "data", "cases_reference.json")

MODEL = os.environ.get("ECG_REFERENCE_MODEL", "gpt-5.5")

_client: OpenAI | None = None


def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


SYSTEM = """\
Tu es cardiologue, enseignant d'ECG et auteur du corrigé de référence (préparation
EDN, France). On te fournit, pour un cas ECG, l'énoncé, l'interprétation de
référence et le TEXTE PÉDAGOGIQUE de l'enseignant (Pierre) ainsi que ses renvois
au référentiel. Tu produis deux livrables complémentaires.

=== 1. RÉPONSE ATTENDUE (corrigé-type) ===
Rédige la réponse idéale qu'un très bon étudiant devrait écrire, en TEXTE LIBRE
structuré dans l'ordre de lecture systématique de l'ECG :
fréquence → rythme (sinusal ?) → conduction (PR) → axe → QRS (durée, morphologie)
→ repolarisation (ST/T/QT) → conclusion diagnostique.
- Fidèle à l'interprétation de référence, sans rien inventer au-delà du texte fourni.
- Concise mais complète (un bon paragraphe), niveau étudiant avancé.

=== 2. FICHE DE SECOURS (filet de sécurité) ===
Cette fiche servira de VÉRITÉ DE REPLI si une correction automatique dérape.
Elle DOIT être ancrée sur le texte de l'enseignant (ne pas extrapoler) :
- resume : 2-4 phrases résumant l'attendu, fondées sur le texte de Pierre.
- criteres_indispensables : la liste des éléments SANS lesquels la réponse est
  incomplète (diagnostic principal + descripteurs clés), chacun avec un rang EDN
  (A = indispensable, B = important, C = complémentaire).
- diagnostic_principal : le diagnostic retenu (ou « ECG normal »).
- pieges : les pièges/erreurs classiques à éviter sur ce tracé.
- references_item : les références au référentiel / item EDN citées ou impliquées
  par le texte (ex. « EDN Item 231 — ECG : indications et interprétation »).
- citation_source : une courte citation VERBATIM (≤ 200 caractères) tirée du texte
  de Pierre qui justifie l'attendu.

Réponds UNIQUEMENT via l'outil `rendre_reference`.
"""

TOOL = {
    "type": "function",
    "function": {
        "name": "rendre_reference",
        "description": "Retourne le corrigé-type et la fiche de secours du cas.",
        "parameters": {
            "type": "object",
            "properties": {
                "reponse_attendue": {"type": "string",
                                     "description": "Corrigé-type en texte libre structuré."},
                "points_cles": {
                    "type": "array",
                    "description": "Concepts clés du corrigé, avec rang EDN.",
                    "items": {"type": "object", "properties": {
                        "label": {"type": "string"},
                        "rang": {"type": "string", "enum": ["A", "B", "C"]},
                    }, "required": ["label", "rang"]},
                },
                "fiche_secours": {
                    "type": "object",
                    "properties": {
                        "resume": {"type": "string"},
                        "diagnostic_principal": {"type": "string"},
                        "criteres_indispensables": {
                            "type": "array",
                            "items": {"type": "object", "properties": {
                                "label": {"type": "string"},
                                "rang": {"type": "string", "enum": ["A", "B", "C"]},
                            }, "required": ["label", "rang"]},
                        },
                        "pieges": {"type": "array", "items": {"type": "string"}},
                        "references_item": {"type": "string"},
                        "citation_source": {"type": "string"},
                    },
                    "required": ["resume", "diagnostic_principal",
                                 "criteres_indispensables", "pieges",
                                 "references_item", "citation_source"],
                },
            },
            "required": ["reponse_attendue", "points_cles", "fiche_secours"],
        },
    },
}


def build_prompt(case: dict) -> str:
    qcm = case.get("qcm") or {}
    parts = [
        f"# CAS {case.get('num')} — {case.get('titre')}",
        f"Famille : {case.get('famille','')}",
        "",
        "## Énoncé",
        f"Patient : {case.get('patient','')}",
        f"Contexte : {case.get('contexte','')}",
    ]
    if qcm:
        opts = "\n".join(qcm.get("options", []))
        parts += ["", "## QCM associé",
                  f"{qcm.get('question','')}\n{opts}\nRéponses : {qcm.get('reponses','')}"]
    parts += ["", "## Interprétation de référence (enseignant)",
              case.get("interpretation_ref", "") or "(non fournie)"]
    if case.get("second_trace"):
        parts += ["", "## Second tracé", case["second_trace"]]
    if case.get("commentaires"):
        parts += ["", "## Texte pédagogique de Pierre (à citer)", case["commentaires"]]
    if case.get("referentiel"):
        parts += ["", "## Renvoi au référentiel / item", case["referentiel"]]
    parts += ["", "Produis les deux livrables via `rendre_reference`."]
    return "\n".join(parts)


def generate_one(case: dict, retries: int = 3) -> dict:
    prompt = build_prompt(case)
    last = None
    for attempt in range(retries):
        try:
            resp = client().chat.completions.create(
                model=MODEL,
                temperature=1,  # seule valeur supportée par gpt-5.x
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": prompt}],
                tools=[TOOL],  # type: ignore[arg-type]
                tool_choice={"type": "function",
                             "function": {"name": "rendre_reference"}},
            )
            calls = resp.choices[0].message.tool_calls or []
            if not calls:
                raise ValueError("pas d'appel d'outil")
            data = json.loads(calls[0].function.arguments)  # type: ignore[union-attr]
            return {
                "num": case["num"],
                "titre": case.get("titre", ""),
                "famille": case.get("famille", ""),
                "model": MODEL,
                "reponse_attendue": data.get("reponse_attendue", ""),
                "points_cles": data.get("points_cles", []),
                "fiche_secours": data.get("fiche_secours", {}),
                "error": None,
            }
        except Exception as ex:  # noqa: BLE001
            last = f"{type(ex).__name__}: {ex}"
            time.sleep(2 * (attempt + 1))
    return {"num": case["num"], "titre": case.get("titre", ""),
            "famille": case.get("famille", ""), "model": MODEL,
            "reponse_attendue": "", "points_cles": [], "fiche_secours": {},
            "error": last}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="nums séparés par des virgules")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--force", action="store_true", help="régénère même si déjà fait")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    cases = json.load(open(CASES, encoding="utf-8"))["cases"]

    if args.only:
        wanted = {int(x) for x in args.only.split(",") if x.strip()}
        cases = [c for c in cases if int(c["num"]) in wanted]

    todo = []
    for c in cases:
        dst = os.path.join(OUT_DIR, f"{int(c['num']):02d}.json")
        if os.path.exists(dst) and not args.force:
            prev = json.load(open(dst, encoding="utf-8"))
            if not prev.get("error"):
                continue
        todo.append(c)

    print(f"Modèle={MODEL} | à générer : {len(todo)}/{len(cases)} cas | workers={args.workers}")
    if not todo:
        print("Rien à faire (tout est déjà généré). Utilise --force pour régénérer.")
    else:
        t0 = time.time()
        done = 0
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(generate_one, c): c for c in todo}
            for fut in as_completed(futs):
                res = fut.result()
                dst = os.path.join(OUT_DIR, f"{int(res['num']):02d}.json")
                json.dump(res, open(dst, "w", encoding="utf-8"),
                          ensure_ascii=False, indent=2)
                done += 1
                flag = "OK " if not res["error"] else "ERR"
                print(f"  [{done}/{len(todo)}] {flag} cas {res['num']:>2} — {res['titre'][:40]}"
                      + (f"  ({res['error']})" if res["error"] else ""))
        print(f"Terminé en {time.time()-t0:.0f}s")

    # Consolidation
    all_refs = []
    for c in json.load(open(CASES, encoding="utf-8"))["cases"]:
        dst = os.path.join(OUT_DIR, f"{int(c['num']):02d}.json")
        if os.path.exists(dst):
            all_refs.append(json.load(open(dst, encoding="utf-8")))
    all_refs.sort(key=lambda r: int(r["num"]))
    ok = sum(1 for r in all_refs if not r.get("error"))
    json.dump({"model": MODEL, "count": len(all_refs), "ok": ok,
               "references": all_refs},
              open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"→ {OUT_JSON} : {ok}/{len(all_refs)} cas OK")


if __name__ == "__main__":
    main()
