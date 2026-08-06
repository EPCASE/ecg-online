"""
🎓 Feedback Pédagogique — Commentaire personnalisé basé sur le cours SFC
==========================================================================
Génère un feedback pédagogique pour un candidat après évaluation ECG,
en s'appuyant sur les extraits du cours SFC (Item 231 EDN).

Le feedback est :
  - Personnalisé selon les erreurs/réussites du candidat
  - Ancré dans le cours officiel (citations SFC)
  - Structuré : félicitations → erreurs avec rappels de cours → pièges → conseils

Utilisation :
    from pedagogical_feedback import generate_pedagogical_feedback
    from candidate_report import generate_candidate_report

    report = generate_candidate_report(...)
    feedback = generate_pedagogical_feedback(report)
    print(feedback.texte)

Auteur : BMad Team
Date   : 2026-02-28
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from openai import OpenAI
from pydantic import BaseModel, Field

from edn_knowledge_base import (
    EDNEntry,
    get_edn_entry,
    get_edn_entries_for_ids,
    POINTS_CLES_GENERAUX,
)

logger = logging.getLogger(__name__)

# Type hints pour éviter les imports circulaires
# On importe CandidateReport au runtime uniquement
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from candidate_report import CandidateReport


# ──────────────────────────────────────────────────────────────────────────────
# Structures de données
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class PedagogicalFeedback:
    """Feedback pédagogique structuré pour le candidat."""
    texte: str                          # Texte complet du feedback (markdown)
    rang_edn_manques: List[str]         # Rangs EDN des concepts manqués ("A", "B")
    concepts_cours_cites: List[str]     # Noms des concepts pour lesquels le cours est cité
    has_critical_miss: bool             # True si un concept rang A a été manqué
    erreur: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Construction du contexte de cours pour le prompt
# ──────────────────────────────────────────────────────────────────────────────

def _build_course_context(report) -> str:
    """
    Construit le contexte de cours pertinent à injecter dans le prompt GPT.
    Sélectionne uniquement les entrées EDN liées aux concepts du cas.
    """
    # Collecter tous les ontology_ids pertinents pour ce cas
    relevant_ids: Set[str] = set()

    # IDs des validants (attendus)
    for vd in report.validant_details:
        relevant_ids.add(vd.golden_id)

    # IDs des descripteurs (attendus)
    for dd in report.descripteur_details:
        relevant_ids.add(dd.golden_id)

    # IDs des concepts trouvés par le candidat
    for c in report.concepts_extraits:
        if c.ontology_id != "NONE":
            relevant_ids.add(c.ontology_id)

    # IDs des découvertes
    for dec in report.decouvertes:
        relevant_ids.add(dec.ontology_id)

    # Récupérer les entrées EDN (dédupliquées par objet)
    seen_entries: Set[int] = set()
    entries: List[EDNEntry] = []

    for oid in relevant_ids:
        entry = get_edn_entry(oid)
        if entry and id(entry) not in seen_entries:
            seen_entries.add(id(entry))
            entries.append(entry)

    if not entries:
        return "Aucun extrait de cours pertinent trouvé pour ce cas."

    # Construire le texte de contexte
    parts = []
    parts.append("=== EXTRAITS DU COURS SFC — Item 231 (EDN) ===\n")

    for entry in entries:
        rang_label = {"A": "RANG A (indispensable)", "B": "RANG B (important)", "C": "RANG C (complémentaire)"}
        parts.append(f"--- {entry.titre_cours} [{rang_label.get(entry.rang_edn, entry.rang_edn)}] ---")
        parts.append(f"Extrait : {entry.extrait_cours}")
        if entry.points_cles:
            parts.append("Points clés :")
            for pc in entry.points_cles:
                parts.append(f"  • {pc}")
        if entry.pieges_classiques:
            parts.append("Pièges classiques :")
            for piege in entry.pieges_classiques:
                parts.append(f"  ⚠️ {piege}")
        parts.append("")

    return "\n".join(parts)


def _build_student_summary(report) -> str:
    """Construit un résumé structuré de la performance du candidat."""
    parts = []

    parts.append(f"DIAGNOSTIC PRINCIPAL DU CAS : {report.diagnostic_principal}")
    parts.append(f"TEXTE DU CANDIDAT : « {report.texte_etudiant} »")
    parts.append(f"SCORE FINAL : {report.score_final_pct:.1f}%")
    parts.append("")

    # Validants
    parts.append("DIAGNOSTICS VALIDANTS (notés) :")
    for vd in report.validant_details:
        status = "TROUVÉ" if vd.found else "MANQUÉ"
        entry = get_edn_entry(vd.golden_id)
        rang = f" [Rang EDN : {entry.rang_edn}]" if entry else ""
        if vd.match_type == "exact":
            parts.append(f"  ✅ {vd.golden_name} — {status} (exact, 100%){rang}")
        elif vd.match_type == "requires":
            sat = ", ".join(vd.requires_satisfied) if hasattr(vd, 'requires_satisfied') and vd.requires_satisfied else "?"
            parts.append(f"  � {vd.golden_name} — {status} (requires, {vd.score_pct:.0f}% — trouvés: {sat}){rang}")
        elif vd.match_type == "qualifier":
            quals = ", ".join(vd.qualifiers_found) if hasattr(vd, 'qualifiers_found') and vd.qualifiers_found else "?"
            parts.append(f"  🔶 {vd.golden_name} — {status} (qualifier, {vd.score_pct:.0f}% — via: {quals}){rang}")
        elif vd.match_type == "support":
            sups = ", ".join(vd.supports_found) if hasattr(vd, 'supports_found') and vd.supports_found else "?"
            parts.append(f"  🔹 {vd.golden_name} — {status} (support, {vd.score_pct:.0f}% — via: {sups}){rang}")
        elif vd.match_type == "excluded":
            excl = vd.excluded_by if hasattr(vd, 'excluded_by') and vd.excluded_by else "?"
            parts.append(f"  🚫 {vd.golden_name} — EXCLU (contredit par: {excl}){rang}")
        else:
            parts.append(f"  ❌ {vd.golden_name} — {status}{rang}")

    # Descripteurs
    if report.descripteur_details:
        parts.append("\nDESCRIPTEURS (non notés) :")
        for dd in report.descripteur_details:
            status = "identifié" if dd.found else "non mentionné"
            parts.append(f"  {'✅' if dd.found else '⬜'} {dd.golden_name} — {status}")

    # Découvertes
    if report.decouvertes:
        parts.append(f"\nDÉCOUVERTES ADDITIONNELLES — {len(report.decouvertes)} concept(s) EXPLICITEMENT ET CORRECTEMENT mentionné(s) par l'étudiant dans son texte, mais hors barème noté (ce ne sont PAS des matches indirects/qualifier — l'étudiant les a bien écrits) :")
        for dec in report.decouvertes:
            parts.append(f"  🟢 {dec.concept_name} ({dec.categorie}) — l'étudiant a mentionné ce concept explicitement")

    return "\n".join(parts)


# ──────────────────────────────────────────────────────────────────────────────
# Prompt système pour le feedback pédagogique
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Tu es un professeur de cardiologie bienveillant et pédagogue qui corrige l'interprétation ECG d'un étudiant en médecine préparant les EDN.

Tu disposes :
1. Du résultat de l'évaluation automatique (concepts trouvés/manqués, score V3 ontologique)
2. D'extraits du cours SFC officiel (Item 231 — Chapitre 15) pertinents pour ce cas
3. D'un éventuel commentaire du correcteur humain (expert) sur ce cas

Le scoring V3 utilise des relations ontologiques pour évaluer la réponse. Le
TYPE DE MATCH (fourni dans le contexte ci-dessous : exact / requires /
qualifier / support / excluded / missed) indique COMMENT le concept a été
crédité — tu dois IMPÉRATIVEMENT adapter ta formulation à ce type, car c'est
la source n°1 d'incompréhension signalée par les étudiants (ne JAMAIS
présenter un match indirect comme une identification explicite et
consciente) :
- **exact** (100%) : le concept attendu est écrit noir sur blanc par l'étudiant
  → tu peux dire « vous avez identifié / mentionné X ».
- **requires** (proportionnel) : seulement CERTAINS critères constitutifs du
  concept ont été trouvés dans le texte, pas le concept lui-même nommé
  → dis « votre réponse contient [tel(s) critère(s)], ce qui va dans le sens
  de X, mais vous ne l'avez pas nommé explicitement ». NE DIS JAMAIS
  « vous avez identifié X ».
- **qualifier** / **support** : un élément PROCHE ou INDIRECT a été trouvé
  (synonyme approximatif, signe partagé avec un autre diagnostic, concept
  voisin) — PAS le concept exact
  → dis « votre réponse évoque un élément proche de X, mais ce n'est pas tout
  à fait X » ou « [élément trouvé] peut orienter vers X sans le confirmer
  formellement ». NE DIS JAMAIS que l'étudiant a « identifié » ou « trouvé »
  le concept lui-même.
- **excluded** (0%) : un concept contradictoire a été identifié, invalidant
  la réponse → explique le conflit clairement.
- **missed** (0%) : rien de pertinent n'a été trouvé → dis simplement que le
  concept n'a pas été mentionné, sans inventer ce que l'étudiant aurait
  « presque » dit s'il n'y a aucune trace dans son texte.

RÈGLE ABSOLUE — NE PAS CONFONDRE match_type ET DÉCOUVERTES : la règle
match_type ci-dessus s'applique UNIQUEMENT aux concepts validants notés
(section « DIAGNOSTICS VALIDANTS » du contexte). Les concepts listés dans
la section « DÉCOUVERTES ADDITIONNELLES » sont d'une nature complètement
différente : ce sont des concepts que l'étudiant a EXPLICITEMENT et
CORRECTEMENT écrits dans son texte (extraction directe, pas de matching
indirect), simplement en dehors du barème noté pour ce cas. Pour CES
concepts-là, tu DOIS dire que l'étudiant les a « mentionnés » / « identifiés »
/ « notés » explicitement — ne dis JAMAIS qu'un concept listé en découverte
« n'est pas nommé explicitement » ou « n'est qu'évoqué » : ce serait FAUX et
c'est l'erreur la plus fréquente et la plus dommageable relevée par les
étudiants. Exemple : si « bradycardie » apparaît en découverte, l'étudiant a
littéralement écrit ce mot — dis « vous avez également noté la bradycardie »,
jamais « votre réponse évoque la bradycardie sans la nommer ».

RÈGLE ABSOLUE — INTERDICTION DE JARGON TECHNIQUE : les mots suivants sont des
LABELS INTERNES à l'algorithme, réservés à TON raisonnement. Ils ne doivent
JAMAIS apparaître littéralement dans le texte que tu écris pour l'étudiant :
"match", "match de type", "exact", "requires", "qualifier", "support",
"excluded", "missed", "rang A"/"rang B"/"rang C" en tant que tels (dis plutôt
« un point indispensable », « un point important », « un point complémentaire »
ou utilise le terme du concept directement), et aucun pourcentage brut
(33%, 67%, 100%...). Reformule TOUJOURS en langage médical/pédagogique
naturel destiné à un étudiant, jamais en vocabulaire de pipeline technique.
Exemple INTERDIT : « ces éléments ont été identifiés par un match de type
qualifier ». Exemple CORRECT : « votre réponse évoque des éléments qui vont
dans le sens de ce diagnostic (bradycardie, déviation axiale), sans que vous
ne l'ayez nommé explicitement ».

RÈGLE ABSOLUE sur les rangs EDN : le rang (A/B/C) de chaque concept t'est
donné EXPLICITEMENT dans le contexte ci-dessous. Utilise TOUJOURS exactement
ce rang fourni — ne le déduis JAMAIS, ne l'invente JAMAIS, ne le change
JAMAIS d'une phrase à l'autre pour un même concept.

RÈGLE ABSOLUE sur le ton vs le score : le ton général doit être cohérent avec
le score final indiqué.
- Score < 40% : PAS de formulation de type « félicitations », « excellent
  travail » — reste factuel et constructif, sans dramatiser.
- Score ≥ 80% : ton positif et valorisant assumé.
- Entre les deux : ton neutre-encourageant, sans excès dans un sens ou l'autre.

RÈGLE ABSOLUE — NE JAMAIS INVENTER DE NUANCE CLINIQUE NON DEMANDÉE : tu ne dois
JAMAIS introduire de distinction, de règle diagnostique, de mécanisme
physiopathologique ou de terminologie qui ne provient PAS directement du
contexte fourni (score, concepts, extraits de cours). En particulier :
- Ne présente JAMAIS deux formulations synonymes de la réponse de l'étudiant
  comme des concepts différents (ex: si l'étudiant écrit un terme usuel qui
  correspond exactement au concept validant attendu, ne dis pas qu'il ne l'a
  "pas nommé explicitement" ou qu'il existe une "distinction" à faire — fais
  confiance à l'information "trouvé"/"non trouvé" et au type de match fournis,
  ne les remets jamais en question par une nuance clinique de ton cru).
- N'ajoute pas de règles diagnostiques générales, de risques, de mécanismes
  physiopathologiques ou de rappels non directement liés aux extraits de
  cours fournis (pas de rappel inventé sur la torsade de pointes, le
  bigéminisme, etc. si ce n'est pas dans les extraits fournis).
- Si un score est de 100%, ne cherche PAS à trouver un défaut ou une nuance à
  ajouter à tout prix — un score parfait mérite un feedback court et
  simplement valorisant, sans conseil de révision artificiel.

Si tu as un doute sur une nuance clinique, ABSTIENS-toi de la mentionner
plutôt que de risquer une approximation ou une contradiction avec la réponse
réelle de l'étudiant : la fiabilité prime toujours sur l'exhaustivité.

Ta mission est de rédiger un COMMENTAIRE PÉDAGOGIQUE personnalisé en français,
en UNE SEULE section continue (pas de titres de sous-parties, pas de
séparation artificielle en 2 blocs qui répéteraient la même information sous
deux formes différentes). Le commentaire doit, dans un flux naturel :

1. Traiter les concepts clés de ce cas (validants d'abord, puis descripteurs
   manqués les plus importants, puis erreurs/exclusions le cas échéant) :
   pour chacun, indique le statut (trouvé exact / partiellement évoqué /
   manqué / erroné) EN RESPECTANT le type de match (cf. règle ci-dessus, SANS
   jamais nommer le type de match littéralement) et le rang EDN fourni (SANS
   jamais écrire "rang A/B/C" littéralement, cf. règle ci-dessus). Quand tu
   cites le cours, recopie MOT POUR MOT un passage réellement présent dans
   la section "EXTRAITS DU COURS SFC" fournie plus bas dans le contexte
   utilisateur (jamais une paraphrase, jamais un texte inventé). N'écris
   JAMAIS de texte de substitution générique du type "extrait du cours" ou
   toute formule décrivant l'action de citer plutôt que de citer réellement.
   Le format attendu est : 📖 « [ici le texte du cours copié tel quel] » —
   (Item 231, SFC), où [ici le texte du cours copié tel quel] est remplacé
   par le contenu réel — jamais laissé sous cette forme littérale entre
   crochets. Si aucun extrait pertinent n'est disponible pour un concept
   donné, ne fais simplement PAS de citation pour ce concept (pas de
   citation vide, pas de placeholder).
2. Ne PAS répéter un même concept une deuxième fois pour le commenter à
   nouveau sous un angle différent — chaque concept n'est mentionné QU'UNE
   SEULE FOIS dans tout le texte.
3. Terminer par UNE SEULE phrase de synthèse/conseil (pas un résumé de ce qui
   précède) — UNIQUEMENT si un point manque réellement ou peut être précisé ;
   si le score est de 100% et qu'aucun manque réel n'existe, ne force PAS de
   conseil et termine simplement sur une note positive brève. Intègre le
   commentaire du correcteur humain si fourni, sans le dupliquer par une
   remarque similaire de ton cru.

## Règles générales :
- Ton bienveillant mais exigeant, comme un bon PU qui veut que ses étudiants réussissent.
- Cite le cours SFC UNIQUEMENT si tu recopies un extrait réel présent dans le
  contexte fourni (jamais de citation inventée ou vide) — entre guillemets avec source.
- Ne cite QUE les concepts les plus importants (max 2-3 rappels de cours au total,
  jamais plus — préfère la concision à l'exhaustivité).
- Ne PAS répéter le score numérique (il est déjà affiché ailleurs).
- Ne PAS utiliser de titres markdown (## ...) — un texte continu, éventuellement avec des sauts de paragraphe.
- Rester CONCIS : 80-160 mots au total pour un score ≥ 80% (feedback court et
  valorisant), jusqu'à 220 mots maximum pour un score plus faible nécessitant
  plus de rappels — ne jamais dépasser ces bornes.
- Format texte simple (pas de HTML), avec des emojis si pertinent, sans excès.
- Vérifie-toi avant de conclure : aucun des mots interdits de la RÈGLE ABSOLUE
  sur le jargon technique ne doit apparaître dans ta réponse finale, et aucune
  nuance clinique non fournie dans le contexte n'a été ajoutée.
"""


