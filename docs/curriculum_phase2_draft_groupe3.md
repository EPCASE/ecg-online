# Draft Curriculum Phase 2 — Groupe 3/3 (dernier groupe)

Ce document reprend le même format que `curriculum_phase2_draft_groupe2.md`.
Merci d'annoter directement ce fichier (réponses aux questions ouvertes, ajustements de hints/teaching points) puis de me le renvoyer pour validation avant génération des JSON.

Rappel : ce groupe couvre les 5 derniers parcours, pour un total de 15/15 parcours phase 2.

---

## 1. `malignant-rhythms-and-channelopathies` (Fondamental → Avancé, 4 cas seulement)

Cas : 50 (foundation), 51 (guided), 52 (contrast), 74 (mastery/integration)

> ⚠️ Ce parcours n'a que 4 cas (pas 5) selon `case_curriculum_map.json`. Pas de phase "integration" séparée — je propose de fusionner integration+mastery sur le cas 74 (Brugada), ou de garder 4 phases (foundation/guided/contrast/mastery). **Question ouverte Q1** : gardez-vous 4 phases (foundation/guided/contrast/mastery) sans "integration" ? ok fusionner integration+mastery sur le cas 74 (Brugada) pour ce parcours.

### Cas 50 — foundation
- Diagnostic : Fibrillation ventriculaire sur myocardiopathie ischémique post-infarctus (TV polymorphe → FV sur ESV à couplage court).
- Objective : Reconnaître la fibrillation ventriculaire et son contexte de survenue (séquelle de nécrose, ESV à couplage court).
- Teaching point : La FV se traduit par des QRS larges, polymorphes, irréguliers, sans organisation, à une fréquence non mesurable — urgence vitale absolue nécessitant un choc électrique immédiat. Le déclencheur classique est une extrasystole ventriculaire tombant sur l'onde T (phénomène R/T) sur un myocarde cicatriciel.
- Hints : (1) Le tracé de base est-il organisé ou anarchique ? (2) Cherchez la séquelle de nécrose sous-jacente. (3) Qu'est-ce qui a déclenché l'épisode ?
- Proposition `required_concepts`: `["FIBRILLATION_VENTRICULAIRE", "SEQUELLE_DE_NECROSE"]`
- Proposition `unsafe_errors`: `["TACHYCARDIE_VENTRICULAIRE_POLYMORPHE"]` (ne pas s'arrêter au stade pré-FV)

### Cas 51 — guided
- Diagnostic : Torsade de pointes.
- Objective : Différencier la torsade de pointes d'une TV polymorphe classique et d'une FV.
- Teaching point : La torsade de pointes est une TV polymorphe particulière avec axe des QRS variant progressivement ("torsion" autour de la ligne isoélectrique), sur QT long, souvent auto-résolutive, déclenchée par une ESV en contexte de QT long (médicamenteux, hypokaliémie).
- Hints : (1) Mesurez le QT avant/après l'épisode. (2) L'axe des QRS change-t-il progressivement pendant l'épisode ? (3) Quel contexte médicamenteux/métabolique favorisant ?
- Proposition `required_concepts`: `["TORSADE_DE_POINTES", "QT_LONG"]`
- Proposition `unsafe_errors`: `["FIBRILLATION_VENTRICULAIRE"]` (ne pas confondre avec FV : ici auto-résolutif et QT long identifiable)

### Cas 52 — contrast
- Diagnostic : FA pré-excitée sur WPW ("Wolf malin").
- Objective : Reconnaître la fibrillation atriale conduite par voie accessoire — piège classique car ressemble à une TV.
- Teaching point : Tachycardie irrégulière à QRS larges polymorphes (alternance de QRS fins/larges/intermédiaires, aspect "en accordéon"), à ne pas confondre avec une TV ni un BBG. Risque de dégénérescence en FV — CEE si instable, éviter les bloquants du nœud AV (digoxine, vérapamil, bêtabloquants) qui favorisent la conduction par la voie accessoire.
- Hints : (1) La tachycardie est-elle réellement régulière ? (2) Les QRS ont-ils tous la même morphologie ? (3) Contre-indication thérapeutique majeure à connaître.
- Proposition `required_concepts`: `["WOLF_MALIN", "FAISCEAU_ACCESSOIRE_A_CONDUCTION_ANTEROGRADE"]`
- Proposition `unsafe_errors`: `["TORSADE_DE_POINTES", "BLOC_DE_BRANCHE_GAUCHE"]` (négations golden explicites)

### Cas 74 — mastery
- Diagnostic : Syndrome de Brugada.
- Objective : Identifier l'aspect ECG typique de Brugada de type 1 (canalopathie, risque de mort subite).
- Teaching point : Sus-décalage ST en dôme (>2mm) en V1-V3 avec onde T négative, sans miroir — pattern électrique isolé, en dehors de tout contexte ischémique aigu. Diagnostic différentiel majeur du SCA ST+ antérieur mais contexte et morphologie diffèrent (dôme vs onde de Pardee, pas de miroir).
- Hints : (1) Quelle est la morphologie précise du sus-décalage (dôme vs convexe classique) ? (2) Y a-t-il un miroir ? (3) Contexte clinique évocateur (syncope, mort subite familiale) ?
- Proposition `required_concepts`: `["SYNDROME_DE_BRUGADA", "ASPECT_DE_BRUGADA_DE_TYPE_1"]`
- Proposition `unsafe_errors`: `[]` (pas de négation explicite dans le golden, mais on pourrait ajouter SCA ST+ antérieur en différentiel — **Question ouverte Q2** : ajouter `SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_AVEC_SUS_DECALAGE_DU_SEGMENT_ST` comme unsafe_error pour ce cas ?) non

---

## 2. `embolism-and-pericardium` (Intermédiaire)

Cas : 53 (foundation), 54 (guided), 55 (contrast), 56 (integration), 57 (mastery)

### Cas 53 — foundation
- Diagnostic : Embolie pulmonaire (forme non compliquée).
- Objective : Repérer les signes ECG évocateurs d'EP (tachycardie sinusale, S1Q3T3, aspect de retard droit).
- Teaching point : Le S1Q3T3 (onde S en DI, onde Q et T négative en DIII) associé à une tachycardie sinusale et un aspect de retard droit doit faire évoquer une EP, en l'absence de trouble majeur de repolarisation évocateur de SCA ST+.
- Hints : (1) La fréquence cardiaque est-elle normale ? (2) Cherchez l'aspect S1Q3T3. (3) Y a-t-il un sus-décalage ST évocateur de SCA ?
- Proposition `required_concepts`: `["EMBOLIE_PULMONAIRE", "TACHYCARDIE_SINUSALE"]`
- Proposition `unsafe_errors`: `["SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_AVEC_SUS_DECALAGE_DU_SEGMENT_ST"]`

### Cas 54 — guided
- Diagnostic : Choc obstructif sur EP massive / cœur pulmonaire aigu.
- Objective : Reconnaître les signes de gravité de l'EP (BBD complet nouveau, tachycardie).
- Teaching point : Dans l'EP massive, un BBD complet peut apparaître (surcharge ventriculaire droite aiguë), associé à S1Q3T3 et ondes T négatives antérieures (V1-V3) — l'ECG n'est ni sensible ni spécifique mais rarement normal dans l'EP massive.
- Hints : (1) Le BBD est-il complet ou incomplet ? (2) Où sont les ondes T négatives (antérieures vs inférieures) ? (3) L'ECG normal élimine-t-il une EP grave ?
- Proposition `required_concepts`: `["EMBOLIE_PULMONAIRE", "BLOC_DE_BRANCHE_DROIT_COMPLET"]`
- Proposition `unsafe_errors`: `[]`

### Cas 55 — contrast
- Diagnostic : Péricardite aiguë.
- Objective : Différencier la péricardite du SCA ST+ (sus-décalage diffus concave, sous-décalage PQ, absence de miroir/onde Q).
- Teaching point : Sus-décalage ST diffus concave vers le haut (plusieurs territoires, hors aVR/V1), sous-décalage du segment PQ (surtout DI-DII, sus-décalage en aVR), absence de systématisation coronaire et pas d'onde Q de nécrose — clés pour distinguer d'un SCA ST+.
- Hints : (1) Le sus-décalage respecte-t-il un territoire coronaire unique ? (2) Cherchez le sous-décalage du segment PQ. (3) Y a-t-il un miroir ou des ondes Q ?
- Proposition `required_concepts`: `["PERICARDITE", "SOUS_PQ"]`
- Proposition `unsafe_errors`: `["SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_AVEC_SUS_DECALAGE_DU_SEGMENT_ST"]`

### Cas 56 — integration
- Diagnostic : Épanchement péricardique abondant / aspect de tamponnade.
- Objective : Reconnaître le microvoltage et l'alternance électrique comme signes de tamponnade.
- Teaching point : Tachycardie sinusale + microvoltage diffus + alternance électrique des QRS (surtout V3-V4) constituent le trépied classique évocateur d'un épanchement péricardique abondant/tamponnade — ne pas confondre le microvoltage avec une hypertrophie atriale.
- Hints : (1) L'amplitude des QRS varie-t-elle d'un battement à l'autre ? (2) Le voltage global est-il faible ? (3) Fréquence cardiaque ?
- Proposition `required_concepts`: `["TAMPONNADE", "ALTERNANCE_DES_QRS", "MICROVOLTAGE"]`
- Proposition `unsafe_errors`: `["HYPERTROPHIE_ATRIALE_DROITE"]` (négation golden explicite)

### Cas 57 — mastery
- Diagnostic : Myocardite.
- Objective : Évoquer une myocardite devant un sus-décalage modéré sans miroir, en contexte viral/douleur thoracique.
- Teaching point : Sus-décalage ST modéré (souvent inférieur), QRS fins, absence de miroir — la myocardite est un diagnostic différentiel majeur du SCA ST+ à éliminer en cas de doute (troponine, contexte viral, IRM cardiaque).
- Hints : (1) Y a-t-il un miroir ? (2) Le contexte est-il évocateur (fièvre, syndrome viral récent) ? (3) Quel diagnostic différentiel principal à éliminer ?
- Proposition `required_concepts`: `["MYOCARDITE"]`
- Proposition `unsafe_errors`: `["SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_AVEC_SUS_DECALAGE_DU_SEGMENT_ST"]` (négation golden explicite)

---

## 3. `acs-st-elevation` (Avancé)

Cas : 58 (foundation), 59 (guided), 60 (contrast), 61 (integration), 62 (mastery)

### Cas 58 — foundation
- Diagnostic : SCA ST+ antéro-septo-apical.
- Objective : Identifier le territoire antérieur étendu (V1-V4 + DI/aVL) et l'onde de Pardee.
- Teaching point : Sus-décalage englobant l'onde T (onde de Pardee) de V1 à V4 + DI/aVL/aVR, avec miroir inférieur/V6 — évoque une occlusion proximale de l'IVA en amont de la première septale.
- Hints : (1) Quelles dérivations sont concernées ? (2) Où est le miroir ? (3) Quel territoire coronaire est probablement occlus ?
- Proposition `required_concepts`: `["SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_AVEC_SUS_DECALAGE_DU_SEGMENT_ST", "SEPTAL"]`
- Proposition `unsafe_errors`: `[]`

### Cas 59 — guided
- Diagnostic : SCA ST+ inférieur.
- Objective : Reconnaître le territoire inférieur systématisé (DII-DIII-aVF) avec miroir et ondes Q sans que celles-ci n'éliminent l'indication de reperfusion.
- Teaching point : Sus-décalage systématisé inférieur avec onde de Pardee, miroir en aVL/V2, ondes Q inférieures présentes dès la phase aiguë — ne pas conclure à tort que la présence d'ondes Q rend la reperfusion inutile.
- Hints : (1) Le territoire est-il systématisé ? (2) Où est le miroir ? (3) Les ondes Q contre-indiquent-elles la reperfusion ?
- Proposition `required_concepts`: `["SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_AVEC_SUS_DECALAGE_DU_SEGMENT_ST", "PRESENCE_D_ONDE_Q_PATHOLOGIQUE"]`
- Proposition `unsafe_errors`: `[]`

### Cas 60 — contrast
- Diagnostic : SCA ST+ inférieur avec extension VD, compliqué de dysfonction sinusale + échappement.
- Objective : Repérer une complication rythmique (dysfonction sinusale + échappement) associée à un SCA ST+ inférieur avec extension droite.
- Teaching point : L'extension au VD (sus-décalage V3R-V4R) et la dysfonction sinusale (absence d'onde P, rythme d'échappement) sont des complications fréquentes du SCA ST+ inférieur (artère coronaire droite proximale irrigant le nœud sinusal).
- Hints : (1) Cherchez le sus-décalage en dérivations droites V3R-V4R. (2) Voyez-vous des ondes P ? (3) Quelle est l'origine probable du rythme d'échappement ?
- Proposition `required_concepts`: `["VENTRICULE_DROIT", "DYSFONCTION_SINUSALE", "ECHAPPEMENT"]`
- Proposition `unsafe_errors`: `[]`

### Cas 61 — integration
- Diagnostic : SCA ST+ inférieur avec extension VD et postérieure, BAV 2/1.
- Objective : Reconnaître une extension postérieure (miroir V1-V2, à confirmer par V7-V9) et un trouble conductif associé (BAV 2/1).
- Teaching point : Devant un infarctus inférieur, l'ECG 18 dérivations est systématique pour rechercher une extension droite et postérieure. Une bradycardie à QRS fins avec BAV 2/1 peut compliquer un SCA inférieur (atteinte du nœud AV par l'artère coronaire droite).
- Hints : (1) Quel est le rapport R/S en V1-V2 ? (2) Pourquoi demander un 18 dérivations ? (3) Le rythme est-il régulier ?
- Proposition `required_concepts`: `["POSTERIEUR", "VENTRICULE_DROIT", "BAV_2_POUR_1"]`
- Proposition `unsafe_errors`: `[]`

