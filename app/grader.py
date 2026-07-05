"""
grader.py — Correction ouverte d'une réponse ECG par GPT
========================================================
Cœur autonome de l'app : prend le texte libre d'un candidat sur un cas ECG
et le compare à l'interprétation de référence (i        arguments = tool_calls[0].function.arguments  # type: ignore[union-attr]
        data = json.loads(arguments)
        score = int(max(0, min(100, data.get("score", 0))))
        return Correction(
            score=score,
            verdict=data.get("verdict", ""),
            diagnostic_retenu=data.get("diagnostic_retenu", ""),
            score_diagnostic=int(max(0, min(100, data.get("score_diagnostic", score)))),
            score_descriptif=int(max(0, min(100, data.get("score_descriptif", score)))),
            correspondance=data.get("correspondance", ""),
            type_erreur=data.get("type_erreur", ""),
            elements_trouves=data.get("elements_trouves", []),
            elements_manques=data.get("elements_manques", []),
            elements_errones=data.get("elements_errones", []),
            commentaire=data.get("commentaire", ""),
            model=model,
        )e de Pierre) via
un appel GPT structuré. Retourne un score (0-100) + un commentaire pédagogique
+ le détail des éléments trouvés / manqués / erronés.

Aucune dépendance au pipeline ontologique : 100 % autonome, une seule clé
OPENAI_API_KEY. Le modèle est configurable (GPT-4o par défaut).

Contrat de sortie (JSON strict, validé) :
  {
    "score": 78,
    "verdict": "Bonne interprétation, diagnostic principal correct.",
    "elements_trouves":  [{"label": "...", "rang": "A|B|C"}],
    "elements_manques":  [{"label": "...", "rang": "A|B|C", "importance": "..."}],
    "elements_errones":  [{"label": "...", "correction": "..."}],
    "commentaire": "Texte pédagogique en markdown.",
    "diagnostic_retenu": "..."
  }
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional

from openai import OpenAI

DEFAULT_MODEL = os.environ.get("ECG_GRADER_MODEL", "gpt-4o-2024-08-06")

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    """Client OpenAI paresseux (thread-safe, réutilisé)."""
    global _client
    if _client is None:
        _client = OpenAI()   # lit OPENAI_API_KEY dans l'environnement
    return _client


SYSTEM_PROMPT = """\
Tu es un cardiologue expert et enseignant en ECG (préparation EDN/ECOS, France).
Tu corriges la réponse LIBRE d'un étudiant sur un cas ECG, en la comparant à
l'INTERPRÉTATION DE RÉFÉRENCE fournie (rédigée par un enseignant).

## Principes de correction
1. Le DIAGNOSTIC PRINCIPAL prime : s'il est correct, le score démarre haut
   (>= 60). S'il est manqué ou faux, le score reste bas (<= 40) même si des
   descripteurs secondaires sont justes.
2. Récompense la démarche (fréquence, rythme, axe, conduction, repolarisation)
   quand elle est présente et juste, mais NE pénalise PAS l'absence de détails
   mineurs si le diagnostic est bon et bien argumenté.
3. Sanctionne les affirmations FAUSSES ou dangereuses (ex. conclure « normal »
   sur un tracé pathologique = faute grave, plafonne le score à 30).
4. Utilise le rang EDN quand c'est pertinent (A = indispensable, B = important,
   C = complémentaire). Un élément rang A manqué doit peser lourd.
5. Reste FACTUEL : ne crédite que ce qui est réellement écrit par l'étudiant.
   Sois bienveillant mais rigoureux.

## Crédit PARTIEL (barème progressif — très important)
Une réponse peut être correcte sans employer le libellé exact. À l'inverse, une
description forte sans nommer le diagnostic mérite un crédit partiel, pas 0 ni 100.
Exemple pour une extrasystole ventriculaire (ESV) :
 - « ESV » / « extrasystole ventriculaire » nommée .............. crédit complet
 - extrasystole + QRS large + absence d'onde P + pause compensatoire ... 75-90 %
 - extrasystole + QRS large seulement .......................... 50-70 %
 - extrasystole seule .......................................... 30-50 %
 - QRS large isolé ............................................. pas de validation

## Équivalences cliniques à reconnaître (ne PAS pénaliser)
- Flutter : « commun / isthmique / typique / antihoraire / CTI-dépendant / droit »
  = flutter droit typique (crédit complet). « flutter atrial » seul = partiel.
