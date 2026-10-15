"""Copii de siguranță: automat în fiecare zi, restaurare și export complet.

Copiile stau în folderul data/backups, lângă baza de date. Se păstrează ultimele 30.
Pentru siguranță în caz că se strică discul, exportul complet (ZIP) se poate salva pe un stick
sau în cloud; din el se poate restaura totul.
"""

import io
import re
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook

from .db import connect, db_path

KEEP = 30
NAME_RE = re.compile(r"^testify-[0-9T_-]+(-[a-z-]+)?\.db$")
REQUIRED_TABLES = {"settings", "sales", "expenses", "products"}
EXPORT_TABLES = ["sales", "expenses", "purchases", "products", "clients", "suppliers", "employees",
                 "salary_history", "absences", "categories", "goals", "month_locks", "fiscal_rules", "audit_log"]
SECRET_SETTINGS = ("anthropic_api_key",)


def backup_dir() -> Path:
    folder = db_path().parent / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def copy_database(target: Path) -> None:
    """Copie consistentă, chiar dacă aplicația scrie în acel moment (API-ul de backup SQLite)."""
    source = connect()
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()


def create_backup(label: str = "") -> dict:
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    name = f"testify-{stamp}{'-' + label if label else ''}.db"
    copy_database(backup_dir() / name)
    prune()
    mirror(backup_dir() / name)
    return describe(backup_dir() / name)


def extra_dir() -> Path | None:
    from .db import get_settings

    conn = connect()
    try:
        folder = get_settings(conn).get("backup_extra_dir", "").strip()
    finally:
        conn.close()
    return Path(folder) if folder else None


def check_extra_dir(folder: str) -> str:
    """Folderul suplimentar (de exemplu sincronizat cu Google Drive / OneDrive) trebuie să existe."""
    folder = folder.strip()
    if not folder:
        return ""
    path = Path(folder).expanduser()
    if not path.is_dir():
        raise ValueError("Folderul nu există. Creați-l întâi (de exemplu în Google Drive sau OneDrive).")
    probe = path / ".testify-test"
    try:
        probe.write_text("ok")
        probe.unlink()
    except OSError:
        raise ValueError("Aplicația nu poate scrie în acest folder.") from None
    return str(path)


def mirror(path: Path) -> None:
    """O copie și în folderul suplimentar; dacă nu merge (stick scos, cloud oprit), se notează și atât."""
    from .db import set_setting

    folder = extra_dir()
    if not folder:
        return
    status = "ok"
    try:
        target = folder / "TestifyBackups"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target / path.name)
        for old in sorted(target.glob("testify-*.db"), key=lambda p: p.name, reverse=True)[KEEP:]:
            old.unlink(missing_ok=True)
    except OSError as error:
        status = f"eroare: {error.strerror or error}"
    conn = connect()
    try:
        set_setting(conn, "backup_extra_status", f"{datetime.now():%Y-%m-%d %H:%M} {status}")
        conn.commit()
    finally:
        conn.close()


def daily_backup() -> dict | None:
    """Face copia zilei, dacă nu există deja. Rulează la pornire și apoi din oră în oră."""
    if not db_path().exists():
        return None
    today = date.today().isoformat()
    if any(path.name.startswith(f"testify-{today}") for path in backup_dir().glob("testify-*.db")):
        return None
    return create_backup()


def prune() -> None:
    backups = sorted(backup_dir().glob("testify-*.db"), key=lambda p: p.name, reverse=True)
    for old in backups[KEEP:]:
        old.unlink(missing_ok=True)


def describe(path: Path) -> dict:
    stat = path.stat()
    return {"name": path.name, "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")}


def list_backups() -> list[dict]:
    return [describe(p) for p in sorted(backup_dir().glob("testify-*.db"), key=lambda p: p.name, reverse=True)]


def backup_path(name: str) -> Path:
    if not NAME_RE.match(name):
        raise ValueError("Numele copiei nu este valid.")
    path = backup_dir() / name
    if not path.exists():
        raise ValueError("Copia nu mai există.")
    return path


def check_database(path: Path) -> None:
    """O bază de date restaurată trebuie să fie chiar o bază Testify, întreagă."""
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Copia este deteriorată.")
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        finally:
            conn.close()
    except sqlite3.DatabaseError:
        raise ValueError("Fișierul nu este o copie de siguranță Testify.") from None
    if not REQUIRED_TABLES <= tables:
        raise ValueError("Fișierul nu este o copie de siguranță Testify.")


def restore_from(path: Path) -> dict:
    """Înlocuiește datele actuale cu copia; înainte, salvează starea de acum (se poate reveni)."""
    check_database(path)
    safety = create_backup("inainte-de-restaurare")
    source = sqlite3.connect(path)
    destination = connect()
    try:
        source.backup(destination)
    finally:
        source.close()
        destination.close()
    return safety


def restore_upload(content: bytes, filename: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "upload.db"
        if filename.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as archive:
                    with archive.open("testify.db") as member, open(target, "wb") as out:
                        shutil.copyfileobj(member, out)
            except (zipfile.BadZipFile, KeyError):
                raise ValueError("Arhiva nu conține o copie Testify (testify.db).") from None
        else:
            target.write_bytes(content)
        return restore_from(target)


def full_export() -> bytes:
    """ZIP cu baza de date (pentru restaurare) și toate datele în Excel (pentru oameni)."""
    buffer = io.BytesIO()
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "testify.db"
        copy_database(copy)
        conn = sqlite3.connect(copy)
        conn.row_factory = sqlite3.Row
        for key in SECRET_SETTINGS:  # cheia AI nu pleacă din calculator
            conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        conn.commit()
        book = Workbook()
        book.remove(book.active)
        for table in EXPORT_TABLES:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            sheet = book.create_sheet(table[:31])
            columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
            sheet.append(columns)
            for row in rows:
                sheet.append([f"'{v}" if isinstance(v, str) and v[:1] in "=+-@" else v for v in row])
        conn.execute("VACUUM")
        conn.close()
        excel = io.BytesIO()
        book.save(excel)
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(copy, "testify.db")
            archive.writestr("toate-datele.xlsx", excel.getvalue())
            archive.writestr("CITESTE.txt", (
                "Export complet Testify Hardware, " + datetime.now().strftime("%d.%m.%Y %H:%M") + "\n\n"
                "testify.db        - baza de date; se restaurează din Setări → Copii de siguranță.\n"
                "toate-datele.xlsx - toate datele, câte o foaie pentru fiecare tabel.\n\n"
                "Păstrați arhiva într-un loc sigur (stick, cloud). Parola aplicației rămâne cea de acum.\n"
                "Cheia pentru asistentul AI nu este inclusă.\n").encode("utf-8"))
    return buffer.getvalue()
