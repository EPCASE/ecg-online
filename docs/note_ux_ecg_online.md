# Note UX — ECG Online / Edu-ECG

## Objectif de cette note

Cette note synthétise les pistes UX pour faire évoluer l’interface ECG Online d’un outil opérationnel de collecte vers un véritable **parcours d’entraînement ECG**, capable à la fois :

1. de récolter des réponses libres exploitables pour le pipeline Edu-ECG ;
2. d’accrocher les utilisateurs ;
3. de donner envie de lire davantage d’ECG ;
4. de rendre la progression pédagogique lisible ;
5. de préparer une future interface hybride texte libre + concepts cliquables.

L’enjeu n’est pas seulement esthétique. L’UX conditionne directement la qualité de la base de réponses étudiantes, l’équilibre de lecture entre les cas, l’usage du QCM, la compréhension du score et la rétention des utilisateurs.

---

## 1. Diagnostic général

L’interface actuelle semble surtout pensée comme une interface de collecte :

- choisir un cas ;
- lire un ECG ;
- saisir une interprétation ;
- obtenir une correction ;
- éventuellement utiliser le mode QCM.

Cette structure est fonctionnelle, mais elle ne suffit pas pour créer un usage répété.

Le risque actuel est que l’utilisateur pense :

> “Je dois faire un devoir d’ECG dans une interface sombre.”

Alors qu’il faudrait qu’il pense :

> “Je progresse dans un entraînement ECG, je comprends ce qui me manque, et j’ai envie d’en faire un de plus.”

L’objectif UX doit donc être de transformer l’app en **boucle d’entraînement** plutôt qu’en simple banque de cas.

---

## 2. Problèmes UX identifiés

| Problème | Effet probable |
|---|---|
| Cas mélangés | L’étudiant ne perçoit pas de progression |
| Liste brute 1–75 | Les premiers cas seront surreprésentés |
| Cas anonymisés ou peu contextualisés | Moins de narration, moins d’engagement |
| QCM trop facilement accessible | Risque d’appauvrir les réponses libres |
| Score peu explicite | Frustration ou incompréhension |
| Absence d’incitation à continuer | Faible rétention |
| Absence de parcours | Difficulté à se situer |
| Interface très opérationnelle | Bonne pour collecter, moins bonne pour apprendre |
| Pas de recommandation du cas suivant | Rupture après correction |
| Système de notation peu clair | L’utilisateur ne sait pas comment s’améliorer |

---

## 3. Décision structurante : séparer deux modes

Il faut distinguer deux usages qui n’ont pas les mêmes contraintes.

### 3.1 Mode “Entraînement guidé”

Objectif : accrocher, faire progresser, donner envie.

Caractéristiques :

- parcours progressif ;
- feedback immédiat ;
- score lisible ;
- possibilité d’aide ;
- badges sobres ;
- séries thématiques ;
- QCM comme remédiation ;
- suggestions de concepts possibles.

Ce mode est pensé pour l’étudiant qui veut apprendre.

### 3.2 Mode “Challenge / Réponse libre”

Objectif : récolter des données de qualité.

Caractéristiques :

- réponse libre avant toute aide ;
- pas de QCM visible au départ ;
- cas randomisés intelligemment ;
- correction après soumission ;
- traçabilité de l’usage d’indices ou du QCM ;
- suivi des scores ;
- collecte exploitable pour le pipeline.

Ce mode est pensé pour la recherche, l’évaluation et la constitution du corpus.

### 3.3 Pourquoi cette séparation est importante

Le QCM rassure l’utilisateur, mais il transforme la tâche. Il favorise la reconnaissance plutôt que la production. Or le cœur scientifique d’Edu-ECG est précisément la correction d’une réponse libre.

Le QCM ne doit donc pas être supprimé, mais il ne doit pas devenir le mode principal.

---

## 4. Nouvelle architecture de l’accueil

L’écran d’accueil ne devrait pas montrer d’abord une liste de 75 cas.

Il devrait proposer une action claire.

### Proposition d’accueil

```text
Que veux-tu faire aujourd’hui ?

1. Faire mon ECG du jour
   1 cas court, correction immédiate

2. M’entraîner par niveau
   Débutant → Intermédiaire → Avancé

3. Réviser un thème
   Rythme · Conduction · Ischémie · Stimulation · Extrasystoles · ECG normal
```

