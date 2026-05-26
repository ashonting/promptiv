"""End-to-end smoke test for the teaser page.

Run this against a locally running Flask app:
    # Terminal 1 (started by user):
    flask run --port 5000

    # Terminal 2:
    pytest tests/e2e/test_teaser_flow.py -v
"""
import os
import pytest
from playwright.sync_api import sync_playwright, expect


BASE_URL = os.environ.get("PROMPTIV_BASE_URL", "http://localhost:5000")


@pytest.fixture
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        yield page
        browser.close()


def test_page_loads_with_headline(page):
    page.goto(BASE_URL)
    expect(page.locator("h1.headline")).to_contain_text("Somewhere new is")
    expect(page.locator(".subhead")).to_contain_text("Your budget is bigger than your map")


def test_first_card_visible_on_load(page):
    page.goto(BASE_URL)
    first_card = page.locator('.ex-card[data-card-idx="0"]')
    expect(first_card).to_be_visible()


def test_signup_flow_transitions_to_thanks(page):
    page.goto(BASE_URL)
    page.fill("#email-input", "playwright-e2e@example.com")
    page.click("button[type='submit']")
    expect(page.locator("#thanks-state")).to_be_visible(timeout=5000)
    expect(page.locator(".ack")).to_contain_text("We're working on it")


def test_qualifier_submit_dismisses_thanks(page):
    page.goto(BASE_URL)
    page.fill("#email-input", "playwright-e2e-2@example.com")
    page.click("button[type='submit']")
    expect(page.locator("#thanks-state")).to_be_visible(timeout=5000)

    page.click('.pick[data-pick="stretch"]')
    page.fill("#airport-input", "BNA")
    page.fill("#frustration-input", "everything is overwhelming")
    page.click("#qualifier-submit")

    # After submit, the thanks block should be replaced with a quiet message
    expect(page.locator("#thanks-state")).to_contain_text("Thanks. We'll be in touch.", timeout=5000)


def test_qualifier_skip_dismisses_thanks(page):
    page.goto(BASE_URL)
    page.fill("#email-input", "playwright-e2e-3@example.com")
    page.click("button[type='submit']")
    expect(page.locator("#thanks-state")).to_be_visible(timeout=5000)

    page.click("#qualifier-skip")
    expect(page.locator("#thanks-state")).to_contain_text("Thanks", timeout=5000)


def test_privacy_page_loads(page):
    page.goto(BASE_URL + "/privacy")
    expect(page.locator("h1")).to_contain_text("Privacy")


def test_terms_page_loads(page):
    page.goto(BASE_URL + "/terms")
    expect(page.locator("h1")).to_contain_text("Terms")
