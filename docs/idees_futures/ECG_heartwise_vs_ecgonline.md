ECG-online vs HeartWise ECG_LLM_Judge

Analyse comparative du lexique, du NER et du matching

Projet : ECG-onlineObjet : Identifier les éléments réutilisables de la méthode HeartWise, clarifier les différences avec l’ontologie ECG-online et définir un plan de comparaison expérimental.Statut : Document de travailDate : 31 juillet 2026

1. Résumé exécutif

La composante de HeartWise qui chevauche ECG-online repose essentiellement sur trois briques :

un lexique ECG normalisé, présenté comme une ontologie ;

un LLM qui convertit un texte libre en une liste de termes canoniques ;

un matching entre la liste issue du texte candidat et celle issue du texte de référence, avec calcul de précision, rappel et F1.

Cette approche est utile et pragmatique, mais elle ne constitue pas une ontologie relationnelle comparable à celle d’ECG-online.

Le fichier HeartWise est principalement organisé comme suit :

catégorie
└── terme canonique
    └── liste de synonymes et formulations équivalentes

À l’inverse, ECG-online décrit des concepts dotés de relations et de propriétés :

concept
├── type
├── catégorie
├── poids
├── parents / enfants
├── requires
├── supports
├── excludes
├── qualificatifs
├── topographies
└── synonymes

La conséquence principale est la suivante :

HeartWise fournit un bon lexique de comptes rendus ECG et une baseline simple d’extraction/matching. ECG-online possède une structure plus adaptée au raisonnement, à la composition des concepts et au scoring pédagogique.

La stratégie recommandée n’est donc pas de remplacer le système ECG-online, mais de :

récupérer les synonymes et formulations utiles de HeartWise ;

reproduire leur méthode comme baseline ;

intégrer certaines bonnes pratiques techniques ;

comparer leur pipeline au pipeline actuel ;

développer un matcher ontologique plus rigoureux, polarisé et un-à-un.

2. Périmètre de la comparaison

Cette analyse porte uniquement sur la brique ECG_LLM_Judge de HeartWise :

lexique ECG ;

extraction des constatations depuis un texte libre ;

normalisation ;

matching ;

calcul des scores.

Elle ne porte pas sur le reste de DeepECG-Tok :

tokenizer du signal ECG ;

représentation du signal ;

intégration avec MedGemma ;

génération de comptes rendus depuis le signal ;

prédiction d’endpoints cliniques.

3. Comparaison structurelle des référentiels

Dimension

HeartWise

ECG-online

Objet principal

Lexique contrôlé

Ontologie relationnelle

Unité

Terme canonique + synonymes

Concept avec identifiant et propriétés

Organisation

Catégories relativement plates

Hiérarchie multi-niveaux

Relations sémantiques

Non explicites

parents, children, requires, supports, excludes

Composition

Concepts souvent précombinés

Concepts décomposables et recombinables

Polarité

Non structurée

present, absent, hypothese

Topographie

Souvent incluse dans le label

Concept séparé

Mesures

Comparaison déterministe pour certains champs

Souvent converties en concepts cliniques

Pondération

F1 global et pénalités simples

Poids cliniques et scoring pédagogique

Finalité

Comparaison de comptes rendus

Évaluation du raisonnement d’un apprenant

3.1. Nature réelle du lexique HeartWise

Le fichier HeartWise contient des rubriques comme :

rythme ;

conduction ;

hypertrophie/cavités ;

infarctus/ischémie ;

péricardite ;

autres anomalies de repolarisation.

Chaque terme canonique est associé à plusieurs formulations.

Exemple conceptuel :

{
  "Left bundle branch block": [
    "lbbb",
    "left bundle branch block",
    "complete left bundle branch block"
  ]
}

Ce format est très utile pour reconnaître des formulations équivalentes, mais il ne décrit pas les relations cliniques entre les concepts.

Il s’agit donc davantage d’une :

