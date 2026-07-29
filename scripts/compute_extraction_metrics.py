"""
compute_extraction_metrics.py — Calcul P/R/F1 + Kappa du golden d'extraction.
==============================================================================
Cf. GOLDEN_EXTRACTION.md §5. Compare `pipeline_extraction` (sortie NER+onto de
prod, rejouée/figée au moment de la construction de l'échantillon) à
`annotation_expert.concepts` (vérité de terrain humaine) pour chaque item de
`data/extraction_golden.json`.

Définitions (par item, ensembles de paires (ontology_id, statut)) :
  - Vrai positif (TP)  : concept dans pipeline_extraction ET dans l'annotation
                          experte, avec le même statut.
  - Faux positif (FP)  : concept extrait par le pipeline, absent de
                          l'annotation experte (hallucination) — ou présent
                          mais avec un statut différent (compté aussi en FN
                          côté expert, cf. `--strict-statut`).
  - Faux négatif (FN)  : concept annoté par l'expert (source="ajoute_expert"
                          ou "ajoute_gpt56" accepté), absent de l'extraction
                          pipeline (omission).

Precision = TP / (TP + FP)   — combien de sorties du pipeline sont correctes.
Rappel    = TP / (TP + FN)   — combien de concepts réels sont retrouvés.
F1        = moyenne harmonique.

Calcule aussi les métriques **par méthode d'extraction** (coupe_circuit /
juge_llm / fallback_subterm / lexical_backstop / pattern_inference) en
n'affectant à chaque méthode que les TP/FP dont le concept pipeline provient
de cette méthode (les FN n'ont pas de méthode, ils ne sont affectés à aucune
brique — ils comptent seulement dans le rappel global).

Kappa de Cohen (accord inter-annotateur) : calculé sur les items
`double_annotation=true` ayant les deux relectures (`annotation_expert` et
`annotation_expert_2`) complétées, en comparant leurs ensembles de concepts
(ontology_id, statut) item par item (accord binaire par concept possible dans
l'un OU l'autre des deux relectures — cf. `_cohen_kappa_sets`).

Usage :
    python scripts/compute_extraction_metrics.py [--json rapport.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from typing import Dict, List, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import extraction_golden  # noqa: E402


ConceptKey = Tuple[str, str]  # (ontology_id, statut)


def _pipeline_set_with_method(item: dict) -> Dict[ConceptKey, str]:
    """{(ontology_id, statut): method} pour la sortie pipeline de l'item."""
    out = {}
    for c in item.get("pipeline_extraction", []) or []:
        oid = c.get("ontology_id")
        statut = c.get("statut", "present")
        if oid:
            out[(oid, statut)] = c.get("method", "?")
    return out


def _expert_set(annotation: dict) -> Set[ConceptKey]:
    """{(ontology_id, statut)} pour une relecture experte (slot rempli)."""
    if not annotation:
        return set()
    out = set()
    for c in annotation.get("concepts", []) or []:
        oid = c.get("ontology_id")
        statut = c.get("statut", "present")
        if oid:
            out.add((oid, statut))
    return out


def compute_confusion(items: Dict[str, dict]) -> dict:
    """Calcule TP/FP/FN globaux et par méthode, sur les items annotés."""
    tp_total = fp_total = fn_total = 0
    by_method = defaultdict(lambda: {"tp": 0, "fp": 0})
    fp_examples: List[dict] = []
    fn_examples: List[dict] = []

    n_used = 0
    for item_id, item in sorted(items.items()):
        annotation = item.get("annotation_expert")
        if not annotation:
            continue
        n_used += 1
        pipeline = _pipeline_set_with_method(item)
        expert = _expert_set(annotation)

        for key, method in pipeline.items():
            if key in expert:
                tp_total += 1
                by_method[method]["tp"] += 1
            else:
                fp_total += 1
                by_method[method]["fp"] += 1
                fp_examples.append({
                    "item_id": item_id, "ontology_id": key[0], "statut": key[1],
                    "method": method,
                })

        pipeline_keys = set(pipeline.keys())
        for key in expert:
            if key not in pipeline_keys:
                fn_total += 1
                fn_examples.append({
                    "item_id": item_id, "ontology_id": key[0], "statut": key[1],
                })

    def _prf(tp, fp, fn):
        precision = tp / (tp + fp) if (tp + fp) else None
        recall = tp / (tp + fn) if (tp + fn) else None
        f1 = (2 * precision * recall / (precision + recall)
              if precision and recall and (precision + recall) else None)
        return {"tp": tp, "fp": fp, "fn": fn,
                "precision": precision, "recall": recall, "f1": f1}

    global_metrics = _prf(tp_total, fp_total, fn_total)

    per_method = {}
    for method, counts in by_method.items():
        # Rappel non défini par méthode (FN n'a pas de méthode) — seule la
        # précision par méthode a du sens (qualité des sorties de cette brique).
        tp, fp = counts["tp"], counts["fp"]
        precision = tp / (tp + fp) if (tp + fp) else None
        per_method[method] = {"tp": tp, "fp": fp, "precision": precision}

    return {
        "n_items_used": n_used,
        "global": global_metrics,
        "per_method": per_method,
        "fp_examples": fp_examples,
        "fn_examples": fn_examples,
    }


