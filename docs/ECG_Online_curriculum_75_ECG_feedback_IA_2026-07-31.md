# ECG Online — Curriculum complet de 75 ECG et architecture de feedback pédagogique assisté par IA

**Version :** 1.0  
**Date :** 31 juillet 2026  
**Projet :** ECG Online  
**Objet :** reconstruire les parcours pédagogiques afin de couvrir les 75 ECG, limiter les inégalités d’exposition et utiliser l’IA comme moteur de feedback, de remédiation et de réactivation.

---

## 1. Résumé exécutif

La banque d’ECG Online contient 75 cas. L’application dispose actuellement de cinq micro-parcours :

1. blocs auriculoventriculaires ;
2. fibrillation atriale et flutter ;
3. tachycardies régulières à QRS fins ;
4. QRS larges en rythme sinusal ;
5. tachycardies à QRS larges.

Ces parcours utilisent 29 positions pédagogiques, mais seulement 26 ECG distincts. Les cas 37, 39 et 42 sont réutilisés dans plusieurs parcours, tandis que 49 ECG ne sont présents dans aucun parcours. La mécanique actuelle crée donc une exposition très inégale : certains tracés sont vus dans la banque libre et dans plusieurs modules, tandis que les deux tiers de la banque ne bénéficient d’aucune scénarisation pédagogique.

La proposition retenue est de remplacer cette organisation partielle par :

- **15 parcours fondamentaux de 5 ECG**, couvrant exactement les cas 1 à 75 ;
- **aucune répétition fixe d’un ECG dans le curriculum principal** ;
- une progression en cinq temps : **fondation, guidage, contraste, intégration, maîtrise** ;
- des séances ultérieures de **réactivation intercalée et adaptative**, qui choisissent les ECG selon l’historique individuel ;
- un feedback IA fondé sur l’ontologie et le score déterministe existants, enrichi par des fonctions de feedback sur la tâche, le raisonnement et l’autorégulation ;
- une séparation nette entre :
  - le **moteur de mesure**, qui doit rester aussi déterministe et auditable que possible ;
  - le **moteur narratif**, qui reformule les résultats en feedback pédagogique ;
  - le **moteur d’adaptation**, qui choisit le cas suivant et le niveau d’aide.

La couverture des 75 cas ne doit pas être confondue avec la maîtrise. Un étudiant peut avoir rencontré 75 ECG sans avoir consolidé les compétences correspondantes. L’interface doit donc afficher séparément :

- la **couverture** : ECG distincts rencontrés ;
- la **maîtrise** : compétences validées sans aide ;
- la **rétention** : compétences revalidées après espacement ;
- la **calibration** : adéquation entre confiance déclarée et performance.

---

## 2. Audit du dispositif actuel

### 2.1. Les cinq parcours existants

Les parcours actuellement déclarés dans `frontend/pathways.json` sont organisés en trois niveaux :

- fondamentaux ;
- orientation ;
- intégration.

Ils utilisent les cas suivants :

| Parcours actuel | Cas principaux | Remédiation |
|---|---:|---:|
| Blocs auriculoventriculaires | 23, 24, 25, 26, 28 | 29 |
| FA et flutter | 37, 39, 42, 41 | 38 |
| Tachycardies à QRS fins | 37, 42, 43, 44, 40 | 39 |
| QRS larges en rythme sinusal | 8, 9, 13, 10, 14 | 15 |
| Tachycardies à QRS larges | 49, 45, 47, 46, 48 | 35 |

Conséquences :

- 29 utilisations ;
- 26 ECG distincts ;
- 3 ECG employés deux fois : 37, 39 et 42 ;
- 49 ECG absents de tout parcours.

### 2.2. Ce qui fonctionne déjà

Les parcours existants possèdent plusieurs qualités qu’il faut conserver :

- engagement par une première réponse libre ;
- verrouillage de cette première réponse avant l’accès aux indices ;
- indices gradués ;
- distinction entre entraînement guidé et test de maîtrise ;
- remédiation après un test non validé ;
- collecte de la confiance et des données temporelles ;
- correction fondée sur des critères validants et complémentaires ;
- moteur neurosymbolique avec scoring ontologique déterministe ;
- possibilité de repli vers un correcteur génératif.

La reconstruction proposée ne remplace donc pas la mécanique technique. Elle élargit son périmètre, clarifie ses règles pédagogiques et évite que la progression dépende de quelques ECG privilégiés.

### 2.3. Limites pédagogiques identifiées

1. **Couverture incomplète.**  
   Les modules ne balayent qu’environ un tiers de la banque.

2. **Réutilisations non contrôlées.**  
   Les cas 37, 39 et 42 servent dans plusieurs apprentissages, ce qui renforce leur exposition indépendamment des besoins de l’étudiant.

3. **Confusion possible entre thème et compétence.**  
   Un thème tel que « FA/flutter » décrit une famille diagnostique. Une compétence doit être formulée comme une action observable : identifier l’organisation atriale, distinguer une irrégularité anarchique d’une variation sinusale, ou interpréter l’effet d’un bloc nodal transitoire.

4. **Remédiation trop liée à un seul cas.**  
   Une remédiation fixe peut être mémorisée. Elle ne permet pas toujours de savoir si l’étudiant a corrigé son modèle mental ou seulement reconnu le tracé.

5. **Absence de curriculum global.**  
   Les cinq parcours sont de bons micro-parcours, mais ne forment pas encore une trajectoire couvrant les prérequis, les pièges, les urgences et la rétention.

---

## 3. Principes pédagogiques retenus

## 3.1. Produire avant de recevoir de l’aide

Chaque ECG commence par une production autonome :

1. interprétation libre structurée ;
2. niveau de confiance ;
3. validation irréversible de la première lecture ;
4. accès éventuel à une aide ;
5. réponse finale séparée.