terminologie contrôlée ;

table de normalisation ;

ressource de synonymie ;

que d’une ontologie formelle.

4. Différences cliniques importantes entre les deux référentiels

4.1. Rythme sinusal et ECG normal

Dans HeartWise, le terme canonique Sinusal inclut notamment :

sinus rhythm ;

normal sinus rhythm ;

normal ECG ;

normal.

Cette équivalence est trop large.

Un rythme sinusal peut coexister avec :

un bloc de branche ;

un QT long ;

une hypertrophie ;

un infarctus ;

une anomalie de repolarisation.

Dans ECG-online, le rythme sinusal n’est qu’un élément possible d’un ECG normal. La normalité doit être construite à partir de plusieurs caractéristiques compatibles.

Conclusion : ne pas importer l’équivalence rythme sinusal = ECG normal.

4.2. Fibrillation atriale et fréquence ventriculaire

HeartWise regroupe sous Afib :

fibrillation atriale ;

fibrillation atriale rapide ;

fibrillation atriale lente.

Cette approche perd une partie de l’information.

Dans ECG-online, il est préférable de séparer :

FIBRILLATION_ATRIALE
+
TACHYCARDIE ou BRADYCARDIE

Conclusion : conserver une logique compositionnelle.

4.3. Bloc atrioventriculaire 2/1

HeartWise inclut 2:1 AV block parmi les synonymes de Mobitz I.

Cette équivalence est discutable : une conduction 2/1 ne permet généralement pas de classer automatiquement le bloc en Mobitz I ou Mobitz II.

Dans ECG-online, le rapport 2/1 est un qualificatif indépendant.

Conclusion : rejeter ce mapping et conserver :

BAV_2
+
CONDUCTION_2_1

sans classification automatique en Mobitz I.

4.4. Préexcitation, onde delta et WPW

HeartWise possède des entrées distinctes pour :

la préexcitation/WPW ;

l’onde delta.

Mais certains synonymes apparaissent dans les deux entrées.

Une représentation relationnelle devrait plutôt être :

ONDE_DELTA
    ↓ soutient
PREEXCITATION_VENTRICULAIRE
    ↓ éventuellement associée à
SYNDROME_DE_WOLFF_PARKINSON_WHITE

Conclusion : importer les formulations lexicales, mais pas l’ambiguïté conceptuelle.

4.5. Hypertrophie ventriculaire gauche et strain

HeartWise regroupe sous Left ventricular hypertrophy :

HVG ;

HVG avec strain ;

HVG avec anomalies secondaires de repolarisation.

Dans un système pédagogique, il faut distinguer :

HYPERTROPHIE_VENTRICULAIRE_GAUCHE
+
ANOMALIE_SECONDAIRE_DE_REPOLARISATION

Conclusion : décomposer les concepts composites.

4.6. Topographie de l’ischémie et de la repolarisation

HeartWise utilise de nombreux labels précombinés :

ST elevation (anterior - V3-V4) ;

ST depression (inferior - II, III, aVF) ;

T wave inversion (lateral - I, aVL, V5-V6) ;

Q wave (septal - V1-V2).

ECG-online peut représenter séparément :

ANOMALIE
+
POLARITE ou MORPHOLOGIE
+
TOPOGRAPHIE
+
DERIVATIONS

Exemple :

{
  "finding": "SUS_DECALAGE_ST",
  "topography": "ANTERIEUR",
  "leads": ["V3", "V4"],
  "status": "present"
}

Conclusion : les formulations HeartWise sont utiles comme surfaces lexicales, mais ne doivent pas devenir les identifiants fondamentaux de l’ontologie.

5. Ce que le lexique HeartWise peut apporter

Le lexique HeartWise constitue une bonne source pour :

enrichir les synonymes anglais ;

intégrer les formulations des comptes rendus automatiques ;

reconnaître les abréviations nord-américaines ;