# ──────────────────────────────────────────────────────────────────────────────
# Garde-fou déterministe : cohérence du ton avec le score (P5, belt-and-suspenders)
# ──────────────────────────────────────────────────────────────────────────────

_CONGRATULATORY_PATTERNS = [
    "félicitations", "excellent travail", "excellente interprétation",
    "superbe travail", "bravo", "parfait !", "magnifique",
]


def _enforce_tone_guardrail(texte: str, score_pct: float) -> str:
    """
    Filet de sécurité déterministe (non-LLM) : si le score est < 40%, on
    retire toute formulation congratulatoire que le LLM aurait pu laisser
    passer malgré l'instruction dans le prompt (P5). Ne modifie pas le texte
    si le score est >= 40%.
    """
    if score_pct >= 40:
        return texte

    import re as _re
    cleaned = texte
    for pattern in _CONGRATULATORY_PATTERNS:
        cleaned = _re.sub(pattern, "", cleaned, flags=_re.IGNORECASE)
    # Nettoyer une ponctuation orpheline éventuelle laissée par la suppression
    cleaned = _re.sub(r"\s{2,}", " ", cleaned)
    cleaned = _re.sub(r"\s+([.,!?])", r"\1", cleaned)
    return cleaned.strip()


# Termes de jargon interne qui ne doivent jamais apparaître dans le texte
# destiné à l'étudiant (P2 belt-and-suspenders). Détection simple par
# expressions régulières, insensible à la casse.
_JARGON_PATTERNS = [
    r"\bmatch(?:e|é)?\s+(?:de\s+type\s+)?(?:exact|requires?|qualifier|support|excluded|missed)\b",
    r"\btype\s+de\s+match\b",
    r"\brang\s+[ABC]\b",
    r"\b\d{1,3}\s?%\b",
    r"«\s*extrait du cours\s*»",
    r"«\s*texte\s+(?:réellement\s+)?recopié",
    r"\[ici le texte",
    r"\btexte de substitution\b",
    r"«\s*\[.*?\]\s*»",  # citation encore sous forme de placeholder entre crochets
]


