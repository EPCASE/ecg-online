"""pattern_inference.py — Inference d'EXTRACTION de patterns "verdict".

Moteur GENERIQUE (aucun ID code en dur) : il lit, dans l'ontologie, les
concepts portant le flag declaratif `infer_from_requires` et conclut leur
presence quand leurs `requires` sont suffisamment satisfaits ET qu'aucune de
leurs `excludes_families` n'est presente.

Conforme au principe "savoir dans l'ontologie, mecanismes dans le code" :
  - le SAVOIR = quels concepts sont des verdicts inferables (`infer_from_requires`),
    leurs `requires`, `excludes_families`, `negation_of` (ontologie, expert)
  - le MECANISME = la satisfaction des requires + l'ecran excludes (code generique)

Role : c'est de l'EXTRACTION ("trouver l'ECG normal dans la lecture de
l'etudiant"), PAS du barème. Le scoring juge ensuite si c'est correct. Sans ce
moteur, un etudiant qui decrit un tracé normal ("rythme sinusal, PR normal,
QRS fins, pas de trouble") sans ecrire litteralement "ECG normal" n'a jamais
le concept-verdict extrait -> sensibilite ECG_NORMAL 41.7%. Avec : 83.3%.

Polarite (requires "normaux/negatifs") : un require R est satisfait si R (ou un
descendant) est present, OU si son pendant pathologique (`R.negation_of` ou le
concept que R nie) est explicitement absent. Lu de l'ontologie.

Zero dependance externe (pur stdlib).
"""
from __future__ import annotations
import re
import unicodedata
from typing import Dict, List, Optional, Set


def _canon(s: str) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s).strip())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"_+", "_", re.sub(r"[^A-Z0-9]+", "_", s.upper())).strip("_")


class PatternInferencer:
    """Infere les concepts-verdict flagges `infer_from_requires` dans l'ontologie."""

    def __init__(self, concepts: Dict[str, dict]):
        self.concepts = concepts
        self._canon2id = {_canon(c): c for c in concepts}
        # index hierarchie (canon)
        self._children = {
            _canon(c): {_canon(x) for x in (cd.get("children") or [])}
            for c, cd in concepts.items()
        }
        self._requires = {
            _canon(c): [_canon(r) for r in (cd.get("requires") or [])]
            for c, cd in concepts.items()
        }
        self._excl_fam = {
            _canon(c): [_canon(f) for f in (cd.get("excludes_families") or [])]
            for c, cd in concepts.items()
        }
        self._neg_of = {
            _canon(c): [_canon(x) for x in (cd.get("negation_of") or [])]
            for c, cd in concepts.items()
        }
        self._desc = {c: self._descendants(c) for c in self._canon2id}
        # concepts-verdict opt-in (lecture du flag declaratif)
        self.targets = []  # [(canon_id, min_satisfied)]
        for c, cd in concepts.items():
            flag = cd.get("infer_from_requires")
            if isinstance(flag, dict):
                self.targets.append((_canon(c), int(flag.get("min_satisfied", 1))))
            elif flag:  # True / truthy : exiger tous les requires
                kc = _canon(c)
                self.targets.append((kc, len(self._requires.get(kc, [])) or 1))

    def _descendants(self, root: str) -> Set[str]:
        seen, stack = set(), list(self._children.get(root, ()))
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            stack.extend(self._children.get(x, ()))
        return seen

    def _present_or_desc(self, cid: str, found: Set[str]) -> bool:
        return cid in found or bool(self._desc.get(cid, set()) & found)

    def _require_satisfied(self, r: str, found: Set[str], absent: Set[str]) -> bool:
        # positif : le require (ou un descendant) est present
        if self._present_or_desc(r, found):
            return True
        # polarite : le pendant pathologique du require est explicitement absent
        for x in self._neg_of.get(r, []):
            if x in absent or (self._desc.get(x, set()) & absent):
                return True
        return False

    def _excluded(self, target: str, found: Set[str]) -> Optional[str]:
        for fam in self._excl_fam.get(target, []):
            if self._present_or_desc(fam, found):
                return fam
        return None

    def infer(self, found_ids, absent_ids=None):
        """Renvoie une liste de dicts pour chaque concept-verdict infere :
          {ontology_id, statut='present', method='pattern_inference',
           n_requires, n_total, blocked_by=None}
        `found_ids`/`absent_ids` : iterables d'IDs ontologiques (present/absent).
        N'infere PAS un concept deja present. Idempotent, point fixe.
        """
        found = {_canon(x) for x in (found_ids or [])}
        absent = {_canon(x) for x in (absent_ids or [])}
        out = []
        emitted: Set[str] = set()
        changed = True
        while changed:
            changed = False
            for target, min_sat in self.targets:
                if target in found or target in emitted:
                    continue
                reqs = self._requires.get(target, [])
                if not reqs:
                    continue
                # ecran excludes : une famille pathologique presente => pas de verdict
                if self._excluded(target, found):
                    continue
                n_ok = sum(1 for r in reqs if self._require_satisfied(r, found, absent))
                if n_ok >= min_sat:
                    cid = self._canon2id.get(target, target)
                    out.append({
                        "ontology_id": cid,
                        "statut": "present",
                        "method": "pattern_inference",
                        "n_requires": n_ok,
                        "n_total": len(reqs),
                    })
                    emitted.add(target)
                    found.add(target)  # peut declencher un autre verdict
                    changed = True
        return out
