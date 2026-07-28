"""
scoring_thresholds.py — Registre central des seuils numériques du scorer.
==========================================================================
Phase 0.3 du plan d'analyse (audit architecture, juillet 2026).

Constat de l'audit : le pipeline neurosymbolique est majoritairement piloté
par des mécanismes GÉNÉRIQUES (ontologie déclarative : requires/excludes/
implies/negation_of, cf. `scoring_v3.py`) — bon signe de robustesse. Mais
plusieurs SEUILS NUMÉRIQUES qui pilotent des décisions de notation étaient
dispersés, non documentés, et dupliqués entre `app/neuro_grader.py`,
`rag_pipeline/scoring_v3.py` et `rag_pipeline/candidate_report.py` :
  - `score_pct >= 60.0`   (neuro_grader : validant compte comme « trouvé »)
  - `min(score, 25)`      (neuro_grader : plafond exclusion rang A)
  - `min(score, 70)`      (neuro_grader : plafond exclusion rang B)
  - `2.0/3.0`, `1.0/3.0`  (scoring_v3 : crédit parent proche/lointain)
  - `_BACKSTOP_MIN_WORDS` (candidate_report : longueur mini rattrapage lexical)
  - `90/70/50`            (candidate_report : bandes de couleur du rapport HTML)

Ce module est la SOURCE UNIQUE de ces valeurs. Modifier le comportement de
notation = modifier UNE constante ICI (avec sa justification), jamais un
nombre magique dispersé dans un `if`. Objectif : rendre les futurs réglages
(Phase 1+) traçables, revuables en code review, et testables isolément.

Convention : chaque constante porte un commentaire expliquant SON EFFET et
POURQUOI cette valeur (pas juste ce qu'elle fait). Aucune de ces valeurs
n'a été modifiée par ce refactor — c'est une extraction pure, le
comportement de notation reste strictement identique (cf. non-régression
Phase 0.2 : 322 réponses réelles, 0 nouvelle contradiction).
"""
from __future__ import annotations

# ─────────────────────────── Validants (app/neuro_grader.py) ───────────────────────────

# Un validant du scoring V3 peut renvoyer found=True avec un score_pct partiel
# (ex. match_type="requires" avec seulement une partie des critères réunis).
# L'afficher comme « ✓ trouvé » en dessous de ce seuil créait l'incohérence
# « tout semble trouvé mais la note est basse » (cas 2, sans « rythme sinusal »
# explicite). Sous ce seuil → affiché comme « à compléter » (rang A manqué).
VALIDANT_FOUND_THRESHOLD_PCT: float = 60.0

# Plafonds de score appliqués quand l'étudiant AFFIRME à tort un concept que
# le golden exige d'ÉCARTER (`statut="absent"`, cf. bug « miroir » cas 57).
#   • rang A (faute grave, ex. confondre 2 diagnostics incompatibles) : plafond
#     bas — la note ne peut plus refléter une « bonne » réponse.
#   • rang B (faute mineure, exclusion mais pas centrale) : plafond plus doux.
EXCLUSION_RANG_A_SCORE_CAP: int = 25
EXCLUSION_RANG_B_SCORE_CAP: int = 70

# ─────────────────────────── Scoring ontologique (rag_pipeline/scoring_v3.py) ──────

# Crédit accordé quand un concept golden n'est pas trouvé directement mais
# qu'un de ses `has_qualifiers`/`has_qualifier_families` l'est (qualifiant
# proche reconnu, ex. « bloc de branche » qualifié mais pas le type exact).
SUB_REQUIRE_QUALIFIER_CREDIT: float = 2.0 / 3.0

# Crédit accordé quand seul un `supports` (élément de support, encore plus
# indirect que le qualifiant) du concept golden est reconnu.
SUB_REQUIRE_SUPPORT_CREDIT: float = 1.0 / 3.0

# Crédit pour la relation déclarative `implies` (antécédent clinique) —
# GELÉ À 0.0 (Option A, découplage de la brique scoring, cf. commentaire
# détaillé dans scoring_v3.py). L'axiome reste actif pour la MESURE mais
# neutralisé pour la NOTE tant qu'un barème multi-niveaux n'est pas décidé.
IMPLIES_CREDIT: float = 0.0

# Crédit pour la relation déclarative `negation_of` (pôle positif nié) —
# GELÉ À 0.0 pour la même raison (Option A). La lecture sémantique de la
# négation par le NER reste 100 % active en amont ; seul le crédit barème
# est neutralisé.
NEGATION_CREDIT: float = 0.0

# ─────────────────────────── Rattrapage lexical (rag_pipeline/candidate_report.py) ──

# Longueur minimale (en mots) d'un synonyme pour être éligible au rattrapage
# lexical déterministe post-NER. Un synonyme trop court (« bloc », « onde »)
# risquerait un faux positif ; les vrais oublis du NER sont des expressions
# multi-mots distinctives.
BACKSTOP_MIN_DISTINCTIVE_WORDS: int = 3

# ─────────────────────────── Affichage (rapport HTML / synthèse texte) ────────────

# Bandes de score pour la coloration/le libellé du rapport (cosmétique — sans
# impact sur la note elle-même). Gardées ici pour visibilité et cohérence
# inter-modules (candidate_report.format_report_html, _build_comment, etc.).
SCORE_BAND_EXCELLENT: int = 90   # >= : "Excellent" / vert
SCORE_BAND_GOOD: int = 70        # >= : "Bien" / orange
SCORE_BAND_PARTIAL: int = 50     # >= : "À améliorer" / rouge-orangé
                                 # < SCORE_BAND_PARTIAL : "Insuffisant" / rouge
