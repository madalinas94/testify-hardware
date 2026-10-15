"""Testi cu inteligență artificială (opțional): răspunde la întrebări despre cifrele firmei.

Funcționează doar dacă proprietarul activează opțiunea și pune o cheie API Anthropic.
La fiecare întrebare, aplicația trimite modelului Claude un rezumat al datelor firmei
(luni, stoc, clienți, furnizori, salarii) și conversația de până atunci. Fără cheie,
aplicația rămâne complet locală, iar Testi folosește doar regulile lui obișnuite.
"""

import base64
import json
import os
import sqlite3
from datetime import date

import anthropic

from . import calc, inventory
from .db import get_settings, set_setting
from .fiscal import settings_for_month

AI_MODEL = "claude-opus-5-5"
MAX_TURNS = 12  # câte mesaje din conversație se trimit (ultimele)

SYSTEM_PROMPT = """Ești Testi, asistentul financiar din aplicația internă a unei firme mici din România \
care vinde accesorii IT. Vorbești cu proprietarul firmei: un antreprenor, nu un contabil, care vrea \
răspunsuri clare și scurte.

Cum răspunzi:
- În limba română, cu diacritice, pe un ton prietenos, la persoana a doua singular („ai încasat”).
- Pe baza datelor firmei din mesajul de sistem (JSON). Nu inventa cifre. Dacă o informație nu e în \
date, spune asta și ce ar trebui introdus în aplicație ca să poți răspunde.
- Cu cifre concrete: sume în lei (format românesc, de exemplu 12.345 lei), luni numite explicit.
- Scurt: 2–6 propoziții sau o listă scurtă. Fără tabele mari. Poți folosi **îngroșat** și liste cu „- ”.
- Când explici o schimbare (de exemplu de ce a scăzut profitul), compară lunile și numește cauzele \
din date: vânzări, costul mărfii, cheltuieli pe categorii, salarii, impozit.
- Pentru decizii fiscale sau juridice, dă orientarea din date, dar recomandă confirmarea cu contabilul.

Termeni din date: revenue = venituri fără TVA; cogs = costul mărfii vândute; gross_margin = marja brută; \
opex_total = cheltuieli operaționale inclusiv salarii brute și CAM; profit = profit net după impozitul \
pe profit; owner_income = ce rămâne proprietarului după impozitul pe dividende; receivables = bani de \
încasat de la clienți (cu TVA); payables = bani de plătit furnizorilor (cu TVA); days_left = în câte \
zile se termină stocul la ritmul actual de vânzare."""


