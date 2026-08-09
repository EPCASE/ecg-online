"""
gpt_annotator.py — Second annotateur automatique (GPT-5.6), indépendant du pipeline.
=====================================================================================
Cf. GOLDEN_EXTRACTION.md §5bis pour la justification méthodologique.

⚠️ Rôle STRICTEMENT limité à proposer un brouillon candidat supplémentaire,
au même titre que `pipeline_extraction` : ce module ne doit JAMAIS voir la
sortie du pipeline NER de production (`ner_extractor.py`, GPT-4o) — sinon on
mesurerait la cohérenc            matches = golden_config.search_concepts(c.concept_name, limit=5)
            best = matches[0] if matches else None
            # Doublon avec un critère déjà validé : on l'écarte purement et
            # simplement, MÊME si le meilleur score de résolution est sous
            # le seuil (ex. "Bloc AV Mobitz I" ne matche le bon ID qu'à 49
            # avec un autre concept proche en tête à 55) — on regarde TOUS
            # les candidats retournés, pas seulement le premier, sinon on
            # repropose des reformulations de critères existants comme
            # s'ils étaient neufs.
            if any(m["id"] in existing_ids for m in matches):
                continuele avec lui-même, pas sa justesse clinique
(circularité). Le prompt est écrit indépendamment de `ner_extractor.SYSTEM_PROMPT`
et vise l'exhaustivité (pas de contrainte de scoring/note).

L'annotation FINALE reste 100 % humaine (`annotation_expert` /
`annotation_expert_2`, cf. `app/extraction_golden.py`) — ce module ne fait que
réduire le travail de saisie en proposant des concepts à accepter/rejeter.

Modèle configurable via ECG_ANNOTATOR_MODEL (défaut : gpt-5.6). Se dégrade
proprement (liste vide + `available()=False`) si le modèle n'existe pas
encore côté API ou si la clé est absente — n'empêche jamais l'annotation
manuelle classique.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.environ.get("ECG_ANNOTATOR_MODEL", "gpt-5.6")

_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI()  # lit OPENAI_API_KEY dans l'environnement
    return _client


def available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


# ─────────────────────────── Schéma structuré ───────────────────────────
class CandidateConcept(BaseModel):
    """Un concept ECG proposé par le second annotateur, en langage libre
    (PAS d'ID ontologique ici : la résolution ontologique se fait ensuite
    côté page d'annotation via le picker existant, `golden_config.search_concepts`)."""
    concept: str = Field(description="Nom clinique du concept, en français standard.")
    statut: str = Field(description="'present', 'absent' ou 'hypothese'.")
    justification: str = Field(
        description="Courte citation ou paraphrase du texte source justifiant ce concept.")


class CandidateExtraction(BaseModel):
    concepts: List[CandidateConcept]


# Prompt VOLONTAIREMENT différent de ner_extractor.SYSTEM_PROMPT : ici on vise
# l'EXHAUSTIVITÉ pédagogique (golden d'extraction), pas la note de l'étudiant.
# Aucune connaissance de la sortie du pipeline de production n'est injectée.
SYSTEM_PROMPT = """\
Tu es un cardiologue expert, chargé de constituer un GOLDEN D'ANNOTATION de
référence (pas une correction d'étudiant, pas une notation).

Tâche : lis le texte libre ci-dessous, rédigé par un étudiant en médecine à
propos d'un tracé ECG, et liste EXHAUSTIVEMENT tous les concepts cliniques,
rythmiques et morphologiques ECG qu'il mentionne — qu'ils soient corrects ou
non, qu'ils soient importants ou secondaires.

Règles :
1. Sois EXHAUSTIF : n'omets aucun concept ECG mentionné, même mineur
   (ex. « QRS fins », « PR normal », « axe normal »).
2. N'ajoute AUCUN concept qui n'est pas réellement mentionné ou clairement
   impliqué par le texte (pas d'invention, pas de déduction clinique
   hasardeuse au-delà de ce qui est écrit).
3. Statut :
   - "present" : le concept est affirmé comme présent.
   - "absent" : le concept est explicitement nié / écarté.
   - "hypothese" : évoqué avec doute (« pourrait être », « à confirmer »).
4. Utilise des noms cliniques STANDARD (pas d'abréviation obscure) mais reste
   fidèle au sens exact du texte (ne reformule pas au-delà du nécessaire).
5. Ne juge pas la qualité de la réponse de l'étudiant, ne donne aucune note :
   ton seul rôle est l'inventaire clinique exhaustif.

Réponds uniquement avec la liste structurée demandée.
"""


def annotate(texte_etudiant: str, model: str = DEFAULT_MODEL) -> List[dict]:
    """Renvoie une liste de concepts candidats [{concept, statut, justification}].

    Liste vide si le modèle est indisponible ou en cas d'erreur (dégradation
    propre — ne doit jamais faire planter la page d'annotation)."""
    texte_etudiant = (texte_etudiant or "").strip()
    if not texte_etudiant or not available():
        return []
    try:
        client = _get_client()
        # Note : certains modèles (ex. gpt-5.x) ne supportent que temperature=1
        # (défaut) — on ne force pas 0 comme pour le NER de prod (GPT-4o),
        # pour rester compatible avec la famille de modèles la plus récente.
        resp = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Texte de l'étudiant :\n« {texte_etudiant} »"},
            ],
            response_format=CandidateExtraction,
        )
        result = resp.choices[0].message.parsed
        if result is None:
            return []
        return [c.model_dump() for c in result.concepts]
    except Exception as ex:
        logger.warning("gpt_annotator.annotate a échoué (%s: %s) — "
                        "dégradation propre, liste vide renvoyée.",
                        type(ex).__name__, ex)
        return []


