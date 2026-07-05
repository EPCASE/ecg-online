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
                                        │ grade(case, texte)
                                        ▼
                                 ┌──────────────┐
                                 │  app/grader  │  GPT‑4o (function calling)
                                 │   .py        │  ancré sur interpretation_ref
                                 └──────────────┘
```

- **`data/cases.json`** — la banque : 75 cas structurés (contexte, tracé, interprétation de référence, commentaires, référentiel EDN).
- **`app/grader.py`** — cœur IA : compare la réponse libre à la référence et renvoie un JSON structuré (score, éléments trouvés/manqués/erronés, commentaire).
- **`app/server.py`** — API REST + service des images + service du front.
- **`frontend/`** — interface (sélecteur de cas, visualiseur de tracé, zone de réponse, résultat animé).

La correction **ne divulgue jamais** la réponse de référence avant que l'étudiant
ait soumis la sienne (voir `cases_repo.public_case`).

---

## 📁 Structure du dépôt

```
ecg-online/
├── app/
│   ├── __init__.py
│   ├── grader.py          # correction GPT (score + commentaire)
│   ├── cases_repo.py      # accès banque de cas + expurgation réponse
│   └── server.py          # API Flask + front + images
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── data/
│   ├── cases.json         # 75 cas (contrat de données)
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
├── requirements.txt
├── runtime.txt            # python-3.11.9
├── .env.example
├── README.md
└── ROADMAP.md             # plan de route détaillé
```

---

## 🔌 API

| Méthode | Route | Description |
|--------|-------|-------------|
| `GET`  | `/api/health` | Statut + présence clé OpenAI + modèle |
| `GET`  | `/api/cases` | Index léger des 75 cas |
| `GET`  | `/api/families` | Familles + compteurs |
| `GET`  | `/api/case/<num>` | Énoncé public d'un cas (sans correction) |
| `GET`  | `/api/case/<num>/full` | Cas complet (enseignant/debug) |
| `POST` | `/api/grade` | `{num, answer}` → correction GPT |
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
git push scalingo main
```

Scalingo détecte automatiquement Python via `requirements.txt` + `runtime.txt`,
et lance le process `web` du `Procfile` (gunicorn). Aucune base de données
n'est requise : la banque de cas est un fichier JSON versionné.

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