def _cohen_kappa_sets(pairs: List[Tuple[Set[ConceptKey], Set[ConceptKey]]]) -> dict:
    """Kappa de Cohen sur des paires d'ensembles de concepts (annotateur 1 vs 2).

    On construit l'univers des concepts possibles = union de tout ce qui a été
    proposé par l'un OU l'autre relecteur sur l'ensemble des items en double
    annotation, et on calcule un accord binaire "présent/absent" par
    concept-item (matrice 2x2 classique)."""
    a_yes_b_yes = a_yes_b_no = a_no_b_yes = a_no_b_no_placeholder = 0
    # Pour "les deux disent absent", on ne peut énumérer tout l'univers des
    # concepts possibles (ontologie entière) de façon pertinente : on se
    # limite à l'univers observé (union des deux relectures) par item, ce qui
    # est l'approche standard pour ce type de golden (cf. littérature NER).
    a_yes_b_yes = a_yes_b_no = a_no_b_yes = 0
    n_pairs = 0
    for set_a, set_b in pairs:
        universe = set_a | set_b
        for key in universe:
            in_a = key in set_a
            in_b = key in set_b
            n_pairs += 1
            if in_a and in_b:
                a_yes_b_yes += 1
            elif in_a and not in_b:
                a_yes_b_no += 1
            elif not in_a and in_b:
                a_no_b_yes += 1

    if n_pairs == 0:
        return {"kappa": None, "n_pairs": 0, "note": "aucune paire double-annotée disponible"}

    po = a_yes_b_yes / n_pairs  # accord observé (les deux "non" ne sont pas comptés, univers restreint)
    p_a_yes = (a_yes_b_yes + a_yes_b_no) / n_pairs
    p_b_yes = (a_yes_b_yes + a_no_b_yes) / n_pairs
    pe = p_a_yes * p_b_yes + (1 - p_a_yes) * (1 - p_b_yes)
    kappa = (po - pe) / (1 - pe) if (1 - pe) else None

    return {
        "kappa": kappa,
        "n_pairs": n_pairs,
        "a_yes_b_yes": a_yes_b_yes,
        "a_yes_b_no": a_yes_b_no,
        "a_no_b_yes": a_no_b_yes,
        "po": po,
        "pe": pe,
        "note": "Univers restreint à l'union des concepts proposés par les 2 "
                "relecteurs par item (standard NER) — pas l'ontologie entière.",
    }


def _jaccard_f1_agreement(pairs: List[Tuple[Set[ConceptKey], Set[ConceptKey]]]) -> dict:
    """Accord inter-annotateur basé sur Jaccard/F1 (moyenné par item), la
    métrique standard pour ce type d'annotation NER à univers de concepts
    ouvert (cf. note dans compute_kappa : le Kappa de Cohen classique est
    instable ici car l'univers restreint aux concepts proposés gonfle
    artificiellement l'accord attendu par hasard `pe`)."""
    if not pairs:
        return {"jaccard_mean": None, "f1_mean": None, "n_items": 0,
                "n_perfect_agreement": 0}
    jaccards = []
    f1s = []
    n_perfect = 0
    for set_a, set_b in pairs:
        inter = len(set_a & set_b)
        union = len(set_a | set_b)
        jaccard = inter / union if union else 1.0
        precision = inter / len(set_a) if set_a else 1.0
        recall = inter / len(set_b) if set_b else 1.0
        f1 = (2 * precision * recall / (precision + recall)
              if (precision + recall) else 0.0)
        jaccards.append(jaccard)
        f1s.append(f1)
        if set_a == set_b:
            n_perfect += 1
    return {
        "jaccard_mean": sum(jaccards) / len(jaccards),
        "f1_mean": sum(f1s) / len(f1s),
        "n_items": len(pairs),
        "n_perfect_agreement": n_perfect,
    }