améliorer la couverture des formulations liées à la stimulation ;

créer un corpus externe de stress-test ;

établir une baseline publiée.

5.1. Classification proposée des entrées HeartWise

Chaque entrée doit être classée dans l’une des catégories suivantes :

Correspondance exacteLe terme correspond directement à un concept ECG-online.

Synonyme à importerLa formulation peut être ajoutée aux synonymes d’un concept existant.

Concept composite à décomposerLe label HeartWise combine plusieurs concepts ECG-online.

Assertion ou degré de certitude à séparerLes formulations possible, probable, cannot rule out ne doivent pas être des synonymes ordinaires.

Mapping ambigu à rejeterExemple : BAV 2/1 associé automatiquement à Mobitz I.

Véritable lacune de l’ontologie ECG-onlineLe concept est cliniquement utile et absent du référentiel actuel.

6. Analyse de la logique NER HeartWise

6.1. Fonctionnement

Le système HeartWise ne réalise pas un NER classique en plusieurs étapes.

Il demande directement au LLM :

Extraire les constatations ECG présentes dans le texte et les retourner sous forme de liste JSON en utilisant les termes exacts du lexique.

Exemple :

[
  "Sinusal",
  "Left bundle branch block",
  "ST elevation (inferior - II, III, aVF)"
]

Le même extracteur est appliqué :

au texte candidat ;

au texte de référence.

Les deux listes sont ensuite comparées.

6.2. Pipeline HeartWise

texte libre
→ LLM contraint par le lexique
→ liste de termes canoniques
→ matching
→ précision / rappel / F1

6.3. Pipeline ECG-online

texte étudiant
→ extraction des mentions
   ├── terme brut
   ├── contexte phrastique
   └── statut : présent / absent / hypothèse
→ recherche hybride
   ├── BM25
   └── embeddings
→ exact-match déterministe ou juge LLM limité au Top-K
→ concept ontologique
→ expansion sémantique
→ scoring pédagogique

Conclusion : le pipeline ECG-online est plus adapté aux réponses naturelles d’apprenants et ne doit pas être remplacé par le NER HeartWise.

7. Éléments utiles à reprendre dans leur logique NER

7.1. Extraction symétrique candidat/référence

L’idée d’appliquer exactement le même extracteur aux deux textes est utile pour :

comparer deux comptes rendus libres ;

créer une baseline ;

importer une nouvelle référence textuelle ;

évaluer des cas non encore curés ;

proposer automatiquement un premier gold.

Recommandation

Conserver deux modes :

MODE PEDAGOGIQUE
réponse étudiant → NER → ontologie
gold humain déjà ontologique

MODE HEARTWISE / BASELINE
réponse étudiant → extracteur fermé
texte référence → même extracteur fermé

Le mode symétrique ne doit pas remplacer le gold humain validé.

7.2. Cache d’extraction versionné

HeartWise met en cache les extractions.

ECG-online devrait intégrer un cache dont la clé comprend :

hash du texte
+ version de l’ontologie
+ version du prompt
+ modèle
+ version du modèle
+ température
+ paramètres d’inférence

Bénéfices

reproductibilité ;

réduction du coût ;

auditabilité ;

relance exacte des expériences ;

comparaison fiable entre versions.

7.3. Extracteur fermé comme baseline

Le modèle HeartWise choisit directement dans une liste fermée de concepts.

Ce mode peut être ajouté à ECG-online comme moteur expérimental :

texte + catalogue autorisé
→ IDs ontologiques directement

Il peut servir :

de baseline simple ;

de second lecteur ;

de contrôle de cohérence ;

de moteur de secours pour des cas à catalogue réduit.

Il ne doit pas remplacer le NER ouvert actuel.

7.4. Fallback déterministe pour les comptes rendus structurés

Leur fallback découpe les comptes rendus sur les points-virgules.

Cela peut être utile pour :

Sinus rhythm; Left axis deviation; Right bundle branch block

