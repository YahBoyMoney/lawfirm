import mimetypes
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://berhelaw.test"
ADMIN_PATH = "/api/leads/case-review"


@pytest.fixture(scope="module")
def webkit_browser():
    with sync_playwright() as playwright:
        try:
            browser = playwright.webkit.launch(headless=True)
            smoke_context = browser.new_context()
            smoke_context.close()
        except PlaywrightError as error:
            pytest.skip(f"Playwright WebKit cannot create a browser context in this environment: {error}")
        yield browser
        browser.close()


def local_file(pathname):
    path = ROOT / pathname.lstrip("/")
    if pathname.endswith("/") or path.is_dir():
        path /= "index.html"
    return path


def install_routes(context, intake=None, feed=None):
    def handle(route):
        parsed = urlparse(route.request.url)
        if parsed.hostname == "admin.berhelaw.com" and parsed.path == ADMIN_PATH and intake:
            intake(route)
            return
        if parsed.hostname != "berhelaw.test":
            route.abort()
            return
        if parsed.path == "/data/garden-grove-chemical-leak-updates.json" and feed:
            feed(route)
            return
        path = local_file(parsed.path)
        if not path.is_file():
            route.fulfill(status=404, body="Not found", content_type="text/plain")
            return
        route.fulfill(
            status=200,
            body=path.read_bytes(),
            content_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        )

    context.route("**/*", handle)


def fill_required_form(page, selector="form[data-intake-form]", *, consent=True, phone="+44 (0)20 7946 0958"):
    form = page.locator(selector)
    form.locator('[name="firstName"]').fill("QA")
    form.locator('[name="lastName"]').fill("Reviewer")
    form.locator('[name="phone"]').fill(phone)
    form.locator('[name="email"]').fill("qa-review@example.test")
    form.locator('[name="summary"]').fill("Controlled browser contract check with no sensitive information.")
    for select in form.locator("select[required]").all():
        select.select_option(index=1)
    for field in form.locator('input[required]:not([type="checkbox"]):not([name="firstName"]):not([name="lastName"]):not([name="phone"]):not([name="email"])').all():
        field.fill("QA required value")
    for area in form.locator('textarea[required]:not([name="summary"])').all():
        area.fill("QA conflict-safe required value")
    if consent:
        form.locator('[name="consent"]').check()
    return form


def test_mobile_navigation_open_close_escape_and_focus(webkit_browser):
    context = webkit_browser.new_context(viewport={"width": 390, "height": 844})
    install_routes(context)
    page = context.new_page()
    page.goto(f"{ORIGIN}/")
    toggle = page.locator(".nav-toggle")
    navigation = page.locator("#site-navigation")

    toggle.click()
    assert toggle.get_attribute("aria-expanded") == "true"
    assert navigation.get_attribute("data-open") == "true"
    page.keyboard.press("Tab")
    assert page.locator("#site-navigation a").first.evaluate("element => element === document.activeElement")
    page.keyboard.press("Escape")
    assert toggle.get_attribute("aria-expanded") == "false"
    assert toggle.evaluate("element => element === document.activeElement")
    toggle.click()
    toggle.click()
    assert navigation.get_attribute("data-open") == "false"
    context.close()


def test_mobile_navigation_remains_available_without_javascript(webkit_browser):
    context = webkit_browser.new_context(viewport={"width": 390, "height": 844}, java_script_enabled=False)
    install_routes(context)
    page = context.new_page()
    page.goto(f"{ORIGIN}/")
    assert page.locator("#site-navigation a").first.is_visible()
    assert not page.locator(".nav-toggle").is_visible()
    context.close()


def test_valid_form_post_gets_only_controlled_server_acknowledgement(webkit_browser):
    captured = {}

    def intake(route):
        captured.update(parse_qs(route.request.post_data or "", keep_blank_values=True))
        route.fulfill(status=200, content_type="text/html", body="<h1>Controlled intake acknowledgement</h1>")

    context = webkit_browser.new_context()
    install_routes(context, intake=intake)
    page = context.new_page()
    page.goto(f"{ORIGIN}/free-case-review/")
    fill_required_form(page, "#general-review").locator('[type="submit"]').click()
    page.wait_for_url("https://admin.berhelaw.com/api/leads/case-review")
    expect(page.get_by_role("heading", name="Controlled intake acknowledgement")).to_be_visible()
    assert captured["firstName"] == ["QA"]
    assert captured["lastName"] == ["Reviewer"]
    assert captured["matterType"] == ["General civil matter"]
    assert captured["caseType"]
    assert captured["preferred_contact"]
    assert captured["knownDeadline"] == [""]
    assert captured["bot-field"] == [""]
    assert captured["form_version"] == ["2026-07-11.2"]
    context.close()