# ═══════════════════════ Contrôle qualité (relecture finale) ═══════════════════════
# Rôle DIFFÉRENT du second avis aveugle ci-dessus (`annotate`) : ici GPT-5.6 voit
# À LA FOIS le texte étudiant ET l'annotation humaine déjà finalisée, et doit
# repérer des erreurs/oublis/doutes potentiels — un vrai passage de relecture
# critique, pas une extraction indépendante. Cf. GOLDEN_EXTRACTION.md §5ter.
class ReviewFlag(BaseModel):
    concept: str = Field(description="Le concept annoté (ou manquant) concerné.")
    type_probleme: str = Field(
        description="'omission' (concept du texte non annoté), 'douteux' "
                    "(concept annoté mais absent/mal interprété dans le texte), "
                    "'statut_a_verifier' (present/absent/hypothese qui semble erroné), "
                    "ou 'ok_mais_limite' (cas limite mais probablement correct).")
    commentaire: str = Field(description="Explication concise du doute, en français.")


class ReviewResult(BaseModel):
    alertes: List[ReviewFlag]
    synthese: str = Field(description="Une phrase de synthèse sur la qualité globale de l'annotation.")


REVIEW_SYSTEM_PROMPT = """\
Tu es un cardiologue expert, relecteur qualité d'un golden d'annotation ECG
(vérité de terrain servant à mesurer un pipeline d'IA — PAS une correction
d'étudiant, pas de notation).

On te donne :
1. Le texte libre original rédigé par un étudiant.
2. L'annotation FINALE déjà réalisée par un expert humain (liste de concepts
   avec leur statut present/absent/hypothese).

IMPORTANT — les noms de concepts (concept_name) NE sont PAS du texte libre :
ce sont des libellés PRÉ-DÉFINIS, choisis dans une ONTOLOGIE fermée (liste
fixe de concepts ECG possibles). L'expert humain a dû faire correspondre le
texte de l'étudiant au concept ontologique le plus proche disponible — il ne
pouvait pas inventer un libellé plus précis même s'il le voulait. En
conséquence :
 - Un concept_name qui utilise un terme légèrement différent, plus générique,
   ou reformulé par rapport au texte source (ex. « dépolarisation » vs
   « repolarisation », « flutter atrial » vs « flutter droit typique »,
   « BAV 1 » vs « bloc AV du premier degré ») n'est PAS forcément une erreur :
   c'est probablement le concept ontologique disponible le plus proche.
   Ne signale ce genre de différence QUE si tu es sûr qu'aucun concept
   ontologique proche ne pouvait raisonnablement correspondre (mauvaise
   correspondance sémantique claire, pas juste une variante de formulation).
 - Concentre-toi surtout sur les VRAIES omissions (concept mentionné dans le
   texte et absent de toute forme dans l'annotation) et les VRAIS désaccords
   de statut (present/absent/hypothese qui contredit le texte).

Ta tâche : relire les deux et repérer les points DOUTEUX ou potentiellement
ERRONÉS dans l'annotation humaine, à savoir :
 - Un concept clairement présent dans le texte mais ABSENT de l'annotation,
   y compris sous une forme reformulée/ontologique (omission réelle).
 - Un concept annoté dont le statut ou le sens contredit clairement le texte
   (pas une simple variante de nommage).
 - Un statut (present/absent/hypothese) qui semble incohérent avec la
   formulation du texte.
 - Ne signale PAS de faux problèmes : si l'annotation est correcte et
   complète (même avec un nommage ontologique différent du texte source),
   renvoie une liste d'alertes VIDE. Ne cherche pas à tout prix des erreurs
   à signaler, et ne signale jamais une simple différence de formulation
   comme une erreur.

Sois concis et factuel. Cite le texte source pour justifier chaque alerte, et
précise dans `type_probleme` si le doute concerne vraiment le concept
(omission/erreur) plutôt qu'un simple nommage ontologique différent.
"""


