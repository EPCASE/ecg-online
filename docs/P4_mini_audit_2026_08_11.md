# P4 — Mini-audit préalable du scoring (2026-08-11)

État des lieux du moteur de scoring en production avant d'ouvrir le
chantier P4 (refonte du scoring), sous l'angle des 3 sous-chantiers de la
roadmap (`audit_doc/roadmap_scientifique_2026.md` §P4).

Fichiers audités :
- `rag_pipeline/scoring_v3.py` (moteur de scoring ontologique, production)
- `rag_pipeline/scoring_thresholds.py` (registre central des seuils)
- `ecg-online/app/neuro_grader.py` (orchestration, caps d'exclusion)
- `rag_pipeline/candidate_report.py` (pipeline complet + rapport)

---

## P4.1 — Séparer adéquation et sécurité : ÉTAT ACTUEL

**Constat : il n'existe qu'UN seul score final, la "sécurité" est
mélangée dedans par écrêtage (`min`).**

Mécanisme actuel (`neuro_grader.py`, lignes ~321-327) :
- score de base = couverture des concepts golden (adéquation pure,
  `score_final_pct` de `candidate_report`) ;
- si l'étudiant affirme un concept que le golden exige d'écarter
  (exclusion violée) : le score est **écrêté** à
  `EXCLUSION_RANG_A_SCORE_CAP = 25` (faute grave) ou
  `EXCLUSION_RANG_B_SCORE_CAP = 70` (faute mineure).

Conséquences :
- l'information "pourquoi la note est basse" est perdue dans le nombre
  final : un 25/100 par écrêtage rang A est indistinguable d'un 25/100
  par couverture très faible ;
- les autres composantes de sécurité listées dans la roadmap (concepts
  faux hors exclusions, contradictions internes — cf. gap `chal_02`,
  erreurs graves) ne sont **pas mesurées du tout** ;
- le gap `chal_02` (P3.3) illustre le trou : "fibrillation atriale avec
  rythme parfaitement régulier" score 100% — aucune détection de
  contradiction diagnostic/descripteurs n'existe.

**Écart à la cible P4.1** : il faut produire deux dimensions distinctes
(score d'adéquation / score de sécurité) visibles séparément. La
mécanique d'écrêtage actuelle est un embryon de score de sécurité (binaire
et destructif) à transformer en dimension explicite.

---

## P4.2 — Calibrer les crédits ontologiques : ÉTAT ACTUEL

**Constat : bonne nouvelle structurelle — les seuils sont déjà
centralisés (`scoring_thresholds.py`, Phase 0.3 de juillet 2026), mais
aucune valeur n'a jamais été calibrée contre des jugements humains.**

Valeurs actuelles et leur origine :

| Crédit | Valeur | Origine |
|---|---|---|
| Concept exact trouvé | 1.0 | définition |
| Enfant plus spécifique trouvé | 1.0 (court-circuit) | choix expert, jamais calibré |
| Parent proche trouvé | 2/3 | choix initial "raisonnable", jamais calibré |
| Parent lointain trouvé | 1/3 | idem |
| Qualifier trouvé | 2/3 (`SUB_REQUIRE_QUALIFIER_CREDIT`) | idem |
| Support trouvé | 1/3 (`SUB_REQUIRE_SUPPORT_CREDIT`) | idem |
| `requires` partiels | proportionnel (n satisfaits / n total, récursif) | définition |
| `implies` (antécédent clinique) | **0.0 — GELÉ** (Option A, découplage) | décision de prudence, en attente d'un barème multi-niveaux |
| `negation_of` (pôle positif nié) | **0.0 — GELÉ** (Option A) | idem |
| Cap exclusion rang A | 25 | choix expert, jamais calibré |
| Cap exclusion rang B | 70 | idem |
| Seuil "validant trouvé" (UI) | 60% | correctif d'affichage (cas 2), jamais calibré |

Matériau de calibration DISPONIBLE sans rien créer :
- `extraction_golden.json` : 100 réponses réelles annotées par l'expert ;
- les notes réelles attribuées historiquement (sessions, corrections
  envoyées) si récupérables ;
- le challenge set P3.3 (16 items avec comportement attendu documenté).

**Écart à la cible P4.2** : la comparaison systématique
crédits-vs-jugement-humain n'a jamais été faite. C'est le sous-chantier
le plus "scientifique" (nécessite un protocole : quelles réponses, quel
juge humain, quelle métrique d'accord).

---

## P4.3 — Restreindre les conversions de négation : ÉTAT ACTUEL

**Constat : le risque principal visé par la roadmap est DÉJÀ neutralisé
(NEGATION_CREDIT = 0.0 gelé), mais deux problèmes adjacents restent
ouverts.**

1. La crainte initiale de la roadmap ("pas de trouble de repolarisation"
   valide à lui seul un ECG normal) ne peut plus se produire au niveau du
   CRÉDIT barème : `NEGATION_CREDIT = 0.0` depuis l'Option A. La lecture
   sémantique de la négation par le NER reste active (statut `absent`
   correctement extrait — vérifié dans le challenge set, ex. chal_03 où
   "pas de flutter typique visible" est bien lu comme absent).
2. **Gap ouvert — double négation (chal_04)** : "il n'est pas exclu
   qu'il n'y ait pas d'anomalie" fait chuter le score à 0% (concept
   ECG_NORMAL non extrait). Fréquence réelle faible, priorité basse.
3. **Gap ouvert — contradiction diagnostic/descripteurs (chal_02)** :
   pas une conversion de négation à strictement parler, mais rattaché à
   P4.3 dans la roadmap ("les contradictions éventuelles"). Aucun
   mécanisme ne vérifie la cohérence interne d'une réponse (FA affirmée +
   rythme régulier décrit = créditée 100%). L'ontologie possède pourtant
   déjà un mécanisme `excludes` (utilisé par `_check_excludes` pour les
   concepts golden absents) qui pourrait servir de base : la relation
   "FIBRILLATION_ATRIALE excludes RYTHME_REGULIER" (si déclarée) rendrait
   la contradiction détectable SANS nouveau mécanisme, juste en
   appliquant les `excludes` AUSSI entre concepts extraits de la réponse
   (aujourd'hui ils ne sont vérifiés qu'entre réponse et golden).

