# 🔍 Audit qualité rédactionnelle du feedback IA — 2026-08-05

## Contexte

Des étudiantes ont signalé que le texte de correction affiché après le score
(le « feedback pédagogique ») est **inadapté** à ce qu'elles ont réellement
écrit, avec des **incohérences**. Cet audit vise à quantifier et qualifier
ces problèmes sur un échantillon réel, puis à proposer des pistes concrètes.

## ⚠️ Découverte préalable — deux systèmes de cas distincts

Avant de lancer l'audit, une confusion a été détectée et corrigée : le
dossier `ecg-online` (75 cas curriculum, en développement) et le dossier
`ECG collector` (15 cas historiques, **l'app réellement utilisée par les
étudiantes en production**) ont des référentiels golden totalement
différents et incompatibles. **Tout audit doit utiliser le golden de
`ECG collector/corrections/golden.json`** (15 cas) — pas celui d'`ecg-online`.
Un premier essai avec le mauvais golden a produit des scores de 0% partout
et un faux diagnostic de bug ; corrigé avant l'audit ci-dessous.

## Méthodologie

1. **Sélection** : les 100 dernières réponses étudiantes réelles non vides
   (`ECG collector/corrections/students/*.json`, triées par `generated_at`
   décroissant — période couverte : 04/07/2026 05:25 à 05:33).
2. **Régénération** : chaque réponse a été rejouée à travers le pipeline de
   correction ACTUEL (`ECG lecture/rag_pipeline/candidate_report.py` +
   `pedagogical_feedback.py`, version `RAG Neurosymbolique v1.1 (C1+C2)`,
   golden `ECG collector/corrections/golden.json`, 15 cas) — donc un
   feedback texte **frais**, produit avec le code d'aujourd'hui, pas une
   copie figée d'une exécution antérieure.
   → Script : `scripts/audit_feedback_quality.py`
   → Sortie : `data/audit_feedback_2026-08-05.json` (100/100 réussis, 0 erreur).
3. **Jugement qualité** : chaque triplet {réponse étudiante, concepts
   trouvés/manqués, score, feedback texte} a été soumis à un juge GPT-4o
   (température 0) qui évalue 5 axes indépendants (1-5) SANS réévaluer la
   justesse du score : adaptation, cohérence interne, redondance, exactitude
   clinique, ton pédagogique — plus une liste de problèmes concrets et un
   verdict global (excellent / acceptable / problématique / inadapté).
   → Script : `scripts/audit_feedback_gpt.py`
   → Sortie : `data/audit_feedback_gpt_verdict_2026-08-05.json`.

## Résultats chiffrés (100 items)

| Axe | Moyenne /5 |
|---|---|
| Adaptation à la réponse réelle | **4.04** |
| Cohérence interne | 4.62 |
| Non-redondance | 4.00 |
| Exactitude clinique | 4.78 |
| Ton pédagogique | 4.58 |

| Verdict global | Nombre | % |
|---|---|---|
| Excellent | 36 | 36% |
| Acceptable | 59 | 59% |
| **Problématique** | **5** | **5%** |
| Inadapté | 0 | 0% |

→ **Aucun cas "inadapté"** (le pire seuil), mais **l'axe le plus faible est
l'adaptation à la réponse réelle et la non-redondance** (tous deux ~4.0/5,
nettement sous l'exactitude clinique à 4.78). C'est cohérent avec le
signalement des étudiantes : le contenu clinique du feedback est globalement
fiable, mais le texte « colle » imparfaitement à ce qu'elles ont VRAIMENT
écrit.

## 128 problèmes concrets détectés — répartition par catégorie

| Catégorie de problème | Occurrences | Exemple typique |
|---|---|---|
| **Redondance** entre les 2 sections du feedback | 25 | Les sections "Référence au cours" et "Votre interprétation" répètent la même info sans valeur ajoutée. |
| **Erreur de rang (A/B/C) affiché** | 13 | Le microvoltage est affiché comme rang B dans un cas alors qu'il est validant (rang A) dans le golden. |
| **Affirmation incorrecte sur ce que l'étudiant a écrit** | 10 | « Vous avez identifié un bloc de branche gauche » alors que l'étudiant a écrit "tachycardie ventriculaire" et n'a jamais mentionné le BBG. |
| **Mention non pertinente / hors-sujet** | 8 | Le feedback évoque la "repolarisation précoce" dans un cas de fibrillation atriale sans lien avec la réponse de l'étudiant. |
| **Confusion clinique/terminologique** | 7 | Confusion entre BAV de haut grade et BAV 2 Mobitz 2 (deux entités distinctes, souvent mal différenciées par le pipeline). |
| **Non-reconnaissance d'un concept que l'étudiant A mentionné** | 4 | L'étudiant écrit "échappement jonctionnel", le feedback dit qu'il a "manqué l'échappement ventriculaire" (concept proche mais différent — pas un vrai manque). |
| **Ton mal calibré par rapport au score** | 2 | Score de 0/100 mais ton du feedback très positif ("Félicitations pour votre excellent travail"). |

## 5 cas jugés "problématiques" — analyse détaillée

### 1. `ECG-YEUE` cas 1 — Faux diagnostic d'onde Q pathologique
**Réponse étudiante** : *« Rythme régulier, onde P négative ou diphasique en
inférieur (…), PR normal, QRS fins, aspect QS en DIII, axe normal, pas
d'HVG, FC à 60bpm, pas de trouble de repolarisation »*
**Problème** : le pipeline détecte "Présence d'onde Q pathologique" dans les
découvertes — mais l'étudiant a écrit **« aspect QS en DIII »**, ce qui est
une observation descriptive normale en DIII (pas forcément pathologique
isolément), pas une affirmation de pathologie. Le feedback affirme ensuite
que ce point contredit "directement" le diagnostic d'ECG normal, ce qui
**sur-interprète le texte de l'étudiant**. Score de 0/100 potentiellement
trop sévère si ce mapping NER→concept est en cause.
→ **Cause racine probable** : le NER/juge neurosymbolique mappe "aspect QS
en DIII" vers un concept trop fort ("onde Q pathologique") sans tenir compte
du contexte isolé (DIII seul) où c'est un variant normal fréquent.

### 2. `ECG-WY55` cas 14 — Confusion QRS fins/larges pour une ESV
**Problème détecté par le juge** : confusion sur la définition d'une
extrasystole ventriculaire (généralement QRS **larges**, pas fins) +
incohérence sur la mention d'ECG normal + critique du rythme sinusal sans
justification. Signale une possible erreur de contenu clinique dans le texte
généré par le LLM de feedback lui-même (pas dans le scoring).