def review_annotation(texte_etudiant: str, concepts_annotes: List[dict],
                      model: str = DEFAULT_MODEL) -> Optional[dict]:
    """Relit une annotation humaine FINALISÉE et signale erreurs/doutes potentiels.

    `concepts_annotes` : liste de dicts {concept_name, statut, ...} (le format
    stocké dans annotation_expert.concepts, cf. app/extraction_golden.py).

    Renvoie {"alertes": [...], "synthese": "..."} ou None si indisponible/erreur
    (dégradation propre)."""
    texte_etudiant = (texte_etudiant or "").strip()
    if not texte_etudiant or not available():
        return None
    concepts_txt = "\n".join(
        f"  - {c.get('concept_name', c.get('concept', '?'))} "
        f"[{c.get('statut', 'present')}]"
        for c in concepts_annotes
    ) or "  (aucun concept annoté)"
    user_content = (
        f"## Texte de l'étudiant\n« {texte_etudiant} »\n\n"
        f"## Annotation finale de l'expert humain\n{concepts_txt}\n\n"
        "Relis et signale les points douteux, s'il y en a."
    )
    try:
        client = _get_client()
        resp = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format=ReviewResult,
        )
        result = resp.choices[0].message.parsed
        if result is None:
            return None
        return result.model_dump()
    except Exception as ex:
        logger.warning("gpt_annotator.review_annotation a échoué (%s: %s) — "
                        "dégradation propre.", type(ex).__name__, ex)
        return None


