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

## Synthèse : ordre d'attaque proposé

| Chantier | Effort | Impact | Dépendances |
|---|---|---|---|
| **P4.3-contradiction (chal_02)** : appliquer les `excludes` de l'ontologie entre concepts extraits d'une même réponse | Faible-moyen (mécanisme existant à étendre) | Élevé (trou de sécurité réel, score 100% sur réponse incohérente) | Vérifier que l'ontologie déclare les excludes pertinents (FA↔régulier, etc.) |
| **P4.1** : séparer adéquation/sécurité en 2 dimensions visibles | Moyen (refactor du rapport + UI) | Élevé (lisibilité pédagogique, prérequis pour P4.2) | Bénéficie du travail P4.3-contradiction (la sécurité a besoin des contradictions comme entrée) |
| **P4.2** : calibration des crédits vs jugements humains | Élevé (protocole + annotation + analyse) | Moyen-élevé (rigueur scientifique) | Mieux APRÈS P4.1 (calibrer sur la dimension adéquation isolée est plus propre) |
| P4.3-double-négation (chal_04) | Moyen (NER) | Faible (fréquence réelle basse) | Aucune — peut rester en backlog |

**Recommandation** : commencer par **P4.3-contradiction** (détection des
`excludes` intra-réponse), car :
1. c'est le trou de sécurité le plus flagrant démontré par le challenge
   set (chal_02 : 100% sur une réponse cliniquement incohérente) ;
2. le mécanisme `excludes` existe déjà dans l'ontologie et dans
   `scoring_v3._check_excludes` — c'est une extension, pas une création ;
3. son résultat (liste des contradictions internes) est exactement
   l'entrée dont le futur score de sécurité (P4.1) aura besoin — on
   construit dans le bon ordre.