En dessous :

```text
Progression
12 ECG corrigés · Série en cours : 3 jours · Meilleur thème : conduction · Thème à travailler : repolarisation
```

L’idée est de ne pas présenter l’outil comme une base de données, mais comme un entraînement.

---

## 5. Organisation des cas

### 5.1 Parcours progressif

Il faut recréer la progressivité du livre ou d’un enseignement structuré.

Exemple :

#### Niveau 1 — Fondamentaux

- ECG normal ;
- fibrillation atriale ;
- BBD ;
- BAV complet ;
- microvoltage ;
- rythme sinusal simple.

#### Niveau 2 — Intermédiaire

- flutter ;
- BAV 2 ;
- BBG ;
- WPW ;
- extrasystoles ventriculaires ;
- troubles de conduction plus nuancés.

#### Niveau 3 — Avancé

- tachycardie ventriculaire ;
- SCA ST+ ;
- stimulation ;
- diagnostics piégeux ;
- cas mixtes.

#### Niveau 4 — Expert / Rythmologie

- pacemaker complexe ;
- flutter atypique ;
- TV selon mécanisme ;
- électrophysiologie ;
- anomalies combinées ;
- cas incomplets ou ambigus.

Même si la difficulté est d’abord empirique, elle pourra être recalibrée par les scores réels des utilisateurs.

---

### 5.2 Parcours thématiques

Proposer une entrée par familles :

- Rythme ;
- Conduction ;
- QRS ;
- Repolarisation ;
- Ischémie ;
- Pacemaker ;
- Extrasystoles ;
- Troubles métaboliques ;
- ECG normal ;
- Cas mixtes.

Chaque famille peut avoir une progression interne.

---

### 5.3 ECG du jour

Un cas unique, immédiatement accessible.

Objectif :

- réduire la friction ;
- créer une routine ;
- favoriser le retour régulier ;
- éviter la paralysie devant 75 cas.

Exemple :

```text
ECG du jour
Durée estimée : 3 minutes
Objectif masqué
Correction immédiate
```

---

### 5.4 Mode aléatoire équilibré

Ne pas utiliser un hasard pur.

Il faut un hasard pondéré :

- suréchantillonner les cas peu lus ;
- sous-échantillonner les cas déjà très lus ;
- varier les familles diagnostiques ;
- éviter de proposer deux cas trop similaires d’affilée ;
- tenir compte du niveau de l’utilisateur ;
- tenir compte des erreurs précédentes.

Objectif recherche : éviter que les cas du haut de la liste aient beaucoup plus de réponses que les cas du bas.

---

## 6. Gestion du QCM

### 6.1 Ne pas afficher le QCM avant la réponse libre

Si le QCM est visible immédiatement, il biaise la tâche.

L’étudiant reconnaît la bonne réponse au lieu de produire une interprétation structurée.

### 6.2 Positionner le QCM comme aide après tentative

Après une première réponse libre :

```text
Besoin d’aide ?
[Afficher un indice]
[Passer en QCM]
[Voir la structure attendue]
```

Le QCM devient une remédiation, pas une échappatoire.

### 6.3 Taguer les conditions de réponse

Pour la base de données, il faut distinguer :

- réponse libre sans aide ;
- réponse libre avec indice ;
- réponse libre puis QCM ;
- QCM direct ;
- correction consultée ;
- réponse modifiée après aide.

Cela permettra d’analyser séparément les performances et la qualité des données.

---

## 7. Score et feedback

Le score doit être compréhensible et actionnable.

Un score global seul n’est pas suffisant.

### Proposition de restitution

```text
Score global : 72 %

Diagnostic principal : 80 %
Description ECG : 60 %
Sécurité clinique : OK
Formulation : partielle
```

Puis :

```text
Ce que tu as trouvé
✓ Rythme sinusal
✓ QRS larges
✓ Bloc de branche droit

Ce qui manque
• Préciser complet/incomplet
• Mentionner la repolarisation secondaire

Ce qui est en trop ou discutable
• “Ischémie” : non retenu ici
```

Puis une phrase pédagogique :

```text
Ton raisonnement va dans la bonne direction : tu reconnais le trouble de conduction, mais tu ne qualifies pas assez le bloc. Dans une réponse EDN, le diagnostic “BBD complet” doit être explicite.
```