class AIError(Exception):
    """Eroare explicată pe înțeles, afișată direct proprietarului."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


def stored_key(conn: sqlite3.Connection) -> str:
    return get_settings(conn).get("anthropic_api_key", "")


def status(conn: sqlite3.Connection) -> dict:
    settings = get_settings(conn)
    key = settings.get("anthropic_api_key", "")
    env_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_key = bool(key) or env_key
    return {
        "enabled": settings.get("ai_enabled") == "1" and has_key,
        "switched_on": settings.get("ai_enabled") == "1",
        "has_key": has_key,
        "key_source": "setări" if key else ("variabilă de mediu" if env_key else None),
        "key_hint": f"{key[:7]}…{key[-4:]}" if len(key) > 12 else None,
        "model": AI_MODEL,
    }


def save_settings(conn: sqlite3.Connection, enabled: bool, api_key: str | None, clear_key: bool) -> None:
    set_setting(conn, "ai_enabled", "1" if enabled else "0")
    if clear_key:
        set_setting(conn, "anthropic_api_key", "")
    elif api_key:
        set_setting(conn, "anthropic_api_key", api_key.strip())


def business_snapshot(conn: sqlite3.Connection, today: str | None = None) -> dict:
    """Rezumatul datelor firmei pe care îl primește modelul (fără parole sau alte setări)."""
    today = today or date.today().isoformat()
    settings = settings_for_month(conn, today[:7])
    first = calc.first_data_month(conn) or today[:7]
    months, ym = [], today[:7]
    while ym >= first and len(months) < 12:
        s = calc.month_summary(conn, ym)
        months.append({
            "month": ym, "label": s["label"], "in_progress": ym == today[:7],
            "revenue": s["revenue"], "invoices": s["sales_count"], "cogs": s["cogs"],
            "gross_margin": s["gross_margin"], "gross_margin_pct": s["gross_margin_pct"],
            "expenses_by_category": s["expenses_by_category"], "salaries_gross": s["payroll"]["gross"],
            "salaries_net": s["payroll"]["net"], "opex_total": s["opex_total"],
            "profit_before_tax": s["profit_before_tax"], "company_tax": s["taxes"]["company_tax"],
            "profit": s["profit"], "owner_income": s["owner_income"],
            "vat_payable": s["vat"]["payable"] if s["vat"] else None,
            "purchases": s["purchases"], "stock_value": s["stock_value"],
        })
        ym = calc.shift_month(ym, -1)
    months.reverse()

    receivables = calc.receivables(conn, today)
    payables = calc.payables(conn, today)
    products = inventory.products_overview(conn, today)
    clients = [dict(row) for row in conn.execute(
        "SELECT c.name, c.type, c.city, c.agent, c.payment_terms, "
        "COALESCE(SUM(s.amount), 0) AS total_sales, COUNT(s.id) AS invoices, MAX(s.date) AS last_sale "
        "FROM clients c LEFT JOIN sales s ON s.client_id = c.id GROUP BY c.id ORDER BY total_sales DESC")]
    employees = calc.payroll(conn, today[:7])["lines"]
    from . import obligations, treasury  # import local: modulele depind de calc
    forecast = treasury.forecast(conn)
    return {
        "company": settings.get("company_name"),
        "today": today,
        "tax_regime": settings.get("tax_regime"),
        "vat_payer": settings.get("vat_payer", "1") == "1",
        "tax_rates_percent": {key: settings[key] for key in (
            "cas_rate", "cass_rate", "income_tax_rate", "cam_rate", "profit_tax_rate",
            "micro_tax_rate", "dividend_tax_rate", "vat_standard_rate", "vat_reduced_rate")},
        "months": months,
        "receivables": {"total": receivables["total"], "overdue": receivables["overdue"],
                        "by_client": receivables["clients"]},
        "payables": {"total": payables["total"], "overdue": payables["overdue"],
                     "due_next_7_days": payables["due_soon"], "by_supplier": payables["suppliers"]},
        "products": [{key: p[key] for key in ("code", "name", "category", "supplier", "sale_price", "cost",
                                              "margin_pct", "stock", "min_stock", "status", "stock_value",
                                              "sold_30", "days_left")} for p in products if p["active"]],
        "clients": clients,
        "employees": [{key: e[key] for key in ("name", "role", "gross", "net", "employer_cost", "worked_days")}
                      for e in employees],
        "fiscal_calendar_next": [{key: i[key] for key in ("date", "form", "title", "amount", "paid")}
                                 for i in obligations.calendar_items(conn) if i["days_left"] >= 0][:12],
        "cash_forecast_30_days": {key: forecast[key] for key in (
            "balance_set", "start_balance", "lowest", "end_balance", "total_in", "total_out")},
        "goals_this_month": calc.goals_for(conn, today[:7]),
        "closed_months": [row["month"] for row in conn.execute("SELECT month FROM month_locks ORDER BY month")],
    }


def make_client(conn: sqlite3.Connection) -> anthropic.Anthropic:
    key = stored_key(conn)
    # Fără cheie salvată, SDK-ul folosește ANTHROPIC_API_KEY din mediu.
    return anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()


def clean_history(messages: list[dict]) -> list[dict]:
    """Ultimele mesaje, alternând corect și începând cu o întrebare."""
    history = [{"role": m["role"], "content": m["content"].strip()} for m in messages
               if m.get("role") in ("user", "assistant") and str(m.get("content", "")).strip()]
    history = history[-MAX_TURNS:]
    while history and history[0]["role"] != "user":
        history.pop(0)
    if not history or history[-1]["role"] != "user":
        raise AIError("Scrieți o întrebare pentru Testi.", 400)
    return history


def ask(conn: sqlite3.Connection, messages: list[dict]) -> dict:
    if not status(conn)["enabled"]:
        raise AIError("Asistentul AI nu este activat. Îl puteți porni din Setări.", 400)
    history = clean_history(messages)
    snapshot = json.dumps(business_snapshot(conn), ensure_ascii=False, separators=(",", ":"))
    response = call_claude(
        make_client(conn),
        output_config={"effort": "medium"},
        # Instrucțiunile fixe primele (se pot reține în cache), datele firmei după ele.
        system=[
            {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": f"Datele firmei (JSON, sume în lei):\n{snapshot}"},
        ],
        messages=history,
    )
    if response.stop_reason == "refusal":
        return {"reply": "Nu pot răspunde la această întrebare. Încearcă să o formulezi altfel, "
                         "legat de cifrele firmei.", "model": response.model}
    text = "\n".join(block.text for block in response.content if block.type == "text").strip()
    if not text:
        raise AIError("Nu am primit un răspuns. Încercați din nou.")
    return {"reply": text, "model": response.model}


def call_claude(client: anthropic.Anthropic, **params):
    """Un apel la Claude, cu erorile traduse pe înțeles pentru proprietar."""
    try:
        return client.beta.messages.create(
            model=AI_MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",  # dacă modelul refuză, o preia automat modelul de rezervă
            **params,
        )
    except anthropic.AuthenticationError:
        raise AIError("Cheia API nu este validă. Verificați-o în Setări.", 400)
    except anthropic.PermissionDeniedError:
        raise AIError("Cheia API nu are acces la acest model.", 400)
    except anthropic.RateLimitError:
        raise AIError("Prea multe întrebări într-un timp scurt. Încercați din nou peste un minut.", 429)
    except anthropic.APIConnectionError:
        raise AIError("Nu există conexiune la internet. Testi cu AI are nevoie de internet.", 503)
    except anthropic.APIStatusError as error:
        raise AIError(f"Serviciul AI a răspuns cu o eroare ({error.status_code}). Încercați mai târziu.")


RECEIPT_PROMPT = """Aceasta este o factură sau un bon fiscal primit de o firmă din România (plătitoare de \
TVA). Extrage datele pentru a înregistra cheltuiala. Reguli:
- date: data documentului (AAAA-LL-ZZ). Dacă nu se vede, pune un șir gol.
- supplier: numele firmei care a emis documentul (ex. „OMV Petrom SA”), fără CUI.
- document_number: numărul facturii sau al bonului, dacă se vede.
- total: totalul de plată, CU TVA, în lei. net: suma fără TVA. vat: TVA total. Dacă documentul are \
mai multe cote, adună-le. Dacă nu se vede TVA separat, calculează-l din cotă.
- vat_kind: „standard” (21%, sau 19% pe documente mai vechi de august 2025), „reduced” (11%, 9% sau 5%) \
sau „none” (fără TVA: taxe, asigurări, comisioane bancare). La cote mixte, alege cota cu suma cea mai mare.
- category: alege EXACT una din categoriile: {categories}.
- description: 2–6 cuvinte despre ce s-a cumpărat (ex. „Motorină 45 litri”).
- confidence: „high” dacă documentul e clar, „medium” dacă ai ghicit ceva, „low” dacă nu e lizibil.
- notes: ce n-ai putut citi sau ce ar trebui verificat; șir gol dacă totul e clar.
Nu inventa: ce nu se vede rămâne gol (sau 0 la sume) și scrii în notes."""


def receipt_schema(categories: list[str]) -> dict:
    text = {"type": "string"}
    return {
        "type": "object",
        "properties": {
            "date": text, "supplier": text, "document_number": text,
            "total": {"type": "number"}, "net": {"type": "number"}, "vat": {"type": "number"},
            "vat_kind": {"type": "string", "enum": ["standard", "reduced", "none"]},
            "category": {"type": "string", "enum": categories},
            "description": text,
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "notes": text,
        },
        "required": ["date", "supplier", "document_number", "total", "net", "vat", "vat_kind", "category",
                     "description", "confidence", "notes"],
        "additionalProperties": False,
    }


RECEIPT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "application/pdf"}


def read_receipt(conn: sqlite3.Connection, content: bytes, media_type: str) -> dict:
    """Citește un bon sau o factură (poză sau PDF) și propune cheltuiala completată."""
    if not status(conn)["enabled"]:
        raise AIError("Pentru citirea bonurilor, porniți Testi cu AI din Setări.", 400)
    if media_type not in RECEIPT_TYPES:
        raise AIError("Trimiteți o poză (JPG, PNG) sau un PDF.", 400)
    categories = [row["name"] for row in conn.execute("SELECT name FROM categories ORDER BY id")]
    data = base64.standard_b64encode(content).decode("utf-8")
    block = ({"type": "document", "source": {"type": "base64", "media_type": media_type, "data": data}}
             if media_type == "application/pdf" else
             {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}})
    response = call_claude(
        make_client(conn),
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": receipt_schema(categories)}},
        messages=[{"role": "user", "content": [
            block, {"type": "text", "text": RECEIPT_PROMPT.format(categories=", ".join(categories))}]}],
    )
    if response.stop_reason == "refusal":
        raise AIError("Nu am putut citi documentul. Completați cheltuiala manual.", 422)
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        result = json.loads(text)
    except ValueError:
        raise AIError("Nu am putut citi documentul. Încercați o poză mai clară.", 422)
    # Verificări simple: sumele trebuie să se lege (net + TVA = total).
    if result["total"] and not result["net"]:
        result["net"] = round(result["total"] - result["vat"], 2)
    result["consistent"] = abs(result["net"] + result["vat"] - result["total"]) <= 0.05 * max(result["total"], 1)
    try:
        date.fromisoformat(result["date"])
    except ValueError:
        result["date"] = ""
    return result
