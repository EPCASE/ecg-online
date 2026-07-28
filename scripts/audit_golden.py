#!/usr/bin/env python
"""
audit_golden.py — Audit automatisé de la cohérence golden × ontologie.
========================================================================
Phase 0.1 du plan d'analyse (cf. ROADMAP.md / audit architecture, juillet 2026).

Objectif : détecter, de façon reproductible et outillée (pas un `_dbg*.py`
jetable), les classes de bugs structurels identifiées lors de l'audit
manuel (incohérence validant/descripteur cas 39/40, etc.) AVANT qu'elles ne
remontent comme un bug-report étudiant.

Contrôles effectués (chacun = une fonction `check_*`, un `Finding` par
anomalie) :

  1. `duplicate_concept_role`  — un même concept_id golden apparaît à la fois
     en rôle VALIDANT et en rôle DESCRIPTEUR dans le même cas (root cause du
     bug « miroir » cas 39/40, corrigé côté scorer mais toujours présent
     côté données : 34/75 cas au dernier audit).
  2. `unknown_concept_id`      — un `golden_id` mappé ne correspond à AUCUN
     concept de `ontology_v2.json` (ID périmé / renommé / faute de frappe).
  3. `case_without_validant`   — un cas n'a AUCUN concept validant mappé →
     le scorer onto n'a rien à mesurer, `grade_neuro` se replie sur GPT-4o
     silencieusement (perte de déterminisme non visible sans cet audit).
  4. `dangling_requires`       — un concept a un `requires` qui pointe vers
     un ID absent de l'ontologie (casse `_score_sub_require` silencieusement).
  5. `dangling_excludes` / `dangling_excludes_family` — idem pour `excludes` /
     `excludes_families` (ces derniers référencent un concept PARENT, pas une
     categorie — cf. `scoring_v3._check_excludes`).
  6. `duplicate_label_mapping` — un label de barème (point-clé) apparaît
     mappé à 2 golden_id différents selon la casse/l'espace (source de
     confusion humaine en curation).

Sortie : rapport texte (console) + JSON structuré (`--json out.json`) pour
être consommé par CI / un futur dashboard. Code de sortie 1 si des
anomalies BLOQUANTES sont trouvées (checks 1-4), 0 sinon (les autres sont
des avertissements).

Usage :
    python scripts/audit_golden.py
    python scripts/audit_golden.py --json audit_report.json
    python scripts/audit_golden.py --case 40      # un seul cas
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

GOLDEN_PATH = os.path.join(ROOT_DIR, "data", "cases_golden.json")
SCORING_PATH = os.path.join(ROOT_DIR, "data", "scoring_config.json")
ONTO_CANDIDATES = [
    os.path.join(ROOT_DIR, "rag_pipeline", "data", "ontology_v2.json"),
    os.path.join(ROOT_DIR, "data", "ontology_v2.json"),
]

SEVERITY_BLOCKING = "blocking"   # bug structurel avéré (comme cas 39/40)
SEVERITY_WARNING = "warning"     # dette / risque, pas un bug confirmé


@dataclass
class Finding:
    check: str
    severity: str
    case: Optional[str]
    message: str
    detail: dict = field(default_factory=dict)


def _load_json(path: str) -> dict:
    if not os.path.exists(path):
        print(f"⚠️  Fichier introuvable : {path}", file=sys.stderr)
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_ontology() -> Dict[str, dict]:
    for p in ONTO_CANDIDATES:
        if os.path.exists(p):
            data = _load_json(p)
            return data.get("concepts", data)
    print("⚠️  ontology_v2.json introuvable dans les emplacements attendus.", file=sys.stderr)
    return {}


def _load_golden() -> dict:
    return _load_json(GOLDEN_PATH)


def _load_scoring() -> dict:
    return _load_json(SCORING_PATH)


def _norm_statut(m: dict) -> str:
    s = str((m or {}).get("statut") or "").strip().lower()
    return "absent" if s == "absent" else "present"


def _label_role(scoring_case: Optional[dict], label: str, rang: str = "A") -> str:
    """Rôle effectif d'un label pour un cas donné, en répliquant la logique de
    `app/scoring_config.py::curated_points` (sans importer le package `app`,
    pour garder ce script autonome/portable) :
      - un rôle explicitement configuré (`roles[label]`) prime ;
      - un label listé dans `extra_validants` est toujours validant ;
      - sinon défaut = validant si rang A, complémentaire sinon (ici on ne
        connaît pas le rang réel côté golden ; on ne s'en sert que pour les
        labels absents de `roles`/`extra_validants`, considérés complémentaires
        par prudence — seul le croisement avec `roles` est fiable)."""
    roles = (scoring_case or {}).get("roles", {}) or {}
    extra_validants = set((scoring_case or {}).get("extra_validants", []) or [])
    if label in extra_validants:
        return "validant"
    if label in roles:
        return roles[label]
    return "complementaire"


# ─────────────────────────── Checks ───────────────────────────

def check_duplicate_concept_role(golden: dict, scoring: Optional[dict] = None) -> List[Finding]:
    """Un concept_id présent à la fois côté validant (rang A implicite via
    scoring_config, ici on ne connaît que le mapping golden — donc on détecte
    la duplication au niveau du mapping lui-même : le même golden_id apparaît
    pour 2 labels différents dans le même cas). C'est le signal amont du bug
    validant/descripteur (le rôle exact est tranché par scoring_config.json).

    Si `scoring` (scoring_config.json chargé) est fourni, chaque duplication
    est triée en 2 sévérités distinctes en comparant les tuples (role, statut)
    de chaque occurrence :
      • BLOCKING (« CONFLIT RÉEL ») — les occurrences divergent en rôle
        (validant vs complémentaire) et/ou en statut (present vs absent).
        C'est exactement le pattern derrière le bug cas 39/40 (redondance
        anodine) et le bug cas 4 (contradiction present/absent — plus grave).
      • WARNING (« doublon inoffensif ») — toutes les occurrences ont le
        même (role, statut) : redondance cosmétique du barème, sans risque
        fonctionnel, ne nécessite pas de correction prioritaire.
    Sans `scoring` fourni (rétrocompatibilité), tout duplicat reste BLOCKING
    comme avant (comportement historique du script)."""
    findings = []
    scoring_cases = (scoring or {}).get("cases", {}) if scoring else None
    for num, case in (golden.get("cases") or {}).items():
        mapping = case.get("mapping") or {}
        by_concept: Dict[str, List[str]] = {}
        for label, m in mapping.items():
            cid = m.get("golden_id")
            if not cid:
                continue
            by_concept.setdefault(cid, []).append(label)
        scoring_case = scoring_cases.get(num) if scoring_cases is not None else None
        for cid, labels in by_concept.items():
            if len(labels) <= 1:
                continue
            if scoring_cases is None:
                # Pas de scoring_config disponible : comportement historique.
                findings.append(Finding(
                    check="duplicate_concept_role",
                    severity=SEVERITY_BLOCKING,
                    case=num,
                    message=(f"concept {cid} mappé à {len(labels)} labels différents "
                             f"dans le cas {num} — risque de contradiction "
                             f"trouvé/manqué (cf. bug cas 39/40)."),
                    detail={"concept_id": cid, "labels": labels},
                ))
                continue

            tuples = []
            for lbl in labels:
                m = mapping.get(lbl) or {}
                role = _label_role(scoring_case, lbl)
                statut = _norm_statut(m)
                tuples.append((role, statut))
            is_conflict = len(set(tuples)) > 1
            detail = {
                "concept_id": cid,
                "labels": labels,
                "roles_statuts": [{"label": lbl, "role": r, "statut": s}
                                  for lbl, (r, s) in zip(labels, tuples)],
            }
            if is_conflict:
                findings.append(Finding(
                    check="duplicate_concept_role",
                    severity=SEVERITY_BLOCKING,
                    case=num,
                    message=(f"*** CONFLIT RÉEL *** concept {cid} mappé à {len(labels)} "
                             f"labels dans le cas {num} avec des (rôle, statut) "
                             f"différents {tuples} — risque de contradiction "
                             f"trouvé/manqué (cf. bug cas 39/40 et cas 4)."),
                    detail=detail,
                ))
            else:
                findings.append(Finding(
                    check="duplicate_concept_role_harmless",
                    severity=SEVERITY_WARNING,
                    case=num,
                    message=(f"doublon inoffensif : concept {cid} mappé à {len(labels)} "
                             f"labels dans le cas {num}, tous en ({tuples[0][0]}, "
                             f"{tuples[0][1]}) — redondance cosmétique du barème, "
                             f"aucun risque fonctionnel."),
                    detail=detail,
                ))
    return findings


def check_unknown_concept_id(golden: dict, onto: Dict[str, dict]) -> List[Finding]:
    findings = []
    for num, case in (golden.get("cases") or {}).items():
        mapping = case.get("mapping") or {}
        for label, m in mapping.items():
            cid = m.get("golden_id")
            if cid and cid not in onto:
                findings.append(Finding(
                    check="unknown_concept_id",
                    severity=SEVERITY_BLOCKING,
                    case=num,
                    message=f"golden_id '{cid}' (label « {label} ») absent de l'ontologie.",
                    detail={"concept_id": cid, "label": label},
                ))
    return findings


def check_case_without_validant(golden: dict) -> List[Finding]:
    """Approximation : un cas où AUCUN mapping n'a de golden_id résolu du tout
    (le rôle validant/descripteur vit dans scoring_config.json ; sans le
    croiser on flag ici les cas totalement non mappés — cas encore plus grave :
    repli GPT-4o garanti)."""
    findings = []
    for num, case in (golden.get("cases") or {}).items():
        mapping = case.get("mapping") or {}
        resolved = [m for m in mapping.values() if m.get("golden_id")]
        if not resolved:
            findings.append(Finding(
                check="case_without_validant",
                severity=SEVERITY_BLOCKING,
                case=num,
                message=f"cas {num} : aucun label mappé à un concept ontologique "
                        f"→ repli GPT-4o garanti (perte de déterminisme).",
                detail={"nb_labels": len(mapping)},
            ))
    return findings


def check_dangling_relations(onto: Dict[str, dict]) -> List[Finding]:
    findings = []
    for cid, c in onto.items():
        for rel in ("requires", "excludes"):
            for target in (c.get(rel) or []):
                tid = target if isinstance(target, str) else target.get("id")
                if tid and tid not in onto:
                    findings.append(Finding(
                        check=f"dangling_{rel}",
                        severity=SEVERITY_BLOCKING,
                        case=None,
                        message=f"concept {cid} : '{rel}' pointe vers '{tid}' inexistant.",
                        detail={"concept_id": cid, "relation": rel, "target": tid},
                    ))
        for fam in (c.get("excludes_families") or []):
            # `excludes_families` référence un concept PARENT (pas une catégorie) :
            # scoring_v3._check_excludes() teste `fam in found_set` puis regarde
            # ses descendants. Si `fam` n'est pas un concept_id existant, la
            # famille entière est silencieusement inopérante.
            if fam not in onto:
                findings.append(Finding(
                    check="dangling_excludes_family",
                    severity=SEVERITY_BLOCKING,
                    case=None,
                    message=f"concept {cid} : excludes_families '{fam}' n'est pas "
                            f"un concept_id existant dans l'ontologie.",
                    detail={"concept_id": cid, "family": fam},
                ))
    return findings


def check_duplicate_label_mapping(golden: dict) -> List[Finding]:
    """Labels quasi-identiques (espaces/casse) mappés différemment — dette de
    curation, pas un bug de scoring en soi (WARNING)."""
    findings = []
    for num, case in (golden.get("cases") or {}).items():
        mapping = case.get("mapping") or {}
        norm_seen: Dict[str, str] = {}
        for label, m in mapping.items():
            norm = " ".join(label.split()).strip().lower()
            cid = m.get("golden_id")
            if norm in norm_seen and norm_seen[norm] != cid:
                findings.append(Finding(
                    check="duplicate_label_mapping",
                    severity=SEVERITY_WARNING,
                    case=num,
                    message=f"cas {num} : labels quasi-identiques mappés à des "
                            f"concepts différents ({norm_seen[norm]} vs {cid}).",
                    detail={"label_norm": norm},
                ))
            norm_seen[norm] = cid
    return findings


CHECKS = [
    ("duplicate_concept_role", lambda g, o, s: check_duplicate_concept_role(g, s)),
    ("unknown_concept_id", lambda g, o, s: check_unknown_concept_id(g, o)),
    ("case_without_validant", lambda g, o, s: check_case_without_validant(g)),
    ("dangling_relations", lambda g, o, s: check_dangling_relations(o)),
    ("duplicate_label_mapping", lambda g, o, s: check_duplicate_label_mapping(g)),
]


def run_audit(case_filter: Optional[str] = None) -> List[Finding]:
    golden = _load_golden()
    onto = _load_ontology()
    scoring = _load_scoring()

    if case_filter:
        cases = golden.get("cases", {})
        if case_filter in cases:
            golden = {**golden, "cases": {case_filter: cases[case_filter]}}
        else:
            golden = {**golden, "cases": {}}

    findings: List[Finding] = []
    for _, fn in CHECKS:
        findings.extend(fn(golden, onto, scoring))
    return findings


def print_report(findings: List[Finding]) -> None:
    nb_blocking = sum(1 for f in findings if f.severity == SEVERITY_BLOCKING)
    nb_warning = sum(1 for f in findings if f.severity == SEVERITY_WARNING)

    by_check: Dict[str, List[Finding]] = {}
    for f in findings:
        by_check.setdefault(f.check, []).append(f)

    print("=" * 78)
    print("AUDIT GOLDEN × ONTOLOGIE — Phase 0.1")
    print("=" * 78)
    if not findings:
        print("✅ Aucune anomalie détectée.")
        return

    for check, items in sorted(by_check.items()):
        sev = items[0].severity
        icon = "🔴" if sev == SEVERITY_BLOCKING else "🟡"
        print(f"\n{icon} {check} — {len(items)} occurrence(s)")
        for f in items[:20]:
            case_str = f"[cas {f.case}] " if f.case else ""
            print(f"   {case_str}{f.message}")
        if len(items) > 20:
            print(f"   … et {len(items) - 20} de plus")

    print("\n" + "-" * 78)
    print(f"TOTAL : {nb_blocking} bloquant(s), {nb_warning} avertissement(s) "
          f"sur {len(findings)} anomalie(s).")
    print("-" * 78)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", metavar="FILE", help="Écrit le rapport structuré en JSON.")
    parser.add_argument("--case", metavar="NUM", help="Limite l'audit à un seul cas.")
    parser.add_argument("--fail-on-warning", action="store_true",
                         help="Retourne aussi code 1 si des WARNING existent (CI stricte).")
    args = parser.parse_args()

    findings = run_audit(case_filter=args.case)
    print_report(findings)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump([asdict(x) for x in findings], f, ensure_ascii=False, indent=2)
        print(f"\n📄 Rapport JSON écrit : {args.json}")

    nb_blocking = sum(1 for x in findings if x.severity == SEVERITY_BLOCKING)
    nb_warning = sum(1 for x in findings if x.severity == SEVERITY_WARNING)
    if nb_blocking:
        return 1
    if args.fail_on_warning and nb_warning:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
