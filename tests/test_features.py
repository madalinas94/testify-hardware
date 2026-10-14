"""Funcțiile „end to end”: backup, închiderea lunii, jurnal, stornare, calendar fiscal, trezorerie,
impozit pe profit trimestrial, concedii, salariu minim și obiective."""

import io
import os
import tempfile
import zipfile
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import obligations, ro_calendar


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("TESTIFY_FISCAL_FEED", "")
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("TESTIFY_DB", os.path.join(tmp, "test.db"))
        from app.main import app
        with TestClient(app, raise_server_exceptions=False) as test_client:
            test_client.post("/api/auth/setup", json={"password": "parola123", "demo": True})
            yield test_client


def hub(client):
    return next(p for p in client.get("/api/products").json() if p["code"] == "P101")


# ---------- Calendar ----------

def test_orthodox_easter_and_holidays():
    assert ro_calendar.orthodox_easter(2025) == date(2025, 4, 20)
    assert ro_calendar.orthodox_easter(2026) == date(2026, 4, 12)
    assert ro_calendar.working_days("2026-10") == 22
    assert ro_calendar.working_days("2026-12") == 21  # 1, 25 decembrie
    # 25 octombrie 2026 e duminică: termenul se mută luni, 26.
    assert ro_calendar.deadline(2026, 10) == date(2026, 10, 26)


# ---------- Backup ----------

def test_daily_backup_exists_and_restore_brings_data_back(client):
    backups = client.get("/api/backups").json()["backups"]
    assert backups, "copia zilnică se face la pornire"
    name = client.post("/api/backups").json()["name"]
    sale = client.get("/api/sales?month=2026-09").json()[-1]
    assert client.delete(f"/api/sales/{sale['id']}").status_code == 200
    before = client.get("/api/summary?month=2026-09").json()["sales_count"]
    response = client.post(f"/api/backups/{name}/restore")
    assert response.status_code == 200 and "inainte-de-restaurare" in response.json()["safety_backup"]
    # sesiunea rămâne valabilă, iar vânzarea ștearsă a revenit
    assert client.get("/api/summary?month=2026-09").json()["sales_count"] == before + 1


def test_restore_rejects_bad_names_and_files(client):
    assert client.post("/api/backups/..%2Ftest.db/restore").status_code in (400, 404)
    response = client.post("/api/backups/upload", files={"file": ("x.db", b"nu e baza", "application/octet-stream")})
    assert response.status_code == 400


def test_full_export_restores_and_hides_ai_key(client):
    client.put("/api/ai/settings", json={"enabled": True, "api_key": "sk-ant-secret"})
    content = client.get("/api/export/full").content
    archive = zipfile.ZipFile(io.BytesIO(content))
    assert {"testify.db", "toate-datele.xlsx", "CITESTE.txt"} <= set(archive.namelist())
    assert b"sk-ant-secret" not in archive.read("testify.db")
    response = client.post("/api/backups/upload", files={"file": ("export.zip", content, "application/zip")})
    assert response.status_code == 200
    assert client.get("/api/summary?month=2026-09").json()["sales_count"] == 114


# ---------- Închiderea lunii și jurnalul ----------

def test_closed_month_cannot_be_changed_until_reopened(client):
    overview = client.get("/api/closing?month=2026-09").json()
    assert overview["can_close"] and overview["checklist"]
    assert client.post("/api/closing/2026-09").status_code == 200
    sale = client.get("/api/sales?month=2026-09").json()[0]
    for response in [
        client.delete(f"/api/sales/{sale['id']}"),
        client.post("/api/sales", json={"date": "2026-09-30", "description": "x", "amount": 5}),
        client.post("/api/expenses", json={"date": "2026-09-30", "category": "Altele", "amount": 5}),
    ]:
        assert response.status_code == 400 and "închisă" in response.json()["detail"]
    assert client.post(f"/api/closing/{date.today():%Y-%m}").status_code == 400  # luna în curs
    assert client.delete("/api/closing/2026-09").status_code == 200
    assert client.delete(f"/api/sales/{sale['id']}").status_code == 200


def test_closed_month_blocks_import_replace(client):
    client.post("/api/closing/2026-08")
    response = client.post("/api/import", files=[("files", ("vanzari.csv", b"data,suma\n", "text/csv"))],
                           data={"replace": "true"})
    assert response.status_code == 400


