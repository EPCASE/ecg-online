# Curriculum Phase 2 — Brouillon groupe 2/3 (5 parcours)

> **À relire et annoter directement dans ce fichier** (commentaires, corrections,
> ajustements de formulation). Une fois validé, je génère les fichiers
> `frontend/pedagogy-<id>.json` définitifs à partir de ce contenu.
>
> Parcours couverts ici : `bav-foundations` (à migrer vers le nouveau format),
> `wide-qrs-sinus` (à migrer), `normal-and-hypertrophy` (nouveau),
> `artifacts-and-normal-variants` (nouveau), `fa-flutter` (à migrer).

---

## 1. `bav-foundations` — Blocs auriculoventriculaires (fondamentaux)

*Parcours existant (`frontend/pedagogy-bav.json`), à migrer vers le nouveau
format enrichi (required_concepts/unsafe_errors). Cas identiques (23, 24, 25,
26, 28) ; le cas 29 quitte ce parcours pour `bav-advanced` (déjà fait).*

**Objectifs pédagogiques :**
- Vérifier systématiquement la relation entre les ondes P et les complexes QRS.
- Distinguer BAV du premier degré, Mobitz I, Mobitz II et BAV 2/1.
- Reconnaître un BAV complet et caractériser son rythme d'échappement.
- Identifier les formes à risque nécessitant une prise en charge urgente.

### Foundation — Cas 23
**Diagnostic golden :** BAV du 1er degré marqué en rythme sinusal, associé à une HAG.
**Teaching point :** Toutes les ondes P sont conduites avec un PR fixe > 200 ms : BAV du premier degré. Une hypertrophie atriale gauche associée n'en change pas la nature.
**Hints :**
1. Compte séparément les ondes P et les QRS : chaque onde P est-elle conduite ?
2. Mesure l'intervalle PR sur plusieurs cycles : est-il fixe ?
3. Toutes les P sont conduites, mais le PR est fixe et > 200 ms → BAV1.
**required_concepts (proposé) :** `BAV_DE_TYPE_1`, `RYTHME_SINUSAL`
**unsafe_errors (proposé) :** *(aucun — pas de confusion dangereuse à ce stade)*

### Guided — Cas 24
**Diagnostic golden :** BAV du 2e degré Mobitz 1 (Luciani-Wenckebach).
**Teaching point :** L'allongement progressif du PR avant une onde P bloquée définit un BAV Mobitz I (Wenckebach) — un bloc bifasciculaire associé ne doit pas faire conclure à tort à un Mobitz II.
**Hints :**
1. Repère une onde P qui n'est pas suivie d'un QRS.
2. Compare les PR des battements conduits avant la pause : s'allongent-ils ?
3. PR qui s'allonge progressivement puis P bloquée = Mobitz I.
**required_concepts (proposé) :** `BAV_2_MOBITZ_1`
**unsafe_errors (proposé) :** `BAV_2_MOBITZ_2`

