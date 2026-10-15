"""Testify Hardware — aplicația internă pentru calculul lunar.

Pornire: uvicorn app.main:app --host 0.0.0.0 --port 8000 (din folderul testify_hardware)
"""

import asyncio
import re
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path

from fastapi import (APIRouter, Cookie, Depends, FastAPI, File, Form, HTTPException, Query,
                     Response, UploadFile)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

from . import (assistant_ai, audit, auth, backup, calc, closing, demo, efactura, exports, fiscal, importer,
               inventory, letter, obligations, planning, treasury)
from .db import DEFAULT_SETTINGS, DEFAULT_SUPPLIER_TERMS, get_conn, get_settings, init_db, set_setting

STATIC_DIR = Path(__file__).resolve().parent / "static"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"
VAT_KIND_PATTERN = r"^(standard|reduced|none)$"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def run_fiscal_check() -> dict:
    with get_conn() as conn:
        return fiscal.check_for_updates(conn)


async def fiscal_watcher() -> None:
    """Verifică periodic, în fundal, dacă au apărut reguli fiscale noi."""
    while True:
        await asyncio.to_thread(run_fiscal_check)
        await asyncio.sleep(fiscal.CHECK_INTERVAL_HOURS * 3600)


async def backup_watcher() -> None:
    """Copia de siguranță zilnică: la pornire și apoi verificare din oră în oră."""
    while True:
        try:
            await asyncio.to_thread(backup.daily_backup)
        except Exception:  # discul plin sau folder blocat nu opresc aplicația
            pass
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    tasks = [asyncio.create_task(backup_watcher())]
    if fiscal.feed_url():
        tasks.append(asyncio.create_task(fiscal_watcher()))
    yield
    for task in tasks:
        task.cancel()


app = FastAPI(title="Testify Hardware", description="Aplicația internă pentru calculul lunar",
              lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

FIELD_NAMES = {
    "date": "data", "amount": "suma", "quantity": "cantitatea", "unit_price": "prețul", "unit_cost": "costul",
    "cost_total": "costul mărfii", "sale_price": "prețul de vânzare", "cost": "costul", "gross": "salariul brut",
    "name": "numele", "code": "codul", "category": "categoria", "password": "parola", "new": "parola nouă",
    "hire_date": "data angajării", "end_date": "data plecării", "effective_from": "data", "min_stock": "stocul minim",
    "payment_terms": "termenul de plată", "company_name": "numele firmei", "month": "luna",
    "revenue": "vânzări", "profit": "profit", "balance": "soldul", "days": "zilele", "discount": "reducerea",
    "payday": "ziua salariilor", "tax_loss_carried": "pierderea fiscală", "hours_per_day": "norma", "leave_days": "zilele de concediu",
}


def friendly_error(error: dict) -> str:
    """Mesajele de validare, în română și pe înțeles."""
    field = FIELD_NAMES.get(str(error.get("loc", [""])[-1]), "câmpul")
    kind, ctx = error.get("type", ""), error.get("ctx") or {}
    limit = ctx.get("le", ctx.get("lt", ctx.get("ge", ctx.get("gt", ""))))
    if isinstance(limit, float) and limit.is_integer():
        limit = int(limit)
    limit = f"{limit:,}".replace(",", ".") if isinstance(limit, (int, float)) else limit
    messages = {
        "missing": f"Completați {field}.",
        "string_too_short": f"Completați {field}.",
        "string_too_long": f"Textul pentru {field} este prea lung.",
        "less_than_equal": f"Valoarea pentru {field} este prea mare (maximum {limit}).",
        "less_than": f"Valoarea pentru {field} este prea mare.",
        "greater_than": f"Valoarea pentru {field} trebuie să fie mai mare decât {limit}.",
        "greater_than_equal": f"Valoarea pentru {field} trebuie să fie cel puțin {limit}.",
        "int_parsing": f"Introduceți un număr întreg pentru {field}.",
        "float_parsing": f"Introduceți un număr pentru {field}.",
        "string_pattern_mismatch": f"Formatul pentru {field} nu este corect.",
    }
    if kind == "value_error":
        return str(error.get("msg", "")).removeprefix("Value error, ")
    return messages.get(kind, f"Valoarea pentru {field} nu este corectă.")


@app.exception_handler(RequestValidationError)
async def validation_error(_request, exc: RequestValidationError):
    details = list(dict.fromkeys(friendly_error(error) for error in exc.errors()))
    return JSONResponse(status_code=422, content={"detail": " ".join(details)})


@app.exception_handler(sqlite3.DatabaseError)
async def database_error(_request, exc: sqlite3.DatabaseError):
    if closing.is_lock_error(exc):
        return JSONResponse(status_code=400, content={"detail": CLOSED_MESSAGE})
    raise exc


CLOSED_MESSAGE = ("Luna este închisă, deci documentele din ea nu se mai pot modifica. Dacă trebuie "
                  "neapărat o corectură, redeschideți luna din Rapoarte → Închiderea lunii.")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/static/index.html")


def valid_date(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if not DATE_RE.match(value):
        raise ValueError("Data trebuie să fie în formatul AAAA-LL-ZZ.")
    day = date.fromisoformat(value)
    if day.year < 2000 or day > date.today() + timedelta(days=366):
        raise ValueError("Data nu pare corectă (prea veche sau prea departe în viitor).")
    return value


def not_in_future(value: str) -> str:
    """Facturile și recepțiile nu pot avea o dată din viitor."""
    if value and value > date.today().isoformat():
        raise ValueError("Data nu poate fi în viitor.")
    return value


MAX_AMOUNT = 1_000_000_000  # o sumă mai mare pe un singur document e aproape sigur o greșeală de tastare


def ensure_stock(conn, *product_ids) -> None:
    """Oprește operația (și o anulează) dacă ar lăsa un produs cu stoc negativ."""
    stock = inventory.stock_on(conn, "9999-12-31")
    for pid in {p for p in product_ids if p}:
        if stock.get(pid, 0) < 0:
            name = conn.execute("SELECT name FROM products WHERE id = ?", (pid,)).fetchone()["name"]
            available = stock[pid]
            raise HTTPException(status_code=400, detail=f"Stoc insuficient pentru „{name}”: operația ar lăsa "
                                f"{available} buc. Faceți întâi o recepție de marfă.")


def unique_name_error(kind: str) -> HTTPException:
    return HTTPException(status_code=400, detail=f"Există deja {kind} cu acest nume.")


# ---------- Autentificare ----------

class PasswordIn(BaseModel):
    password: str = Field(min_length=4, max_length=200)


class SetupIn(PasswordIn):
    demo: bool = False


class ChangePasswordIn(BaseModel):
    current: str
    new: str = Field(min_length=4, max_length=200)


class RecoverIn(BaseModel):
    code: str = Field(min_length=4, max_length=40)
    password: str = Field(min_length=4, max_length=200)


class CurrentPasswordIn(BaseModel):
    current: str


def start_session(response: Response, conn) -> None:
    token = auth.create_session(conn)
    response.set_cookie(auth.COOKIE_NAME, token, httponly=True, samesite="strict",
                        max_age=60 * 60 * 24 * 30)


@app.get("/api/auth/status")
def auth_status(testify_session: str | None = Cookie(default=None)):
    with get_conn() as conn:
        settings = get_settings(conn)
        return {
            "setup_done": auth.is_setup_done(conn),
            "logged_in": auth.is_valid_session(conn, testify_session),
            "company": settings.get("company_name"),
            "owner_name": settings.get("owner_name", ""),
            "has_recovery": auth.has_recovery_code(conn),
            "has_pin": auth.has_pin(conn),
            "idle_lock_minutes": auth.idle_limit_minutes(conn),
        }


@app.post("/api/auth/setup")
def auth_setup(body: SetupIn, response: Response):
    with get_conn() as conn:
        if auth.is_setup_done(conn):
            raise HTTPException(status_code=400, detail="Parola a fost deja setată.")
        auth.set_password(conn, body.password)
        code = auth.set_recovery_code(conn)
        if body.demo:
            with audit.paused(conn):
                demo.load_demo_data(conn)
            audit.log_event(conn, "Au fost încărcate datele firmei din T3 2026", "import")
        start_session(response, conn)
    return {"ok": True, "recovery_code": code}


@app.post("/api/auth/login")
def auth_login(body: PasswordIn, response: Response):
    auth.limiter.check()
    with get_conn() as conn:
        if not auth.check_password(conn, body.password):
            auth.limiter.failed()
            raise HTTPException(status_code=401, detail="Parolă greșită.")
        auth.limiter.reset()
        auth.unlock_pin(conn)
        start_session(response, conn)
    return {"ok": True}


class PinIn(BaseModel):
    pin: str = Field(pattern=r"^\d{4,8}$")


@app.post("/api/auth/pin-login")
def auth_pin_login(body: PinIn, response: Response):
    auth.limiter.check()
    with get_conn() as conn:
        if not auth.has_pin(conn):
            raise HTTPException(status_code=400, detail="PIN-ul nu este activ. Intrați cu parola.")
        if not auth.check_pin(conn, body.pin):
            auth.limiter.failed()
            conn.commit()  # greșeala se numără chiar dacă cererea se termină cu eroare
            left = auth.has_pin(conn)
            raise HTTPException(status_code=401, detail="PIN greșit." if left else
                                "PIN greșit de 3 ori: intrați acum cu parola (PIN-ul se reactivează după).")
        start_session(response, conn)
    return {"ok": True}


@app.post("/api/auth/recover")
def auth_recover(body: RecoverIn, response: Response):
    """Parolă uitată: cu codul de recuperare se pune o parolă nouă și se primește un cod nou."""
    auth.limiter.check()
    with get_conn() as conn:
        if not auth.check_recovery_code(conn, body.code):
            auth.limiter.failed()
            raise HTTPException(status_code=400, detail="Codul de recuperare nu este corect.")
        auth.limiter.reset()
        auth.set_password(conn, body.password)
        auth.end_all_sessions(conn)  # cine era conectat cu parola veche iese
        code = auth.set_recovery_code(conn)  # codul folosit nu mai e valabil
        start_session(response, conn)
    return {"ok": True, "recovery_code": code}


@app.post("/api/auth/logout")
def auth_logout(response: Response, testify_session: str | None = Cookie(default=None)):
    with get_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (testify_session,))
    response.delete_cookie(auth.COOKIE_NAME)
    return {"ok": True}


# Tot ce urmează cere autentificare.
api = APIRouter(prefix="/api", dependencies=[Depends(auth.require_login)])


@api.post("/auth/change-password")
def change_password(body: ChangePasswordIn):
    with get_conn() as conn:
        if not auth.check_password(conn, body.current):
            raise HTTPException(status_code=400, detail="Parola actuală nu este corectă.")
        auth.set_password(conn, body.new)
    return {"ok": True}


class SetPinIn(CurrentPasswordIn):
    pin: str = Field(pattern=r"^\d{4,8}$")


@api.put("/auth/pin")
def set_pin(body: SetPinIn):
    with get_conn() as conn:
        if not auth.check_password(conn, body.current):
            raise HTTPException(status_code=400, detail="Parola actuală nu este corectă.")
        if len(set(body.pin)) == 1 or body.pin in "0123456789" or body.pin in "9876543210":
            raise HTTPException(status_code=400, detail="Alegeți un PIN mai greu de ghicit (nu 1111 sau 1234).")
        auth.set_pin(conn, body.pin)
        audit.log_event(conn, "PIN-ul de intrare rapidă a fost setat", "security")
    return {"ok": True}


@api.delete("/auth/pin")
def delete_pin():
    with get_conn() as conn:
        auth.clear_pin(conn)
        audit.log_event(conn, "PIN-ul de intrare rapidă a fost dezactivat", "security")
    return {"ok": True}


@api.post("/auth/recovery-code")
def new_recovery_code(body: CurrentPasswordIn):
    with get_conn() as conn:
        if not auth.check_password(conn, body.current):
            raise HTTPException(status_code=400, detail="Parola actuală nu este corectă.")
        return {"recovery_code": auth.set_recovery_code(conn)}


# ---------- Dashboard și rapoarte ----------

@api.get("/dashboard")
def get_dashboard(month: str = Query(default_factory=calc.current_month, pattern=MONTH_PATTERN)):
    with get_conn() as conn:
        result = calc.dashboard(conn, month)
        result["reminders"] = obligations.reminders(conn)
        result["closed"] = bool(conn.execute("SELECT 1 FROM month_locks WHERE month = ?", (month,)).fetchone())
        return result


@api.get("/payroll")
def get_payroll(month: str = Query(default_factory=calc.current_month, pattern=MONTH_PATTERN)):
    with get_conn() as conn:
        return calc.payroll(conn, month)


@api.get("/summary")
def get_summary(month: str = Query(default_factory=calc.current_month, pattern=MONTH_PATTERN)):
    with get_conn() as conn:
        return calc.month_summary(conn, month)


@api.get("/export/excel")
def export_excel(month: str = Query(pattern=MONTH_PATTERN)):
    with get_conn() as conn:
        content = exports.excel_report(conn, month)
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="raport-{month}.xlsx"'},
    )