def test_audit_log_records_changes(client):
    assert client.get("/api/audit").json()[0]["table"] == "import"  # datele demo: un singur rând
    expense = client.post("/api/expenses", json={"date": "2026-10-10", "category": "Chirie", "amount": 100}).json()
    client.put(f"/api/expenses/{expense['id']}", json={"date": "2026-10-10", "category": "Chirie", "amount": 150})
    client.delete(f"/api/expenses/{expense['id']}")
    log = client.get("/api/audit?limit=3").json()
    assert [e["action"] for e in log] == ["delete", "update", "insert"]
    assert "suma: 100 → 150" in log[1]["details"]
    assert log[0]["text"] == "Cheltuiala Chirie ștearsă"


# ---------- Stornare și reduceri ----------

def test_discount_reduces_amount(client):
    product = hub(client)
    sale = client.post("/api/sales", json={"date": "2026-10-14", "product_id": product["id"], "quantity": 2,
                                           "discount": 10}).json()
    row = next(s for s in client.get("/api/sales?month=2026-10").json() if s["id"] == sale["id"])
    assert row["amount"] == round(2 * product["sale_price"] * 0.9, 2) and row["discount"] == 10


def test_return_puts_stock_back_and_reduces_revenue_and_vat(client):
    product = hub(client)
    sale = client.post("/api/sales", json={"date": "2026-10-14", "product_id": product["id"], "quantity": 3}).json()
    before = client.get("/api/summary?month=2026-10").json()
    response = client.post(f"/api/sales/{sale['id']}/return", json={"quantity": 2, "reason": "defect"})
    assert response.status_code == 201 and response.json()["amount"] == -2 * product["sale_price"]
    after = client.get("/api/summary?month=2026-10").json()
    assert hub(client)["stock"] == product["stock"] - 1
    assert after["revenue"] == pytest.approx(before["revenue"] - 2 * product["sale_price"])
    assert after["vat"]["collected"] < before["vat"]["collected"]
    assert after["cogs"] < before["cogs"]
    # nu se poate returna mai mult decât s-a vândut și nici edita factura stornată
    assert client.post(f"/api/sales/{sale['id']}/return", json={"quantity": 2}).status_code == 400
    assert client.put(f"/api/sales/{sale['id']}", json={"date": "2026-10-14", "product_id": product["id"],
                                                         "quantity": 5}).status_code == 400
    assert client.delete(f"/api/sales/{sale['id']}").status_code == 400
    listed = next(s for s in client.get("/api/sales?month=2026-10").json() if s["id"] == sale["id"])
    assert listed["returned_quantity"] == 2


def test_return_of_closed_month_invoice_goes_in_current_month(client):
    sale = client.get("/api/sales?month=2026-09").json()[0]
    client.post("/api/closing/2026-09")
    response = client.post(f"/api/sales/{sale['id']}/return", json={})
    assert response.status_code == 201


# ---------- Calendar fiscal și impozit pe profit ----------

def test_fiscal_calendar_has_amounts_for_october_deadlines(client):
    data = client.get("/api/obligations?year=2026").json()
    items = {item["id"]: item for item in data["items"]}
    september = client.get("/api/summary?month=2026-09").json()
    d112 = items["d112-2026-09"]
    taxes = september["taxes"]
    assert d112["date"] == "2026-10-26" and d112["amount"] == pytest.approx(
        taxes["cas"] + taxes["cass"] + taxes["income_tax"] + taxes["cam"])
    assert items["d300-2026-09"]["amount"] == september["vat"]["payable"]
    assert items["profit-2026-T3"]["date"] == "2026-10-26"
    assert data["profit_tax"]["quarters"][3]["deadline"] == "2027-06-25"


def test_quarterly_profit_tax_uses_cumulative_profit_and_losses(client):
    year = client.get("/api/obligations?year=2026").json()["profit_tax"]
    q3 = year["quarters"][2]
    months = [client.get(f"/api/summary?month={m}").json()["profit_before_tax"] for m in q3["months"]]
    assert q3["profit_before_tax"] == pytest.approx(sum(months))
    client.put("/api/settings", json={"company_name": "Testify Hardware", "tax_regime": "profit",
                                      "tax_loss_carried": 50000})
    with_loss = client.get("/api/obligations?year=2026").json()["profit_tax"]
    assert with_loss["loss_at_start"] == 50000
    assert with_loss["quarters"][2]["loss_recovered"] > 0
    assert with_loss["total"] < year["total"]