- Bloc de branche droit : « BBD + QRS large » ou « BBD + QRS ≥ 120 ms » ou
  « rSR' en V1-V2 + QRS large » = BBD COMPLET. « BBD » seul = partiel. (idem BBG.)
- Pré-excitation : « WPW » ou « PR court + onde delta » = complet ;
  « PR court » seul ou « onde delta » seule = partiel.
- SCA ST+ : « SCA ST+ / STEMI / IDM ST+ / infarctus ST+ » ou
  « sus-décalage ST territorial + miroir » ou « courant de lésion sous-épicardique
  territorial » ou « onde de Pardee » = complet.
- Microvoltage : « microvoltage / microvolté / bas voltage / faible voltage /
  petits QRS / QRS de petite amplitude / QRS très petits » = oui.
  ⚠️ « QRS fins » seul (= QRS étroits) ne vaut PAS microvoltage.
- Stimulation : « électro-entraîné / électrostimulé / spike / pacemaker »,
  en distinguant l'étage atrial (spike auriculaire, électro-entraîné à l'étage
  atrial) et ventriculaire (spike ventriculaire, QRS larges stimulés).

## Signes NÉGATIFS (à valoriser)
Les négations pertinentes sont pédagogiquement importantes et doivent compter
quand la référence les attend : « pas d'ischémie », « pas de trouble de conduction »,
« pas d'hypertrophie », « QT non allongé », « QRS non larges », « PR normal »…

## Règle « ECG normal »
- « ECG normal » / « tracé normal » explicite SUFFIT si le diagnostic attendu est
  un ECG normal (ne pas exiger tous les critères détaillés).
- OU au moins 4 critères de normalité présents (rythme sinusal, fréquence normale,
  axe normal, PR normal, QRS fins, QT normal, absence d'ischémie/conduction/
  hypertrophie/arythmie) permettent d'inférer « ECG normal ».
- MAIS bloque « ECG normal » si un diagnostic pathologique explicite est présent
  (BAV, bloc de branche, microvoltage, pré-excitation, SCA, flutter, FA, ESV
  significatives, hypertrophie, anomalie de repolarisation pathologique).

## Deux notes séparées
Fournis, en plus du score global :
 - `score_diagnostic` (0-100) : l'étudiant a-t-il identifié le diagnostic attendu ?
 - `score_descriptif` (0-100) : a-t-il correctement décrit les critères ECG ?
Le `score` global reflète surtout le diagnostic (pondération ~70/30).

## Type d'erreur (pour chaque cas)
Classe la nature du principal écart via `type_erreur` :
 - « aucune » (réponse correcte)
 - « etudiant » (vraie erreur clinique)
 - « incomplet » (réponse acceptable mais partielle)
 - « formulation » (bon fond, libellé/synonyme non standard)

Le commentaire s'adresse à l'étudiant (tutoiement pédagogique), concis
(4-8 phrases), en français, format markdown avec au besoin des puces.

