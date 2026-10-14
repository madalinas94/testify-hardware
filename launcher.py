"""Pornirea aplicației ca program Windows (TestifyHardware.exe), fără Python instalat.

Datele stau în folderul „TestifyData”, lângă .exe: baza de date și copiile de siguranță.
Dublu-click pe .exe pornește aplicația și deschide browserul. Dacă aplicația rulează deja,
doar deschide browserul. Fereastra neagră trebuie lăsată deschisă cât timp lucrați.
"""

import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

PORT = int(os.environ.get("TESTIFY_PORT", "8000"))


def data_folder() -> Path:
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    folder = base / "TestifyData"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def already_running(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/auth/status", timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


def open_browser(url: str) -> None:
    if os.environ.get("TESTIFY_NO_BROWSER") != "1":
        webbrowser.open(url)


def main() -> None:
    os.environ.setdefault("TESTIFY_DB", str(data_folder() / "testify.db"))
    url = f"http://localhost:{PORT}/"
    if already_running(PORT):
        print("Aplicația rulează deja. Deschid browserul…")
        open_browser(url)
        return
    if not port_free(PORT):
        print(f"Portul {PORT} este folosit de alt program. Închideți-l sau setați TESTIFY_PORT.")
        input("Apăsați Enter pentru a închide…")
        return

    import uvicorn

    from app.main import app

    def open_when_ready():
        for _ in range(60):
            if already_running(PORT):
                open_browser(url)
                return
            time.sleep(0.5)

    threading.Thread(target=open_when_ready, daemon=True).start()
    print("=" * 60)
    print("  Testify Hardware rulează.")
    print(f"  Deschideți în browser: {url}")
    print(f"  Datele sunt în: {data_folder()}")
    print("  Lăsați această fereastră deschisă. Pentru oprire, închideți-o.")
    print("=" * 60)
    # 0.0.0.0: aplicația se poate deschide și de pe telefon, din aceeași rețea Wi-Fi.
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
