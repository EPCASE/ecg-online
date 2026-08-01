"""
generate_baseline_report.py — P0.1 : Figer une baseline scientifique.
======================================================================

Consolide, dans un unique fichier JSON reproductible, toutes les versions et
métriques nécessaires pour qu'une prédiction historique (issue de l'app ou
d'un export) puisse être reliée à une configuration complète et identifiable
(cf. `audit_doc/roadmap_scientifique_2026.md` §P0.1).

Contenu généré :
  - pipeline_version (app.neuro_grader.PIPELINE_VERSION)
  - ontology_version (metadata.version de rag_pipeline/data/ontology_v2.json
    + compteurs structurels)
  - versions des jeux de données (cases.json, cases_golden.json,
    scoring_config.json, case_curriculum_map.json)
  - versions/modèles LLM utilisés (grader étudiant, mapping golden)
  - dépendances Python (interpréteur + versions figées de requirements.txt)
  - rapport de métriques d'extraction (précision/rappel/F1 global + par
    méthode, accord inter-annotateur)
  - statut de l'audit golden (bloquants/avertissements)
  - statut de la suite de tests (nombre de tests, pass/fail)
  - commit Git courant

Usage :
    python scripts/generate_baseline_report.py [--out data/baseline_report.json]

Ce script est volontairement autonome (stdlib uniquement + modules internes
déjà présents) afin de pouvoir être exécuté en CI ou en local sans dépendance
supplémentaire, et rejoué à tout moment pour regénérer/vérifier une baseline.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
sys.path.insert(0, ROOT_DIR)


def _run(cmd: list[str]) -> str:
    try:
        out = subprocess.run(
            cmd, cwd=ROOT_DIR, capture_output=True, text=True, check=False
        )
        return out.stdout.strip()
    except Exception as exc:  # pragma: no cover - defensif
        return f"<erreur: {exc}>"


def _load_json(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def get_git_info() -> dict:
    return {
        "commit": _run(["git", "rev-parse", "HEAD"]),
        "commit_short": _run(["git", "rev-parse", "--short", "HEAD"]),
        "branch": _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "describe": _run(["git", "describe", "--tags", "--always"]),
        "date": _run(["git", "log", "-1", "--format=%ai"]),
    }


def get_pipeline_version() -> str:
    try:
        from app import neuro_grader
        return getattr(neuro_grader, "PIPELINE_VERSION", "inconnue")
    except Exception as exc:  # pragma: no cover
        return f"<erreur import neuro_grader: {exc}>"


def get_ontology_version() -> dict:
    onto_path = os.path.join(
        ROOT_DIR, "rag_pipeline", "data", "ontology_v2.json"
    )
    data = _load_json(onto_path)
    if data is None:
        return {"error": f"introuvable: {onto_path}"}
    return data.get("metadata", {})


def get_models_info() -> dict:
    models = {}
    try:
        from app import grader
        models["grader_etudiant_default_model"] = getattr(
            grader, "DEFAULT_MODEL", "inconnu"
        )
    except Exception as exc:  # pragma: no cover
        models["grader_etudiant_default_model"] = f"<erreur: {exc}>"
    try:
        from app import neuro_grader
        models["neuro_grader_pipeline_tag"] = "neuro-pipeline-v3"
    except Exception:
        pass
    golden = _load_json(os.path.join(DATA_DIR, "cases_golden.json"))
    if golden:
        models["golden_mapping_model"] = golden.get("model", "inconnu")
    return models


def get_datasets_versions() -> dict:
    versions = {}
    for name, key in [
        ("cases.json", None),
        ("cases_golden.json", "version"),
        ("scoring_config.json", "version"),
        ("case_curriculum_map.json", None),
    ]:
        path = os.path.join(DATA_DIR, name)
        data = _load_json(path)
        if data is None:
            versions[name] = {"error": "introuvable"}
            continue
        entry: dict = {}
        if key and key in data:
            entry["version"] = data[key]
        else:
            entry["version"] = "n/a (pas de champ version explicite)"
        if "n_cases" in data:
            entry["n_cases"] = data["n_cases"]
        if "cases" in data and isinstance(data["cases"], (list, dict)):
            entry["n_cases"] = entry.get("n_cases", len(data["cases"]))
        if "_meta" in data:
            entry["meta"] = data["_meta"]
        if "updated" in data:
            entry["updated"] = data["updated"]
        versions[name] = entry
    return versions


def get_python_dependencies() -> dict:
    py_version = _run([sys.executable, "-V"])
    req_path = os.path.join(ROOT_DIR, "requirements.txt")
    pinned = []
    if os.path.exists(req_path):
        with open(req_path, encoding="utf-8") as fh:
            pinned = [
                line.strip()
                for line in fh
                if line.strip() and not line.strip().startswith("#")
            ]
    return {
        "python_executable": sys.executable,
        "python_version": py_version,
        "requirements_txt_pinned": pinned,
    }


def get_extraction_metrics() -> dict:
    path = os.path.join(DATA_DIR, "extraction_metrics_report.json")
    data = _load_json(path)
    if data is None:
        return {"error": f"introuvable: {path}"}
    confusion = data.get("confusion", {})
    kappa = data.get("kappa", {})
    return {
        "source_file": "data/extraction_metrics_report.json",
        "n_items_used": confusion.get("n_items_used"),
        "global": confusion.get("global", {}),
        "per_method": confusion.get("per_method", {}),
        "inter_annotator_jaccard_f1": kappa.get("jaccard_f1", {}),
        "inter_annotator_caveat": kappa.get("kappa_caveat"),
    }


def get_golden_audit_status() -> dict:
    audit_script = os.path.join(ROOT_DIR, "scripts", "audit_golden.py")
    if not os.path.exists(audit_script):
        return {"error": "scripts/audit_golden.py introuvable"}
    out = subprocess.run(
        [sys.executable, audit_script],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    text = out.stdout + out.stderr
    return {
        "raw_last_lines": "\n".join(text.strip().splitlines()[-5:]),
        "returncode": out.returncode,
    }


def get_test_suite_status() -> dict:
    out = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    text = out.stderr  # unittest écrit son résumé sur stderr
    return {
        "summary_last_lines": "\n".join(text.strip().splitlines()[-6:]),
        "returncode": out.returncode,
        "all_passed": out.returncode == 0,
    }


def build_baseline_report(run_tests: bool = True, run_audit: bool = True) -> dict:
    report = {
        "baseline_generated_at": datetime.now(timezone.utc).isoformat(),
        "roadmap_reference": "audit_doc/roadmap_scientifique_2026.md §P0.1",
        "git": get_git_info(),
        "pipeline_version": get_pipeline_version(),
        "ontology_version": get_ontology_version(),
        "datasets_versions": get_datasets_versions(),
        "models": get_models_info(),
        "python_dependencies": get_python_dependencies(),
        "extraction_metrics": get_extraction_metrics(),
    }
    if run_audit:
        report["golden_audit_status"] = get_golden_audit_status()
    if run_tests:
        report["test_suite_status"] = get_test_suite_status()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(DATA_DIR, "baseline_report.json"),
        help="Chemin du fichier JSON de sortie",
    )
    parser.add_argument(
        "--skip-tests", action="store_true", help="Ne pas relancer la suite de tests"
    )
    parser.add_argument(
        "--skip-audit", action="store_true", help="Ne pas relancer l'audit golden"
    )
    args = parser.parse_args()

    report = build_baseline_report(
        run_tests=not args.skip_tests, run_audit=not args.skip_audit
    )

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    print(f"Baseline écrite dans {args.out}")
    print(json.dumps(
        {
            "pipeline_version": report["pipeline_version"],
            "ontology_version": report["ontology_version"].get("version"),
            "commit": report["git"]["commit_short"],
        },
        indent=2, ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
