# ECG Lecture — Entraînement à l'interprétation ECG avec correction IA

Application web **autonome** d'entraînement à la lecture d'ECG.
L'étudiant observe un tracé, rédige son interprétation **en texte libre**, et une
IA (GPT‑4o) la corrige : **score /100 + commentaire pédagogique**, en la comparant
à l'interprétation de référence rédigée par l'enseignant.

Banque de **75 cas** ECG extraits de l'ouvrage de référence (tracés + énoncés +
interprétations attendues).

---

## 🚀 Démarrage rapide (local)

```powershell
# 1. Se placer dans le dossier
cd "ECG lecture\ecg-online"

# 2. Créer un environnement Python 3.11
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer la clé OpenAI
Copy-Item .env.example .env
#   puis éditer .env et renseigner OPENAI_API_KEY=sk-...

# 5. Lancer
python run.py
```

➡️ Ouvrir **http://localhost:5000**

> Sous macOS / Linux : `source .venv/bin/activate` puis `cp .env.example .env`.

---

## 🧠 Comment ça marche

```
┌──────────┐   énoncé + tracé    ┌──────────────┐
│ Frontend │ ──────────────────► │  Flask API   │
│ (HTML/JS)│ ◄────────────────── │ app/server.py│
└──────────┘   score + comment   └──────┬───────┘
                                        │ /api/grade
                          ┌─────────────┴──────────────┐
                          ▼ (défaut)                    ▼ (repli)
                 ┌──────────────────┐          ┌──────────────┐
                 │ app/neuro_grader │          │  app/grader  │
                 │  Pipeline RAG    │          │   GPT‑4o     │
                 │  neurosymbolique │          │  (autonome)  │
                 │  (scoring V3)    │          └──────────────┘
                 └────────┬─────────┘
                          ▼
                 rag_pipeline/ (vendoré)
                 NER → recherche hybride → juge → scoring V3 → feedback
```