### Objectif du score

Le score ne doit pas seulement sanctionner. Il doit orienter la prochaine action.

Il doit répondre à quatre questions :

1. Qu’ai-je bien identifié ?
2. Qu’ai-je oublié ?
3. Qu’ai-je affirmé à tort ?
4. Quel ECG dois-je faire maintenant pour progresser ?

---

## 8. Boucle d’engagement

La page après correction est centrale.

Actuellement, le risque est :

```text
Cas → réponse → score → fin
```

Il faut créer :

```text
Cas → réponse → correction → apprentissage → prochain cas recommandé
```

### Après chaque correction

Proposer trois suites :

```text
Continuer

1. Faire un cas similaire
   Pour consolider ce diagnostic

2. Faire un cas plus difficile
   Même famille, niveau supérieur

3. Corriger une faiblesse
   Tu as manqué la repolarisation : faire un cas ciblé
```

Cette recommandation transforme l’évaluation en parcours.

---

## 9. Gamification sobre

La gamification peut être utile, mais elle doit rester médicale, sobre et orientée compétence.

L’objectif n’est pas de faire un jeu vidéo. L’objectif est de soutenir :

- la compétence ;
- l’autonomie ;
- la motivation ;
- la régularité ;
- la progression visible.

### 9.1 Éléments à intégrer

#### Progression personnelle

```text
Niveau ECG 3 — Interne débutant
18 ECG lus
Précision diagnostique : 72 %
Meilleure série : 5 ECG
```

#### Badges pédagogiques

- 5 ECG lus ;
- première FA reconnue ;
- conduction niveau 1 validée ;
- 3 diagnostics urgents reconnus ;
- 10 cas sans QCM ;
- première correction parfaite ;
- repolarisation niveau 1 ;
- stimulation niveau 1.

#### Série légère

```text
Série en cours : 3 jours
Un ECG demain pour continuer.
```

Sans culpabilisation ni pénalité agressive.

#### Objectifs courts

```text
Objectif du jour : reconnaître un trouble de conduction
Durée estimée : 3 minutes
```

#### Déblocage progressif

Les cas avancés apparaissent après les cas simples. Cela donne un sentiment de progression.

---

### 9.2 Éléments à éviter

- leaderboard public ;
- classement par score brut ;
- compétition entre étudiants ;
- badges enfantins ;
- punition des erreurs ;
- score global opaque ;
- titre “expert” trop précoce ;
- gamification qui encourage le QCM plutôt que la réponse libre.

En médecine, un mauvais leaderboard peut décourager les étudiants faibles, alors que ce sont eux qui ont le plus besoin de l’outil.

---

## 10. Aide à l’écriture

C’est probablement l’évolution UX la plus intéressante.

Il faut créer un troisième mode entre texte libre pur et QCM :

> Réponse libre assistée.

### Exemple

L’étudiant écrit :

```text
Rythme sinusal, QRS larges, aspect rSR’ en V1...
```

L’interface propose :

```text
Concepts détectés :
✓ Rythme sinusal
✓ QRS larges
✓ Bloc de branche droit probable
? BBD complet
```

L’utilisateur peut alors confirmer, refuser ou compléter.

### Deux usages différents

#### Entraînement

Les suggestions peuvent apparaître pendant l’écriture.

#### Challenge / collecte

Les suggestions ne doivent apparaître qu’après la soumission.

Cela évite de biaiser les réponses libres utilisées pour entraîner ou évaluer le pipeline.

---

## 11. Lien avec la grille DALL-E / pré-annotation par clic

La grille DALL-E est une bonne interface de validation conceptuelle.

Edu-ECG est un bon moteur de lecture, scoring et feedback.

Il ne faut pas forcément fusionner les bases, mais créer un pont :

```text
Réponse libre étudiant
        │
        ▼
Extraction Edu-ECG
NER + recherche hybride + juge contraint
        │
        ▼
Concepts Edu-ECG normalisés
        │
        ▼
Crosswalk Edu ↔ DALL-E
        │
        ▼
Tags DALL-E proposés
        │
        ▼
Validation humaine par clic
```

Dans l’autre sens :

