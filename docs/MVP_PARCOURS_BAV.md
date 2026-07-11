# MVP — micro-parcours « Blocs auriculoventriculaires »

## Intention

Ce MVP transforme cinq ECG existants en un parcours court fondé sur la maîtrise. Il ne remplace pas la banque libre des 75 cas et ne modifie aucun contenu clinique de référence.

Le déroulement est volontairement contraint :

1. interprétation initiale en texte libre ;
2. estimation de la confiance ;
3. verrouillage de la première réponse ;
4. indices experts progressifs sur les quatre cas d’apprentissage ;
5. réponse finale et correction par le moteur existant ;
6. test de maîtrise sans indice ;
7. un seul cas de consolidation supplémentaire en cas d’échec.

## Séquence pédagogique

| Ordre | Cas | Fonction pédagogique | Concept central |
|---:|---:|---|---|
| 1 | 23 | Fondation | Toutes les ondes P conduites, PR fixe >200 ms |
| 2 | 24 | Apprentissage guidé | Wenckebach : allongement progressif du PR |
| 3 | 25 | Contraste | Mobitz II : PR stable avec blocage inopiné |
| 4 | 26 | Discrimination | BAV 2/1, sans surclasser arbitrairement type I/II |
| 5 | 28 | Test autonome | BAV complet avec échappement jonctionnel |
| 6, optionnel | 29 | Consolidation | BAV complet avec échappement distal à QRS larges |

Le parcours est donc limité à cinq ECG dans le fonctionnement normal et à six ECG au maximum.

## Règles de maîtrise

Le test final est considéré réussi si :

- le sous-score diagnostique est au moins égal à 75/100 ;
- le correcteur ne classe pas la réponse comme une erreur clinique de l’étudiant ;
- aucun indice n’a été utilisé sur le cas de maîtrise.

Ce seuil est un paramètre du prototype et devra être validé ou recalibré sur les données pilotes.

## Données recueillies

Le frontend transmet au collecteur existant :

- identifiant du parcours ;
- phase et position ;
- réponse initiale ;
- réponse finale ;
- confiance initiale ;
- nombre d’indices utilisés ;
- modification ou non de la réponse après engagement initial ;
- temps avant verrouillage de la réponse initiale ;
- temps total avant correction.

La modification proposée de `app/collector.py` étend l’onglet `reponses` sans supprimer les anciennes colonnes ni modifier l’onglet `par_cas`.

## Accès

Une fois les fichiers installés :

- page directe : `/static/pathway.html` ;
- bouton d’accueil : « Parcours BAV guidé » ;
- retour à la banque libre : `/`.

## Validation technique

```bash
node --check frontend/pathway-core.js
node --check frontend/pathway.js
node tests/test_pathway_core.js
python -m json.tool frontend/pedagogy-bav.json >/dev/null
```

## Vérification pédagogique manuelle

- le titre diagnostique réel n’est pas révélé avant correction ;
- les indices sont inaccessibles avant la première réponse ;
- le premier indice oriente l’attention mais ne donne pas le diagnostic ;
- le cas 26 conclut à un BAV 2/1 sans affirmer abusivement Mobitz I ou II ;
- le cas 28 ne propose aucun indice ;
- l’échec au cas 28 ne peut ajouter qu’un seul cas ;
- les interprétations de référence et le barème existants restent inchangés.

## Limites du MVP

- les indices sont statiques et écrits par un expert ; ce choix est volontaire pour la cohérence clinique ;
- il n’existe pas encore de réactivation automatique à J7 ou J30 ;
- la confiance est recueillie sur une échelle simple de 0 à 100 ;
- le seuil de maîtrise n’est pas encore validé empiriquement ;
- l’expérience doit être testée sur mobile et sur les navigateurs utilisés par les étudiants.

## Étape suivante après validation

Le même moteur pourra être réutilisé pour :

- FA versus flutter ;
- tachycardies régulières à QRS fins ;
- tachycardies à QRS larges ;
- douleur thoracique et sus-décalage du segment ST.

La généralisation ne doit intervenir qu’après validation du parcours BAV, de son acceptabilité et de la qualité des données recueillies.
