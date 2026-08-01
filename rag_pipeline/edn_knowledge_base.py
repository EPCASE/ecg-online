"""
📚 EDN Knowledge Base — Cours SFC Item 231 structuré
=====================================================
Base de connaissances extraite du chapitre 15 de la SFC
(Item 231 — Électrocardiogramme : indications et interprétations).

Chaque entrée est indexée par ontology_id et contient :
  - rang_edn : "A", "B" ou "C"
  - titre_cours : titre de la section du cours
  - points_cles : phrases clés à retenir (pour feedback)
  - pieges_classiques : erreurs fréquentes à éviter
  - extrait_cours : extrait textuel condensé du cours SFC

Source : https://www.sfcardio.fr/publication/chapitre-15-item-231-electrocardiogramme-indications-et-interpretations/
Auteur : BMad Team — 2026-02-28
"""

from __future__ import annotations
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class EDNEntry:
    """Entrée de la knowledge base EDN pour un concept ECG."""
    ontology_ids: List[str]            # IDs ontologiques couverts par cette entrée
    rang_edn: str                       # "A", "B", ou "C"
    titre_cours: str                    # Section du cours SFC
    points_cles: List[str]             # Points à retenir
    pieges_classiques: List[str]       # Pièges / confusions fréquentes
    extrait_cours: str                 # Extrait condensé du cours


# ──────────────────────────────────────────────────────────────────────────────
# KNOWLEDGE BASE — indexée par thème, chaque thème couvre N ontology_ids
# ──────────────────────────────────────────────────────────────────────────────