### Contrast — Cas 25
**Diagnostic golden :** BAV du 2e degré type 2 (Mobitz 2).
**Teaching point :** Une onde P bloquée de façon inopinée, avec des PR conduits constants (sans allongement progressif préalable), définit un Mobitz II — à distinguer du Mobitz I du cas précédent.
**Hints :**
1. Cherche l'onde P responsable de la pause.
2. Compare le PR avant/après la P bloquée : y a-t-il un allongement progressif ?
3. PR constant puis P bloquée brutalement = Mobitz II (risque d'évolution vers BAV complet).
**required_concepts (proposé) :** `BAV_2_MOBITZ_2`
**unsafe_errors (proposé) :** `BAV_2_MOBITZ_1`, `DYSFONCTION_SINUSALE`

### Integration — Cas 26
**Diagnostic golden :** BAV du 2e degré 2/1.
**Teaching point :** Une onde P sur deux est conduite : le diagnostic descriptif est BAV 2/1, sans pouvoir trancher Mobitz I ou II sur ce seul tracé (cf. `BAV_DE_HAUT_GRADE`/`BAV_2_POUR_1` désormais documenté dans la base EDN).
**Hints :**
1. Recherche une activité atriale cachée en fin d'onde T.
2. Compare la fréquence atriale à la fréquence ventriculaire.
3. Une P sur deux conduite = BAV 2/1 ; le siège (nodal/infrahissien) se déduit de la largeur du QRS.
**required_concepts (proposé) :** `BAV_2_POUR_1`
**unsafe_errors (proposé) :** `BAV_2_MOBITZ_1`, `BAV_2_MOBITZ_2` *(à discuter : accepter l'un des deux comme non-erreur si l'étudiant argumente le siège par la largeur du QRS ?)*

### Mastery — Cas 28 (test)
**Diagnostic golden :** BAV du 3e degré (complet) avec échappement jonctionnel régulier.
**Teaching point :** Dissociation atrioventriculaire complète (P régulières sans lien avec les QRS) + échappement jonctionnel régulier à QRS fins = BAV complet à échappement proximal (plutôt rassurant que l'échappement soit jonctionnel et non ventriculaire).
**required_concepts (proposé) :** `BAV_COMPLET`, `RYTHME_D_ECHAPPEMENT_JONCTIONNEL`
**unsafe_errors (proposé) :** *(aucun désaccord clinique évident, à confirmer)*

> ⚠️ **Question pour toi :** le fichier legacy a un bloc `remediation` avec le
> cas 29 (échappement plus distal). Le cas 29 appartient maintenant à
> `bav-advanced` — je propose de **supprimer ce bloc remediation** ici pour
> éviter la redondance. Confirme ou dis-moi si tu veux le garder comme
> "bonus" indépendant du mapping officiel = 
**reponse pour LLM** oui tu peux supprimer ici et éviter la redondance

---

## 2. `wide-qrs-sinus` — Morphologies des QRS larges (rythme sinusal)

*Parcours existant (`frontend/pedagogy-qrs-larges-sinus.json`), à migrer.
Cas : 8, 9, 13, 10, 14.*

**Objectifs pédagogiques (proposés) :**
- Reconnaître un ECG normal avec petite onde q septale physiologique (référence de base).
- Appliquer les critères précis de bloc de branche droit complet.
- Appliquer les critères précis de bloc de branche gauche complet.
- Reconnaître un bloc bifasciculaire (BBD + hémibloc antérieur gauche) associé à un BAV1.
- Identifier une alternance de bloc de branche, marqueur de gravité chez un patient syncopal.

### Foundation — Cas 8
**Diagnostic golden :** ECG normal avec activation ventriculaire normale.
**Teaching point :** Avant d'étudier les QRS larges pathologiques, rappel du repère normal : QRS fins (85 ms), petite onde q physiologique en V5-V6 (activation septale), pas de trouble de repolarisation.
**Hints :**
1. Mesure la durée du QRS : est-elle dans la norme (< 100-120 ms) ?
2. Une petite onde q fine en V5-V6 est-elle pathologique ou physiologique ?
3. QRS fins + petite q septale isolée en V5-V6 = tracé normal, ne pas la confondre avec une onde Q de nécrose.
**required_concepts (proposé) :** `ECG_NORMAL`, `RYTHME_SINUSAL`
**unsafe_errors (proposé) :** *(aucun)*

### Guided — Cas 9
**Diagnostic golden :** Bloc de branche droite complet typique.
**Teaching point :** QRS > 120 ms, aspect rSR' en V1, onde S large et traînante en V6 : bloc de branche droite complet — la démarche en 3 temps (durée puis V1 puis V6) permet de le confirmer avec certitude.
**Hints :**
1. Mesure la durée du QRS : dépasse-t-elle 120 ms ?
2. Regarde la morphologie en V1 : QRS globalement positif avec un aspect particulier ?
3. QRS > 120 ms + rSR' en V1 + S traînante en V6 = BBD complet.
**required_concepts (proposé) :** `BLOC_DE_BRANCHE_DROIT_COMPLET`
**unsafe_errors (proposé) :** `BLOC_DE_BRANCHE_GAUCHE_COMPLET`

### Contrast — Cas 13
**Diagnostic golden :** Bloc de branche gauche complet.
**Teaching point :** QRS > 120 ms, QRS négatif en V1-V2 (QS/rS), onde R large positive en DI/V6 : bloc de branche gauche complet, avec troubles secondaires de repolarisation (discordance appropriée) à ne pas confondre avec une ischémie.
**Hints :**
1. Compare l'aspect en V1 à celui du cas précédent (BBD) : est-il positif ou négatif ?
2. Cherche l'onde R large en DI et V6.
3. QRS négatif en V1-V2 + R large en DI/V6 = BBG complet ; les troubles de repolarisation associés sont secondaires et attendus (discordance appropriée).
**required_concepts (proposé) :** `BLOC_DE_BRANCHE_GAUCHE_COMPLET`
**unsafe_errors (proposé) :** `BLOC_DE_BRANCHE_DROIT_COMPLET`

### Integration — Cas 10
**Diagnostic golden :** Bloc bifasciculaire (BBD complet + hémibloc antérieur gauche) associé à un BAV du 1er degré.
**Teaching point :** La sémiologie s'additionne : critères de BBD complet en V1/V6 + déviation axiale gauche (hémibloc antérieur gauche) + PR > 200 ms (BAV1) = bloc bifasciculaire avec BAV1 associé, une association qui doit alerter sur le risque de progression vers un BAV infrahissien.
**Hints :**
1. Retrouve d'abord les critères de BBD complet, comme au cas précédent.
2. Cherche en plus une déviation axiale gauche marquée.
3. BBD complet + déviation axiale gauche = bloc bifasciculaire ; vérifie aussi le PR pour ne pas manquer un BAV1 associé.
**required_concepts (proposé) :** `BLOC_BIFASCICULAIRE`, `BAV_DE_TYPE_1`
**unsafe_errors (proposé) :** `BLOC_DE_BRANCHE_GAUCHE_COMPLET`

### Mastery — Cas 14 (test)
**Diagnostic golden :** Bloc de branche alternant (BBD complet / BBG complet en alternance) avec trouble de conduction atrioventriculaire (PR variable, ondes P bloquées).
**Teaching point :** Une alternance de bloc de branche droite et gauche, avec des ondes P parfois bloquées, traduit une atteinte diffuse et instable du système de conduction — c'est une urgence chez un patient syncopal (indication de stimulation).
**required_concepts (proposé) :** `BLOC_DE_BRANCHE_DROIT_COMPLET`, `BLOC_DE_BRANCHE_GAUCHE_COMPLET`
**unsafe_errors (proposé) :** *(à discuter : comment encoder "ne pas réduire à un seul type de bloc" comme unsafe_error ?)*
**reponse pour LLM** aucune idéee pour le unsafe error, peut-être `BLOC_DE_BRANCHE_ALTERNANT` si tu veux forcer la reconnaissance de l'alternance
---

## 3. `normal-and-hypertrophy` — ECG normal et hypertrophies

*Nouveau parcours. Cas : 3, 4, 5, 6, 7.*

**Objectifs pédagogiques (proposés) :**
- Consolider les critères complets d'un ECG normal.
- Reconnaître une hypertrophie atriale gauche.
- Reconnaître une hypertrophie atriale et ventriculaire droite associées.
- Reconnaître une hypertrophie ventriculaire gauche électrique (indice de Sokolow).
- Reconnaître une hypertrophie ventriculaire droite isolée avec troubles de repolarisation.

### Foundation — Cas 3
**Diagnostic golden :** ECG normal.
**Teaching point :** Un ECG strictement normal impose de vérifier chaque paramètre (rythme, PR, QRS, axe, repolarisation, QT) — la petite onde q physiologique en V5-V6 ne doit pas être confondue avec une séquelle de nécrose.
**Hints :**
1. Vérifie chaque paramètre un par un : rythme, PR, QRS, axe, repolarisation, QT.
2. Une petite onde q isolée en V5-V6 est-elle pathologique ?
3. Tous les paramètres sont dans la norme et la q septale est physiologique → ECG normal.
**required_concepts (proposé) :** `ECG_NORMAL`
**unsafe_errors (proposé) :** *(aucun)*

### Guided — Cas 4
**Diagnostic golden :** Hypertrophie auriculaire gauche.
**Teaching point :** Une onde P élargie (> 120 ms), bifide/crochetée dans les dérivations inférieures et latérales, définit une hypertrophie atriale gauche — l'indice de Sokolow peut rester négatif malgré des troubles de repolarisation latéraux associés.
**Hints :**
1. Mesure la durée de l'onde P : dépasse-t-elle 120 ms ?
2. Regarde la morphologie de l'onde P en DI-DII-DIII/aVF : est-elle bifide ?
3. P élargie et bifide en inférieur/latéral = hypertrophie atriale gauche, indépendamment du Sokolow.
**required_concepts (proposé) :** `HYPERTROPHIE_ATRIALE_GAUCHE`
**unsafe_errors (proposé) :** `HYPERTROPHIE_VENTRICULAIRE_GAUCHE` *(à discuter : les deux peuvent coexister — plutôt un piège de confusion qu'une vraie erreur de sécurité)*

### Contrast — Cas 5
**Diagnostic golden :** Hypertrophie auriculaire droite associée à des signes d'HVD.
**Teaching point :** Une onde P ample et pointue (> 2,5 mm en D2) définit une hypertrophie atriale droite ; associée à de grandes ondes R en V1-V2, elle oriente vers une hypertrophie ventriculaire droite concomitante — à distinguer de l'hypertrophie atriale gauche du cas précédent par la morphologie de l'onde P.
**Hints :**
1. Compare la morphologie de l'onde P à celle du cas précédent : pointue ou bifide ?
2. Mesure son amplitude en D2 : dépasse-t-elle 2,5 mm ?
3. P ample et pointue = hypertrophie atriale droite ; cherche des signes de HVD associée (grandes ondes R en V1-V2).
**required_concepts (proposé) :** `HYPERTROPHIE_ATRIALE_DROITE`, `HYPERTROPHIE_VENTRICULAIRE_DROITE`
**unsafe_errors (proposé) :** `HYPERTROPHIE_ATRIALE_GAUCHE`

### Integration — Cas 6
**Diagnostic golden :** Hypertrophie ventriculaire gauche électrique de type diastolique.
**Teaching point :** Un indice de Sokolow > 35 mm (R amples en V5-V6 + S profondes en V1-V2) avec des ondes T positives en précordiales gauches définit une HVG diastolique — à ne pas confondre avec la forme sévère (T négatives) vue dans la base EDN.
**Hints :**
1. Calcule ou estime l'indice de Sokolow : dépasse-t-il 35 mm ?
2. Regarde la polarité des ondes T en précordiales gauches : positives ou négatives ?
3. Sokolow > 35 mm avec T positives = HVG de type diastolique (moins sévère que la forme avec T négatives).
**required_concepts (proposé) :** `HYPERTROPHIE_VENTRICULAIRE_GAUCHE`
**unsafe_errors (proposé) :** *(aucun)*

### Mastery — Cas 7 (test)
**Diagnostic golden :** Hypertrophie ventriculaire droite.
**Teaching point :** Une déviation axiale droite avec un rapport R/S > 1 en V1 (grandes ondes R) et des troubles de repolarisation en précordiales droites définissent une hypertrophie ventriculaire droite — à ne pas confondre avec une HVG ou une hypertrophie biventriculaire.
**required_concepts (proposé) :** `HYPERTROPHIE_VENTRICULAIRE_DROITE`
**unsafe_errors (proposé) :** `HYPERTROPHIE_VENTRICULAIRE_GAUCHE`
**reponse pour LLM**  plutot un trouble de la conduction pour l'unsafe error, mais je ne sais pas comment le formuler hbpg? 
---

## 4. `artifacts-and-normal-variants` — Pièges techniques et variantes du rythme normal

*Nouveau parcours. Cas : 1, 2, 39, 33, 34.*

**Objectifs pédagogiques (proposés) :**
- Reconnaître une inversion d'électrodes des membres et ne pas la sur-interpréter.
- Distinguer un artefact de ligne de base (tremblement) d'une vraie arythmie atriale.
- Reconnaître une arythmie sinusale respiratoire physiologique.
- Reconnaître une extrasystole atriale conduite à QRS fin.
- Reconnaître un trigéminisme ventriculaire.

### Foundation — Cas 1
**Diagnostic golden :** Inversion des électrodes des deux bras (poignet droit/gauche), tracé corrigé normal.
**Teaching point :** Une onde P, un QRS et une onde T négatifs en DI, avec par ailleurs un rythme sinusal normal (PR, QRS, QT normaux) et une progression normale de l'onde R en précordiales, orientent vers une inversion des électrodes des membres plutôt qu'une vraie pathologie (déviation axiale droite ou trouble de repolarisation latérale).
**Hints :**
1. La négativité en DI concerne-t-elle uniquement l'onde P/QRS/T, ou tout le tracé est-il cohérent par ailleurs (PR, QRS, QT normaux) ?
2. Regarde la progression de l'onde R en précordiales : est-elle normale ?
3. DI totalement négatif (P, QRS, T) avec le reste du tracé normal = inversion d'électrodes, pas une pathologie.
**required_concepts (proposé) :** `INVERSION_D_ELECTRODES`
**unsafe_errors (proposé) :** *hemibloc posterieur gauche ou déviation axiale droite *

### Guided — Cas 2
**Diagnostic golden :** Rythme sinusal avec bloc de branche gauche et artefact de ligne de base par tremblement mimant une arythmie atriale.
**Teaching point :** Une trémulation de la ligne de base liée à un tremblement (parkinsonien) peut mimer une fibrillation ou un flutter atrial ; la présence de QRS réguliers et d'ondes P sinusales identifiables dans certaines dérivations permet d'éliminer une vraie arythmie atriale — un bloc de branche gauche authentique est associé.
**Hints :**
1. Les QRS sont-ils réguliers malgré l'aspect trémulant de la ligne de base ?
2. Cherche des ondes P sinusales identifiables dans au moins une dérivation.
3. QRS réguliers + P sinusales retrouvables = artefact de ligne de base, pas une arythmie atriale ; ne pas oublier de décrire le BBG associé.
**required_concepts (proposé) :** `RYTHME_SINUSAL`, `BLOC_DE_BRANCHE_GAUCHE_COMPLET`
**unsafe_errors (proposé) :** `FIBRILLATION_ATRIALE`

### Contrast — Cas 39
**Diagnostic golden :** Arythmie sinusale respiratoire physiologique.
**Teaching point :** Une variation de la fréquence cardiaque en rythme sinusal (P normales, PR normal), sans pause ni ralentissement pathologique, chez un adolescent asymptomatique, définit une arythmie sinusale physiologique — à ne pas confondre avec une dysfonction sinusale.
**Hints :**
1. Le rythme reste-t-il sinusal (onde P normale devant chaque QRS) malgré la variation de fréquence ?
2. Y a-t-il une vraie pause ou un ralentissement pathologique, ou seulement une variation progressive ?
3. Variation de fréquence en rythme sinusal, sans pause pathologique, chez un sujet jeune = arythmie sinusale physiologique.
**required_concepts (proposé) :** `ARYTHMIE_SINUSALE`
**unsafe_errors (proposé) :** `DYSFONCTION_SINUSALE`

### Integration — Cas 33
**Diagnostic golden :** Rythme sinusal bradycarde avec extrasystole atriale conduite à QRS fin, troubles de repolarisation associés.
**Teaching point :** Une activité atriale prématurée de morphologie différente de l'onde P sinusale, suivie d'un QRS fin non modifié, définit une extrasystole atriale conduite — le QRS fin élimine une origine ventriculaire.
**Hints :**
1. Cherche une onde P prématurée de morphologie différente des P sinusales (parfois masquée dans l'onde T précédente).
2. Le QRS qui suit est-il fin ou large ?
3. P prématurée + QRS fin conduit normalement = extrasystole atriale, pas ventriculaire.
**required_concepts (proposé) :** `EXTRASYSTOLE_ATRIALE`
**unsafe_errors (proposé) :** `EXTRASYSTOLE_VENTRICULAIRE`

### Mastery — Cas 34 (test)
**Diagnostic golden :** Extrasystoles ventriculaires en trigéminisme sur rythme sinusal.
**Teaching point :** Une organisation régulière de deux battements sinusaux suivis d'une extrasystole ventriculaire (QRS large, non précédée d'activité atriale) définit un trigéminisme ventriculaire.
**required_concepts (proposé) :** `TRIGEMINISME_VENTRICULAIRE`
**unsafe_errors (proposé) :** `EXTRASYSTOLE_ATRIALE`

---

## 5. `fa-flutter` — Fibrillation atriale et flutter

*Parcours existant (`frontend/pedagogy-fa-flutter.json`), à migrer.
Cas : 31, 37, 38, 41, 42.*

**Objectifs pédagogiques (proposés) :**
- Reconnaître une maladie de l'oreillette (alternance FA rapide / bradycardie sinusale).
- Reconnaître une fibrillation atriale rapide à QRS fins.
- Reconnaître une fibrillation atriale à réponse ventriculaire lente, sans la confondre avec un BAV complet.
- Reconnaître un flutter atrial commun typique à conduction 4/1.
- Reconnaître un flutter atrial rapide à conduction 2/1, démasqué par manœuvre vagale.

### Foundation — Cas 31
**Diagnostic golden :** Maladie de l'oreillette / syndrome bradycardie-tachycardie.
**Teaching point :** L'alternance, chez un même patient, d'épisodes de fibrillation atriale rapide et de bradycardie sinusale marquée définit une maladie de l'oreillette (syndrome bradycardie-tachycardie), une forme particulière de dysfonction sinusale.
**Hints :**
1. Sur le premier tracé, la tachycardie est-elle régulière ou irrégulière ?
2. Sur le second tracé, quelle est la fréquence et le rythme de base ?
3. FA rapide sur un tracé + bradycardie sinusale marquée sur l'autre, chez le même patient = maladie de l'oreillette.
**required_concepts (proposé) :** `FIBRILLATION_ATRIALE`, `DYSFONCTION_SINUSALE`
**unsafe_errors (proposé) :** *(aucun)*

### Guided — Cas 37
**Diagnostic golden :** Fibrillation atriale rapide à QRS fins.
**Teaching point :** Une tachycardie irrégulière à QRS fins, sans onde P sinusale identifiable, avec trémulation continue de la ligne de base, définit une fibrillation atriale — à ne pas confondre avec un flutter (activité atriale monomorphe organisée).
**Hints :**
1. Le rythme ventriculaire est-il régulier ou irrégulier ?
2. Trouves-tu une onde P sinusale identifiable, ou la ligne de base est-elle trémulante en continu ?
3. Tachycardie irrégulière à QRS fins + trémulation continue = fibrillation atriale.
**required_concepts (proposé) :** `FIBRILLATION_ATRIALE`
**unsafe_errors (proposé) :** `FLUTTER_DROIT_TYPIQUE`

### Contrast — Cas 38
**Diagnostic golden :** Fibrillation atriale à réponse ventriculaire lente.
**Teaching point :** Une fibrillation atriale avec une cadence ventriculaire lente (~40/min) et des diastoles très irrégulières oriente vers une FA à réponse ventriculaire lente plutôt qu'un BAV complet — l'irrégularité marquée est l'argument clé qui élimine la dissociation atrioventriculaire régulière du BAV complet.
**Hints :**
1. Le rythme ventriculaire lent est-il parfaitement régulier, ou très irrégulier ?
2. Retrouves-tu une trémulation de la ligne de base (activité atriale anarchique) ou de vraies ondes P régulières ?
3. Rythme lent mais très irrégulier + trémulation anarchique = FA à réponse ventriculaire lente, pas un BAV complet (qui serait régulier).
**required_concepts (proposé) :** `FIBRILLATION_ATRIALE`, `REPONSE_VENTRICULAIRE_LENTE`
**unsafe_errors (proposé) :** `BAV_COMPLET`

### Integration — Cas 41
**Diagnostic golden :** Flutter atrial commun typique antihoraire, conduction AV 4/1.
**Teaching point :** Une activité atriale monomorphe rapide (~270/min) en dents de scie dans les dérivations inférieures, avec conduction atrioventriculaire fixe (ici 4/1), définit un flutter atrial commun typique antihoraire.
**Hints :**
1. L'activité atriale est-elle monomorphe organisée ou anarchique ?
2. Cherche l'aspect en dents de scie dans les dérivations inférieures.
3. Activité atriale monomorphe en dents de scie + conduction fixe = flutter typique, pas une fibrillation atriale.
**required_concepts (proposé) :** `FLUTTER_DROIT_TYPIQUE`
**unsafe_errors (proposé) :** `FIBRILLATION_ATRIALE`, `RYTHME_SINUSAL`

### Mastery — Cas 42 (test)
**Diagnostic golden :** Flutter atrial commun rapide à conduction 2/1, démasqué par manœuvre vagale.
**Teaching point :** Une tachycardie régulière à QRS fins (~170 bpm) peut cacher des ondes F de flutter à conduction 2/1 ; la manœuvre vagale (ou l'adénosine), en ralentissant transitoirement la conduction atrioventriculaire, démasque les ondes F en dents de scie sans interrompre le circuit du flutter lui-même.
**required_concepts (proposé) :** `FLUTTER_DROIT_TYPIQUE`
**unsafe_errors (proposé) :** *(à discuter : tachycardie jonctionnelle comme diagnostic différentiel plausible avant manœuvre vagale ?)*

---

## Points à trancher avant génération des JSON définitifs

1. **`bav-foundations`** : supprimer le bloc `remediation` (cas 29, déjà dans `bav-advanced`) ?
2. **Cas 26 (`BAV_2_POUR_1`)** : accepter Mobitz I/II comme non-erreur si argumenté par la largeur du QRS, ou les marquer strictement comme `unsafe_errors` ? non bav2 pour 1 c'est un bloc de haut grade, donc Mobitz I ou II ne sont pas des erreurs, mais des sous-types possibles. Donc je dirais de ne pas les mettre en unsafe_errors.    
3. **Cas 4/5** (hypertrophies atriales G/D) : HVG et HAG peuvent légitimement coexister — dois-je les mettre en `unsafe_errors` (risque de confusion) ou les retirer pour éviter de pénaliser une réponse cliniquement correcte ? les retirer
4. **Cas 1** (inversion d'électrodes) : ajouter une déviation axiale droite comme `unsafe_errors` ? oui
5. **Cas 14 et 42** : comment formuler des `unsafe_errors` pertinents (aucune confusion dangereuse évidente identifiée) — les laisser vides ou trouver un piège plus fin ? les laisser vides
6. Valider `estimated_minutes` (proposé 15-16 min par défaut, à ajuster si besoin). ok 
