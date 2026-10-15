"""Decizii: simulatorul „Ce-ar fi dacă…”, comenzile recomandate la furnizori și analiza clienților
și a produselor (cine aduce profitul, cine nu mai cumpără, ce marfă stă degeaba)."""

import math
import sqlite3
from datetime import date, timedelta

from . import calc, inventory, treasury
from .fiscal import settings_for_month

SAFETY_DAYS = 7     # rezervă: comanda pleacă înainte să se ajungă la stocul minim
COVER_DAYS = 30     # o comandă acoperă cam o lună de vânzări
INACTIVE_DAYS = 60  # client care nu a mai cumpărat de atâtea zile


# ---------- Simulatorul „Ce-ar fi dacă…” ----------

def simulate(conn: sqlite3.Connection, base_month: str, price_pct: float = 0, volume_pct: float = 0,
             cost_pct: float = 0, raise_pct: float = 0, new_employees: list[float] | None = None,
             extra_expenses: float = 0) -> dict:
    """Recalculează luna de bază cu modificările propuse. Totul pe lună, fără TVA."""
    settings = settings_for_month(conn, base_month)
    base = calc.month_summary(conn, base_month)
    price, volume, cost = 1 + price_pct / 100, 1 + volume_pct / 100, 1 + cost_pct / 100

    revenue = base["revenue"] * price * volume
    cogs = base["cogs"] * volume * cost
    expenses = base["operating_expenses"] + extra_expenses
    payroll = base["payroll"]["employer_cost"] * (1 + raise_pct / 100)
    salary_taxes = (base["taxes"]["cas"] + base["taxes"]["cass"] + base["taxes"]["income_tax"]
                    + base["taxes"]["cam"]) * (1 + raise_pct / 100)
    hires = []
    for gross in new_employees or []:
        breakdown = calc.salary_breakdown(gross, settings)
        payroll += breakdown["employer_cost"]
        salary_taxes += breakdown["cas"] + breakdown["cass"] + breakdown["income_tax"] + breakdown["cam"]
        hires.append(breakdown)
    pbt = revenue - cogs - expenses - payroll
    if settings.get("tax_regime") == "micro":
        company_tax = calc.rnd(revenue * calc.rate(settings, "micro_tax_rate"))
    else:
        company_tax = max(0.0, calc.rnd(pbt * calc.rate(settings, "profit_tax_rate")))
    profit = pbt - company_tax
    dividend_tax = max(profit, 0) * calc.rate(settings, "dividend_tax_rate")
    margin_pct = (revenue - cogs) / revenue if revenue else 0
    fixed = expenses + payroll
    breakeven = fixed / margin_pct if margin_pct > 0 else None

    scenario = {
        "revenue": calc.r2(revenue), "cogs": calc.r2(cogs), "gross_margin": calc.r2(revenue - cogs),
        "gross_margin_pct": calc.r2(margin_pct * 100), "operating_expenses": calc.r2(expenses),
        "payroll_cost": calc.r2(payroll), "salary_taxes": calc.r2(salary_taxes),
        "profit_before_tax": calc.r2(pbt), "company_tax": calc.r2(company_tax), "profit": calc.r2(profit),
        "owner_income": calc.r2(max(profit, 0) - dividend_tax),
        "breakeven_revenue": calc.r2(breakeven) if breakeven else None,
    }
    baseline = {
        "revenue": base["revenue"], "cogs": base["cogs"], "gross_margin": base["gross_margin"],
        "gross_margin_pct": base["gross_margin_pct"], "operating_expenses": base["operating_expenses"],
        "payroll_cost": base["payroll"]["employer_cost"],
        "salary_taxes": calc.r2(base["taxes"]["total"] - base["taxes"]["company_tax"]),
        "profit_before_tax": base["profit_before_tax"], "company_tax": base["taxes"]["company_tax"],
        "profit": base["profit"], "owner_income": base["owner_income"],
        "breakeven_revenue": calc.r2((base["operating_expenses"] + base["payroll"]["employer_cost"])
                                     / (base["gross_margin"] / base["revenue"])) if base["gross_margin"] > 0 else None,
    }
    delta = {key: calc.r2((scenario[key] or 0) - (baseline[key] or 0)) for key in scenario}
    notes = []
    if hires:
        hire_cost = sum(h["employer_cost"] for h in hires)
        extra_sales = hire_cost / margin_pct if margin_pct > 0 else None
        notes.append(f"{'Angajatul nou costă' if len(hires) == 1 else 'Angajații noi costă'} firma {calc.fmt(hire_cost)} pe "
                     f"lună (cu CAM). Ca să-i acoperiți, trebuie vânzări în plus de "
                     f"{calc.fmt(extra_sales) if extra_sales else '—'} pe lună, la marja actuală.")
    if price_pct:
        # Efectul prețului singur, fără celelalte modificări, ca să fie clar de unde vine fiecare leu.
        base_fixed = base["operating_expenses"] + base["payroll"]["employer_cost"]
        price_only = (base["revenue"] * price - base["cogs"] * cost) - base_fixed - base["profit_before_tax"]
        notes.append(f"Doar din prețuri ({price_pct:+g}%), la aceleași cantități, profitul înainte de impozit se schimbă cu "
                     f"{calc.fmt(price_only)} pe lună.")
        if price_pct > 0:
            drop = _volume_break_even(base, price, cost, base["operating_expenses"], base["payroll"]["employer_cost"])
            if drop > 0:
                notes.append(f"Prețurile mai mari rămân avantajoase chiar dacă vindeți cu până la "
                             f"{calc.fmt_pct(drop)} mai puțin decât acum.")
    if scenario["profit"] < 0 <= baseline["profit"]:
        notes.append("În acest scenariu, firma intră pe pierdere.")
    if breakeven:
        notes.append(f"Pragul de rentabilitate: {calc.fmt(breakeven)} vânzări pe lună (sub această sumă, firma pierde bani).")
    return {"base_month": base_month, "label": calc.month_label(base_month), "baseline": baseline,
            "scenario": scenario, "delta": delta, "yearly_profit_delta": calc.r2(delta["profit"] * 12),
            "hires": hires, "notes": notes}