Cette séquence évite que l’indice transforme une tâche de rappel en tâche de reconnaissance. Elle permet aussi de mesurer :

- la compétence autonome ;
- l’effet de l’aide ;
- la capacité de révision ;
- la sensibilité à l’automatisation.

## 3.2. Retrieval practice et pratique distribuée

Le fait de devoir récupérer une connaissance ou une stratégie en mémoire améliore généralement davantage la rétention qu’une nouvelle exposition passive. La littérature en formation des professionnels de santé retrouve un bénéfice fréquent de la pratique de récupération et de l’espacement, même si les interventions sont hétérogènes.

Conséquences pour ECG Online :

- ne pas présenter immédiatement le corrigé ;
- réutiliser les **compétences**, mais pas nécessairement le même ECG ;
- revalider à distance ;
- mélanger progressivement les diagnostics ;
- éviter la répétition immédiate en boucle du même cas.

## 3.3. Interleaving et discrimination

La reconnaissance experte ne dépend pas seulement de la connaissance d’un prototype. Elle dépend de la capacité à distinguer des diagnostics proches.

Chaque parcours contient donc au moins un cas de contraste :

- ECG normal versus anomalie ;
- artéfact versus arythmie ;
- pause sinusale versus BAV ;
- Mobitz I versus Mobitz II ;
- FA lente versus FA avec BAV complet ;
- flutter 2/1 versus tachycardie jonctionnelle ;
- TV versus TSV avec aberration ou préexcitation ;
- péricardite versus SCA ST+ ;
- Brugada versus ischémie antérieure ;
- hyperkaliémie versus bloc intraventriculaire.

Le feedback doit expliciter **le critère discriminant**, pas seulement donner l’étiquette finale.

## 3.4. Scaffolding puis fading

Les aides doivent diminuer avec la progression :

- **fondation** : plan de lecture explicite et indices disponibles ;
- **guidage** : questionnement focalisé ;
- **contraste** : indices moins directifs ;
- **intégration** : aucune aide avant une première conclusion complète ;
- **maîtrise** : aucun indice avant correction.

La disparition progressive de l’aide est une propriété du parcours, et non une décision improvisée du modèle génératif.

## 3.5. Mastery learning

La validation d’un parcours ne doit pas reposer uniquement sur un score global. Elle nécessite :

- un seuil de score ;
- la présence de concepts indispensables ;
- l’absence d’erreur dangereuse ;
- une réponse autonome ;
- idéalement une revalidation différée.

Exemple : reconnaître « tachycardie à QRS larges » sans identifier la dissociation atrioventriculaire ou la capture ne suffit pas à valider la compétence « certifier une TV ».

## 3.6. Feedback à trois niveaux

Le feedback doit répondre à trois questions :

- **Où vais-je ?** Quel était l’objectif de la tâche ?
- **Où en suis-je ?** Qu’ai-je correctement identifié ou omis ?
- **Quelle est l’étape suivante ?** Que dois-je regarder ou faire au prochain ECG ?

Il doit couvrir trois niveaux utiles :

1. **Tâche** : exactitude des observations et du diagnostic ;
2. **Processus** : qualité de la stratégie de lecture et du raisonnement discriminant ;
3. **Autorégulation** : confiance, usage des indices, révision et plan de progression.

Le feedback centré sur la personne (« excellent », « tu es mauvais en conduction ») apporte peu d’information opérationnelle et doit être évité.

---

## 4. Architecture générale du curriculum

## 4.1. Quinze parcours, cinq ECG par parcours

Chaque parcours utilise cinq cas distincts :

| Phase | Fonction |
|---|---|
| Fondation | Introduire la représentation mentale et le vocabulaire |
| Guidage | Appliquer la stratégie avec questionnement progressif |
| Contraste | Distinguer une situation voisine ou un piège |
| Intégration | Combiner plusieurs dimensions de lecture |
| Maîtrise | Réponse autonome sans indice |

Les 75 cas sont utilisés une fois dans le curriculum principal. Les répétitions apparaissent uniquement dans les séances adaptatives ultérieures.

## 4.2. Niveaux

### Niveau A — Construire la lecture

- parcours 1 à 3 ;
- qualité, normalité, ondes P, voltages, axe, QRS ;
- objectif : acquérir une procédure stable.

### Niveau B — Rythme et conduction

- parcours 4 à 9 ;
- dysfonction sinusale, BAV, extrasystoles, FA, flutter et tachycardies régulières ;
- objectif : analyser l’activité atriale et sa relation avec les QRS.

### Niveau C — Urgences rythmiques et QRS larges

- parcours 10 et 11 ;
- TV, préexcitation, polymorphisme, embolie pulmonaire et péricardite ;
- objectif : sécuriser le premier tri et reconnaître les signes décisifs.

### Niveau D — Ischémie, repolarisation et situations intégratives

- parcours 12 à 15 ;
- SCA, complications, séquelles, troubles métaboliques, canalopathies et cardiomyopathies ;
- objectif : intégrer topographie, temporalité, contexte et diagnostics différentiels.

---

# 5. Les quinze parcours proposés

> Les intitulés ci-dessous reposent sur les diagnostics et points clés présents dans `data/cases.json`, `data/cases_reference.json` et `data/cases_golden.json`. Avant mise en production, chaque objectif et chaque indice doit faire l’objet d’une validation clinique finale dans l’interface de curation.

## Parcours 1 — Vérifier le tracé et reconnaître la normalité

**Cas : 1 à 5**

| Phase | Cas | Fonction pédagogique |
|---|---:|---|
| Fondation | 3 | Appliquer une lecture systématique et savoir conclure à un ECG normal |
| Guidage | 1 | Reconnaître une inversion des électrodes des bras |
| Contraste | 2 | Distinguer un artéfact de tremblement d’une arythmie atriale |
| Intégration | 4 | Identifier une hypertrophie atriale gauche à partir de l’onde P |
| Maîtrise | 5 | Identifier une hypertrophie atriale droite et ses signes associés |

