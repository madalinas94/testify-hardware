"""Teste de interfață: un browser adevărat apasă butoanele, ca Robert.

Rulează pe GitHub la fiecare modificare (vezi .github/workflows/tests.yml). Local:
    pip install playwright && python -m playwright install chromium
    pytest tests/e2e
"""

import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_INVOICE = ROOT / "sample_data" / "efactura" / "factura_conex_CNX-24518.xml"
ROUTES = ["dashboard", "vanzari", "stoc", "clienti", "furnizori", "cheltuieli", "bani", "angajati", "taxe",
          "decizii", "calendar", "rapoarte", "setari"]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def server():
    port = free_port()
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "TESTIFY_DB": os.path.join(tmp, "ui.db"), "TESTIFY_FISCAL_FEED": ""}
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
                                   cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        url = f"http://127.0.0.1:{port}"
        for _ in range(60):
            try:
                urllib.request.urlopen(f"{url}/api/auth/status", timeout=1)
                break
            except OSError:
                time.sleep(0.25)
        yield url
        process.terminate()
        process.wait(timeout=10)


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as playwright:
        executable = os.environ.get("TESTIFY_CHROMIUM")  # de exemplu un Chromium deja instalat
        try:
            instance = playwright.chromium.launch(executable_path=executable) if executable else playwright.chromium.launch()
        except sync_api.Error as error:
            pytest.skip(f"Browserul nu este instalat (python -m playwright install chromium): {error.message[:80]}")
        yield instance
        instance.close()


@pytest.fixture(scope="module")
def logged_in(server, browser):
    """Prima pornire: parolă nouă, datele firmei, codul de recuperare."""
    context = browser.new_context(viewport={"width": 1360, "height": 900})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(server)
    page.fill("#auth-password", "parola123")
    page.fill("#auth-confirm", "parola123")
    page.click("#auth-submit")
    page.check("[data-act=ack]")
    page.click("[data-act=continue]")
    page.wait_for_selector("#trend-chart")
    page.evaluate("robot.close()")
    yield page, errors
    context.close()


def go(page, route, selector):
    page.goto(page.url.split("#")[0] + "#" + route)
    page.wait_for_selector(selector)
    page.evaluate("robot.close()")


def test_every_page_opens_without_errors(logged_in):
    page, errors = logged_in
    for route in ROUTES:
        go(page, route, "#view > *:not(.kpis)")
        page.wait_for_timeout(300)
        assert not page.query_selector("#view .empty svg + p:has-text('Error')"), route
    assert errors == []


def test_double_click_creates_one_invoice(logged_in):
    page, _ = logged_in
    go(page, "vanzari", "#sale-form")
    before = page.evaluate("fetch('/api/sales?month=' + currentMonth()).then(r => r.json()).then(x => x.length)")
    page.select_option("#sale-form [name=product_id]", index=3)
    page.fill("#sale-form [name=quantity]", "1")
    page.dblclick("#sale-form button[type=submit]")
    page.wait_for_timeout(1200)
    after = page.evaluate("fetch('/api/sales?month=' + currentMonth()).then(r => r.json()).then(x => x.length)")
    assert after == before + 1


def test_return_puts_invoice_on_minus(logged_in):
    page, _ = logged_in
    go(page, "vanzari", "#sale-form")
    page.click("[data-return]")
    page.click("#return-form button[type=submit]")
    page.wait_for_selector(".tag.storno")


def test_simulator_reacts_to_presets(logged_in):
    page, _ = logged_in
    go(page, "decizii", "#sim-result .sim-big")
    page.click("[data-preset='0']")  # angajez un vânzător
    page.wait_for_selector(".sim-year.bad")
    assert "5.113" in page.inner_text("#sim-result")


def test_efactura_import_from_settings(logged_in):
    page, _ = logged_in
    go(page, "setari", "#efactura-drop")
    page.set_input_files("#efactura-files", str(SAMPLE_INVOICE))
    page.wait_for_selector("#efactura-save")
    page.click("#efactura-save")
    page.wait_for_selector(".toast:has-text('Import reușit')")


def test_close_month_and_audit_log(logged_in):
    page, _ = logged_in
    page.evaluate("state.month = '2026-09'")
    go(page, "rapoarte", "#close-month")
    page.click("#close-month")
    page.click("[data-yes]")
    page.wait_for_selector("#reopen-month")
    assert "închisă" in page.inner_text("#audit-card")


def test_phone_layout_and_pin_login(server, browser, logged_in):
    page, _ = logged_in
    page.evaluate("fetch('/api/auth/pin', {method: 'PUT', headers: {'Content-Type': 'application/json'}, "
                  "body: JSON.stringify({current: 'parola123', pin: '4826'})})")
    phone = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    mobile = phone.new_page()
    mobile.goto(server)
    mobile.wait_for_selector("#auth-password")
    assert "PIN" in mobile.inner_text("#auth-password-label")
    mobile.fill("#auth-password", "4826")
    mobile.click("#auth-submit")
    mobile.wait_for_selector("#trend-chart")
    for route in ["dashboard", "vanzari", "stoc", "bani", "decizii", "calendar"]:
        go(mobile, route, "#view > *:not(.kpis)")
        mobile.wait_for_timeout(400)
        overflow = mobile.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        assert not overflow, f"derulare orizontală pe telefon: {route}"
    phone.close()
