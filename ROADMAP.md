# 🗺️ ROADMAP — ECG Lecture

> ⚠️ **Ce fichier contient 2 sections** :
> 1. **Suivi d'exécution ACTUEL** (ci-dessous) — reflète l'état réel du projet aujourd'hui,
>    fait le pont avec `../AUDIT.md` (§8, plan P0/P1/P2 du 2026-07-03).
> 2. **Roadmap historique d'origine** (à partir de "Phase 0 — Fondations") — décrit la
>    genèse du projet (extraction des 75 cas, grader GPT seul). **Obsolète sur le scoring**
>    (le scoring ontologique V3 décrit comme "futur" en Phase 2 y est en réalité déjà en
>    prod depuis longtemps) mais gardée pour l'historique et le contrat de données.

---

## 🔄 SUIVI D'EXÉCUTION — plan d'audit (cf. `../AUDIT.md` §8)

> **But du projet** : une plateforme en ligne où l'étudiant lit un ECG, écrit son
> interprétation en **texte libre**, et reçoit une correction **IA neurosymbolique**
> (score + commentaire pédagogique) fondée sur une banque de 75 cas et une ontologie.
> Objectif 10 mois : **prototype robuste → facultés → open source multi-langue**.

### 🔴 P0 — Bloquant (avant toute conclusion/publication)

| # | Action | Statut |
|---|--------|:------:|
| P0.1 | Créer le **golden d'extraction** (~50 réponses annotées par un expert, tous les concepts réellement présents, pas seulement ceux qui comptent pour la note ; double annotation sur ~15 → Kappa de Cohen) | ❌ pas commencé |
| P0.2 | Recalculer précision/rappel/F1 réels de l'extraction contre ce golden | ❌ dépend de P0.1 |
| P0.3 | Unifier les chiffres publiés (README ~92 %, RAG-onto 62,4 %, ARCHITECTURE 42 %, CSV réel 85,1 %/60,2 % → incohérents) en une source de vérité versionnée | ❌ pas commencé |
| P0.4 | Tests de non-régression du scoring | ✅ fait (`rag_pipeline/tests/test_scoring_v3.py`, 18 tests) |

### 🟡 P1 — Important (validité scientifique)

| # | Action | Statut |
|---|--------|:------:|
| P1.5 | Étendre le golden de **scoring** (40-50 cas, ≥2 experts, plusieurs validants/cas — actuellement 75 cas mais mono-expert) | ❌ pas commencé (voir *Phase E* ci-dessous : le nettoyage de cohérence interne du golden actuel est un prérequis pratique) |
| P1.6 | Refondre la métrique : note exactitude (existante) + note fiabilité (pénalité concepts faux pondérée par gravité clinique) | ❌ dépend de P0.1 |
| P1.7 | Corriger la négation trop généreuse (`absent("trouble de repolarisation")` → `ECG_NORMAL` complet = 100 % avec une seule négation isolée) | ❌ pas commencé |
| P1.8 | Ablation par brique (NER/Search/Juge) + validation humaine d'un échantillon du juge | ❌ pas commencé |
| P1.9 | Étendre les tests à `semantic_layer` et à la conversion des négations | ❌ pas commencé |

### 🟢 P2 — Consolidation

| # | Action | Statut |
|---|--------|:------:|
| P2.10 | Monorepo (fusionner `RAG ontologique` ↔ `ECG lecture/rag_pipeline`, nettoyer les scripts `_*.py` jetables) | ❌ pas commencé |
| P2.11 | Fallback local (embeddings sentence-transformers + juge Mistral/Llama, reproductibilité) | ❌ pas commencé |
| P2.12 | Panel multi-juges + exploitation du score de confiance | ❌ pas commencé |
| P2.13 | (Optionnel/bonus) Mapping SNOMED + raisonneur OWL | ❌ déclassé par l'audit lui-même |

---

### 🧹 Travaux réalisés HORS plan initial (dette annexe, rattachable à P1.5)

En creusant le golden de scoring existant (préalable pratique à son extension), des
incohérences internes ont été détectées et corrigées :

