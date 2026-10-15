"""Regresii pentru problemele găsite la verificarea finală a codului (corectitudine și securitate)."""

import os
import shutil
import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import auth

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data" / "efactura" / "factura_conex_CNX-24518.xml"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("TESTIFY_FISCAL_FEED", "")
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("TESTIFY_DB", os.path.join(tmp, "test.db"))
        from app.main import app
        auth.limiter.reset()
        with TestClient(app, raise_server_exceptions=False) as test_client:
            test_client.post("/api/auth/setup", json={"password": "parola123", "demo": True})
            yield test_client


def backups_folder() -> Path:
    from app import backup
    return backup.backup_dir()


# ---------- Copii de siguranță ----------

def test_restoring_the_oldest_of_30_backups_keeps_the_data(client):
    real = client.post("/api/backups").json()["name"]
    folder = backups_folder()
    for old in folder.glob("testify-*.db"):
        if old.name != real:
            old.unlink()
    for i in range(30):  # 30 de copii mai vechi: următoarea copie o șterge pe cea mai veche
        shutil.copy(folder / real, folder / f"testify-2000-01-01_00-00-{i:02d}.db")
    response = client.post("/api/backups/testify-2000-01-01_00-00-00.db/restore")
    assert response.status_code == 200
    assert client.get("/api/summary?month=2026-09").json()["sales_count"] == 114
    assert client.get("/api/auth/status").json()["setup_done"] is True


def test_backup_without_password_is_refused(client):
    empty = backups_folder() / "testify-2000-01-01_00-00-00.db"
    conn = sqlite3.connect(empty)
    conn.executescript("CREATE TABLE settings(key, value); CREATE TABLE sales(id); CREATE TABLE expenses(id); "
                       "CREATE TABLE products(id);")
    conn.close()
    response = client.post(f"/api/backups/{empty.name}/restore")
    assert response.status_code == 400 and "goală" in response.json()["detail"]


def test_backups_hold_no_api_key_or_sessions_and_restore_keeps_the_key(client):
    client.put("/api/ai/settings", json={"enabled": True, "api_key": "sk-ant-secret-1234567890"})
    name = client.post("/api/backups").json()["name"]
    data = (backups_folder() / name).read_bytes()
    assert b"sk-ant-secret" not in data
    conn = sqlite3.connect(backups_folder() / name)
    assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    conn.close()
    assert client.post(f"/api/backups/{name}/restore").status_code == 200
    assert client.get("/api/ai/status").json()["has_key"] is True


def test_month_closing_backup_can_be_restored(client):
    client.post("/api/closing/2026-09")
    name = next(b["name"] for b in client.get("/api/backups").json()["backups"] if "inchidere" in b["name"])
    assert client.post(f"/api/backups/{name}/restore").status_code == 200


# ---------- Luna închisă ----------

def test_closed_month_still_allows_collecting_and_terms_but_not_amounts(client):
    client.post("/api/closing/2026-09")
    sale = next(s for s in client.get("/api/sales?month=2026-09").json() if not s["paid"])
    assert client.patch(f"/api/sales/{sale['id']}/paid", json={"paid": True}).status_code == 200
    purchase = client.get("/api/purchases?month=2026-09").json()[0]
    assert client.patch(f"/api/purchases/{purchase['id']}/paid", json={"paid": True}).status_code == 200
    alfa = next(c for c in client.get("/api/clients").json() if c["name"] == "Alfa Office SRL")
    assert client.put(f"/api/clients/{alfa['id']}", json={"name": alfa["name"], "payment_terms": 45}).status_code == 200
    supplier = client.get("/api/suppliers").json()[0]
    assert client.put(f"/api/suppliers/{supplier['id']}", json={**supplier, "payment_terms": 20}).status_code == 200
    from app.db import get_conn
    with pytest.raises(sqlite3.IntegrityError), get_conn() as conn:
        conn.execute("UPDATE sales SET amount = amount + 1 WHERE id = ?", (sale["id"],))


