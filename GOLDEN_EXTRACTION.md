# 🎯 Golden d'extraction — Méthodologie (P0 bloquant, cf. `../AUDIT.md` §4 et §8)

> Objectif : mesurer pour la première fois la **précision et le rappel réels de
> l'extraction** (NER + résolution ontologique), indépendamment du scoring
> pédagogique. Aujourd'hui on sait seulement si la note finale est juste ;
> on ne sait pas si le pipeline invente ou omet des concepts en cours de route.
>
> Rappel de la distinction (cf. AUDIT §4) :
>
> | | Golden **de scoring** (existant, `data/cases_golden.json`) | Golden **d'extraction** (ce document) |
> |---|---|---|
> | Contenu | 1-3 concepts qui comptent pour la **note** par cas | **Tous** les concepts réellement présents dans le texte d'une réponse |
> | Granularité | Par **cas** (75 cas) | Par **réponse individuelle** (texte libre d'un étudiant) |
> | Sert à | Noter l'étudiant | Auditer la fiabilité du NER + mapping ontologique |

---

## 1. Corpus retenu : 322 réponses réelles sur les 75 cas actuels

Décision actée le 2026-07-29 : on annote des réponses réelles issues du
**Google Sheet `reponses`** (ECG Collector), rejouables via
`scripts/audit_golden_impact.py::_fetch_reponses()`, et **pas** l'ancien POC
`ECG collector/corrections/data.json` (15 cas, 10 étudiants de test, textes
très courts — médiane 42 caractères).

Constat mesuré (2026-07-29) :

| | Ancien POC (rejeté) | **Corpus retenu** |
|---|---|---|
| Cas couverts | 15 | **47 des 75 cas réels** |
| Réponses totales | 150 (dont 99 non vides) | **322** |
| Longueur (médiane / max) | 42 / 355 caractères | **119 / 623 caractères** |
| Nature | Test interne | Vrais utilisateurs de la plateforme |

➡️ Corpus bien plus riche, varié et représentatif de l'usage réel — donc plus
pertinent pour juger la robustesse de l'extraction en conditions réelles.

## 2. Taille de l'échantillon : 100 réponses (au lieu des ~50 de l'audit initial)

Le doublement (50 → 100) est décidé pour :
- Couvrir plus largement les 47 cas disponibles (répartition très inégale :
  cas 2/23/24/37 ont 18-29 réponses, d'autres n'en ont qu'1).
- Donner une marge statistique correcte pour le calcul de P/R/F1 par méthode
  d'extraction (coupe-circuit / juge LLM / fallback).

### Stratégie de sélection (stratifiée, pas aléatoire pure)

Un tirage aléatoire simple sur-représenterait mécaniquement les cas à fort
volume (2, 23, 24, 37 = déjà 87 réponses à eux seuls sur 322). On applique
donc une stratification en 2 passes, implémentée dans
`scripts/build_extraction_golden_sample.py` :

1. **Couverture** : garantir **au moins 1 réponse par cas couvert** (jusqu'à
   47 réponses), en priorisant si possible une réponse de longueur médiane
   (ni la plus courte, ni la plus longue — évite les cas dégénérés "erzerzer").
2. **Complément** : compléter jusqu'à 100 en piochant dans les cas à fort
   volume, avec un **plafond de 5 réponses/cas** pour éviter qu'un seul cas
   n'écrase l'échantillon, réparti proportionnellement au volume disponible.
3. **Double annotation (Kappa de Cohen)** : parmi les 100, **20 réponses**
   (~20 %, tirées aléatoirement mais fixées par graine `random.seed(42)`
   pour reproductibilité) sont marquées `"double_annotation": true` et doivent
   être annotées par 2 relecteurs indépendants.

### Reproductibilité

Le tirage est **déterministe** (graine fixe `SEED = 42`). Relancer
`scripts/build_extraction_golden_sample.py` produit exactement le même
échantillon de 100 réponses tant que le corpus source (`reponses` sheet)
n'a pas changé.

## 3. Format du fichier golden d'extraction

Nouveau fichier : **`data/extraction_golden.json`**

```jsonc
{
  "version": 1,
  "created": "2026-07-29T00:00:00",
  "seed": 42,
  "n_total": 100,
  "n_double_annotation": 20,
  "items": {
    "<item_id>": {                       // ex. "42-017" (cas-index dans l'échantillon)
      "cas": 42,
      "reponse_texte": "Tachycardie régulière à QRS fins...",
      "double_annotation": false,

      // Pré-rempli automatiquement en rejouant le pipeline actuel
      // (candidate_report.generate_candidate_report), à VALIDER/CORRIGER
      // par l'expert — pas à ressaisir de zéro.
      "pipeline_extraction": [
        {
          "terme_brut": "Tachycardie",
          "ontology_id": "TACHYCARDIE",
          "concept_name": "Tachycardie",
          "statut": "present",
          "method": "coupe_circuit"
        }
      ],

      // Rempli par l'annotateur humain via la page /annotation.
      // null tant que non annoté.
      "annotation_expert": null,
      // une fois annoté :
      // "annotation_expert": {
      //   "annotateur": "Pierre",
      //   "annotated_at": "2026-07-30T10:00:00",
      //   "concepts": [
      //     {"ontology_id": "TACHYCARDIE", "concept_name": "Tachycardie",
      //      "statut": "present", "source": "confirme_pipeline"},
      //     {"ontology_id": "QRS_FINS", "concept_name": "QRS fins",
      //      "statut": "present", "source": "ajoute_expert"}
      //   ]
      // }

      // Uniquement pour les 20 items en double annotation :
      "annotation_expert_2": null
    }
  }
}
```

Chaque concept annoté a un `statut` (`present` / `absent`, même convention
que `cases_golden.json`) et un `source` qui trace si l'expert a **confirmé**
une extraction du pipeline, **corrigé** un `ontology_id` erroné, **supprimé**
une hallucination, ou **ajouté** un concept manqué par le pipeline. Ce détail
est ce qui permettra de calculer précision/rappel *par type d'erreur*.

## 4. Outil d'annotation : page web dédiée `/annotation`

Choix : une **page Flask intégrée à l'app existante** (pas d'outil externe
type Label Studio/Prodigy) — cohérent avec le pattern déjà en place pour
`/curation` (`app/server.py`, protection par jeton `CURATION_TOKEN`).

- **Backend** : nouveau module `app/extraction_golden.py` (I/O du fichier
  `data/extraction_golden.json`, écriture atomique — même pattern que
  `golden_config.py`/`scoring_config.py`) + endpoints REST dans `server.py` :
  - `GET  /annotation` → page HTML.
  - `GET  /api/annotation/overview` → liste des 100 items + statut (annoté /
    en attente / double-annotation en désaccord).
  - `GET  /api/annotation/<item_id>` → texte de la réponse + pré-remplissage
    pipeline + picker de concepts ontologiques (réutilise
    `golden_config.search_concepts`).
  - `POST /api/annotation/<item_id>` → enregistre l'annotation experte.
- **Frontend** : `frontend/annotation.html` + JS dédié — réutilise le picker
  de concepts déjà construit pour `/curation` (`search_concepts` +
  `resolve_concept`).
- **Protection** : même jeton `CURATION_TOKEN` que `/curation` (réservé à
  l'enseignant/expert annotateur).

## 5. Export et calcul des métriques

Script `scripts/compute_extraction_metrics.py` (à écrire après que
l'annotation soit avancée) :

1. Charge `data/extraction_golden.json`, ne garde que les items avec
   `annotation_expert` renseigné.
2. Pour chaque item : compare `pipeline_extraction` (rejoué à l'identique ou
   relu depuis le pré-remplissage figé) vs `annotation_expert.concepts` :
   - **Vrai positif** : concept présent dans les deux (même `ontology_id` +
     `statut`).
   - **Faux positif (hallucination)** : concept extrait par le pipeline,
     absent de l'annotation experte.
   - **Faux négatif (omission)** : concept annoté par l'expert, absent de
     l'extraction pipeline.
3. Calcule précision, rappel, F1 **globaux**, puis **par méthode
   d'extraction** (`coupe_circuit` / `juge_llm` / `fallback`) pour identifier
   quelle brique génère le plus d'erreurs (répond aussi à P1.8 de la
   roadmap : ablation par brique).
4. Sur les 20 items en double annotation : calcule le **Kappa de Cohen**
   entre `annotation_expert` et `annotation_expert_2` (accord inter-expert),
   pour savoir si le golden d'extraction lui-même est fiable.
5. Sortie : rapport texte + JSON (`extraction_metrics_report.json`),
   pattern similaire à `scripts/audit_golden_impact.py`.

## 5bis. Accélérateur : GPT-5.6 comme second annotateur automatique

Proposition (2026-07-29) : plutôt que de faire annoter les 100 réponses à la
main dans leur intégralité, on utilise **GPT-5.6 comme relecteur indépendant
automatique**, en complément (pas en remplacement) de l'expert humain.

### Pourquoi c'est utile ET pourquoi il faut se méfier de la circularité

Le pipeline d'extraction (`ner_extractor.py`) utilise déjà GPT-4o. Si on
demandait au **même modèle avec le même prompt** de « vérifier » sa propre
sortie, on mesurerait la cohérence du modèle avec lui-même, pas sa justesse
clinique — biais de circularité qui invaliderait tout le golden.

Pour que GPT-5.6 apporte une vraie valeur de second-lecteur, 3 garde-fous :

1. **Modèle différent** de celui du pipeline (GPT-5.6 ≠ GPT-4o utilisé par
   `ner_extractor.MODEL` / `candidate_report`) → pas le même biais de modèle.
2. **Prompt différent et plus exhaustif**, écrit indépendamment du prompt de
   `ner_extractor.SYSTEM_PROMPT` — on ne demande pas « confirme cette liste »
   mais **« liste tous les concepts ECG présents dans ce texte, à l'aveugle »**
   (sans jamais montrer la sortie du pipeline au modèle).
3. **GPT-5.6 ne remplace pas l'expert humain** : son rôle est de proposer un
   **brouillon candidat supplémentaire** (comme le fait déjà `pipeline_extraction`
   pour le pipeline), que l'expert peut accepter/rejeter au même titre que
   les concepts du pipeline. La décision finale reste 100 % humaine
   (`annotation_expert`), sinon le golden ne mesurerait plus rien d'indépendant.

### Implémentation proposée

- Nouveau module `app/gpt_annotator.py` : appelle GPT-5.6 avec un prompt
  d'extraction EXHAUSTIVE (contrairement au NER de production qui a des
  contraintes de scoring, ce prompt n'a pas d'enjeu de note — il peut être
  plus verbeux/complet), en structured output (liste de concepts + statut).
- Le script `build_extraction_golden_sample.py` est étendu : en plus de
  `pipeline_extraction` (GPT-4o, prod), chaque item reçoit un champ
  `gpt56_extraction` (second avis indépendant).
- Dans la page `/annotation`, un **3ᵉ jeu de puces** apparaît (à côté des
  puces violettes pipeline et vertes ajout expert) : orange = suggestion
  GPT-5.6 non encore présente côté pipeline — l'expert clique pour
  accepter/rejeter, exactement comme pour les concepts pipeline.
- Effet attendu : réduit le travail de saisie manuelle (l'expert n'a plus
  qu'à trier des propositions, quasi jamais à taper un concept de zéro),
  tout en gardant l'annotation finale **humaine et indépendante** du pipeline
  évalué (donc valide pour mesurer sa précision/rappel sans circularité).
- **Non bloquant** : si GPT-5.6 n'est pas disponible/configuré, la page
  fonctionne comme avant (pré-remplissage pipeline uniquement).

## 6. Statut d'avancement

| Étape | Statut |
|---|---|
| 1. Ce document de méthodologie | ✅ |
| 2. Script de sélection stratifiée (100 réponses, seed=42) | ✅ `scripts/build_extraction_golden_sample.py` |
| 3. Pré-remplissage via rejeu du pipeline | ✅ (même script, 100/100 items pré-remplis) |
| 3bis. Second avis indépendant GPT-5.6 | ✅ `app/gpt_annotator.py`, 100/100 items (option `--gpt56`) |
| 4. Page d'annotation `/annotation` | ✅ `frontend/annotation.html` + `.js`, endpoints `app/server.py` |
| 5. Script de calcul des métriques (P/R/F1 + Kappa) | ✅ `scripts/compute_extraction_metrics.py` |
| 6. Campagne d'annotation réelle (expert) | ✅ 100/100 items, 18/20 doubles annotations |
| 7. Rapport final + mise à jour `AUDIT.md`/`ROADMAP.md` | ✅ `AUDIT.md` §0/§1/§4bis/§5/§8 mis à jour |

## 7. Résultats (2026-07-29, sur 100/100 items annotés)

Calculés via `python scripts/compute_extraction_metrics.py`, détail complet
dans `data/extraction_metrics_report.json`.

**Global** (547 TP / 58 FP / 66 FN) :

| Précision | Rappel | F1 |
|---|---|---|
| **90.4 %** | **89.2 %** | **89.8 %** |

**Précision par méthode d'extraction** (part de FP par brique — répond à
P1.8 de la roadmap, ablation par méthode) :

| Méthode | n | Précision |
|---|---|---|
| `coupe_circuit` | 483 | **96.5 %** |
| `juge_llm` | 84 | 67.9 % |
| `lexical_backstop` | 26 | 69.2 % |
| `fallback_subterm` | 9 | 66.7 % |
| `pattern_inference` | 3 | 0.0 % (échantillon trop petit) |

➡️ Le coupe-circuit lexical est très fiable ; les briques de secours
(`juge_llm`, `lexical_backstop`, `fallback_subterm`) génèrent
proportionnellement 3x plus de faux positifs — cohérent avec leur rôle de
filet de sécurité sur les cas ambigus, mais à surveiller/améliorer en
priorité.

**Fiabilité du golden lui-même** (18 items en double annotation complétés) :
Jaccard moyen **97.7 %**, F1 inter-annotateur **98.7 %**, accord parfait sur
16/18 items. ⚠️ Le Kappa de Cohen classique calculé sur un univers restreint
ressort artificiellement proche de 0 (-0.021) malgré cet excellent accord —
biais connu de la métrique dans ce contexte (univers de concepts ouvert, très
peu de "vrais négatifs" observables) ; le rapport documente cette mise en
garde et privilégie Jaccard/F1 comme métrique de référence pour ce golden.


## Repères techniques

- Sélection : `python scripts/build_extraction_golden_sample.py`
- Golden d'extraction : `data/extraction_golden.json`
- Page d'annotation : `/annotation` (jeton `CURATION_TOKEN` si configuré)
- Calcul métriques : `python scripts/compute_extraction_metrics.py [--json data/extraction_metrics_report.json]`