- **Phase A — Centralisation des seuils de scoring** ✅ *(commit `bc77081`)*
  `rag_pipeline/scoring_thresholds.py` : élimination des magic numbers dans
  `neuro_grader.py`, `scoring_v3.py`, `candidate_report.py`.
- **Phase B — Audit automatisé golden × ontologie** ✅ *(commit `bc77081`)*
  `scripts/audit_golden.py` (statique) + `scripts/audit_golden_impact.py`
  (cross-référence avec 322 réponses réelles Google Sheets) : détecte duplications
  concept_id, ID inconnus, cas sans validant, relations `requires`/`excludes` cassées.
- **Phase C — Correction golden : cas 4 (contradiction present/absent)** ✅ *(commit `cc16a81`)*
  `HYPERTROPHIE_VENTRICULAIRE_GAUCHE` était mappé à la fois `present` (validant) et
  `absent` (descripteur, critère de Sokolow) dans le même cas → remappé vers le
  concept qualifier dédié `INDICE_DE_SOKOLOW__35_MM`.
- **Phase D — Triage CONFLIT RÉEL vs doublon inoffensif** ✅ *(commit `412c8d2`)*
  `check_duplicate_concept_role` croise désormais avec `scoring_config.json` pour
  distinguer les vraies contradictions (rôle/statut divergents) des redondances
  cosmétiques du barème. Résultat sur les 40 duplications restantes : **19 CONFLIT
  RÉEL / 21 doublons inoffensifs**.

### 🔜 Phase E — PROCHAINE ÉTAPE : corriger les 19 CONFLIT RÉEL restants

**Statut : ❌ pas commencé — c'est la suite immédiate.**

Liste des 19 cas (obtenue via `python scripts/audit_golden.py`), à traiter par lot
puis valider en UNE SEULE fois avec `scripts/audit_golden_impact.py` (replay coûteux
en API/Google Sheets, à ne pas relancer à chaque petite modif) :

| Cas | Concept | Gravité |
|---|---|---|
| 43 | `FAISCEAU_ACCESSOIRE_A_CONDUCTION_ANTEROGRADE` | 🔴 present/absent — même pattern que cas 4 |
| 44 | `RYTHME_SINUSAL` | 🔴 present/absent — même pattern que cas 4 |
| 6, 8, 12, 17, 16, 14, 22, 27, 31, 33, 39, 40, 46, 56 (×2), 68, 70 | divers | 🟠 rôle validant/descripteur divergent, statut identique (present/present) — pattern cas 39/40, déjà neutralisé côté scorer par le garde-fou `_validant_manque_ids` mais données à nettoyer |

**Procédure** :
1. Corriger les cas 43 et 44 en priorité (vraies contradictions cliniques comme cas 4).
2. Traiter le reste du lot (17 cas restants) par groupes de 5-6.
3. Une fois tout le lot terminé : `scripts/audit_golden.py` (doit tomber à 0 CONFLIT RÉEL)
   **puis** `scripts/audit_golden_impact.py` (322 réponses, doit rester 0 contradiction)
   pour valider l'ensemble en une seule passe.
4. Commit + push.

### Repères de contexte technique

