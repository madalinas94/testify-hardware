"""Închiderea de lună: după ce raportul a plecat la contabil, luna nu se mai poate modifica.

Blocarea o fac triggerele SQLite, deci se aplică oricum ar veni modificarea (formular, import,
API). O lună închisă se poate redeschide; ambele operații apar în jurnalul de modificări.
"""

import json
import sqlite3

LOCK_MESSAGE = "LUNA_INCHISA"
# Tabelul → expresia care dă data documentului.
LOCKED_TABLES = {"sales": "date", "expenses": "date", "purchases": "date", "salary_history": "effective_from"}


def install_triggers(conn: sqlite3.Connection) -> None:
    for table, column in LOCKED_TABLES.items():
        checks = {
            "insert": [f"NEW.{column}"],
            "update": [f"OLD.{column}", f"NEW.{column}"],
            "delete": [f"OLD.{column}"],
        }
        for action, values in checks.items():
            condition = " OR ".join(
                f"substr({value}, 1, 7) IN (SELECT month FROM month_locks)" for value in values)
            conn.execute(f"DROP TRIGGER IF EXISTS lock_{table}_{action}")
            conn.execute(
                f"CREATE TRIGGER lock_{table}_{action} BEFORE {action.upper()} ON {table} "
                f"WHEN {condition} BEGIN SELECT RAISE(ABORT, '{LOCK_MESSAGE}'); END")


def is_lock_error(error: Exception) -> bool:
    return isinstance(error, sqlite3.DatabaseError) and LOCK_MESSAGE in str(error)


def closed_months(conn: sqlite3.Connection) -> list[dict]:
    return [{"month": row["month"], "closed_at": row["closed_at"], "snapshot": json.loads(row["snapshot"])}
            for row in conn.execute("SELECT * FROM month_locks ORDER BY month DESC")]


def checklist(conn: sqlite3.Connection, ym: str) -> list[dict]:
    """Ce merită verificat înainte de închidere. Nimic nu blochează închiderea: e un ajutor."""
    from . import calc, inventory

    start, end = calc.month_bounds(ym)
    items = []
    count = conn.execute("SELECT COUNT(*) FROM sales WHERE date BETWEEN ? AND ?", (start, end)).fetchone()[0]
    items.append({"ok": count > 0, "text": f"{count} vânzări înregistrate în lună." if count
                  else "Nu există nicio vânzare în lună."})
    expenses = conn.execute("SELECT COUNT(*) FROM expenses WHERE date BETWEEN ? AND ?",
                            (start, end)).fetchone()[0]
    items.append({"ok": expenses > 0, "text": f"{expenses} cheltuieli înregistrate." if expenses
                  else "Nu există cheltuieli: lipsesc chiria, utilitățile?"})
    missing = []
    previous = calc.shift_month(ym, -1)
    p_start, p_end = calc.month_bounds(previous)
    for (category,) in conn.execute(
            "SELECT DISTINCT category FROM expenses WHERE date BETWEEN ? AND ? AND category IN "
            "('Chirie', 'Utilități', 'Internet și telefonie', 'Contabilitate')", (p_start, p_end)):
        if not conn.execute("SELECT 1 FROM expenses WHERE category = ? AND date BETWEEN ? AND ?",
                            (category, start, end)).fetchone():
            missing.append(category)
    if missing:
        items.append({"ok": False, "text": "Cheltuieli lunare care lipsesc față de luna trecută: "
                      + ", ".join(missing) + "."})
    negative = [p["name"] for p in inventory.products_overview(conn, end) if p["stock"] < 0]
    items.append({"ok": not negative, "text": "Stocurile sunt pozitive." if not negative
                  else f"Stoc negativ la: {', '.join(negative[:3])}."})
    unpaid = conn.execute("SELECT COUNT(*) FROM sales WHERE paid = 0 AND due_date <= ?", (end,)).fetchone()[0]
    items.append({"ok": unpaid == 0, "text": "Toate facturile scadente sunt încasate." if not unpaid
                  else f"{unpaid} facturi scadente sunt încă neîncasate (bifați-le dacă banii au intrat)."})
    payroll = calc.payroll(conn, ym)["lines"]
    items.append({"ok": bool(payroll), "text": f"Salarii calculate pentru {len(payroll)} angajați." if payroll
                  else "Nu există salarii în lună."})
    return items


def close_month(conn: sqlite3.Connection, ym: str) -> dict:
    from . import calc

    if ym >= calc.current_month():
        raise ValueError("Se pot închide doar lunile încheiate.")
    if conn.execute("SELECT 1 FROM month_locks WHERE month = ?", (ym,)).fetchone():
        raise ValueError("Luna este deja închisă.")
    summary = calc.month_summary(conn, ym)
    snapshot = {key: summary[key] for key in ("revenue", "gross_margin", "total_costs", "profit_before_tax",
                                              "profit", "owner_income")}
    snapshot["company_tax"] = summary["taxes"]["company_tax"]
    snapshot["vat_payable"] = summary["vat"]["payable"] if summary["vat"] else 0
    conn.execute("INSERT INTO month_locks(month, snapshot) VALUES (?, ?)", (ym, json.dumps(snapshot)))
    return snapshot


def reopen_month(conn: sqlite3.Connection, ym: str) -> None:
    if conn.execute("DELETE FROM month_locks WHERE month = ?", (ym,)).rowcount == 0:
        raise ValueError("Luna nu este închisă.")