def test_loss_recovery_is_limited_to_70_percent():
    assert obligations.LOSS_LIMIT == 0.70


def test_reminders_and_paid_marking(client):
    from app.db import get_conn

    a_week_before = date(2026, 10, 20)
    with get_conn() as conn:
        assert any(r["id"] == "d112-2026-09" for r in obligations.reminders(conn, a_week_before))
        assert not obligations.reminders(conn, date(2026, 10, 1))  # prea devreme pentru memento
    assert client.patch("/api/obligations/d112-2026-09/paid", json={"paid": True}).status_code == 200
    with get_conn() as conn:
        assert not any(r["id"] == "d112-2026-09" for r in obligations.reminders(conn, a_week_before))
    assert "reminders" in client.get("/api/dashboard").json()


# ---------- Trezorerie ----------

def test_treasury_forecast(client):
    assert client.get("/api/treasury").json()["balance_set"] is False
    client.put("/api/treasury/balance", json={"balance": 100000})
    forecast = client.get("/api/treasury").json()
    assert forecast["balance_set"] and forecast["start_balance"] == 100000
    assert len(forecast["days"]) == 31
    assert any(e["kind"] == "tax" for e in forecast["events"])
    assert forecast["end_balance"] == pytest.approx(100000 + forecast["total_in"] - forecast["total_out"], abs=1)
    with_overdue = client.get("/api/treasury?include_overdue=true").json()
    assert with_overdue["total_in"] >= forecast["total_in"]


# ---------- Salarii ----------

def test_unpaid_leave_reduces_gross_and_leave_balance(client):
    employee = client.get("/api/employees").json()[0]
    base = client.get("/api/payroll?month=2026-10").json()
    line = next(l for l in base["lines"] if l["employee_id"] == employee["id"])
    assert line["working_days"] == 22
    client.post(f"/api/employees/{employee['id']}/absences", json={"month": "2026-10", "kind": "fara_plata", "days": 11})
    client.post(f"/api/employees/{employee['id']}/absences", json={"month": "2026-10", "kind": "odihna", "days": 3})
    after = next(l for l in client.get("/api/payroll?month=2026-10").json()["lines"]
                 if l["employee_id"] == employee["id"])
    assert after["gross"] == round(line["gross"] / 2) and after["worked_days"] == 8
    details = next(e for e in client.get("/api/employees").json() if e["id"] == employee["id"])
    assert details["leave_taken"] == 3 and details["leave_left"] == 18
    too_many = client.post(f"/api/employees/{employee['id']}/absences",
                           json={"month": "2026-10", "kind": "medical", "days": 20})
    assert too_many.status_code == 400


def test_minimum_wage_follows_the_rules(client):
    assert client.get("/api/payroll?month=2026-06").json()["min_wage"] == 4050
    assert client.get("/api/payroll?month=2026-10").json()["min_wage"] == 4325
    response = client.post("/api/employees", json={"name": "Ion Test", "hire_date": "2026-10-01", "gross": 4000})
    payroll = client.get("/api/payroll?month=2026-10").json()
    assert response.status_code == 201 and any("Ion Test" in w for w in payroll["warnings"])
    client.post("/api/employees", json={"name": "Ana Part", "hire_date": "2026-10-01", "gross": 2200,
                                        "hours_per_day": 4})
    payroll = client.get("/api/payroll?month=2026-10").json()
    assert not any("Ana Part" in w for w in payroll["warnings"])


# ---------- Obiective ----------

def test_goals_progress_on_dashboard(client):
    assert client.get("/api/dashboard?month=2026-09").json()["goals"] is None
    client.put("/api/goals", json={"month": "default", "revenue": 200000, "profit": 20000})
    client.put("/api/goals", json={"month": "2026-09", "revenue": 150000})
    goals = client.get("/api/dashboard?month=2026-09").json()["goals"]
    assert goals["revenue"]["target"] == 150000 and goals["profit"]["target"] == 20000
    assert goals["revenue"]["projected"] == goals["revenue"]["actual"]  # luna e încheiată
    current = client.get("/api/dashboard").json()["goals"]
    assert current["revenue"]["target"] == 200000 and current["day"] == date.today().day