def _detect_jargon_leak(texte: str) -> List[str]:
    """
    Détecte (sans corriger automatiquement, car une correction naïve
    dégraderait la lisibilité) toute fuite de jargon technique interne dans
    le texte pédagogique final. Retourne la liste des motifs trouvés, pour
    logging/monitoring — permet de mesurer la fréquence du problème sans
    bloquer la génération.
    """
    import re as _re
    found = []
    for pattern in _JARGON_PATTERNS:
        if _re.search(pattern, texte, flags=_re.IGNORECASE):
            found.append(pattern)
    return found


# ──────────────────────────────────────────────────────────────────────────────
# Validation post-hoc des affirmations cliniques (piste "problèmes résiduels"
# de l'audit 2026-08-06) : un second appel LLM, dédié et à température nulle,
# relit le texte généré à la lumière STRICTE du contexte fourni (concepts +
# extraits de cours réels) et signale toute affirmation clinique qui n'y est
# PAS ancrée (règle diagnostique inventée, distinction terminologique non
# fournie, mécanisme physiopathologique non cité). Contrairement au garde-fou
# jargon (regex), ceci nécessite un jugement sémantique — d'où un LLM juge
# dédié, séparé du rédacteur, avec une consigne volontairement stricte et un
# rôle borné (verdict + citation du passage fautif, pas de réécriture libre).
# ──────────────────────────────────────────────────────────────────────────────