@api.get("/export/letter")
def export_letter(month: str = Query(pattern=MONTH_PATTERN)):
    with get_conn() as conn:
        content = letter.letter_pdf(conn, month)
    return Response(content, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="scrisoarea-lunii-{month}.pdf"'})


@api.get("/export/pdf")
def export_pdf(month: str = Query(pattern=MONTH_PATTERN)):
    with get_conn() as conn:
        content = exports.pdf_report(conn, month)
    return Response(
        content, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="raport-{month}.pdf"'},
    )


# ---------- Vânzări ----------

class SaleIn(BaseModel):
    """O factură pe un produs din stoc sau un total pe zi/lună (fără produs)."""
    date: str
    product_id: int | None = None
    client_id: int | None = None
    quantity: int | None = Field(default=None, ge=1, le=1_000_000)
    unit_price: float | None = Field(default=None, gt=0, le=MAX_AMOUNT)
    amount: float | None = Field(default=None, gt=0, le=MAX_AMOUNT)
    cost_total: float | None = Field(default=None, ge=0, le=MAX_AMOUNT)
    description: str = Field(default="", max_length=200)
    invoice_number: str | None = Field(default=None, max_length=40)
    paid: bool | None = None
    discount: float = Field(default=0, ge=0, lt=100)  # reducere în procente, pe facturile cu produs

    @field_validator("date")
    @classmethod
    def check_date(cls, value):
        return not_in_future(valid_date(value))


class ReturnIn(BaseModel):
    """Retur (stornare): o factură cu minus care readuce marfa în stoc și scade TVA."""
    date: str = Field(default_factory=lambda: date.today().isoformat())
    quantity: int | None = Field(default=None, ge=1, le=1_000_000)
    amount: float | None = Field(default=None, gt=0, le=MAX_AMOUNT)
    reason: str = Field(default="", max_length=200)

    @field_validator("date")
    @classmethod
    def check_date(cls, value):
        return not_in_future(valid_date(value))


def next_invoice_number(conn) -> str:
    numbers = [int(match.group(1)) for (number,) in conn.execute(
        "SELECT invoice_number FROM sales WHERE invoice_number LIKE 'NB-%'")
        if (match := re.match(r"NB-(\d+)$", number or ""))]
    return f"NB-{max(numbers, default=1000) + 1:04d}"


def sale_values(conn, body: SaleIn) -> dict:
    """Completează o vânzare: preț și cost din produs, scadență din termenul clientului."""
    client = None
    if body.client_id:
        client = conn.execute("SELECT * FROM clients WHERE id = ?", (body.client_id,)).fetchone()
        if not client:
            raise HTTPException(status_code=404, detail="Clientul nu există.")
    terms = client["payment_terms"] if client else 0
    due = (date.fromisoformat(body.date) + timedelta(days=terms)).isoformat()
    values = {"date": body.date, "client_id": body.client_id, "due_date": due,
              "paid": int(body.paid if body.paid is not None else terms == 0)}
    if body.product_id:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (body.product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Produsul nu există.")
        quantity = body.quantity or 1
        price = body.unit_price or product["sale_price"]
        if not price:
            raise HTTPException(status_code=422, detail="Completați prețul de vânzare.")
        values.update(product_id=product["id"], product=product["name"], quantity=quantity,
                      unit_price=price, unit_cost=product["cost"], discount=body.discount,
                      amount=round(quantity * price * (1 - body.discount / 100), 2),
                      description=body.description or f"{product['name']} ×{quantity}")
    else:
        if not body.amount:
            raise HTTPException(status_code=422, detail="Completați suma vânzării.")
        if not body.description.strip():
            raise HTTPException(status_code=422, detail="Completați descrierea.")
        values.update(product_id=None, product=None, quantity=None, unit_price=None, discount=0,
                      unit_cost=body.cost_total or 0, amount=round(body.amount, 2),
                      description=body.description.strip())
    return values


def check_invoice_unique(conn, number: str, sale_id: int | None = None) -> None:
    clash = conn.execute("SELECT id FROM sales WHERE invoice_number = ? AND id IS NOT ?",
                         (number, sale_id)).fetchone()
    if clash:
        raise HTTPException(status_code=400, detail=f"Există deja factura {number}.")


SALE_COLUMNS = ["date", "description", "product", "quantity", "amount", "product_id", "client_id",
                "unit_price", "unit_cost", "due_date", "paid", "discount"]


def stock_warning(conn, product_id: int | None) -> str | None:
    if not product_id:
        return None
    product = next((p for p in inventory.products_overview(conn) if p["id"] == product_id), None)
    if product and product["stock"] < 0:
        return f"Atenție: stocul pentru „{product['name']}” a ajuns la {product['stock']} buc."
    if product and product["status"] == "low":
        return f"Mai sunt doar {product['stock']} buc. din „{product['name']}”."
    return None


@api.get("/sales")
def list_sales(month: str = Query(default_factory=calc.current_month, pattern=MONTH_PATTERN)):
    start, end = calc.month_bounds(month)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT s.*, c.name AS client_name, c.type AS client_type, "
            "(SELECT -SUM(amount) FROM sales r WHERE r.storno_of = s.id) AS returned_amount, "
            "(SELECT -SUM(quantity) FROM sales r WHERE r.storno_of = s.id) AS returned_quantity, "
            "(SELECT invoice_number FROM sales o WHERE o.id = s.storno_of) AS storno_of_invoice FROM sales s "
            "LEFT JOIN clients c ON c.id = s.client_id WHERE s.date BETWEEN ? AND ? "
            "ORDER BY s.date DESC, s.id DESC",
            (start, end),
        ).fetchall()
    return [dict(row) for row in rows]


@api.get("/sales/next-invoice")
def get_next_invoice():
    with get_conn() as conn:
        return {"invoice_number": next_invoice_number(conn)}


@api.post("/sales", status_code=201)
def create_sale(body: SaleIn):
    with get_conn() as conn:
        values = sale_values(conn, body)
        values["invoice_number"] = (body.invoice_number or "").strip() or next_invoice_number(conn)
        check_invoice_unique(conn, values["invoice_number"])
        columns = SALE_COLUMNS + ["invoice_number"]
        cursor = conn.execute(
            f"INSERT INTO sales({', '.join(columns)}) VALUES ({', '.join('?' * len(columns))})",
            [values[column] for column in columns],
        )
        ensure_stock(conn, values["product_id"])
        warning = stock_warning(conn, values["product_id"])
    return {"id": cursor.lastrowid, "invoice_number": values["invoice_number"], "warning": warning}


@api.put("/sales/{sale_id}")
def update_sale(sale_id: int, body: SaleIn):
    with get_conn() as conn:
        values = sale_values(conn, body)
        old = conn.execute("SELECT product_id, storno_of FROM sales WHERE id = ?", (sale_id,)).fetchone()
        if not old:
            raise HTTPException(status_code=404, detail="Vânzarea nu există.")
        if old["storno_of"] or has_returns(conn, sale_id):
            raise HTTPException(status_code=400, detail="Factura are o stornare legată de ea și nu se mai "
                                "poate modifica. Ștergeți stornarea întâi sau faceți încă un retur.")
        if body.invoice_number:
            values["invoice_number"] = body.invoice_number.strip()
            check_invoice_unique(conn, values["invoice_number"], sale_id)
        cursor = conn.execute(
            f"UPDATE sales SET {', '.join(f'{column} = ?' for column in values)} WHERE id = ?",
            [*values.values(), sale_id],
        )
        ensure_stock(conn, values["product_id"], old["product_id"])
        warning = stock_warning(conn, values["product_id"])
    return {"ok": True, "warning": warning}


class PaidIn(BaseModel):
    paid: bool


@api.patch("/sales/{sale_id}/paid")
def set_sale_paid(sale_id: int, body: PaidIn):
    with get_conn() as conn:
        if conn.execute("UPDATE sales SET paid = ? WHERE id = ?",
                        (int(body.paid), sale_id)).rowcount == 0:
            raise HTTPException(status_code=404, detail="Vânzarea nu există.")
    return {"ok": True}


def has_returns(conn, sale_id: int) -> bool:
    return conn.execute("SELECT 1 FROM sales WHERE storno_of = ?", (sale_id,)).fetchone() is not None


@api.post("/sales/{sale_id}/return", status_code=201)
def return_sale(sale_id: int, body: ReturnIn):
    """Stornare totală sau parțială: factură nouă, cu minus, legată de cea inițială."""
    with get_conn() as conn:
        original = conn.execute("SELECT * FROM sales WHERE id = ?", (sale_id,)).fetchone()
        if not original:
            raise HTTPException(status_code=404, detail="Vânzarea nu există.")
        if original["storno_of"] or original["amount"] < 0:
            raise HTTPException(status_code=400, detail="O stornare nu se poate storna din nou.")
        if body.date < original["date"]:
            raise HTTPException(status_code=400, detail="Returul nu poate fi înaintea facturii.")
        done = conn.execute("SELECT COALESCE(-SUM(quantity), 0) AS qty, COALESCE(-SUM(amount), 0) AS amount "
                            "FROM sales WHERE storno_of = ?", (sale_id,)).fetchone()
        reason = body.reason.strip()
        if original["product_id"]:
            left = original["quantity"] - done["qty"]
            quantity = body.quantity or left
            if quantity > left:
                raise HTTPException(status_code=400, detail=f"Se mai pot returna cel mult {left} buc. din "
                                    f"factura {original['invoice_number']}.")
            amount = -round(quantity * original["unit_price"] * (1 - (original["discount"] or 0) / 100), 2)
            values = {"quantity": -quantity, "unit_cost": original["unit_cost"], "unit_price": original["unit_price"],
                      "description": f"Retur {original['product']} ×{quantity}" + (f": {reason}" if reason else "")}
        else:
            left = round(original["amount"] - done["amount"], 2)
            amount_back = round(body.amount or left, 2)
            if amount_back > left + 0.001:
                raise HTTPException(status_code=400, detail=f"Se mai pot storna cel mult {left:.2f} lei din "
                                    f"factura {original['invoice_number']}.")
            amount = -amount_back
            share = amount_back / original["amount"]
            values = {"quantity": None, "unit_price": None, "unit_cost": -round((original["unit_cost"] or 0) * share, 2),
                      "description": f"Stornare {original['description']}" + (f": {reason}" if reason else "")}
        if left <= 0:
            raise HTTPException(status_code=400, detail="Factura a fost deja stornată complet.")
        number = next_invoice_number(conn)
        cursor = conn.execute(
            "INSERT INTO sales(date, description, product, quantity, amount, invoice_number, product_id, "
            "client_id, unit_price, unit_cost, due_date, paid, storno_of, discount) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (body.date, values["description"], original["product"], values["quantity"], amount, number,
             original["product_id"], original["client_id"], values["unit_price"], values["unit_cost"],
             body.date, original["paid"], sale_id, original["discount"] or 0))
    return {"id": cursor.lastrowid, "invoice_number": number, "amount": amount}


