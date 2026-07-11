# Tableau multi-parcours ECG

## Objectif

Cette itération transforme le MVP BAV en un moteur générique pour trois micro-parcours :

1. blocs auriculoventriculaires ;
2. fibrillation atriale versus flutter typique ;
3. première orientation des tachycardies régulières à QRS fins.

Le tableau est accessible par `/static/pathways.html`. L’ancienne URL `/static/pathway.html` reste compatible et ouvre le parcours BAV ; le paramètre `?id=` sélectionne les autres parcours.

## Modèle de données

`frontend/pathways.json` est l’allowlist des parcours disponibles. Chaque entrée pointe vers un fichier `pedagogy-*.json`, qui contient :

- objectifs d’apprentissage ;
- séquence de 4 à 6 étapes ;
- libellés pré-réponse neutres ;
- indices experts progressifs ;
- point pédagogique révélé après correction ;
- test autonome sans indice ;
- éventuelle remédiation guidée ;
- messages de bilan propres à la compétence.

Chaque progression reste isolée dans `localStorage` sous la clé historique `ecg_pathway_v1_<id>`. La clé BAV n’a pas changé.

## États du tableau

- **Non commencé** : aucune activité.
- **En cours** : parcours commencé, sans test autonome évalué.
- **À consolider** : test autonome échoué, y compris après une remédiation guidée.
- **Acquis** : test autonome réussi sans indice.

Une remédiation aidée ne peut jamais transformer un échec autonome en maîtrise. Elle prépare une future réactivation.

## Validité pédagogique renforcée

La V2 corrige quatre limites du MVP initial :

- les titres ne révèlent plus le diagnostic avant la réponse ;
- la réponse initiale verrouillée et les indices vus survivent à un rafraîchissement ;
- les performances accompagnées et autonomes sont affichées séparément ;
- les cas dont le premier tracé ne permet pas un mécanisme unique sont marqués `formative_only` et exclus de la validation.

Les images secondaires des cas 42–44 contiennent les réponses et restent donc post-correction. `cas_41_p2.png` est masqué dans le parcours FA/flutter en raison d’un libellé erroné dans l’asset source.

## Portée clinique

Le parcours FA/flutter valide la reconnaissance d’un flutter commun typique et la distinction entre activité atriale organisée et anarchique. Il ne prétend pas couvrir tous les flutters atypiques ou à conduction variable.

Le parcours QRS fins valide une **première orientation autonome**, notamment la reconnaissance d’une tachycardie sinusale. Les cas AVRT et AVNRT restent formatifs : leur mécanisme exact ne peut pas être certifié à partir du seul tracé primaire.

## Limite de sécurité

Les indices sont chargés depuis des fichiers statiques. Le verrouillage est suffisant pour un usage pédagogique ordinaire, mais ne protège pas contre l’inspection volontaire du réseau ou du code source. Une étude nécessitant un aveugle technique strict devra déplacer les indices vers une machine d’état côté serveur.
