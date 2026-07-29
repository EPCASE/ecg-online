"""
_fix_phase_e_conflicts.py — Correction des 19 CONFLIT RÉEL (Phase E, ROADMAP.md).
====================================================================================
Script ONE-SHOT (jetable après exécution, cf. convention `_*.py`). Corrige les
19 cas signalés par `scripts/audit_golden.py` où un même `golden_id` est mappé
à plusieurs labels avec des (rôle, statut) divergents dans `cases_golden.json`.

Politique de correction (traçable, cf. ROADMAP.md §Phase E) :
  - 17 cas "pattern 39/40" (même statut, rôle différent validant/complémentaire) :
    on démappe le(s) label(s) COMPLÉMENTAIRE(S) redondant(s), en conservant le
    label VALIDANT (celui qui pilote effectivement le scoring). Le label
    démappé reste dans le barème (scoring_config) mais n'est plus lié à un
    concept ontologique tant qu'un curateur ne le remappe pas manuellement
    vers un concept plus spécifique via /curation — il n'y a pas de perte
    d'information de scoring puisque le validant reste mappé.
  - Cas 43 (contradiction present/absent réelle, avant/après ablation) : on
    démappe le label "après ablation" (statut absent, décrit une DISPARITION
    post-thérapeutique du signe, hors du cadre du diagnostic principal de ce
    cas) en conservant le label "en rythme sinusal : pré-excitation..." (statut
    present, décrit le signe pathologique central du syndrome de WPW).
  - Cas 44 (contradiction present/absent réelle) : on démappe le label
    "Rythme non sinusal pendant la crise" (statut absent) en conservant
    "reprise d'un rythme sinusal" (statut present) — l'information "rythme non
    sinusal pendant la crise" reste couverte par ailleurs par le mapping vers
    MORPHOLOGIE_DE_L_ONDE_P_NON_SINUSALE (onde P' rétrograde) déjà présent
    dans ce même cas.

Après exécution : `python scripts/audit_golden.py` doit tomber à 0 CONFLIT RÉEL.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN_PATH = os.path.join(ROOT, "data", "cases_golden.json")

# {case_num: [labels à démapper (retirer golden_id)]}
LABELS_TO_UNMAP = {
    "6": ["Contexte étiologique mentionné : insuffisance aortique significative avec dilatation et HVG à l’échographie"],
    "8": ["Aspect normal rS en V1", "Aspect normal qR en V6"],
    "12": ["Conclusion : bloc de branche droite complet associé à une hypertrophie ventriculaire droite"],
    "17": ["Conclusion : bradycardie sinusale physiologique du sportif"],
    "16": ["Morphologie d’hémibloc antérieur gauche : rS en dérivations inférieures, qR en DI/aVL"],
    "14": ["Identifier un bloc de branche alternant"],
    "22": ["Conclure à des activités atriales stimulées, non spontanées sinusales et non rétrogrades"],
    "27": ["Diagnostic de bloc auriculoventriculaire de haut degré"],
    "31": ["Décrire l’activité atriale rapide, polymorphe/anarchique avec trémulation de la ligne de base"],
    "33": ["Identification d’un battement prématuré supraventriculaire à QRS fin identique aux QRS de base"],
    "39": ["Irrégularité sinusale périodique des intervalles PP avec accélérations et ralentissements successifs suivant la respiration"],
    "40": ["Contexte compatible avec une tachycardie sinusale réactionnelle : fièvre/surinfection, anémie, insuffisance rénale, décompensation cardiaque"],
    "43": ["Après ablation : disparition de la pré-excitation, PR non court, onde delta absente, QRS fins"],
    "44": ["Rythme non sinusal pendant la crise, activité atriale difficile à voir"],
    "46": ["Aspect de QRS proche de celui de la première tachycardie en faveur d’une tachycardie antidromique sur voie accessoire"],
    "56": [
        "Définition du microvoltage : QRS ≤ 5 mm en périphériques et/ou ≤ 10 mm en précordiales, ici absence de dépassement de ces seuils",
        "Contexte compatible avec perforation de sonde de défibrillateur et épanchement/tamponnade",
    ],
    "68": ["Signe de gravité imposant une prise en charge urgente comme SCA avec sus-décalage ST"],
    "70": [
        "Sus-décalage ST majeur > 10 mm en territoire inférieur",
        "Aspect en dôme monophasique englobant l’onde T",
    ],
}


def main():
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        data = json.load(f)

    total_removed = 0
    not_found = []
    for num, labels in LABELS_TO_UNMAP.items():
        case = data["cases"].get(num)
        if not case:
            not_found.append((num, "CAS INTROUVABLE"))
            continue
        mapping = case.get("mapping", {})
        for label in labels:
            if label in mapping:
                cid = mapping[label].get("golden_id")
                del mapping[label]
                total_removed += 1
                print(f"[cas {num}] démappé : {cid} <- « {label[:70]}... »")
            else:
                not_found.append((num, label))

    if not_found:
        print("\n⚠️ Labels non trouvés (vérifier accents/apostrophes) :")
        for num, label in not_found:
            print(f"  [cas {num}] {label!r}")

    print(f"\nTotal démappé : {total_removed}")

    if not not_found:
        with open(GOLDEN_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ Écrit dans {GOLDEN_PATH}")
    else:
        print("❌ Rien écrit (labels manquants à corriger d'abord).")


if __name__ == "__main__":
    main()