@api.delete("/sales/{sale_id}")
def delete_sale(sale_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT product_id FROM sales WHERE id = ?", (sale_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Vânzarea nu există.")
        if has_returns(conn, sale_id):
            raise HTTPException(status_code=400, detail="Factura are o stornare. Ștergeți întâi stornarea.")
        conn.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
        ensure_stock(conn, row["product_id"])  # ștergerea unui retur scoate marfa din nou din stoc
    return {"ok": True}


# ---------- Cheltuieli și categorii ----------

class ExpenseIn(BaseModel):
    date: str
    category: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=200)
    amount: float = Field(gt=0, le=MAX_AMOUNT)
    supplier: str = Field(default="", max_length=120)
    vat_kind: str = Field(default="standard", pattern=VAT_KIND_PATTERN)
    doc_number: str = Field(default="", max_length=40)

    @field_validator("date")
    @classmethod
    def check_date(cls, value):
        return valid_date(value)


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str = Field(default="#94a3b8", pattern=r"^#[0-9a-fA-F]{6}$")
    vat_kind: str = Field(default="standard", pattern=VAT_KIND_PATTERN)


@api.get("/expenses")
def list_expenses(month: str = Query(default_factory=calc.current_month, pattern=MONTH_PATTERN)):
    start, end = calc.month_bounds(month)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date DESC, id DESC",
            (start, end),
        ).fetchall()
    return [dict(row) for row in rows]