**Objectifs**

- vérifier la qualité et la cohérence technique avant toute interprétation ;
- utiliser un plan stable de lecture ;
- ne pas transformer une anomalie technique en diagnostic ;
- analyser la durée, l’amplitude et la morphologie de l’onde P ;
- accepter la conclusion « ECG normal » lorsque tous les critères sont réunis.

**Erreur pivot à remédier**

> « Toute ligne de base ondulante est une FA » ou « toute anomalie de DI est pathologique ».

**Feedback IA prioritaire**

- indiquer les dérivations qui contredisent l’hypothèse erronée ;
- demander si l’anomalie est cohérente dans toutes les dérivations ;
- distinguer observation, interprétation et conclusion.

---

## Parcours 2 — Voltages, hypertrophies et premières morphologies de conduction

**Cas : 6 à 10**

| Phase | Cas | Fonction pédagogique |
|---|---:|---|
| Fondation | 6 | Reconnaître une hypertrophie ventriculaire gauche électrique |
| Guidage | 7 | Approfondir axe/voltage ou une variante d’hypertrophie de la banque |
| Contraste | 8 | Comparer l’activation ventriculaire normale à un QRS large |
| Intégration | 9 | Reconnaître un bloc de branche droit complet |
| Maîtrise | 10 | Associer BBD, axe gauche et PR long sans conclure abusivement à un « trifasciculaire » |

**Objectifs**

- séparer durée, voltage, axe et morphologie ;
- utiliser V1, DI et V6 comme dérivations pivots ;
- reconnaître le BBD complet ;
- comprendre la notion de bloc bifasciculaire ;
- ne pas confondre association ECG et localisation certaine des ralentissements.

---

## Parcours 3 — QRS larges en rythme sinusal : classer sans surclasser

**Cas : 11 à 15**

| Phase | Cas | Fonction pédagogique |
|---|---:|---|
| Fondation | 13 | Reconnaître un bloc de branche gauche complet |
| Guidage | 11 | Réexaminer un bloc bifasciculaire en contexte clinique |
| Contraste | 12 | BBD complet associé à une surcharge/hypertrophie droite |
| Intégration | 15 | Décrire un bloc intraventriculaire aspécifique |
| Maîtrise | 14 | Reconnaître l’alternance de morphologies de branche et sa gravité |

**Objectifs**

- reconnaître BBD et BBG complets ;
- intégrer l’axe sans perdre l’analyse morphologique ;
- savoir conclure « trouble de conduction intraventriculaire aspécifique » ;
- reconnaître un bloc alternant ;
- hiérarchiser le risque clinique.

**Critère de maîtrise obligatoire**

La réponse au cas 14 doit contenir une notion d’**alternance BBD–BBG** ou de **bloc de branche alternant**, et identifier la sévérité conductrice.

---

## Parcours 4 — Bradycardies et dysfonction sinusale

**Cas : 16 à 20**

| Phase | Cas | Fonction pédagogique |
|---|---:|---|
| Fondation | 16 | Identifier une bradycardie et rechercher son mécanisme |
| Guidage | 17 | Distinguer variation physiologique et dysfonction |
| Contraste | 18 | Analyser une situation de ralentissement ou de pause |
| Intégration | 19 | Croiser rythme, activité atriale et contexte |
| Maîtrise | 20 | Diagnostiquer une pause sinusale et l’opposer à un BAV paroxystique |

**Objectifs**

- ne pas appeler « bradycardie sinusale » tout rythme lent ;
- chercher l’activité atriale pendant les pauses ;
- distinguer absence d’ondes P et ondes P bloquées ;
- caractériser un échappement ;
- relier ECG, symptômes et urgence.

**Feedback discriminant**

- « Pendant la pause, vois-tu des ondes P qui continuent ? »
- « Le problème vient-il de la formation de l’influx ou de sa transmission aux ventricules ? »

---

## Parcours 5 — Échappements, stimulation et premiers BAV

**Cas : 21 à 25**

| Phase | Cas | Fonction pédagogique |
|---|---:|---|
| Fondation | 21 | Dysfonction sinusale avec échappement jonctionnel et conduction rétrograde |
| Guidage | 22 | Lire un stimulateur double chambre avec stimulation atriale et QRS natifs |
| Contraste | 23 | BAV du premier degré : ralentissement sans onde P bloquée |
| Intégration | 24 | BAV Mobitz I : dynamique progressive du PR |
| Maîtrise | 25 | BAV Mobitz II : blocage inopiné avec PR conduits constants |

**Objectifs**

- localiser approximativement un échappement par fréquence et largeur des QRS ;
- analyser séparément stimulation atriale et ventriculaire ;
- distinguer BAV I, Mobitz I et Mobitz II ;
- utiliser la dynamique du PR plutôt qu’une photographie isolée ;
- intégrer la largeur des QRS au niveau de risque.

---

## Parcours 6 — BAV avancés et dissociation atrioventriculaire

**Cas : 26 à 30**

| Phase | Cas | Fonction pédagogique |
|---|---:|---|
| Fondation | 26 | Décrire un BAV 2/1 sans imposer Mobitz I ou II |
| Guidage | 27 | Reconnaître un BAV de haut degré sur hyperkaliémie |
| Contraste | 28 | BAV complet avec échappement jonctionnel |
| Intégration | 29 | BAV complet avec échappement plus distal ou plus instable |
| Maîtrise | 30 | Distinguer FA lente et FA associée à un BAV complet |

**Objectifs**

- décrire le rapport de conduction ;
- reconnaître plusieurs ondes P consécutives bloquées ;
- identifier une dissociation atrioventriculaire ;
- caractériser l’échappement ;
- utiliser la régularité ventriculaire dans une FA pour suspecter un BAV complet ;
- rechercher une cause réversible, notamment métabolique.

