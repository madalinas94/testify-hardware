"""Calendarul fiscal: ce se plătește la ANAF, când și cât, plus impozitul pe profit trimestrial.

Termenele urmează regulile pentru o firmă plătitoare de TVA lunar, cu impozit pe profit:
- D112 (contribuții și impozit pe salarii) și D300 (TVA): pe 25 ale lunii următoare;
- D394 (declarația informativă de TVA): pe 30 ale lunii următoare;
- impozitul pe profit: trimestrial, pe 25 ale lunii de după trimestru; trimestrul IV se
  plătește odată cu declarația anuală D101, până pe 25 iunie anul următor.
Un termen care pică în weekend sau de sărbători se mută în prima zi lucrătoare.
"""

import json
import sqlite3
from datetime import date

from . import calc
from .db import get_settings, set_setting
from .fiscal import settings_for_month
from .ro_calendar import deadline

LOSS_LIMIT = 0.70  # pierderea fiscală se recuperează din cel mult 70% din profitul impozabil
PAID_KEY = "obligations_paid"


def year_pbt(conn: sqlite3.Connection, year: int, last_month: int = 12) -> float:
    return calc.r2(sum(calc.month_summary(conn, f"{year}-{m:02d}")["profit_before_tax"]
                       for m in range(1, last_month + 1)))


def loss_pool(conn: sqlite3.Connection, year: int) -> float:
    """Pierderea fiscală de recuperat la începutul anului dat.

    Pornește de la pierderea din anii dinaintea datelor din aplicație (introdusă în Setări)
    și adaugă pierderile, respectiv scade recuperările, an de an.
    """
    settings = get_settings(conn)
    pool = float(settings.get("tax_loss_carried") or 0)
    first = calc.first_data_month(conn)
    if not first:
        return pool
    for past in range(int(first[:4]), year):
        pbt = year_pbt(conn, past)
        if pbt < 0:
            pool += -pbt
        else:
            pool -= min(pool, LOSS_LIMIT * pbt)
    return calc.r2(pool)


def quarter_of(month: int) -> int:
    return (month - 1) // 3 + 1


def profit_tax_quarters(conn: sqlite3.Connection, year: int) -> dict:
    """Impozitul pe profit pe trimestre, calculat cumulat de la începutul anului."""
    pool = loss_pool(conn, year)
    rows = []
    cumulative_pbt = paid_so_far = 0.0
    for quarter in range(1, 5):
        months = [f"{year}-{m:02d}" for m in range(quarter * 3 - 2, quarter * 3 + 1)]
        # Lunile viitoare nu au încă vânzări: ar apărea ca pierdere falsă (doar salarii), deci nu se adună.
        pbt = calc.r2(sum(calc.month_summary(conn, m)["profit_before_tax"] for m in months
                          if m <= calc.current_month()))
        cumulative_pbt = calc.r2(cumulative_pbt + pbt)
        settings = settings_for_month(conn, months[-1])
        rate = calc.rate(settings, "profit_tax_rate")
        recovered = calc.r2(min(pool, LOSS_LIMIT * max(cumulative_pbt, 0)))
        taxable = max(0.0, cumulative_pbt - recovered)
        cumulative_tax = calc.rnd(taxable * rate)
        due = max(0.0, calc.r2(cumulative_tax - paid_so_far))
        paid_so_far = max(paid_so_far, cumulative_tax)
        rows.append({
            "quarter": quarter, "months": months, "profit_before_tax": pbt,
            "cumulative_pbt": cumulative_pbt, "loss_recovered": recovered,
            "taxable": calc.r2(taxable), "tax_due": due,
            "deadline": (deadline(year + 1, 6) if quarter == 4 else deadline(year, quarter * 3 + 1)).isoformat(),
            "estimate": months[-1] >= calc.current_month(),
        })
    return {"year": year, "loss_at_start": pool, "loss_limit_pct": LOSS_LIMIT * 100, "quarters": rows,
            "total": calc.r2(sum(r["tax_due"] for r in rows))}


def paid_ids(conn: sqlite3.Connection) -> set[str]:
    try:
        return set(json.loads(get_settings(conn).get(PAID_KEY) or "[]"))
    except ValueError:
        return set()


def set_paid(conn: sqlite3.Connection, item_id: str, paid: bool) -> None:
    ids = paid_ids(conn)
    ids = ids | {item_id} if paid else ids - {item_id}
    set_setting(conn, PAID_KEY, json.dumps(sorted(ids)))