### Vérification faite (2026-08-11) — couverture des `excludes` dans l'ontologie

- **39/358 concepts** déclarent au moins une relation `excludes` (ex :
  `BAV_COMPLET → PR_NORMAL`, `BLOC_DE_BRANCHE → QRS_FINS`,
  `BLOC_DE_BRANCHE_DROIT → BLOC_DE_BRANCHE_GAUCHE`).
- **MAIS la relation critique du chal_02 n'existe pas** :
  `FIBRILLATION_ATRIALE` ne déclare aucun excludes (notamment pas
  `RYTHME_REGULIER`), et réciproquement. Le mécanisme est donc là, mais
  sa **couverture clinique est incomplète** pour la détection de
  contradictions intra-réponse.
- Conséquence pour le plan : le chantier P4.3-contradiction a DEUX volets
  distincts, à traiter dans cet ordre :
  1. **Volet moteur** (code) : appliquer les `excludes` entre concepts
     extraits d'une même réponse (aujourd'hui vérifiés uniquement entre
     réponse et golden `absent`) ;
  2. **Volet ontologie** (données, validation expert requise) : enrichir
     les `excludes` des diagnostics rythmiques majeurs (FA↔régularité,
     etc.) — chaque ajout est une décision CLINIQUE (attention aux cas
     limites réels, ex. FA + BAV complet = rythme d'échappement régulier,
     donc "FA excludes RYTHME_REGULIER" est cliniquement FAUX dans
     l'absolu — il faudra probablement une modélisation plus fine, ex.
     exclusion "par défaut sauf mention d'un mécanisme d'échappement",
     ou une liste courte validée cas par cas par l'expert).

---

## DÉCISION D'ARCHITECTURE (2026-08-11) — Détection de contradictions

Discussion expert/agent suite au mini-audit ci-dessus. Cette décision
**amende la recommandation initiale** (qui proposait d'attaquer
P4.3-contradiction en premier par simple extension des `excludes`).

### Le problème de fond soulevé par l'expert

La relation `excludes` de l'ontologie mélange aujourd'hui **trois
catégories** sémantiquement différentes :

1. **Contradiction sémantique absolue** : A et B ne peuvent JAMAIS être
   vrais ensemble (typiquement concept / négation). Légitime en
   ontologie, comportement "hard".
2. **Incompatibilité clinique par défaut** : A et B sont normalement
   incompatibles, mais des situations physiopathologiques réelles
   autorisent leur coexistence. Exemples :
   - FA + rythme régulier → possible si BAV complet avec échappement ;
   - QRS fins + bloc de branche → possible en cas d'aberration de
     conduction, BBB intermittent, alternance de morphologies,
     extrasystoles avec aberration (donc `BLOC_DE_BRANCHE excludes
     QRS_FINS`, déclaré actuellement, est FAUX dans l'absolu).
3. **Incompatibilité propre à un tracé** : sur CET ECG, A est
   incompatible avec ce qu'on observe. Ressort du golden (mécanisme
   `statut: absent` / `role: exclusion` existant, caps 25/70).

La sémantique correcte de la catégorie 2 exigerait en toute rigueur une
notion de **portée** ("A exclut B pour le même événement QRS au même
moment") — structure absente du pipeline (sac plat de concepts), et dont
l'introduction serait une refonte disproportionnée.

### Options évaluées

| Option | Verdict |
|---|---|
| A. Enrichir les `excludes` globaux de l'ontologie | ❌ Produit des faux positifs sur les cas cliniquement riches (FA + BAV complet, aberration de conduction) |
| B. Refonte avec raisonnement à portée (événements QRS) | ❌ Disproportionné — chal_02 est synthétique, jamais observé chez un étudiant réel. Limite architecturale NOTÉE, à revisiter seulement si des cas réels le justifient |
| C. Tout basculer dans le golden par cas | ⚠️ Fonctionne mais perd la connaissance générique réutilisable |
| **D. Compromis retenu : conflits par défaut + override automatique par le golden** | ✅ |

### Architecture retenue (Option D)

**Quatre niveaux de contraintes** :

| Niveau | Exemple | Où ? | Comportement |
|---|---|---|---|
| Contradiction logique | A / NEGATION_A | Ontologie (`excludes` strict ou `negation_of`) | hard, `severity: error` |
| Incompatibilité clinique par défaut | FA / RYTHME_REGULIER | Ontologie (`conflicts_by_default`) | conditionnelle, `severity: warning` |
| Override contextuel | FA + BAV complet dans le golden | Golden/contexte du cas | lève la contrainte |
| Interdiction spécifique du cas | "ne pas conclure à sinus" | Golden (`absent`/`exclusion`) | hard pour CE cas (caps 25/70) |

**Règle-clé (override automatique par le golden)** — purement générique,
zéro logique cardiologique dans Python :

> Si les deux concepts d'une relation de conflit sont validés par le
> golden du cas, la relation ne doit JAMAIS produire de contradiction
> dans ce cas.

```text
if response_contains(A, B):
    if golden_accepts(A, B):            # coexistence validée par le cas
        no_conflict()
    elif case_override_allows(A, B):    # allowed_cooccurrences (optionnel)
        no_conflict()
    else:
        apply_constraint(A, B)          # selon severity
```

Le moteur dispose de deux ensembles d'informations (contexte du cas /
golden + réponse de l'étudiant) : il décide si une incompatibilité est
APPLICABLE à partir du contexte, puis seulement examine la réponse.
L'étudiant n'a pas à mentionner l'exception lui-même.

Flux cible :

```text
             ONTOLOGIE
                 │
    ┌────────────┴─────────────┐
contradictions absolues  conflits par défaut
    └────────────┬─────────────┘
                 ▼
         CONTEXTE DU CAS
   (golden / allowed_cooccurrences)
                 ▼
        CONTRAINTES ACTIVES
                 ▼
       RÉPONSE DE L'ÉTUDIANT
                 ▼
             SCORING
```

**Implémentation incrémentale (V1 pragmatique)** :
1. Détection de A/B normalement incompatibles (relation ontologie) ;
2. Si le golden accepte A ET B → conflit neutralisé automatiquement ;
3. Sinon appliquer la règle (selon sévérité) ;
4. Champ léger `allowed_cooccurrences: [[QRS_FINS, BLOC_DE_BRANCHE]]`
   dans le golden, ajouté SEULEMENT quand un cas réel le réclame (couvre
   le cas où les deux concepts sont légitimes mais où l'un n'a pas
   vocation à être exigé dans la correction) ;
5. Le champ `exceptions:` dans l'ontologie n'est PAS nécessaire pour
   l'instant (l'override golden le rend redondant).

### Conséquence : audit obligatoire des 39 `excludes` existants

Chaque relation doit être reclassée avec la question-test :

> **Cette relation reste-t-elle vraie quelle que soit la situation
> clinique représentable sur un ECG ?**

- Oui → `excludes` (hard, `severity: error`) ;
- Non, mais utile pédagogiquement → `conflicts_by_default`
  (`severity: warning`, override golden possible) ;
- Vraie seulement pour certains ECG → sort de l'ontologie, passe dans le
  golden des cas concernés.

Résultat attendu : très peu de vrais `excludes` restants (essentiellement
les paires concept/négation) — et c'est le reflet correct de la clinique.

---

## Synthèse : ordre d'attaque proposé

| Chantier | Effort | Impact | Dépendances |
|---|---|---|---|
| **P4.3-contradiction (chal_02)** : appliquer les `excludes` de l'ontologie entre concepts extraits d'une même réponse | Faible-moyen (mécanisme existant à étendre) | Élevé (trou de sécurité réel, score 100% sur réponse incohérente) | Vérifier que l'ontologie déclare les excludes pertinents (FA↔régulier, etc.) |
| **P4.1** : séparer adéquation/sécurité en 2 dimensions visibles | Moyen (refactor du rapport + UI) | Élevé (lisibilité pédagogique, prérequis pour P4.2) | Bénéficie du travail P4.3-contradiction (la sécurité a besoin des contradictions comme entrée) |
| **P4.2** : calibration des crédits vs jugements humains | Élevé (protocole + annotation + analyse) | Moyen-élevé (rigueur scientifique) | Mieux APRÈS P4.1 (calibrer sur la dimension adéquation isolée est plus propre) |
| P4.3-double-négation (chal_04) | Moyen (NER) | Faible (fréquence réelle basse) | Aucune — peut rester en backlog |

**Recommandation (AMENDÉE 2026-08-11 suite à la décision d'architecture
ci-dessus)** : P4.3-contradiction est requalifié — ce n'est plus une
simple extension des `excludes` mais l'implémentation de l'Option D :

1. **P4.3a — Audit des 39 `excludes`** (expert requis) : reclasser chaque
   relation en `excludes` strict / `conflicts_by_default` / golden par cas
   (question-test ci-dessus) ;
2. **P4.3b — Moteur** : implémenter la vérification des conflits
   intra-réponse AVEC override automatique par le golden
   (`golden_accepts(A, B) → no_conflict`) et sévérités error/warning ;
3. **P4.1** : séparer adéquation/sécurité — le résultat de P4.3b (liste
   des contradictions actives) est exactement l'entrée de la dimension
   sécurité ;
4. **P4.2** : calibration après P4.1.

L'ordre P4.3a/P4.3b vs P4.1 peut s'inverser si l'audit expert des 39
relations n'est pas disponible rapidement : P4.1 n'en dépend pas
structurellement (la dimension sécurité peut naître avec les seules
exclusions golden par cas, et intégrer les conflits ontologiques ensuite).