EDN_ENTRIES: List[EDNEntry] = [

    # ══════════════════════════════════════════════════════════════════
    # I.A — ECG NORMAL
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=["RYTHME_SINUSAL"],
        rang_edn="A",
        titre_cours="I.A — ECG normal : rythme sinusal",
        points_cles=[
            "Le rythme sinusal est défini par une onde P positive en D2, D3, aVF avec un QRS après chaque P et une P avant chaque QRS.",
            "La fréquence cardiaque normale de repos est entre 50 et 100 bpm.",
            "Bradycardie = FC < 50 bpm, Tachycardie = FC > 100 bpm.",
            "FC = 300 / nombre de grands carreaux entre 2 QRS.",
        ],
        pieges_classiques=[
            "Ne pas confondre 'rythme sinusal' et 'rythme sinusal normal' : en BAV complet, le rythme atrial peut être sinusal mais l'ECG n'est pas en rythme sinusal normal.",
        ],
        extrait_cours=(
            "Le rythme sinusal est un rythme qui provient d'un automatisme du nœud sinusal. "
            "Il génère une onde P positive dans les dérivations inférieures (D2). "
            "Lorsqu'on dit 'rythme sinusal normal', on sous-entend un rythme sinusal associé "
            "à une descente normale par les voies de conduction (NAV, His, branches, Purkinje). "
            "Il y a alors une onde P devant chaque QRS et un QRS derrière chaque P."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "ECG_NORMAL",
            "PAS_D_ANOMALIE_DE_LE_REPOLARISATION",
            "ONDE_T_NORMALES",
        ],
        rang_edn="A",
        titre_cours="I.A — ECG normal : critères complets",
        points_cles=[
            "Affirmer qu'un ECG est normal impose d'être systématique sur tous les paramètres : rythme, conduction (PR/QRS/QT), axe, repolarisation.",
            "Repolarisation normale : ondes T positives dans toutes les dérivations sauf aVR (et parfois D3, aVL, V1 isolément selon l'orientation du cœur).",
            "Deux ondes T négatives dans un même territoire signent une anomalie pathologique.",
        ],
        pieges_classiques=[
            "Ne pas conclure trop vite à la normalité : la seule façon d'être sûr qu'un ECG est normal est d'être systématique sur tous les critères (rythme, PR, QRS, axe, ST, T, QT).",
        ],
        extrait_cours=(
            "Il est important de savoir affirmer qu'un ECG est normal ; la seule manière d'en être "
            "certain est d'être systématique. Sur un ECG normal, les ondes T sont positives partout "
            "sauf en aVR (et parfois D3, aVL ou V1 selon l'orientation du cœur). Deux ondes T négatives "
            "dans un même territoire signent une pathologie."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # I.B — BLOCS DE BRANCHE
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "BLOC_DE_BRANCHE_DROIT_COMPLET",
            "BLOC_DE_BRANCHE_DROIT",
            "BBD_COMPLET",
        ],
        rang_edn="A",
        titre_cours="I.B.1 — Bloc complet de branche droite",
        points_cles=[
            "Durée de QRS > 120 ms.",
            "En V1 : QRS globalement positif avec aspect RsR'.",
            "En V6 : aspect qRs avec onde S traînante et arrondie.",
            "La discordance appropriée signifie que la polarité des ondes T et des QRS n'est plus concordante.",
        ],
        pieges_classiques=[
            "Avant de décrire un trouble de conduction, toujours commencer par décrire le rythme atrial pour ne pas passer à côté d'une tachycardie supraventriculaire.",
            "Ne pas confondre un bloc de branche (sans conséquence immédiate) avec une TV (mortelle si non prise en charge) devant des QRS larges.",
        ],
        extrait_cours=(
            "Le bloc complet de branche droite se caractérise par : QRS > 120 ms, "
            "en V1 QRS globalement positif avec aspect RsR', en V6 aspect qRs avec onde S traînante. "
            "Le diagnostic se fait sur : durée QRS > 120 ms, puis aspect en V1 (positif = droit), "
            "puis vérification de l'aspect inverse en V6."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "BLOC_DE_BRANCHE_GAUCHE_COMPLET",
            "BLOC_DE_BRANCHE_GAUCHE",
        ],
        rang_edn="A",
        titre_cours="I.B.1 — Bloc complet de branche gauche",
        points_cles=[
            "Durée de QRS > 120 ms.",
            "En V1 : QRS globalement négatif, aspect rS ou QS.",
            "En V6, D1, aVL : notch (double pic) avec onde R exclusive.",
            "En présence d'un BBG, l'interprétation de la repolarisation antérieure est difficile.",
        ],
        pieges_classiques=[
            "La discordance appropriée du BBG avec sus-décalage ST en V1-V2 peut faire évoquer à tort un SCA avec ST.",
            "Devant une douleur thoracique persistante avec BBG, le diagnostic d'infarctus antérieur doit être évoqué et conduire à une évaluation rapide.",
        ],
        extrait_cours=(
            "Le BBG complet se caractérise par : QRS > 120 ms, en V1 QRS négatif (rS ou QS), "
            "en V6/D1/aVL notch avec onde R exclusive. La discordance appropriée du BBG en V1-V2 "
            "peut mimer un sus-décalage de ST. En contexte de douleur thoracique + BBG, "
            "il faut éliminer un SCA."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "BLOC_DE_BRANCHE_DROIT_INCOMPLET",
            "BLOC_DE_BRANCHE_GAUCHE_INCOMPLET",
            "BBG_INCOMPLET",
        ],
        rang_edn="B",
        titre_cours="I.B.1 — Blocs incomplets de branche",
        points_cles=[
            "Les blocs incomplets présentent les mêmes anomalies mais avec durée de QRS entre 100 et 120 ms.",
            "Leur intérêt séméiologique est plus faible.",
        ],
        pieges_classiques=[],
        extrait_cours=(
            "Les blocs incomplets de branche présentent les mêmes anomalies morphologiques "
            "qu'un bloc complet mais avec des QRS entre 100 et 120 ms."
        ),
    ),

    EDNEntry(
        ontology_ids=["BLOC_INTRAVENTRICULAIRE_ASPECIFIQUE"],
        rang_edn="B",
        titre_cours="I.B.1 — Bloc intraventriculaire aspécifique (diagnostic d'élimination)",
        points_cles=[
            "Diagnostic d'élimination devant un QRS large (> 120 ms) qui ne remplit "
            "ni les critères de bloc de branche droit (V1/V6) ni ceux de bloc de "
            "branche gauche (V1/V6/DI/aVL).",
        ],
        pieges_classiques=[
            "Ne pas conclure à un bloc de branche gauche ou droit par défaut devant "
            "un QRS large : vérifier explicitement les critères des deux avant de "
            "retenir un bloc indifférencié/aspécifique.",
        ],
        extrait_cours=(
            "Le bloc intraventriculaire aspécifique (ou bloc indifférencié) est un "
            "diagnostic d'élimination en présence d'un QRS large (> 120 ms) mais ne "
            "présentant pas les caractéristiques d'un bloc de branche droite ou gauche."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # I.B.2 — HÉMIBLOCS
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "HÉMIBLOC_ANTÉRIEUR_GAUCHE",
            "HBAG",
            "BLOC_FASCICULAIRE_ANTERIEUR_GAUCHE",
        ],
        rang_edn="A",
        titre_cours="I.B.2 — Hémibloc antérieur gauche",
        points_cles=[
            "Élargissement modéré du QRS (> 100 ms).",
            "Déviation axiale gauche au-delà de −30° (négativité de D2).",
            "L'HBAG est fréquent car la branche antérieure est superficielle et fragile.",
        ],
        pieges_classiques=[],
        extrait_cours=(
            "L'HBAG est caractérisé par un QRS > 100 ms avec déviation axiale gauche "
            "au-delà de −30° (négativité de D2). C'est un hémibloc fréquent car la branche "
            "antérieure gauche est superficielle et de petite taille."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "HÉMIBLOC_POSTÉRIEUR_GAUCHE",
            "HBPG",
        ],
        rang_edn="A",
        titre_cours="I.B.2 — Hémibloc postérieur gauche",
        points_cles=[
            "Déviation axiale droite > +90° (négativité en D1, aspect S1Q3).",
            "L'HBPG est rare car la branche postérieure est profonde.",
            "Toujours éliminer d'abord une inversion d'électrodes (P négative en D1).",
        ],
        pieges_classiques=[
            "Le premier diagnostic lorsque D1 est négatif n'est pas un HBPG mais une inversion de positionnement des électrodes frontales.",
        ],
        extrait_cours=(
            "L'HBPG est caractérisé par une déviation axiale droite > +90° (S1Q3) en l'absence "
            "de pathologie du VD ou de morphologie longiligne. L'HBPG est rare. "
            "Si D1 est négatif, penser d'abord à une inversion d'électrodes."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # I.B.3 — BLOCS BIFASCICULAIRES
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "BLOC_BIFASCICULAIRE",
        ],
        rang_edn="A",
        titre_cours="I.B.3 — Blocs bifasciculaires",
        points_cles=[
            "La séméiologie s'additionne : HBAG + BBD ou HBPG + BBD.",
            "QRS > 120 ms.",
            "Un bloc bifasciculaire suggère un risque de BAV complet infrahissien.",
            "Syncope + bloc bifasciculaire = hospitalisation en cardiologie avec télémétrie.",
        ],
        pieges_classiques=[
            "Le terme 'bloc trifasciculaire' est souvent utilisé par excès en présence d'un bloc bifasciculaire + BAV1. On ne sait pas si le BAV1 est nodal ou infrahissien sans exploration électrophysiologique.",
        ],
        extrait_cours=(
            "Un bloc bifasciculaire (BBG complet ou BBD + hémibloc) attire l'attention sur le risque "
            "que la 3e branche dysfonctionne. Syncope + bloc bifasciculaire = hospitalisation. "
            "Le BBG peut contribuer à une cardiopathie par désynchronisation de la contraction."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # I.B.4 — BAV
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "BAV_1",
            "BAV_1ER_DEGRÉ",
            "BAV_DE_TYPE_1",
        ],
        rang_edn="A",
        titre_cours="I.B.4 — BAV du 1er degré",
        points_cles=[
            "Allongement fixe et constant de PR > 200 ms sans onde P bloquée.",
            "L'intervalle PR explore la totalité de la conduction de la sortie du nœud sinusal jusqu'aux extrémités du réseau de Purkinje.",
        ],
        pieges_classiques=[],
        extrait_cours=(
            "Le BAV1 est un allongement fixe et constant de PR > 200 ms sans onde P bloquée."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "BAV_2_MOBITZ_1",
            "BAV_2_TYPE_WENCKEBACH",
            "BAV_2EME_DEGRÉ_MOBITZ_1",
        ],
        rang_edn="A",
        titre_cours="I.B.4 — BAV du 2e degré Mobitz 1 (Wenckebach)",
        points_cles=[
            "Allongement progressif du PR jusqu'au blocage d'une onde P (période de Luciani-Wenckebach).",
            "Siège habituellement suprahissien (nodal) → QRS fins.",
            "Considéré comme relativement bénin dans la majorité des cas.",
        ],
        pieges_classiques=[
            "Ne pas confondre Mobitz 1 (allongement progressif du PR) avec Mobitz 2 (PR fixe avant le blocage). La distinction est cruciale car le pronostic et la prise en charge diffèrent radicalement.",
        ],
        extrait_cours=(
            "BAV 2e degré Mobitz 1 (Luciani-Wenckebach) : allongement progressif du PR "
            "jusqu'au blocage d'une onde P. Siège habituellement suprahissien. "
            "Dans le BAV 2/1, on s'oriente vers un BAV suprahissien si les QRS sont fins."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "BAV_2_MOBITZ_2",
            "BAV_2EME_DEGRÉ_MOBITZ_2",
        ],
        rang_edn="A",
        titre_cours="I.B.4 — BAV du 2e degré Mobitz 2",
        points_cles=[
            "PR fixe et constant avant le blocage d'une onde P.",
            "Siège infrahissien → QRS souvent larges.",
            "Indication de pacemaker même en l'absence de symptôme.",
            "Plus grave que le Mobitz 1 : risque d'évolution vers le BAV complet.",
        ],
        pieges_classiques=[
            "Ne pas confondre Mobitz 1 et Mobitz 2 : Mobitz 1 = allongement progressif du PR (Wenckebach), Mobitz 2 = PR fixe avant le blocage. La confusion est une erreur classique aux EDN.",
            "Dans le BAV 2/1, on s'oriente vers un BAV infrahissien (Mobitz 2) si les QRS sont larges.",
        ],
        extrait_cours=(
            "BAV 2e degré Mobitz 2 : PR fixe avant le blocage d'une onde P. "
            "Siège infrahissien, souvent QRS larges. Indication de pacemaker même sans symptôme. "
            "Dans le BAV 2/1, QRS larges orientent vers un siège infrahissien (Mobitz 2)."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "BAV_3",
            "BAV_COMPLET",
            "BAV_3EME_DEGRÉ",
        ],
        rang_edn="A",
        titre_cours="I.B.4 — BAV du 3e degré (complet)",
        points_cles=[
            "Dissociation complète entre ondes P et QRS.",
            "Ondes P régulières à fréquence normale, QRS à échappement (jonctionnel 40-60 bpm ou ventriculaire 15-30 bpm).",
            "QRS fins = bloc nodal (suprahissien), QRS larges = bloc infrahissien.",
            "Indication de pacemaker dans tous les BAV infrahissiens.",
        ],
        pieges_classiques=[
            "Ne pas confondre la dissociation AV du BAV complet avec la dissociation ventriculo-atriale d'une TV.",
        ],
        extrait_cours=(
            "BAV 3e degré (complet) : dissociation complète entre P et QRS. "
            "Ondes P régulières à fréquence normale, QRS à rythme d'échappement. "
            "QRS fins → bloc nodal, QRS larges → bloc infrahissien."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "BAV_DE_HAUT_GRADE",
            "BAV_2_POUR_1",
        ],
        rang_edn="B",
        titre_cours="I.B.4 — BAV de haut grade et BAV 2 pour 1",
        points_cles=[
            "Le BAV 2/1 ne peut être classé ni Mobitz 1 ni Mobitz 2 (il n'y a qu'un seul PR avant chaque blocage, donc pas d'allongement progressif observable).",
            "On s'oriente vers un BAV infrahissien si les QRS sont larges, suprahissien si les QRS sont fins (et si du Mobitz 1 est présent à d'autres moments).",
        ],
        pieges_classiques=[
            "Ne pas essayer de classer à tort un BAV 2/1 en Mobitz 1 ou 2 : c'est un BAV de haut grade à part, dont le siège se déduit de la largeur du QRS.",
        ],
        extrait_cours=(
            "Dans le BAV 2/1, on s'oriente vers un BAV infrahissien si les QRS sont larges "
            "et suprahissien si les QRS sont fins et s'il existe du BAV2 Mobitz I à d'autres moments."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # I.B.5 — DYSFONCTION SINUSALE
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "DYSFONCTION_SINUSALE",
            "BRADYCARDIE_SINUSALE",
            "BLOC_SINO_ATRIAL",
            "RYTHME_D_ECHAPPEMENT_JONCTIONNEL",
            "DISSOCIATION_ATRIO_VENTRICULAIRE",
        ],
        rang_edn="A",
        titre_cours="I.B.5 — Dysfonction sinusale",
        points_cles=[
            "Seules deux structures peuvent entraîner une bradycardie : le nœud sinusal et le NAV.",
            "Pauses par manque intermittent d'une onde P = bloc sinoatrial du 2e degré.",
            "L'échappement jonctionnel apparaît quand le nœud sinusal fait défaut (P absente devant QRS, possible P rétrograde).",
        ],
        pieges_classiques=[],
        extrait_cours=(
            "La dysfonction sinusale peut se manifester par des pauses (BSA du 2e degré) "
            "ou un échappement jonctionnel. Seules deux structures peuvent causer une bradycardie : "
            "le nœud sinusal (dysfonction sinusale) ou le NAV (BAV)."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # I.C — TROUBLES DU RYTHME SUPRAVENTRICULAIRES
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "FIBRILLATION_ATRIALE",
            "FA",
            "ACFA",
            "REPONSE_VENTRICULAIRE_LENTE",
        ],
        rang_edn="A",
        titre_cours="I.C.1 — Fibrillation atriale",
        points_cles=[
            "La fibrillation atriale est le seul diagnostic en cas de tachycardie complètement irrégulière à QRS fins.",
            "Activation atriale anarchique → QRS irrégulièrement irréguliers (intervalles RR non multiples d'une valeur commune).",
            "L'activité sinusale est remplacée par des mailles amples ou une fine trémulation de la ligne de base.",
            "En l'absence de bloc de branche, les QRS sont fins.",
            "Réponse ventriculaire lente : cadence ventriculaire ralentie (souvent sous traitement freinateur ou par BAV associé), à distinguer d'un rythme d'échappement régulier.",
        ],
        pieges_classiques=[
            "On ne doit pas évoquer un flutter dès que les mailles de FA sont amples. L'activité atriale du flutter est monomorphe, celle de la FA est anarchique.",
            "Association FA + BAV complet : l'évoquer quand l'activité ventriculaire devient lente et régulière (échappement automatique).",
            "Association FA + bloc de branche = tachycardie irrégulière à QRS larges → ne pas confondre avec une TV.",
        ],
        extrait_cours=(
            "La fibrillation atriale correspond à une activation atriale anarchique. "
            "C'est une tachycardie entre 100 et 200 bpm à QRS irrégulièrement irréguliers. "
            "La FA est le seul diagnostic en cas de tachycardie complètement irrégulière à QRS fins. "
            "L'activité sinusale est remplacée par des mailles ou une fine trémulation de la ligne de base."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "FLUTTER_ATRIAL",
            "FLUTTER_DROIT_TYPIQUE",
            "FLUTTER_DROIT_TYPIQUE_INVERSE",
            "FLUTTER_ATRIAL_ATYPIQUE",
            "FLUTTER_GAUCHE",
            "FLUTTER_COMMUN",
        ],
        rang_edn="A",
        titre_cours="I.C.2 — Flutters atriaux",
        points_cles=[
            "Activité atriale monomorphe rapide (~300 bpm) sans retour à la ligne isoélectrique.",
            "Aspect en 'toit d'usine' ou 'dents de scie' des ondes F.",
            "Flutter typique antihoraire : F négatives en D2/D3/aVF, positives en V1, négatives en V6.",
            "Cadence ventriculaire usuelle : 150 bpm (transmission 2/1), mais aussi 100 (3/1), 75 (4/1).",
            "La conduction peut être variable (2/1, 3/1, alternance).",
        ],
        pieges_classiques=[
            "Ne pas confondre flutter (activité atriale monomorphe, organisée) et FA (activité anarchique).",
            "En cas de flutter 2/1 → FC à 150 bpm, les ondes F peuvent être masquées par les QRS. Utiliser les manœuvres vagales pour démasquer.",
        ],
        extrait_cours=(
            "Les flutters atriaux correspondent à une boucle d'activation atriale se répétant à l'identique. "
            "Activité monomorphe ~300 bpm, aspect en dents de scie. Flutter typique : F négatives en inférieur. "
            "Cadence ventriculaire usuelle 150 bpm (2/1). Manœuvres vagales utiles pour démasquer les ondes F."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "TACHYCARDIE_SINUSALE",
            "TACHYCARDIE_SUPRA_VENTRICULAIRE",
        ],
        rang_edn="A",
        titre_cours="I.C — Tachycardie sinusale vs tachycardie supraventriculaire",
        points_cles=[
            "La tachycardie sinusale est un rythme sinusal accéléré (> 100 bpm) : onde P sinusale (positive en D2/D3/aVF) devant chaque QRS, PR normal.",
            "Elle est le plus souvent réactionnelle (effort, fièvre, douleur, anxiété, anémie, hyperthyroïdie) et ne nécessite pas de traitement antiarythmique spécifique.",
            "À différencier des tachycardies supraventriculaires non sinusales (jonctionnelles, atriales, FA, flutter) dont l'onde P n'est pas sinusale ou est absente.",
        ],
        pieges_classiques=[
            "Ne pas traiter une tachycardie sinusale comme un trouble du rythme : chercher et traiter sa cause déclenchante plutôt que de la ralentir.",
        ],
        extrait_cours=(
            "La tachycardie sinusale est un rythme sinusal accéléré (FC > 100 bpm), le plus souvent "
            "réactionnelle à une cause sous-jacente (effort, fièvre, douleur, anémie). "
            "Elle se différencie des tachycardies supraventriculaires non sinusales par la morphologie "
            "de l'onde P (sinusale, positive en D2) devant chaque QRS avec PR normal."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "TACHYCARDIE_ATRIALE_FOCALE",
            "TACHYCARDIE_ATRIALE",
        ],
        rang_edn="C",
        titre_cours="I.C.3 — Tachycardies atriales focales",
        points_cles=[
            "Activité atriale monomorphe avec retour à la ligne de base entre les ondes P (différence avec le flutter).",
            "Warm-up / cool-down : accélération progressive initiale puis décélération.",
        ],
        pieges_classiques=[],
        extrait_cours=(
            "Les TAF sont des arythmies atriales focales par hyperautomatisme. "
            "L'activité atriale est monomorphe avec retour à la ligne de base entre les P. "
            "Caractérisées par un warm-up et cool-down."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "TACHYCARDIE_JONCTIONNELLE",
            "TACHYCARDIE_JONCTIONELLE",
            "TACHYCARDIE_PAR_RÉENTRÉE_INTRANODALE",
            "TACHYCARDIE_ORTHODROMIQUE",
        ],
        rang_edn="A",
        titre_cours="I.C.4 — Tachycardies jonctionnelles",
        points_cles=[
            "Tachycardies très régulières, souvent rapides autour de 200 bpm (130-260 bpm).",
            "Deux formes : réentrée intranodale (activité P non visible) et rythme réciproque (voie accessoire, P rétrograde à distance du QRS).",
            "Réduites par les manœuvres vagales ou l'adénosine IV.",
        ],
        pieges_classiques=[],
        extrait_cours=(
            "Les tachycardies jonctionnelles (maladie de Bouveret) sont des tachycardies très régulières "
            "~200 bpm. Deux formes : réentrée intranodale (P non visible) et rythme réciproque (voie accessoire). "
            "Réduites par manœuvres vagales ou adénosine IV."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # EXTRASYSTOLES
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "EXTRASYSTOLE_ATRIALE",
            "ESA",
        ],
        rang_edn="A",
        titre_cours="I.C.5 — Extrasystoles atriales",
        points_cles=[
            "Onde P prématurée de morphologie différente de l'onde P sinusale, suivie d'un QRS fin.",
            "L'onde P peut être masquée par l'onde T précédente.",
        ],
        pieges_classiques=[],
        extrait_cours=(
            "Les extrasystoles atriales montrent une onde P trop précoce de morphologie "
            "différente de P sinusale, suivie d'un QRS fin."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "EXTRASYSTOLE_VENTRICULAIRE",
            "ESV",
            "BIGÉMINISME",
            "TRIGÉMINISME",
            "BIGEMINISME_VENTRICULAIRE",
            "TRIGEMINISME_VENTRICULAIRE",
            "DOUBLET_ESV",
            "DOUBLET_VENTRICULAIRE",
            "TRIPLET_ESV",
            "MULTIPLES_ESV",
            "EXTRASYSTOLE_A_COUPLAGE_COURT",
        ],
        rang_edn="A",
        titre_cours="I.C.5 — Extrasystoles ventriculaires",
        points_cles=[
            "QRS large prématuré ± onde P rétrograde.",
            "Bigéminisme = un battement sur deux, trigéminisme = un battement sur trois.",
            "Doublet = 2 ESV consécutives, triplet = 3 (au-delà, on parle de TV non soutenue).",
            "Des ESV fréquentes ou polymorphes doivent faire rechercher une cardiopathie.",
            "Une ESV à couplage très court (tombant sur l'onde T précédente, phénomène R/T) est un facteur déclenchant classique de torsade de pointes ou de fibrillation ventriculaire.",
        ],
        pieges_classiques=[
            "Ne pas banaliser une extrasystole ventriculaire à couplage très court : le risque de dégénérescence en trouble du rythme ventriculaire grave est plus élevé qu'une ESV isolée à couplage normal.",
        ],
        extrait_cours=(
            "Les ESV sont des QRS larges prématurés. Bigéminisme = 1 sur 2, trigéminisme = 1 sur 3, "
            "doublet = 2 ESV consécutives. Des ESV fréquentes ou polymorphes doivent faire rechercher "
            "une cardiopathie. Une ESV à couplage très court (phénomène R/T) est un facteur déclenchant "
            "classique de torsade de pointes ou de fibrillation ventriculaire."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # I.D — TROUBLES DU RYTHME VENTRICULAIRE
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "TACHYCARDIE_VENTRICULAIRE",
            "TV",
            "TACHYCARDIE_VENTRICULAIRE_CICATRICIELLE",
            "TACHYCARDIE_VENTRICULAIRE_MONOMORPHE",
            "TACHYCARDIE_VENTRICULAIRE_POLYMORPHE",
            "TVNS",
            "CAPTURE_SUPRAVENTRICULAIRE",
        ],
        rang_edn="A",
        titre_cours="I.D.1 — Tachycardies ventriculaires",
        points_cles=[
            "RÈGLE D'OR : Toute tachycardie régulière à QRS larges est une TV jusqu'à preuve du contraire.",
            "Suspicion : tachycardie (FC > 100 bpm) + QRS > 120 ms pour ≥3 battements.",
            "TVNS = entre 3 battements et 30 secondes. TV soutenue = > 30 secondes.",
            "Arguments de certitude : dissociation ventriculo-atriale, complexes de capture ou de fusion.",
            "Un complexe de capture (QRS fin précédé d'une onde P) ne peut exister que s'il y a dissociation ventriculo-atriale : il prouve indirectement le diagnostic de TV.",
            "Arguments en faveur : cardiopathie sous-jacente, concordance positive/négative V1-V6, déviation axiale extrême.",
        ],
        pieges_classiques=[
            "Ne pas confondre un bloc de branche (sans conséquence immédiate) avec une TV (mortelle si non prise en charge) devant des QRS larges.",
            "La suspicion de TV impose de donner l'alerte (appeler le 15).",
        ],
        extrait_cours=(
            "Les TV naissent sous la bifurcation hissienne → QRS larges. "
            "Règle : toute tachycardie régulière à QRS larges est une TV jusqu'à preuve du contraire. "
            "Suspicion = FC > 100 + QRS > 120 ms × ≥3 battements. "
            "Arguments de certitude : dissociation VA, captures (QRS fin précédé d'une P), fusions. "
            "La TV est un état instable, prémonitoire de l'arrêt cardiaque."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "RYTHME_IDIOVENTRICULAIRE_ACCELERE",
        ],
        rang_edn="C",
        titre_cours="I.D.1 bis — Rythme idioventriculaire accéléré (RIVA)",
        points_cles=[
            "Rythme ventriculaire régulier, à QRS larges, mais à fréquence relativement lente (40-120 bpm) — contrairement à la TV qui est > 100 bpm avec un contexte de tachycardie franche.",
            "Souvent bénin, classiquement observé lors de la reperfusion après désobstruction coronaire dans le SCA avec sus-décalage du ST.",
        ],
        pieges_classiques=[
            "Ne pas traiter un RIVA comme une TV : il est le plus souvent bien toléré et ne nécessite pas d'antiarythmique, surtout dans le contexte post-reperfusion.",
        ],
        extrait_cours=(
            "Le RIVA est un rythme ventriculaire régulier à QRS larges mais à fréquence relativement "
            "lente (40-120 bpm), classiquement observé à la reperfusion après désobstruction coronaire. "
            "Il est généralement bénin, à ne pas confondre avec une TV."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "FIBRILLATION_VENTRICULAIRE",
            "CARDIOVERSION_ELECTRIQUE",
        ],
        rang_edn="A",
        titre_cours="I.D.2 — Fibrillation ventriculaire",
        points_cles=[
            "Urgence absolue → cardioversion électrique immédiate.",
            "Tachycardie irrégulière à QRS larges polymorphes.",
            "Perte de connaissance en quelques secondes, pouls aboli → arrêt cardiaque.",
        ],
        pieges_classiques=[],
        extrait_cours=(
            "La FV est une urgence absolue nécessitant une cardioversion électrique immédiate. "
            "ECG : tachycardie irrégulière à QRS larges polymorphes. "
            "Le patient perd connaissance en quelques secondes (débit cardiaque nul)."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "TORSADE_DE_POINTES",
        ],
        rang_edn="B",
        titre_cours="I.D.3 — Torsades de pointes",
        points_cles=[
            "TV polymorphe associée à un QT long.",
            "Peut s'arrêter spontanément ou dégénérer en FV.",
            "Causes : bradycardie extrême, hypokaliémie, hypocalcémie, hypomagnésémie, médicaments allongeant le QT, QT long congénital.",
            "Un QT allongé doit alerter → vérifier médicaments et ionogramme.",
        ],
        pieges_classiques=[
            "La torsade de pointes peut être impossible à différencier d'une FV sur l'aspect ECG seul. Le contexte (QT long, médicaments) permet le diagnostic.",
        ],
        extrait_cours=(
            "La torsade de pointes est une TV polymorphe sur QT long. "
            "Causes : bradycardie extrême, hypokaliémie, hypocalcémie, médicaments allongeant le QT, "
            "syndrome du QT long congénital. Un QT allongé doit alerter : vérifier ionogramme et médicaments."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # I.E — HYPERTROPHIES
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "HYPERTROPHIE_VENTRICULAIRE_GAUCHE",
            "HVG",
        ],
        rang_edn="A",
        titre_cours="I.E.2 — Hypertrophie ventriculaire gauche",
        points_cles=[
            "Indice de Sokolow : S(V1 ou V2) + R(V5 ou V6) > 35 mm.",
            "Forme sévère : onde T négative en dérivations latérales (D1, aVL, V5, V6) + sous-décalage ST.",
            "Étiologie la plus fréquente : HTA, puis rétrécissement aortique.",
        ],
        pieges_classiques=[
            "Attention aux aspects trompeurs de pseudo-nécrose en V1/V2 : une HVG importante peut donner un aspect QS qui mime une séquelle d'infarctus.",
        ],
        extrait_cours=(
            "L'HVG se manifeste par un Sokolow > 35 mm. Forme sévère : onde T négative "
            "en latéral avec sous-décalage ST. Étiologie la plus fréquente : HTA. "
            "Attention aux pseudo-nécroses en V1-V2."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "HYPERTROPHIE_VENTRICULAIRE_DROITE",
            "HVD",
        ],
        rang_edn="B",
        titre_cours="I.E.3 — Hypertrophie ventriculaire droite",
        points_cles=[
            "Déviation axiale droite > 90-110°.",
            "En V1 : onde R ample > 6 mm.",
            "Association fréquente à une hypertrophie atriale droite.",
            "Dans l'embolie pulmonaire : aspect S1Q3T3.",
        ],
        pieges_classiques=[
            "Aspect S1Q3T3 de l'embolie pulmonaire : ne pas confondre avec un infarctus inférieur.",
            "Onde T négative en V1-V3 dans les formes sévères : ne pas confondre avec une ischémie myocardique.",
        ],
        extrait_cours=(
            "L'HVD se manifeste par une déviation axiale droite, R ample en V1. "
            "Dans l'embolie pulmonaire : aspect S1Q3T3. Attention à ne pas confondre "
            "les T négatives en V1-V3 avec une ischémie."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "HYPERTROPHIE_ATRIALE_DROITE",
            "HYPERTROPHIE_ATRIALE_GAUCHE",
        ],
        rang_edn="B",
        titre_cours="I.E.1 — Hypertrophies atriales",
        points_cles=[
            "HAD : onde P > 2,5 mm en amplitude en D2, ou > 2 mm en V1/V2.",
            "HAG : onde P de durée > 110-120 ms, composante négative > 40 ms en V1.",
        ],
        pieges_classiques=[],
        extrait_cours=(
            "HAD : P > 2,5 mm en D2 (souvent pointue). HAG : P > 120 ms, composante négative en V1."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # I.F — DYSKALIÉMIES
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "HYPOKALIÉMIE",
        ],
        rang_edn="A",
        titre_cours="I.F.1 — Hypokaliémie",
        points_cles=[
            "Onde T plate ou négative, diffuse, avec ST sous-décalé.",
            "QRS normal.",
            "Allongement de QT, apparition d'une onde U.",
            "Risque de TV, torsade de pointes, FV.",
        ],
        pieges_classiques=[
            "L'onde U ne doit pas être intégrée dans la mesure du QT.",
        ],
        extrait_cours=(
            "L'hypokaliémie donne : T plate/négative diffuse, ST sous-décalé, QRS normal, "
            "allongement QT, onde U. Risque : ESV, TV, torsade de pointes, FV."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "HYPERKALIÉMIE",
        ],
        rang_edn="A",
        titre_cours="I.F.1 — Hyperkaliémie",
        points_cles=[
            "Onde T ample, pointue et symétrique.",
            "Allongement de PR.",
            "Élargissement de QRS.",
            "Risque de BAV, TV, dysfonction sinusale.",
        ],
        pieges_classiques=[],
        extrait_cours=(
            "L'hyperkaliémie donne : onde T ample, pointue, symétrique, allongement PR, "
            "élargissement QRS. Risque : BAV, TV, dysfonction sinusale."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # I.F.2 — PÉRICARDITE
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "PÉRICARDITE_AIGUË",
            "PÉRICARDITE",
            "MICROVOLTAGE",
        ],
        rang_edn="B",
        titre_cours="I.F.2 — Péricardite aiguë",
        points_cles=[
            "Phase 1 : microvoltage + sus-décalage ST concave vers le haut, diffus, concordant, sans miroir + sous-décalage de PQ.",
            "Différence avec SCA : sus-décalage diffus, concave vers le haut, sans miroir.",
            "4 phases évolutives classiques.",
        ],
        pieges_classiques=[
            "Ne pas conclure à tort à une péricardite devant un SCA avec sus-décalage de ST, car l'image en miroir peut être absente.",
        ],
        extrait_cours=(
            "La péricardite aiguë se manifeste par un sus-décalage ST concave vers le haut, "
            "diffus, concordant, sans miroir, et un sous-décalage de PQ. "
            "Ne pas confondre avec un SCA (l'image en miroir du SCA peut être absente)."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # I.F.3 — PRÉEXCITATION / WPW
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "PRÉEXCITATION_VENTRICULAIRE",
            "WOLFF_PARKINSON_WHITE",
            "WPW",
            "FAISCEAU_ACCESSOIRE_A_CONDUCTION_ANTEROGRADE",
            "WOLF_MALIN",
            "TJ_ORTHODROMIQUE_UTILISANT_UNE_VOIE_ACCESSOIRE",
            "TJ_ANTIDROMIQUE_UTILISANT_UNE_VOIE_ACCESSOIRE",
        ],
        rang_edn="B",
        titre_cours="I.F.3 — Préexcitation / Wolff-Parkinson-White",
        points_cles=[
            "PR court (< 120 ms).",
            "Élargissement de QRS par onde δ (empâtement du pied de QRS).",
            "Risque de mort subite si la voie accessoire a une période réfractaire courte (pas de filtre comme le NAV).",
            "FA préexcitée ('super-Wolff') : tachycardie irrégulière à QRS larges de taille variable ('en accordéon').",
        ],
        pieges_classiques=[
            "L'adénosine est contre-indiquée en cas de FA préexcitée (super-Wolff).",
        ],
        extrait_cours=(
            "La préexcitation se manifeste par un PR court < 120 ms et une onde δ. "
            "WPW = voie accessoire + palpitations par réentrée. "
            "FA préexcitée (super-Wolff) : tachycardie irrégulière à QRS larges en accordéon. "
            "Contre-indication de l'adénosine dans cette situation."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # I.F.4 — MALADIE CORONARIENNE / SCA
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "SYNDROME_CORONARIEN_À_LA_PHASE_AIGUE_AVEC_SUS_DÉCALAGE_DU_SEGMENT_ST",
            "INFARCTUS_DU_MYOCARDE_À_LA_PHASE_AIGUE",
            "ISCHÉMIE_SOUS_ENDOCARDIQUE",
            "ISCHÉMIE_SOUS_ÉPICARDIQUE",
            "COURANT_DE_LESION_SOUS_EPICARDIQUE",
            "COURANT_DE_LESION_SOUS_ENDOCARDIQUE",
            "SYNDROME_CORONARIEN_À_LA_PHASE_AIGUE_SANS_ÉLÉVATION_DU_SEGMENT_ST",
            "ONDE_Q_DE_NÉCROSE",
            "SEQUELLE_DE_NECROSE",
            "CARDIOPATHIE_ISCHEMIQUE_CHRONIQUE",
            "ANEVRYSME_VENTRICULAIRE",
        ],
        rang_edn="A",
        titre_cours="I.F.4 — Maladie coronarienne / Syndromes coronariens aigus",
        points_cles=[
            "Traquer le sus-décalage (territoire occlus) puis chercher le miroir (sous-décalage).",
            "Sus-décalage significatif : ≥2 mm en V1-V3, ≥1 mm ailleurs, dans ≥2 dérivations adjacentes.",
            "Onde de Pardee : sus-décalage ST englobant l'onde T.",
            "SCA sans ST : sous-décalage ST, inversion des T, pseudo-normalisation des T, aplatissement des T, ou ECG normal.",
            "Ondes Q de nécrose : ≥1/3 du QRS en amplitude et > 30-40 ms.",
            "Sous-décalage en antérieur (V1-V3) = penser au miroir d'un sus-décalage postérieur → ECG 18 dérivations.",
            "Séquelle de nécrose (cardiopathie ischémique chronique) : ondes Q de nécrose persistantes, sans sus-décalage ST évolutif.",
            "Anévrisme ventriculaire : sus-décalage ST persistant à distance d'un infarctus, associé à des ondes Q séquellaires.",
        ],
        pieges_classiques=[
            "Au cours des SCA avec ST, ne pas confondre la lésion et son miroir.",
            "Ne pas confondre une onde de Pardee avec un élargissement de QRS.",
            "Ne pas évoquer à tort une péricardite devant un SCA.",
            "BBG + douleur thoracique = éliminer SCA.",
            "5 étiologies de sus-décalage ST : SCA, anévrisme ventriculaire, repolarisation précoce, angor de Prinzmetal, péricardite.",
        ],
        extrait_cours=(
            "SCA avec ST : traquer le sus-décalage (≥2 mm en V1-V3, ≥1 mm ailleurs), chercher le miroir. "
            "Onde de Pardee = sus-décalage englobant l'onde T. "
            "SCA sans ST : sous-décalage, T négatives, pseudo-normalisation, T plates, ou ECG normal. "
            "Ondes Q de nécrose : ≥1/3 du QRS, > 30-40 ms. "
            "5 causes de sus-décalage : SCA, anévrisme, repolarisation précoce, Prinzmetal, péricardite."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # STIMULATEUR CARDIAQUE
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "STIMULATEUR_CARDIAQUE",
            "PACEMAKER",
            "STIMULATION_VENTRICULAIRE",
            "STIMULATION_ATRIALE",
            "STIMULATION_SÉQUENTIELLE",
        ],
        rang_edn="B",
        titre_cours="I.F.5 — ECG et stimulateur cardiaque",
        points_cles=[
            "Le spike de stimulation est pathognomonique d'une stimulation cardiaque.",
            "Stimulation atriale : spike + onde P.",
            "Stimulation ventriculaire : spike + QRS large (aspect BBG car stimulation VD).",
            "Indications pacemaker : bradycardies symptomatiques, BAV infrahissiens même sans symptôme.",
        ],
        pieges_classiques=[],
        extrait_cours=(
            "Le spike de stimulation (0,4-1 ms) est pathognomonique. "
            "Stimulation atriale = spike + P. Stimulation ventriculaire = spike + QRS large (aspect BBG). "
            "Unipolaire = bien visible, bipolaire = peu visible sur ECG de surface."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # EMBOLIE PULMONAIRE
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "EMBOLIE_PULMONAIRE",
        ],
        rang_edn="B",
        titre_cours="I.E.3 — Embolie pulmonaire (signes ECG)",
        points_cles=[
            "Aspect S1Q3T3 : onde S en D1, onde Q en D3, onde T négative en D3.",
            "Déviation axiale droite, tachycardie sinusale, BBD.",
            "Peut être associée à une FA.",
        ],
        pieges_classiques=[
            "L'aspect S1Q3T3 n'est pas spécifique de l'EP.",
        ],
        extrait_cours=(
            "L'embolie pulmonaire peut donner un aspect S1Q3T3, une déviation axiale droite, "
            "une tachycardie sinusale, un BBD. Souvent associée à une FA."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # QT LONG
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "QT_LONG",
            "ALLONGEMENT_QT",
            "MEDICAMENTS",
        ],
        rang_edn="A",
        titre_cours="I.F.1 — Allongement de l'intervalle QT",
        points_cles=[
            "QT corrigé (Bazett) = QT mesuré / √(RR en secondes).",
            "QTc normal < 440 ms à 60 bpm.",
            "Causes : médicamenteuses (antiarythmiques, psychotropes, antibiotiques, antiémétiques, antipaludéens), congénitales, ioniques (hypokaliémie, hypocalcémie, hypomagnésémie).",
            "Un QT allongé expose au risque de torsade de pointes → vérifier ionogramme et médicaments.",
        ],
        pieges_classiques=[
            "Si une onde U est présente, elle ne doit pas être incluse dans la mesure du QT.",
        ],
        extrait_cours=(
            "Le QT est corrigé par la formule de Bazett : QTc = QT / √(RR). "
            "Normal < 440 ms. Un QT allongé doit alerter : vérifier médicaments (antiarythmiques, "
            "psychotropes, antibiotiques...) et ionogramme pour prévenir les torsades de pointes."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "QT_COURT",
        ],
        rang_edn="C",
        titre_cours="I.F.1 bis — QT court",
        points_cles=[
            "Anomalie inverse du QT long : intervalle QT raccourci pour la fréquence cardiaque, à mesurer avec la même méthode (Bazett) que le QT long.",
            "Peut être d'origine génétique (canalopathie rare) ou favorisé par une hyperkaliémie/hypercalcémie.",
        ],
        pieges_classiques=[
            "Toujours corriger le QT par la fréquence cardiaque (Bazett) avant de conclure à un QT anormalement court : un QT apparemment court peut simplement refléter une bradycardie.",
        ],
        extrait_cours=(
            "Le QT court est l'anomalie inverse du QT long, mesuré et corrigé selon la même "
            "méthode (formule de Bazett). Il peut être génétique ou favorisé par une dyskaliémie/"
            "dyscalcémie."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # REPOLARISATION PRÉCOCE
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "REPOLARISATION_PRÉCOCE",
        ],
        rang_edn="B",
        titre_cours="I.F.4 — Repolarisation précoce",
        points_cles=[
            "Sus-décalage de ST dans les dérivations inférolatérales.",
            "Une des 5 étiologies de sus-décalage du segment ST.",
        ],
        pieges_classiques=[
            "Ne pas confondre avec un SCA ou une péricardite.",
        ],
        extrait_cours=(
            "La repolarisation précoce donne un sus-décalage ST dans les dérivations inférolatérales. "
            "C'est un diagnostic différentiel du SCA et de la péricardite."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # ARTEFACTS TECHNIQUES
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "INVERSION_D_ELECTRODES",
        ],
        rang_edn="B",
        titre_cours="Artefact technique — Inversion d'électrodes",
        points_cles=[
            "Inversion bras droit/bras gauche : onde P, QRS et T négatifs en DI, avec aVR positif (aspect en miroir des dérivations des membres).",
            "À évoquer devant un tracé discordant avec la clinique avant de conclure à une pathologie.",
        ],
        pieges_classiques=[
            "Ne pas interpréter à tort une inversion d'électrodes comme un trouble du rythme ou une dextrocardie.",
        ],
        extrait_cours=(
            "Une inversion des électrodes des membres (typiquement bras droit/bras gauche) donne un "
            "tracé en miroir : onde P, QRS et T négatifs en DI et aVR positif. Il faut y penser devant "
            "un ECG discordant avec la clinique avant d'évoquer une pathologie."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "ARYTHMIE_SINUSALE",
        ],
        rang_edn="B",
        titre_cours="I.A — Arythmie sinusale",
        points_cles=[
            "Variation physiologique de la fréquence cardiaque liée à la respiration (accélération à l'inspiration).",
            "Rythme reste sinusal (onde P positive en D2, D3, aVF) : ne pas confondre avec un trouble du rythme.",
        ],
        pieges_classiques=[
            "Fréquente chez le sujet jeune et sportif : ne pas la confondre avec une pathologie du nœud sinusal.",
        ],
        extrait_cours=(
            "L'arythmie sinusale correspond à une variation physiologique, le plus souvent respiratoire, "
            "de la fréquence cardiaque en rythme sinusal. Elle n'a pas de caractère pathologique."
        ),
    ),

    # ══════════════════════════════════════════════════════════════════
    # AUTRES CAUSES DE SUS-DÉCALAGE / PATHOLOGIES HORS ITEM 231
    # (contenu bref, ces items relèvent d'autres items EDN — cardiomyopathies,
    #  péricardite/myocardite, mort subite — le programme Item 231 ne les
    #  détaille pas ; entrées volontairement synthétiques)
    # ══════════════════════════════════════════════════════════════════

    EDNEntry(
        ontology_ids=[
            "SYNDROME_DE_BRUGADA",
            "ASPECT_DE_BRUGADA_DE_TYPE_1",
        ],
        rang_edn="B",
        titre_cours="Canalopathie — Syndrome de Brugada",
        points_cles=[
            "Type 1 : sus-décalage ST 'en dôme' > 2 mm suivi d'une onde T négative en V1-V2.",
            "Risque de mort subite par TV/FV, souvent d'origine génétique.",
        ],
        pieges_classiques=[
            "Ne pas confondre avec un bloc de branche droit ou un SCA antérieur.",
        ],
        extrait_cours=(
            "Le syndrome de Brugada de type 1 se manifeste par un sus-décalage ST en dôme en V1-V2 "
            "suivi d'une onde T négative, avec un risque de mort subite rythmique."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "TAKOTSUBO",
        ],
        rang_edn="C",
        titre_cours="Cardiomyopathie de stress — Takotsubo",
        points_cles=[
            "Peut mimer un SCA avec sus-décalage ST, souvent déclenché par un stress intense.",
            "Coronarographie normale malgré l'aspect ECG évocateur d'ischémie.",
        ],
        pieges_classiques=[
            "Diagnostic différentiel du SCA : ne pas l'affirmer sans coronarographie.",
        ],
        extrait_cours=(
            "Le syndrome de Takotsubo mime un SCA à l'ECG (sus-décalage ST) mais les coronaires "
            "sont angiographiquement normales ; il est déclenché par un stress physique ou émotionnel intense."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "TAMPONNADE",
        ],
        rang_edn="B",
        titre_cours="Complication péricardique — Tamponnade",
        points_cles=[
            "Microvoltage et alternance électrique (variation d'amplitude des QRS d'un battement à l'autre).",
            "Tachycardie sinusale quasi constante.",
        ],
        pieges_classiques=[
            "L'ECG seul ne fait pas le diagnostic : l'échocardiographie est indispensable.",
        ],
        extrait_cours=(
            "La tamponnade péricardique peut se traduire par un microvoltage et une alternance "
            "électrique (variation d'amplitude des QRS), associés à une tachycardie sinusale."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "MYOCARDITE",
        ],
        rang_edn="B",
        titre_cours="Atteinte myocardique — Myocardite",
        points_cles=[
            "ECG souvent peu spécifique : troubles de repolarisation, parfois aspect pseudo-SCA ou troubles du rythme/conduction.",
            "Peut se compliquer de troubles du rythme ventriculaire ou de BAV.",
        ],
        pieges_classiques=[
            "Un ECG normal n'élimine pas une myocardite.",
        ],
        extrait_cours=(
            "La myocardite peut donner un ECG normal ou des anomalies non spécifiques (troubles de "
            "repolarisation, troubles du rythme ou de conduction), parfois un aspect pseudo-SCA."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "AMYLOSE",
        ],
        rang_edn="C",
        titre_cours="Cardiopathie infiltrative — Amylose cardiaque",
        points_cles=[
            "Microvoltage contrastant avec un épaississement pariétal important à l'échographie.",
            "Association évocatrice : microvoltage + hypertrophie pariétale échographique.",
        ],
        pieges_classiques=[
            "Ne pas conclure à tort à une HVG devant l'épaississement pariétal : le microvoltage électrique oriente vers l'amylose.",
        ],
        extrait_cours=(
            "L'amylose cardiaque associe classiquement un microvoltage électrique à un épaississement "
            "pariétal important en échographie, discordance évocatrice du diagnostic."
        ),
    ),

    EDNEntry(
        ontology_ids=[
            "ISCHEMIQUE",
        ],
        rang_edn="A",
        titre_cours="I.F.4 — Ischémie myocardique (terme générique)",
        points_cles=[
            "Sous-décalage ST ou inversion des ondes T dans un territoire coronaire.",
            "À distinguer de la lésion (sus-décalage ST) et de la nécrose (onde Q).",
        ],
        pieges_classiques=[
            "Ischémie, lésion et nécrose sont 3 stades distincts à ne pas confondre.",
        ],
        extrait_cours=(
            "L'ischémie myocardique se traduit par un sous-décalage ST ou une inversion des ondes T "
            "systématisés à un territoire coronaire, à distinguer de la lésion (sus-décalage ST) et "
            "de la nécrose (onde Q de nécrose)."
        ),
    ),
]