def check_category(conn, name: str) -> None:
    if not conn.execute("SELECT 1 FROM categories WHERE name = ?", (name,)).fetchone():
        raise HTTPException(status_code=400, detail=f"Categoria „{name}” nu există. Adăugați-o întâi.")


@api.post("/expenses", status_code=201)
def create_expense(body: ExpenseIn):
    with get_conn() as conn:
        check_category(conn, body.category)
        cursor = conn.execute(
            "INSERT INTO expenses(date, category, description, amount, supplier, vat_kind, doc_number) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (body.date, body.category, body.description, body.amount, body.supplier, body.vat_kind,
             body.doc_number.strip()),
        )
    return {"id": cursor.lastrowid}


@api.put("/expenses/{expense_id}")
def update_expense(expense_id: int, body: ExpenseIn):
    with get_conn() as conn:
        check_category(conn, body.category)
        cursor = conn.execute(
            "UPDATE expenses SET date = ?, category = ?, description = ?, amount = ?, supplier = ?, "
            "vat_kind = ? WHERE id = ?",
            (body.date, body.category, body.description, body.amount, body.supplier, body.vat_kind,
             expense_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Cheltuiala nu există.")
    return {"ok": True}


@api.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int):
    with get_conn() as conn:
        if conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,)).rowcount == 0:
            raise HTTPException(status_code=404, detail="Cheltuiala nu există.")
    return {"ok": True}


@api.get("/categories")
def list_categories():
    with get_conn() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT * FROM categories ORDER BY name = 'Altele', id")]


@api.post("/categories", status_code=201)
def create_category(body: CategoryIn):
    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM categories WHERE name = ?", (body.name,)).fetchone():
            raise HTTPException(status_code=400, detail="Categoria există deja.")
        cursor = conn.execute(
            "INSERT INTO categories(name, color, vat_kind) VALUES (?, ?, ?)",
            (body.name, body.color, body.vat_kind),
        )
    return {"id": cursor.lastrowid}


@api.delete("/categories/{category_id}")
def delete_category(category_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT name FROM categories WHERE id = ?", (category_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Categoria nu există.")
        used = conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE category = ?", (row["name"],)
        ).fetchone()[0]
        if used:
            raise HTTPException(
                status_code=400,
                detail=f"Categoria are {used} cheltuieli și nu poate fi ștearsă.",
            )
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    return {"ok": True}


# ---------- Produse, stoc și recepții de marfă ----------

class ProductIn(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(default="", max_length=100)
    supplier: str = Field(default="", max_length=120)
    sale_price: float = Field(ge=0, le=MAX_AMOUNT)
    cost: float = Field(ge=0, le=MAX_AMOUNT)
    min_stock: int = Field(default=5, ge=0)  # pragul de alertă propus de client
    opening_stock: int = Field(default=0, ge=0)
    active: bool = True


class PurchaseIn(BaseModel):
    date: str
    product_id: int
    quantity: int = Field(ge=1, le=1_000_000)
    unit_cost: float | None = Field(default=None, gt=0, le=MAX_AMOUNT)
    supplier: str = Field(default="", max_length=120)
    doc_number: str = Field(default="", max_length=40)
    paid: bool | None = None

    @field_validator("date")
    @classmethod
    def check_date(cls, value):
        return not_in_future(valid_date(value))


@api.get("/products")
def list_products():
    with get_conn() as conn:
        return inventory.products_overview(conn)


@api.post("/products", status_code=201)
def create_product(body: ProductIn):
    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM products WHERE code = ?", (body.code,)).fetchone():
            raise HTTPException(status_code=400, detail="Există deja un produs cu acest cod.")
        supplier_terms(conn, body.supplier)
        cursor = conn.execute(
            "INSERT INTO products(code, name, category, supplier, sale_price, cost, min_stock, "
            "opening_stock, opening_date, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (body.code, body.name, body.category, body.supplier, body.sale_price, body.cost,
             body.min_stock, body.opening_stock, date.today().isoformat(), int(body.active)),
        )
    return {"id": cursor.lastrowid}