def calendar_items(conn: sqlite3.Connection, today: date | None = None, back: int = 2, ahead: int = 3) -> list[dict]:
    today = today or date.today()
    settings = get_settings(conn)
    paid = paid_ids(conn)
    this_month = today.strftime("%Y-%m")
    items = []
    quarter_cache: dict[int, dict] = {}
    for offset in range(-back - 1, ahead):
        ym = calc.shift_month(this_month, offset)
        year, month = int(ym[:4]), int(ym[5:])
        summary = calc.month_summary(conn, ym)
        estimate = ym >= this_month
        label = calc.month_label(ym)
        pay = summary["payroll"]
        salary_taxes = calc.r2(pay["cas"] + pay["cass"] + pay["income_tax"] + pay["cam"])
        if pay["gross"]:
            payday = min(int(settings.get("payday") or 10), 28)
            items.append({"id": f"net-{ym}", "kind": "salary", "form": "Salarii",
                          "title": f"Plata salariilor nete pentru {label}", "amount": pay["net"],
                          "date": deadline(year, month + 1, payday).isoformat(), "estimate": estimate})
            items.append({"id": f"d112-{ym}", "kind": "anaf", "form": "D112",
                          "title": f"Contribuții și impozit pe salarii, {label}", "amount": salary_taxes,
                          "date": deadline(year, month + 1).isoformat(), "estimate": estimate,
                          "details": f"CAS {calc.fmt(pay['cas'])}, CASS {calc.fmt(pay['cass'])}, impozit "
                                     f"{calc.fmt(pay['income_tax'])}, CAM {calc.fmt(pay['cam'])}"})
        if summary["vat"]:
            vat = summary["vat"]["payable"]
            items.append({"id": f"d300-{ym}", "kind": "anaf", "form": "D300",
                          "title": f"TVA {'de plată' if vat >= 0 else 'de recuperat'}, {label}",
                          "amount": vat, "date": deadline(year, month + 1).isoformat(), "estimate": estimate})
            items.append({"id": f"d394-{ym}", "kind": "info", "form": "D394",
                          "title": f"Declarația informativă de TVA, {label} (fără plată)", "amount": None,
                          "date": deadline(year, month + 1, 30).isoformat(), "estimate": estimate})
        if month % 3 == 0:
            quarter = quarter_of(month)
            if settings.get("tax_regime") == "micro":
                months = [calc.shift_month(ym, -i) for i in range(3)]
                amount = calc.r2(sum(calc.month_summary(conn, m)["taxes"]["company_tax"] for m in months))
                items.append({"id": f"micro-{year}-T{quarter}", "kind": "anaf", "form": "D100",
                              "title": f"Impozit microîntreprindere, trimestrul {quarter} {year}",
                              "amount": amount, "date": deadline(year, month + 1).isoformat(), "estimate": estimate})
            else:
                quarters = quarter_cache.setdefault(year, profit_tax_quarters(conn, year))
                row = quarters["quarters"][quarter - 1]
                title = (f"Impozit pe profit, trimestrul IV {year} și declarația anuală D101" if quarter == 4
                         else f"Impozit pe profit, trimestrul {quarter} {year}")
                items.append({"id": f"profit-{year}-T{quarter}", "kind": "anaf",
                              "form": "D101" if quarter == 4 else "D100", "title": title,
                              "amount": row["tax_due"], "date": row["deadline"], "estimate": row["estimate"],
                              "details": (f"Pierdere recuperată: {calc.fmt(row['loss_recovered'])}"
                                          if row["loss_recovered"] else None)})
    result = []
    for item in items:
        day = date.fromisoformat(item["date"])
        days_left = (day - today).days
        if days_left < -62 or days_left > 100:
            continue
        done = item["id"] in paid
        # Termenele trecute se consideră rezolvate (aplicația nu vede extrasul de cont).
        status = ("paid" if done else "past" if days_left < 0 else "soon" if days_left <= 7 else "upcoming")
        result.append({**item, "days_left": days_left, "paid": done, "status": status})
    result.sort(key=lambda item: (item["date"], item["kind"] != "anaf", item["form"]))
    return result


def reminders(conn: sqlite3.Connection, today: date | None = None) -> list[dict]:
    """Ce trebuie plătit în următoarele 7 zile și nu e bifat ca plătit (pentru Testi și dashboard)."""
    return [item for item in calendar_items(conn, today)
            if item["status"] == "soon" and item["kind"] != "info" and (item["amount"] or 0) > 0]