# ═══════════════ Second avis IA sur le golden de scoring V2 (P1.3) ═══════════════
# Rôle DIFFÉRENT des deux précédents : ici GPT relit les CRITÈRES DE SCORING
# structurés (role/expected_status/importance/error_severity/...) qu'un
# relecteur humain unique a validés pour un cas, en s'appuyant sur le texte
# d'interprétation de référence du cas ECG (`interpretation_ref`, rédigé par
# un cardiologue). Remplace la double annotation humaine + adjudication :
# un seul expert reste responsable, l'IA ne fait que signaler des doutes.
class ScoringReviewFlag(BaseModel):
    criterion_id: Optional[str] = Field(
        default=None,
        description="L'identifiant du critère EXISTANT concerné (criterion_id), pris "
                    "EXACTEMENT dans la liste fournie. Laisser vide/null si type_probleme="
                    "'omission' (par définition, un critère omis n'existe pas encore).")
    type_probleme: str = Field(
        description="'role_a_verifier' (required/alternative/optional/exclusion qui semble "
                    "incohérent avec le texte de référence), 'importance_a_verifier', "
                    "'severite_a_verifier', 'omission' (élément du texte de référence non "
                    "couvert par aucun critère — utiliser concept_suggere/label_suggere), "
                    "ou 'ok_mais_limite' (cas limite probablement correct).")
    commentaire: str = Field(description="Explication concise du doute, en français, citant le texte de référence.")
    concept_suggere: Optional[str] = Field(
        default=None,
        description="UNIQUEMENT si type_probleme='omission' : identifiant de concept "
                    "suggéré en MAJUSCULES_SNAKE_CASE pour le nouveau critère (ex. "
                    "'ONDE_Q_NECROSE'). Null sinon.")
    label_suggere: Optional[str] = Field(
        default=None,
        description="UNIQUEMENT si type_probleme='omission' : libellé lisible suggéré pour "
                    "le nouveau critère (ex. 'Présence d'ondes Q de nécrose en antérieur'). "
                    "Null sinon.")


class ScoringReviewResult(BaseModel):
    alertes: List[ScoringReviewFlag]
    synthese: str = Field(description="Une phrase de synthèse sur la qualité globale des critères.")


SCORING_REVIEW_SYSTEM_PROMPT = """\
Tu es un cardiologue expert, relecteur qualité d'un golden de SCORING ECG
(critères structurés servant à noter automatiquement les réponses des
étudiants — PAS une correction d'étudiant).

On te donne :
1. Le texte d'interprétation de référence du cas (rédigé par un cardiologue,
   c'est la « vérité » clinique du tracé).
2. La liste des critères de scoring structurés qu'un relecteur humain a
   validés pour ce cas (chaque critère a : role [required/alternative/
   optional/exclusion], expected_status [present/absent/hypothesis_acceptable],
   importance [major/intermediate/minor], error_severity
   [none/minor/major/dangerous], etc.).

Ta tâche : relire ces critères à la lumière du texte de référence et signaler
les points DOUTEUX ou potentiellement ERRONÉS, à savoir :
 - Un `role` qui semble incohérent (ex. un élément clairement secondaire
   marqué `required`, ou un élément central marqué `optional`).
 - Une `importance`/`error_severity` qui semble disproportionnée par rapport
   à la gravité clinique réelle décrite dans le texte.
 - Une omission : un élément clinique important du texte de référence qui
   n'est couvert par AUCUN critère de la liste. Dans ce cas, laisse
   `criterion_id` vide et renseigne `concept_suggere` (MAJUSCULES_SNAKE_CASE)
   et `label_suggere` (libellé lisible) pour permettre au relecteur de créer
   le critère manquant en un clic.
 - Un `expected_status` qui contredit le texte (ex. marqué "present" alors
   que le texte l'exclut explicitement).

Ne signale PAS de faux problèmes : si les critères sont cohérents et complets,
renvoie une liste d'alertes VIDE. Sois concis, factuel, cite le texte de
référence pour justifier chaque alerte.
"""


