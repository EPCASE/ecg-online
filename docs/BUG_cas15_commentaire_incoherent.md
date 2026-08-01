# Bug — Commentaire pédagogique incohérent sur le cas 15 (bloc indifférencié)

**Date de découverte : 01/08/2026**
**Sévérité : moyenne** (n'affecte que le cas 15 sur 75, mais commentaire
pédagogique activement trompeur — cite une règle de cours qui contredit le
diagnostic attendu du cas)
**Statut : documenté, PAS corrigé** (correctif hors périmètre de la branche
`agent/curriculum-phase2` ; touche le pipeline de production sur `main`)

---

## Symptôme

Sur le cas 15 (« bloc indifférencié »), un étudiant ayant noté « bloc
intraventriculaire aspécifique » (= le bon diagnostic) reçoit un commentaire
pédagogique du correcteur qui :

- affirme que le diagnostic attendu est un **bloc de branche gauche (BBG)** ;
- cite le cours SFC Item 231 sur le BBG (« Le BBG complet se caractérise
  par : QRS > 120 ms... ») comme si c'était la référence pertinente ;
- reproche à l'étudiant d'avoir noté « bloc intraventriculaire aspécifique »
  en la qualifiant de réponse contradictoire avec le BBG.

C'est l'inverse de la réalité clinique du cas : le cas 15 est spécifiquement
construit pour qu'on **exclue** BBD et BBG et qu'on conclue à un bloc
indifférencié (cf. `cases_reference.json`, cas 15, `fiche_secours.pieges` :
« Ne pas conclure à un bloc de branche gauche : l'aspect qR en DI ne
correspond pas à un BBG typique »).

## Reproduction

1. Ouvrir le cas 15 (`bloc indifférencié`).
2. Soumettre une réponse contenant « bloc intraventriculaire aspécifique »
   (ou un synonyme proche : « bloc indifférencié », etc.) comme diagnostic.
3. Observer le commentaire pédagogique généré : il cite le cours sur le BBG.

## Cause racine (confirmée par inspection du code, pas seulement supposée)

Deux anomalies cumulées, indépendantes du travail sur le curriculum :

### 1. `data/scoring_config.json` — le cas 15 est le seul des 75 sans entrée

```
python -c "
import json
d = json.load(open('data/scoring_config.json', encoding='utf-8'))
all_ids = sorted(int(k) for k in d['cases'].keys())
missing = sorted(set(range(1,76)) - set(all_ids))
print('missing:', missing)
"
# → missing: [15]
```

Sans config, `app/scoring_config.py::curated_points()` retombe sur un rôle
par défaut (rang A ⇒ validant) recalculé à partir de `cases_reference.json`
— ce chemin de repli n'a probablement jamais été testé pour ce cas précis.

### 2. `rag_pipeline/edn_knowledge_base.py` — `BLOC_INTRAVENTRICULAIRE_ASPECIFIQUE` n'a **aucune `EDNEntry`**

Vérifié : le concept existe bien dans l'ontologie réelle utilisée en
production (`data/ontology_v2.json`, confirmé aussi dans l'index construit
`rag_pipeline/rag_index/metadata_ontologie.json`, `source_file:
ontology_v2.json`), avec 11 synonymes dont « bloc indifférencié » :

```json
"BLOC_INTRAVENTRICULAIRE_ASPECIFIQUE": {
  "concept_name": "Bloc intraventriculaire aspécifique",
  "categorie": "DIAGNOSTIC_MOYEN",
  "poids": 3,
  "has_qualifiers": ["QRS_LARGE"],
  "excludes_families": ["BLOC_DE_BRANCHE"],
  "synonymes": ["bloc indifférencié", "aspect de bloc indifférencié", ...]
}
```

Mais **aucune entrée `EDNEntry` dans `rag_pipeline/edn_knowledge_base.py`**
ne référence `BLOC_INTRAVENTRICULAIRE_ASPECIFIQUE` dans son
`ontology_ids`. Recherche confirmée :

```
grep -r "BLOC_INTRAVENTRICULAIRE_ASPECIFIQUE" rag_pipeline/edn_knowledge_base.py
# → aucun résultat
```

