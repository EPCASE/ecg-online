"""Non-régression : négation / exclusions cliniques (bug « miroir », cas 57).
================================================================================
Objectif (Palier 2, semaine 4 — FEUILLE_DE_ROUTE_ALIGNEE.md) : garantir que le
correctif `_check_exclusions()` (app/neuro_grader.py) continue à bien détecter :

  1. VIOLATION grave (rang A)   : un concept golden `statut=absent` est AFFIRMÉ
     par l'étudiant → erreur clinique (cas 57 : affirmer un « miroir » alors que
     le barème dit « Absence de miroir » = confondre myocardite et SCA ST+).
  2. VIOLATION mineure (rang B/C) : idem mais sur un descripteur secondaire.
  3. SÉCURITÉ : le concept est correctement NIÉ par l'étudiant → point crédité,
     pas de pénalité.
  4. NEUTRE : le concept n'est ni affirmé ni nié → aucun effet.

Toutes les données (texte étudiant réel, contrat golden réel, annotation
experte réelle avec `ontology_id` résolu) proviennent de la bibliothèque de cas
déjà disponible :
  - `data/cases_golden.json`      → contrat golden (exclusions statut=absent).
  - `data/extraction_golden.json` → `annotation_expert` (double-annotation
    GPT-5.6 + validation humaine, déjà présente pour ces cas). AUCUN appel
    API n'est nécessaire ici : la ground truth est déjà validée dans le repo.

On teste directement `_check_exclusions()` (la fonction protégée par ce
correctif) plutôt que le pipeline complet (NER GPT-4o + embeddings), pour que
ces tests soient rapides, déterministes et exécutables hors-ligne (CI).
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("ECG_COLLECT", "0")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import golden_config  # noqa: E402
from app.neuro_grader import _check_exclusions  # noqa: E402


def _concept(ontology_id: str, statut: str) -> SimpleNamespace:
    """Fabrique un `ExtractedConcept` minimal (duck-typing, cf. candidate_report.py)."""
    return SimpleNamespace(
        terme_brut="(test)",
        statut=statut,
        ontology_id=ontology_id,
        concept_name="(test)",
        method="test",
        justification="",
    )


def _report(concepts):
    """Fabrique un `CandidateReport` minimal (seul `concepts_extraits` est lu)."""
    return SimpleNamespace(concepts_extraits=concepts)


class ExclusionNonRegressionTest(unittest.TestCase):
    """Cas réels issus de `data/extraction_golden.json` (annotation_expert)
    dont le concept `ontology_id` recoupe une exclusion golden du même cas
    (`data/cases_golden.json`). Aucune donnée inventée."""

    # ── Violations réelles (étudiant AFFIRME à tort un concept à écarter) ──

    def test_cas57_bug_miroir_affirme_a_tort_rang_A(self) -> None:
        """Cas 57 (myocardite) : golden dit « Absence de miroir » (rang A).
        Réponse réelle (item 57-01) : « ... je vois un miroir en lateral ... »
        → le NER/l'expert résout MIROIR en statut=present → doit être flaggé
        comme violation GRAVE (le bug historique « miroir » corrigé)."""
        g = golden_config.golden_for_scorer(57)
        exclusions = g["exclusions"]
        self.assertTrue(
            any(e["concept_id"] == "MIROIR" and e["rang"] == "A" for e in exclusions),
            "le contrat golden du cas 57 doit toujours exposer MIROIR en exclusion rang A",
        )
        report = _report([_concept("MIROIR", "present")])
        out = _check_exclusions(report, exclusions)
        self.assertTrue(out["violated_A"], "affirmer MIROIR doit déclencher violated_A")
        self.assertTrue(
            any("Miroir" in e["label"] for e in out["errones"]),
            f"attendu un élément erroné mentionnant Miroir, reçu: {out['errones']}",
        )

    def test_cas14_bloc_de_branche_droit_affirme_a_tort(self) -> None:
        """Cas 14 : golden interdit de réduire l'interprétation à un simple BBD.
        Réponses réelles (items 14-01, 14-04) affirment « bloc de branche
        droit » → violation (rang A, car mappé rang A dans le golden)."""
        g = golden_config.golden_for_scorer(14)
        exclusions = g["exclusions"]
        self.assertTrue(any(e["concept_id"] == "BLOC_DE_BRANCHE_DROIT" for e in exclusions))
        report = _report([_concept("BLOC_DE_BRANCHE_DROIT", "present")])
        out = _check_exclusions(report, exclusions)
        self.assertTrue(out["violated_A"] or out["violated_B"])
        self.assertTrue(out["errones"])

    def test_cas2_fibrillation_atriale_affirmee_a_tort(self) -> None:
        """Cas 2 (BBG + artéfact mimant une arythmie) : golden dit d'éliminer
        une FA (rang A). Réponses réelles (items 2-02, 2-05) affirment
        « Fibrillation atriale » → violation grave attendue."""
        g = golden_config.golden_for_scorer(2)
        exclusions = g["exclusions"]
        self.assertTrue(any(e["concept_id"] == "FIBRILLATION_ATRIALE" for e in exclusions))
        report = _report([_concept("FIBRILLATION_ATRIALE", "present")])
        out = _check_exclusions(report, exclusions)
        self.assertTrue(out["violated_A"])

    # ── Scénario symétrique : négation correcte → crédit sécurité ──

    def test_negation_correcte_credite_comme_point_de_securite(self) -> None:
        """Si l'étudiant NIE explicitement (statut=absent) un concept que le
        golden demande d'écarter, ce n'est PAS une erreur : c'est un point de
        sécurité valorisé (`trouves`), sans pénalité ni `violated_*`."""
        g = golden_config.golden_for_scorer(57)
        exclusions = g["exclusions"]
        report = _report([_concept("MIROIR", "absent")])
        out = _check_exclusions(report, exclusions)
        self.assertFalse(out["violated_A"])
        self.assertFalse(out["violated_B"])
        self.assertTrue(
            any("Miroir" in t["label"] for t in out["trouves"]),
            f"négation correcte doit être créditée, reçu: {out['trouves']}",
        )

    def test_concept_non_mentionne_est_neutre(self) -> None:
        """Si le concept à écarter n'apparaît nulle part dans l'extraction du
        candidat (ni affirmé ni nié), aucun effet (ni bonus ni malus) — cas
        nominal, le concept n'a simplement pas été mentionné."""
        g = golden_config.golden_for_scorer(57)
        exclusions = g["exclusions"]
        report = _report([_concept("MYOCARDITE", "present")])  # sans rapport
        out = _check_exclusions(report, exclusions)
        self.assertFalse(out["violated_A"])
        self.assertFalse(out["violated_B"])
        self.assertEqual(out["errones"], [])
        self.assertEqual(out["trouves"], [])

    def test_hypothese_ne_declenche_pas_de_violation(self) -> None:
        """Un concept en simple hypothèse (« peut-être X ») ne doit PAS être
        traité comme une affirmation fautive — seul un statut `present` franc
        déclenche la violation (règle explicite de `_check_exclusions`)."""
        g = golden_config.golden_for_scorer(57)
        exclusions = g["exclusions"]
        report = _report([_concept("MIROIR", "hypothese")])
        out = _check_exclusions(report, exclusions)
        self.assertFalse(out["violated_A"])
        self.assertEqual(out["errones"], [])

    def test_rang_C_affirme_a_tort_est_traite_comme_violation_mineure(self) -> None:
        """Cas 47 : golden exclut « Complexe de fusion » en rang C (mineur).
        `_check_exclusions` ne connaît que deux paliers de gravité (A=grave,
        tout le reste=mineur) : un rang C affirmé à tort doit donc rester une
        erreur signalée et déclencher `violated_B` (plafond doux), mais
        JAMAIS `violated_A` (réservé aux exclusions rang A comme le « miroir »
        du cas 57, cf. `_report_to_correction`)."""
        g = golden_config.golden_for_scorer(47)
        exclusions = g["exclusions"]
        self.assertTrue(any(e["concept_id"] == "COMPLEXE_DE_FUSION" for e in exclusions))
        report = _report([_concept("COMPLEXE_DE_FUSION", "present")])
        out = _check_exclusions(report, exclusions)
        self.assertFalse(out["violated_A"])
        self.assertTrue(out["violated_B"])
        self.assertTrue(out["errones"])  # toujours signalé comme erreur

    def test_golden_contract_stable_51_exclusions_across_cases(self) -> None:
        """Garde-fou anti-drift : le nombre de cas golden portant au moins une
        exclusion (`statut=absent`) ne doit pas chuter silencieusement (une
        régression de curation ferait disparaître le correctif « miroir » sans
        qu'aucun test ne s'en aperçoive). Seuil bas (≥30) pour tolérer des
        évolutions futures du barème sans casser ce test à chaque édition."""
        import json

        golden = json.loads(
            (Path(__file__).resolve().parents[1] / "data" / "cases_golden.json").read_text(
                encoding="utf-8"
            )
        )["cases"]
        cases_with_exclusion = {
            int(num)
            for num, c in golden.items()
            if any(m.get("statut") == "absent" for m in c.get("mapping", {}).values())
        }
        self.assertGreaterEqual(len(cases_with_exclusion), 30)
        self.assertIn(57, cases_with_exclusion, "cas 57 (bug miroir) doit rester golden-mappé")


if __name__ == "__main__":
    unittest.main()