def review_scoring_criteria(interpretation_ref: str, criteria: List[dict],
                            model: str = DEFAULT_MODEL) -> Optional[dict]:
    """Second avis GPT sur des critères de scoring_v2 déjà validés par un
    relecteur humain unique. Renvoie {"alertes": [...], "synthese": "..."}
    ou None si indisponible/erreur (dégradation propre — ne doit jamais
    empêcher le relecteur de continuer à travailler manuellement)."""
    interpretation_ref = (interpretation_ref or "").strip()
    if not interpretation_ref or not available():
        return None
    criteres_txt = "\n".join(
        f"  - [{c.get('criterion_id', '?')}] {c.get('label', '?')} — "
        f"role={c.get('role')}, expected_status={c.get('expected_status')}, "
        f"importance={c.get('importance')}, error_severity={c.get('error_severity')}"
        for c in criteria
    ) or "  (aucun critère)"
    user_content = (
        f"## Texte d'interprétation de référence\n« {interpretation_ref} »\n\n"
        f"## Critères de scoring validés par le relecteur\n{criteres_txt}\n\n"
        "Relis et signale les points douteux, s'il y en a."
    )
    try:
        client = _get_client()
        resp = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": SCORING_REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format=ScoringReviewResult,
        )
        result = resp.choices[0].message.parsed
        if result is None:
            return None
        return result.model_dump()
    except Exception as ex:
        logger.warning("gpt_annotator.review_scoring_criteria a échoué (%s: %s) — "
                        "dégradation propre.", type(ex).__name__, ex)
        return None


# ═══════════════ Génération de critères candidats scoring_v2 (P1.3) ═══════════════
# DIFFÉRENT de review_scoring_criteria (qui relit des critères déjà écrits) :
# ici GPT part DIRECTEMENT du texte d'interprétation de référence et propose
# une liste de critères scoring_v2 COMPLETS (tous les champs du schéma), sans
# connaître les critères déjà annotés par l'expert. Sert à défricher un cas
# (ou à compléter une annotation existante) — le relecteur humain reste seul
# responsable de la version finale : il relit, corrige, ajoute ou ignore.
class SuggestedCriterion(BaseModel):
    concept_name: str = Field(description="Nom clinique STANDARD du concept, en français, PAS un ID "
                              "ontologique inventé (ex. 'Onde Q de nécrose', pas 'ONDE_Q_NECROSE'). "
                              "La résolution vers un concept_id réel de l'ontologie se fait ensuite "
                              "par recherche automatique — n'invente jamais d'ID toi-même.")
    label: str = Field(description="Libellé lisible du critère.")
    role: str = Field(description="'required', 'alternative', 'optional' ou 'exclusion'.")
    expected_status: str = Field(description="'present', 'absent' ou 'hypothesis_acceptable'.")
    importance: str = Field(description="'major', 'intermediate' ou 'minor'.")
    error_severity: str = Field(description="'none', 'minor', 'major' ou 'dangerous'.")
    sufficient_alone: bool = Field(description="True si ce seul critère suffit à valider le diagnostic principal.")
    minimum_specificity: str = Field(description="'exact_only', 'child_ok', 'parent_ok' ou 'any_related'.")
    comment: str = Field(description="Courte justification clinique, citant le texte de référence.")


class SuggestedCriteriaResult(BaseModel):
    criteria: List[SuggestedCriterion]


