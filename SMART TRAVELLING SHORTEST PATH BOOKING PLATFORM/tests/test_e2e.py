"""Optional browser tests. Run only against a disposable running demo instance.

RAILORA_E2E_URL=http://localhost:8080 pytest tests/test_e2e.py -v
The booking test cancels its own booking afterwards. No real tickets/payments exist.
"""

import os

import pytest
from playwright.sync_api import expect, sync_playwright

URL = os.getenv("RAILORA_E2E_URL", "").rstrip("/")
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not URL, reason="Set RAILORA_E2E_URL to a running disposable demo server."),
]


@pytest.fixture
def browser():
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        yield instance
        instance.close()


def login(page, admin=False):
    page.goto(URL + "/login", wait_until="networkidle")
    page.get_by_role("button", name="Admin demo" if admin else "Traveler demo", exact=True).click()
    page.wait_for_url("**/admin" if admin else "**/dashboard", timeout=20000)
    expect(page.locator(".page-title")).to_be_visible(timeout=15000)


def test_login_visuals_and_invalid_password(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(URL + "/login", wait_until="networkidle")
    expect(page.get_by_text("Welcome aboard.", exact=True)).to_be_visible()
    page.locator(".auth-input input").nth(1).fill("wrong-password")
    page.get_by_role("button", name="Sign in to your workspace", exact=True).click()
    expect(page.get_by_text("Email or password is incorrect.", exact=True)).to_be_visible(timeout=10000)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.close()


def test_user_booking_is_pushed_to_admin_then_cancelled(browser):
    user_context = browser.new_context(viewport={"width": 1440, "height": 1100})
    admin_context = browser.new_context(viewport={"width": 1440, "height": 1100})
    traveler = user_context.new_page()
    admin = admin_context.new_page()
    errors = []
    traveler.on("pageerror", lambda e: errors.append(str(e)))
    admin.on("pageerror", lambda e: errors.append(str(e)))
    login(traveler)
    login(admin, admin=True)
    traveler.get_by_role("button", name="Find trains", exact=True).first.click()
    traveler.wait_for_url("**/search", timeout=15000)
    traveler.get_by_role("button", name="Book ticket", exact=True).first.click()
    expect(traveler.get_by_text("Passenger details", exact=True)).to_be_visible(timeout=10000)
    traveler.locator(".passenger-row input").first.fill("E2E Test Traveler")
    traveler.get_by_role("button", name="Confirm journey", exact=True).click()
    expect(traveler.get_by_text("You’re all set. Happy travels!", exact=True)).to_be_visible(timeout=15000)
    pnr = traveler.locator(".success-pnr").inner_text()
    expect(admin.get_by_text(pnr, exact=True)).to_be_visible(timeout=15000)
    traveler.get_by_role("button", name="View my bookings", exact=True).click()
    traveler.wait_for_url("**/bookings", timeout=10000)
    card = traveler.locator(".booking-card").filter(has_text=pnr)
    card.get_by_role("button", name="View ticket", exact=True).click()
    with traveler.expect_download() as download:
        traveler.get_by_role("button", name="Download PDF ticket", exact=True).click()
    assert download.value.suggested_filename == f"Railora-{pnr}.pdf"
    assert download.value.failure() is None
    traveler.get_by_role("button", name="Close", exact=True).click()
    card.get_by_role("button", name="Cancel", exact=True).click()
    traveler.get_by_role("button", name="Cancel booking", exact=True).click()
    expect(card.locator(".status-badge")).to_have_text("Cancelled", timeout=15000)
    assert errors == []
    user_context.close()
    admin_context.close()


def test_mobile_navigation_is_responsive(browser):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    login(page)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.locator(".mobile-menu").click()
    expect(page.locator(".sidebar")).to_have_class("sidebar mobile-open")
    page.locator(".sidebar").get_by_role("button", name="Find trains", exact=True).click()
    page.wait_for_url("**/search", timeout=15000)
    expect(page.get_by_text("Find your perfect journey.", exact=True)).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.close()


def test_algorithm_lab_process_worker_and_seat_sandbox(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    login(page)
    page.goto(URL + "/lab", wait_until="networkidle")
    page.get_by_role("button", name="Run the algorithms", exact=True).click()
    expect(page.get_by_text("Greedy · Dijkstra", exact=True)).to_be_visible(timeout=30000)
    expect(page.get_by_text("BZA → MAS → SBC → NDLS", exact=True).first).to_be_visible()
    page.get_by_role("button", name="Try seat allocation", exact=True).click()
    expect(page.get_by_text("C1-01, C1-02, C1-03", exact=True)).to_be_visible()
    page.close()
