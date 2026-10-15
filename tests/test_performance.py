"""Testul de performanță: 5 ani de date (aprox. 9.000 de facturi) nu trebuie să încetinească aplicația."""

import os
import random
import tempfile
import time

import pytest
from fastapi.testclient import TestClient

from app import calc

YEARS = 5
LIMIT_SECONDS = 3.0  # cât poate dura, cel mult, o pagină grea pe un calculator obișnuit de birou


def fill_five_years(conn) -> None:
    rng = random.Random(42)
    products = [row["id"] for row in conn.execute("SELECT id FROM products")]
    clients = [row["id"] for row in conn.execute("SELECT id FROM clients")]
    first = calc.shift_month("2026-09", -12 * YEARS + 1)
    month = first
    sales, purchases, expenses = [], [], []
    while month < "2026-07":
        for _ in range(150):
            day = f"{month}-{rng.randint(1, 28):02d}"
            pid = rng.choice(products)
            qty = rng.randint(1, 4)
            sales.append((day, "Vânzare istorică", qty, round(qty * 120.0, 2), pid, rng.choice(clients), 120.0, 60.0, day))
        for pid in products:
            purchases.append((f"{month}-02", f"NIR-{month}-{pid}", "Conex Distributie SRL", pid, 60, 60.0, f"{month}-02"))
        for category, amount in [("Chirie", 6500), ("Utilități", 1800), ("Marketing", 2300), ("Transport", 1100)]:
            expenses.append((f"{month}-05", category, category, amount))
        month = calc.shift_month(month, 1)
    conn.executemany("INSERT INTO sales(date, description, quantity, amount, product_id, client_id, unit_price, "
                     "unit_cost, due_date, paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)", sales)
    conn.executemany("INSERT INTO purchases(date, doc_number, supplier, product_id, quantity, unit_cost, due_date, paid) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, 1)", purchases)
    conn.executemany("INSERT INTO expenses(date, category, description, amount) VALUES (?, ?, ?, ?)", expenses)
    conn.execute("UPDATE products SET opening_date = ?", (f"{first}-01",))
    conn.execute("UPDATE employees SET hire_date = ?", (f"{first}-01",))
    conn.execute("UPDATE salary_history SET effective_from = ?", (f"{first}-01",))


@pytest.fixture(scope="module")
def big_client():
    saved = {key: os.environ.get(key) for key in ("TESTIFY_DB", "TESTIFY_FISCAL_FEED")}
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["TESTIFY_DB"] = os.path.join(tmp, "big.db")
        os.environ["TESTIFY_FISCAL_FEED"] = ""
        from app import audit
        from app.db import get_conn
        from app.main import app
        with TestClient(app) as client:
            client.post("/api/auth/setup", json={"password": "parola123", "demo": True})
            with get_conn() as conn, audit.paused(conn):
                fill_five_years(conn)
            yield client
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.mark.parametrize("path", [
    "/api/dashboard?month=2026-09", "/api/obligations?year=2026", "/api/treasury", "/api/products",
    "/api/analysis?month=2026-09&months=12", "/api/reorder", "/api/export/letter?month=2026-09",
    "/api/export/excel?month=2026-09", "/api/sales?month=2026-09",
])
def test_heavy_pages_stay_fast_with_five_years_of_data(big_client, path):
    count = big_client.get("/api/summary?month=2024-05").json()["sales_count"]
    assert count >= 150
    start = time.perf_counter()
    response = big_client.get(path)
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    assert elapsed < LIMIT_SECONDS, f"{path} a durat {elapsed:.2f} s"