Ce mécanisme doit être réservé à un parseur de comptes rendus automatiques :

parse_machine_generated_ecg_report()

Il est peu adapté aux textes libres d’étudiants.

8. Analyse de la logique de matching HeartWise

8.1. Étapes générales

HeartWise :

compare les labels exacts ;

recherche des équivalences dans les synonymes ;

accepte parfois une proximité lexicale ;

calcule précision, rappel et F1 ;

applique éventuellement une pénalité pour certaines assertions critiques.

8.2. Sortie utile

Le verdict expose :

éléments candidats ;

éléments de référence ;

éléments manquants ;

éléments surnuméraires ;

précision ;

rappel ;

F1.

Ce format doit être repris comme format d’audit commun.

Format recommandé

{
  "matched": [],
  "missing": [],
  "unsupported": [],
  "contradictory": [],
  "matches": [
    {
      "candidate_id": "BLOC_DE_BRANCHE_GAUCHE",
      "reference_id": "BLOC_DE_BRANCHE_GAUCHE",
      "match_type": "exact",
      "credit": 1.0
    }
  ]
}

9. Éléments utiles à reprendre dans leur matching

9.1. Séparation des mesures numériques et du matching sémantique

HeartWise extrait certaines valeurs par règles déterministes et applique des tolérances.

Exemples de tolérances utilisées :

fréquence cardiaque : ±5 bpm ;

PR : ±20 ms ;

QT : ±20 ms ;

QTc : ±20 ms.

Le principe est pertinent, même si les seuils doivent être discutés.

Recommandation

Conserver simultanément :

{
  "concept_id": "PR_ALLONGE",
  "measurement": {
    "name": "PR",
    "value": 220,
    "unit": "ms"
  }
}

Cela permet d’évaluer séparément :

l’extraction de la mesure ;

l’exactitude numérique ;

sa catégorisation ;

son interprétation clinique.

9.2. Validation du schéma JSON

Le rapport complet doit être validé par un JSON Schema ou un schéma Pydantic.

Le schéma doit contrôler :

identifiants autorisés ;

statut clinique ;

types ;

unités ;

valeurs numériques ;

champs obligatoires ;

absence de clés inattendues.

Une sortie invalide doit être signalée, et non réparée silencieusement.

9.3. Pénalité des assertions graves non soutenues

Le principe d’une pénalité pour les assertions critiques erronées est pertinent.

Dans ECG-online, la pénalité doit dépendre de la gravité :

Type d’erreur

Pénalité

Erreur descriptive mineure

Faible

Diagnostic important non soutenu

Modérée à forte

Diagnostic urgent contradictoire

Très forte

Exemple :

erreur d’axe ;

faux diagnostic de STEMI ;

ne doivent pas avoir le même poids.

10. Éléments HeartWise à ne pas reprendre

10.1. Matching sur deux mots communs

HeartWise accepte parfois une équivalence lorsque deux expressions partagent au moins deux mots.

Cette règle est dangereuse.

Exemples :

ST elevation anterior
ST depression anterior

right bundle branch block
left bundle branch block

Les expressions sont lexicalement proches, mais cliniquement opposées.

Décision : ne pas importer cette règle.

10.2. Absence de polarité structurée

La sortie HeartWise ne distingue pas suffisamment :

présent ;

absent ;

hypothétique ;

ancien ;

discuté puis rejeté.

ECG-online possède déjà :

present
absent
hypothese

avec des garde-fous de négation et de hedging.

Décision : conserver le modèle ECG-online.

10.3. Fallback par similarité textuelle brute

La proximité textuelle ne mesure pas la justesse clinique.

Exemple :

pas de fibrillation atriale
fibrillation atriale

Ces phrases sont lexicalement proches mais opposées.

Décision : ne jamais utiliser la similarité brute pour attribuer une note clinique.

10.4. Matching non strictement un-à-un