def test_malformed_phone_is_blocked_with_accessible_error(webkit_browser):
    posts = []
    context = webkit_browser.new_context()
    install_routes(context, intake=lambda route: posts.append(route.request.post_data))
    page = context.new_page()
    page.goto(f"{ORIGIN}/free-case-review/")
    form = fill_required_form(page, "#general-review", phone="111")
    form.locator('[type="submit"]').click()
    phone = form.locator('[name="phone"]')
    error = form.locator("[data-phone-error]")
    assert phone.get_attribute("aria-invalid") == "true"
    assert error.get_attribute("aria-live") == "polite"
    assert "7 to 15 digits" in error.inner_text()
    assert posts == []
    context.close()


@pytest.mark.parametrize("phone", ["1......", "callme1234567"])
def test_native_phone_constraint_rejects_junk_without_javascript(webkit_browser, phone):
    posts = []
    context = webkit_browser.new_context(java_script_enabled=False)
    install_routes(context, intake=lambda route: posts.append(route.request.post_data))
    page = context.new_page()
    page.goto(f"{ORIGIN}/free-case-review/")
    form = fill_required_form(page, "#general-review", phone=phone)
    assert not form.locator('[name="phone"]').evaluate("element => element.validity.valid")
    assert posts == []
    context.close()


def test_required_consent_blocks_post(webkit_browser):
    posts = []
    context = webkit_browser.new_context()
    install_routes(context, intake=lambda route: posts.append(route.request.post_data))
    page = context.new_page()
    page.goto(f"{ORIGIN}/free-case-review/")
    form = fill_required_form(page, "#general-review", consent=False)
    form.locator('[type="submit"]').click()
    consent = form.locator('[name="consent"]')
    assert consent.evaluate("element => !element.validity.valid")
    assert posts == []
    assert page.url.startswith(f"{ORIGIN}/free-case-review/")
    context.close()


@pytest.mark.parametrize("failure", ["400", "500", "network"])
def test_server_and_network_failures_never_show_success(webkit_browser, failure):
    def intake(route):
        if failure == "network":
            route.abort("failed")
        else:
            route.fulfill(status=int(failure), content_type="text/html", body=f"<h1>Submission failed ({failure})</h1>")

    context = webkit_browser.new_context()
    install_routes(context, intake=intake)
    page = context.new_page()
    page.goto(f"{ORIGIN}/free-case-review/")
    form = fill_required_form(page, "#general-review")
    try:
        form.locator('[type="submit"]').click(timeout=5000)
    except PlaywrightError:
        pass
    assert "/success.html" not in page.url
    assert page.get_by_text("Your request reached the intake system.").count() == 0
    context.close()


def test_forged_submission_reference_is_never_rendered(webkit_browser):
    context = webkit_browser.new_context()
    install_routes(context)
    page = context.new_page()
    page.goto(f"{ORIGIN}/success.html?reference=FAKE123")
    assert page.get_by_text("FAKE123").count() == 0
    assert page.locator("[data-submission-reference]").count() == 0
    context.close()


@pytest.mark.parametrize(
    ("route_path", "form_selector", "expected"),
    [
        ("/free-case-review/", "#general-review", {"caseType", "preferred_contact", "knownDeadline", "county"}),
        ("/landing/truck-fleet-rideshare-accident-california/", "#truck-review", {"preferred_contact", "county"}),
        ("/landing/garden-grove-chemical-leak/", "#garden-review", {"preferred_contact"}),
    ],
)
def test_javascript_disabled_native_posts_use_production_keys(webkit_browser, route_path, form_selector, expected):
    captured = {}

    def intake(route):
        captured.update(parse_qs(route.request.post_data or "", keep_blank_values=True))
        route.fulfill(status=200, content_type="text/html", body="<h1>Native POST received</h1>")

    context = webkit_browser.new_context(java_script_enabled=False)
    install_routes(context, intake=intake)
    page = context.new_page()
    page.goto(f"{ORIGIN}{route_path}")
    fill_required_form(page, form_selector).locator('[type="submit"]').click()
    page.wait_for_url("https://admin.berhelaw.com/api/leads/case-review")
    expect(page.get_by_role("heading", name="Native POST received")).to_be_visible()
    canonical = {"firstName", "lastName", "matterType", "phone", "email", "bot-field", "summary", "consent", "page_url", "referrer", "campaign"}
    assert canonical | expected <= captured.keys()
    assert captured["form_version"] == ["2026-07-11.2"]
    assert captured["consent_version"] == ["2026-07-11"]
    context.close()


