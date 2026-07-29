# -*- coding: utf-8 -*-
"""Recupere les vraies reponses etudiantes soumises sur les cas des parcours
'niveau 2' (regular-narrow-tachycardias + wide-qrs-sinus), les rejoue avec
le moteur neuro_grader actuel, et detecte les incoherences logiques :
- un concept et une exclusion mutuelle tous deux 'trouves'
- score affiche incoherent avec le detail des validants
- un validant a score nul affiche comme trouve (regression du fix a9c8902)
"""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

import gspread
from google.oauth2.service_account import Credentials

SECRETS_PATH = Path(r"C:\Users\Administrateur\ECG collector\.streamlit\secrets.toml")
with open(SECRETS_PATH, "rb") as f:
    secrets = tomllib.load(f)
creds = Credentials.from_service_account_info(
    secrets["google_sheets"],
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"],
)
client = gspread.authorize(creds)
sh = client.open_by_key(secrets["google_sheet_id"])

ws = sh.worksheet("reponses")
values = ws.get_all_values()
header = values[0]
idx = {h: i for i, h in enumerate(header)}
rows = values[1:]

NIVEAU2_CASES = {"37", "42", "43", "44", "40", "39", "8", "9", "13", "10", "14", "15"}

filtered = [r for r in rows if r[idx["cas"]] in NIVEAU2_CASES and r[idx["reponse"]].strip()]
print(f"Reponses niveau 2 trouvees : {len(filtered)} / {len(rows)}")

# Sauvegarde pour reutilisation (evite de re-interroger la sheet)
import json
out = [
    {
        "horodatage": r[idx["horodatage"]],
        "session": r[idx["session"]],
        "cas": r[idx["cas"]],
        "titre": r[idx["titre"]],
        "reponse": r[idx["reponse"]],
        "score": r[idx["score"]],
        "correspondance": r[idx["correspondance"]],
        "parcours": r[idx["parcours"]] if "parcours" in idx else "",
        "phase": r[idx["phase"]] if "phase" in idx else "",
    }
    for r in filtered
]
Path("_niveau2_reponses.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("Sauvegarde -> _niveau2_reponses.json")

from collections import Counter
print("Repartition par cas:", Counter(o["cas"] for o in out))
