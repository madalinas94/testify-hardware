"""Jurnalul de modificări: fiecare adăugare, modificare sau ștergere se notează automat.

Notarea o fac triggerele SQLite, deci nicio operație nu scapă (nici cele din import, care
se notează ca un singur rând). În jurnal se păstrează valorile vechi și noi, iar textul
afișat proprietarului se construiește la citire.
"""

import json
import sqlite3
from contextlib import contextmanager

from .db import set_setting

# Tabelul → (substantivul afișat, genul pentru acord: f/m/n, coloana care dă numele rândului)
TABLES = {
    "sales": ("Vânzarea", "f", "invoice_number"),
    "expenses": ("Cheltuiala", "f", "category"),
    "purchases": ("Recepția", "f", "doc_number"),
    "products": ("Produsul", "m", "name"),
    "clients": ("Clientul", "m", "name"),
    "suppliers": ("Furnizorul", "m", "name"),
    "employees": ("Angajatul", "m", "name"),
    "salary_history": ("Salariul", "n", "gross"),
    "absences": ("Absența", "f", "kind"),
    "goals": ("Obiectivul", "n", "month"),
    "categories": ("Categoria", "f", "name"),
    "month_locks": ("Închiderea lunii", "f", "month"),
}
VERBS = {
    "insert": {"f": "adăugată", "m": "adăugat", "n": "adăugat"},
    "update": {"f": "modificată", "m": "modificat", "n": "modificat"},
    "delete": {"f": "ștearsă", "m": "șters", "n": "șters"},
}
FIELD_LABELS = {
    "date": "data", "description": "descrierea", "amount": "suma", "quantity": "cantitatea",
    "unit_price": "prețul", "unit_cost": "costul", "paid": "plătit", "due_date": "scadența",
    "client_id": "clientul", "product_id": "produsul", "invoice_number": "factura", "category": "categoria",
    "supplier": "furnizorul", "vat_kind": "TVA", "name": "numele", "sale_price": "prețul de vânzare",
    "cost": "costul", "min_stock": "stocul minim", "active": "activ", "payment_terms": "termenul de plată",
    "hire_date": "data angajării", "end_date": "data plecării", "role": "funcția", "gross": "salariul brut",
    "effective_from": "de la", "doc_number": "documentul", "revenue": "vânzări", "profit": "profit",
    "days": "zile", "kind": "tipul", "discount": "reducerea", "code": "codul", "type": "tipul",
}
SETTING_LABELS = {
    "company_name": "numele firmei", "owner_name": "numele proprietarului", "tax_regime": "regimul de impozitare",
    "vat_payer": "plătitor de TVA", "payday": "ziua salariilor", "tax_loss_carried": "pierderea fiscală",
}
HIDDEN_FIELDS = {"id", "snapshot", "opening_date"}
PAUSE_KEY = "audit_paused"


def install_triggers(conn: sqlite3.Connection) -> None:
    """(Re)creează triggerele; se rulează la fiecare pornire, după migrări."""
    for table in TABLES:
        columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})")]
        old = "json_object(" + ", ".join(f"'{c}', OLD.{c}" for c in columns) + ")"
        new = "json_object(" + ", ".join(f"'{c}', NEW.{c}" for c in columns) + ")"
        key = "rowid"
        active = f"(SELECT value FROM settings WHERE key = '{PAUSE_KEY}') IS NOT '1'"
        statements = {
            "insert": (f"AFTER INSERT ON {table} WHEN {active}", f"NEW.{key}", "NULL", new),
            "update": (f"AFTER UPDATE ON {table} WHEN {active} AND {old} IS NOT {new}", f"NEW.{key}", old, new),
            "delete": (f"AFTER DELETE ON {table} WHEN {active}", f"OLD.{key}", old, "NULL"),
        }
        for action, (when, row_id, old_value, new_value) in statements.items():
            conn.execute(f"DROP TRIGGER IF EXISTS audit_{table}_{action}")
            conn.execute(
                f"CREATE TRIGGER audit_{table}_{action} {when} BEGIN "
                f"INSERT INTO audit_log(table_name, row_id, action, old, new) "
                f"VALUES ('{table}', {row_id}, '{action}', {old_value}, {new_value}); END")


def log_event(conn: sqlite3.Connection, text: str, kind: str = "event") -> None:
    """Un rând scris de aplicație (de exemplu un import sau o restaurare)."""
    conn.execute("INSERT INTO audit_log(table_name, action, new) VALUES (?, ?, ?)",
                 (kind, "event", json.dumps({"text": text}, ensure_ascii=False)))


@contextmanager
def paused(conn: sqlite3.Connection):
    """Operațiile în masă (import, date demo) nu umplu jurnalul cu mii de rânduri."""
    set_setting(conn, PAUSE_KEY, "1")
    try:
        yield
    finally:
        set_setting(conn, PAUSE_KEY, "0")


def show(value) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, float):
        return f"{value:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".").removesuffix(",00")
    return str(value)


def describe(row: sqlite3.Row) -> dict:
    old = json.loads(row["old"]) if row["old"] else None
    new = json.loads(row["new"]) if row["new"] else None
    entry = {"id": row["id"], "at": row["at"], "table": row["table_name"], "action": row["action"]}
    if row["action"] == "event":
        return {**entry, "text": new.get("text", ""), "details": []}
    noun, gender, name_col = TABLES.get(row["table_name"], ("Rândul", "n", "id"))
    record = new or old or {}
    name = record.get(name_col)
    if row["table_name"] == "salary_history":
        name = f"{show(record.get('gross'))} lei de la {record.get('effective_from')}"
    elif row["table_name"] == "sales" and record.get("description"):
        name = f"{record.get('invoice_number') or ''} {record['description']}".strip()
    text = f"{noun} {show(name)} {VERBS[row['action']][gender]}".replace("  ", " ")
    table = row["table_name"]
    if table == "month_locks":
        from .calc import month_label
        label = month_label(record.get("month", "2000-01"))
        text = f"Luna {label} a fost {'închisă' if row['action'] == 'insert' else 'redeschisă'}"
    elif table == "absences":
        from .calc import ABSENCE_KINDS
        text = f"{ABSENCE_KINDS.get(record.get('kind'), 'Absență')}: {record.get('days')} zile ({record.get('month')}) " \
               f"{VERBS[row['action']]['n']}"
    elif table == "goals":
        text = f"Obiectivul {'general' if record.get('month') == 'default' else 'pentru ' + str(record.get('month'))} " \
               f"{VERBS[row['action']]['n']}"
    details = []
    if row["action"] == "update":
        for key, value in new.items():
            if key not in HIDDEN_FIELDS and old.get(key) != value:
                details.append(f"{FIELD_LABELS.get(key, key)}: {show(old.get(key))} → {show(value)}")
    elif "amount" in record:
        details.append(f"suma: {show(record['amount'])} lei")
    elif row["table_name"] == "purchases":
        details.append(f"{record.get('quantity')} buc. × {show(record.get('unit_cost'))} lei")
    return {**entry, "text": text, "details": details}


def entries(conn: sqlite3.Connection, limit: int = 200, table: str | None = None) -> list[dict]:
    sql, params = "SELECT * FROM audit_log", []
    if table:
        sql += " WHERE table_name = ?"
        params.append(table)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    return [describe(row) for row in conn.execute(sql, params)]