@api.put("/products/{product_id}")
def update_product(product_id: int, body: ProductIn):
    with get_conn() as conn:
        clash = conn.execute("SELECT id FROM products WHERE code = ? AND id != ?",
                             (body.code, product_id)).fetchone()
        if clash:
            raise HTTPException(status_code=400, detail="Există deja un produs cu acest cod.")
        cursor = conn.execute(
            "UPDATE products SET code = ?, name = ?, category = ?, supplier = ?, sale_price = ?, "
            "cost = ?, min_stock = ?, active = ? WHERE id = ?",
            (body.code, body.name, body.category, body.supplier, body.sale_price, body.cost,
             body.min_stock, int(body.active), product_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Produsul nu există.")
    return {"ok": True}


@api.delete("/products/{product_id}")
def delete_product(product_id: int):
    with get_conn() as conn:
        used = conn.execute(
            "SELECT (SELECT COUNT(*) FROM sales WHERE product_id = ?) + "
            "(SELECT COUNT(*) FROM purchases WHERE product_id = ?)", (product_id, product_id),
        ).fetchone()[0]
        if used:
            raise HTTPException(status_code=400, detail="Produsul are vânzări sau recepții. "
                                "Îl puteți marca inactiv în loc să-l ștergeți.")
        if conn.execute("DELETE FROM products WHERE id = ?", (product_id,)).rowcount == 0:
            raise HTTPException(status_code=404, detail="Produsul nu există.")
    return {"ok": True}


@api.get("/purchases")
def list_purchases(month: str = Query(default_factory=calc.current_month, pattern=MONTH_PATTERN)):
    start, end = calc.month_bounds(month)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT pu.*, p.name AS product_name, p.code AS product_code, "
            "pu.quantity * pu.unit_cost AS value FROM purchases pu "
            "JOIN products p ON p.id = pu.product_id WHERE pu.date BETWEEN ? AND ? "
            "ORDER BY pu.date DESC, pu.id DESC", (start, end)).fetchall()
    return [dict(row) for row in rows]


@api.post("/purchases", status_code=201)
def create_purchase(body: PurchaseIn):
    """Recepție de marfă: crește stocul. Costul intră în profit când marfa se vinde."""
    with get_conn() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (body.product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Produsul nu există.")
        cost = body.unit_cost or product["cost"]
        doc = body.doc_number or f"NIR-{date.today():%y%m%d}-{body.product_id}"
        supplier = body.supplier or product["supplier"]
        terms = supplier_terms(conn, supplier)
        due = (date.fromisoformat(body.date) + timedelta(days=terms)).isoformat()
        paid = body.paid if body.paid is not None else terms == 0
        cursor = conn.execute(
            "INSERT INTO purchases(date, doc_number, supplier, product_id, quantity, unit_cost, due_date, paid) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (body.date, doc, supplier, product["id"], body.quantity, cost, due, int(paid)),
        )
        if cost != product["cost"]:  # costul de achiziție se actualizează la ultimul preț
            conn.execute("UPDATE products SET cost = ? WHERE id = ?", (cost, product["id"]))
    return {"id": cursor.lastrowid}


@api.delete("/purchases/{purchase_id}")
def delete_purchase(purchase_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT product_id FROM purchases WHERE id = ?", (purchase_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Recepția nu există.")
        conn.execute("DELETE FROM purchases WHERE id = ?", (purchase_id,))
        ensure_stock(conn, row["product_id"])
    return {"ok": True}


@api.patch("/purchases/{purchase_id}/paid")
def set_purchase_paid(purchase_id: int, body: PaidIn):
    with get_conn() as conn:
        if conn.execute("UPDATE purchases SET paid = ? WHERE id = ?",
                        (int(body.paid), purchase_id)).rowcount == 0:
            raise HTTPException(status_code=404, detail="Recepția nu există.")
    return {"ok": True}


# ---------- Furnizori și plăți ----------

def supplier_terms(conn, name: str) -> int:
    """Termenul de plată al furnizorului; un furnizor nou primește termenul implicit."""
    if not name:
        return 0
    row = conn.execute("SELECT payment_terms FROM suppliers WHERE name = ?", (name,)).fetchone()
    if row:
        return row["payment_terms"]
    conn.execute("INSERT INTO suppliers(name, payment_terms) VALUES (?, ?)", (name, DEFAULT_SUPPLIER_TERMS))
    return DEFAULT_SUPPLIER_TERMS


class SupplierIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    payment_terms: int = Field(default=DEFAULT_SUPPLIER_TERMS, ge=0, le=365)
    contact: str = Field(default="", max_length=200)
    lead_days: int = Field(default=5, ge=0, le=120)  # în câte zile livrează după comandă


@api.get("/suppliers")
def list_suppliers(month: str = Query(default_factory=calc.current_month, pattern=MONTH_PATTERN)):
    start, end = calc.month_bounds(month)
    with get_conn() as conn:
        due = {item["supplier"]: item for item in calc.payables(conn)["suppliers"]}
        rows = conn.execute(
            "SELECT s.*, "
            "COALESCE((SELECT SUM(quantity * unit_cost) FROM purchases pu WHERE pu.supplier = s.name "
            "AND pu.date BETWEEN ? AND ?), 0) AS month_purchases, "
            "COALESCE((SELECT SUM(quantity * unit_cost) FROM purchases pu WHERE pu.supplier = s.name), 0) "
            "AS total_purchases, "
            "(SELECT COUNT(*) FROM products p WHERE p.supplier = s.name) AS products "
            "FROM suppliers s ORDER BY total_purchases DESC, s.name", (start, end)).fetchall()
        return [{**dict(row), "payable": due.get(row["name"], {}).get("amount", 0),
                 "overdue": due.get(row["name"], {}).get("overdue", 0),
                 "due_soon": due.get(row["name"], {}).get("due_soon", 0)} for row in rows]


@api.post("/suppliers", status_code=201)
def create_supplier(body: SupplierIn):
    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM suppliers WHERE name = ?", (body.name,)).fetchone():
            raise HTTPException(status_code=400, detail="Furnizorul există deja.")
        cursor = conn.execute("INSERT INTO suppliers(name, payment_terms, contact, lead_days) VALUES (?, ?, ?, ?)",
                              (body.name, body.payment_terms, body.contact, body.lead_days))
    return {"id": cursor.lastrowid}


@api.put("/suppliers/{supplier_id}")
def update_supplier(supplier_id: int, body: SupplierIn):
    with get_conn() as conn:
        old = conn.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()
        if not old:
            raise HTTPException(status_code=404, detail="Furnizorul nu există.")
        if conn.execute("SELECT 1 FROM suppliers WHERE name = ? AND id != ?", (body.name, supplier_id)).fetchone():
            raise unique_name_error("un furnizor")
        conn.execute("UPDATE suppliers SET name = ?, payment_terms = ?, contact = ?, lead_days = ? WHERE id = ?",
                     (body.name, body.payment_terms, body.contact, body.lead_days, supplier_id))
        if old["name"] != body.name:  # redenumirea se vede peste tot
            for table in ("purchases", "products", "expenses"):
                conn.execute(f"UPDATE {table} SET supplier = ? WHERE supplier = ?", (body.name, old["name"]))
        if old["payment_terms"] != body.payment_terms:  # recepțiile neplătite primesc noul termen
            conn.execute("UPDATE purchases SET due_date = date(date, ?) WHERE supplier = ? AND paid = 0",
                         (f"+{body.payment_terms} days", body.name))
    return {"ok": True}


@api.get("/payables")
def get_payables():
    with get_conn() as conn:
        return calc.payables(conn)


@api.get("/inventory")
def get_inventory(month: str = Query(default_factory=calc.current_month, pattern=MONTH_PATTERN)):
    with get_conn() as conn:
        return inventory.inventory_month(conn, month)


# ---------- Clienți și încasări ----------

class ClientIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: str = Field(default="B2B", max_length=40)
    city: str = Field(default="", max_length=80)
    agent: str = Field(default="", max_length=80)
    payment_terms: int = Field(default=0, ge=0, le=365)


@api.get("/clients")
def list_clients(month: str = Query(default_factory=calc.current_month, pattern=MONTH_PATTERN)):
    start, end = calc.month_bounds(month)
    with get_conn() as conn:
        due = {item["client"]: item for item in calc.receivables(conn)["clients"]}
        rows = conn.execute(
            "SELECT c.*, "
            "COALESCE((SELECT SUM(amount) FROM sales s WHERE s.client_id = c.id "
            "AND s.date BETWEEN ? AND ?), 0) AS month_sales, "
            "COALESCE((SELECT SUM(amount) FROM sales s WHERE s.client_id = c.id), 0) AS total_sales, "
            "(SELECT COUNT(*) FROM sales s WHERE s.client_id = c.id) AS invoices, "
            "(SELECT MAX(date) FROM sales s WHERE s.client_id = c.id) AS last_sale "
            "FROM clients c ORDER BY total_sales DESC", (start, end)).fetchall()
        return [{**dict(row), "receivable": due.get(row["name"], {}).get("amount", 0),
                 "overdue": due.get(row["name"], {}).get("overdue", 0)} for row in rows]


@api.post("/clients", status_code=201)
def create_client(body: ClientIn):
    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM clients WHERE name = ?", (body.name,)).fetchone():
            raise HTTPException(status_code=400, detail="Clientul există deja.")
        cursor = conn.execute(
            "INSERT INTO clients(name, type, city, agent, payment_terms) VALUES (?, ?, ?, ?, ?)",
            (body.name, body.type, body.city, body.agent, body.payment_terms))
    return {"id": cursor.lastrowid}


@api.put("/clients/{client_id}")
def update_client(client_id: int, body: ClientIn):
    with get_conn() as conn:
        old = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
        if not old:
            raise HTTPException(status_code=404, detail="Clientul nu există.")
        if conn.execute("SELECT 1 FROM clients WHERE name = ? AND id != ?", (body.name, client_id)).fetchone():
            raise unique_name_error("un client")
        conn.execute(
            "UPDATE clients SET name = ?, type = ?, city = ?, agent = ?, payment_terms = ? WHERE id = ?",
            (body.name, body.type, body.city, body.agent, body.payment_terms, client_id))
        if old["payment_terms"] != body.payment_terms:  # facturile neîncasate primesc noul termen
            conn.execute("UPDATE sales SET due_date = date(date, ?) WHERE client_id = ? AND paid = 0",
                         (f"+{body.payment_terms} days", client_id))
    return {"ok": True}


@api.delete("/clients/{client_id}")
def delete_client(client_id: int):
    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM sales WHERE client_id = ?", (client_id,)).fetchone():
            raise HTTPException(status_code=400, detail="Clientul are facturi și nu poate fi șters.")
        if conn.execute("DELETE FROM clients WHERE id = ?", (client_id,)).rowcount == 0:
            raise HTTPException(status_code=404, detail="Clientul nu există.")
    return {"ok": True}


@api.get("/receivables")
def get_receivables():
    with get_conn() as conn:
        return calc.receivables(conn)


# ---------- Import din fișierele firmei ----------

@api.post("/import")
async def import_data(files: list[UploadFile] = File(...), replace: bool = Form(False)):
    contents = []
    for upload in files:
        data = await upload.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"„{upload.filename}” depășește 10 MB.")
        contents.append((upload.filename or "fisier", data))
    try:
        with get_conn() as conn:
            with audit.paused(conn):
                result = importer.import_files(conn, contents, replace=replace)
            audit.log_event(conn, f"Import din {', '.join(name for name, _ in contents)}"
                            + (" (datele vechi au fost înlocuite)" if replace else ""), "import")
            return result
    except sqlite3.DatabaseError as error:
        if closing.is_lock_error(error):
            raise HTTPException(status_code=400, detail="Importul nu a reușit: fișierul conține documente "
                                "dintr-o lună închisă. Nu s-a modificat nimic.")
        raise HTTPException(status_code=400, detail="Importul nu a reușit: fișierul pare stricat sau "
                            "nu este un Excel/CSV valid. Nu s-a modificat nimic.")
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=400, detail=f"Importul nu a reușit: {error}")
    except Exception:
        raise HTTPException(status_code=400, detail="Importul nu a reușit: fișierul pare stricat sau "
                            "nu este un Excel/CSV valid. Nu s-a modificat nimic.")