def compute_kappa(items: Dict[str, dict]) -> dict:
    pairs = []
    used_items = []
    for item_id, item in sorted(items.items()):
        if not item.get("double_annotation"):
            continue
        a1 = item.get("annotation_expert")
        a2 = item.get("annotation_expert_2")
        if not a1 or not a2:
            continue
        pairs.append((_expert_set(a1), _expert_set(a2)))
        used_items.append(item_id)
    result = _cohen_kappa_sets(pairs)
    result["items_used"] = used_items
    result["jaccard_f1"] = _jaccard_f1_agreement(pairs)
    result["kappa_caveat"] = (
        "Le Kappa de Cohen classique est PEU FIABLE ici : l'univers de "
        "concepts par item est restreint (union des 2 relectures), donc "
        "quasi tous les items sont 'oui' dans cet univers → l'accord "
        "attendu par hasard (pe) est artificiellement gonflé, ce qui peut "
        "produire un Kappa proche de 0 ou négatif MÊME EN CAS D'ACCORD "
        "QUASI-PARFAIT. Préférer `jaccard_f1` (moyenne du Jaccard/F1 par "
        "item), métrique standard pour l'accord inter-annotateur en NER à "
        "univers ouvert."
    )
    return result


def _fmt_pct(x):
    return f"{x * 100:.1f}%" if isinstance(x, (int, float)) else "n/a"


def print_report(confusion: dict, kappa: dict) -> None:
    g = confusion["global"]
    print("=" * 70)
    print("GOLDEN D'EXTRACTION — MÉTRIQUES P/R/F1")
    print("=" * 70)
    print(f"Items utilisés (annotation_expert renseignée) : {confusion['n_items_used']}")
    print()
    print(f"  TP={g['tp']}  FP={g['fp']}  FN={g['fn']}")
    print(f"  Précision : {_fmt_pct(g['precision'])}")
    print(f"  Rappel    : {_fmt_pct(g['recall'])}")
    print(f"  F1        : {_fmt_pct(g['f1'])}")
    print()
    print("-" * 70)
    print("Précision par méthode d'extraction (part de FP par brique)")
    print("-" * 70)
    for method, m in sorted(confusion["per_method"].items(),
                             key=lambda kv: -(kv[1]["tp"] + kv[1]["fp"])):
        n = m["tp"] + m["fp"]
        print(f"  {method:20s}  n={n:4d}  TP={m['tp']:4d}  FP={m['fp']:4d}  "
              f"précision={_fmt_pct(m['precision'])}")
    print()
    print("-" * 70)
    print("Accord inter-annotateur (items double-annotation)")
    print("-" * 70)
    jf = kappa.get("jaccard_f1", {})
    if jf.get("n_items"):
        print(f"  Items utilisés : {jf['n_items']}  "
              f"(accord parfait sur {jf['n_perfect_agreement']}/{jf['n_items']})")
        print(f"  Jaccard moyen : {_fmt_pct(jf['jaccard_mean'])}")
        print(f"  F1 moyen      : {_fmt_pct(jf['f1_mean'])}  <- métrique de référence")
        if kappa.get("kappa") is not None:
            print(f"  (Kappa de Cohen classique = {kappa['kappa']:.3f} — voir mise en garde ci-dessous)")
            print(f"  ⚠️ {kappa['kappa_caveat']}")
    else:
        print(f"  Non calculable : {kappa.get('note')}")
    print()
    print("-" * 70)
    print(f"Exemples de FP (hallucinations pipeline) — {min(10, len(confusion['fp_examples']))} / {len(confusion['fp_examples'])}")
    print("-" * 70)
    for ex in confusion["fp_examples"][:10]:
        print(f"  [{ex['item_id']}] {ex['ontology_id']} ({ex['statut']}) — méthode={ex['method']}")
    print()
    print("-" * 70)
    print(f"Exemples de FN (omissions pipeline) — {min(10, len(confusion['fn_examples']))} / {len(confusion['fn_examples'])}")
    print("-" * 70)
    for ex in confusion["fn_examples"][:10]:
        print(f"  [{ex['item_id']}] {ex['ontology_id']} ({ex['statut']})")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", help="Chemin de sortie JSON détaillé (optionnel)")
    args = parser.parse_args()

    data = extraction_golden.load()
    items = data["items"]

    confusion = compute_confusion(items)
    kappa = compute_kappa(items)
    print_report(confusion, kappa)

    if args.json:
        report = {"confusion": confusion, "kappa": kappa}
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\nRapport JSON écrit dans {args.json}")


if __name__ == "__main__":
    main()