class ClinicalClaimValidation(BaseModel):
    """Verdict structuré du juge de validation clinique post-hoc."""
    contient_affirmation_non_fondee: bool = Field(
        description="True si le texte contient au moins une affirmation clinique "
                    "(règle diagnostique, distinction terminologique, mécanisme "
                    "physiopathologique) qui n'est PAS directement soutenue par le "
                    "contexte fourni (concepts trouvés/manqués, extraits de cours)."
    )
    passages_problematiques: List[str] = Field(
        default_factory=list,
        description="Citation exacte (courte, 5-20 mots) du/des passage(s) du texte "
                    "contenant une affirmation clinique non fondée par le contexte. "
                    "Liste vide si contient_affirmation_non_fondee est False."
    )
    justification: str = Field(
        default="",
        description="Brève explication (1 phrase) de pourquoi chaque passage cité "
                    "est considéré comme non fondé par le contexte."
    )


_CLINICAL_VALIDATOR_SYSTEM_PROMPT = """Tu es un relecteur cardiologue extrêmement
rigoureux. Ta SEULE tâche est de vérifier qu'un texte de feedback pédagogique
destiné à un étudiant ne contient AUCUNE affirmation clinique qui ne soit pas
directement soutenue par le contexte fourni (liste des concepts trouvés/
manqués, extraits du cours SFC).

Une affirmation clinique est "non fondée" si elle relève de l'un de ces cas :
- Une règle diagnostique générale (ex: "les QRS fins signent toujours une
  origine nodale") qui n'apparaît PAS mot pour mot ou en substance dans les
  extraits de cours fournis.
- Une distinction terminologique entre deux formulations qui, dans le
  contexte fourni, désignent en réalité le MÊME concept validant (trouvé/
  manqué) — le texte ne doit jamais remettre en question le statut
  trouvé/manqué donné dans le contexte.
- Un mécanisme physiopathologique, un risque, ou un rappel médical qui
  n'est PAS présent dans les extraits de cours fournis.

Ce n'est PAS une affirmation non fondée :
- Le simple fait de nommer un concept et son statut (trouvé/manqué/rang EDN)
  tel que donné dans le contexte.
- Une reformulation fidèle d'un extrait de cours fourni.
- Une phrase d'encouragement ou de synthèse générique sans contenu clinique
  nouveau.

Analyse le texte ci-dessous STRICTEMENT à la lumière du contexte fourni.
Ne sois PAS complaisant : si un doute raisonnable existe sur le fondement
d'une affirmation, considère-la comme non fondée."""


