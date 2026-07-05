"""
run.py — Point d'entrée local de l'ECG Lecture.
Charge le .env puis lance le serveur Flask sur http://localhost:5000

    python run.py

En production (Scalingo), c'est le Procfile/gunicorn qui prend le relais.
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app.server import create_app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app = create_app()
    print(f"\n  ECG Lecture ▶  http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=True)
