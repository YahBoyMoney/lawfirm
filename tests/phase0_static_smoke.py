from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"


def soup():
    return BeautifulSoup(INDEX.read_text(encoding="utf-8"), "html.parser")


def test_robots_and_sitemap_cover_public_canonical_pages_only():
    robots = ROOT / "robots.txt"
    sitemap = ROOT / "sitemap.xml"
    assert robots.exists(), "robots.txt must exist"
    assert sitemap.exists(), "sitemap.xml must exist"
    robots_text = robots.read_text(encoding="utf-8")
    sitemap_text = sitemap.read_text(encoding="utf-8")
    assert "Sitemap: https://berhelaw.com/sitemap.xml" in robots_text
    expected = {
        "https://berhelaw.com/",
        "https://berhelaw.com/privacy.html",
        "https://berhelaw.com/terms.html",
        "https://berhelaw.com/disclaimer.html",
    }
    for url in expected:
        assert f"<loc>{url}</loc>" in sitemap_text
    assert sitemap_text.count("<lastmod>2026-05-25</lastmod>") == 21
    assert sitemap_text.count("<lastmod>2026-05-28</lastmod>") == 1
    assert (
        "<loc>https://berhelaw.com/landing/garden-grove-chemical-leak/</loc>\n"
        "    <lastmod>2026-05-28</lastmod>"
    ) in sitemap_text
    assert "success.html" not in sitemap_text


def test_intake_has_accessible_errors_honeypot_and_conservative_privacy_copy():
    doc = soup()
    form = doc.select_one("#caseForm")
    assert form is not None
    assert form.get("aria-labelledby") == "caseTitle"
    assert form.get("aria-describedby") == "caseFormIntro formPrivacyNote"
    assert doc.select_one("#caseTitle") is not None
    assert doc.select_one("#caseFormIntro") is not None
    assert doc.select_one("#formPrivacyNote") is not None
    summary = form.select_one("#formErrors[role='alert'][aria-live='assertive']")
    assert summary is not None
    assert summary.has_attr("hidden")
    for field in ["firstName", "lastName", "phone", "email", "consent"]:
        control = form.select_one(f"#{field}")
        error = form.select_one(f"#{field}Error.field-error")
        assert control is not None and error is not None
        described_by = str(control.get("aria-describedby") or "")
        assert f"{field}Error" in described_by
    honeypot_wrap = form.select_one("[data-honeypot-wrapper]")
    honeypot_input = form.select_one("input[name='bot-field']")
    assert honeypot_wrap is not None
    assert honeypot_wrap.get("aria-hidden") == "true"
    assert honeypot_input is not None
    assert honeypot_input.get("type") == "text"
    assert honeypot_input.get("tabindex") == "-1"
    assert honeypot_input.get("autocomplete") == "off"
    consent_label = form.select_one('label.consent[for="consent"]')
    assert consent_label is not None
    consent_text = consent_label.get_text(" ", strip=True).lower()
    assert "attorney-client relationship" in consent_text
    assert "consent is not required" not in consent_text
    privacy_note = form.select_one(".privacy-note")
    assert privacy_note is not None
    privacy_html = str(privacy_note)
    assert "privacy.html" in privacy_html
    privacy_text = privacy_note.get_text(" ", strip=True).lower()
    assert "privacy policy" in privacy_text
    assert "urgent" in privacy_text and "909-609-6685" in privacy_text


def test_mobile_cta_pair_has_intake_and_call_and_hides_for_footer_links():
    doc = soup()
    bar = doc.select_one(".mobile-cta-bar")
    assert bar is not None
    intake_link = bar.select_one('a.mobile-cta.intake[href="#intake"]')
    assert intake_link is not None
    assert intake_link.get("aria-label") == "Start Online Intake for Berhe Jones LLP case review"
    links = {a.get_text(" ", strip=True) for a in bar.select("a")}
    assert any("Start Online Intake" in text for text in links)
    assert any("Call 909-609-6685" in text for text in links)
    css = INDEX.read_text(encoding="utf-8")
    assert "body.footer-in-view .mobile-cta-bar" in css


def test_malformed_email_and_junk_phone_do_not_show_success():
    file_url = INDEX.resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path="/snap/bin/chromium")
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(file_url)
        page.evaluate("""
            () => {
              window.fetch = () => Promise.resolve({ ok: true, status: 200 });
              HTMLFormElement.prototype.submit = function () { this.dataset.nativeSubmit = 'true'; };
            }
        """)

        def fill_valid_basics():
            page.fill("#firstName", "Test")
            page.fill("#lastName", "User")
            page.fill("#phone", "9095551212")
            page.fill("#email", "test@example.com")
            page.check("#consent")

        fill_valid_basics()
        page.fill("#email", "not-an-email")
        page.click("#caseForm .submit")
        expect(page.locator("#email")).to_have_attribute("aria-invalid", "true")
        expect(page.locator("#emailError")).to_be_visible()
        expect(page.locator("#formErrors")).to_be_visible()
        assert "Received" not in page.locator("#caseForm .submit").inner_text()

        page.fill("#email", "test@example.com")
        page.fill("#phone", "111")
        page.click("#caseForm .submit")
        expect(page.locator("#phone")).to_have_attribute("aria-invalid", "true")
        expect(page.locator("#phoneError")).to_be_visible()
        assert "Received" not in page.locator("#caseForm .submit").inner_text()
        browser.close()
