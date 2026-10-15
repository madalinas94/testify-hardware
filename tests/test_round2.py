"""Runda 2: e-Factura, simulator, comenzi recomandate, analiză, scrisoarea lunii, bon citit cu AI,
PIN, blocare după inactivitate și copia în folderul suplimentar."""

import io
import json
import os
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import assistant_ai

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data" / "efactura" / "factura_conex_CNX-24518.xml"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("TESTIFY_FISCAL_FEED", "")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("TESTIFY_DB", os.path.join(tmp, "test.db"))
        from app.main import app
        with TestClient(app, raise_server_exceptions=False) as test_client:
            test_client.post("/api/auth/setup", json={"password": "parola123", "demo": True})
            yield test_client


def preview(client, name="f.xml", content=None):
    return client.post("/api/efactura/preview", files=[("files", (name, content or SAMPLE.read_bytes(), "text/xml"))])


# ---------- e-Factura ----------

def test_efactura_preview_matches_products_and_categories(client):
    invoice = preview(client).json()["invoices"][0]
    assert invoice["supplier"] == "Conex Distributie SRL" and invoice["total"] == 5953.20
    targets = [(line["target"], line.get("product_name") or line.get("category")) for line in invoice["lines"]]
    assert targets == [("product", "Hub USB-C 7in1"), ("product", "Incarcator GaN 65W"),
                       ("expense", "Transport"), ("expense", "Ambalaje și consumabile")]


def test_efactura_save_adds_stock_expenses_and_skips_duplicates(client):
    hub = next(p for p in client.get("/api/products").json() if p["code"] == "P101")
    invoice = preview(client).json()["invoices"][0]
    result = client.post("/api/efactura/save", json={"invoices": [invoice]}).json()
    assert result == {"purchases": 2, "expenses": 2, "skipped": 0}
    after = next(p for p in client.get("/api/products").json() if p["code"] == "P101")
    assert after["stock"] == hub["stock"] + 30
    receipt = next(x for x in client.get("/api/purchases?month=2026-10").json() if x["doc_number"] == "CNX-24518")
    assert receipt["due_date"] == "2026-11-11" and not receipt["paid"]
    assert client.post("/api/efactura/save", json={"invoices": [invoice]}).json()["skipped"] == 1
    assert preview(client).json()["invoices"][0]["duplicate"] is True


def test_efactura_zip_from_spv_and_bad_files(client):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("4123456789.xml", SAMPLE.read_bytes())
        archive.writestr("semnatura_4123456789.xml", b"<Signature/>")
    assert len(preview(client, "spv.zip", buffer.getvalue()).json()["invoices"]) == 1
    assert preview(client, "x.xml", b"nu e xml").status_code == 400
    evil = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a SYSTEM "file:///etc/passwd">]><Invoice>&a;</Invoice>'
    assert preview(client, "evil.xml", evil).status_code == 400


def test_efactura_credit_note_becomes_negative_expense(client):
    credit = SAMPLE.read_text(encoding="utf-8").replace("<Invoice ", "<CreditNote ").replace("</Invoice>", "</CreditNote>") \
        .replace("Invoice-2", "CreditNote-2").replace("InvoiceLine", "CreditNoteLine") \
        .replace("InvoicedQuantity", "CreditedQuantity").replace("CNX-24518", "CNX-NC-7")
    invoice = preview(client, "nc.xml", credit.encode()).json()["invoices"][0]
    assert invoice["credit_note"] and invoice["total"] < 0
    assert all(line["target"] == "expense" for line in invoice["lines"])


# ---------- Simulator, comenzi, analiză, scrisoare ----------

def test_simulator_hire_and_price(client):
    base = client.post("/api/simulate", json={"month": "2026-09"}).json()
    assert all(abs(v) < 0.01 for v in base["delta"].values())
    hire = client.post("/api/simulate", json={"month": "2026-09", "new_employees": [5000]}).json()
    assert hire["delta"]["payroll_cost"] == 5113
    price = client.post("/api/simulate", json={"month": "2026-09", "price_pct": 10}).json()
    assert price["delta"]["revenue"] == pytest.approx(base["scenario"]["revenue"] * 0.10, abs=1)
    assert price["delta"]["profit"] > 0 and any("Doar din prețuri" in n for n in price["notes"])
    assert client.post("/api/simulate", json={"month": "2026-09", "price_pct": 500}).status_code == 422