def test_closed_month_blocks_employee_dates_and_regime_change(client):
    client.post("/api/closing/2026-08")
    employee = client.get("/api/employees").json()[0]
    moved = client.put(f"/api/employees/{employee['id']}", json={"name": employee["name"], "hire_date": "2026-09-01"})
    assert moved.status_code == 400
    settings = client.get("/api/settings").json()
    regime = client.put("/api/settings", json={"company_name": settings["company_name"], "tax_regime": "micro"})
    assert regime.status_code == 400


# ---------- Stoc, vânzări, cheltuieli ----------

def test_new_product_counts_older_receipts(client):
    product = client.post("/api/products", json={"code": "NEW1", "name": "Produs nou", "sale_price": 50,
                                                 "cost": 20}).json()
    client.post("/api/purchases", json={"date": "2026-10-10", "product_id": product["id"], "quantity": 10})
    stock = next(p for p in client.get("/api/products").json() if p["id"] == product["id"])["stock"]
    assert stock == 10


def test_editing_a_sale_keeps_its_historical_cost(client):
    sale = next(s for s in client.get("/api/sales?month=2026-09").json() if s["product_id"])
    client.post("/api/purchases", json={"date": "2026-10-10", "product_id": sale["product_id"], "quantity": 5,
                                        "unit_cost": sale["unit_cost"] * 2})
    client.put(f"/api/sales/{sale['id']}", json={"date": sale["date"], "product_id": sale["product_id"],
                                                 "quantity": sale["quantity"], "unit_price": sale["unit_price"],
                                                 "description": "alt text", "invoice_number": sale["invoice_number"]})
    after = next(s for s in client.get("/api/sales?month=2026-09").json() if s["id"] == sale["id"])
    assert after["unit_cost"] == sale["unit_cost"]


def test_expense_edit_saves_document_number(client):
    expense = client.post("/api/expenses", json={"date": "2026-10-10", "category": "Chirie", "amount": 10,
                                                 "doc_number": "A1"}).json()
    client.put(f"/api/expenses/{expense['id']}", json={"date": "2026-10-10", "category": "Chirie", "amount": 10,
                                                       "doc_number": "B2"})
    row = next(e for e in client.get("/api/expenses?month=2026-10").json() if e["id"] == expense["id"])
    assert row["doc_number"] == "B2"


def test_parallel_invoices_get_unique_numbers(client):
    product = client.get("/api/products").json()[0]
    client.post("/api/purchases", json={"date": "2026-10-10", "product_id": product["id"], "quantity": 100})

    def sell(_):
        return client.post("/api/sales", json={"date": "2026-10-14", "product_id": product["id"], "quantity": 1})

    with ThreadPoolExecutor(max_workers=10) as pool:
        responses = list(pool.map(sell, range(20)))
    numbers = [r.json()["invoice_number"] for r in responses if r.status_code == 201]
    assert len(numbers) == len(set(numbers)) and len(numbers) >= 15


def test_settings_save_with_missing_backup_folder(client, tmp_path):
    settings = client.get("/api/settings").json()
    body = {"company_name": settings["company_name"], "tax_regime": "profit", "backup_extra_dir": str(tmp_path)}
    assert client.put("/api/settings", json=body).status_code == 200
    tmp_path.rmdir()  # stickul a fost scos
    assert client.put("/api/settings", json={**body, "company_name": "Testify SRL"}).status_code == 200


# ---------- e-Factura ----------