def test_mobile_sticky_cta_suppression_on_hero_and_form_focus(webkit_browser):
    context = webkit_browser.new_context(viewport={"width": 390, "height": 844})
    install_routes(context)
    page = context.new_page()
    page.goto(f"{ORIGIN}/")
    page.wait_for_timeout(150)
    sticky = page.locator(".mobile-actions")
    assert sticky.get_attribute("data-suppressed") == "true"
    assert sticky.get_attribute("aria-hidden") == "true"
    page.goto(f"{ORIGIN}/free-case-review/")
    first_name = page.locator('#general-review [name="firstName"]')
    first_name.scroll_into_view_if_needed()
    page.wait_for_timeout(100)
    assert sticky.get_attribute("data-suppressed") == "true"
    assert sticky.get_attribute("aria-hidden") == "true"
    first_name.focus()
    page.wait_for_timeout(50)
    assert sticky.get_attribute("data-suppressed") == "true"
    assert sticky.get_attribute("aria-hidden") == "true"
    first_name.blur()
    page.wait_for_timeout(50)
    assert sticky.get_attribute("data-suppressed") == "true"
    assert sticky.get_attribute("aria-hidden") == "true"
    context.close()


def feed_payload(last_verified):
    return {
        "lastVerifiedUtc": last_verified,
        "updates": [{
            "timeUtc": last_verified,
            "title": "Controlled public update",
            "summary": "Controlled source summary.",
            "sourceLabel": "Official controlled source",
            "sourceUrl": "https://ggcity.org/emergency",
        }],
    }


@pytest.mark.parametrize(
    ("state", "payload", "status_code", "expected_text"),
    [
        ("fresh", feed_payload("2026-07-10T12:00:00Z"), 200, "Official emergency sources remain primary"),
        ("stale", feed_payload("2026-06-01T12:00:00Z"), 200, "Last verified June 1, 2026"),
        ("malformed", {"lastVerifiedUtc": "not-a-date", "updates": []}, 200, "malformed and cannot be verified"),
        ("malformed", {**feed_payload("2026-07-10T12:00:00Z"), "updates": [{**feed_payload("2026-07-10T12:00:00Z")["updates"][0], "timeUtc": "not-a-date"}]}, 200, "malformed and cannot be verified"),
        ("unavailable", None, 503, "local update feed is unavailable"),
    ],
)
def test_garden_grove_feed_states(webkit_browser, state, payload, status_code, expected_text):
    def feed(route):
        if payload is None:
            route.fulfill(status=status_code, body="Unavailable", content_type="text/plain")
        else:
            route.fulfill(status=status_code, json=payload)

    context = webkit_browser.new_context()
    context.add_init_script("Date.now = () => new Date('2026-07-11T12:00:00Z').getTime()")
    install_routes(context, feed=feed)
    page = context.new_page()
    page.goto(f"{ORIGIN}/landing/garden-grove-chemical-leak/")
    status = page.locator("#updates-status")
    assert status.get_attribute("data-feed-state") == state
    assert expected_text.lower() in status.inner_text().lower()
    if state == "fresh":
        assert status.get_attribute("role") == "status"
        assert "feed-status--stale" not in (status.get_attribute("class") or "")
    else:
        assert status.get_attribute("role") == "alert"
        assert "feed-status--stale" in (status.get_attribute("class") or "")
        assert "official" in status.inner_text().lower()
    context.close()


def test_garden_grove_stale_state_is_visible_without_javascript(webkit_browser):
    context = webkit_browser.new_context(java_script_enabled=False)
    install_routes(context)
    page = context.new_page()
    page.goto(f"{ORIGIN}/landing/garden-grove-chemical-leak/")
    status = page.locator("#updates-status")
    assert status.get_attribute("data-feed-state") == "stale"
    assert status.get_attribute("role") == "alert"
    assert "last verified may 31, 2026" in status.inner_text().lower()
    assert "official city and county sources" in status.inner_text().lower()
    context.close()