**Critère de sécurité**

Toute confusion entre FA lente irrégulière et FA avec rythme ventriculaire parfaitement régulier doit déclencher une remédiation obligatoire.

---

## Parcours 7 — Extrasystoles et séquences ventriculaires

**Cas : 31 à 35**

| Phase | Cas | Fonction pédagogique |
|---|---:|---|
| Fondation | 32 | Reconnaître une extrasystole ventriculaire |
| Guidage | 33 | Caractériser répétitivité, morphologie et repos compensateur |
| Contraste | 34 | Distinguer extrasystole atriale et ventriculaire |
| Intégration | 31 | Reconnaître un syndrome bradycardie–tachycardie |
| Maîtrise | 35 | Diagnostiquer une tachycardie ventriculaire non soutenue |

**Objectifs**

- identifier la prématurité ;
- analyser largeur et morphologie du QRS prématuré ;
- rechercher une onde P prématurée ;
- distinguer repos compensateur complet ou incomplet ;
- reconnaître doublets, triplets et salves ;
- définir le caractère non soutenu.

---

## Parcours 8 — De l’irrégularité sinusale à la fibrillation atriale

**Cas : 36 à 40**

| Phase | Cas | Fonction pédagogique |
|---|---:|---|
| Fondation | 39 | Reconnaître une arythmie sinusale respiratoire physiologique |
| Guidage | 37 | Identifier une fibrillation atriale typique |
| Contraste | 38 | Reconnaître une FA à réponse ventriculaire lente |
| Intégration | 36 | Identifier une extrasystole ventriculaire à couplage court et phénomène R sur T |
| Maîtrise | 40 | Reconnaître une tachycardie sinusale réactionnelle |

**Objectifs**

- distinguer irrégularité progressive et irrégularité anarchique ;
- rechercher des ondes P répétitives ;
- ne pas confondre vitesse ventriculaire et organisation atriale ;
- identifier un marqueur de gravité ventriculaire ;
- reconnaître la commande sinusale dans une tachycardie.

**Révision de la version actuelle**

Les cas 37 et 39 ne doivent plus être réemployés comme étapes fixes dans le parcours des tachycardies à QRS fins. Les compétences qu’ils enseignent seront réactivées avec des cas nouveaux ou des questions de transfert.

---

## Parcours 9 — Flutter et tachycardies régulières à QRS fins

**Cas : 41 à 45**

| Phase | Cas | Fonction pédagogique |
|---|---:|---|
| Fondation | 41 | Reconnaître le flutter commun typique et sa morphologie atriale |
| Guidage | 42 | Flutter rapide 2/1 démasqué par ralentissement nodal |
| Contraste | 43 | Tachycardie orthodromique sur voie accessoire |
| Intégration | 44 | Tachycardie par réentrée intranodale |
| Maîtrise | 45 | Tachycardie régulière large révélant un flutter avec aberration fixe |

**Objectifs**

- construire le différentiel d’une tachycardie régulière ;
- analyser largeur des QRS, régularité et activité atriale ;
- comprendre ce qu’une manœuvre vagale ou un bloqueur nodal démontre réellement ;
- ne pas suraffirmer AVNRT versus AVRT sur le seul ECG initial ;
- reconnaître qu’un flutter peut se présenter avec des QRS larges.

**Feedback de processus**

Le moteur doit évaluer si l’étudiant :

1. commence par régularité et largeur ;
2. recherche l’activité atriale ;
3. formule plusieurs hypothèses compatibles ;
4. utilise le tracé après manœuvre comme information supplémentaire.

---

## Parcours 10 — Tachycardies à QRS larges : sécuriser le diagnostic

**Cas : 46 à 50**

| Phase | Cas | Fonction pédagogique |
|---|---:|---|
| Fondation | 49 | FA avec bloc de branche : irrégulière, large, monomorphe |
| Guidage | 46 | Tachycardie antidromique ou préexcitation comme diagnostic différentiel |
| Contraste | 47 | TV très probable sur cardiopathie structurelle |
| Intégration | 50 | Tachycardie polymorphe/torsade ou autre forme complexe de la banque |
| Maîtrise | 48 | Certifier une TV par dissociation AV et capture |

**Objectifs**

- trier régulier/irrégulier et mono-/polymorphe ;
- considérer une tachycardie régulière large comme une TV jusqu’à preuve solide du contraire ;
- reconnaître le poids du terrain ;
- rechercher capture, fusion et dissociation ;
- distinguer diagnostic probable et diagnostic certain.

**Critère de maîtrise obligatoire**

Le cas 48 n’est validé que si la réponse mentionne au moins un signe certain : **dissociation atrioventriculaire** ou **complexe de capture**.

---

## Parcours 11 — Préexcitation, urgences différentielles et inflammation

**Cas : 51 à 55**

| Phase | Cas | Fonction pédagogique |
|---|---:|---|
| Fondation | 51 | Reconnaître une préexcitation en rythme sinusal ou son expression clinique |
| Guidage | 52 | Diagnostiquer une FA préexcitée à conduction rapide (« WPW malin ») |
| Contraste | 53 | Reconnaître les signes ECG possibles d’embolie pulmonaire |
| Intégration | 54 | Intégrer les signes de cœur pulmonaire aigu dans une EP massive |
| Maîtrise | 55 | Distinguer une péricardite aiguë d’un SCA ST+ |

**Objectifs**

- reconnaître PR court, onde delta et QRS élargi ;
- identifier une FA préexcitée irrégulière, large et polymorphe ;
- éviter les bloqueurs nodaux inappropriés dans ce contexte ;
- interpréter l’ECG d’EP comme un ensemble peu sensible et peu spécifique ;
- reconnaître le caractère diffus du sus-ST et les anomalies du segment PR dans la péricardite.

---