Le matching HeartWise peut augmenter le nombre de vrais positifs sur la base de synonymes sans reconstruire complètement les ensembles appariés.

Plusieurs concepts candidats peuvent potentiellement correspondre au même concept de référence.

Décision : construire un véritable matching biparti un-à-un.

10.5. Concepts trop composites

Leur extraction directe vers des labels comme :

ST elevation (septal - V1-V2)

fusionne :

l’anomalie ;

la polarité ;

la topographie ;

les dérivations.

Décision : conserver la décomposition ECG-online.

11. Matcher cible recommandé pour ECG-online

11.1. Principe

concepts candidats
→ matrice de compatibilité ontologique
→ appariement biparti un-à-un
→ classification des matches
→ scores et pénalités

11.2. Types de correspondance

Relation

Crédit indicatif

Même identifiant

1,00

Synonyme du même concept

1,00

Enfant plus spécifique correct

1,00

Parent acceptable mais imprécis

0,50 à 0,75

Concept associé mais non équivalent

0,25

Concept incompatible

0

Concept explicitement contradictoire

Pénalité

11.3. Contraintes

un concept candidat ne peut être apparié qu’une fois ;

un concept de référence ne peut être apparié qu’une fois ;

la polarité doit être compatible ;

les concepts exclusifs ne peuvent pas être considérés comme proches ;

les mesures et les concepts sont évalués séparément ;

la topographie doit pouvoir être partiellement concordante ;

la gravité clinique doit influencer la pénalité.

12. Architecture proposée après intégration

                           TEXTE ETUDIANT
                                  │
                     ┌────────────┴────────────┐
                     │                         │
                     ▼                         ▼
          NER ouvert ECG-online      Extracteur fermé baseline
          terme + contexte + statut  HeartWise-like
                     │                         │
                     ▼                         │
          recherche hybride + juge             │
                     │                         │
                     ▼                         ▼
               concepts ontologiques normalisés
                                  │
                     canal numérique parallèle
                                  │
                                  ▼
                  matching ontologique un-à-un
                                  │
                 ┌────────────────┼────────────────┐
                 ▼                ▼                ▼
              score        analyse d’erreurs    feedback

13. Plan de comparaison expérimental

13.1. Systèmes à comparer

Système A — ECG-online actuel

ontologie ECG-online ;

NER actuel ;

recherche hybride ;

juge Top-K ;

scoring actuel.

Système B — HeartWise reproduit

lexique HeartWise ;

prompt HeartWise ;

extraction fermée ;

matching HeartWise ;

F1 HeartWise.

Système C — HeartWise avec le même LLM qu’ECG-online

lexique HeartWise ;

extracteur Qwen ou modèle local ;

matching HeartWise.

Système D — ECG-online hybride

ontologie ECG-online enrichie par les synonymes HeartWise ;

NER actuel ;

canal numérique déterministe ;

matcher biparti ;

scoring pédagogique.

13.2. Comparaisons par composant

Comparaison des référentiels

Même LLM, même prompt, mêmes textes :

ontologie ECG-online ;

lexique HeartWise ;

lexique HeartWise enrichi en français ;

ontologie hybride.

Comparaison des extracteurs

Même référentiel :

NER actuel ;

extracteur fermé HeartWise-like ;

modèle local ;

modèle externe de référence.

Comparaison des matchers

Mêmes concepts extraits :

matching HeartWise ;

scoring ECG-online actuel ;

matching biparti ontologique cible.

14. Gold standard recommandé

Le gold standard doit distinguer :

14.1. Ce que l’étudiant a écrit

concept exprimé ;

polarité ;

certitude ;

topographie ;

valeur numérique ;

formulation exacte.

14.2. Ce qui est vrai sur l’ECG

concept correct ;

concept incorrect ;

omission ;

contradiction ;

gravité clinique ;

étape du raisonnement concernée.

Deux cardiologues doivent annoter indépendamment un échantillon, avec adjudication des désaccords.