# ---------- Angajați și salarii ----------

class EmployeeIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(default="", max_length=120)
    hire_date: str
    end_date: str | None = None
    notes: str = Field(default="", max_length=500)
    hours_per_day: int = Field(default=8, ge=1, le=8)   # norma: 8 = normă întreagă, 4 = jumătate de normă
    leave_days: int = Field(default=21, ge=0, le=60)    # zile de concediu de odihnă pe an

    @field_validator("hire_date", "end_date")
    @classmethod
    def check_dates(cls, value):
        return valid_date(value)

    @model_validator(mode="after")
    def check_order(self):
        if self.end_date and self.end_date < self.hire_date:
            raise ValueError("Data plecării nu poate fi înaintea datei angajării.")
        return self


class NewEmployeeIn(EmployeeIn):
    gross: float = Field(gt=0)


class SalaryIn(BaseModel):
    gross: float = Field(gt=0)
    effective_from: str
    note: str = Field(default="", max_length=200)

    @field_validator("effective_from")
    @classmethod
    def check_date(cls, value):
        return valid_date(value)


def employee_details(conn, employee) -> dict:
    settings = fiscal.settings_for_month(conn, calc.current_month())
    history = [dict(row) for row in conn.execute(
        "SELECT * FROM salary_history WHERE employee_id = ? ORDER BY effective_from DESC, id DESC",
        (employee["id"],),
    )]
    gross = calc.gross_for_month(conn, employee, calc.current_month())
    current = history[0]["gross"] if history else 0
    year = calc.current_month()[:4]
    taken = conn.execute("SELECT COALESCE(SUM(days), 0) FROM absences WHERE employee_id = ? AND kind = 'odihna' "
                         "AND month LIKE ?", (employee["id"], f"{year}-%")).fetchone()[0]
    minimum = calc.min_wage_for(employee, settings)
    absences = [dict(row) for row in conn.execute(
        "SELECT * FROM absences WHERE employee_id = ? ORDER BY month DESC, id DESC LIMIT 24", (employee["id"],))]
    return {
        **dict(employee),
        "active": gross is not None,
        "salary": calc.salary_breakdown(gross if gross is not None else current, settings),
        "history": history,
        "leave_taken": taken,
        "leave_left": employee["leave_days"] - taken,
        "min_wage": minimum,
        "below_min_wage": bool(minimum and (gross if gross is not None else current) < minimum),
        "absences": absences,
    }


@api.get("/employees")
def list_employees():
    with get_conn() as conn:
        employees = conn.execute(
            "SELECT * FROM employees ORDER BY end_date IS NOT NULL, name"
        ).fetchall()
        return [employee_details(conn, employee) for employee in employees]


@api.post("/employees", status_code=201)
def create_employee(body: NewEmployeeIn):
    with get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO employees(name, role, hire_date, end_date, notes, hours_per_day, leave_days) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (body.name, body.role, body.hire_date, body.end_date, body.notes, body.hours_per_day, body.leave_days),
        )
        conn.execute(
            "INSERT INTO salary_history(employee_id, gross, effective_from, note) "
            "VALUES (?, ?, ?, 'Salariu inițial')",
            (cursor.lastrowid, body.gross, body.hire_date),
        )
    return {"id": cursor.lastrowid}