```text
Clics DALL-E
        │
        ▼
Tags DALL-E
        │
        ▼
Crosswalk DALL-E ↔ Edu
        │
        ▼
Concepts Edu-ECG
        │
        ▼
Score / feedback / analyse de cohérence
```

### Usage UX possible

Après soumission :

```text
L’IA pense avoir reconnu :
✓ BBD complet
✓ QRS larges
✓ Repolarisation secondaire

Confirme les concepts :
[Valider] [Modifier] [Ajouter un concept]
```

Cela permet :

- d’améliorer la correction ;
- d’enrichir le golden ;
- de corriger les erreurs du pipeline ;
- d’entraîner un futur modèle local ;
- d’intégrer une logique de pré-annotation par clic.

---

## 12. Gestion du contexte des cas

L’anonymisation est nécessaire, mais elle ne doit pas tuer la narration pédagogique.

### Avant réponse

Ne pas spoiler le diagnostic.

Exemple :

```text
Cas 12 — Douleur thoracique
Niveau : intermédiaire
Objectif masqué
```

### Après réponse

Révéler l’objectif pédagogique :

```text
Thème : syndrome coronarien aigu ST+
Objectif pédagogique : reconnaître le courant de lésion sous-épicardique et le miroir.
```

### Principe

Donner assez de contexte pour engager l’utilisateur, mais pas assez pour donner la réponse.

---

## 13. Données à instrumenter

Pour améliorer à la fois le produit et la recherche, l’interface doit logger certains événements.

### Données utilisateur / session

- utilisateur anonyme ou pseudonyme ;
- date ;
- session ;
- cas consulté ;
- ordre du cas ;
- mode utilisé : entraînement, challenge, QCM ;
- parcours : niveau, thème, ECG du jour.

### Données d’interaction

- temps passé sur le tracé ;
- temps avant première saisie ;
- temps total avant soumission ;
- nombre de modifications ;
- longueur de réponse ;
- usage du zoom ;
- usage d’un indice ;
- usage du QCM ;
- abandon avant soumission ;
- abandon après correction ;
- bouton suivant choisi.

### Données pédagogiques

- score global ;
- score diagnostic ;
- score descriptif ;
- sécurité clinique ;
- concepts trouvés ;
- concepts manqués ;
- concepts erronés ;
- type d’erreur ;
- feedback affiché ;
- cas suivant recommandé.

### Analyses possibles

- quels ECG accrochent ;
- quels ECG font abandonner ;
- quels concepts sont systématiquement manqués ;
- effet du QCM sur la qualité des réponses ;
- effet des indices ;
- progression par thème ;
- effet de la correction sur le cas suivant ;
- équilibre de collecte entre cas.

---

## 14. Version UX cible en trois écrans

### 14.1 Écran 1 — Accueil

```text
Prépare tes ECG EDN

Un entraînement court, corrigé par IA, avec feedback pédagogique.

[ECG du jour — 3 min]
[Parcours progressif]
[Réviser un thème]

Ta progression
12/75 ECG lus · Série 3 jours · Diagnostic principal 74 %
```

---

### 14.2 Écran 2 — Cas

```text
Cas recommandé — Niveau 2
Contexte : malaise chez un patient de 78 ans
Objectif masqué

[Tracé ECG zoomable]

Ton interprétation
Structure conseillée :
Rythme · Fréquence · Axe · Conduction · Repolarisation · Diagnostic

[Corriger ma réponse]
[Besoin d’un indice]
```

---

### 14.3 Écran 3 — Correction

```text
Score : 72 %

Diagnostic principal : partiel
Description : correcte
Sécurité : pas d’erreur critique

Tu as trouvé :
✓ Rythme sinusal
✓ QRS larges

À améliorer :
• Nommer le bloc complet
• Décrire la repolarisation secondaire

Feedback :
...

Continuer :
[Cas similaire]
[Cas plus difficile]
[Revoir la fiche conduction]
```

---

## 15. Backlog priorisé

## Sprint 1 — Engagement minimal

Objectif : donner envie de commencer et de continuer.

- [ ] Remplacer la liste brute par une page d’accueil orientée action.
- [ ] Ajouter “ECG du jour”.
- [ ] Ajouter “Parcours progressif”.
- [ ] Ajouter “Réviser un thème”.
- [ ] Afficher une progression utilisateur minimale.
- [ ] Ajouter un bouton “cas suivant recommandé” après correction.
- [ ] Transformer les cas en cartes plutôt qu’en simple liste.
- [ ] Ajouter niveau et contexte non spoiler.