def _volume_break_even(base: dict, price: float, cost: float, expenses: float, payroll: float) -> float:
    """Cu cât pot scădea vânzările (în %) la prețurile noi, ca profitul înainte de impozit să rămână la fel."""
    unit_margin = base["revenue"] * price - base["cogs"] * cost
    if unit_margin <= 0:
        return 0.0
    needed = base["profit_before_tax"] + expenses + payroll
    return (1 - needed / unit_margin) * 100


# ---------- Comenzi recomandate ----------

def reorder(conn: sqlite3.Connection, today: str | None = None) -> dict:
    today = today or date.today().isoformat()
    day = date.fromisoformat(today)
    suppliers = {row["name"]: dict(row) for row in conn.execute("SELECT * FROM suppliers")}
    settings = settings_for_month(conn, today[:7])
    vat = calc.rate(settings, "vat_standard_rate") if settings.get("vat_payer", "1") == "1" else 0
    lines = []
    for product in inventory.products_overview(conn, today):
        if not product["active"]:
            continue
        supplier = suppliers.get(product["supplier"], {})
        lead = supplier.get("lead_days", 5)
        daily = product["sold_30"] / 30
        stock, minimum = product["stock"], product["min_stock"]
        point = math.ceil(daily * (lead + SAFETY_DAYS)) + minimum
        if stock > point and stock > minimum:
            continue
        if daily <= 0 and stock > minimum:
            continue
        quantity = (math.ceil(daily * (lead + COVER_DAYS)) + minimum - stock) if daily > 0 else max(2 * minimum - stock, 1)
        quantity = max(quantity, 1)
        days_left = (stock - minimum) / daily if daily > 0 else 0
        order_by = day + timedelta(days=max(0, math.floor(days_left) - lead))
        run_out = day + timedelta(days=math.floor(stock / daily)) if daily > 0 and stock > 0 else day
        lines.append({
            "product_id": product["id"], "code": product["code"], "name": product["name"],
            "supplier": product["supplier"] or "Fără furnizor", "stock": stock, "min_stock": minimum,
            "daily": calc.r2(daily), "lead_days": lead, "quantity": quantity, "unit_cost": product["cost"],
            "value": calc.r2(quantity * product["cost"]),
            "order_by": order_by.isoformat(), "run_out": run_out.isoformat(),
            "urgency": "now" if order_by <= day else "week" if (order_by - day).days <= 7 else "soon",
        })
    lines.sort(key=lambda line: (line["order_by"], line["supplier"]))
    groups: dict[str, dict] = {}
    for line in lines:
        group = groups.setdefault(line["supplier"], {"supplier": line["supplier"], "lines": [], "value": 0.0,
                                                     "terms": suppliers.get(line["supplier"], {}).get("payment_terms", 30),
                                                     "lead_days": line["lead_days"],
                                                     "contact": suppliers.get(line["supplier"], {}).get("contact", "")})
        group["lines"].append(line)
        group["value"] = calc.r2(group["value"] + line["value"])
    for group in groups.values():
        group["value_with_vat"] = calc.r2(group["value"] * (1 + vat))
        group["payment_due"] = (day + timedelta(days=group["lead_days"] + group["terms"])).isoformat()
        group["urgency"] = min((line["urgency"] for line in group["lines"]), key=["now", "week", "soon"].index)
        group["message"] = order_message(group, conn)
    ordered = sorted(groups.values(), key=lambda g: (["now", "week", "soon"].index(g["urgency"]), -g["value"]))
    total_vat = calc.r2(sum(g["value_with_vat"] for g in ordered))
    forecast = treasury.forecast(conn, day)
    warning = None
    if forecast["balance_set"] and total_vat > max(forecast["lowest"]["balance"], 0):
        warning = (f"Toate comenzile costă {calc.fmt(total_vat)} cu TVA, mai mult decât cel mai mic sold estimat "
                   f"({calc.fmt(forecast['lowest']['balance'])}). Comandați întâi ce e urgent.")
    return {"groups": ordered, "count": len(lines), "total": calc.r2(sum(g["value"] for g in ordered)),
            "total_with_vat": total_vat, "cash_warning": warning,
            "assumptions": {"safety_days": SAFETY_DAYS, "cover_days": COVER_DAYS}}