Réponds UNIQUEMENT via l'outil `rendre_correction`.
"""

TOOL = {
    "type": "function",
    "function": {
        "name": "rendre_correction",
        "description": "Retourne la correction structurée de la réponse de l'étudiant.",
        "parameters": {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": 0, "maximum": 100,
                          "description": "Note globale 0-100 (pondérée ~70 diagnostic / 30 descriptif)."},
                "score_diagnostic": {"type": "integer", "minimum": 0, "maximum": 100,
                                     "description": "L'étudiant a-t-il identifié le diagnostic attendu ?"},
                "score_descriptif": {"type": "integer", "minimum": 0, "maximum": 100,
                                     "description": "Qualité de la description des critères ECG."},
                "verdict": {"type": "string",
                            "description": "Une phrase de synthèse."},
                "correspondance": {"type": "string",
                                   "enum": ["exacte", "acceptable", "partielle", "incorrecte"],
                                   "description": "Niveau de correspondance du diagnostic principal."},
                "type_erreur": {"type": "string",
                                "enum": ["aucune", "etudiant", "incomplet", "formulation"],
                                "description": "Nature du principal écart."},
                "diagnostic_retenu": {"type": "string",
                                      "description": "Le diagnostic principal que l'étudiant a retenu (ou 'aucun')."},
                "elements_trouves": {
                    "type": "array",
                    "items": {"type": "object", "properties": {
                        "label": {"type": "string"},
                        "rang": {"type": "string", "enum": ["A", "B", "C", "?"]},
                    }, "required": ["label", "rang"]},
                },
                "elements_manques": {
                    "type": "array",
                    "items": {"type": "object", "properties": {
                        "label": {"type": "string"},
                        "rang": {"type": "string", "enum": ["A", "B", "C", "?"]},
                        "importance": {"type": "string"},
                    }, "required": ["label", "rang"]},
                },
                "elements_errones": {
                    "type": "array",
                    "items": {"type": "object", "properties": {
                        "label": {"type": "string"},
                        "correction": {"type": "string"},
                    }, "required": ["label", "correction"]},
                },
                "commentaire": {"type": "string",
                                "description": "Feedback pédagogique markdown, 4-8 phrases."},
            },
            "required": ["score", "score_diagnostic", "score_descriptif",
                         "verdict", "correspondance", "type_erreur",
                         "diagnostic_retenu", "elements_trouves",
                         "elements_manques", "elements_errones", "commentaire"],
        },
    },
}


@dataclass
class Correction:
    score: int
    verdict: str
    diagnostic_retenu: str
    score_diagnostic: int = 0
    score_descriptif: int = 0
    correspondance: str = ""
    type_erreur: str = ""
    elements_trouves: List[dict] = field(default_factory=list)
    elements_manques: List[dict] = field(default_factory=list)
    elements_errones: List[dict] = field(default_factory=list)
    commentaire: str = ""
    model: str = ""
    error: Optional[str] = None

    def to_dict(self):
        return asdict(self)


def _build_user_prompt(case: dict, texte_etudiant: str) -> str:
    parts = [
        f"# CAS {case.get('num')} — {case.get('titre')}",
        "",
        f"## Contexte patient\n{case.get('patient','')}\n{case.get('contexte','')}",
        "",
        "## Interprétation de référence (enseignant)",
        case.get("interpretation_ref", "") or "(non fournie)",
    ]
    if case.get("referentiel"):
        parts += ["", "## Ce que dit le référentiel EDN", case["referentiel"][:1500]]
    parts += [
        "",
        "## Réponse LIBRE de l'étudiant à corriger",
        f"« {texte_etudiant.strip()} »",
        "",
        "Corrige cette réponse en appelant `rendre_correction`.",
    ]
    return "\n".join(parts)


def grade(case: dict, texte_etudiant: str, model: str = DEFAULT_MODEL,
          temperature: float = 0.0) -> Correction:
    """Corrige une réponse d'étudiant pour un cas donné. Robuste aux erreurs."""
    texte_etudiant = (texte_etudiant or "").strip()
    if not texte_etudiant:
        return Correction(score=0, verdict="Réponse vide.",
                          diagnostic_retenu="aucun",
                          commentaire="Aucune réponse n'a été fournie.",
                          model=model)
    try:
        resp = get_client().chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(case, texte_etudiant)},
            ],
            tools=[TOOL],  # type: ignore[arg-type]
            tool_choice={"type": "function", "function": {"name": "rendre_correction"}},
        )
        tool_calls = resp.choices[0].message.tool_calls or []
        if not tool_calls:
            raise ValueError("Le modèle n'a pas renvoyé d'appel d'outil.")
        arguments = tool_calls[0].function.arguments  # type: ignore[union-attr]
        data = json.loads(arguments)
        score = int(max(0, min(100, data.get("score", 0))))
        return Correction(
            score=score,
            verdict=data.get("verdict", ""),
            diagnostic_retenu=data.get("diagnostic_retenu", ""),
            score_diagnostic=int(max(0, min(100, data.get("score_diagnostic", score)))),
            score_descriptif=int(max(0, min(100, data.get("score_descriptif", score)))),
            correspondance=data.get("correspondance", ""),
            type_erreur=data.get("type_erreur", ""),
            elements_trouves=data.get("elements_trouves", []),
            elements_manques=data.get("elements_manques", []),
            elements_errones=data.get("elements_errones", []),
            commentaire=data.get("commentaire", ""),
            model=model,
        )
    except Exception as ex:
        return Correction(score=0, verdict="Erreur de correction.",
                          diagnostic_retenu="", commentaire="",
                          model=model,
                          error=f"{type(ex).__name__}: {ex}")


if __name__ == "__main__":
    # Smoke test rapide (nécessite OPENAI_API_KEY + data/cases.json)
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    cases = json.load(open(os.path.join(here, "..", "data", "cases.json"),
                           encoding="utf-8"))["cases"]
    case = next(c for c in cases if c["num"] == 3)  # ECG normal
    txt = sys.argv[1] if len(sys.argv) > 1 else "rythme sinusal, ECG normal, FC 70"
    corr = grade(case, txt)
    print(json.dumps(corr.to_dict(), ensure_ascii=False, indent=2))