---

## Sprint 2 — Collecte propre

Objectif : préserver la qualité des données.

- [ ] Masquer le QCM avant une tentative libre.
- [ ] Taguer les réponses selon les aides utilisées.
- [ ] Randomiser les cas de manière pondérée.
- [ ] Suréchantillonner les cas peu lus.
- [ ] Logger temps, abandon, aide, QCM, score.
- [ ] Distinguer mode entraînement et mode challenge.
- [ ] Exporter les métriques d’usage.

---

## Sprint 3 — Correction compréhensible

Objectif : rendre le score actionnable.

- [ ] Séparer score diagnostic, score descriptif et sécurité clinique.
- [ ] Afficher concepts trouvés, manqués, erronés.
- [ ] Expliquer le score en une phrase.
- [ ] Proposer un cas suivant selon l’erreur.
- [ ] Ajouter un feedback court avant le feedback long.
- [ ] Ajouter une fiche pédagogique liée au concept manqué.

---

## Sprint 4 — Aide à l’écriture

Objectif : connecter texte libre et concepts.

- [ ] Afficher les concepts détectés après soumission.
- [ ] Permettre de confirmer/refuser un concept.
- [ ] Ajouter un mode “réponse assistée”.
- [ ] Proposer des tags cliquables issus du crosswalk DALL-E ↔ Edu-ECG.
- [ ] Enregistrer les validations humaines pour enrichir le golden.
- [ ] Créer une inbox de concepts douteux pour revue experte.

---

## Sprint 5 — Gamification sobre

Objectif : améliorer la rétention.

- [ ] Ajouter badges pédagogiques.
- [ ] Ajouter streak léger.
- [ ] Ajouter niveaux par thème.
- [ ] Ajouter objectifs quotidiens ou hebdomadaires.
- [ ] Ajouter déblocage progressif.
- [ ] Éviter leaderboard public initialement.
- [ ] Éviter score compétitif brut.

---

## 16. Roadmap produit

### V0 actuelle

- Banque de cas ;
- réponse libre ;
- correction IA ;
- QCM disponible ;
- interface opérationnelle.

### V1 engagement

- accueil orienté action ;
- ECG du jour ;
- parcours ;
- thèmes ;
- progression ;
- cas suivant recommandé.

### V2 pédagogie

- score explicite ;
- feedback structuré ;
- concepts trouvés/manqués ;
- recommandations ciblées ;
- fiches de révision.

### V3 collecte intelligente

- randomisation pondérée ;
- tracking d’usage ;
- séparation aide/sans aide ;
- export recherche.

### V4 aide à l’écriture

- concepts détectés ;
- validation par clic ;
- crosswalk DALL-E ;
- inbox de correction ;
- amélioration continue.

### V5 autonomie / personnalisation

- adaptation au niveau ;
- parcours individualisé ;
- modèles locaux ;
- feedback calibré ;
- recommandation de cas selon erreurs.

---

## 17. Principe directeur

L’app doit devenir moins :

> “banque de cas + correction”

et plus :

> “parcours d’entraînement ECG avec feedback, progression et recommandation.”

Le QCM doit être une aide, pas la porte d’entrée.

La liste des 75 cas doit cesser d’être l’interface principale.

La correction doit recommander le prochain cas.

Le score doit être expliqué par concepts.

La gamification doit soutenir la compétence, pas créer une compétition.

Le bon modèle mental est proche de :

> Duolingo pour ECG, mais avec une sobriété médicale.

C’est-à-dire :

- progression ;
- séries ;
- feedback immédiat ;
- thèmes ;
- niveaux ;
- relance douce ;
- réponse libre au centre ;
- correction traçable ;
- données exploitables.

---

## 18. Phrase de synthèse

L’objectif UX d’ECG Online n’est pas seulement de faciliter la saisie d’interprétations ECG. Il est de transformer la lecture ECG en une boucle d’apprentissage courte, répétable et gratifiante, où chaque réponse libre produit un feedback compréhensible, une progression mesurable, et une donnée exploitable pour améliorer le moteur neuro-symbolique.