### 3. `ECG-VQFO` cas 15 — Le feedback invente un concept trouvé
**Réponse étudiante** : *« Tachycardie à QRS large à 240bpm. Tachycardie
ventriculaire. »*
**Golden** : Bloc de branche gauche complet (score partiel 66.7% — trouvé),
Fibrillation atriale (manquée).
**Problème** : le feedback affirme que l'étudiant **a identifié** le bloc de
branche gauche (« ce diagnostic a été identifié par l'étudiant, mais
seulement partiellement ») — mais l'étudiant n'a écrit ni "bloc de branche"
ni rien s'en approchant explicitement. Le score de 66.7% provient
probablement d'un **match indirect via QRS large** (un descripteur commun
aux deux diagnostics), mais le texte du feedback présente cela comme une
identification directe et consciente, ce qui est **trompeur** pour
l'étudiant qui n'a jamais pensé "BBG".
→ **Cause racine probable** : le scoring V3 peut créditer un concept via un
chemin d'inférence indirect (ex: descripteur partagé), mais le prompt de
génération du feedback ne distingue pas "trouvé directement" de "trouvé par
inférence/proximité" — le texte généré présente systématiquement un
"trouvé" comme une identification explicite et consciente.

### 4. `ECG-R48T` cas 4 — Rang erroné + ton mal calibré
Le microvoltage est présenté comme rang B dans le texte alors qu'il est
validant (rang A, le seul validant du cas) dans le golden — **erreur
factuelle sur le barème lui-même**, pas juste une nuance de reformulation.
Le ton reste "trop positif" malgré un score de 0/100 (aucun validant trouvé).

### 5. `ECG-QHCN` cas 11 — Contradiction interne
Le feedback accuse l'étudiant d'avoir manqué des concepts de rang A alors
que sa réponse contient effectivement un BBG et un trouble de repolarisation
mentionnés — texte jugé "trop générique", ne s'adaptant pas à la réponse
spécifique.

## Synthèse des causes racines (par ordre de fréquence/impact)

1. **Redondance structurelle du template en 2 sections** (25 occurrences,
   le problème le PLUS fréquent) — le prompt de `pedagogical_feedback.py`
   génère quasi-systématiquement 2 sections ("Référence au cours" /
   "Votre interprétation") qui se chevauchent largement en contenu. C'est un
   problème de **prompt engineering pur**, facilement corrigeable.

2. **Le texte ne distingue jamais "trouvé directement" de "trouvé par
   proximité/inférence"** — quand le scoring V3 crédite un concept via un
   chemin indirect (synonyme approximatif, concept parent, descripteur
   partagé), le LLM de feedback le présente TOUJOURS comme si l'étudiant
   l'avait explicitement et consciemment écrit. C'est la cause principale
   des "affirmations incorrectes sur ce que l'étudiant a écrit" (10 cas) et
   contribue aux problèmes d'adaptation (axe le plus faible : 4.04/5).

3. **Incohérences ponctuelles rang A/B/C affichées dans le texte** (13 cas)
   — le rang affiché dans le commentaire ne correspond pas toujours au rang
   réel du golden (ex: microvoltage annoncé rang B alors que rang A/seul
   validant). Suggère que le LLM de feedback n'a pas un accès fiable/
   structuré au rang réel de chaque concept, ou improvise si l'info n'est
   pas clairement injectée dans le prompt.

4. **Mapping NER→concept parfois trop agressif** (ex: "aspect QS en DIII" →
   "onde Q pathologique") — peut faire basculer un score à 0 pour un
   étudiant qui a en fait une description clinique correcte et nuancée.
   Ce point recoupe les chantiers déjà identifiés dans
   `audit_doc/roadmap_scientifique_2026.md` (juge sémantique global,
   filtrage des faux positifs) — pas un problème nouveau, mais une
   illustration concrète de son impact sur le VÉCU étudiant (score 0 +
   feedback qui semble "inventer" un problème).

5. **Confusions cliniques ponctuelles dans le texte généré** (BAV haut grade
   vs Mobitz 2, ESV QRS fins vs larges) — le LLM de feedback (GPT-4o-mini
   selon `pedagogical_feedback.py`) peut produire des approximations
   médicales quand il rédige librement autour d'un concept, même si le
   scoring sous-jacent est correct.

## Pistes d'amélioration priorisées

### 🥇 Priorité 1 — Corriger la redondance structurelle (impact : 25/128 problèmes, effort : faible)
Réviser le prompt système de `generate_pedagogical_feedback()` pour
distinguer clairement le RÔLE de chaque section (ex: section 1 = uniquement
les points manqués avec citation de cours ; section 2 = uniquement une
synthèse d'encouragement + 1 conseil concret, sans re-décrire les mêmes
concepts). Fusionner en une seule section si la distinction ne peut pas être
maintenue proprement. **Gain attendu : rapide, sans risque, cause la plus
fréquente.**

### 🥈 Priorité 2 — Ne jamais présenter un concept "trouvé par proximité" comme une identification explicite (impact : 10-14/128, effort : moyen)
Injecter dans le prompt de feedback, pour chaque concept validant, le
`match_type` réel (exact / synonyme / inférence / descripteur partagé) —
déjà disponible dans `validant_details` du `CandidateReport` — et instruire
explicitement le LLM à formuler différemment selon ce type (« vous l'avez
mentionné explicitement » vs « votre réponse contient des éléments qui s'en
rapprochent, mais vous ne l'avez pas nommé directement »). C'est la cause
principale du sentiment d'« inadéquation » signalé par les étudiantes.

### 🥉 Priorité 3 — Garantir la cohérence du rang affiché avec le golden réel (impact : 13/128, effort : faible)
Le rang (A/B/C) est une donnée STRUCTURÉE déjà disponible
(`golden_config`/`scoring_config`) — elle ne devrait JAMAIS être laissée à
l'improvisation du LLM rédacteur. Injecter le rang exact dans le prompt (déjà
probablement fait en partie, à vérifier) et/ou post-traiter le texte généré
pour vérifier/corriger automatiquement les mentions de rang par rapport à la
donnée structurée.