Conséquence dans `rag_pipeline/pedagogical_feedback.py::_build_course_context()` :
`get_edn_entry("BLOC_INTRAVENTRICULAIRE_ASPECIFIQUE")` retourne `None`
(comportement normal et sans exception de `edn_knowledge_base.get_edn_entry`,
`app/edn_knowledge_base.py:875-877`), donc aucun extrait de cours n'est
injecté dans le prompt GPT pour ce concept spécifique. Le prompt système
(`SYSTEM_PROMPT` dans `pedagogical_feedback.py`) demande cependant à GPT de
« citer le cours SFC » pour les concepts pertinents — en l'absence de la
bonne entrée, GPT semble combler ce vide en s'appuyant sur l'entrée EDN
existante la plus proche disponible dans le contexte (celle du BBG, très
complète, avec des `pieges_classiques` qui parlent justement de confusion
bloc de branche / diagnostic différentiel), produisant un commentaire
cohérent en apparence mais cliniquement faux pour ce cas précis.

### Point supplémentaire à vérifier (non confirmé, piste)

Le champ `excludes_families: ["BLOC_DE_BRANCHE"]` défini sur ce concept
dans l'ontologie n'est référencé nulle part dans `rag_pipeline/*.py`
(recherche texte confirmée) — c'est une donnée d'exclusion morte, jamais
lue par le scorer ni le juge neurosymbolique. Si elle était exploitée, elle
pourrait servir à bloquer explicitement toute mention du BBG dans le
feedback de ce cas.

## Correctifs proposés (non appliqués)

1. **Ajouter l'entrée manquante dans `edn_knowledge_base.py`** :
   ```python
   EDNEntry(
       ontology_ids=["BLOC_INTRAVENTRICULAIRE_ASPECIFIQUE"],
       rang_edn="B",
       titre_cours="I.B.1 — Bloc intraventriculaire aspécifique (diagnostic d'élimination)",
       points_cles=[
           "Diagnostic d'élimination devant un QRS large (> 120 ms) qui ne remplit "
           "ni les critères de bloc de branche droite (V1/V6) ni ceux de bloc de "
           "branche gauche (V1/V6/DI/aVL).",
       ],
       pieges_classiques=[
           "Ne pas conclure à un bloc de branche gauche ou droite par défaut devant "
           "un QRS large : vérifier explicitement les critères des deux avant de "
           "retenir un bloc indifférencié.",
       ],
       extrait_cours=(
           "Le bloc intraventriculaire aspécifique (ou bloc indifférencié) est un "
           "diagnostic d'élimination en présence d'un QRS large (> 120 ms) mais ne "
           "présentant pas les caractéristiques d'un bloc de branche droite ou gauche."
       ),
   ),
   ```
   (texte directement réutilisable depuis `cases_reference.json`, cas 15,
   `fiche_secours.citation_source` — déjà rédigé et validé cliniquement).

2. **Compléter `data/scoring_config.json` pour le cas 15**, pour qu'il ne
   soit plus le seul cas sans config explicite (rôles validant/complémentaire
   à définir en cohérence avec `cases_golden.json` du même cas).

3. *(Optionnel, plus structurel)* faire exploiter `excludes_families` par le
   juge neurosymbolique ou au minimum par `pedagogical_feedback.py`, pour
   empêcher explicitement toute citation de cours sur une famille de
   concepts exclue par le concept réellement attendu.

## Portée de l'impact

Recherche des autres concepts golden potentiellement dans le même cas
(présents dans `cases_golden.json` mais absents de `edn_knowledge_base.py`)
— **non exhaustivement vérifiée**, à faire avant de corriger uniquement ce
cas ponctuel : il est possible que d'autres `golden_id` utilisés dans les
75 cas souffrent du même trou de couverture EDN.

## Périmètre de cette découverte

Ce bug a été découvert incidemment en construisant le parcours curriculum
`bundle-branch-advanced` (Phase 2, cas 16/11/12/15/49) sur la branche
`agent/curriculum-phase2` — il est totalement indépendant du travail sur
le curriculum et n'a pas été corrigé ici. Le correctif touche
`rag_pipeline/edn_knowledge_base.py` et/ou `data/scoring_config.json`,
tous deux actifs sur `main` (pipeline de production déployé sur Scalingo).