SUGGEST_CRITERIA_SYSTEM_PROMPT = """\
Tu es un cardiologue expert, chargé de préparer un premier jet de GOLDEN DE
SCORING structuré pour un cas ECG (critères servant à noter automatiquement
des réponses d'étudiants — PAS une correction d'étudiant).

On te donne le texte d'interprétation de référence du cas (rédigé par un
cardiologue). Ta tâche : proposer la liste des critères de scoring
structurés qui permettraient de noter la réponse d'un étudiant sur ce cas.

Pour choisir les critères, tu dois te reposer sur la STRUCTURE DE L'ONTOLOGIE
qui t'est fournie (section « Concepts structurellement liés au diagnostic
principal ») plutôt que d'inventer librement des sous-éléments descriptifs à
partir du texte :
 - Cette liste contient les concepts que l'ontologie relie DÉJÀ au diagnostic
   principal (`requires` = indispensables, `supports` = renforcent sans être
   indispensables, `children` = sous-types plus précis).
 - Ne propose un critère QUE pour un concept de cette liste qui est
   EFFECTIVEMENT mentionné (ou clairement impliqué) dans le texte de
   référence — ignore les autres.
 - N'invente PAS de concept hors de cette liste, SAUF s'il correspond à un
   élément du texte clairement important et absent de la liste (diagnostic
   différentiel explicitement écarté, par exemple) — reste alors très
   sélectif.
 - Si la liste est vide ou qu'aucun de ses éléments n'est mentionné dans le
   texte, renvoie une liste de critères VIDE plutôt que d'inventer des
   critères descriptifs redondants avec le diagnostic principal déjà posé.

Pour chaque critère retenu :
 - `role` : "required" pour le(s) élément(s) indispensable(s) (souvent le
   diagnostic principal), "optional" pour les éléments descriptifs
   valorisés mais non pénalisants, "exclusion" pour un diagnostic
   différentiel proche qu'il ne faut PAS conclure à tort (uniquement si le
   texte le mentionne explicitement comme à éliminer).
 - `importance`/`error_severity` proportionnées à la gravité clinique réelle
   (un oubli sur le diagnostic principal d'une pathologie dangereuse est
   `major`/`dangerous` ; un détail descriptif mineur est `minor`/`none` ou
   `minor`).
 - `sufficient_alone=true` UNIQUEMENT pour le critère qui, à lui seul,
   suffit à valider la conclusion diagnostique principale (généralement
   un seul critère par cas, parfois aucun si le diagnostic nécessite
   plusieurs éléments combinés).
 - `minimum_specificity="exact_only"` par défaut, sauf si tu identifies
   clairement qu'un concept plus général ou plus précis serait aussi
   acceptable pédagogiquement.

Sois raisonnable en nombre (typiquement 0 à 4 critères SUPPLÉMENTAIRES par
cas, en plus du/des diagnostic(s) principal(aux) déjà validé(s)) : ne
fragmente pas excessivement, concentre-toi sur ce qui est vraiment
discriminant pour noter la réponse d'un étudiant. N'invente aucun élément
qui ne serait pas dans le texte source.

⚠️ RÈGLE ANTI-FRAGMENTATION (particulièrement pour un « ECG normal ») : si un
seul critère (le diagnostic principal, `sufficient_alone=true`) suffit à
valider toute la réponse, NE crée PAS un critère séparé pour chaque détail
descriptif qui ne fait que reformuler ce même diagnostic normal (ex. ne
propose pas séparément « QRS fins », « axe normal », « PR normal », « QTc
normal », « repolarisation normale » si le texte dit simplement « ECG
normal ») — ce sont des redites, pas des critères de scoring utiles. Un
critère descriptif optionnel n'a de sens QUE s'il apporte une information
cliniquement DISCRIMINANTE distincte du diagnostic principal (ex. préciser
le rythme sous-jacent, ou écarter explicitement un diagnostic différentiel
nommé dans le texte). En cas de doute, privilégie MOINS de critères.

IMPORTANT sur `concept_name` : donne un nom clinique STANDARD en langage
naturel correspondant EXACTEMENT (ou au plus proche) à un concept de la
liste fournie si elle est non vide (ex. « Onde Q de nécrose », « Bloc de
branche droit complet »), JAMAIS un identifiant en MAJUSCULES_SNAKE_CASE —
la résolution vers un concept_id de l'ontologie se fait automatiquement
après coup, par recherche sur ce nom. Si tu inventes toi-même un ID, il ne
correspondra à rien.
"""