def test_efactura_returns_and_credit_notes_never_go_into_stock(client):
    xml = SAMPLE.read_text(encoding="utf-8").replace(
        '<cbc:InvoicedQuantity unitCode="H87">5</cbc:InvoicedQuantity>\n    <cbc:LineExtensionAmount currencyID="RON">375.00',
        '<cbc:InvoicedQuantity unitCode="H87">-2</cbc:InvoicedQuantity>\n    <cbc:LineExtensionAmount currencyID="RON">-170.00')
    xml = xml.replace("Cutii carton ambalaj 40x30", "Hub USB-C 7 in 1")
    invoice = client.post("/api/efactura/preview", files=[("files", ("f.xml", xml.encode(), "text/xml"))]).json()["invoices"][0]
    returned = invoice["lines"][3]
    assert returned["target"] == "expense" and returned["can_stock"] is False
    assert client.post("/api/efactura/save", json={"invoices": [invoice]}).status_code == 200
    forced = {**invoice, "number": "X-2", "lines": [{**returned, "target": "product", "product_id": 1}]}
    response = client.post("/api/efactura/save", json={"invoices": [forced]})
    assert response.status_code == 400 and "stoc" in response.json()["detail"]


def test_efactura_entities_are_refused_anywhere_in_the_file(client):
    padding = b"<!--" + b"x" * 6000 + b"-->"
    evil = b'<?xml version="1.0"?>' + padding + b'<!DOCTYPE x [<!ENTITY a "boom">]><Invoice>&a;</Invoice>'
    response = client.post("/api/efactura/preview", files=[("files", ("e.xml", evil, "text/xml"))])
    assert response.status_code == 400


# ---------- Siguranță ----------

def test_limiter_is_per_device():
    limiter = auth.AttemptLimiter()
    for _ in range(5):
        limiter.failed("192.168.1.50")
    with pytest.raises(Exception):
        limiter.check("192.168.1.50")
    limiter.check("127.0.0.1")  # proprietarul, de pe calculatorul lui, nu e blocat


def test_parallel_wrong_pins_still_lock_after_three(client):
    client.put("/api/auth/pin", json={"current": "parola123", "pin": "4826"})
    client.post("/api/auth/logout")
    auth.limiter.reset()

    def guess(pin):
        return client.post("/api/auth/pin-login", json={"pin": pin}).status_code

    with ThreadPoolExecutor(max_workers=20) as pool:
        list(pool.map(guess, [f"{i:04d}" for i in range(1000, 1020)]))
    auth.limiter.reset()
    assert client.post("/api/auth/pin-login", json={"pin": "4826"}).status_code == 400  # PIN blocat


def test_password_change_logs_out_other_devices(client):
    phone_cookie = client.cookies.get("testify_session")
    client.cookies.clear()
    client.post("/api/auth/login", json={"password": "parola123"})
    assert client.post("/api/auth/change-password", json={"current": "parola123", "new": "parolanoua1"}).status_code == 200
    assert client.get("/api/dashboard").status_code == 200  # dispozitivul care a schimbat parola rămâne
    client.cookies.clear()
    client.cookies.set("testify_session", phone_cookie)
    assert client.get("/api/dashboard").status_code == 401


def test_sessions_are_stored_hashed(client):
    from app.db import get_conn
    token = client.cookies.get("testify_session")
    with get_conn() as conn:
        stored = [row[0] for row in conn.execute("SELECT token FROM sessions")]
    assert token not in stored and auth.token_hash(token) in stored


def test_unknown_host_names_are_refused(client):
    assert client.get("/api/auth/status", headers={"host": "evil.example.com"}).status_code == 400
    assert client.get("/api/auth/status", headers={"host": "192.168.1.20:8000"}).status_code == 200
    assert client.get("/api/auth/status", headers={"host": "localhost:8000"}).status_code == 200


def test_first_setup_only_from_the_office_computer(monkeypatch):
    monkeypatch.setenv("TESTIFY_FISCAL_FEED", "")
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("TESTIFY_DB", os.path.join(tmp, "fresh.db"))
        from app.main import app
        with TestClient(app, client=("192.168.1.77", 50000)) as phone:
            response = phone.post("/api/auth/setup", json={"password": "parola123"})
            assert response.status_code == 403
        with TestClient(app) as office:
            assert office.post("/api/auth/setup", json={"password": "scurt"}).status_code == 422  # minim 8
            assert office.post("/api/auth/setup", json={"password": "parola123"}).status_code == 200
