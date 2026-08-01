# Bug — Commentaire pédagogique incohérent sur le cas 15 (bloc indifférencié)

**Date de découverte : 01/08/2026**
**Sévérité : moyenne pour le cas 15 isolément, MAJEURE à l'échelle du produit**
(audit du 01/08/2026 : 125/153 `golden_id` sans `EDNEntry`, dont 48 concepts
diagnostiques touchant 59 des 75 cas — voir section « Portée de l'impact »)
**Statut : cas 15 CORRIGÉ** (branche `fix/edn-bloc-indifferencie`, commit
`381a149`, non fusionné dans `main`) — **le trou de couverture générique
reste ouvert et documenté ci-dessous, remédiation à planifier séparément**

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

## Portée de l'impact — audit exhaustif effectué le 01/08/2026

Le correctif ponctuel du cas 15 étant appliqué (branche `fix/edn-bloc-indifferencie`,
commit `381a149`), un audit systématique a été mené sur les **153 `golden_id`
distincts** utilisés dans les mappings de `cases_golden.json` à travers les
75 cas, en croisant avec `rag_pipeline/edn_knowledge_base.py` (`get_edn_entry`)
et la `categorie` de chaque concept dans `data/ontology_v2.json`.

**Résultat : le trou de couverture EDN est bien plus large que le seul cas 15.**

- **125 des 153 `golden_id` utilisés (82 %) n'ont aucune `EDNEntry`.**
- Parmi eux, **48 sont des concepts diagnostiques** (`categorie` commençant par
  `DIAGNOSTIC_`, donc de vrais points de conclusion clinique et pas de simples
  descripteurs/qualificatifs comme `PR_NORMAL` ou `AXE_NORMAL_DU_QRS`) :
  - **3 `DIAGNOSTIC_URGENT`** : `EXTRASYSTOLE_A_COUPLAGE_COURT` (cas 36, 50),
    `CARDIOVERSION_ELECTRIQUE` (cas 50, 63), `WOLF_MALIN` (cas 52).
  - **29 `DIAGNOSTIC_MAJEUR`**, dont des diagnostics majeurs à fort enjeu
    pédagogique/clinique : `SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_AVEC_SUS_DECALAGE_DU_SEGMENT_ST`
    (12 cas : 53, 57–65, 68, 70), `FAISCEAU_ACCESSOIRE_A_CONDUCTION_ANTEROGRADE` (5 cas),
    `TACHYCARDIE_SINUSALE` (5 cas), `ECG_NORMAL` (3 cas : 3, 8, 39 — même le
    diagnostic « normal » n'a pas d'entrée !), `HYPERKALIEMIE`, `BAV_DE_TYPE_1`,
    `RYTHME_D_ECHAPPEMENT_JONCTIONNEL`, `SYNDROME_CORONARIEN_...SANS_ELEVATION_ST`,
    `PERICARDITE`, `TAMPONNADE`, `MYOCARDITE`, `TAKOTSUBO`, `ASPECT_DE_BRUGADA_DE_TYPE_1`,
    `SYNDROME_DE_BRUGADA`, `AMYLOSE`, `HYPOKALIEMIE`, `QT_COURT`, `MICROVOLTAGE`,
    et d'autres (liste complète disponible via le script d'audit ci-dessous).
  - **16 `DIAGNOSTIC_MOYEN`**, dont `PAS_D_ANOMALIE_DE_LE_REPOLARISATION` (16 cas)
    et `COURANT_DE_LESION_SOUS_EPICARDIQUE` (19 cas) qui sont très fréquemment
    utilisés dans les cas d'ischémie/SCA.
- **59 des 75 cas (79 %)** ont au moins un concept `DIAGNOSTIC_*` sans `EDNEntry`
  — donc potentiellement exposés au même mode de défaillance que le cas 15
  (GPT sans la bonne citation de cours, susceptible de substituer une entrée
  proche mais incorrecte).
- Répartition par famille clinique (nombre de concepts diagnostiques manquants) :
  `rythme` (24), `conduction` (16), `ischemie` (13), `pericarde` (9), `genetique` (5),
  `normal` (3), `hypertrophie` (3), `embolie` (2), `metabolique` (2), `infiltratif` (2),
  `technique` (1) — **toutes les familles cliniques sont touchées**, sans exception.

Script d'audit utilisé (reproductible) :
```python
import json, sys
sys.path.insert(0, "rag_pipeline")
from edn_knowledge_base import get_edn_entry

onto = json.load(open("../data/ontology_v2.json", encoding="utf-8"))["concepts"]
golden = json.load(open("data/cases_golden.json", encoding="utf-8"))["cases"]

from collections import defaultdict
usage = defaultdict(list)
for num, c in golden.items():
    for label, m in c["mapping"].items():
        usage[m.get("golden_id")].append(num)

missing_diag = [
    (gid, onto.get(gid, {}).get("categorie", "?"), sorted(set(int(n) for n in nums)))
    for gid, nums in usage.items()
    if not get_edn_entry(gid) and onto.get(gid, {}).get("categorie", "").startswith("DIAGNOSTIC")
]
print(f"{len(usage)} golden_ids distincts, {len(missing_diag)} concepts diagnostiques sans EDNEntry")
```

### Recommandation

Compte tenu de l'ampleur (125 concepts, 59 cas), il n'est **pas raisonnable
de corriger cela cas par cas en réactif** (comme pour le cas 15). Deux options
pour la suite, à trancher séparément de ce ticket :

1. **Remédiation manuelle priorisée** : rédiger d'abord les `EDNEntry` pour
   les 3 `DIAGNOSTIC_URGENT` et les 29 `DIAGNOSTIC_MAJEUR` (32 entrées),
   qui couvrent le risque clinique/pédagogique le plus élevé (SCA ST+,
   Brugada, tamponnade, hyperkaliémie, WPW, etc.), en s'appuyant sur
   `cases_reference.json`/`fiche_secours` de chaque cas concerné comme
   source de texte clinique déjà validé (même méthode que pour le cas 15).
2. **Remédiation structurelle** : générer semi-automatiquement un squelette
   d'`EDNEntry` pour chaque `golden_id` manquant à partir des champs déjà
   présents dans `ontology_v2.json` (`concept_name`, `synonymes`) et de
   `cases_reference.json` (texte clinique), puis relecture/validation
   manuelle rang par rang — plus rapide à grande échelle que la rédaction
   entièrement manuelle.

Dans les deux cas, il serait utile de compléter `get_edn_entries_for_ids()`
avec un log d'avertissement (`logger.warning`) quand un `golden_id` demandé
par `_build_course_context()` n'a pas d'entrée, pour rendre ce trou de
couverture visible en production au lieu de silencieux — actuellement
aucune télémétrie ne signale ces trous, ils ne sont détectables que par
audit manuel comme celui-ci.

## Périmètre de cette découverte

Ce bug a été découvert incidemment en construisant le parcours curriculum
`bundle-branch-advanced` (Phase 2, cas 16/11/12/15/49) sur la branche
`agent/curriculum-phase2` — il est totalement indépendant du travail sur
le curriculum et n'a pas été corrigé ici. Le correctif touche
`rag_pipeline/edn_knowledge_base.py` et/ou `data/scoring_config.json`,
tous deux actifs sur `main` (pipeline de production déployé sur Scalingo).