def suggest_scoring_criteria(interpretation_ref: str, case_id: str = "",
                             model: str = DEFAULT_MODEL,
                             existing_criteria: Optional[List[dict]] = None) -> Optional[List[dict]]:
    """Propose une liste de critères scoring_v2 à partir du texte de
    référence d'un cas, CONTRAINTE par la structure de l'ontologie.

    Au lieu de laisser GPT fragmenter librement le texte en critères
    descriptifs (ce qui produisait des redites du diagnostic principal —
    ex. « QRS fins », « PR normal », « QTc normal » pour un simple ECG
    normal), on calcule d'abord les concepts STRUCTURELLEMENT liés au(x)
    diagnostic(s) déjà validé(s) via `golden_config.related_concepts`
    (`requires`/`supports`/`children` de l'ontologie), et on demande à GPT
    de choisir UNIQUEMENT parmi cette liste fermée (ceux réellement
    mentionnés dans le texte) plutôt que d'inventer librement.

    `existing_criteria` (optionnel) : critères DÉJÀ validés pour ce cas
    (typiquement `expert_1.criteria`). Sert à la fois à ne pas dupliquer et
    à calculer la liste fermée de concepts structurellement liés.

    Chaque `concept_name` proposé par GPT est ENSUITE résolu contre
    l'ontologie réelle (`golden_config.search_concepts`) : on ne fait
    JAMAIS confiance à un ID inventé par le modèle. Si un bon match existe
    (score élevé), le critère porte le vrai `concept_id` de l'ontologie
    (`resolved=True`). Sinon, le critère est marqué `resolved=False` avec
    ses meilleures pistes (`onto_candidates`) : à DISCUTER avec le
    relecteur humain plutôt qu'à couper court à sa création (cf. golden_config
    pour le workflow d'ajout de concept à l'ontologie).

    Renvoie une liste de dicts prêts à être fusionnés dans `criteria`, ou
    None si indisponible/erreur (dégradation propre)."""
    interpretation_ref = (interpretation_ref or "").strip()
    if not interpretation_ref or not available():
        return None
    from . import golden_config

    existing_ids = {c.get("concept_id") for c in (existing_criteria or []) if c.get("concept_id")}

    # Liste fermée des concepts structurellement liés aux diagnostics déjà
    # validés (requires/supports/children de l'ontologie) — c'est LA base
    # de la contrainte anti-fragmentation, pas juste une consigne textuelle.
    related = []
    seen_related_ids = set()
    for c in (existing_criteria or []):
        cid = c.get("concept_id")
        if not cid:
            continue
        for rc in golden_config.related_concepts(cid):
            if rc["id"] in seen_related_ids or rc["id"] in existing_ids:
                continue
            seen_related_ids.add(rc["id"])
            related.append(rc)

    existing_txt = ""
    if existing_criteria:
        lines = "\n".join(
            f"  - [{c.get('concept_id', '?')}] {c.get('label', '?')} "
            f"(role={c.get('role')}, sufficient_alone={c.get('sufficient_alone', False)})"
            for c in existing_criteria
        )
        has_sufficient = any(c.get("sufficient_alone") for c in existing_criteria)
        warning = (
            "\n\n⚠️ Un critère `sufficient_alone=true` existe déjà ci-dessus : le diagnostic "
            "principal est donc DÉJÀ validable à lui seul. Ne propose de critère "
            "supplémentaire QUE s'il correspond à un concept de la liste ci-dessous ET est "
            "réellement mentionné dans le texte ; sinon renvoie une liste VIDE."
        ) if has_sufficient else ""
        existing_txt = (
            f"\n\n## Critères DÉJÀ validés pour ce cas (ne pas dupliquer)\n{lines}{warning}"
            "\n\n⚠️ NE reformule PAS un critère déjà listé ci-dessus sous un autre nom "
            "(ex. si « BAV 2 Mobitz 1 » est déjà annoté, ne propose pas séparément « Bloc "
            "auriculoventriculaire du second degré Mobitz I » ni « Périodicité de Wenckebach » "
            "— c'est le MÊME concept clinique). Compare mentalement chaque nouvelle "
            "proposition à la liste ci-dessus avant de l'inclure."
        )
    related_txt = ""
    if related:
        rel_lines = "\n".join(
            f"  - {r['name']} (concept_id={r['id']}, relation={r['relation']}, categorie={r['categorie']})"
            for r in related
        )
        related_txt = (
            f"\n\n## Concepts structurellement liés au diagnostic principal (ontologie)\n"
            f"{rel_lines}\n\nChoisis UNIQUEMENT dans cette liste (ceux réellement mentionnés "
            "dans le texte ci-dessus) — n'en propose pas d'autres sauf exception justifiée "
            "(cf. consignes système)."
        )
    else:
        related_txt = (
            "\n\n## Concepts structurellement liés au diagnostic principal (ontologie)\n"
            "(aucun — l'ontologie ne relie aucun sous-concept au(x) diagnostic(s) déjà "
            "validé(s) pour ce cas ; ne propose donc AUCUN critère descriptif "
            "supplémentaire, renvoie une liste vide, sauf élément vraiment nouveau et "
            "cliniquement significatif explicitement mentionné dans le texte)"
        )
    user_content = (
        f"## Texte d'interprétation de référence\n« {interpretation_ref} »"
        f"{existing_txt}{related_txt}\n\nPropose UNIQUEMENT les critères manquants, s'il y en "
        "a de réellement utiles (liste vide autorisée et même préférable si tout est déjà "
        "couvert ou si la liste de concepts liés ne contient rien de mentionné dans le texte)."
    )
    try:
        client = _get_client()
        resp = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": SUGGEST_CRITERIA_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format=SuggestedCriteriaResult,
        )
        result = resp.choices[0].message.parsed
        if result is None:
            return None
        out = []
        for i, c in enumerate(result.criteria):
            matches = golden_config.search_concepts(c.concept_name, limit=5)
            best = matches[0] if matches else None
            # Doublon avec un critère déjà validé : on l'écarte purement et
            # simplement, MÊME si le meilleur score de résolution est sous
            # le seuil (ex. "Bloc AV Mobitz I" ne matche le bon ID qu'à 49
            # avec un autre concept proche en tête à 55) — on regarde TOUS
            # les candidats retournés, pas seulement le premier, sinon on
            # repropose des reformulations de critères existants comme
            # s'ils étaient neufs.
            if any(m["id"] in existing_ids for m in matches):
                continue
            # Seuil raisonnable : en dessous, on ne fait pas confiance à
            # l'auto-résolution — on préfère laisser le relecteur trancher
            # (créer le concept manquant ou choisir une meilleure piste).
            resolved = bool(best and best["score"] >= 65)
            if resolved and best is not None:
                concept_id = best["id"]
                slug = re.sub(r"[^a-z0-9_]+", "_", concept_id.lower()).strip("_") or f"critere_{i}"
            else:
                concept_id = ""  # à choisir/créer par le relecteur, pas d'ID inventé
                slug = re.sub(r"[^a-z0-9_]+", "_", c.concept_name.lower()).strip("_") or f"critere_{i}"
            out.append({
                "criterion_id": f"case_{case_id}_{slug}" if case_id else slug,
                "concept_id": concept_id,
                "concept_name_propose": c.concept_name,
                "resolved": resolved,
                "onto_candidates": matches,  # pistes ontologiques, à discuter si non résolu
                "label": c.label,
                "role": c.role,
                "expected_status": c.expected_status,
                "importance": c.importance,
                "error_severity": c.error_severity,
                "alternative_group": None,
                "group_logic": "ALL",
                "group_min_n": None,
                "sufficient_alone": c.sufficient_alone,
                "minimum_specificity": c.minimum_specificity,
                "expert_confidence": "medium",
                "evidence_source": "gpt_assisted_reviewed",
                "comment": c.comment,
            })
        return out
    except Exception as ex:
        logger.warning("gpt_annotator.suggest_scoring_criteria a échoué (%s: %s) — "
                        "dégradation propre.", type(ex).__name__, ex)
        return None


if __name__ == "__main__":
    import sys
    txt = sys.argv[1] if len(sys.argv) > 1 else (
        "Rythme sinusal régulier, PR normal, QRS fins. "
        "Pas de trouble de repolarisation. Suspicion de bloc incomplet droit."
    )
    concepts = annotate(txt)
    print(json.dumps(concepts, ensure_ascii=False, indent=2))