def _validate_clinical_claims(
    feedback_text: str,
    course_context: str,
    student_summary: str,
    model: str = "gpt-4o",
) -> ClinicalClaimValidation:
    """
    Appelle un juge LLM dédié (Structured Outputs) pour détecter toute
    affirmation clinique du texte de feedback non fondée par le contexte
    réellement fourni (concepts + extraits de cours). Utilisé en filet de
    sécurité post-génération : en cas de détection, une reformulation
    corrective ciblée est demandée au rédacteur (cf. appelant).
    """
    client = OpenAI()
    user_message = f"""CONTEXTE FOURNI AU RÉDACTEUR (concepts + cours) :

{student_summary}

{course_context}

TEXTE DE FEEDBACK À VÉRIFIER :

{feedback_text}"""
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": _CLINICAL_VALIDATOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0,
        response_format=ClinicalClaimValidation,
    )
    parsed = response.choices[0].message.parsed
    if parsed is None:
        return ClinicalClaimValidation(contient_affirmation_non_fondee=False)
    return parsed


def _correct_unfounded_claims(
    feedback_text: str,
    validation: ClinicalClaimValidation,
    model: str = "gpt-4o",
) -> str:
    """
    Demande une réécriture ciblée du texte de feedback pour retirer/adoucir
    les passages signalés comme non fondés par le juge de validation
    clinique, sans changer le reste du texte ni le ton général.
    """
    client = OpenAI()
    passages = "\n".join(f"- « {p} »" for p in validation.passages_problematiques)
    retry_message = f"""Le texte de feedback pédagogique suivant contient des
affirmations cliniques jugées NON FONDÉES par le contexte réellement fourni
(règle diagnostique, distinction terminologique ou mécanisme physiopatho-
logique inventé, absent du contexte) :

{passages}

Raison : {validation.justification}

Réécris le texte en SUPPRIMANT ou en NEUTRALISANT uniquement ces passages
(remplace-les par une formulation neutre qui reste dans les limites du
contexte fourni, ou supprime-les si aucune reformulation fondée n'est
possible), SANS modifier le reste du texte ni son ton général, et en
respectant STRICTEMENT toutes les règles système (jargon interdit, rangs
EDN, ton vs score, citations réelles uniquement) :

{feedback_text}"""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": retry_message},
        ],
        temperature=0.3,
        max_tokens=800,
    )
    return (response.choices[0].message.content or "").strip()


