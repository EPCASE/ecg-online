"""
gpt_annotator.py — Second annotateur automatique (GPT-5.6), indépendant du pipeline.
=====================================================================================
Cf. GOLDEN_EXTRACTION.md §5bis pour la justification méthodologique.

⚠️ Rôle STRICTEMENT limité à proposer un brouillon candidat supplémentaire,
au même titre que `pipeline_extraction` : ce module ne doit JAMAIS voir la
sortie du pipeline NER de production (`ner_extractor.py`, GPT-4o) — sinon on
mesurerait la cohérence du modèle avec lui-même, pas sa justesse clinique
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


if __name__ == "__main__":
    import sys
    txt = sys.argv[1] if len(sys.argv) > 1 else (
        "Rythme sinusal régulier, PR normal, QRS fins. "
        "Pas de trouble de repolarisation. Suspicion de bloc incomplet droit."
    )
    concepts = annotate(txt)
    print(json.dumps(concepts, ensure_ascii=False, indent=2))