## Parcours 12 — Repolarisation et ischémie : apprendre la topographie

**Cas : 56 à 60**

| Phase | Cas | Fonction pédagogique |
|---|---:|---|
| Fondation | 56 | Identifier une anomalie élémentaire de repolarisation |
| Guidage | 57 | Distinguer sus-décalage, sous-décalage et ondes T |
| Contraste | 58 | Opposer variante/non-coronarien et ischémie systématisée |
| Intégration | 59 | Localiser un syndrome coronarien à partir des dérivations |
| Maîtrise | 60 | Reconnaître un SCA inférieur associé à une dysfonction sinusale/échappement |

**Objectifs**

- décrire avant d’étiqueter ;
- identifier le territoire ;
- rechercher un miroir ;
- analyser les ondes Q ;
- intégrer rythme et conduction aux anomalies ischémiques ;
- demander des dérivations complémentaires lorsque nécessaire.

---

## Parcours 13 — SCA ST+ et complications immédiates

**Cas : 61 à 65**

| Phase | Cas | Fonction pédagogique |
|---|---:|---|
| Fondation | 61 | SCA inférieur avec extension droite et postérieure |
| Guidage | 62 | SCA antérieur sur bloc de branche gauche |
| Contraste | 64 | Rythme idioventriculaire accéléré de reperfusion versus TV |
| Intégration | 63 | SCA antérieur compliqué de fibrillation ventriculaire |
| Maîtrise | 65 | SCA inférieur compliqué d’un BAV de haut degré |

**Objectifs**

- utiliser les dérivations droites et postérieures ;
- reconnaître une ischémie aiguë malgré un trouble de conduction ;
- identifier un RIVA de reperfusion ;
- reconnaître une fibrillation ventriculaire ;
- intégrer les complications conductives des infarctus inférieurs.

---

## Parcours 14 — Ischémie complexe, séquelles et mécanismes transitoires

**Cas : 66 à 70**

| Phase | Cas | Fonction pédagogique |
|---|---:|---|
| Fondation | 66 | SCA sans sus-décalage : sous-ST/ondes T et contexte |
| Guidage | 67 | Ischémie ou séquelle nécessitant intégration temporelle |
| Contraste | 68 | Ischémie diffuse sévère avec sus-ST en aVR/V1 |
| Intégration | 69 | Anévrisme ventriculaire sur séquelle de nécrose |
| Maîtrise | 70 | Angor de Prinzmetal avec sus-ST inférieur transitoire |

**Objectifs**

- distinguer lésion aiguë, ischémie sous-endocardique et séquelle ;
- interpréter le sus-ST en aVR dans son contexte global ;
- ne pas prendre un sus-ST persistant de séquelle pour un SCA aigu sans intégrer la clinique ;
- reconnaître la valeur de la régression sous dérivé nitré ;
- gérer la temporalité et la comparaison de tracés.

---

## Parcours 15 — Diagnostics intégratifs : cardiomyopathies, métabolisme et canalopathies

**Cas : 71 à 75**

| Phase | Cas | Fonction pédagogique |
|---|---:|---|
| Fondation | 71 | Reconnaître un tableau compatible avec un Takotsubo |
| Guidage | 72 | Intégrer un diagnostic de repolarisation/cardiomyopathie de la banque |
| Contraste | 73 | Hyperkaliémie menaçante avec QRS très élargis et T pointues |
| Intégration | 74 | Syndrome de Brugada et diagnostic différentiel du sus-ST antérieur |
| Maîtrise | 75 | Amylose cardiaque : microvoltage, pseudo-nécrose et discordance structure–voltage |

**Objectifs**

- reconnaître les limites de la spécificité ECG ;
- intégrer contexte, topographie et dynamique ;
- distinguer hyperkaliémie, trouble de branche et tachyarythmie ;
- reconnaître un aspect de Brugada de type 1 ;
- utiliser la discordance entre épaisseur myocardique et voltage dans l’amylose.

---

# 6. Relecture critique du curriculum

## 6.1. Pourquoi une répartition stricte par groupes de cinq est acceptable ici

La numérotation de la banque suit déjà une organisation clinique relativement cohérente. Une répartition par blocs consécutifs :

- facilite la migration technique ;
- garantit la couverture intégrale ;
- conserve les associations de tracés complémentaires ;
- limite les erreurs de correspondance entre images et objectifs ;
- rend le curriculum auditable.

Cette organisation ne doit cependant pas conduire à une succession purement catégorielle. À l’intérieur de chaque parcours, l’ordre pédagogique peut différer de l’ordre numérique, comme proposé ci-dessus.

## 6.2. Risque de cloisonnement thématique

Si tous les cas d’un même module appartiennent à la même famille, l’étudiant peut utiliser le titre du parcours comme indice diagnostique.

Mesures correctrices :

- masquer le diagnostic précis du cas ;
- utiliser des titres de parcours centrés sur une **compétence**, pas une maladie ;
- introduire un cas de contraste hors du prototype principal ;
- réaliser les tests de rétention dans des séries mixtes ;
- utiliser un mode « challenge intercalé » sans annonce du thème.

## 6.3. Risque de mémorisation du cas de maîtrise

Un même cas fixe peut devenir reconnaissable.

Mesures :

- conserver un cas fixe pour le déploiement initial et la comparabilité ;
- créer ensuite un **pool de maîtrise équivalent** ;
- ne jamais utiliser le cas de fondation comme test final ;
- exiger une revalidation différée sur un autre ECG ;
- suivre le nombre d’expositions au niveau individuel.

## 6.4. Risque de sur-assistance par l’IA

Un tuteur génératif peut :

- dévoiler trop tôt le diagnostic ;
- remplacer l’effort de récupération ;
- produire un commentaire plausible mais incorrect ;
- renforcer une réponse erronée ;
- créer une dépendance à l’aide.

Mesures :