# ──────────────────────────────────────────────────────────────────────────────
# INDEX inversé : ontology_id → EDNEntry
# ──────────────────────────────────────────────────────────────────────────────

import unicodedata


def _normalize_id(ontology_id: str) -> str:
    """Normalise un ontology_id pour l'indexation/la recherche : supprime les
    accents et met en majuscules. Les `golden_id` de `cases_golden.json` sont
    systématiquement sans accent (ex. `PERICARDITE`), alors que certains
    `ontology_ids` d'`EDNEntry` ci-dessus sont accentués (ex. `PÉRICARDITE`) —
    sans cette normalisation, `get_edn_entry()` ne les retrouvait jamais bien
    que l'entrée existe (cf. docs/BUG_cas15_commentaire_incoherent.md)."""
    s = unicodedata.normalize("NFD", ontology_id.strip().upper())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


_INDEX: Dict[str, EDNEntry] = {}

def _build_index():
    global _INDEX
    if _INDEX:
        return
    for entry in EDN_ENTRIES:
        for oid in entry.ontology_ids:
            _INDEX[_normalize_id(oid)] = entry

_build_index()


def get_edn_entry(ontology_id: str) -> Optional[EDNEntry]:
    """Récupère l'entrée EDN pour un concept donné (insensible aux accents)."""
    return _INDEX.get(_normalize_id(ontology_id))