Le gold ne doit pas dépendre uniquement d’un autre LLM.

15. Critères de jugement

Critère principal

F1 conceptuel par réponse par rapport au gold humain.

Critères secondaires

précision micro et macro ;

rappel micro et macro ;

exact match de la liste ;

taux de concepts non mappés ;

sensibilité aux erreurs majeures ;

faux diagnostics critiques ;

négations mal interprétées ;

hypothèses suraffirmées ;

contradictions non détectées ;

erreurs numériques ;

stabilité entre plusieurs exécutions ;

taux de JSON invalide ;

latence ;

coût ;

concordance avec la note pédagogique humaine.

16. Décisions d’implémentation

À intégrer rapidement

Cache versionné des extractions

Canal numérique déterministe parallèle

Format standard matched / missing / unsupported / contradictory

Extracteur fermé HeartWise-like comme baseline

Mode symétrique candidat/référence pour les textes non curés

Validation systématique du JSON

Pénalités selon la gravité clinique

Import contrôlé des synonymes HeartWise

À conserver

NER avec mention originale

Contexte phrastique

Statut présent/absent/hypothèse

Recherche hybride BM25 + embeddings

Exact-match déterministe

Juge QCM limité au Top-K

Relations ontologiques

Décomposition finding/diagnostic/qualificatif/topographie

Scoring pédagogique

À développer

Crosswalk HeartWise → ECG-online

Matcher biparti un-à-un

Compatibilité parent/enfant

Gestion structurée des contradictions

Évaluation distincte des valeurs numériques

Benchmark reproductible des différentes méthodes

17. Livrables proposés

docs/
├── HEARTWISE_ECGONLINE_ANALYSIS.md
├── HEARTWISE_REPRODUCIBILITY_MANIFEST.yaml
└── HEARTWISE_MAPPING_GUIDELINES.md

data/
├── heartwise_ecgonline_crosswalk.csv
├── heartwise_synonyms_import_candidates.csv
├── heartwise_rejected_mappings.csv
└── heartwise_fr_extension.json

benchmark/
├── heartwise_baseline/
├── ecgonline_current/
├── ecgonline_hybrid/
├── gold_human/
└── results/

src/
├── extractors/
│   ├── open_ner.py
│   └── closed_heartwise_like.py
├── matching/
│   ├── heartwise_matcher.py
│   └── ontology_bipartite_matcher.py
└── numeric/
    └── ecg_measurement_evaluator.py

18. Conclusion

La méthode HeartWise n’est pas identique à celle d’ECG-online.

HeartWise a développé :

un lexique ECG relativement large ;

une extraction LLM directement contrainte vers ce lexique ;

un matching conceptuel simple ;

une validation du juge global.

ECG-online possède :

une véritable structure ontologique ;

une décomposition des concepts ;

une gestion de la polarité et de l’incertitude ;

un entity linking en plusieurs étapes ;

des relations logiques ;

un scoring adapté à l’apprentissage.

La stratégie la plus rationnelle est donc :

utiliser HeartWise comme ressource lexicale, baseline méthodologique et source de bonnes pratiques techniques, tout en conservant l’architecture ontologique et pédagogique d’ECG-online.

La contribution scientifique potentielle d’ECG-online devient alors claire :

montrer qu’un matching relationnel, polarisé et pédagogique apporte davantage qu’une simple comparaison lexicale de constatations ECG.

19. Sources techniques principales

HeartWise-AI, dépôt ECG_LLM_Judge

ontology/ecg_ontology.json

judges.py

EPCASE, dépôt ecg-online

rag_pipeline/data/ontology_v2.json

rag_pipeline/ner_extractor.py

rag_pipeline/hybrid_search.py

rag_pipeline/neurosymbolic_judge.py

rag_pipeline/semantic_layer.py

rag_pipeline/candidate_report.py

rag_pipeline/scoring_v3.py