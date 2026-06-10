from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
PRACTICE_AREAS = ROOT / "practice-areas" / "index.html"
CASE_REVIEW = ROOT / "free-case-review" / "index.html"


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
    assert sitemap_text.count("<lastmod>2026-05-25</lastmod>") == 3
    assert sitemap_text.count("<lastmod>2026-05-29</lastmod>") == 0
    assert sitemap_text.count("<lastmod>2026-05-30</lastmod>") == 0
    assert sitemap_text.count("<lastmod>2026-05-31</lastmod>") == 1
    assert sitemap_text.count("<lastmod>2026-06-03</lastmod>") == 18
    assert (
        "<loc>https://berhelaw.com/</loc>\n"
        "    <lastmod>2026-06-03</lastmod>"
    ) in sitemap_text
    assert (
        "<loc>https://berhelaw.com/landing/garden-grove-chemical-leak/</loc>\n"
        "    <lastmod>2026-05-31</lastmod>"
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


def test_fable_ux_pass_homepage_has_tightened_hero_markers():
    doc = soup()
    hero_locale = doc.select_one(".hero-locale")
    assert hero_locale is not None
    title = doc.select_one("#heroTitle")
    assert title is not None
    hero_text = title.get_text(" ", strip=True)
    assert "proof goes cold" in hero_text
    chip_text = {chip.get_text(" ", strip=True) for chip in doc.select(".conv-chips .chip")}
    assert "Deadline screen first" in chip_text
    assert "Proof and recovery check" in chip_text
    css = INDEX.read_text(encoding="utf-8")
    assert ".hero-locale" in css
    assert "Fable 5 UX pass" in css


def test_fable_ux_pass_practice_page_surfaces_paths_above_fold():
    doc = BeautifulSoup(PRACTICE_AREAS.read_text(encoding="utf-8"), "html.parser")
    hero = doc.select_one(".hero.practice-hero")
    assert hero is not None
    picks = hero.select(".practice-picks a")
    assert len(picks) >= 4
    pick_text = {pick.get_text(" ", strip=True) for pick in picks}
    assert any("Injury and wrongful death" in text for text in pick_text)
    assert any("Employment claims" in text for text in pick_text)
    assert any("Civil rights matters" in text for text in pick_text)
    assert any("Consumer and lemon law" in text for text in pick_text)
    screen_steps = hero.select(".screen-card .screen-step")
    assert [step.get_text(" ", strip=True) for step in screen_steps] == ["01", "02", "03"]


def test_quality_lead_case_review_page_has_guided_conversion_markers():
    doc = BeautifulSoup(CASE_REVIEW.read_text(encoding="utf-8"), "html.parser")
    text = doc.get_text(" ", strip=True)
    hero = doc.select_one(".hero.review-hero")
    assert hero is not None
    assert "Get the right case screen before proof goes cold" in text
    assert [li.get_text(" ", strip=True) for li in doc.select(".review-kicker li")] == [
        "Deadline first",
        "Fit and proof",
        "Recovery source",
    ]
    assert len(doc.select(".review-signal-grid .review-signal")) == 4
    assert "Good-fit details to include" in text
    assert "What happens next" in text
    assert "Do not send full medical records" in text
    assert "Quality lead conversion pass" in CASE_REVIEW.read_text(encoding="utf-8")


def test_quality_lead_case_review_form_and_faq_schema_are_safe():
    import json

    doc = BeautifulSoup(CASE_REVIEW.read_text(encoding="utf-8"), "html.parser")
    form = doc.select_one('form#caseReviewForm[name="case-review"]')
    assert form is not None
    assert form.get("action") == "/success.html"
    assert form.get("method") == "POST"
    assert form.has_attr("data-netlify")
    assert form.get("netlify-honeypot") == "bot-field"
    assert form.get("aria-labelledby") == "caseReviewTitle"
    assert form.get("aria-describedby") == "caseReviewUrgentNote caseReviewPrivacyNote"
    summary = doc.select_one("#summary")
    assert summary is not None
    assert summary.get("aria-describedby") == "caseReviewUrgentNote caseReviewPrivacyNote"
    assert doc.select_one("#caseType") is not None
    assert doc.select_one("#deadline") is not None
    assert doc.select_one('button.submit[type="submit"]') is not None
    assert doc.select_one('[data-honeypot-wrapper][aria-hidden="true"] input[name="bot-field"][tabindex="-1"]') is not None

    faqs = doc.select(".faq-list details")
    assert len(faqs) == 6
    faq_text = set()
    for faq in faqs:
        summary_tag = faq.select_one("summary")
        assert summary_tag is not None
        faq_text.add(summary_tag.get_text(" ", strip=True))
    assert "How much does a case review cost?" in faq_text
    assert "What if a deadline is close?" in faq_text

    schema_blocks = [json.loads(script.string) for script in doc.select('script[type="application/ld+json"]') if script.string]
    faq_schema = next(block for block in schema_blocks if block.get("@type") == "FAQPage")
    assert len(faq_schema["mainEntity"]) == 6
    assert {item["name"] for item in faq_schema["mainEntity"]} == faq_text


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