- **Golden** : `data/cases_golden.json` (75 cas, label → concept_id + statut).
- **Rôles** : `data/scoring_config.json` (label → validant/complémentaire).
- **Jointure** : `app/golden_config.py::golden_for_scorer(num)`.
- **Audit statique** : `python scripts/audit_golden.py` (`--case NUM` pour un seul cas).
- **Audit impact réel** : `python scripts/audit_golden_impact.py` (nécessite
  `.streamlit/secrets.toml` + accès Google Sheets — **coûteux, à ne lancer qu'en fin de lot**).
- Env : `.venv\Scripts\python.exe`, encodage forcé `PYTHONIOENCODING=utf-8` sous PowerShell.

---

## 📜 Roadmap historique d'origine (genèse du projet — scoring GPT seul, aujourd'hui dépassé)

> **But du projet** : une plateforme en ligne où l'étudiant lit un ECG, écrit son
> interprétation en **texte libre**, et reçoit une correction **IA** (score +
> commentaire pédagogique) fondée sur une banque de **75 cas** de référence.
>
> **Ce document est le point d'entrée du workspace.** Après avoir fermé la
> conversation actuelle, ouvrez le dossier `ecg-online/` comme workspace : tout
> ce qu'il faut est ici, listé ci‑dessous.

---

## 📍 Où trouver quoi (le dépôt)

**Dépôt applicatif autonome :** `ECG lecture/ecg-online/`
C'est le seul dossier nécessaire pour faire tourner et déployer l'app.

| Élément | Emplacement | État |
|---------|-------------|------|
| Banque de 75 cas (contrat de données) | `data/cases.json` | ✅ |
| Tracés ECG (108 PNG) | `data/ecg_images/` | ✅ |
| Extraction brute Word | `data/cases_bank_raw.json` | ✅ |
| Mapping cas → pages PDF | `data/pdf_case_map.json` | ✅ |
| Correcteur IA (GPT‑4o) | `app/grader.py` | ✅ |
| Accès banque + expurgation | `app/cases_repo.py` | ✅ |
| API Flask + service front/images | `app/server.py` | ✅ |
| Interface web | `frontend/{index.html, style.css, app.js}` | ✅ |
| Galerie statique des 75 tracés | `ecg_gallery_75.html` | ✅ |
| Scripts d'extraction (docx/pdf) | `scripts/` | ✅ |
| Déploiement Scalingo | `Procfile`, `runtime.txt`, `requirements.txt` | ✅ |
| Config secrets | `.env.example` (+ `.env` local) | ✅ |
| Doc d'utilisation | `README.md` | ✅ |

**Sources brutes** (hors dépôt, sur le poste de travail) :
- Word : `Desktop\Articles\relecture ECG Pierre\textes à envoyer.docx`
- PDF  : `Desktop\Articles\relecture ECG Pierre\ECG 12.pdf` (307 pages)

---

## ✅ Phase 0 — Fondations (FAIT)

- [x] Extraction des **75 cas** depuis le Word (énoncés, QCM, interprétations, commentaires, référentiel EDN).
- [x] Compilation des **75 tracés** depuis le PDF (rendu 200 DPI, second tracé géré).
- [x] Consolidation → `data/cases.json` (75/75 avec tracé **et** interprétation).
- [x] **Grader GPT‑4o** autonome : réponse libre → score /100 + éléments trouvés/manqués/erronés + commentaire.
- [x] **API Flask** + **frontend** moderne (sélecteur, filtres par famille, visualiseur de tracé, correction animée).
- [x] Paquet **déployable Scalingo** (Procfile, runtime, requirements) — sans base de données.

**Répartition des familles** (75 cas) :
`rythme 25 · conduction 21 · ischémie 12 · hypertrophie 4 · péricarde 3 ·
normal 2 · génétique 2 · embolie 2 · métabolique 2 · technique 1 · infiltratif 1`

---

## 🎯 Phase 1 — Mise en route & validation (À FAIRE en premier)

Objectif : ouvrir le workspace, lancer l'app, vérifier la correction sur quelques cas.

- [ ] `python -m venv .venv` + `pip install -r requirements.txt`.
- [ ] Renseigner `OPENAI_API_KEY` dans `.env`.
- [ ] `python run.py` → tester 3–4 cas (un normal, un STEMI, un BAV, une FA).
- [ ] **Relecture qualité** : vérifier que `interpretation_ref` est correcte pour chaque cas (l'extraction Word peut avoir des coquilles). Corriger directement dans `data/cases.json`.
- [ ] Générer une **correction de référence GPT pour les 75 cas** (batch) afin d'avoir un « corrigé‑type » figé + repérer les cas où l'IA dérape.

**Livrable** : app fonctionnelle en local, banque relue, corrigé‑type des 75 cas.

---

## 🧮 Phase 2 — Scoring robuste (ontologique)

Aujourd'hui le score est **100 % GPT**. On veut le fiabiliser/objectiver.

- [ ] Intégrer le **scoring ontologique** existant (`RAG ontologique/scoring_v3.py`) comme second avis : score = Σ score(concept)/N (enfant=1.0, parent 2/3 ou 1/3, excludes=0).
- [ ] Mode **hybride** : GPT pour l'extraction des concepts de la réponse libre + scoring ontologique pour la note → score reproductible, commentaire GPT.
- [ ] Réutiliser `candidate_report.py` (NER→RAG→Judge→scoring) et `pedagogical_feedback.py` (feedback EDN Item 231) si on rebranche l'ontologie.
- [ ] Points de vigilance connus : faux positifs « ECG normal » (revoir gold/règle), négation/hedging (garde‑fous déjà présents dans le pipeline).

**Décision à prendre** : GPT‑seul (simple, déjà là) **vs** hybride ontologique
(reproductible, plus lourd). Démarrer GPT‑seul en prod, brancher l'hybride ensuite.

---

## 🌐 Phase 3 — Déploiement & accès

- [ ] `git init` du dossier `ecg-online/` (dépôt dédié) + premier commit.
- [ ] Créer l'app Scalingo, `env-set OPENAI_API_KEY`, `git push scalingo main`.
- [ ] Nom de domaine / accès étudiants.
- [ ] **Option API CHU** : remplacer l'endpoint OpenAI par l'API interne du CHU
      (même contrat `grade()`), garder GPT‑4o en repli. Abstraire le client dans `grader.py`.

---

## 📈 Phase 4 — Pédagogie & suivi

- [ ] Comptes étudiants + historique des scores (nécessitera une petite BDD — Postgres Scalingo).
- [ ] Tableau de bord enseignant (progression, cas les plus ratés).
- [ ] Mode « examen » (temps limité, tirage aléatoire par famille).
- [ ] Export des réponses pour analyse.

---

## 🔍 Phase 5 — Enrichissement de la banque

- [ ] Ajouter de nouveaux ECG (le livre + le Word en contiennent d'autres).
- [ ] Combler les **angles morts** repérés à l'évaluation du pipeline (familles sous‑représentées : technique, infiltratif, métabolique).
- [ ] Vérifier/annoter finement chaque tracé (rang EDN A/B/C par concept).

---

## 🧩 Contrat de données `cases.json`

Chaque cas suit ce schéma (le grader et l'API en dépendent) :

```json
{
  "num": 3,
  "titre": "ECG normal",
  "famille": "normal",
  "patient": "Femme de 28 ans…",
  "contexte": "Bilan systématique…",
  "qcm": { "question": "…", "options": ["…"], "reponses": "A" },
  "interpretation_ref": "Rythme sinusal régulier à 70/min, axe normal…",
  "second_trace": "",
  "commentaires": "Piège classique : …",
  "referentiel": "EDN Item 231 — …",
  "images": ["cas_03.png"]
}
```

> ⚠️ Toute modification du schéma → adapter `app/cases_repo.py` (champs cachés) et
> `app/grader.py` (`_build_user_prompt`).

---

## 🛠️ Rappels techniques

- **Python 3.11** (voir `runtime.txt`).
- **Clé unique** : `OPENAI_API_KEY`. Modèle réglable via `ECG_GRADER_MODEL`.
- **Aucune dépendance** au pipeline d'évaluation (`goldenset_extraction`, `RAG ontologique`) pour faire tourner l'app : le dossier `ecg-online/` est **autonome**.
- Config prouvée à l'évaluation : NER `gpt-4o-2024-08-06` + juge `gpt-4o-mini` → F1 ≈ 0.935.
- Pas de base de données en Phase 0‑3 (banque = JSON versionné).

---

## 📌 Prochaine action immédiate

➡️ **Phase 1, étape 1** : ouvrir `ecg-online/` comme workspace, créer le venv,
installer, renseigner la clé, `python run.py`, et relire les interprétations de
référence des 75 cas.