@api.put("/employees/{employee_id}")
def update_employee(employee_id: int, body: EmployeeIn):
    with get_conn() as conn:
        cursor = conn.execute(
            "UPDATE employees SET name = ?, role = ?, hire_date = ?, end_date = ?, notes = ?, hours_per_day = ?, "
            "leave_days = ? WHERE id = ?",
            (body.name, body.role, body.hire_date, body.end_date, body.notes, body.hours_per_day, body.leave_days,
             employee_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Angajatul nu există.")
    return {"ok": True}


@api.delete("/employees/{employee_id}")
def delete_employee(employee_id: int):
    with get_conn() as conn:
        employee = conn.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
        if not employee:
            raise HTTPException(status_code=404, detail="Angajatul nu există.")
        # Salariile din lunile trecute fac parte din rapoartele deja trimise: nu se șterg.
        if employee["hire_date"] < f"{calc.current_month()}-01":
            raise HTTPException(status_code=400, detail="Angajatul are salarii în lunile trecute. Completați "
                                "„Data plecării” în loc să-l ștergeți, ca rapoartele vechi să rămână corecte.")
        conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
    return {"ok": True}


@api.post("/employees/{employee_id}/salary", status_code=201)
def add_salary(employee_id: int, body: SalaryIn):
    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM employees WHERE id = ?", (employee_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Angajatul nu există.")
        conn.execute(
            "INSERT INTO salary_history(employee_id, gross, effective_from, note) "
            "VALUES (?, ?, ?, ?)",
            (employee_id, body.gross, body.effective_from, body.note or "Modificare salariu"),
        )
    return {"ok": True}


class AbsenceIn(BaseModel):
    month: str = Field(pattern=MONTH_PATTERN)
    kind: str = Field(pattern="^(odihna|medical|fara_plata)$")
    days: int = Field(ge=1, le=23)
    note: str = Field(default="", max_length=200)


@api.post("/employees/{employee_id}/absences", status_code=201)
def add_absence(employee_id: int, body: AbsenceIn):
    from .ro_calendar import working_days

    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM employees WHERE id = ?", (employee_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Angajatul nu există.")
        if conn.execute("SELECT 1 FROM month_locks WHERE month = ?", (body.month,)).fetchone():
            raise HTTPException(status_code=400, detail=CLOSED_MESSAGE)
        already = conn.execute("SELECT COALESCE(SUM(days), 0) FROM absences WHERE employee_id = ? AND month = ?",
                               (employee_id, body.month)).fetchone()[0]
        if already + body.days > working_days(body.month):
            raise HTTPException(status_code=400, detail=f"{calc.month_label(body.month)} are doar "
                                f"{working_days(body.month)} zile lucrătoare.")
        cursor = conn.execute("INSERT INTO absences(employee_id, month, kind, days, note) VALUES (?, ?, ?, ?, ?)",
                              (employee_id, body.month, body.kind, body.days, body.note))
    return {"id": cursor.lastrowid}


@api.delete("/absences/{absence_id}")
def delete_absence(absence_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT month FROM absences WHERE id = ?", (absence_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Absența nu există.")
        if conn.execute("SELECT 1 FROM month_locks WHERE month = ?", (row["month"],)).fetchone():
            raise HTTPException(status_code=400, detail=CLOSED_MESSAGE)
        conn.execute("DELETE FROM absences WHERE id = ?", (absence_id,))
    return {"ok": True}


@api.get("/salary-preview")
def salary_preview(gross: float = Query(gt=0)):
    with get_conn() as conn:
        return calc.salary_breakdown(gross, fiscal.settings_for_month(conn, calc.current_month()))


# ---------- Setări ----------

class SettingsIn(BaseModel):
    company_name: str = Field(min_length=1, max_length=120)
    owner_name: str = Field(default="", max_length=60)
    tax_regime: str = Field(pattern="^(profit|micro)$")
    vat_payer: bool = True
    payday: int = Field(default=10, ge=1, le=28)
    tax_loss_carried: float = Field(default=0, ge=0, le=MAX_AMOUNT)
    idle_lock_minutes: int = Field(default=15, ge=0, le=480)
    backup_extra_dir: str = Field(default="", max_length=400)


@api.get("/settings")
def read_settings():
    with get_conn() as conn:
        settings = get_settings(conn)
    result = {key: settings.get(key, default) for key, default in DEFAULT_SETTINGS.items()}
    result["backup_extra_status"] = settings.get("backup_extra_status", "")
    return result


@api.put("/settings")
def write_settings(body: SettingsIn):
    try:
        body.backup_extra_dir = backup.check_extra_dir(body.backup_extra_dir)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    with get_conn() as conn:
        old = get_settings(conn)
        changed = []
        for key, value in body.model_dump().items():
            text = ("1" if value else "0") if isinstance(value, bool) else str(value)
            if old.get(key) != text:
                changed.append(key)
            set_setting(conn, key, text)
        if changed:
            audit.log_event(conn, "Setările firmei au fost modificate (" + ", ".join(
                audit.SETTING_LABELS.get(key, key) for key in changed) + ")", "settings")
    return {"ok": True}


# ---------- Legislație fiscală ----------

@api.get("/fiscal")
def fiscal_overview():
    with get_conn() as conn:
        return fiscal.overview(conn)


@api.post("/fiscal/check")
async def fiscal_check():
    return await asyncio.to_thread(run_fiscal_check)


@api.post("/fiscal/seen")
def fiscal_seen():
    with get_conn() as conn:
        fiscal.mark_seen(conn)
    return {"ok": True}


# ---------- Asistentul AI (opțional) ----------

class AISettingsIn(BaseModel):
    enabled: bool
    api_key: str | None = Field(default=None, max_length=300)
    clear_key: bool = False


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=4000)


class ChatIn(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)


@api.get("/ai/status")
def ai_status():
    with get_conn() as conn:
        return assistant_ai.status(conn)


@api.put("/ai/settings")
def ai_settings(body: AISettingsIn):
    with get_conn() as conn:
        assistant_ai.save_settings(conn, body.enabled, body.api_key, body.clear_key)
        return assistant_ai.status(conn)


@api.post("/ai/chat")
def ai_chat(body: ChatIn):
    try:
        with get_conn() as conn:
            return assistant_ai.ask(conn, [m.model_dump() for m in body.messages])
    except assistant_ai.AIError as error:
        raise HTTPException(status_code=error.status, detail=str(error))


# ---------- Copii de siguranță ----------

@api.get("/backups")
def list_backups():
    return {"backups": backup.list_backups(), "folder": str(backup.backup_dir()), "keep": backup.KEEP}


@api.post("/backups", status_code=201)
def make_backup():
    return backup.create_backup("manual")


def after_restore(token: str | None) -> None:
    """După restaurare: schema adusă la zi și sesiunea curentă păstrată (nu e scos afară)."""
    init_db()
    with get_conn() as conn:
        if token:
            conn.execute("INSERT OR IGNORE INTO sessions(token) VALUES (?)", (token,))
        audit.log_event(conn, "Datele au fost restaurate dintr-o copie de siguranță", "backup")


@api.post("/backups/{name}/restore")
def restore_backup(name: str, testify_session: str | None = Cookie(default=None)):
    try:
        safety = backup.restore_from(backup.backup_path(name))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    after_restore(testify_session)
    return {"ok": True, "safety_backup": safety["name"]}


@api.post("/backups/upload")
async def restore_upload(file: UploadFile = File(...), testify_session: str | None = Cookie(default=None)):
    data = await file.read()
    if len(data) > 200 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Fișierul este prea mare.")
    try:
        safety = await asyncio.to_thread(backup.restore_upload, data, file.filename or "")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    after_restore(testify_session)
    return {"ok": True, "safety_backup": safety["name"]}


@api.get("/export/full")
def export_full():
    content = backup.full_export()
    return Response(content, media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="testify-export-complet-{date.today().isoformat()}.zip"'})


# ---------- Jurnal, închiderea lunii, calendar fiscal, trezorerie, obiective ----------

@api.get("/audit")
def get_audit(limit: int = Query(default=200, ge=1, le=2000), table: str | None = Query(default=None)):
    with get_conn() as conn:
        return audit.entries(conn, limit, table)


@api.get("/closing")
def closing_overview(month: str = Query(default_factory=lambda: calc.shift_month(calc.current_month(), -1),
                                        pattern=MONTH_PATTERN)):
    with get_conn() as conn:
        closed = closing.closed_months(conn)
        return {"month": month, "closed": closed, "is_closed": any(c["month"] == month for c in closed),
                "can_close": month < calc.current_month(), "checklist": closing.checklist(conn, month)}


@api.post("/closing/{month}")
def close_month(month: str):
    if not re.match(MONTH_PATTERN, month):
        raise HTTPException(status_code=422, detail="Luna nu este corectă.")
    with get_conn() as conn:
        try:
            snapshot = closing.close_month(conn, month)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))
    backup.create_backup(f"inchidere-{month}")
    return {"ok": True, "snapshot": snapshot}