def get_edn_entries_for_ids(ontology_ids: List[str]) -> Dict[str, EDNEntry]:
    """Récupère les entrées EDN pour une liste d'IDs. Retourne un dict id → entry."""
    result = {}
    for oid in ontology_ids:
        entry = get_edn_entry(oid)
        if entry:
            result[oid] = entry
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Points-clés généraux (algorithmes décisionnels)
# ──────────────────────────────────────────────────────────────────────────────

POINTS_CLES_GENERAUX = [
    "On regarde en premier la fréquence cardiaque (normale, bradycardie < 60, tachycardie > 100), on détermine si le rythme est sinusal ou non.",
    "On détermine les temps de conduction (PR, QRS, QT), l'axe électrique des QRS et on analyse la repolarisation.",
    "En cas de bradycardie, on recherche une dysfonction sinusale et/ou un BAV.",
    "Le diagnostic de bloc de branche se fait sur la durée du QRS (positif V1 = droit, négatif V1 = gauche). Les blocs de branche ne donnent pas de bradycardie.",
    "Devant un QRS large, ne pas confondre bloc de branche (sans conséquence immédiate) et TV (mortelle si non prise en charge).",
    "En cas de tachycardie, on examine la largeur des QRS et la régularité, puis on utilise les manœuvres vagales ou l'adénosine.",
    "La fibrillation atriale est le seul diagnostic en cas de tachycardie complètement irrégulière à QRS fins.",
    "Toute tachycardie régulière à QRS larges est une TV jusqu'à preuve du contraire.",
    "L'indice de Sokolow est un bon marqueur d'HVG.",
    "Au cours des SCA avec ST, ne pas confondre la lésion et son miroir.",
]


# ──────────────────────────────────────────────────────────────────────────────
# Statistiques
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"📚 EDN Knowledge Base : {len(EDN_ENTRIES)} entrées")
    print(f"   Rang A : {sum(1 for e in EDN_ENTRIES if e.rang_edn == 'A')}")
    print(f"   Rang B : {sum(1 for e in EDN_ENTRIES if e.rang_edn == 'B')}")
    print(f"   Rang C : {sum(1 for e in EDN_ENTRIES if e.rang_edn == 'C')}")
    print(f"   Index inversé : {len(_INDEX)} ontology_ids couverts")
