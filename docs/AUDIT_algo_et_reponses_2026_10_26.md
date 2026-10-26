# Audit algorithme + nouvelles réponses étudiantes — 26 oct. 2026

Périmètre : pipeline **neuro-v1.3** (déployé 13/08, inchangé depuis), 228 nouvelles copies (14/08 → 26/10), rappel des 139 copies annotées en aveugle (août). Objectif fixé par l'expert : *prototype avec correction irréprochable*, fondamentaux révisables.

---

## 1. Les données depuis le 13 août

| | |
|---|---|
| Copies non vides reçues | **228** (43 sessions, 47 cas), 100 % `neuro-v1.3` |
| Mode | parcours 173 / libre 55 |
| Score moyen / médian | 67,5 / **100** |
| Distribution | **0 : 52 (23 %)** · 10-49 : 14 · 50-69 : 30 · 70-89 : 3 · **100 : 129 (57 %)** |
| `LOW_CONFIDENCE` (NER vide) | 18 — tous des saisies-poubelle (« ccvfrzh », « jj », « * ») ou des sondes (« [AUDIT] », injection de prompt) |
| Onglet `feedback` | 1 ligne (sonde) — **aucun retour étudiant** |
| Onglet `concept_review` | 23 votes, tous antérieurs au 13/08 — **le 👍/👎 n'est plus utilisé** |

→ **80 % des notes sont 0 ou 100.** C'était déjà 67 % en août (339/508). La correction ne discrimine pratiquement pas : elle fonctionne en *tout-ou-rien sur le diagnostic principal*.

### 1.1 Les 52 zéros, triés

| Catégorie | n | Verdict |
|---|---|---|
| Saisie vide / test / injection | 20 | zéro légitime |
| Diagnostic principal manqué, description correcte (ex. cas 26 « BAV3 » au lieu de « BAV 2/1 », cas 42 « FA » au lieu de flutter, cas 24 « BAV1 » au lieu de Mobitz 1, cas 55 pas de « péricardite ») | 20 | **0 trop sévère** : l'expert a noté 30-70 ces mêmes profils en août |
| **Cas « ECG normal » (1, 3, 8) – description entièrement juste, 0 pour cause de bug** | 9 | **faux zéro** |
| Diagnostic excludé par un concept golden `absent` affirmé (cas 1 « axe droit », cas 63 « torsade ») | 3 | score sécurité 25 ; adéquation 0 → 0 : la faute est réelle mais le reste du travail n'est pas compté |