### Cas 62 — mastery
- Diagnostic : SCA ST+ antérieur sur BBG complet (critères de Sgarbossa).
- Objective : Diagnostiquer un SCA ST+ malgré la présence d'un BBG complet — piège classique.
- Teaching point : Un BBG complet ne doit pas empêcher le diagnostic de SCA ST+ si le sus-décalage est très ample et concordant (ici V1-V4, >5mm en V2-V3) — évoquer les critères de Sgarbossa devant un contexte de douleur thoracique typique.
- Hints : (1) Un BBG élimine-t-il un diagnostic de SCA ST+ ? (2) L'amplitude du sus-décalage est-elle habituelle pour un simple trouble de repolarisation du BBG ? (3) Quel est le contexte clinique ?
- Proposition `required_concepts`: `["BLOC_DE_BRANCHE_GAUCHE_COMPLET", "SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_AVEC_SUS_DECALAGE_DU_SEGMENT_ST"]`
- Proposition `unsafe_errors`: `[]` (**Question ouverte Q3** : faut-il pénaliser explicitement une conclusion "BBG isolé" sans mention du SCA sous-jacent ? Il n'y a pas d'id ontologie dédié à ce piège précis, à confirmer.)

---

## 4. `acs-complex-and-nste` (Avancé)

Cas : 63 (foundation), 64 (guided), 66 (contrast), 67 (integration), 68 (mastery)