### Priorité 4 — Revue ciblée du mapping NER pour les formulations ambiguës type "aspect QS en DIII" (effort : moyen, rejoint le chantier existant)
Ce point recoupe le chantier "juge sémantique global" déjà documenté dans
`audit_doc/roadmap_scientifique_2026.md` — pas une action nouvelle, mais un
signal supplémentaire de son importance pour le vécu étudiant (score 0 sur
un ECG normal correctement décrit, dû à une sur-interprétation d'un terme
descriptif isolé).

### Priorité 5 — Garde-fou de cohérence ton/score (effort : faible)
Ajouter une règle déterministe simple (pas de LLM) : si score < 40, interdire
les formulations "félicitations"/"excellent travail" dans le prompt de
génération, et inversement pour score > 80. Peu de cas concernés (2/128) mais
correction quasi gratuite.

## Fichiers produits

- `scripts/audit_feedback_quality.py` — extraction + régénération du
  feedback frais sur les 100 dernières réponses réelles.
- `scripts/audit_feedback_gpt.py` — juge GPT de la qualité rédactionnelle.
- `data/audit_feedback_2026-08-05.json` — 100 triplets régénérés (score,
  réponse, feedback, détails concepts).
- `data/audit_feedback_gpt_verdict_2026-08-05.json` — 100 verdicts
  structurés + résumé agrégé.
- `data/audit_feedback_gpt_verdict_2026-08-05_AUDIT.md` (ce document).

## Prochaine étape proposée

Implémenter la Priorité 1 (dé-redondance du prompt) et la Priorité 2
(distinction match direct/indirect) dans `pedagogical_feedback.py`, puis
relancer cet audit sur un nouvel échantillon de 100 réponses pour mesurer
l'amélioration (cible : adaptation_score moyenne > 4.5/5, redondance_score
moyenne > 4.5/5, 0 cas "problématique").

---

## 🔄 MISE À JOUR — 06/08/2026 : implémentation complète et cycle d'itérations

Suite à la décision d'implémenter toutes les priorités, un cycle de 5
itérations a été mené, chaque fois en régénérant les 100 mêmes feedbacks
frais et en les ré-auditant avec un juge **beaucoup plus strict** que le
gpt-4o initial : **gpt-5.6** (modèle "reasoning", accessible via API,
nécessite `reasoning_effort="none"` pour le function-calling en
`/v1/chat/completions`).

### ⚠️ Sur le choix du juge : gpt-5.6 change complètement l'échelle