**Cas 1 : 11/11 réponses = 0.** Le golden exige « inversion d'électrodes » (seul validant). Toute réponse qui ne le dit pas vaut 0, même quand l'étudiant a vu « aVR positif, D1 inversé » (réponse du 25/09 — il *décrit* l'inversion sans la nommer). Impossible pour un étudiant de distinguer ce cas d'un ECG normal avec les règles actuelles → démotivant et pédagogiquement faux.

### 1.2 Bug confirmé : `ABSENCE_D_ISCHEMIE` tue « ECG normal »

Rejeu local (`scripts/_replay_zeros_2026_10_26.py`) :

```
CAS 3 "rythme sinusal régulier à 50 bpm, normoaxé, pas de BAV, pas de bloc de branche,
       pas de signe d'hypertrophie, pas de signe d'ischémie, bradycardie physiologique"
   score = 0   adequation = 0   securite = 100
   elements_errones = [Incompatible : ABSENCE_D_ISCHEMIE → écarte « ECG normal »]
```

Chaîne : « pas de signe d'ischémie » → NER résout `ABSENCE_D_ISCHEMIE` (statut *present*) → dans `ontology_v2.json`, `ABSENCE_D_ISCHEMIE.parents = ["ISCHEMIQUE"]` → `ECG_NORMAL.excludes_families` contient la famille ischémique → `_check_excludes` (scoring_v3 l.285) trouve un descendant de la famille dans `found_set` → **ECG_NORMAL excluded → 0**.

Autrement dit : *dire qu'il n'y a pas d'ischémie est traité comme dire qu'il y a une ischémie.* Cela touche les cas 3 et 8 (validant unique `ECG_NORMAL`) et tout cas où le golden a « absence d'ischémie » hors golden. Dans le corpus d'août le même bug explique une partie des 6+2 faux zéros cas 3/8 (cf. échantillon aveugle : 2 copies cas 3 et 1 cas 8 notées 70-100 par l'expert, 0 par la machine).

Même famille de défaut structurel (concept négatif rangé sous le concept qu'il nie) :
`ABSENCE_D_ONDE_P ⊂ ONDE_P`, `ABSENCE_D_ALLONGEMENT_DE_L_INTERVALLE_PR ⊂ PR_NORMAL` (OK), `ABSENCE_DE_QRS ⊂ QRS`, `SCA_SANS_ELEVATION_ST ⊂ INFARCTUS_AIGU` (OK). Seul `ABSENCE_D_ISCHEMIE` est actif dans un `excludes_families`, mais la modélisation « polarité dans la hiérarchie » est le vrai problème.

---

## 2. Ce que disait déjà l'échantillon aveugle d'août (139 copies)

- Écarts ≥ 30 points : **40/139 (29 %)**, dont **31 sous-notations machine** et 9 sur-notations.
- `adéquation = 0` alors que l'expert ≥ 50 : **8 cas** (3, 3, 8, 26, 41, 43, 1, 25) → même mécanisme que ci-dessus.
- Aucune copie notée 100 par la machine et ≤ 50 par l'expert : **la machine ne sur-note jamais un 100**. Les sur-notations sont des 44-67 donnés à des copies « diagnostic faux mais description juste » (cas 4, 23, 38, 39, 40).
- Sécurité : expert signale 11 fautes graves, la machine n'en capte que 3 ; elle en lève 8 dont 5 que l'expert ne juge pas graves. → **le volet sécurité est décorrélé du jugement expert** (précision 3/8, rappel 3/11).

Spearman 0,705 est honorable mais obtenu sur une distribution bimodale : la corrélation vient surtout des 100 justes et des zéros-poubelles. **Sur la zone intermédiaire (où se joue la pédagogie), la machine est quasi aléatoire.**

---

## 3. Diagnostic d'architecture — pourquoi c'est structurel

### 3.1 Le golden est un barème à un seul item
51 cas sur 75 ont **un seul validant positif** (20 en ont 2, 4 en ont 3). Les descripteurs (rang B) sont « indicatifs, sans impact ». Donc :

```
score ≈ 100 × [validant trouvé] × (sécurité/100)
```

Tout le reste du raisonnement (fréquence, rythme, axe, PR, QRS, repolarisation…) **ne pèse rien**. C'est la cause première de la bimodalité, pas un défaut de NER. L'expert, lui, note « bradycardie à valider même si pas dans le diag », « tout le reste est très bon », « bien vu le trouble de conduction de haut grade mais pas le BAV3 » : il note une **lecture structurée**, pas un mot-clé.

### 3.2 La hiérarchie encode mal la *distance* entre diagnostics
- cas 26 : « BAV complet » vs attendu « BAV 2/1 » → 0. L'expert donne 30 (« bien vu le haut grade »). Les deux sont frères sous `BAV_DE_HAUT_GRADE` : la proximité n'est pas créditée.
- cas 42 : « FA » vs « flutter typique » → 0 ; « tachycardie jonctionnelle » vs flutter → 0. L'expert distingue ces erreurs (FA sur rythme régulier = raisonnement faux ; TJ = hypothèse défendable).
- cas 24 : « BAV1 » vs « Mobitz 1 » → 0 ; or l'étudiant a écrit « allongement du PR… onde P bloquée ».

Le `match_type` (exact/child/requires/qualifier/support) existe mais l'arbre n'est pas conçu pour mesurer une *erreur partielle* ; il mesure une *spécificité*.

### 3.3 Polarité et statut sont mélangés dans l'ontologie
« Absence de X » comme concept-fils de X (§1.2), « Pas d'anomalie de repolarisation » comme concept, etc. La négation est à la fois dans le NER (statut `absent`), dans l'ontologie (concepts négatifs) et dans le golden (`statut=absent`). Trois mécanismes concurrents → bugs miroir récurrents (cas 57 en juillet, ABSENCE_D_ISCHEMIE aujourd'hui).

### 3.4 La sécurité est une liste d'exceptions
`SAFETY_PENALTY_*` à 75/50/30, golden override, allowed_cooccurrences, cap frère-du-golden… Chaque incident d'août a produit une constante ou une exception. C'est exactement le « cas par cas » que l'expert veut éviter, et les métriques (§2) montrent que ça ne reproduit pas son jugement.

### 3.5 Pas de boucle de retour
Zéro feedback étudiant, zéro vote 👍/👎 depuis août, les 228 copies n'ont jamais été relues. Le système ne peut pas s'améliorer sans signal.

---

## 4. Réponse à la question : entraîner un modèle, ou ontologie + règles ?

### Option A — Modèle entraîné sur des milliers de réponses
- Données disponibles : ~740 copies uniques, **139 annotées** (une seule note globale, un expert). Pour apprendre un score 0-100 par cas avec 75 cas distincts, il faut typiquement 50-100 copies **annotées** par cas, soit 4 000-7 000 annotations expertes → **1 à 2 ans de collecte au rythme actuel (~100 copies/mois)**, et surtout **des centaines d'heures d'annotation** du seul expert disponible.
- Un modèle ne généralise pas à un **76ᵉ cas** sans ré-annoter ; or le projet CNEC promet 15 parcours et de nouveaux cas.
- Opacité : impossible de dire à l'étudiant *pourquoi* 40/100 — incompatible avec l'objectif pédagogique et avec la publication.
- Verdict : **non, pas comme moteur de notation**. Oui comme *détecteur* (voir B3).

### Option B — Ontologie + règles génériques (recommandée, mais refondue)
Le problème n'est pas le choix symbolique, c'est que la **couche de notation est un barème à mot-clé déguisé**. Proposition de refonte en trois couches, chacune générique (aucune règle par cas) :

**B1. Lecture structurée = grille universelle d'axes.**
Toute réponse est projetée sur ~8 axes fixes de la lecture ECG : *fréquence · rythme/origine · conduction AV · conduction intra-ventriculaire · axe · hypertrophies · repolarisation/ischémie · QT* + un axe *synthèse diagnostique*. Pour chaque cas, le golden fournit la **valeur attendue de chaque axe** (dérivable automatiquement du golden actuel + ontologie : ex. cas 26 → fréquence=bradycardie, rythme=sinusal, AV=BAV 2/1, QRS=fins, repol=normale, synthèse=BAV 2/1). Score = somme pondérée des axes ; la synthèse pèse 40-50 %, jamais 100 %. Effet immédiat : plus de bimodalité, le « tout le reste est très bon » de l'expert est compté, le cas 1 devient notable (axes justes, synthèse manquée).

**B2. Distance sémantique entre diagnostics, calculée dans l'ontologie.**
Pour l'axe synthèse, remplacer « trouvé / exclu / manqué » par une distance sur le graphe : même concept = 1 ; frère sous le même parent clinique (BAV complet ↔ BAV 2/1) = 0,5 ; même grande famille (TJ ↔ flutter, tous deux TSV régulières) = 0,25 ; famille opposée ou mécanisme contradictoire avec un fait décrit (FA + « rythme régulier ») = 0 **et** faute de cohérence. C'est générique, auditable, et c'est ce que fait l'expert (« petite erreur sur le type de BAV2 » = 50).

**B3. Sécurité = règles cliniques explicites et peu nombreuses, plus un juge LLM contraint.**
Garder ≤ 10 règles de sécurité *universelles* (ex. « conclure rythme sinusal/ECG normal devant un trouble AV de haut grade », « TV lue comme TSV », « STEMI non vu »), pondérées par la gravité du cas (champ golden `gravite`). Supprimer les constantes ad hoc par type de pénalité. Pour les contradictions intra-réponse, utiliser le LLM **comme juge sur une question fermée** (« l'étudiant affirme-t-il A et B simultanément pour le même tracé ? ») et non comme extracteur libre : c'est là que les copies étudiantes sont utiles — comme **jeu de test** de ces règles, pas comme jeu d'entraînement.

**B4. Corriger la polarité dans l'ontologie.**
Supprimer les concepts « Absence de X » de la hiérarchie de X : la négation est un **statut** porté par le NER (`present/absent/hypothese`), pas un concept. `ABSENCE_D_ISCHEMIE` → `ISCHEMIQUE` statut *absent*. Une seule source de vérité pour la négation, le bug §1.2 disparaît par construction, ainsi que la classe « miroir ».

### Où les données collectées servent vraiment
- **Jeu de régression** : les 740 copies + 139 annotations deviennent le test automatique de chaque modification (aujourd'hui rien n'empêche une régression silencieuse).
- **Annotation par axes** plutôt que note globale : 20 min/cas pour l'expert (valeur attendue par axe), c'est 75 × 20 min = 25 h, faisable, et ça remplace des milliers d'annotations de copies.
- **Fine-tuning éventuel du NER** (pas du scorer) : les 23 votes concept_review + relecture des `concepts_detectes` sur les 740 copies.

---

## 5. Actions proposées (ordre)

1. **Hotfix prod (1 j)** — `ABSENCE_D_ISCHEMIE` : retirer `parents=[ISCHEMIQUE]` (ou ignorer les concepts à polarité négative dans `_check_excludes`). Rejouer cas 1/3/8 des 228 copies ; corriger les scores en Sheet si l'expert le souhaite. Même audit rapide pour `ABSENCE_D_ONDE_P`, `ABSENCE_DE_QRS`.
2. **Figer le jeu de régression (1 j)** — 740 copies + 139 annotations + 52 zéros classés ci-dessus → script `pytest` qui échoue si Spearman < 0,70 ou si un « faux zéro » connu réapparaît.
3. **Décision expert** sur la grille d'axes (B1) : liste des axes et pondération synthèse/description. C'est la seule décision de fond ; tout le reste en découle.
4. **Génération automatique du golden par axes** depuis `cases_golden.json` + ontologie, puis **validation expert 75 cas** (format tableau, ~25 h au total, découpable).
5. **Implémentation B1+B2+B4 sur `p4-dev`** (branche séparée, main inchangé), comparaison sur le jeu de régression, échantillon aveugle n°2 (100 copies dont les 52 zéros récents).
6. **B3 sécurité** après B1/B2, car la moitié des « fautes graves » actuelles disparaissent quand la synthèse ne vaut plus 100 % du score.
7. **Réactiver la boucle de retour** : rendre le 👍/👎 et le feedback visibles (ils ne sont pas utilisés depuis août — vérifier qu'ils sont bien affichés dans l'app).

---

## 6. Fichiers de cette session
- `scripts/_audit_new_responses_2026_10_26.py` — stats + liste des zéros depuis une date.
- `scripts/_replay_zeros_2026_10_26.py` — rejeu local détaillé de 15 copies (sortie `_replay_zeros_out.txt`, `_replay_zeros_2026_10_26.json`).
- Dumps non committés (données étudiantes) : `_sheet_reponses.json` (823), `_sheet_feedback.json`, `_sheet_concept_review.json`.