### Cas 63 — foundation
- Diagnostic : SCA ST+ antérieur compliqué de FV déclenchée par ESV.
- Objective : Associer un SCA ST+ antérieur typique à sa complication rythmique majeure (FV), sans la confondre avec une torsade/TV organisée/RIVA.
- Teaching point : Le sus-décalage antérieur (onde de Pardee en V5) précède la FV déclenchée par une ESV — reconnaître la FV (rythme extrêmement rapide, polymorphe, anarchique) et la distinguer d'une torsade (pas de QT long ici), d'une TV organisée, ou d'un RIVA (fréquence bien plus basse).
- Hints : (1) Le rythme initial est-il sinusal ? (2) Qu'est-ce qui déclenche l'épisode ? (3) En quoi ce rythme diffère-t-il d'une torsade ou d'un RIVA ?
- Proposition `required_concepts`: `["SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_AVEC_SUS_DECALAGE_DU_SEGMENT_ST", "FIBRILLATION_VENTRICULAIRE"]`
- Proposition `unsafe_errors`: `["TORSADE_DE_POINTES"]` (négation golden explicite)

### Cas 64 — guided
- Diagnostic : RIVA de reperfusion sur SCA ST+ inférieur/postérieur reperfusé.
- Objective : Reconnaître le RIVA comme signe de reperfusion (bénin), à ne pas confondre avec une TV.
- Teaching point : Le RIVA est un rythme ventriculaire focal, fréquence ~80/min (donc < 100/min, à la différence d'une TV), QRS larges, souvent avec complexe de fusion — signe indirect de reperfusion coronaire réussie, ne nécessite habituellement pas de traitement spécifique.
- Hints : (1) Quelle est la fréquence exacte du rythme ventriculaire ? (2) Voyez-vous un complexe de fusion ? (3) Ce rythme doit-il inquiéter dans ce contexte ?
- Proposition `required_concepts`: `["RYTHME_IDIOVENTRICULAIRE_ACCELERE", "COMPLEXE_DE_FUSION"]`
- Proposition `unsafe_errors`: `["TACHYCARDIE_VENTRICULAIRE"]` (négation golden explicite : fréquence < 100/min élimine la TV)

### Cas 66 — contrast
- Diagnostic : SCA sans sus-décalage (NSTEMI) antérieur.
- Objective : Différencier le NSTEMI du SCA ST+ (sous-décalage + ondes T négatives, sans sus-décalage).
- Teaching point : Sous-décalage significatif V1-V4 avec ondes T négatives, en l'absence de sus-décalage — évoque un NSTEMI antérieur (à confirmer par l'élévation enzymatique, orientant vers NSTEMI plutôt qu'angor instable).
- Hints : (1) Y a-t-il un sus-décalage ST ? (2) Quel est l'aspect des ondes T ? (3) Qu'est-ce qui distingue NSTEMI et angor instable sur le plan biologique ?
- Proposition `required_concepts`: `["SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_SANS_ELEVATION_DU_SEGMENT_ST"]`
- Proposition `unsafe_errors`: `[]`

### Cas 67 — integration
- Diagnostic : SCA sans sus-décalage associé à une FA rapide.
- Objective : Repérer une FA rapide comme facteur précipitant/masquant d'un SCA NSTEMI.
- Teaching point : Une FA rapide (~130 bpm, PR non mesurable) peut précipiter une ischémie myocardique par déséquilibre besoin/apport en O2 chez une patiente coronarienne — le sous-décalage ST diffus et les troubles de repolarisation orientent vers un angor instable secondaire dans ce contexte.
- Hints : (1) Le rythme est-il sinusal ? (2) Quel est l'aspect du segment ST ? (3) Comment la tachyarythmie peut-elle expliquer l'ischémie ?
- Proposition `required_concepts`: `["FIBRILLATION_ATRIALE", "SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_SANS_ELEVATION_DU_SEGMENT_ST"]`
- Proposition `unsafe_errors`: `[]`

### Cas 68 — mastery
- Diagnostic : Ischémie diffuse sévère (sus-décalage aVR/V1 + sous-décalage diffus) évocatrice de tronc commun/tritronculaire.
- Objective : Reconnaître le pattern à haut risque de lésion du tronc commun gauche ou tritronculaire.
- Teaching point : L'association sus-décalage ST en aVR (et V1) + sous-décalage diffus important (inférieur, V3-V6) est un pattern à très haut risque, évocateur d'une lésion du tronc commun gauche ou de lésions tritronculaires sévères — urgence coronarographique.
- Hints : (1) Quelles dérivations montrent un sus-décalage (aVR est-il concerné) ? (2) Le sous-décalage est-il localisé ou diffus ? (3) Quel est le niveau de risque de ce pattern ?
- Proposition `required_concepts`: `["SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_AVEC_SUS_DECALAGE_DU_SEGMENT_ST", "ISCHEMIQUE"]`
- Proposition `unsafe_errors`: `[]`

---

## 5. `ischemia-variants-and-metabolic` (Avancé, 6 cas)

Cas : 69 (foundation), 70 (guided), 71 (contrast), 72 (integration), 73 (mastery), 75 (?)

> ⚠️ Ce parcours a 6 cas (un de plus que la normale). Je propose de traiter le cas 75 (amylose) comme une phase "mastery2" ou bonus après le cas 73, ou de le fusionner avec 73 en un même palier "mastery". **Question ouverte Q4** : comment traiter le 6e cas (75) — phase bonus séparée, ou fusion avec 73 ? bonus séparée

### Cas 69 — foundation
- Diagnostic : Anévrisme du VG sur séquelle de nécrose antéro-septo-apicale + BBD complet.
- Objective : Reconnaître une séquelle ancienne (ondes Q, rabotage R) avec sus-décalage persistant évoquant un anévrisme, sans le confondre avec un BBG.
- Teaching point : Onde Q + rabotage de l'onde R de V1 à V4 (séquelle antéro-septo-apicale) avec sus-décalage persistant modéré évoque un anévrisme ventriculaire à distance de l'infarctus — le BBD complet associé (axe droit) ne doit pas être confondu avec un BBG ou un hémibloc antérieur gauche.
- Hints : (1) L'aspect QRS évoque-t-il un BBD ou un BBG ? (2) Le sus-décalage est-il aigu ou chronique (persistant) ? (3) Que suggère la persistance du sus-décalage à distance ?
- Proposition `required_concepts`: `["SEQUELLE_DE_NECROSE", "ANEVRYSME_VENTRICULAIRE", "BLOC_DE_BRANCHE_DROIT_COMPLET"]`
- Proposition `unsafe_errors`: `["BLOC_DE_BRANCHE_GAUCHE"]` (négation golden explicite)

### Cas 70 — guided
- Diagnostic : Angor spastique de Prinzmetal avec SCA ST+ inférieur transitoire.
- Objective : Évoquer un spasme coronaire devant un sus-décalage régressif spontanément/sous trinitrine.
- Teaching point : Le caractère transitoire et régressif du sus-décalage (souvent sous trinitrine), associé à des extrasystoles ventriculaires pendant l'épisode, oriente vers un angor spastique de Prinzmetal plutôt qu'une occlusion fixe.
- Hints : (1) Le sus-décalage est-il permanent ou transitoire ? (2) Quel traitement fait régresser les symptômes ? (3) Quelles arythmies peuvent accompagner l'épisode ?
- Proposition `required_concepts`: `["SYNDROME_CORONARIEN_A_LA_PHASE_AIGUE_AVEC_SUS_DECALAGE_DU_SEGMENT_ST"]`
- Proposition `unsafe_errors`: `[]`

### Cas 71 — contrast
- Diagnostic : Takotsubo.
- Objective : Évoquer le Takotsubo comme diagnostic d'exclusion devant des ondes T négatives géantes et un QT long, sans argument pour un BBG.
- Teaching point : Ondes T négatives géantes diffuses (inférieur + V2-V6) avec QT très allongé, en l'absence de BBG franc — le Takotsubo est un diagnostic différentiel de SCA à évoquer après exclusion d'une cause coronarienne (diagnostic d'exclusion).
- Hints : (1) Les ondes T sont-elles négatives de façon localisée ou diffuse ? (2) Le QT est-il normal ? (3) Ce diagnostic est-il un diagnostic de certitude ou d'exclusion ?
- Proposition `required_concepts`: `["TAKOTSUBO", "ONDE_T_NEGATIVE", "QT_LONG"]`
- Proposition `unsafe_errors`: `["BLOC_DE_BRANCHE_GAUCHE"]` (négation golden explicite)

### Cas 72 — integration
- Diagnostic : Hypokaliémie.
- Objective : Reconnaître l'onde U et l'allongement apparent du QT comme signes d'hypokaliémie, sans conclure à tort à une hyperkaliémie ou un BAV.
- Teaching point : Onde U ample avec allongement apparent du QT (en réalité QU) et contexte de traitement diurétique (furosémide) orientent vers une hypokaliémie — à ne pas confondre avec une hyperkaliémie (signes ECG opposés) ni sur-interpréter comme un BAV du 2e degré.
- Hints : (1) Cherchez une onde U après l'onde T. (2) Le QT est-il vraiment long ou est-ce un QU ? (3) Quel contexte médicamenteux est évocateur ?
- Proposition `required_concepts`: `["HYPOKALIEMIE", "ONDE_U"]`
- Proposition `unsafe_errors`: `["HYPERKALIEMIE"]` (négation golden explicite)

### Cas 73 — mastery
- Diagnostic : Hyperkaliémie menaçante.
- Objective : Reconnaître les signes de gravité de l'hyperkaliémie (ondes T amples pointues, QRS très élargis).
- Teaching point : Ondes T amples, pointues et symétriques + QRS extrêmement élargis (proche de 200ms, sans aspect typique de bloc de branche) sont des signes de gravité de l'hyperkaliémie menaçante — l'activité atriale peut disparaître, rendant le rythme sinusal non affirmable (mais ce n'est pas un trouble du rythme atrial primitif).
- Hints : (1) Quel est l'aspect des ondes T ? (2) La largeur du QRS est-elle celle d'un bloc de branche classique ? (3) Voit-on des ondes P ?
- Proposition `required_concepts`: `["HYPERKALIEMIE", "ONDE_T_AMPLE"]`
- Proposition `unsafe_errors`: `[]`

### Cas 75 — bonus/6e cas
- Diagnostic : Amylose cardiaque.
- Objective : Évoquer une amylose cardiaque devant un microvoltage périphérique contrastant avec un voltage précordial conservé et des pseudo-ondes Q.
- Teaching point : Microvoltage des dérivations périphériques (<5mm) avec voltage précordial conservé (QRS >10mm en V3-V4) et pseudo-ondes Q de nécrose en V1-V2 — pattern évocateur d'infiltration amyloïde du myocarde, à ne pas confondre avec une vraie séquelle de nécrose.
- Hints : (1) Comparez le voltage périphérique et précordial. (2) Les ondes Q en V1-V2 correspondent-elles à une vraie séquelle ? (3) Quel diagnostic infiltratif évoquer ?
- Proposition `required_concepts`: `["AMYLOSE", "MICROVOLTAGE"]`
- Proposition `unsafe_errors`: `["PRESENCE_D_ONDE_Q_PATHOLOGIQUE"]` (piège : pseudo-ondes Q à ne pas confondre avec vraie nécrose)

---

## Questions ouvertes récapitulatives

- **Q1** (`malignant-rhythms-and-channelopathies`, 4 cas) : garder 4 phases (foundation/guided/contrast/mastery) sans "integration" ?
- **Q2** (cas 74, Brugada) : ajouter le SCA ST+ antérieur comme `unsafe_error` (diagnostic différentiel), ou laisser vide comme dans le golden ?
- **Q3** (cas 62, SCA ST+ sur BBG) : existe-t-il/faut-il un unsafe_error dédié pour le piège "BBG isolé sans évoquer le SCA sous-jacent" ? Pas d'id ontologie identifié pour l'instant.
- **Q4** (`ischemia-variants-and-metabolic`, 6 cas) : comment traiter le 6e cas (75, amylose) — phase bonus après mastery, ou fusion avec cas 73 ?

## Estimation temps

Proposition : 15-16 min par parcours (cohérent avec groupe 2), sauf éventuellement `malignant-rhythms-and-channelopathies` (4 cas seulement) → 12-13 min ?