@api.delete("/closing/{month}")
def reopen_month(month: str):
    with get_conn() as conn:
        try:
            closing.reopen_month(conn, month)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))
    return {"ok": True}


@api.get("/obligations")
def get_obligations(year: int = Query(default_factory=lambda: date.today().year, ge=2000, le=2100)):
    with get_conn() as conn:
        return {"items": obligations.calendar_items(conn), "profit_tax": obligations.profit_tax_quarters(conn, year),
                "regime": get_settings(conn).get("tax_regime", "profit")}


@api.patch("/obligations/{item_id}/paid")
def set_obligation_paid(item_id: str, body: PaidIn):
    if not re.match(r"^[a-z0-9-]{3,40}$", item_id, re.I):
        raise HTTPException(status_code=422, detail="Obligația nu este corectă.")
    with get_conn() as conn:
        obligations.set_paid(conn, item_id, body.paid)
    return {"ok": True}


class CashBalanceIn(BaseModel):
    balance: float = Field(ge=-MAX_AMOUNT, le=MAX_AMOUNT)


@api.get("/treasury")
def get_treasury(include_overdue: bool = False):
    with get_conn() as conn:
        return treasury.forecast(conn, include_overdue=include_overdue)


@api.put("/treasury/balance")
def set_cash_balance(body: CashBalanceIn):
    with get_conn() as conn:
        set_setting(conn, "cash_balance", str(round(body.balance, 2)))
        set_setting(conn, "cash_balance_date", date.today().isoformat())
    return {"ok": True}


class GoalIn(BaseModel):
    month: str = Field(pattern=r"^(default|\d{4}-(0[1-9]|1[0-2]))$")
    revenue: float | None = Field(default=None, gt=0, le=MAX_AMOUNT)
    profit: float | None = Field(default=None, ge=-MAX_AMOUNT, le=MAX_AMOUNT)


@api.get("/goals")
def get_goals(month: str = Query(default_factory=calc.current_month, pattern=MONTH_PATTERN)):
    with get_conn() as conn:
        general = conn.execute("SELECT * FROM goals WHERE month = 'default'").fetchone()
        specific = conn.execute("SELECT * FROM goals WHERE month = ?", (month,)).fetchone()
        return {"default": dict(general) if general else None, "month": dict(specific) if specific else None,
                "effective": calc.goals_for(conn, month)}


@api.put("/goals")
def save_goal(body: GoalIn):
    with get_conn() as conn:
        if body.revenue is None and body.profit is None:
            conn.execute("DELETE FROM goals WHERE month = ?", (body.month,))
        else:
            conn.execute("INSERT INTO goals(month, revenue, profit) VALUES (?, ?, ?) ON CONFLICT(month) DO UPDATE "
                         "SET revenue = excluded.revenue, profit = excluded.profit",
                         (body.month, body.revenue, body.profit))
    return {"ok": True}


# ---------- Bon / factură citite cu AI ----------

@api.post("/ai/receipt")
async def ai_receipt(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Fișierul depășește 10 MB. Faceți o poză mai mică.")
    media_type = (file.content_type or "").split(";")[0].strip().lower()
    if media_type == "image/jpg":
        media_type = "image/jpeg"
    def read():  # conexiunea SQLite se deschide în același fir în care e folosită
        with get_conn() as conn:
            return assistant_ai.read_receipt(conn, data, media_type)

    try:
        return await asyncio.to_thread(read)
    except assistant_ai.AIError as error:
        raise HTTPException(status_code=error.status, detail=str(error))


# ---------- e-Factura (SPV) ----------

@api.post("/efactura/preview")
async def efactura_preview(files: list[UploadFile] = File(...)):
    contents = []
    for upload in files:
        data = await upload.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"„{upload.filename}” depășește 10 MB.")
        contents.append((upload.filename or "factura.xml", data))
    try:
        with get_conn() as conn:
            return efactura.preview(conn, contents)
    except efactura.EFacturaError as error:
        raise HTTPException(status_code=400, detail=str(error))


class EFacturaLineIn(BaseModel):
    name: str = Field(max_length=300)
    quantity: float = Field(gt=0, le=1_000_000)
    net: float = Field(ge=-MAX_AMOUNT, le=MAX_AMOUNT)
    vat_rate: float = Field(ge=0, le=100)
    target: str = Field(pattern="^(product|expense|skip)$")
    product_id: int | None = None
    category: str | None = Field(default=None, max_length=100)
    vat_kind: str | None = Field(default=None, pattern=VAT_KIND_PATTERN)


class EFacturaInvoiceIn(BaseModel):
    number: str = Field(max_length=60)
    date: str
    due_date: str | None = None
    supplier: str = Field(min_length=1, max_length=200)
    lines: list[EFacturaLineIn] = Field(min_length=1, max_length=500)

    @field_validator("date", "due_date")
    @classmethod
    def check_dates(cls, value):
        return valid_date(value)


class EFacturaSaveIn(BaseModel):
    invoices: list[EFacturaInvoiceIn] = Field(min_length=1, max_length=200)


@api.post("/efactura/save")
def efactura_save(body: EFacturaSaveIn):
    with get_conn() as conn:
        try:
            result = efactura.save(conn, [i.model_dump() for i in body.invoices], supplier_terms)
        except efactura.EFacturaError as error:
            raise HTTPException(status_code=400, detail=str(error))
        product_ids = [l.product_id for i in body.invoices for l in i.lines if l.target == "product"]
        ensure_stock(conn, *product_ids)
        if result["purchases"] or result["expenses"]:
            audit.log_event(conn, f"Import e-Factura: {len(body.invoices) - result['skipped']} facturi "
                            f"({result['purchases']} recepții, {result['expenses']} cheltuieli)", "import")
    return result


# ---------- Decizii: simulator, comenzi, analiză ----------

class SimulateIn(BaseModel):
    month: str = Field(pattern=MONTH_PATTERN)
    price_pct: float = Field(default=0, ge=-50, le=100)
    volume_pct: float = Field(default=0, ge=-90, le=300)
    cost_pct: float = Field(default=0, ge=-50, le=100)
    raise_pct: float = Field(default=0, ge=-30, le=100)
    new_employees: list[float] = Field(default_factory=list, max_length=10)
    extra_expenses: float = Field(default=0, ge=-MAX_AMOUNT, le=MAX_AMOUNT)

    @field_validator("new_employees")
    @classmethod
    def check_salaries(cls, value):
        if any(not 0 < gross <= 100_000 for gross in value):
            raise ValueError("Salariul brut al angajatului nou trebuie să fie între 1 și 100.000 lei.")
        return value


@api.post("/simulate")
def simulate(body: SimulateIn):
    with get_conn() as conn:
        return planning.simulate(conn, body.month, body.price_pct, body.volume_pct, body.cost_pct,
                                 body.raise_pct, body.new_employees, body.extra_expenses)


@api.get("/reorder")
def get_reorder():
    with get_conn() as conn:
        return planning.reorder(conn)


@api.get("/analysis")
def get_analysis(month: str = Query(default_factory=calc.current_month, pattern=MONTH_PATTERN),
                 months: int = Query(default=3, ge=1, le=12)):
    with get_conn() as conn:
        return planning.analysis(conn, month, months)


@api.post("/demo")
def reload_demo():
    backup.create_backup("inainte-de-demo")
    with get_conn() as conn:
        conn.execute("DELETE FROM month_locks")
        with audit.paused(conn):
            result = demo.load_demo_data(conn)
        audit.log_event(conn, "Au fost încărcate datele firmei din T3 2026 (datele vechi au fost înlocuite)",
                        "import")
        return result


app.include_router(api)