Deux moteurs de correction, sélectionnables par la variable d'environnement
**`ECG_GRADER_BACKEND`** (`neuro` par défaut, `gpt` pour l'ancien) :

| Backend | Module | Correction | Note |
|---------|--------|------------|------|
| **`neuro`** ⭐ | `app/neuro_grader.py` + `rag_pipeline/` | Pipeline **neurosymbolique** (6 briques) : extraction NER (GPT‑4o), recherche hybride (embeddings + BM25), juge, **scoring V3 ontologique déterministe** | Score **reproductible**, ancré sur l'ontologie |
| **`gpt`** | `app/grader.py` | GPT‑4o direct, ancré sur `interpretation_ref` | 100 % autonome, 1 clé |

> **Repli automatique** : si le pipeline neuro est indisponible (cas non mappé à
> l'ontologie, dépendance/index absent, erreur), l'API bascule **sans erreur** sur
> le grader GPT‑4o. Le champ `backend` de la réponse indique lequel a répondu.

- **`data/cases.json`** — la banque : 75 cas structurés (contexte, tracé, interprétation de référence, commentaires, référentiel EDN).
- **`app/neuro_grader.py`** — adaptateur : construit le contrat *golden* du cas
  (`golden_config.golden_for_scorer`), exécute le pipeline vendoré, et traduit le
  `CandidateReport` (scoring V3) au format attendu par le frontend.
- **`rag_pipeline/`** — le pipeline **vendoré** (modules + index RAG pré‑calculé
  `rag_index/` + `data/ontology_v2.json`) : l'app reste **autonome** et déployable.
- **`app/grader.py`** — moteur de repli : GPT‑4o direct (function calling).
- **`app/server.py`** — API REST + service des images + service du front.
- **`frontend/`** — interface (sélecteur de cas, visualiseur de tracé, zone de réponse, résultat animé).


La correction **ne divulgue jamais** la réponse de référence avant que l'étudiant
ait soumis la sienne (voir `cases_repo.public_case`).

---

## 🎯 Curation du barème — *validant* vs *complémentaire*

Par défaut, l'IA comparait la réponse à **tous** les critères de la référence,
ce qui rendait la note **trop sévère**. On distingue désormais, pour chaque cas,
deux types de concepts de correction :

| Rôle | Effet sur la note | Usage typique |
|------|-------------------|---------------|
| **Validant** ⭐ | **Compte dans la note** | 1 à 2 par cas : diagnostic principal + anomalie-clé |
| **Complémentaire** | **N'impacte pas la note** (descriptif) | critères secondaires, contexte, pièges |
| **Supprimé** 🗑 | **Totalement exclu** (ni noté, ni montré) | diagnostic attendu à retirer (restaurable) |

➡️ Interface enseignant : **http://localhost:5000/curation**

> 🔒 **Accès réservé.** Le lien n'est **pas** exposé dans l'interface étudiante :
> on y accède directement par l'URL `/curation`. En production, protégez la page
> avec un jeton (voir [Sécurité du barème](#-sécurité-du-barème-curation) plus bas) —
> l'accès se fait alors via `https://…/curation?key=VOTRE_SECRET`.

- Chaque cas liste ses `points_cles` (rang A/B/C) avec un interrupteur
  **Validant / Complémentaire**. On peut aussi **ajouter un concept validant** à la main.
- 🗑 **Supprimer un diagnostic attendu** : il est barré et totalement exclu de la
  correction (ni note, ni « à compléter » côté étudiant). **Restaurable** d'un clic.
- **Défaut intelligent** : rang **A** ⇒ validant, rang **B/C** ⇒ complémentaire.
  Ajustable, puis **Enregistrer** (`Ctrl+S`).
- Les choix sont persistés dans **`data/scoring_config.json`** (écriture atomique)
  et injectés dans le prompt de correction : **seuls les validants font la note** ;
  les complémentaires omis n'enlèvent aucun point (ils restent affichés comme
  « à compléter » à titre indicatif) ; les supprimés disparaissent entièrement.

```
data/scoring_config.json
{
  "cases": {
    "12": {
      "roles": { "<label exact du point_cle>": "validant" | "complementaire" },
      "extra_validants": [ "BAV complet", ... ],
      "removed": [ "<label de diagnostic attendu retiré>", ... ]
    }
  }
}
```

Modules : **`app/scoring_config.py`** (persistance + fusion avec la référence),
**`frontend/curation.{html,css,js}`** (éditeur).

---

## �️ Anonymisation des cas (intégrité de l'examen)

Le **titre** d'un cas *est* son diagnostic (ex. « fibrillation atriale »).
Affiché tel quel dans la barre latérale, il vendrait la mèche. Par défaut
(**`ECG_ANONYMIZE=1`**), l'API publique remplace le titre par **« Cas 1 »,
« Cas 2 »…** et **masque la famille** (ex. « ischémie » trahirait aussi le cas).

- Le **vrai titre ne quitte jamais le serveur** avant correction : il sert au
  scoring et n'est **révélé qu'après** soumission (bloc `reference.titre`).
- La route enseignant **`/api/case/<num>/full`** conserve les vraies données et
  reste fermée tant qu’un `CURATION_TOKEN` non vide n’est pas configuré et fourni.
- Mettre **`ECG_ANONYMIZE=0`** pour réafficher les vrais titres (révision).

Implémenté dans `app/cases_repo.py` (`anon_titre`, `public_case`, `public_index`,
`families`).

---

## 📥 Recueil des réponses (Google Sheets, optionnel)

Chaque réponse libre corrigée peut être archivée dans une **Google Sheet**, pour
analyse pédagogique. **Entièrement optionnel** : sans identifiants, le module est
un *no‑op* silencieux et l'app fonctionne normalement.

Deux feuilles sont alimentées (créées automatiquement) :

| Feuille | Contenu | Forme |
|---------|---------|-------|
| **`reponses`** | Journal à plat, source de vérité | 1 **ligne** par soumission : `horodatage, session, cas, titre, reponse, score, correspondance, backend` |
| **`par_cas`** | Accumulation par cas (« un cas = une ligne ») | 1 **ligne** par cas, chaque réponse dans la **cellule** libre suivante |

- **Non bloquant** : l'écriture part dans un **thread détaché** (latence réseau
  invisible pour l'étudiant), sérialisée par un verrou.
- **Configuration** (variables d'env, cf. `.env.example`) : `GOOGLE_SHEET_ID`,
  `GOOGLE_SHEETS_CREDENTIALS` (JSON du compte de service *inline*) ou
  `GOOGLE_SHEETS_CREDENTIALS_FILE`. Interrupteur : `ECG_COLLECT` (défaut `1`).
- **Mise en place** du compte de service Google : voir
  `ECG collector/SETUP_GOOGLE_SHEETS.md` (projet Google Cloud → activer les API
  Sheets + Drive → clé JSON → **partager la feuille** avec l'e‑mail `client_email`).

> 💡 On peut réutiliser la **même** Google Sheet qu'ECG Collector : les onglets
> (`reponses` / `par_cas`) sont distincts de ses onglets (`sessions` / `responses`),
> donc **aucune collision**.

Implémenté dans `app/collector.py` (branché sur `/api/grade`, statut dans `/api/health`).

---

## 🔒 Sécurité du barème (curation)

La page de réglage du barème est **réservée à l'enseignant** : son lien n'apparaît
**pas** dans l'interface étudiante. Pour empêcher un accès direct par URL, on la
protège par un **jeton** via **`CURATION_TOKEN`** :

| `CURATION_TOKEN` | `/curation` et écritures du barème |
|------------------|-------------------------------------|
| **vide** (défaut) | **ouvert** — pratique en local |
| **défini** (prod) | **protégé** — jeton requis, sinon **403** |

- Accès enseignant : **`https://…/curation?key=VOTRE_SECRET`** (la clé est ensuite
  jointe automatiquement en en‑tête `X-Curation-Token` par `curation.js`).
- Sont protégés : la page `/curation`, les lectures `GET /api/curation[...]`
  (qui exposent les **vrais titres**) et les écritures `POST /api/curation/...`.
- La page **étudiante** (`/`, `/api/grade`, `/api/case/...`) reste **ouverte**.

---

## �📁 Structure du dépôt

```
ecg-online/
├── app/
│   ├── __init__.py
│   ├── grader.py          # correction GPT‑4o directe (backend de repli)
│   ├── neuro_grader.py    # ⭐ adaptateur pipeline neurosymbolique (backend défaut)
│   ├── cases_repo.py      # accès banque de cas + expurgation + anonymisation
│   ├── scoring_config.py  # curation validant/complémentaire (barème)
│   ├── golden_config.py   # pont sémantique : label → concept ontologique
│   ├── collector.py       # recueil optionnel des réponses (Google Sheets)
│   └── server.py          # API Flask + front + images
├── rag_pipeline/          # ⭐ pipeline neurosymbolique VENDORÉ (autonome)
│   ├── candidate_report.py# orchestrateur (briques 2→6)
│   ├── ner_extractor.py   # NER GPT‑4o
│   ├── hybrid_search.py   # recherche hybride (embeddings + BM25)
│   ├── neurosymbolic_judge.py
│   ├── scoring_v3.py      # scoring ontologique déterministe
│   ├── semantic_layer.py  # expansion sémantique
│   ├── pattern_inference.py
│   ├── pedagogical_feedback.py + edn_knowledge_base.py
│   ├── ontology_index.py
│   ├── rag_index/         # index pré‑calculé (npy + metadata + BM25)
│   └── data/ontology_v2.json
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   ├── curation.html      # éditeur du barème (enseignant)
│   ├── curation.css
│   └── curation.js
├── data/
│   ├── cases.json         # 75 cas (contrat de données)
│   ├── cases_reference.json # corrigés-types + points_cles + fiche_secours
│   ├── cases_golden.json  # mapping label → concept ontologique (curation)
│   ├── scoring_config.json# rôles validant/complémentaire (généré)
│   ├── cases_bank_raw.json# extraction brute (docx)
│   ├── pdf_case_map.json  # mapping cas → pages PDF / images
│   └── ecg_images/        # 108 tracés PNG
├── scripts/               # outils d'extraction (docx / pdf → cases.json)
│   ├── extract_cases.py
│   ├── compile_ecg_pdf.py
│   ├── build_cases_json.py
│   └── build_ecg_gallery.py
├── run.py                 # entrée locale
├── Procfile               # entrée Scalingo (gunicorn)
├── requirements.txt       # flask, openai, numpy, rank-bm25, pydantic…
├── runtime.txt            # python-3.11.9
├── .env.example
├── README.md
└── ROADMAP.md             # plan de route détaillé
```

---

## 🔌 API

| Méthode | Route | Description |
|--------|-------|-------------|
| `GET`  | `/api/health` | Statut + clé OpenAI + modèle + **backend** (`neuro`/`gpt`), recueil et anonymisation |
| `GET`  | `/api/cases` | Index léger des 75 cas (**anonymisé** si `ECG_ANONYMIZE=1`) |
| `GET`  | `/api/families` | Familles + compteurs (**vide** si anonymisé) |
| `GET`  | `/api/case/<num>` | Énoncé public d'un cas (sans correction, **anonymisé**) |
| `GET`  | `/api/case/<num>/full` | Cas complet, **vrais titres** (enseignant/debug) |
| `GET`  | `/api/case/<num>/qcm` | QCM public d'un cas (question + options, **sans solution**) |
| `POST` | `/api/case/<num>/qcm` | `{selected:[...]}` → correction du QCM (score + par-option) |
| `POST` | `/api/grade` | `{num, answer}` → correction (+ recueil optionnel) |
| `GET`  | `/curation` | **Interface de curation** (enseignant, 🔒 `CURATION_TOKEN`) |
| `GET`  | `/api/curation` | Vue d'ensemble des 75 cas (🔒) |
| `GET`  | `/api/curation/<num>` | Concepts d'un cas + rôles (🔒) |
| `POST` | `/api/curation/<num>` | Enregistre les rôles choisis (🔒) |
| `POST` | `/api/curation/<num>/reset` | Réinitialise un cas (🔒) |
| `GET`  | `/images/<file>` | Tracé ECG (PNG) |

Exemple :

```bash
curl -X POST http://localhost:5000/api/grade \
  -H "Content-Type: application/json" \
  -d '{"num": 3, "answer": "Rythme sinusal régulier 70/min, axe normal, ECG normal"}'
```

---

## ☁️ Déploiement Scalingo

```bash
# Depuis le dossier ecg-online (dépôt git initialisé)
scalingo create ecg-lecture
scalingo --app ecg-lecture env-set OPENAI_API_KEY=sk-...
# (optionnel) forcer le moteur : neuro (défaut) ou gpt
scalingo --app ecg-lecture env-set ECG_GRADER_BACKEND=neuro
git push scalingo main
```

Scalingo détecte automatiquement Python via `requirements.txt` + `runtime.txt`,
et lance le process `web` du `Procfile` (gunicorn, **1 worker + 4 threads** : le
worker charge l'index RAG en RAM une seule fois). Aucune base de données n'est
requise : la banque de cas **et le pipeline vendoré** (`rag_pipeline/`, index
inclus) sont versionnés dans le dépôt.

> ⚠️ **Vérifier que `rag_pipeline/rag_index/*.npy` est bien commité** (≈ 4,5 Mo) :
> c'est l'index pré‑calculé, indispensable au backend `neuro`. Il n'est pas dans
> `.gitignore`.

### Variables d'environnement

| Variable | Défaut | Rôle |
|----------|--------|------|
| `OPENAI_API_KEY` | — | **Requis** (NER + embeddings + juge + feedback) |
| `ECG_GRADER_BACKEND` | `neuro` | `neuro` (pipeline V3) ou `gpt` (GPT‑4o direct) |
| `ECG_GRADER_MODEL` | `gpt-4o-2024-08-06` | Modèle du backend `gpt` |
| `ECG_ANONYMIZE` | `1` | Cas anonymisés (« Cas N », familles masquées). `0` = vrais titres |
| `CURATION_TOKEN` | *(vide)* | 🔒 Protège `/curation`. Accès via `?key=…`. **Recommandé en prod** |
| `ECG_COLLECT` | `1` | Active le recueil des réponses (si identifiants Google fournis) |
| `GOOGLE_SHEET_ID` | — | ID de la Google Sheet du recueil (optionnel) |
| `GOOGLE_SHEETS_CREDENTIALS` | — | JSON du compte de service *inline* (optionnel) |
| `PORT` | `5000` | Port d'écoute (fourni par Scalingo) |


---

## 🔧 Régénérer la banque de cas

Les scripts d'extraction transforment les sources (Word + PDF) en `cases.json` :

```powershell
python scripts/extract_cases.py       # docx  → cases_bank_raw.json (+ images)
python scripts/compile_ecg_pdf.py     # pdf   → tracés PNG + pdf_case_map.json
python scripts/build_cases_json.py    # fusion → data/cases.json
python scripts/build_ecg_gallery.py   # (option) galerie HTML statique
```

> Les chemins sources (docx/pdf) sont en tête de chaque script.

---

## 📜 Licence & données

Cas cliniques et tracés issus d'un ouvrage pédagogique — **usage
d'enseignement**. Ne pas rediffuser les tracés hors de ce cadre.

Voir `ROADMAP.md` pour le plan de route complet du projet.
