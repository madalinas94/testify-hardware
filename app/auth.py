"""Autentificare pentru un singur utilizator: parola proprietarului și sesiuni."""

import hashlib
import hmac
import secrets
import sqlite3
import time

from fastapi import Cookie, HTTPException

from .db import get_conn, get_settings, set_setting

COOKIE_NAME = "testify_session"
ITERATIONS = 240_000


def hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS)
    return digest.hex()


def is_setup_done(conn: sqlite3.Connection) -> bool:
    return "password_hash" in get_settings(conn)


def set_password(conn: sqlite3.Connection, password: str) -> None:
    salt = secrets.token_hex(16)
    set_setting(conn, "password_salt", salt)
    set_setting(conn, "password_hash", hash_password(password, salt))


def check_password(conn: sqlite3.Connection, password: str) -> bool:
    settings = get_settings(conn)
    if "password_hash" not in settings:
        return False
    expected = settings["password_hash"]
    return hmac.compare_digest(hash_password(password, settings["password_salt"]), expected)


class AttemptLimiter:
    """După 5 încercări greșite la rând, parola și codul de recuperare se blochează 5 minute."""

    def __init__(self, max_failures: int = 5, lock_seconds: int = 300):
        self.max_failures, self.lock_seconds = max_failures, lock_seconds
        self.failures, self.locked_until = 0, 0.0

    def check(self) -> None:
        remaining = self.locked_until - time.monotonic()
        if remaining > 0:
            raise HTTPException(status_code=429, detail=f"Prea multe încercări greșite. "
                                f"Încercați din nou peste {int(remaining // 60) + 1} minute.")

    def failed(self) -> None:
        self.failures += 1
        if self.failures >= self.max_failures:
            self.locked_until = time.monotonic() + self.lock_seconds
            self.failures = 0

    def reset(self) -> None:
        self.failures, self.locked_until = 0, 0.0


limiter = AttemptLimiter()

# Fără caractere ușor de confundat pe hârtie (0/O, 1/I/L).
RECOVERY_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def normalize_code(code: str) -> str:
    return "".join(ch for ch in code.upper() if ch.isalnum())


def set_recovery_code(conn: sqlite3.Connection) -> str:
    """Generează un cod de recuperare nou (16 caractere) și salvează doar amprenta lui."""
    raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(16))
    salt = secrets.token_hex(16)
    set_setting(conn, "recovery_salt", salt)
    set_setting(conn, "recovery_hash", hash_password(raw, salt))
    return "-".join(raw[i:i + 4] for i in range(0, 16, 4))


def has_recovery_code(conn: sqlite3.Connection) -> bool:
    return "recovery_hash" in get_settings(conn)


def check_recovery_code(conn: sqlite3.Connection, code: str) -> bool:
    settings = get_settings(conn)
    if "recovery_hash" not in settings:
        return False
    actual = hash_password(normalize_code(code), settings["recovery_salt"])
    return hmac.compare_digest(actual, settings["recovery_hash"])


def end_all_sessions(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM sessions")


def create_session(conn: sqlite3.Connection) -> str:
    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO sessions(token) VALUES (?)", (token,))
    return token


def idle_limit_minutes(conn: sqlite3.Connection) -> int:
    try:
        return max(int(get_settings(conn).get("idle_lock_minutes") or 0), 0)
    except ValueError:
        return 0


def is_valid_session(conn: sqlite3.Connection, token: str | None, touch: bool = True) -> bool:
    """Sesiune validă și folosită recent: după inactivitate (implicit 15 minute) aplicația se blochează."""
    if not token:
        return False
    row = conn.execute("SELECT (julianday('now') - julianday(COALESCE(last_seen, created_at))) * 1440 AS idle "
                       "FROM sessions WHERE token = ?", (token,)).fetchone()
    if row is None:
        return False
    limit = idle_limit_minutes(conn)
    if limit and row["idle"] > limit:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        return False
    if touch:
        conn.execute("UPDATE sessions SET last_seen = datetime('now') WHERE token = ?", (token,))
    return True


# ---------- PIN rapid (de exemplu pe telefon) ----------
# Un PIN e mai scurt decât parola, deci e mai strict păzit: după 3 încercări greșite se dezactivează
# până la următoarea intrare cu parola.
PIN_MAX_FAILURES = 3


def has_pin(conn: sqlite3.Connection) -> bool:
    settings = get_settings(conn)
    return bool(settings.get("pin_hash")) and settings.get("pin_locked") != "1"


def set_pin(conn: sqlite3.Connection, pin: str) -> None:
    salt = secrets.token_hex(16)
    set_setting(conn, "pin_salt", salt)
    set_setting(conn, "pin_hash", hash_password(pin, salt))
    set_setting(conn, "pin_failures", "0")
    set_setting(conn, "pin_locked", "0")


def clear_pin(conn: sqlite3.Connection) -> None:
    for key in ("pin_salt", "pin_hash", "pin_failures", "pin_locked"):
        conn.execute("DELETE FROM settings WHERE key = ?", (key,))


def check_pin(conn: sqlite3.Connection, pin: str) -> bool:
    settings = get_settings(conn)
    if not has_pin(conn):
        return False
    if hmac.compare_digest(hash_password(pin, settings["pin_salt"]), settings["pin_hash"]):
        set_setting(conn, "pin_failures", "0")
        return True
    failures = int(settings.get("pin_failures") or 0) + 1
    set_setting(conn, "pin_failures", str(failures))
    if failures >= PIN_MAX_FAILURES:
        set_setting(conn, "pin_locked", "1")
    return False


def unlock_pin(conn: sqlite3.Connection) -> None:
    """După o intrare cu parola, PIN-ul blocat redevine activ."""
    if get_settings(conn).get("pin_hash"):
        set_setting(conn, "pin_failures", "0")
        set_setting(conn, "pin_locked", "0")


def require_login(testify_session: str | None = Cookie(default=None)) -> None:
    """Dependență FastAPI: oprește orice cerere fără sesiune validă."""
    with get_conn() as conn:
        if not is_valid_session(conn, testify_session):
            raise HTTPException(status_code=401, detail="Trebuie să vă autentificați.")
