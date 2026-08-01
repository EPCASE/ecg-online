# Lien curriculum ↔ scoring_v2 — dérivation automatique

**Date : 01/08/2026**
**Statut : preuve de concept validée sur le pilote P1.2 (10 cas)**

## Question posée

Le curriculum pédagogique (`ECG_Online_curriculum_75_ECG_feedback_IA_2026-07-31.md`,
§11) définit pour chaque ECG d'un parcours :

```json
"required_concepts": ["BAV_DE_HAUT_GRADE", "HYPERKALIEMIE"],
"unsafe_errors": ["FA_LENTE"]
```

Le schéma `scoring_v2` (P1.1/P1.2) contient une information nettement plus
riche par cas (rôle, statut attendu, gravité, groupes alternatifs...).

Faut-il écrire `required_concepts`/`unsafe_errors` à la main pour les 15
parcours (en risquant une divergence avec le barème réel), ou peut-on les
**dériver automatiquement** du golden de scoring déjà validé ?

## Règle de dérivation retenue

Implémentée dans `scripts/derive_curriculum_objectives.py` :

- `required_concepts` = concepts des critères `role == "required"` **et**
  `expected_status == "present"`.
- `unsafe_errors` = concepts des critères `role == "exclusion"` **et**
  `error_severity` dans `{"major", "dangerous"}` (les exclusions de
  sévérité `none`/`minor` sont volontairement exclues : ce sont des
  nuances de scoring, pas des erreurs dangereuses au sens pédagogique).

## Résultat du test sur le pilote (10 cas)

Exécution : `python scripts/derive_curriculum_objectives.py` (par défaut sur
`data/scoring_pilot_v2.json`).

Le cas 27 (« BAV haut degré sur hyperkaliémie »), qui est justement l'exemple
utilisé dans le §11 du curriculum, donne en sortie automatique :

```json
"required_concepts": ["BAV_DE_HAUT_GRADE", "ONDE_T_AMPLE"],
"unsafe_errors": []
```

À comparer à l'exemple écrit à la main dans le curriculum :

```json
"required_concepts": ["BAV_DE_HAUT_GRADE", "HYPERKALIEMIE"],
"unsafe_errors": ["FA_LENTE"]
```

Les deux versions se recoupent sur le concept pivot (`BAV_DE_HAUT_GRADE`)
mais **ne sont pas identiques** :

- le pilote scoring_v2 utilise `ONDE_T_AMPLE` (signe ECG observable) là où
  le curriculum écrit `HYPERKALIEMIE` (cause clinique sous-jacente) — les
  deux golden ne modélisent pas le concept au même niveau (signe vs cause).
- `unsafe_errors` diffère aussi (`[]` vs `["FA_LENTE"]`) car le pilote P1.2
  n'a pas encore de critère d'exclusion pour ce cas — un oubli du pilote
  solo, pas une erreur du mécanisme de dérivation.

**Conclusion : le mécanisme de dérivation fonctionne et produit une sortie
directement exploitable, mais il ne peut être fiable que si le golden
scoring_v2 est complet et cohérent avec la sémantique attendue par le
curriculum.** Il ne remplace pas une relecture humaine — il **détecte les
écarts** entre les deux golden, ce qui est déjà une valeur en soi (évite
qu'ils divergent silencieusement).

## Recommandation

1. Garder les deux golden séparés (le principe §2.1 du roadmap : ne pas
   fusionner golden conceptuel de scoring et objectifs pédagogiques).
2. Utiliser `derive_curriculum_objectives.py` comme **pré-remplissage**
   lors de la rédaction des 15 parcours (Phase 2 du curriculum, §12) :
   l'auteur humain part de la sortie dérivée puis l'ajuste (ajout de
   causes cliniques, sélection du concept le plus lisible pour l'étudiant,
   ajout d'exclusions pédagogiques absentes du scoring).
3. Ajouter un test de non-régression une fois les 15 parcours écrits : si
   un `required_concepts` d'un parcours ne recoupe **aucun** critère
   `role=required` du golden scoring_v2 correspondant, lever une alerte —
   cela signale soit un concept scoring manquant, soit un objectif
   pédagogique non couvert par le barème.
4. Ce mécanisme ne doit être généralisé aux 75 cas qu'après P1.4
   (migration complète des 75 cas vers scoring_v2) — sur les cas encore en
   ancien schéma (`cases_golden.json`/`scoring_config.json`), la dérivation
   n'est pas applicable (pas de `role`/`error_severity`).

## Lien avec le reste du roadmap

- Ne bloque pas / ne remplace pas P1.3 (annotation multi-expert) : le
  script dérive depuis le pilote actuel `single_expert`, donc sa sortie
  hérite du même niveau de confiance provisoire.
- Peut démarrer en parallèle de P1.3 pour la Phase 1 du curriculum
  (`case_curriculum_map.json`) : l'audit de couverture des 75 cas ne
  dépend pas de la fiabilité fine des critères, seulement de leur
  existence.
