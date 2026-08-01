# P0.1 — Baseline scientifique (versionnée)

> Réf. roadmap : `audit_doc/roadmap_scientifique_2026.md` §P0.1 — *« Figer une
> baseline scientifique »*.
> Critère de sortie visé : **chaque prédiction historique peut être reliée à
> une configuration complète et identifiable.**

## Ce que c'est

Un script reproductible — `scripts/generate_baseline_report.py` — qui
consolide, dans `data/baseline_report.json`, tous les identifiants de version
nécessaires pour caractériser sans ambiguïté un état du système à un instant
donné :

- **`pipeline_version`** — tag exposé par `app/neuro_grader.py`
  (`PIPELINE_VERSION`), déjà retourné par `/api/health` et `/api/grade`.
- **`ontology_version`** — `metadata.version` + compteurs structurels de
  `rag_pipeline/data/ontology_v2.json` (version, source `.owl`, nombre de
  concepts/patterns/findings/qualifiers/relations, date du dernier patch).
- **`datasets_versions`** — versions/tailles de `cases.json`,
  `cases_golden.json` (v1), `scoring_config.json` (v1),
  `case_curriculum_map.json` (75 cas, 15 parcours).
- **`models`** — modèle LLM du grader étudiant (`DEFAULT_MODEL` dans
  `app/grader.py`, ex. `gpt-4o-2024-08-06`), tag du pipeline neuro
  (`neuro-pipeline-v3`), modèle utilisé pour le mapping golden
  (`cases_golden.json.model`, ex. `gpt-5.5`).
- **`python_dependencies`** — version de l'interpréteur Python + versions
  figées de `requirements.txt`.
- **`extraction_metrics`** — rapport de `scripts/compute_extraction_metrics.py`
  (`data/extraction_metrics_report.json`) : précision/rappel/F1 globaux et
  par méthode d'extraction (coupe_circuit, juge_llm, pattern_inference,
  fallback_subterm, lexical_backstop), accord inter-annotateur
  (Jaccard/F1 moyens, préférés au Kappa de Cohen — cf. `kappa_caveat`).
- **`golden_audit_status`** — dernières lignes de `scripts/audit_golden.py`
  (nombre de bloquants/avertissements).
- **`test_suite_status`** — résultat de `python -m unittest discover -s tests`
  (nombre de tests, pass/fail).
- **`git`** — commit, branche, date.

## Comment régénérer la baseline

```powershell
cd ecg-online
.\.venv\Scripts\python.exe scripts\generate_baseline_report.py
```

Options :
- `--out <chemin>` : changer le fichier de sortie (défaut
  `data/baseline_report.json`).
- `--skip-tests` / `--skip-audit` : ne pas relancer la suite de tests /
  l'audit golden (utile pour une génération rapide, au prix d'une baseline
  moins complète).

Le script est volontairement autonome (stdlib + modules internes du projet),
sans dépendance supplémentaire, pour pouvoir être rejoué en CI ou en local à
tout moment.

## Snapshot de référence (2026-08-01, commit `10ddd55`)

| Élément | Valeur |
|---|---|
| `pipeline_version` | `neuro-v1.1` |
| `ontology_version` | `2.0` (345 concepts, 53 patterns, 146 findings) |
| `cases_golden.json` | version 1 (75 cas) |
| `scoring_config.json` | version 1 (75 cas) |
| `case_curriculum_map.json` | 75 cas / 15 parcours (pas de champ version) |
| Modèle grader étudiant | `gpt-4o-2024-08-06` |
| Modèle mapping golden | `gpt-5.5` |
| Python | 3.11.9 (venv `ecg-online/.venv`) |
| Extraction — Précision / Rappel / F1 | 90.4 % / 89.2 % / 89.8 % (n=100 items) |
| Accord inter-annotateur (Jaccard/F1 moyens) | 97.7 % / 98.7 % (18 items double-annotés, 16 en accord parfait) |
| Audit golden | 0 bloquant, 21 avertissements (doublons inoffensifs) |
| Suite de tests | 18/18 tests passants |

Le détail complet et exact est dans `data/baseline_report.json` (généré, ne
pas éditer à la main — relancer le script pour le mettre à jour).

## Limites connues / dette identifiée à cette baseline

- `cases.json` et `case_curriculum_map.json` n'ont pas de champ `version`
  explicite (contrairement à `cases_golden.json`/`scoring_config.json`). À
  envisager pour une prochaine itération de P0.1/P0.3 si des changements
  fréquents de ces fichiers doivent être tracés précisément.
- Le Kappa de Cohen classique calculé sur l'accord inter-annotateur est peu
  informatif ici (univers restreint par item) — préférer la métrique
  Jaccard/F1 fournie à côté (voir `kappa_caveat` dans le rapport).

## Prochaine étape suggérée

Créer un tag Git marquant ce point comme le premier baseline officiel, p. ex. :

```powershell
git tag -a baseline-p0.1-2026-08-01 -m "P0.1 : première baseline scientifique versionnée"
git push origin baseline-p0.1-2026-08-01
```