- verrouiller la réponse initiale ;
- limiter les indices à des gabarits validés ;
- dériver le contenu factuel du score ontologique et de la référence ;
- ne laisser le LLM que reformuler ou sélectionner des messages autorisés ;
- journaliser les concepts utilisés ;
- prévoir un mode sans aide ;
- évaluer la rétention sans IA.

## 6.5. Place du travail EMNLP 2024 discuté dans le projet

L’article de Naguib, Tannier et Névéol ne traite pas directement de pédagogie. Il compare des modèles génératifs auto-régressifs et des modèles masqués pour la reconnaissance d’entités cliniques en anglais, français et espagnol. Les modèles masqués plus légers y surpassent le prompting génératif dans le domaine clinique.

Implication pour ECG Online :

- ne pas confondre la qualité d’un texte généré avec la fiabilité de l’extraction conceptuelle ;
- conserver une architecture hybride ;
- tester séparément :
  - extraction des concepts ;
  - jugement de présence/absence ;
  - scoring ;
  - formulation du feedback ;
- envisager à terme un extracteur clinique spécialisé ou fine-tuné pour la couche NER ;
- ne pas demander au même LLM de produire la mesure, la note et l’explication sans contrôle.

L’article soutient donc surtout la **séparation des responsabilités du système**, pas une méthode d’enseignement particulière.

---

# 7. Architecture du feedback pédagogique assisté par IA

## 7.1. Pipeline proposé

```text
Réponse libre de l’étudiant
        │
        ▼
Normalisation linguistique
        │
        ▼
Extraction des concepts ECG
        │
        ▼
Recherche / alignement ontologique
        │
        ▼
Jugement déterministe ou contrôlé
présent · absent · contradictoire · incertain
        │
        ▼
Score par critères validants
+ détection des erreurs dangereuses
        │
        ├──────────────► Profil longitudinal de compétence
        │
        ▼
Plan de feedback structuré
tâche · processus · autorégulation
        │
        ▼
Réalisation narrative contrôlée par LLM
        │
        ▼
Choix adaptatif du prochain ECG
```

## 7.2. Ce qui doit rester déterministe

- liste des critères validants ;
- poids des critères ;
- concepts indispensables ;
- exclusions mutuelles ;
- erreurs dangereuses ;
- seuil de validation ;
- règles de déblocage des indices ;
- règles de sélection des cas ;
- calcul de couverture et de maîtrise.

## 7.3. Ce que le LLM peut faire

- reformuler un feedback dans un français naturel ;
- adapter la longueur au niveau de l’étudiant ;
- relier une omission au prochain geste de lecture ;
- générer une question socratique à partir d’un gabarit ;
- résumer les erreurs récurrentes ;
- proposer un plan de révision ;
- produire plusieurs formulations équivalentes sans changer le contenu factuel.

## 7.4. Ce que le LLM ne doit pas décider seul

- la vérité de référence ;
- la note ;
- la présence d’une erreur de sécurité ;
- la validation définitive d’un module ;
- le diagnostic d’un ECG non curé ;
- la sélection d’un contenu non validé dans une situation à risque.

---

# 8. Format de feedback recommandé

## 8.1. Feedback immédiat après une réponse

### 1. Synthèse

> **Orientation correcte / partiellement correcte / incorrecte.**  
> Tu as correctement identifié X. Le point qui manque pour sécuriser la conclusion est Y.

### 2. Ce qui est objectivement présent

Deux à quatre éléments maximum :

- rythme/régularité ;
- activité atriale ;
- relation P–QRS ;
- durée/morphologie des QRS ;
- anomalie ST–T ;
- diagnostic ou niveau d’urgence.

### 3. Critère discriminant

> Le diagnostic repose ici surtout sur **[critère]**, car **[raison courte]**.

### 4. Analyse du raisonnement

> Tu as commencé par [bonne stratégie]. En revanche, tu as conclu avant d’avoir vérifié [étape manquante].

### 5. Action suivante

> Au prochain tracé lent, cherche d’abord si des ondes P continuent pendant la pause avant de choisir entre dysfonction sinusale et BAV.

### 6. Calibration

> Confiance élevée avec réponse incorrecte : revalidation nécessaire sans indice.  
> Confiance faible avec réponse correcte : proposer un cas proche pour consolider et recalibrer.

## 8.2. Feedback après utilisation d’indices

Le système doit comparer la première et la seconde réponse :

- concepts ajoutés ;
- concepts retirés ;
- diagnostic révisé ;
- éléments de l’indice recopiés ;
- amélioration réelle du raisonnement.

Exemple :

> L’indice t’a permis de rechercher les ondes P bloquées et de corriger le mécanisme. La conclusion finale est correcte. La compétence n’est toutefois pas encore validée de façon autonome ; elle sera retestée sur un autre ECG.

## 8.3. Feedback en cas de réponse dangereuse

Le ton doit être direct, non humiliant et centré sur l’action :

> Cette interprétation pourrait conduire à une prise en charge inadaptée. Devant une tachycardie régulière à QRS larges sur cardiopathie structurelle, la conduite sûre est de considérer une TV jusqu’à preuve solide du contraire. Reprends maintenant la recherche de dissociation AV, capture et fusion.

Le feedback de sécurité ne doit pas être dilué dans un commentaire général.

---

# 9. Moteur adaptatif de sélection des ECG

## 9.1. Variables individuelles

Pour chaque couple étudiant–ECG :

- nombre d’expositions ;
- date de dernière exposition ;
- score autonome ;
- score final après indices ;
- nombre d’indices ;
- confiance ;
- temps actif ;
- erreurs dangereuses ;
- concepts manquants ;
- répétition exacte d’un texte d’indice ;
- statut de maîtrise.

Pour chaque compétence :

- nombre de cas différents réussis ;
- taux de réussite sans aide ;
- délai depuis dernière réussite ;
- calibration moyenne ;
- stabilité inter-cas ;
- besoin de réactivation.

