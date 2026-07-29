# 📖 Data Dictionary — `/api/grade` (contrat JSON actuel)

> Document minimal (Palier 2, item 5 de `FEUILLE_DE_ROUTE_ALIGNEE.md` §4).
> Objectif : documenter le contrat de sortie **tel qu'il existe réellement**
> aujourd'hui, pas une cible. À étendre au fil des évolutions (`ontology_version`,
> `HUMAN_REVIEW`, etc. — cf. Palier 2/3 de la feuille de route).

## Endpoint

`POST /api/grade`

### Requête

```json
{
  "num": 12,
  "answer": "Texte libre de l'étudiant…",
  "session": "uuid-session-anonyme",
  "meta": { "...": "métriques d'usage optionnelles, cf. note UX §13" }
}
```

### Réponse (200 ou 502 si erreur du backend utilisé)

| Champ | Type | Origine | Description |
|---|---|---|---|
| `score` | int (0-100) | `Correction.to_dict()` | Score global. |
| `score_diagnostic` | int (0-100) | idem | Sous-score : diagnostic principal. |
| `score_descriptif` | int (0-100) | idem | Sous-score : description du tracé. |
| `verdict` | str | idem | Phrase de synthèse. |
| `diagnostic_retenu` | str | idem | Diagnostic identifié par le pipeline dans la réponse. |
| `correspondance` | enum | idem | `exacte` / `acceptable` / `partielle` / `incorrecte`. |
| `type_erreur` | enum | idem | `aucune` / `etudiant` / `incomplet` / `formulation`. |
| `elements_trouves` | list[{label, rang}] | idem | Éléments correctement identifiés (rang A/B/C). |
| `elements_manques` | list[{label, rang, importance}] | idem | Éléments attendus non trouvés. |
| `elements_errones` | list[{label, correction}] | idem | Affirmations incorrectes/dangereuses. |
| `commentaire` | str (markdown) | idem | Feedback pédagogique (GPT ou synthèse déterministe). |
| `concepts_detectes` | list[{terme, concept, statut, id, resolu}] | `neuro_grader._concepts_for_review()` | Ce que le NER a extrait de la réponse (P5, validation étudiante 👍/👎). |
| `model` | str | `Correction.to_dict()` | Modèle/pipeline ayant produit la correction (ex. `neuro-pipeline-v3`, `gpt-4o-2024-08-06`). |
| `error` | str \| null | idem | Message d'erreur si le backend utilisé a échoué. |
| `backend` | enum | `server.py` | `neuro` ou `gpt` — backend qui a **effectivement** produit la correction. |
| `pipeline_version` | str | `neuro_grader.PIPELINE_VERSION` | Version figée du pipeline neurosymbolique (ex. `neuro-v1.1`). **Palier 1.** |
| `response_id` | str (UUID) | `server.py` (généré à chaque appel) | Identifiant unique de cette correction précise. **Palier 2.** |
| `prediction_id` | str (UUID) | idem (alias de `response_id`) | Nom conforme à la littérature ML ; même valeur que `response_id` aujourd'hui. **Palier 2.** |
| `resolution` | object | `abstention.classify()` | Cf. section dédiée ci-dessous. **Palier 1 → 2.** |
| `reference` | object | `server.py` | Corrigé enseignant, révélé **après** correction (titre, famille, interprétation, points clés, fiche de secours). |
| `scoring` | object | `scoring_config.split_for_grader()` | Barème utilisé (validants/complémentaires), pour audit pédagogique. |

### Champ `resolution` (traçabilité du choix de backend)

```json
"resolution": {
  "status": "SUCCESS | LOW_CONFIDENCE | FALLBACK_GPT | TECHNICAL_ERROR | ABSTAIN",
  "reason": "chaîne explicative ou null",
  "primary_backend": "neuro | gpt",
  "used_backend": "neuro | gpt"
}
```

| Statut | Signification | Déclenché par |
|---|---|---|
| `SUCCESS` | Correction produite normalement, confiance suffisante. | Cas nominal. |
| `LOW_CONFIDENCE` | Correction produite, mais peu/aucun concept résolu par le NER. | `abstention.classify()`, seuil `MIN_RESOLVED_CONCEPTS_FOR_CONFIDENCE`. |
| `FALLBACK_GPT` | Le pipeline neuro était indisponible/inapplicable pour ce cas → repli GPT-4o. | `neuro_grader.grade_neuro()` renvoie `None`, motif tracé via `last_skip_reason()`. |
| `TECHNICAL_ERROR` | Le backend utilisé (neuro ou gpt) a levé une exception/erreur API. | `Correction.error` non vide. |
| `ABSTAIN` | *(Réservé, non déclenché aujourd'hui)* aucun backend n'a pu produire de correction fiable. | À implémenter si un jour GPT échoue aussi après repli neuro. |

## Non couvert par ce document (volontairement, cf. anti-scope-creep §3)

- `ontology_version` : pas encore exposé (Palier 2, semaine 3).
- États `HUMAN_REVIEW` : nécessitent une file de curation qui n'existe pas encore.
- Endpoints autres que `/api/grade` (QCM, thèmes, curation…) : non documentés ici,
  cf. les docstrings de `server.py` en tête de fichier pour la liste complète des routes.
