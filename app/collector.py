"""
collector.py — Recueil optionnel des réponses étudiantes dans Google Sheets.
============================================================================
Adaptation Flask (sans Streamlit) du backend Google Sheets d'« ECG Collector ».

Objectif : archiver chaque réponse libre corrigée, pour analyse pédagogique.
Deux feuilles sont alimentées (créées automatiquement si absentes) :

  1. « reponses »  — journal à plat (le recueil principal, robuste) :
       horodatage | session | cas | titre | reponse | score | correspondance | backend
     → une LIGNE par soumission. Jamais de collision, source de vérité.

  2. « par_cas »   — accumulation par cas (la « feuille 3 » demandée) :
       cas | titre | réponse #1 | réponse #2 | …
     → une LIGNE par cas ; chaque nouvelle réponse est ajoutée dans la
       première colonne libre de la ligne du cas. Vue pratique « un cas =
       une ligne, une réponse par cellule ».

Robustesse (comme neuro_grader) :
  • Tout est OPTIONNEL. Sans credentials / sans gspread → `available()` = False,
    et `collect_answer()` est un no-op silencieux. L'app fonctionne normalement.
  • L'écriture se fait dans un THREAD DÉTACHÉ : la correction n'attend jamais
    Google Sheets (latence réseau invisible pour l'étudiant).
  • Un verrou sérialise les écritures dans le process (Procfile = 1 worker,
    plusieurs threads) → pas de collision sur « par_cas ».

Configuration (variables d'environnement) :
  • GOOGLE_SHEETS_CREDENTIALS       : JSON du Service Account (chaîne), OU
    GOOGLE_SHEETS_CREDENTIALS_FILE  : chemin vers le fichier JSON.
  • GOOGLE_SHEET_ID                 : ID de la Google Sheet (dans son URL).
  • ECG_COLLECT (défaut "1")        : "0"/"false" pour désactiver le recueil.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import List, Optional

# En-têtes des deux feuilles.
# Colonnes de métriques d'usage (note UX §13) ajoutées en fin de journal pour
# ne pas casser les feuilles existantes (append de colonnes, ordre stable).
LOG_COLS = ["horodatage", "session", "cas", "titre", "reponse",
            "score", "correspondance", "backend",
            "tentative", "refait", "t_reflexion_s", "t_total_s",
            "editions", "longueur", "mode"]
PARCAS_HEADER = ["cas", "titre", "réponses →"]

_LOCK = threading.Lock()          # sérialise les écritures dans le process
_ENSURED = False                  # feuilles vérifiées/créées une seule fois
_SS_CACHE = None                  # spreadsheet gspread mémorisé


# ─────────────────────────── Configuration ───────────────────────────
def _enabled() -> bool:
    return os.environ.get("ECG_COLLECT", "1").strip().lower() not in (
        "0", "false", "no", "off", "")


def _get_credentials() -> Optional[dict]:
    """JSON du Service Account, depuis une variable d'env (inline) ou un fichier."""
    raw = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    path = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE")
    if path and os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _get_sheet_id() -> Optional[str]:
    return os.environ.get("GOOGLE_SHEET_ID")


def _gspread_importable() -> bool:
    try:
        import gspread  # noqa: F401
        from google.oauth2.service_account import Credentials  # noqa: F401
        return True
    except Exception:
        return False


def is_available() -> bool:
    """Le recueil est-il utilisable (activé + clé + id + lib) ?"""
    return bool(
        _enabled()
        and _get_credentials()
        and _get_sheet_id()
        and _gspread_importable()
    )


def status() -> dict:
    """Diagnostic pour /api/health."""
    return {
        "enabled": _enabled(),
        "creds_set": bool(_get_credentials()),
        "sheet_id_set": bool(_get_sheet_id()),
        "gspread": _gspread_importable(),
        "available": is_available(),
    }