## 9.2. Priorité du prochain cas

Exemple de fonction :

```text
priorité =
  + nouveauté du cas
  + compétence en retard
  + délai depuis dernière exposition
  + erreur dangereuse antérieure
  + faible calibration
  + besoin de transfert
  - nombre d’expositions récentes
  - répétition du même diagnostic
  - utilisation récente d’un cas très similaire
```

## 9.3. Règles minimales

1. Pendant le curriculum principal, présenter chaque cas au maximum une fois.
2. Après les 15 parcours, sélectionner en priorité les ECG :
   - jamais vus ;
   - échoués sans aide ;
   - associés à une erreur dangereuse ;
   - appartenant à une compétence non revalidée.
3. Ne pas présenter deux cas quasi identiques consécutivement, sauf remédiation volontaire.
4. Une réussite après trois indices ne vaut pas une maîtrise autonome.
5. Une compétence doit être démontrée sur au moins deux cas distincts, dont un différé.
6. Un score élevé avec faible confiance déclenche une consolidation, pas une reprise complète.
7. Un score faible avec forte confiance déclenche une remédiation et un travail de calibration.

## 9.4. Espacement initial proposé

- première réactivation : 2 à 4 jours ;
- deuxième : 7 à 14 jours ;
- troisième : 30 à 45 jours ;
- réactivation ultérieure : selon performance et enjeu clinique.

Ces intervalles constituent un point de départ produit, non une vérité biologique. Ils devront être ajustés à partir des données d’usage.

---

# 10. Données d’interface à afficher

## Tableau de bord étudiant

```text
Couverture       42 / 75 ECG
Maîtrise         8 / 15 parcours
Rétention        5 / 8 compétences revalidées
Sans indice      71 %
Calibration      à améliorer
À réactiver      BAV avancés · QRS larges · ischémie postérieure
```

## Tableau de bord enseignant

- distribution du nombre de vues par ECG ;
- taux d’exposition des 75 cas ;
- taux de réussite autonome et final ;
- gain après indices ;
- fréquence des erreurs dangereuses ;
- calibration par compétence ;
- concepts le plus souvent omis ;
- ECG anormalement faciles ou difficiles ;
- cas dont le feedback produit beaucoup de révisions sans gain ultérieur ;
- dérive éventuelle entre correcteur déterministe et commentaire narratif.

---

# 11. Schéma de configuration proposé

```json
{
  "id": "bav-advanced",
  "title": "Analyser une dissociation atrioventriculaire",
  "competency_ids": [
    "atrial_activity",
    "p_qrs_relationship",
    "escape_rhythm",
    "safety_bradycardia"
  ],
  "cases": [
    {
      "num": 26,
      "phase": "foundation",
      "objective": "Décrire un rapport de conduction 2/1 sans surclasser le mécanisme.",
      "required_concepts": ["BAV_2_POUR_1"],
      "unsafe_errors": []
    },
    {
      "num": 27,
      "phase": "guided",
      "objective": "Reconnaître un BAV de haut degré et rechercher une cause métabolique.",
      "required_concepts": ["BAV_DE_HAUT_GRADE", "HYPERKALIEMIE"],
      "unsafe_errors": ["FA_LENTE"]
    },
    {
      "num": 28,
      "phase": "contrast",
      "objective": "Identifier une dissociation AV avec échappement jonctionnel.",
      "required_concepts": ["BAV_COMPLET", "DISSOCIATION_ATRIO_VENTRICULAIRE"]
    },
    {
      "num": 29,
      "phase": "integration",
      "objective": "Caractériser un échappement plus distal et son niveau de risque."
    },
    {
      "num": 30,
      "phase": "mastery",
      "objective": "Distinguer FA lente et FA avec BAV complet.",
      "allow_hints": false,
      "required_concepts": ["FIBRILLATION_ATRIALE", "BAV_COMPLET"]
    }
  ],
  "retention": {
    "minimum_distinct_cases": 2,
    "delay_days": [3, 10, 35]
  }
}
```

---

# 12. Plan d’implémentation

## Phase 1 — Audit et couverture

- créer une table `case_curriculum_map.json` ;
- affecter chaque ECG à un parcours et une phase ;
- vérifier automatiquement que les numéros 1 à 75 apparaissent exactement une fois ;
- produire un rapport des doublons et absences ;
- conserver les cinq anciens parcours sous un drapeau de compatibilité pendant la migration.

## Phase 2 — Création des quinze fichiers de parcours

- dupliquer le schéma actuel ;
- rédiger objectifs, points pédagogiques et indices ;
- limiter chaque indice à une action d’observation ;
- intégrer les critères obligatoires et erreurs dangereuses ;
- valider cliniquement les quinze cas de maîtrise.

## Phase 3 — Feedback structuré

- produire un objet `feedback_plan` avant toute génération narrative ;
- séparer :
  - constat ;
  - critère discriminant ;
  - erreur de processus ;
  - prochaine action ;
  - calibration ;
- ajouter des tests unitaires sur les contradictions ;
- vérifier que le diagnostic n’est jamais révélé avant verrouillage.

## Phase 4 — Adaptation et répétition espacée

- créer le profil longitudinal de compétence ;
- enregistrer l’exposition par ECG ;
- mettre en œuvre `least_seen`, `least_recently_seen` et `weakest_competency` ;
- ajouter les séries mixtes ;
- empêcher une nouvelle validation sur le même cas.

## Phase 5 — Évaluation scientifique

### Question principale

Un curriculum adaptatif avec feedback neurosymbolique et narratif améliore-t-il la compétence autonome d’interprétation ECG et sa rétention, comparativement à une banque libre avec correction standard ?

### Dessin possible

