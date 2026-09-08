from __future__ import annotations

import os
import threading
import webbrowser

from app import app

HOST = os.getenv("TRADELATIN_HOST", "127.0.0.1")
PORT = int(os.getenv("TRADELATIN_PORT", "8002"))
URL = f"http://{HOST}:{PORT}/prices?lang=en"


def open_browser() -> None:
    if os.getenv("TRADELATIN_OPEN_BROWSER", "1").lower() not in {"0", "false", "no"}:
        webbrowser.open_new(URL)


def main() -> None:
    print(f"[SCREEN] contracts={os.getenv('TRADELATIN_CONTRACT_DIR', 'data/contracts')}", flush=True)
    print(f"[SCREEN] refresh_dir={os.getenv('TRADELATIN_REFRESH_DIR', 'data/refresh_requests')}", flush=True)
    threading.Timer(1.5, open_browser).start()
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
