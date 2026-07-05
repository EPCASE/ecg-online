# 🗺️ ROADMAP — ECG Lecture

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
