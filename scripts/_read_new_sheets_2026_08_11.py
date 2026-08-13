#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_read_new_sheets_2026_08_11.py — Audit P4.2 : lire les onglets du Google
Sheet du collector (dont les 2 nouveaux gids fournis par l'expert) pour
mettre à jour l'inventaire du corpus."""
import re
import sys
import json

import gspread
from google.oauth2.service_account import Credentials

RAW = open(r"c:\Users\Administrateur\ECG collector\.streamlit\secrets.toml",
           encoding="utf-8").read()
SID = re.search(r'google_sheet_id\s*=\s*.([\w-]+).', RAW).group(1)

FIELDS = ["type", "project_id", "private_key_id", "private_key",
          "client_email", "client_id", "auth_uri", "token_uri",
          "auth_provider_x509_cert_url", "client_x509_cert_url"]


def get(k):
    # le bloc [google_sheets] est en style JSON : "key": "value"
    m = re.search(r'"' + k + r'"\s*:\s*"(.*?)"(?:,|\s*$)', RAW, re.M)
    return m.group(1) if m else None


creds_dict = {k: get(k) for k in FIELDS}
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=["https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"])
gc = gspread.authorize(creds)
ss = gc.open_by_key(SID)

if len(sys.argv) > 1 and sys.argv[1] == "--dump":
    # dump un onglet par gid → fichier JSON UTF-8 (sys.argv[3])
    gid = int(sys.argv[2])
    out_path = sys.argv[3]
    ws = next(w for w in ss.worksheets() if w.id == gid)
    rows = ws.get_all_values()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"title": ws.title, "n_rows": len(rows),
                   "header": rows[0] if rows else [],
                   "rows": rows[1:]}, f, ensure_ascii=False)
    print(f"OK {ws.title} -> {out_path} ({len(rows)} lignes)")
else:
    for ws in ss.worksheets():
        print(f"gid={ws.id} | {ws.title!r} | {ws.row_count}x{ws.col_count}")