def test_reorder_recommendations(client):
    data = client.get("/api/reorder").json()
    assert data["count"] > 0
    line = data["groups"][0]["lines"][0]
    assert line["quantity"] > 0 and line["order_by"] and line["supplier"]
    assert "Vă rugăm să ne trimiteți" in data["groups"][0]["message"]


def test_analysis_pareto(client):
    data = client.get("/api/analysis?month=2026-09&months=3").json()
    assert data["clients"][0]["class"] == "A" and data["clients"][-1]["cumulative"] == pytest.approx(100, abs=0.1)
    assert 1 <= data["top_count"] <= len(data["clients"]) and data["notes"]


def test_letter_pdf(client):
    response = client.get("/api/export/letter?month=2026-09")
    assert response.status_code == 200 and response.content.startswith(b"%PDF")


# ---------- Bon citit cu AI ----------

def test_receipt_reading_with_fake_claude(client, monkeypatch):
    image = b"\x89PNG fake"
    assert client.post("/api/ai/receipt", files={"file": ("bon.png", image, "image/png")}).status_code == 400
    client.put("/api/ai/settings", json={"enabled": True, "api_key": "sk-ant-test-1234567890abcd"})
    calls = []
    extracted = {"date": "2026-10-14", "supplier": "OMV Petrom SA", "document_number": "B-1029", "total": 302.5,
                 "net": 250.0, "vat": 52.5, "vat_kind": "standard", "category": "Combustibil și auto",
                 "description": "Motorină 40 litri", "confidence": "high", "notes": ""}

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(stop_reason="end_turn", model=assistant_ai.AI_MODEL,
                               content=[SimpleNamespace(type="text", text=json.dumps(extracted))])

    monkeypatch.setattr(assistant_ai, "make_client",
                        lambda conn: SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create))))
    result = client.post("/api/ai/receipt", files={"file": ("bon.png", image, "image/png")}).json()
    assert result["category"] == "Combustibil și auto" and result["consistent"] is True
    call = calls[0]
    assert call["model"] == "claude-opus-5-5" and call["output_config"]["format"]["type"] == "json_schema"
    assert call["messages"][0]["content"][0]["type"] == "image"
    pdf = client.post("/api/ai/receipt", files={"file": ("f.pdf", b"%PDF-1.4", "application/pdf")})
    assert pdf.status_code == 200 and calls[1]["messages"][0]["content"][0]["type"] == "document"
    assert client.post("/api/ai/receipt", files={"file": ("x.txt", b"x", "text/plain")}).status_code == 400


# ---------- Siguranță ----------

def test_pin_login_and_lockout(client):
    assert client.put("/api/auth/pin", json={"current": "gresit", "pin": "4826"}).status_code == 400
    assert client.put("/api/auth/pin", json={"current": "parola123", "pin": "4826"}).status_code == 200
    client.post("/api/auth/logout")
    assert client.get("/api/auth/status").json()["has_pin"] is True
    assert client.post("/api/auth/pin-login", json={"pin": "4826"}).status_code == 200
    client.post("/api/auth/logout")
    for _ in range(3):
        client.post("/api/auth/pin-login", json={"pin": "1111"})
    assert client.post("/api/auth/pin-login", json={"pin": "4826"}).status_code == 400  # PIN blocat
    assert client.post("/api/auth/login", json={"password": "parola123"}).status_code == 200
    assert client.get("/api/auth/status").json()["has_pin"] is True  # reactivat după parolă


def test_idle_session_expires(client):
    from app.db import get_conn

    assert client.get("/api/dashboard").status_code == 200
    with get_conn() as conn:
        conn.execute("UPDATE sessions SET last_seen = datetime('now', '-20 minutes')")
    assert client.get("/api/dashboard").status_code == 401


def test_backup_extra_folder(client, tmp_path):
    settings = client.get("/api/settings").json()
    body = {"company_name": settings["company_name"], "tax_regime": "profit", "backup_extra_dir": "/nu/exista/deloc"}
    assert client.put("/api/settings", json=body).status_code == 400
    body["backup_extra_dir"] = str(tmp_path)
    assert client.put("/api/settings", json=body).status_code == 200
    client.post("/api/backups")
    assert list((tmp_path / "TestifyBackups").glob("testify-*.db"))
    assert client.get("/api/settings").json()["backup_extra_status"].endswith("ok")