def order_message(group: dict, conn) -> str:
    from .db import get_settings

    company = get_settings(conn).get("company_name", "Testify Hardware")
    rows = "\n".join(f"- {line['code']} {line['name']}: {line['quantity']} buc." for line in group["lines"])
    return (f"Bună ziua,\n\nVă rugăm să ne trimiteți următoarele produse:\n{rows}\n\n"
            f"Vă rugăm să ne confirmați disponibilitatea și termenul de livrare.\n\nMulțumim,\n{company}")


# ---------- Analiza clienților și a produselor ----------

def abc(items: list[dict], key: str) -> list[dict]:
    total = sum(max(item[key], 0) for item in items) or 1
    running = 0.0
    for item in sorted(items, key=lambda x: x[key], reverse=True):
        running += max(item[key], 0)
        share = running / total * 100
        item["share"] = calc.r2(max(item[key], 0) / total * 100)
        item["cumulative"] = calc.r2(share)
        item["class"] = "A" if share - item["share"] < 80 else "B" if share - item["share"] < 95 else "C"
    return sorted(items, key=lambda x: x[key], reverse=True)


def analysis(conn: sqlite3.Connection, end_month: str, months: int = 3, today: str | None = None) -> dict:
    today = today or date.today().isoformat()
    start = calc.month_bounds(calc.shift_month(end_month, -(months - 1)))[0]
    end = calc.month_bounds(end_month)[1]
    clients = [dict(row) for row in conn.execute(
        "SELECT c.id, c.name, c.type, COALESCE(SUM(s.amount), 0) AS revenue, "
        "COALESCE(SUM(s.amount - COALESCE(s.quantity, 1) * COALESCE(s.unit_cost, 0)), 0) AS profit, "
        "COUNT(s.id) AS invoices FROM clients c JOIN sales s ON s.client_id = c.id "
        "WHERE s.date BETWEEN ? AND ? GROUP BY c.id", (start, end))]
    for client in clients:
        client["revenue"], client["profit"] = calc.r2(client["revenue"]), calc.r2(client["profit"])
    clients = abc(clients, "profit")
    top_count = next((i + 1 for i, c in enumerate(clients) if c["cumulative"] >= 80), len(clients))

    reference = conn.execute("SELECT MAX(date) FROM sales").fetchone()[0] or today
    reference = min(reference, today)
    cutoff = (date.fromisoformat(reference) - timedelta(days=INACTIVE_DAYS)).isoformat()
    inactive = [dict(row) for row in conn.execute(
        "SELECT c.name, c.type, MAX(s.date) AS last_sale, COUNT(s.id) AS invoices, SUM(s.amount) AS revenue "
        "FROM clients c JOIN sales s ON s.client_id = c.id GROUP BY c.id "
        "HAVING last_sale < ? AND invoices >= 2 ORDER BY revenue DESC", (cutoff,))]

    products = [dict(row) for row in conn.execute(
        "SELECT p.id, p.code, p.name, COALESCE(SUM(s.quantity), 0) AS quantity, COALESCE(SUM(s.amount), 0) AS revenue, "
        "COALESCE(SUM(s.amount - s.quantity * COALESCE(s.unit_cost, 0)), 0) AS profit FROM products p "
        "LEFT JOIN sales s ON s.product_id = p.id AND s.date BETWEEN ? AND ? WHERE p.active = 1 GROUP BY p.id",
        (start, end))]
    for product in products:
        product["revenue"], product["profit"] = calc.r2(product["revenue"]), calc.r2(product["profit"])
    products = abc(products, "profit")

    overview = {p["id"]: p for p in inventory.products_overview(conn, today)}
    last_sales = {row["product_id"]: row["last"] for row in conn.execute(
        "SELECT product_id, MAX(date) AS last FROM sales WHERE product_id IS NOT NULL GROUP BY product_id")}
    dead = []
    for pid, product in overview.items():
        if not product["active"] or product["stock"] <= 0:
            continue
        last = last_sales.get(pid)
        idle = last is None or last < cutoff
        slow = product["days_left"] is not None and product["days_left"] > 120
        if idle or slow:
            dead.append({"code": product["code"], "name": product["name"], "stock": product["stock"],
                         "value": product["stock_value"], "last_sale": last, "days_left": product["days_left"],
                         "reason": "fără vânzări de peste 60 de zile" if idle else
                                   f"stoc pentru ~{product['days_left']} zile"})
    dead.sort(key=lambda item: item["value"], reverse=True)

    notes = []
    if clients:
        notes.append(f"{top_count} din {len(clients)} clienți aduc 80% din profit. Pe ei merită să-i păstrați "
                     "cu prioritate (termene, oferte, telefon personal).")
        top = clients[0]
        if top["share"] >= 30:
            notes.append(f"Atenție la dependență: „{top['name']}” aduce singur {calc.fmt_pct(top['share'])} din profit. "
                         "Dacă pleacă, firma simte imediat.")
    if inactive:
        lost = sum(c["revenue"] for c in inactive)
        notes.append(f"{len(inactive)} clienți care cumpărau des nu au mai cumpărat de peste {INACTIVE_DAYS} de zile "
                     f"(au cumpărat în total {calc.fmt(lost)}). Un telefon îi poate aduce înapoi.")
    if dead:
        value = sum(d["value"] for d in dead)
        notes.append(f"Marfă care stă: {calc.fmt(value)} blocați în {len(dead)} produse. O reducere sau un pachet "
                     "promoțional eliberează banii.")
    losers = [p for p in products if p["profit"] < 0]
    if losers:
        notes.append(f"{len(losers)} produse s-au vândut în pierdere (sub cost). Verificați prețurile.")
    return {"period": {"start": start, "end": end, "months": months,
                       "label": f"{calc.month_label(start[:7])} – {calc.month_label(end_month)}"},
            "clients": clients, "top_count": top_count, "inactive": inactive, "products": products,
            "dead_stock": dead, "dead_stock_value": calc.r2(sum(d["value"] for d in dead)), "notes": notes}
