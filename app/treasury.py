"""Trezoreria: câți bani vor fi în cont în următoarele 30 de zile.

Prognoza pornește de la soldul introdus de proprietar (bancă + casă) și adaugă, zi de zi:
+ încasările de la clienți, la scadența facturilor;
+ vânzările plătite pe loc, după media zilnică a ultimelor 90 de zile;
- plățile către furnizorii de marfă, la scadență (restanțele, imediat);
- cheltuielile obișnuite, după media lunară a ultimelor 3 luni încheiate;
- salariile nete, taxele pe salarii, TVA și impozitul pe profit, la termen (calendarul fiscal).
Totul cu TVA, pentru că asta se mișcă efectiv în cont.
"""

import sqlite3
from datetime import date, timedelta

from . import calc, obligations
from .db import get_settings
from .fiscal import settings_for_month

DAYS = 30


def vat_factor(conn: sqlite3.Connection, ym: str) -> float:
    settings = settings_for_month(conn, ym)
    return 1 + (calc.rate(settings, "vat_standard_rate") if settings.get("vat_payer", "1") == "1" else 0)


def forecast(conn: sqlite3.Connection, today: date | None = None, include_overdue: bool = False) -> dict:
    today = today or date.today()
    end = today + timedelta(days=DAYS)
    settings = get_settings(conn)
    balance_set = settings.get("cash_balance", "") != ""
    start_balance = float(settings.get("cash_balance") or 0)
    balance_date = settings.get("cash_balance_date") or None
    factor = vat_factor(conn, today.strftime("%Y-%m"))
    events: list[dict] = []

    def add(day: date, amount: float, label: str, kind: str):
        if amount:
            events.append({"date": max(day, today).isoformat(), "amount": calc.r2(amount), "label": label,
                           "kind": kind})

    receivables = calc.receivables(conn, today.isoformat())
    overdue_in = 0.0
    for invoice in receivables["invoices"]:
        due = date.fromisoformat(invoice["due_date"]) if invoice["due_date"] else today
        if due < today:
            overdue_in += invoice["amount"]
            if include_overdue:
                add(today + timedelta(days=7), invoice["amount"],
                    f"Încasare restantă {invoice['invoice_number'] or ''} ({invoice['client_name']})", "in")
        elif due <= end:
            add(due, invoice["amount"], f"Încasare {invoice['invoice_number'] or ''} ({invoice['client_name']})", "in")

    for document in calc.payables(conn, today.isoformat())["documents"]:
        due = date.fromisoformat(document["due_date"]) if document["due_date"] else today
        if due <= end:
            label = "Restanță" if due < today else "Plată"
            add(due, -document["amount"], f"{label} furnizor {document['supplier']} ({document['doc_number']})", "out")

    # Vânzări cu plata pe loc (fără termen): media zilnică din ultimele 90 de zile.
    since = (today - timedelta(days=90)).isoformat()
    cash_sales = conn.execute(
        "SELECT COALESCE(SUM(amount), 0), MIN(date) FROM sales WHERE date > ? AND date <= ? "
        "AND (due_date IS NULL OR due_date <= date)", (since, today.isoformat())).fetchone()
    last_data = conn.execute("SELECT MAX(date) FROM sales").fetchone()[0]
    if not cash_sales[0] and last_data:  # date mai vechi: media celor 90 de zile dinaintea ultimei vânzări
        since = (date.fromisoformat(last_data) - timedelta(days=90)).isoformat()
        cash_sales = conn.execute(
            "SELECT COALESCE(SUM(amount), 0), MIN(date) FROM sales WHERE date > ? AND date <= ? "
            "AND (due_date IS NULL OR due_date <= date)", (since, last_data)).fetchone()
    daily_cash_sales = cash_sales[0] * factor / 90

    # Cheltuieli obișnuite: media ultimelor 3 luni încheiate care au cheltuieli.
    months = []
    probe = calc.shift_month(today.strftime("%Y-%m"), -1)
    for _ in range(12):
        start_m, end_m = calc.month_bounds(probe)
        total = conn.execute(
            "SELECT COALESCE(SUM(amount * (1 + CASE vat_kind WHEN 'none' THEN 0 WHEN 'reduced' THEN ? ELSE ? END)), 0) "
            "FROM expenses WHERE date BETWEEN ? AND ?",
            (calc.rate(settings_for_month(conn, probe), "vat_reduced_rate") if factor > 1 else 0,
             factor - 1, start_m, end_m)).fetchone()[0]
        if total:
            months.append(total)
        if len(months) == 3:
            break
        probe = calc.shift_month(probe, -1)
    monthly_expenses = sum(months) / len(months) if months else 0
    daily_expenses = monthly_expenses / 30

    for item in obligations.calendar_items(conn, today):
        day = date.fromisoformat(item["date"])
        if item["paid"] or not item["amount"] or item["amount"] < 0 or not today <= day <= end:
            continue
        add(day, -item["amount"], f"{item['form']}: {item['title']}", "tax" if item["kind"] == "anaf" else "salary")

    days = []
    balance = start_balance
    lowest = {"date": today.isoformat(), "balance": balance}
    for offset in range(DAYS + 1):
        day = (today + timedelta(days=offset)).isoformat()
        todays = [e for e in events if e["date"] == day]
        inflow = sum(e["amount"] for e in todays if e["amount"] > 0) + (daily_cash_sales if offset else 0)
        outflow = -sum(e["amount"] for e in todays if e["amount"] < 0) + (daily_expenses if offset else 0)
        balance += inflow - outflow
        days.append({"date": day, "in": calc.r2(inflow), "out": calc.r2(outflow), "balance": calc.r2(balance)})
        if balance < lowest["balance"]:
            lowest = {"date": day, "balance": calc.r2(balance)}

    events.sort(key=lambda e: (e["date"], e["amount"]))
    total_in = sum(d["in"] for d in days)
    total_out = sum(d["out"] for d in days)
    return {
        "balance_set": balance_set, "start_balance": calc.r2(start_balance), "balance_date": balance_date,
        "balance_stale": bool(balance_date and (today - date.fromisoformat(balance_date)).days > 7),
        "days": days, "events": events, "lowest": lowest, "end_balance": days[-1]["balance"],
        "total_in": calc.r2(total_in), "total_out": calc.r2(total_out),
        "daily_cash_sales": calc.r2(daily_cash_sales), "monthly_expenses": calc.r2(monthly_expenses),
        "overdue_receivables": calc.r2(overdue_in), "include_overdue": include_overdue,
        "goes_negative": lowest["balance"] < 0,
    }
