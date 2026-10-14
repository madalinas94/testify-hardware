"""Testul „clientul pisălog”: date greșite și scenarii ciudate nu trebuie să strice nimic."""

import io
import os
import tempfile

import openpyxl
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("TESTIFY_FISCAL_FEED", "")
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("TESTIFY_DB", os.path.join(tmp, "test.db"))
        from app.main import app
        with TestClient(app, raise_server_exceptions=False) as test_client:
            test_client.post("/api/auth/setup", json={"password": "parola123", "demo": True})
            yield test_client


def product(client, code="P101"):
    return next(p for p in client.get("/api/products").json() if p["code"] == code)


def test_cannot_sell_more_than_in_stock(client):
    hub = product(client)
    response = client.post("/api/sales", json={"date": "2026-10-14", "product_id": hub["id"], "quantity": 50})
    assert response.status_code == 400 and "Stoc insuficient" in response.json()["detail"]
    assert product(client)["stock"] == 5  # nimic nu s-a salvat


def test_editing_a_sale_cannot_push_stock_below_zero(client):
    hub = product(client)
    sale = client.post("/api/sales", json={"date": "2026-10-14", "product_id": hub["id"], "quantity": 2}).json()
    response = client.put(f"/api/sales/{sale['id']}", json={"date": "2026-10-14", "product_id": hub["id"],
                                                              "quantity": 40})
    assert response.status_code == 400
    assert product(client)["stock"] == 3


def test_deleting_a_receipt_cannot_make_stock_negative(client):
    receipt = client.get("/api/purchases?month=2026-09").json()[0]
    assert client.delete(f"/api/purchases/{receipt['id']}").status_code == 400


def test_invoice_numbers_are_unique(client):
    response = client.post("/api/sales", json={"date": "2026-10-14", "description": "x", "amount": 5,
                                               "invoice_number": "NB-1001"})
    assert response.status_code == 400 and "NB-1001" in response.json()["detail"]


@pytest.mark.parametrize("day", ["1990-01-01", "2099-01-01", "2026-02-30"])
def test_implausible_dates_are_rejected(client, day):
    response = client.post("/api/sales", json={"date": day, "description": "x", "amount": 5})
    assert response.status_code == 422


def test_huge_amounts_are_rejected_in_romanian(client):
    response = client.post("/api/sales", json={"date": "2026-10-14", "description": "x", "amount": 999e9})
    assert response.status_code == 422
    assert response.json()["detail"] == "Valoarea pentru suma este prea mare (maximum 1.000.000.000)."


def test_excel_export_does_not_run_formulas(client):
    client.post("/api/sales", json={"date": "2026-09-14", "description": '=HYPERLINK("http://rau.ro")',
                                    "amount": 5})
    book = openpyxl.load_workbook(io.BytesIO(client.get("/api/export/excel?month=2026-09").content))
    texts = [cell.value for row in book["Vânzări"].iter_rows() for cell in row if isinstance(cell.value, str)]
    assert not any(text.startswith("=") for text in texts)
    assert any("HYPERLINK" in text for text in texts)


def test_romanian_excel_csv_is_imported(client):
    csv = "data;nr_factura;produs;cantitate;pret_unitar_fara_tva;client\n14.10.2026;X-2;Cablu ţ;1;10,5;Firmă Ăîâ\n"
    files = [("files", ("vanzari.csv", csv.encode("cp1250"), "text/csv"))]
    assert client.post("/api/import", files=files, data={"replace": "false"}).status_code == 200
    sale = next(s for s in client.get("/api/sales?month=2026-10").json() if s["invoice_number"] == "X-2")
    assert sale["amount"] == 10.5 and sale["client_name"] == "Firmă Ăîâ"


@pytest.mark.parametrize("name,content", [("raport.xlsx", b"nu e zip"), ("gol.csv", b"")])
def test_broken_import_files_give_a_clear_message(client, name, content):
    response = client.post("/api/import", files=[("files", (name, content, "text/plain"))],
                           data={"replace": "true"})
    assert response.status_code == 400 and "Importul nu a reușit" in response.json()["detail"]
    assert client.get("/api/summary?month=2026-09").json()["sales_count"] == 114


def test_renaming_to_an_existing_name_is_refused(client):
    clients = client.get("/api/clients").json()
    response = client.put(f"/api/clients/{clients[0]['id']}", json={"name": clients[1]["name"]})
    assert response.status_code == 400
    suppliers = client.get("/api/suppliers").json()
    response = client.put(f"/api/suppliers/{suppliers[0]['id']}", json={"name": suppliers[1]["name"]})
    assert response.status_code == 400


def test_employee_with_past_salaries_cannot_be_deleted(client):
    employee = client.get("/api/employees").json()[0]
    response = client.delete(f"/api/employees/{employee['id']}")
    assert response.status_code == 400 and "Data plecării" in response.json()["detail"]
    assert client.get("/api/summary?month=2026-09").json()["payroll"]["gross"] == 34525


def test_leaving_date_must_follow_hiring_date(client):
    employee = client.get("/api/employees").json()[0]
    response = client.put(f"/api/employees/{employee['id']}", json={
        "name": employee["name"], "hire_date": "2026-07-01", "end_date": "2026-01-01"})
    assert response.status_code == 422


def test_expense_needs_an_existing_category(client):
    response = client.post("/api/expenses", json={"date": "2026-10-14", "category": "Nu există", "amount": 5})
    assert response.status_code == 400


def test_changing_client_terms_moves_unpaid_due_dates(client):
    alfa = next(c for c in client.get("/api/clients").json() if c["name"] == "Alfa Office SRL")
    client.put(f"/api/clients/{alfa['id']}", json={"name": alfa["name"], "payment_terms": 60})
    invoice = next(i for i in client.get("/api/receivables").json()["invoices"] if i["client_name"] == alfa["name"])
    assert invoice["due_date"] == "2026-10-31" and invoice["date"] == "2026-09-01"


def test_empty_app_pages_work(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("TESTIFY_DB", os.path.join(tmp, "empty.db"))
        monkeypatch.setenv("TESTIFY_FISCAL_FEED", "")
        from app.main import app
        with TestClient(app) as empty:
            empty.post("/api/auth/setup", json={"password": "parola123"})
            for path in ["/api/dashboard", "/api/products", "/api/clients", "/api/suppliers", "/api/receivables",
                         "/api/payables", "/api/inventory", "/api/employees", "/api/export/excel?month=2026-10",
                         "/api/export/pdf?month=2026-10"]:
                assert empty.get(path).status_code == 200, path