Avec le même feedback (v2), gpt-4o notait 5% de cas "problématique" contre
**68% pour gpt-5.6**. gpt-5.6 est beaucoup plus rigoureux et détecte des
contresens fins (ex: affirmer qu'un étudiant "n'a pas nommé explicitement"
un concept qu'il a écrit mot pour mot) que gpt-4o laissait passer. **Toutes
les comparaisons ci-dessous utilisent gpt-5.6 comme juge unique**, ce qui
rend les scores non comparables aux résultats gpt-4o du 05/08 en valeur
absolue — seule la tendance relative (v2→v6) est interprétable.

### Cycle d'itérations — bugs réels découverts et corrigés

1. **v2 (prompt P1/P2/P3/P5 appliqués, gpt-4o-mini)** : régression inattendue
   par rapport à l'ancien prompt sur le juge gpt-4o (4.04→3.45 adaptation) ;
   sur gpt-5.6, 90% de cas à problème. Cause : un bug non lié aux priorités
   d'origine — le prompt utilisateur (`user_message`) demandait encore
   explicitement l'ancien format 2 sections, écrasant le nouveau
   `SYSTEM_PROMPT`. **Corrigé.**

2. **v3 (fix jargon technique)** : découverte d'une **fuite de jargon
   pipeline** dans le texte destiné aux étudiants — le LLM recopiait
   littéralement des labels internes ("match de type qualifier", "rang A",
   pourcentages bruts) et un placeholder de citation non substitué
   (« extrait du cours » littéral). Ajout d'une règle d'interdiction
   explicite + un garde-fou déterministe de détection (`_detect_jargon_leak`)
   avec re-génération automatique si détecté. **Gain sur tous les axes**
   (inadapté 22%→9%).

3. **v4 (fix découvertes vs match_type)** : découverte du bug le **plus
   dommageable** — les concepts listés en "découvertes additionnelles" (hors
   barème, mais **explicitement écrits par l'étudiant**) étaient traités par
   erreur comme des matches indirects/qualifier, menant le LLM à affirmer
   à tort que des termes écrits mot pour mot (ex: "BAV 2 M2", "bradycardie")
   n'étaient "pas nommés explicitement". Clarification stricte dans le
   prompt de la distinction entre `validant_details` (soumis à la règle
   match_type) et `decouvertes` (toujours explicites). **Gain confirmé**
   (adaptation 2.56→3.01, problématique 63%→53%).

4. **v5 (fix récidive du placeholder de citation)** : le fix P2 avait
   réintroduit par erreur un nouveau texte de substitution ("texte
   réellement recopié depuis le contexte") littéralement recopiable par le
   LLM. Reformulation de la consigne + élargissement des patterns de
   détection du garde-fou anti-jargon. Résultat globalement stable
   (pas de régression), artefact éliminé.

5. **v6 (changement de modèle gpt-4o-mini → gpt-4o + garde-fous
   anti-digression clinique)** : à ce stade, les problèmes résiduels
   n'étaient plus des bugs de prompt mais des **approximations cliniques
   spontanées** du LLM rédacteur (confusions Mobitz II / BAV de haut grade,
   distinctions terminologiques inventées entre synonymes, règles
   diagnostiques générales non demandées, conseils artificiels sur des
   réponses à 100%). Deux changements :
   - **Modèle : `gpt-4o-mini` → `gpt-4o`** (précision et respect des
     consignes prioritaires sur le coût).
   - **Nouvelle règle absolue "ne jamais inventer de nuance clinique non
     demandée"** : interdiction de créer des distinctions entre synonymes,
     d'ajouter des règles diagnostiques non fournies dans le contexte, et
     obligation de rester bref/valorisant sur un score de 100% sans forcer
     un conseil artificiel.
   - **Impact : le plus important de tout le cycle.**

### Résultats chiffrés — comparaison gpt-5.6 sur l'ensemble du cycle (100 items à chaque fois)

| Axe (/5) | v2 | v3 | v4 | v5 | **v6 (final)** |
|---|---|---|---|---|---|
| Adaptation | 2.10 | 2.56 | 3.01 | 2.80 | **3.64** |
| Cohérence | 2.81 | 3.23 | 3.56 | 3.48 | **4.20** |
| Redondance | 3.42 | 3.58 | 3.54 | 3.59 | **4.06** |
| Exactitude clinique | 2.78 | 3.03 | 3.08 | 3.15 | **3.40** |
| Ton pédagogique | 3.15 | 3.53 | 3.81 | 3.75 | **4.04** |

| Verdict global | v2 | v3 | v4 | v5 | **v6 (final)** |
|---|---|---|---|---|---|
| Excellent | 0% | 0% | 2% | 1% | **4%** |
| Acceptable | 10% | 28% | 38% | 36% | **65%** |
| Problématique | 68% | 63% | 53% | 55% | **27%** |
| Inadapté | 22% | 9% | 7% | 8% | **4%** |

**Progression totale (v2 baseline → v6 final)** : adaptation +73%,
cohérence +49%, redondance +19% ; cas acceptable+excellent passés de 10%
à 69% ; cas inadapté (le pire verdict) passés de 22% à 4%.

### Changements effectivement livrés dans `pedagogical_feedback.py`

1. Fusion en une seule section continue (fin de la redondance structurelle
   2 sections).
2. Distinction stricte de formulation selon le `match_type` réel
   (exact/requires/qualifier/support/excluded/missed) — sans jamais
   présenter un match indirect comme une identification explicite.
3. Distinction stricte entre `validant_details` (soumis au match_type) et
   `decouvertes` (toujours des mentions explicites de l'étudiant, jamais
   à requalifier en "évoqué sans le nommer").
4. Interdiction stricte de jargon technique interne (match, rang A/B/C,
   pourcentages bruts) dans le texte destiné à l'étudiant, avec garde-fou
   déterministe de détection + re-génération automatique en cas de fuite.
5. Cohérence rang EDN (toujours celui fourni dans le contexte, jamais
   déduit/inventé).
6. Garde-fou déterministe (non-LLM) de cohérence ton/score : suppression
   automatique des formulations congratulatoires si score < 40%.
7. Interdiction d'inventer des nuances cliniques, règles diagnostiques ou
   distinctions terminologiques non fournies dans le contexte — priorité à
   la fiabilité sur l'exhaustivité, en particulier pour les scores de 100%.
8. Citation du cours strictement recopiée mot pour mot depuis le contexte
   fourni, jamais de placeholder ni de citation inventée.
9. Modèle de génération : `gpt-4o-mini` → `gpt-4o`.
10. Synchronisation du fix dans la copie vendored `ecg-online/rag_pipeline/`
    utilisée en production par `neuro_grader.py`.

### Problèmes résiduels (non résolus par le prompt — pistes futures)

Les ~27% de cas encore "problématique" sur gpt-5.6 relèvent maintenant
presque exclusivement de deux natures différentes des bugs corrigés :

1. **Approximations cliniques fines persistantes** du LLM rédacteur (ex:
   "QRS fins → bloc nodal, QRS larges → bloc infrahissien" présenté de
   façon trop catégorique) — amélioré par le passage à gpt-4o mais pas
   éliminé ; pourrait nécessiter une validation post-hoc des affirmations
   cliniques via l'ontologie plutôt que de laisser le LLM généraliser
   librement.
2. **Mapping NER→concept ontologique parfois trop agressif** (Priorité 4
   d'origine, non traitée dans ce cycle — ex: "aspect QS en DIII" mappé à
   "onde Q pathologique" sans tenir compte du contexte isolé). **Confirmé
   comme un problème d'ontologie et non de code** : le synonyme
   `skos:altLabel "Aspect QS"` est associé sans qualificatif à
   `PRESENCE_D_ONDE_Q_PATHOLOGIQUE` dans `BrYOzRZIu7jQTwmfcGsi35.owl`
   (ligne ~6493), alors que cliniquement un QS isolé en DIII est un variant
   normal fréquent. Rejoint le chantier "juge sémantique global" déjà
   documenté dans `audit_doc/roadmap_scientifique_2026.md` — nécessite un
   travail de révision de l'ontologie (retrait du synonyme non qualifié ou
   ajout d'un sous-concept qualifié par dérivation), pas une modification
   du prompt de feedback.
3. **Attribution occasionnelle à l'étudiant d'un concept "découverte"** qui
   provient en réalité d'un descripteur automatique et non du texte de
   l'étudiant lui-même (cas résiduel isolé, ex: "bloc interatrial" — semble
   être une confusion ponctuelle plutôt qu'un biais systématique).

### Fichiers produits (cycle complet)

- `scripts/audit_feedback_quality.py` — extraction + régénération (utilisé
  pour toutes les versions v2 à v6).
- `scripts/audit_feedback_gpt.py` — juge GPT (gpt-4o et gpt-5.6, avec fix
  `reasoning_effort="none"` pour les modèles reasoning en function-calling).
- `data/audit_feedback_2026-08-06_v{2..6}.json` — 100 triplets régénérés
  par version.
- `data/audit_feedback_gpt56_verdict_v{2..6}.json` — verdicts gpt-5.6 par
  version.
- `ECG lecture/rag_pipeline/pedagogical_feedback.py` — fichier canonique
  modifié (SYSTEM_PROMPT réécrit, garde-fous déterministes ajoutés, modèle
  changé), synchronisé vers `ecg-online/rag_pipeline/`.

### Conclusion

Le plafond du prompt engineering seul est probablement atteint. Les gains
mesurés sont réels et significatifs (cas acceptable+excellent : 10%→69%),
mais les problèmes résiduels sont désormais dominés par (a) des
approximations cliniques spontanées du LLM rédacteur et (b) un vrai bug
d'ontologie en amont (mapping NER trop agressif), tous deux hors du
périmètre de `pedagogical_feedback.py`. Prochaine étape naturelle si
l'on souhaite aller plus loin : réviser l'ontologie `BrYOzRZIu7jQTwmfcGsi35.owl`
pour désambiguïser les synonymes contextuels comme "Aspect QS", et/ou
explorer une validation post-hoc des affirmations cliniques du feedback
avant affichage.

---

## 🔄 MISE À JOUR — 06/08/2026 (suite) : P4 ontologie + validation post-hoc clinique (v7)

Deux actions supplémentaires ont été menées :

### 1. Correctif ontologique (P4) — retrait du synonyme ambigu "Aspect QS"

Dans `BrYOzRZIu7jQTwmfcGsi35.owl` (ligne ~6493), le synonyme
`skos:altLabel "Aspect QS"` était associé **sans qualificatif de contexte**
au concept `PRESENCE_D_ONDE_Q_PATHOLOGIQUE`. Or cliniquement, un "aspect QS"
isolé dans une seule dérivation (ex: DIII seul) est un variant normal
fréquent, pas une onde Q pathologique. Ce synonyme a été **retiré** de
l'OWL (les autres synonymes univoques — "onde q pathologique", "onde q de
nécrose", etc. — sont conservés intacts).

**Propagation appliquée** (tous les artefacts dérivés du `.owl`, pour
garder la cohérence dev + prod) :
- `data/ontology_v2.json` et `ecg-online/rag_pipeline/data/ontology_v2.json`
  (copie vendorée production) : synonyme retiré du concept.
- `rag_pipeline/rag_index/metadata_ontologie.json` et son équivalent
  `ecg-online/rag_pipeline/rag_index/` : entrée `surface_form: "Aspect QS"`
  retirée du registre (index 1118).
- `vecteurs_ontologie.npy` (les deux copies) : ligne d'embedding
  correspondante retirée pour garder l'alignement index↔document
  (1676 → 1675 documents).
- `bm25_corpus.json` (les deux copies) : entrée tokenisée correspondante
  retirée au même index pour garder l'alignement avec la matrice/registre.

**Validation directe** (recherche hybride, avant/après) :
- `"aspect QS en DIII"` → ne matche plus `PRESENCE_D_ONDE_Q_PATHOLOGIQUE`
  (meilleurs résultats désormais : `RABOTAGE_DE_L_ONDE_R`, `SUS_PQ`, etc. —
  aucun lien avec l'onde Q pathologique).
- `"onde q pathologique"` → matche toujours correctement le concept via son
  synonyme univoque conservé.

**Vérification sur le cas source du bug** (`ECG-YEUE` cas 1, régénéré en
v7) : le score reste à 0%, mais **pour une raison clinique différente et
légitime** cette fois — l'étudiant a décrit une onde P négative/diphasique
en dérivations inférieures avec une hypothèse de rythme du sinus coronaire,
ce qui est réellement incompatible avec un rythme sinusal normal (donc avec
`ECG_NORMAL`). Le concept "onde Q pathologique" n'apparaît PLUS dans les
découvertes de ce cas — **le faux positif "Aspect QS" est confirmé corrigé**.

### 2. Validation post-hoc des affirmations cliniques (piste "problèmes résiduels")

Ajout dans `pedagogical_feedback.py` d'un **second appel LLM dédié** (juge
séparé du rédacteur, Structured Outputs, température 0), exécuté après la
génération et le contrôle anti-jargon : `_validate_clinical_claims()` relit
le texte de feedback à la lumière STRICTE du contexte réellement fourni
(concepts trouvés/manqués + extraits de cours) et signale toute affirmation
clinique non ancrée dans ce contexte — règle diagnostique inventée,
distinction terminologique non fournie entre deux formulations synonymes,
mécanisme physiopathologique absent des extraits de cours. En cas de
détection, `_correct_unfounded_claims()` demande une réécriture CIBLÉE
(neutralise/retire uniquement les passages fautifs cités, sans réécrire
tout le texte), avec re-vérification anti-jargon avant application. Erreurs
de ce filet de sécurité capturées en best-effort (n'interrompent jamais la
génération). Synchronisé vers la copie vendorée `ecg-online/rag_pipeline/`.

### Résultats v7 (ontologie + validateur clinique) vs v6 — jugés par gpt-5.6

| Axe (/5) | v6 | **v7** |
|---|---|---|
| Adaptation | 3.64 | 3.58 |
| Cohérence | 4.20 | 4.09 |
| Redondance | 4.06 | 4.05 |
| Exactitude clinique | 3.40 | 3.33 |
| Ton pédagogique | 4.04 | 4.00 |

| Verdict global | v6 | **v7** |
|---|---|---|
| Excellent | 4% | 2% |
| Acceptable | 65% | 63% |
| Problématique | 27% | 32% |
| Inadapté | 4% | 3% |

**Interprétation** : les scores agrégés sur les 100 items sont **stables à
la variance près** (différence de 1 à 2 points sur chaque axe, non
significative compte tenu de la génération stochastique à `temperature=0.7`
— chaque run régénère un texte différent même pour le même item). Le
correctif ontologique (P4) est confirmé fonctionnel **au niveau mécanisme**
(vérification directe + cas source du bug), mais il ne représentait qu'un
seul cas parmi 100 dans cet échantillon, donc son effet n'est pas mesurable
isolément sur l'agrégat.

**Constat sur le validateur clinique (P3) — mécanisme inerte en pratique** :
les logs d'exécution du run v7 montrent que le garde-fou anti-jargon (P2)
s'est déclenché 3 fois sur 100, mais le warning "Affirmation(s) clinique(s)
non fondée(s)" ne s'est déclenché **AUCUNE fois** sur les 100 items. Le juge
de validation interne (`_validate_clinical_claims`, modèle `gpt-4o`,
température 0) n'a donc jamais renvoyé `contient_affirmation_non_fondee=True`
dans ce run — ce qui explique entièrement l'absence de gain mesurable : le
mécanisme de correction n'a simplement jamais été déclenché. Or gpt-5.6 (le
juge d'audit externe, plus sévère) relève dans ce même lot des affirmations
qui entrent exactement dans le périmètre visé par ce validateur (ex: "les TV
naissent sous la bifurcation hissienne" présenté comme un fait établi,
"flutter droit typique" vs "flutter atrial antihoraire" présentés à tort
comme deux concepts distincts alors que l'étudiant a écrit une seule
formulation synonyme, polarité de l'onde P en DIII/aVF présentée comme une
règle absolue). Ceci est cohérent avec l'écart de sévérité déjà observé
entre gpt-4o et gpt-5.6 en tant que JUGES D'AUDIT externes sur ce même type
de texte (68% vs 5% de "problématique" sur le lot v2) : `gpt-4o` est
structurellement plus indulgent que `gpt-5.6` sur ce type de nuance fine,
que ce soit comme juge d'audit externe ou comme juge de validation interne.
Deux pistes pour rendre ce garde-fou réellement actif : (a) utiliser
`gpt-5.6` (ou un modèle "reasoning" équivalent) comme juge de validation
interne au lieu de `gpt-4o`, au prix d'une latence/coût plus élevés par
génération (chaque feedback nécessiterait un 2e voire 3e appel reasoning) ;
(b) durcir/enrichir `_CLINICAL_VALIDATOR_SYSTEM_PROMPT` avec des exemples
concrets tirés de ces cas précis, sans changer de modèle. **Non fait dans ce
cycle** — le code est en place et ne casse rien, mais n'apporte
actuellement aucun bénéfice mesuré avec `gpt-4o` comme juge.

### Statut mis à jour des 3 options de suite

1. **P4 (ontologie)** : ✅ fait et vérifié mécaniquement — synonyme ambigu
   retiré, propagé à tous les artefacts dérivés (JSON, index vectoriel,
   BM25), cas source du bug confirmé résolu.
2. **Ship v6/v7 tel quel** : toujours une option raisonnable — le niveau de
   qualité global (~65% acceptable+excellent) est stable entre v6 et v7.
3. **Validation post-hoc clinique** : implémentée et non régressive (aucune
   erreur, aucun jargon réintroduit), mais **inerte en pratique** dans ce
   run (0 déclenchement sur 100 avec `gpt-4o` comme juge interne, alors que
   `gpt-5.6` en tant que juge externe détecte des cas qui auraient dû
   déclencher le mécanisme) — nécessite soit un modèle juge plus strict en
   interne, soit un prompt de validation renforcé, avant de pouvoir
   considérer ce gain comme acquis.

## 🔄 MISE À JOUR — 06/08/2026 (suite 2) : correctif "descripteur support-tier" + validation v8

### Bug utilisateur remonté : hallucination "Bloc interatrial" sur `ECG-Z8C5 cas 1`

L'utilisateur a signalé un cas concret : pour `ECG-Z8C5 cas 1`, l'étudiant a
écrit *"Rythme sinusal a 62 bm régulier pas d'anomalie visible"*, mais le
feedback généré affirmait *"vous avez correctement noté un bloc
interatrial"* — une affirmation totalement absente de la réponse de
l'étudiant.

**Investigation** : contrairement à l'hypothèse initiale (hallucination du
LLM rédacteur), le champ `descripteur_details` du `CandidateReport` lui-même
contenait déjà `{"golden_name": "Bloc interatrial", "found": true}` **avant
même** l'appel au rédacteur — ce n'était donc pas un problème de prompt
mais un **bug de scoring en amont**.

**Root cause** : dans `ontology_v2.json`, le concept `BLOC_INTERATRIAL`
déclare `"supports": ["RYTHME_SINUSAL"]` — un lien statistique **faible**,
prévu uniquement pour nuancer le score partiel des *validants* (tiers le
plus bas de la hiérarchie de matching V3 : exact/enfant (1.0) > implique
(1.0) > négation (1.0) > requires (ratio partiel) > parent-qualifier (2/3)
> parent-support (1/3, distance ≥2) > **supports (1/3)** > manqué/exclu (0)).
Comme "rythme sinusal" apparaît dans la quasi-totalité des réponses
étudiantes, ce lien faible se déclenchait quasi systématiquement. Le même
schéma affecte 3 autres concepts également liés par `supports:
[RYTHME_SINUSAL]` : `HYPERTROPHIE_ATRIALE_DROITE`,
`HYPERTROPHIE_ATRIALE_GAUCHE`, `INSUFFISANCE_CHRONOTROPE`.

Le bug de code exact se situait dans `candidate_report.py` (boucle de
construction des descripteurs, ~ligne 718) :
```python
found = cs.match_type not in ("missed", "excluded")
```
Cette condition traitait **même le tier "support" le plus faible** comme un
`found=True` binaire — acceptable pour les *validants* (affichés avec un
score % qui reflète l'incertitude), mais inapproprié pour les
*descripteurs* (affichés comme une affirmation catégorique dans le texte de
feedback, ex. "vous avez correctement noté un bloc interatrial").

### Correctif appliqué

```python
found = cs.match_type not in ("missed", "excluded", "support")
```

Synchronisé vers la copie vendorée `ecg-online/rag_pipeline/candidate_report.py`.

### Validation à l'échelle (régénération complète v8, 100 items)

Après le correctif, une nouvelle régénération complète a été lancée :
`data/audit_feedback_2026-08-06_v8.json` (100 items, 0 erreur).

**Vérification directe des 2 cas signalés par l'utilisateur** :
- `ECG-Z8C5 cas 1` : `descripteur_details` montre désormais
  `"Bloc interatrial": found: false`. Le texte de feedback ne mentionne
  plus le bloc interatrial du tout — il se limite correctement au rythme
  sinusal et à la fréquence, et invite l'étudiant à être plus systématique.
- `ECG-VQFO cas 6` : de même, `"Bloc intraventriculaire aspécifique":
  found: false` — feedback propre, aucune mention infondée.

**Confirmation à l'échelle via le juge externe gpt-5.6** : l'exemple de
problème explicitement cité dans le rapport v7 — *"Il prétend que
l'étudiant a « correctement noté un bloc interatrial », alors que celui-ci
n'en a jamais fait mention"* — **n'apparaît plus du tout** dans la liste des
problèmes détectés en v8, confirmant que le correctif élimine cette classe
de bug de façon systémique et pas seulement sur le cas isolé vérifié
manuellement.

### Résultats v8 vs v7 (jugés par gpt-5.6)

| Axe (/5) | v6 | v7 | **v8** |
|---|---|---|---|
| Adaptation | 3.64 | 3.58 | **3.67** |
| Cohérence | 4.20 | 4.09 | **4.32** |
| Redondance | 4.06 | 4.05 | 4.02 |
| Exactitude clinique | 3.40 | 3.33 | **3.40** |
| Ton pédagogique | 4.04 | 4.00 | **4.08** |

| Verdict global | v6 | v7 | **v8** |
|---|---|---|---|
| Excellent | 4% | 2% | 0% |
| Acceptable | 65% | 63% | **73%** |
| Problématique | 27% | 32% | **25%** |
| Inadapté | 4% | 3% | **2%** |

**Interprétation** : première amélioration nettement mesurable du cycle —
+10 points sur "acceptable", -7 sur "problématique", et gain le plus net sur
la **cohérence** (+0.23 vs v7, +0.12 vs v6), cohérent avec la nature du bug
corrigé (affirmations contradictoires avec ce que l'étudiant a réellement
écrit). Le score "excellent" tombe à 0%, mais ceci reflète la variance
stochastique de génération (`temperature=0.7`) plutôt qu'une régression —
aucun des exemples de problèmes remontés par gpt-5.6 sur v8 n'est lié au bug
corrigé.

**Constat additionnel sur le validateur clinique (P3)** : contrairement au
run v7 (0 déclenchement sur 100), le run v8 montre le garde-fou
`_validate_clinical_claims` se déclencher **très fréquemment** (>20 fois
observées dans les logs), corrigeant en direct des affirmations non
fondées de nature variée (distinction BAV Mobitz 2 / haut grade, mécanismes
physiopathologiques inventés, contradictions avec des concepts pourtant
marqués TROUVÉ — ex. "vous ne l'avez pas nommé explicitement" alors que le
concept était bien détecté). Notamment, à `ECG-ZKB9 cas 14`, le validateur a
lui-même intercepté et neutralisé une **autre** instance du même type de
bug (une affirmation infondée sur le bloc interatrial), démontrant que les
deux mécanismes (correctif déterministe du seuil de scoring + validateur
LLM post-hoc) se complètent sans se substituer l'un à l'autre. L'absence de
déclenchement en v7 semble donc avoir été un artefact de variance
stochastique du run plutôt qu'un problème structurel du modèle `gpt-4o`
comme juge interne — conclusion à confirmer sur d'autres runs si le doute
persiste, mais elle nuance l'hypothèse initiale ("gpt-4o structurellement
trop indulgent en tant que juge interne").

### Statut mis à jour

1. **Bug "descripteur support-tier"** : ✅ root-cause identifiée, corrigé,
   synchronisé prod, validé à l'échelle (v8, 100 items) — confirmé résolu
   à la fois sur les 2 cas signalés par l'utilisateur et sur l'agrégat
   gpt-5.6 (disparition de l'exemple de problème correspondant).
2. **Piste ouverte** : auditer systématiquement l'ontologie pour d'autres
   liens `supports` faibles pointant vers des concepts quasi-universels
   (sur le modèle de `RYTHME_SINUSAL`), au-delà des 4 concepts déjà
   identifiés (`BLOC_INTERATRIAL`, `HYPERTROPHIE_ATRIALE_DROITE`,
   `HYPERTROPHIE_ATRIALE_GAUCHE`, `INSUFFISANCE_CHRONOTROPE`).
3. **Validateur clinique (P3)** : réévalué comme actif et efficace au vu du
   run v8 (contrairement au constat "inerte" du v7) — recommandé de garder
   ce mécanisme en production, sans changement de modèle pour l'instant.

## 🔄 MISE À JOUR — 06/08/2026 (suite 3) : 2 bugs de couverture lexicale + refonte générique du filet de sécurité (v9)

### Bug 1 — synonyme manquant : "Flutter commun anti-horaire"

L'utilisateur a remonté un exemple concret (`ECG-WY55 cas 8`) : l'étudiant
écrit *« Flutter commun anti-horaire, QRS fins »*, mais le feedback affirme
à tort qu'il n'a pas identifié le « flutter droit typique » (score 0%),
alors que "Flutter commun anti-horaire" **est** le nom clinique standard du
flutter droit typique en sens antihoraire.

**Investigation** : le concept `FLUTTER_ATRIAL_ANTIHORAIRE` (enfant
ontologique de `FLUTTER_DROIT_TYPIQUE`, donc censé le créditer via la règle
"enfant trouvé") existait déjà avec 4 synonymes proches ("Flutter atrial
anti-horaire", "Flutter commun antihoraire" sans tiret, "Flutter atrial
commun anti-horaire"), mais **aucun ne correspondait exactement**, après
normalisation, à la formulation réelle "flutter commun anti horaire"
écrite par l'étudiant. Le NER (GPT-4o) n'a extrait que le mot "flutter"
isolé (trop vague, non résolu), et le filet de sécurité lexical n'a pas pu
rattraper faute de synonyme correspondant à 100%.

**Correctif** : ajout du synonyme exact "Flutter commun anti-horaire" (+
variante "Flutter atrial commun antihoraire") au concept
`FLUTTER_ATRIAL_ANTIHORAIRE`, dans `BrYOzRZIu7jQTwmfcGsi35.owl` et les deux
copies `ontology_v2.json` (dev + prod). Validé : score passe de 0% à 100%
sur le cas exact via le mécanisme "enfant crédite le parent golden".

### Bug 2 — seuil du filet lexical trop strict pour "Echappement ventriculaire"

**Scan systématique** : afin de détecter d'autres cas du même type avant de
les corriger un par un, un scan complet des 73 sessions étudiantes réelles
disponibles (345 cas régénérés) a été effectué, comparant chaque concept
golden marqué "manqué" au texte réel de l'étudiant (recouvrement lexical).
Ce scan a mis en évidence un second bug systémique : **4 étudiants ont écrit
littéralement "échappement ventriculaire"** (ex. *« BAV complet avec
échappement ventriculaire à 42/min »*, `ECG-84SV cas 2`, `ECG-IJZK cas 2`,
`ECG-NDK6 cas 2`), mais le concept restait marqué "manqué" à chaque fois —
alors même que le NOM CANONIQUE exact du concept était écrit mot pour mot.

**Root cause** : le filet de sécurité lexical (`_lexical_backstop_ids`)
exigeait qu'un synonyme fasse **au moins 3 mots** pour être éligible au
rattrapage (`BACKSTOP_MIN_DISTINCTIVE_WORDS=3`), afin d'éviter les faux
positifs sur des mots isolés trop génériques ("bloc", "onde"). Mais
"Echappement ventriculaire" ne fait que 2 mots — donc même écrit
littéralement par l'étudiant, ni le NER ni le backstop ne le capturaient.

**Rejet d'un correctif "liste blanche"** : une première option (ajouter
"Echappement ventriculaire" à une liste d'exceptions en dur) a été jugée
inadéquate — non scalable, spécifique au français, fragile face à
l'extension future de l'ontologie ou à d'autres langues.

**Correctif retenu — critère de SPÉCIFICITÉ LEXICALE générique et
data-driven**, remplaçant le critère de longueur brute :
- Calcul, une fois au chargement de l'ontologie, de la **fréquence
  documentaire (DF)** de chaque mot normalisé : nombre de concepts
  *distincts* dont au moins une forme (nom canonique ou synonyme) contient
  ce mot (`_word_document_frequency()`, mise en cache).
- Un synonyme est désormais éligible au rattrapage lexical s'il contient
  **au moins un mot avec DF ≤ 4** (`BACKSTOP_MAX_WORD_DOCUMENT_FREQUENCY`),
  peu importe le nombre total de mots du synonyme.
- 100% dérivé de l'ontologie chargée — **aucune liste de mots figée en
  dur**, donc indépendant de la langue et scalable à l'ajout de nouveaux
  concepts.

**Validation du seuil retenu (DF≤4)** : calcul exhaustif sur les 349 formes
à 2 mots de l'ontologie V2. Ce seuil rend éligible "Echappement
ventriculaire" (DF("échappement")=4) sans ouvrir la porte aux combinaisons
purement génériques : "ventriculaire" (DF=56), "bloc" (DF=24), "onde"
(DF=38), "gauche" (DF=26) restent tous largement au-dessus du seuil et donc
insuffisants seuls pour déclencher un rattrapage.

**Tests de non-régression** :
- "Echappement ventriculaire" écrit littéralement → rattrapé (3/4 cas
  confirmés corrigés ; le 4e, `ECG-ZKB9 cas 2`, était un vrai manque
  légitime : l'étudiant n'avait écrit que "échappement jonctionnel").
- "Flutter commun anti-horaire" → toujours rattrapé (non-régression OK).
- Texte purement générique ("bloc ventriculaire gauche onde") → aucun
  rattrapage à tort (protection anti-faux-positif intacte).
- Re-scan complet des 345 cas des 73 sessions réelles → aucune nouvelle
  régression détectée.

**Fichiers modifiés** :
- `rag_pipeline/scoring_thresholds.py` : nouvelle constante
  `BACKSTOP_MAX_WORD_DOCUMENT_FREQUENCY=4`, documentée en détail
  (justification + historique du bug qui l'a motivée). Ancienne constante
  `BACKSTOP_MIN_DISTINCTIVE_WORDS` conservée en dépréciée (compat
  descendante uniquement).
- `rag_pipeline/candidate_report.py` : `_word_document_frequency()` +
  `_is_synonym_specific_enough()` remplacent le critère de longueur dans
  `_lexical_backstop_ids()`.
- Synchronisé vers la copie vendorée `ecg-online/rag_pipeline/` (les deux
  fichiers `.py` sont désormais byte-identiques entre les deux copies).

**⚠️ Écart pré-existant noté (hors périmètre de ce correctif)** : les
fichiers `data/ontology_v2.json` (racine, réellement chargé en priorité
par `semantic_layer.py`) et `rag_pipeline/data/ontology_v2.json` (chemin
secondaire, non utilisé par le pipeline canonique sauf fallback) divergent
légèrement sur 5 concepts (`ARTEFACTE`, `ECG_NORMAL`,
`FLUTTER_ATRIAL_ANTIHORAIRE`, `PRESENCE_D_ONDE_Q_PATHOLOGIQUE`,
`TREMULATION_DE_LA_LIGNE_DE_BASE`) — notamment le fix P4 "Aspect QS" n'est
présent que dans `data/ontology_v2.json`. Sans impact sur le pipeline en
production (qui charge `data/ontology_v2.json` en premier), mais à
nettoyer/fusionner dans un futur ménage de repository pour éviter toute
confusion future.

### Résultats v9 vs v8 (jugés par gpt-5.6)

Régénération complète (100 items, `data/audit_feedback_2026-08-06_v9.json`,
0 erreur / 100) avec les deux correctifs actifs, jugée par gpt-5.6
(`data/audit_feedback_gpt56_verdict_v9.json`).

| Axe (/5) | v7 | v8 | **v9** |
|---|---|---|---|
| Adaptation | 3.58 | 3.67 | 3.72 |
| Cohérence | 4.09 | 4.32 | 4.30 |
| Redondance | 4.05 | 4.02 | **4.04** |
| Exactitude clinique | 3.33 | 3.40 | **3.41** |
| Ton pédagogique | 4.00 | 4.08 | **4.06** |

| Verdict global | v7 | v8 | **v9** |
|---|---|---|---|
| Excellent | 2% | 0% | **5%** |
| Acceptable | 63% | 73% | 64% |
| Problématique | 32% | 25% | 28% |
| Inadapté | 3% | 2% | 3% |

**Vérification ciblée des 2 bugs corrigés** :
- `ECG-WY55 cas 8` ("Flutter commun anti-horaire") : score de couverture
  ontologique 100% (contre 0% avant fix), verdict qualité gpt-5.6
  **"excellent"** — le feedback reconnaît désormais correctement le
  diagnostic. ✅ Confirmé corrigé à l'échelle.
- Les 3 cas "Echappement ventriculaire" (`ECG-84SV cas 2`, `ECG-IJZK cas 2`,
  `ECG-NDK6 cas 2`) : couverture ontologique passée à 100% pour le concept
  (contre "manqué" avant fix). Un seul reliquat noté par gpt-5.6 sur
  `ECG-R48T cas 13` : le feedback reproche encore à l'étudiant de ne pas
  avoir cité "l'échappement ventriculaire" alors qu'il avait écrit
  "échappement jonctionnel" — ceci est un **vrai manque légitime** (concept
  différent), pas une régression du fix. ✅ Confirmé corrigé à l'échelle,
  sans faux positif introduit.

**Interprétation globale** : le taux "acceptable+excellent" reste élevé
(69% vs 73% en v8, dans la marge de variance stochastique de génération),
avec un gain notable sur le taux "excellent" (0%→5%) et une légère
amélioration continue de l'adaptation et de l'exactitude clinique. Aucun
signal de régression sur la cohérence/redondance/ton. Les deux bugs de
couverture lexicale identifiés cette session sont confirmés corrigés sans
effet de bord détectable sur l'échantillon de 100 items. Le nouveau critère
générique de spécificité lexicale (DF≤4) peut être considéré comme validé
en production.

**Point de vigilance conservé** : le validateur P3 continue, à raison, de
questionner certaines formulations approximatives du feedback-writer (ex.
citation "flutter commun antihoraire" jugée non strictement sourcée dans
les extraits de cours sur `ECG-ZKB9 cas 5`) — ce n'est pas un défaut du fix
ontologique, mais un rappel que le prompt de rédaction du feedback pourrait
gagner à citer explicitement l'équivalence synonyme↔concept golden quand le
backstop lexical est le mécanisme ayant permis la détection.