- essai randomisé ou stepped-wedge ;
- groupe contrôle : banque libre + feedback standard ;
- intervention : curriculum + feedback structuré + réactivation adaptative ;
- critères :
  - score sur ECG nouveaux ;
  - rétention à 1 mois ;
  - calibration ;
  - temps ;
  - erreurs dangereuses ;
  - couverture de la banque ;
  - dépendance aux indices.

### Point méthodologique essentiel

L’évaluation finale doit utiliser des ECG non vus ou des variantes réellement nouvelles. Une amélioration sur les mêmes 75 cas ne démontrerait pas nécessairement un transfert de compétence.

---

# 13. Indicateurs de qualité avant déploiement

## Curriculum

- [ ] cas 1–75 tous présents ;
- [ ] aucun doublon fixe ;
- [ ] cinq cas par parcours ;
- [ ] un objectif observable par étape ;
- [ ] au moins un contraste par parcours ;
- [ ] cas de maîtrise sans indice ;
- [ ] critères obligatoires définis ;
- [ ] erreurs dangereuses définies.

## Feedback

- [ ] chaque commentaire se fonde sur des concepts scorés ;
- [ ] absence de contradiction entre score et texte ;
- [ ] absence de révélation avant engagement ;
- [ ] distinction tâche/processus/autorégulation ;
- [ ] une action suivante concrète ;
- [ ] longueur limitée ;
- [ ] pas de jugement sur la personne ;
- [ ] traçabilité de la version du modèle et du prompt.

## Adaptation

- [ ] compteur d’exposition par ECG ;
- [ ] sélection des cas les moins vus ;
- [ ] espacement ;
- [ ] revalidation sur cas différent ;
- [ ] prise en compte de la confiance ;
- [ ] gestion spécifique des erreurs dangereuses ;
- [ ] audit de l’équité d’exposition.

---

# 14. Conclusion

La banque de 75 ECG permet de construire un curriculum complet sans ajouter immédiatement de nouveaux tracés. Le principal enjeu n’est pas le volume de contenu mais son orchestration.

La proposition finale repose sur quatre décisions :

1. **les 75 ECG sont intégrés une fois dans 15 parcours principaux de 5 cas** ;
2. **la répétition concerne les compétences et devient adaptative**, plutôt que de réutiliser arbitrairement quelques ECG dans plusieurs modules ;
3. **le feedback IA est structuré par les résultats du moteur ontologique**, et non produit librement à partir de la seule réponse ;
4. **la maîtrise est démontrée sans aide, sur plusieurs cas et après un délai**.

Cette architecture transforme ECG Online d’une banque corrigée par IA en un système d’apprentissage délibéré, longitudinal et scientifiquement évaluable.

---

# Références sélectionnées

1. Naguib M, Tannier X, Névéol A. Few-shot clinical entity recognition in English, French and Spanish: masked language models outperform generative model prompting. *Findings of EMNLP*. 2024:6829–6852. doi:10.18653/v1/2024.findings-emnlp.400.
2. Castro MABC, et al. The Use of Feedback in Improving the Knowledge, Attitudes and Skills of Medical Students: a Systematic Review and Meta-analysis of Randomized Controlled Trials. *Med Sci Educ*. 2021;31:2093–2104. doi:10.1007/s40670-021-01443-3.
3. Brügge E, et al. Large language models improve clinical decision making of medical students through patient simulation and structured feedback: a randomized controlled trial. *BMC Med Educ*. 2024;24:1391. doi:10.1186/s12909-024-06399-7.
4. ChatGPT versus expert feedback on clinical reasoning questions and their effect on learning: a randomized controlled trial. *Postgrad Med J*. 2024. PMID:39656920.
5. Nissen L, et al. A randomised cross-over trial assessing the impact of AI-generated individual feedback on written online assignments for medical students. *Med Teach*. 2025;47:1544–1550. doi:10.1080/0142159X.2025.2451870.
6. Systematic review of distributed practice and retrieval practice in health professions education. PMID:37615780.
7. Fontaine G, et al. Efficacy of adaptive e-learning for health professionals and students: a systematic review and meta-analysis. *BMJ Open*. 2019;9:e025252. doi:10.1136/bmjopen-2018-025252.
8. Compagna K, Ross S, Lee A. An Exploration of Feedback Using Hattie and Timperley’s Feedback Levels. *Fam Med*. 2025;57:508–512. doi:10.22454/FamMed.2025.362243.
9. Hunt EA, et al. Rapid Cycle Deliberate Practice in Medical Education: a Systematic Review. PMID:28540142.
10. AI Use for Medical Students: Impact on Clinical Skill Acquisition and Retention. A Systematic Review. PMID:42006163.

---

## Annexe A — Matrice de couverture

| Parcours | Cas |
|---|---|
| 1 | 1–5 |
| 2 | 6–10 |
| 3 | 11–15 |
| 4 | 16–20 |
| 5 | 21–25 |
| 6 | 26–30 |
| 7 | 31–35 |
| 8 | 36–40 |
| 9 | 41–45 |
| 10 | 46–50 |
| 11 | 51–55 |
| 12 | 56–60 |
| 13 | 61–65 |
| 14 | 66–70 |
| 15 | 71–75 |

**Contrôle de couverture :** 15 × 5 = 75 positions ; chaque numéro 1–75 apparaît une fois.

## Annexe B — Statuts de compétence proposés

- `not_seen`
- `attempted`
- `assisted_success`
- `autonomous_success`
- `mastered`
- `retention_due`
- `retained`
- `unsafe_error`
- `remediation_required`

## Annexe C — Types d’erreurs

- observation manquante ;
- observation incorrecte ;
- relation physiologique incorrecte ;
- diagnostic trop précis ;
- diagnostic insuffisamment précis ;
- contradiction interne ;
- erreur de sécurité ;
- copie d’un indice sans intégration ;
- mauvaise calibration ;
- stratégie de lecture incomplète.