# ──────────────────────────────────────────────────────────────────────────────
# Fonction principale
# ──────────────────────────────────────────────────────────────────────────────

def generate_pedagogical_feedback(
    report,
    model: str = "gpt-4o",
    temperature: float = 0.7,
    commentaire_correcteur: str = "",
) -> PedagogicalFeedback:
    """
    Génère un feedback pédagogique basé sur le cours SFC pour un CandidateReport.

    Args:
        report:      CandidateReport (résultat de generate_candidate_report)
        model:       Modèle OpenAI à utiliser (default: gpt-4o — la précision clinique
                     et le respect strict des consignes de formulation priment sur le
                     coût ; gpt-4o-mini a montré trop d'approximations cliniques et de
                     confusions terminologiques lors des audits qualité)
        temperature: Créativité du feedback (0.7 = naturel mais pas trop créatif)
        commentaire_correcteur: Commentaire libre du correcteur humain pour ce cas

    Returns:
        PedagogicalFeedback avec texte du commentaire et métadonnées.
    """
    # Vérifier qu'il y a un rapport exploitable
    if report.erreur:
        return PedagogicalFeedback(
            texte=f"Impossible de générer un commentaire pédagogique : {report.erreur}",
            rang_edn_manques=[],
            concepts_cours_cites=[],
            has_critical_miss=False,
            erreur=report.erreur,
        )

    # Construire le contexte
    course_context = _build_course_context(report)
    student_summary = _build_student_summary(report)

    # Identifier les concepts manqués et leurs rangs
    rang_manques = []
    concepts_cites = []
    for vd in report.validant_details:
        entry = get_edn_entry(vd.golden_id)
        if entry:
            concepts_cites.append(vd.golden_name)
            if not vd.found:
                rang_manques.append(entry.rang_edn)

    has_critical = "A" in rang_manques

    # Appel GPT
    correcteur_section = ""
    if commentaire_correcteur and commentaire_correcteur.strip():
        correcteur_section = f"\n\nCOMMENTAIRE DU CORRECTEUR HUMAIN (expert) :\n« {commentaire_correcteur.strip()} »\n(Intègre ce commentaire naturellement dans le texte, comme un conseil d'expert.)"

    user_message = f"""Voici l'évaluation d'un étudiant sur un cas ECG.

{student_summary}

{course_context}{correcteur_section}

Rédige le commentaire pédagogique en un seul texte continu (pas de titres, pas de sections numérotées), en respectant strictement les règles de ton, de rang EDN et de formulation par match_type données dans les instructions système."""

    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=800,
        )
        feedback_text = (response.choices[0].message.content or "").strip()

        # Garde-fou P2 (belt-and-suspenders) : si du jargon technique interne
        # a fui dans le texte malgré l'instruction système, on redemande UNE
        # fois une reformulation strictement corrective avant d'abandonner.
        jargon_found = _detect_jargon_leak(feedback_text)
        if jargon_found:
            logger.warning(f"Fuite de jargon détectée dans le feedback ({jargon_found}) — nouvelle tentative de reformulation.")
            retry_message = f"""Le texte suivant contient du jargon technique interdit
(termes de pipeline comme "match", "type de match", "qualifier", "support",
"rang A/B/C", des pourcentages bruts, ou une citation placeholder non réelle
« extrait du cours »). Réécris-le en langage naturel destiné à un étudiant,
en respectant STRICTEMENT les mêmes règles système (aucun de ces termes ne
doit apparaître), sans changer le fond clinique du message :

{feedback_text}"""
            retry_response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": retry_message},
                ],
                temperature=0.3,
                max_tokens=800,
            )
            retried_text = (retry_response.choices[0].message.content or "").strip()
            if retried_text and not _detect_jargon_leak(retried_text):
                feedback_text = retried_text
            else:
                logger.warning("La reformulation n'a pas éliminé le jargon détecté — texte conservé tel quel.")

        # Validation post-hoc des affirmations cliniques : un juge LLM dédié
        # relit le texte à la lumière STRICTE du contexte fourni, et signale
        # toute affirmation clinique non fondée (règle inventée, distinction
        # terminologique non fournie, mécanisme physiopathologique absent du
        # cours). En cas de détection, une reformulation ciblée est demandée
        # (retire/neutralise uniquement les passages fautifs, sans réécrire
        # tout le texte).
        try:
            validation = _validate_clinical_claims(feedback_text, course_context, student_summary, model=model)
            if validation.contient_affirmation_non_fondee and validation.passages_problematiques:
                logger.warning(
                    f"Affirmation(s) clinique(s) non fondée(s) détectée(s) : "
                    f"{validation.passages_problematiques} — {validation.justification}"
                )
                corrected_text = _correct_unfounded_claims(feedback_text, validation, model=model)
                if corrected_text:
                    # Re-vérifier que la correction n'a pas réintroduit du jargon
                    if not _detect_jargon_leak(corrected_text):
                        feedback_text = corrected_text
                    else:
                        logger.warning("La correction clinique a réintroduit du jargon — texte conservé tel quel.")
        except Exception as e_validate:
            # La validation post-hoc est un filet de sécurité best-effort :
            # une erreur ici ne doit jamais faire échouer la génération.
            logger.warning(f"Validation post-hoc des affirmations cliniques ignorée (erreur : {e_validate})")

        feedback_text = _enforce_tone_guardrail(feedback_text, report.score_final_pct)

    except Exception as e:
        logger.error(f"Erreur GPT pour feedback pédagogique : {e}")
        return PedagogicalFeedback(
            texte=_generate_fallback_feedback(report),
            rang_edn_manques=rang_manques,
            concepts_cours_cites=concepts_cites,
            has_critical_miss=has_critical,
            erreur=str(e)[:200],
        )

    return PedagogicalFeedback(
        texte=feedback_text,
        rang_edn_manques=rang_manques,
        concepts_cours_cites=concepts_cites,
        has_critical_miss=has_critical,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Feedback de secours (sans GPT)
# ──────────────────────────────────────────────────────────────────────────────

def _generate_fallback_feedback(report) -> str:
    """
    Génère un feedback minimal basé uniquement sur la knowledge base,
    sans appel LLM. Utilisé en cas d'erreur GPT.
    """
    parts = []

    # Appréciation
    if report.score_final_pct >= 90:
        parts.append("🎉 Excellente interprétation !")
    elif report.score_final_pct >= 70:
        parts.append("👍 Bonne interprétation, quelques points à préciser.")
    elif report.score_final_pct >= 50:
        parts.append("📚 Interprétation partielle — des éléments importants manquent.")
    else:
        parts.append("💪 Cette interprétation nécessite une révision approfondie.")

    # Rappels de cours pour les validants manqués
    for vd in report.validant_details:
        if not vd.found:
            entry = get_edn_entry(vd.golden_id)
            if entry:
                rang_label = {"A": "indispensable", "B": "important", "C": "complémentaire"}
                parts.append(
                    f"\n❌ {vd.golden_name} (Rang EDN : {entry.rang_edn} — {rang_label.get(entry.rang_edn, '')}) :"
                )
                parts.append(f'📖 « {entry.extrait_cours} » — (Item 231, SFC)')
                if entry.pieges_classiques:
                    for piege in entry.pieges_classiques[:1]:
                        parts.append(f"⚠️ Piège : {piege}")

    # Découvertes
    if report.decouvertes:
        parts.append(f"\n🟢 Vous avez identifié {len(report.decouvertes)} élément(s) pertinent(s) au-delà du barème — c'est un bon signe !")

    return "\n".join(parts)


# ──────────────────────────────────────────────────────────────────────────────
# Formatage HTML du feedback
# ──────────────────────────────────────────────────────────────────────────────

def format_feedback_html(feedback: PedagogicalFeedback) -> str:
    """Formate le feedback pédagogique en HTML (dark theme), structuré en 3 sections."""
    import re

    # Badge de criticité
    if feedback.has_critical_miss:
        badge = '<span style="background:#F44336; color:white; padding:2px 8px; border-radius:4px; font-size:12px;">⚠️ Concept rang A manqué</span>'
    elif feedback.rang_edn_manques:
        badge = '<span style="background:#FF9800; color:white; padding:2px 8px; border-radius:4px; font-size:12px;">📝 Points à revoir</span>'
    else:
        badge = '<span style="background:#4CAF50; color:white; padding:2px 8px; border-radius:4px; font-size:12px;">✅ Maîtrise confirmée</span>'

    # Extraire les 3 sections
    sections = re.split(r'##\s*\d+\.\s*', feedback.texte)
    section_titles = re.findall(r'##\s*\d+\.\s*(.+)', feedback.texte)

    section_icons = ["📖", "🔍"]
    section_colors = ["#5C6BC0", "#FF9800"]

    sections_html = ""
    if len(section_titles) >= 2 and len(sections) >= 3:
        for idx in range(2):
            title = section_titles[idx].strip()
            content = sections[idx + 1].strip()
            content_html = content.replace("\n\n", "</p><p>").replace("\n", "<br>")
            content_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content_html)
            content_html = re.sub(r'📖\s*«\s*(.+?)\s*»', r'📖 <em style="color:#90CAF9;">«\1»</em>', content_html)
            icon = section_icons[idx]
            color = section_colors[idx]
            sections_html += f"""
        <div style="border-left:4px solid {color}; padding:12px 16px; margin-bottom:12px; background:#1e2d3d; border-radius:4px;">
            <h4 style="color:{color}; margin:0 0 8px 0; font-size:14px;">{icon} {title}</h4>
            <div style="color:#e0e0e0; font-size:13px; line-height:1.6;">
                <p>{content_html}</p>
            </div>
        </div>"""
    else:
        # Fallback
        text_html = feedback.texte.replace("\n\n", "</p><p>").replace("\n", "<br>")
        text_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text_html)
        text_html = re.sub(r'📖\s*«\s*(.+?)\s*»', r'📖 <em style="color:#90CAF9;">«\1»</em>', text_html)
        sections_html = f'<div style="color:#e0e0e0; font-size:14px; line-height:1.7;"><p>{text_html}</p></div>'

    return f"""
    <div style="background:#1a2332; border-radius:8px; padding:16px; margin-top:16px;
                border-left:4px solid #5C6BC0;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <h3 style="color:#7986CB; margin:0; font-size:16px;">
                🎓 Commentaire pédagogique — Cours SFC, Item 231
            </h3>
            {badge}
        </div>
        {sections_html}
        <div style="color:#666; font-size:11px; margin-top:12px; border-top:1px solid #333; padding-top:8px;">
            Source : Chapitre 15 — Item 231, Société Française de Cardiologie (SFC), Référentiel CNEC 2e édition
        </div>
    </div>
    """


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Ce module nécessite un CandidateReport pour fonctionner.")
    print("Utilisez le notebook candidate_report_demo.ipynb pour tester.")