# ─────────────────────────── Connexion gspread ───────────────────────────
def _get_spreadsheet():
    """Ouvre (et mémorise) la Google Sheet. None si indisponible."""
    global _SS_CACHE
    if _SS_CACHE is not None:
        return _SS_CACHE
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except Exception:
        return None
    creds_dict = _get_credentials()
    sheet_id = _get_sheet_id()
    if not creds_dict or not sheet_id:
        return None
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    try:
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        _SS_CACHE = client.open_by_key(sheet_id)
        return _SS_CACHE
    except Exception as ex:
        print(f"[collector] Erreur ouverture Google Sheet: {type(ex).__name__}: {ex}")
        return None


def _ensure_worksheets(ss) -> None:
    """Crée « reponses » et « par_cas » (avec 1 ligne par cas) si absentes."""
    global _ENSURED
    if _ENSURED:
        return
    existing = [ws.title for ws in ss.worksheets()]

    if "reponses" not in existing:
        ws = ss.add_worksheet(title="reponses", rows=1000, cols=len(LOG_COLS))
        ws.append_row(LOG_COLS)

    if "par_cas" not in existing:
        ws = ss.add_worksheet(title="par_cas", rows=200, cols=30)
        ws.append_row(PARCAS_HEADER)
        # Une ligne par cas (num + titre réel, pour l'enseignant).
        try:
            from . import cases_repo
            rows = [[c.get("num"), c.get("titre", "")]
                    for c in sorted(cases_repo.all_cases(), key=lambda x: x.get("num", 0))]
            if rows:
                ws.append_rows(rows, value_input_option="RAW")  # type: ignore[arg-type]
        except Exception as ex:
            print(f"[collector] Init par_cas partielle: {type(ex).__name__}: {ex}")

    _ENSURED = True


# ─────────────────────────── Écriture ───────────────────────────
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write(num: int, titre: str, answer: str, score, correspondance: str,
           backend: str, session: str, meta: Optional[dict] = None) -> None:
    """Écrit dans les 2 feuilles. Exécuté dans un thread détaché (best-effort)."""
    ss = _get_spreadsheet()
    if not ss:
        return
    meta = meta or {}

    def _m(key, default=""):
        v = meta.get(key)
        return default if v is None else v

    with _LOCK:
        try:
            _ensure_worksheets(ss)

            # 1) Journal à plat « reponses » (append simple).
            ws_log = ss.worksheet("reponses")
            ws_log.append_row(
                [_now_iso(), session, num, titre, answer,
                 "" if score is None else score, correspondance, backend,
                 _m("tentative"), _m("refait"), _m("t_reflexion_s"),
                 _m("t_total_s"), _m("editions"), _m("longueur"),
                 _m("mode", "libre")],
                value_input_option="RAW",  # type: ignore[arg-type]
            )

            # 2) Accumulation « par_cas » : 1 cellule de plus sur la ligne du cas.
            ws_pc = ss.worksheet("par_cas")
            col_a = ws_pc.col_values(1)                 # ["cas", "1", "2", …]
            key = str(num)
            if key in col_a:
                row_idx = col_a.index(key) + 1          # 1-based
            else:
                ws_pc.append_row([num, titre], value_input_option="RAW")  # type: ignore[arg-type]
                row_idx = len(col_a) + 1
            row_vals = ws_pc.row_values(row_idx)        # trailing vides supprimés
            next_col = len(row_vals) + 1                # 1re colonne libre
            ws_pc.update_cell(row_idx, next_col, answer)
        except Exception as ex:
            print(f"[collector] Écriture échouée: {type(ex).__name__}: {ex}")


def collect_answer(num: int, titre: str, answer: str, score=None,
                   correspondance: str = "", backend: str = "",
                   session: str = "", meta: Optional[dict] = None) -> None:
    """Point d'entrée : archive une réponse (no-op si non configuré).

    Non bloquant : lance un thread détaché. N'échoue jamais côté appelant.
    `meta` (optionnel) : métriques d'usage (§13) — tentative, temps, éditions…
    """
    if not is_available():
        return
    if not (answer or "").strip():
        return
    try:
        threading.Thread(
            target=_write,
            args=(num, titre, answer, score, correspondance, backend, session, meta),
            daemon=True,
        ).start()
    except Exception:
        pass  # ne jamais casser la correction pour un problème de recueil
