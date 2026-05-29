import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]

PUBLIC_PAGES = {
    "/attorney-tam-berhe/": ROOT / "attorney-tam-berhe" / "index.html",
    "/case-review-process/": ROOT / "case-review-process" / "index.html",
    "/free-case-review/": ROOT / "free-case-review" / "index.html",
    "/referrals-co-counsel/": ROOT / "referrals-co-counsel" / "index.html",
    "/landing/truck-fleet-rideshare-accident-california/": ROOT / "landing" / "truck-fleet-rideshare-accident-california" / "index.html",
    "/landing/garden-grove-chemical-leak/": ROOT / "landing" / "garden-grove-chemical-leak" / "index.html",
    "/practice-areas/": ROOT / "practice-areas" / "index.html",
    "/practice-areas/personal-injury-wrongful-death/": ROOT / "practice-areas" / "personal-injury-wrongful-death" / "index.html",
    "/practice-areas/employment-workplace-claims/": ROOT / "practice-areas" / "employment-workplace-claims" / "index.html",
    "/practice-areas/civil-rights-government-accountability/": ROOT / "practice-areas" / "civil-rights-government-accountability" / "index.html",
    "/practice-areas/consumer-protection-lemon-law/": ROOT / "practice-areas" / "consumer-protection-lemon-law" / "index.html",
    "/practice-areas/insurance-bad-faith/": ROOT / "practice-areas" / "insurance-bad-faith" / "index.html",
    "/practice-areas/catastrophic-injury/": ROOT / "practice-areas" / "catastrophic-injury" / "index.html",
    "/practice-areas/select-civil-litigation/": ROOT / "practice-areas" / "select-civil-litigation" / "index.html",
    "/resources/": ROOT / "resources" / "index.html",
    "/resources/prepare-for-case-review/": ROOT / "resources" / "prepare-for-case-review" / "index.html",
    "/resources/commercial-vehicle-evidence-checklist/": ROOT / "resources" / "commercial-vehicle-evidence-checklist" / "index.html",
    "/resources/deadlines-and-early-review/": ROOT / "resources" / "deadlines-and-early-review" / "index.html",
}

SUPPORT_PAGES = {
    "/privacy.html": ROOT / "privacy.html",
    "/terms.html": ROOT / "terms.html",
    "/disclaimer.html": ROOT / "disclaimer.html",
}

SOCIAL_IMAGE = "https://berhelaw.com/images/og-berhe-jones-llp.png"
SOCIAL_IMAGE_ALT = "Berhe Jones LLP branded social preview image for California legal services."
APPROVED_REFERRER_POLICY = "strict-origin-when-cross-origin"

PROHIBITED_PUBLIC_TERMS = [
    "noindex",
    "nofollow",
    "noarchive",
    "staging",
    "staged",
    "synthetic-only",
    "synthetic qa",
    "best truck accident lawyer",
    "top uber accident attorney",
    "millions recovered",
    "guaranteed compensation",
    "guaranteed outcome",
    "certified specialist",
]


def page_doc(path: Path) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


def route_exists(href: str) -> bool:
    if not href.startswith("/") or href.startswith("//"):
        return True
    cleaned = href.split("#", 1)[0].split("?", 1)[0]
    if cleaned in {"/", "/privacy.html", "/terms.html", "/disclaimer.html", "/success.html"}:
        return True
    if cleaned in PUBLIC_PAGES:
        return True
    if cleaned.endswith(".html"):
        return (ROOT / cleaned.lstrip("/")).exists()
    return (ROOT / cleaned.lstrip("/") / "index.html").exists()


def test_stage1_pages_are_indexable_and_canonical():
    for route, path in PUBLIC_PAGES.items():
        assert path.exists(), f"missing public page for {route}"
        doc = page_doc(path)
        robots = doc.select_one('meta[name="robots"]')
        assert robots is not None, f"{route} needs robots meta"
        content = str(robots.get("content", "")).lower()
        assert "index" in content and "follow" in content
        assert "noindex" not in content and "nofollow" not in content and "noarchive" not in content
        canonical = doc.select_one('link[rel="canonical"]')
        assert canonical is not None, f"{route} needs a canonical"
        assert canonical.get("href") == f"https://berhelaw.com{route}"


def test_all_html_pages_declare_approved_referrer_policy_meta():
    headers_text = (ROOT / "_headers").read_text(encoding="utf-8")
    assert f"Referrer-Policy: {APPROVED_REFERRER_POLICY}" in headers_text

    for path in ROOT.rglob("*.html"):
        if ".git" in path.parts:
            continue
        doc = page_doc(path)
        referrer_tags = doc.select('meta[name="referrer"]')
        assert len(referrer_tags) == 1, f"{path} needs exactly one referrer policy meta tag"
        assert referrer_tags[0].get("content") == APPROVED_REFERRER_POLICY


def test_stage1_pages_are_in_sitemap_and_homepage_footer():
    sitemap_text = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    home_doc = page_doc(ROOT / "index.html")
    footer_hrefs = {str(a.get("href")) for a in home_doc.select("footer.site a[href]")}
    assert sitemap_text.count("<lastmod>2026-05-25</lastmod>") == 20
    assert sitemap_text.count("<lastmod>2026-05-29</lastmod>") == 2
    assert (
        "<loc>https://berhelaw.com/</loc>\n"
        "    <lastmod>2026-05-29</lastmod>"
    ) in sitemap_text
    assert (
        "<loc>https://berhelaw.com/landing/garden-grove-chemical-leak/</loc>\n"
        "    <lastmod>2026-05-29</lastmod>"
    ) in sitemap_text
    for route in PUBLIC_PAGES:
        assert f"https://berhelaw.com{route}" in sitemap_text
        assert route in footer_hrefs


def test_resource_hub_is_indexable_and_links_to_all_resource_guides():
    route = "/resources/"
    doc = page_doc(PUBLIC_PAGES[route])
    assert doc.select_one("h1") is not None
    assert len(doc.select("h1")) == 1
    canonical = doc.select_one('link[rel="canonical"]')
    assert canonical is not None
    assert canonical.get("href") == "https://berhelaw.com/resources/"
    hrefs = {str(a.get("href")) for a in doc.select("a[href]")}
    assert "/resources/prepare-for-case-review/" in hrefs
    assert "/resources/commercial-vehicle-evidence-checklist/" in hrefs
    assert "/resources/deadlines-and-early-review/" in hrefs


def test_standard_subpage_navigation_links_to_resource_hub():
    routes_with_standard_nav = {
        route: path
        for route, path in PUBLIC_PAGES.items()
        if route != "/landing/garden-grove-chemical-leak/"
    }
    for route, path in routes_with_standard_nav.items():
        doc = page_doc(path)
        nav = doc.select_one('nav[aria-label="Foundation pages"]')
        assert nav is not None, f"{route} needs standard exploratory navigation"
        resource_link = nav.select_one('a[href="/resources/"]')
        assert resource_link is not None, f"{route} nav should link to the resource hub"
        assert resource_link.get_text(" ", strip=True) == "Resources"
        assert route_exists(str(resource_link.get("href")))


def test_public_pages_expose_current_page_state_in_navigation_links():
    home_doc = page_doc(ROOT / "index.html")
    home_brand = home_doc.select_one('a.brand[href="#top"][aria-current="page"]')
    assert home_brand is not None, "homepage brand/home link should expose the current page"
    home_style = "\n".join(style.get_text() for style in home_doc.select("style"))
    assert '.nav-links a[aria-current="page"]' in home_style

    for route, path in PUBLIC_PAGES.items():
        if route == "/landing/garden-grove-chemical-leak/":
            continue
        doc = page_doc(path)
        current_links = doc.select(f'a[href="{route}"][aria-current="page"]')
        assert current_links, f"{route} should mark at least one exact current-page link"
        style_text = "\n".join(style.get_text() for style in doc.select("style"))
        assert '.nav-links a[aria-current="page"]' in style_text
        if route.startswith("/practice-areas/") and route != "/practice-areas/":
            assert doc.select_one(f'.practice-nav a[href="{route}"][aria-current="page"]') is not None
            assert '.practice-nav a[aria-current="page"]' in style_text


def test_stage1_pages_include_dba_and_safety_copy_without_staging_terms():
    for route, path in PUBLIC_PAGES.items():
        text = page_doc(path).get_text(" ", strip=True).lower()
        assert "berhe jones is a dba of the berhe law firm" in text
        assert "attorney-client relationship" in text
        assert "signed written agreement" in text
        assert "guarantee of outcome" in text or "does not guarantee" in text or "no guarantee" in text
        for phrase in PROHIBITED_PUBLIC_TERMS:
            assert phrase not in text, f"{route} contains prohibited public term: {phrase}"


def test_stage1_internal_links_resolve_and_include_legal_pages():
    required_legal_routes = {"/privacy.html", "/disclaimer.html", "/terms.html"}
    for route, path in PUBLIC_PAGES.items():
        doc = page_doc(path)
        raw_hrefs = [str(a.get("href")) for a in doc.select("a[href]") if a.get("href")]
        hrefs = {href.split("#", 1)[0] for href in raw_hrefs if not href.startswith(("tel:", "mailto:"))}
        assert required_legal_routes.issubset(hrefs), f"{route} missing legal-page links"
        assert all(route_exists(href) for href in hrefs), f"{route} has broken local links: {hrefs}"


def test_external_new_tab_links_include_noopener_and_noreferrer():
    for path in ROOT.rglob("*.html"):
        if ".git" in path.parts:
            continue
        doc = page_doc(path)
        for link in doc.select('a[target="_blank"][href]'):
            href = str(link.get("href"))
            if href.startswith("http") and "berhelaw.com" not in href:
                rel_tokens = set(link.get("rel") or [])
                assert "noopener" in rel_tokens, f"{path} external new-tab link needs noopener: {href}"
                assert "noreferrer" in rel_tokens, f"{path} external new-tab link needs noreferrer: {href}"



def test_support_and_success_pages_have_named_home_links():
    support_routes = {
        **SUPPORT_PAGES,
        "/success.html": ROOT / "success.html",
    }
    for route, path in support_routes.items():
        doc = page_doc(path)
        brand_home = doc.select_one('header .brand[href="/"]')
        back_home = doc.select_one('main .back[href="/"]')
        assert brand_home is not None, f"{route} needs a header home link"
        assert back_home is not None, f"{route} needs a back-home link"
        assert brand_home.get("aria-label") == "Berhe Jones LLP home"
        assert back_home.get("aria-label") == "Back to Berhe Jones LLP home"


def test_all_public_support_and_success_pages_show_brand_logo_in_header():
    pages = {
        "/": ROOT / "index.html",
        **PUBLIC_PAGES,
        **SUPPORT_PAGES,
        "/success.html": ROOT / "success.html",
    }
    allowed_logo_paths = {
        "/images/berhe-jones-llp-logo.png",
        "/images/berhe-jones-llp-logo-reverse.png",
    }
    for route, path in pages.items():
        doc = page_doc(path)
        header_logo = doc.select_one("header .brand img.brand-logo")
        assert header_logo is not None, f"{route} needs the Berhe Jones LLP logo in the header"
        assert header_logo.get("src") in allowed_logo_paths
        assert header_logo.get("alt") == "Berhe Jones LLP"
        assert header_logo.get("width") == "1305"
        assert header_logo.get("height") == "308"
        assert header_logo.get("decoding") == "async"


def test_html_does_not_contain_escaped_link_attributes():
    for path in ROOT.rglob("*.html"):
        if ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert 'href=\\"' not in text, f"{path} contains escaped href markup"
        assert 'target=\\"' not in text, f"{path} contains escaped target markup"
        assert 'rel=\\"' not in text, f"{path} contains escaped rel markup"


def test_every_input_declares_explicit_type():
    for path in ROOT.rglob("*.html"):
        if ".git" in path.parts:
            continue
        doc = page_doc(path)
        for input_el in doc.select("input"):
            name = input_el.get("name") or input_el.get("id") or str(input_el)[:80]
            assert input_el.get("type"), f"{path} input {name} should declare an explicit type"


def test_garden_grove_incident_media_images_are_performance_safe():
    doc = page_doc(PUBLIC_PAGES["/landing/garden-grove-chemical-leak/"])
    hero_img = doc.select_one(".hero-media img")
    assert hero_img is not None
    assert hero_img.get("fetchpriority") == "high"
    assert hero_img.get("loading") == "eager"
    assert hero_img.get("decoding") == "async"
    assert hero_img.get("width") and hero_img.get("height")
    assert str(hero_img.get("alt") or "").strip(), "hero incident photo needs descriptive alt text"

    gallery_images = doc.select("#incident-photos .media-card img")
    assert len(gallery_images) == 3
    for img in gallery_images:
        assert img.get("loading") == "lazy", "below-fold incident gallery images should lazy-load"
        assert img.get("decoding") == "async"
        assert img.get("width") and img.get("height"), "incident images need intrinsic dimensions"
        assert str(img.get("alt") or "").strip(), "incident images need factual alt text"


def test_garden_grove_mobile_sticky_call_has_specific_accessible_name():
    doc = page_doc(PUBLIC_PAGES["/landing/garden-grove-chemical-leak/"])
    sticky_screening = doc.select_one('.mobile-sticky-cta a[href="#case-review"]')
    assert sticky_screening is not None
    assert sticky_screening.get_text(" ", strip=True) == "Start screening"
    assert sticky_screening.get("aria-label") == "Start screening for Garden Grove chemical incident case review"
    sticky_call = doc.select_one('.mobile-sticky-cta a[href="tel:+19096096685"]')
    assert sticky_call is not None
    assert sticky_call.get_text(" ", strip=True) == "Call now"
    assert sticky_call.get("aria-label") == "Call Berhe Jones LLP at 909-609-6685"


def test_homepage_mobile_intake_cta_has_specific_accessible_name():
    doc = page_doc(ROOT / "index.html")
    intake_link = doc.select_one('.mobile-cta-bar a.mobile-cta.intake[href="#intake"]')
    assert intake_link is not None
    assert intake_link.get_text(" ", strip=True) == "Start Online Intake"
    assert intake_link.get("aria-label") == "Start Online Intake for Berhe Jones LLP case review"


def test_homepage_consent_checkbox_has_explicit_label():
    doc = page_doc(ROOT / "index.html")
    form = doc.select_one("#caseForm")
    assert form is not None
    consent = form.select_one('#consent[name="consent"][type="checkbox"]')
    assert consent is not None
    consent_label = form.select_one('label.consent[for="consent"]')
    assert consent_label is not None
    assert "attorney-client relationship" in consent_label.get_text(" ", strip=True).lower()


def test_homepage_intake_form_references_visible_privacy_notice():
    doc = page_doc(ROOT / "index.html")
    form = doc.select_one("#caseForm")
    assert form is not None
    assert form.get("aria-labelledby") == "caseTitle"
    assert form.get("aria-describedby") == "caseFormIntro formPrivacyNote"
    assert doc.select_one("#caseTitle") is not None
    assert doc.select_one("#caseFormIntro") is not None
    privacy_note = doc.select_one("#formPrivacyNote.privacy-note")
    assert privacy_note is not None
    privacy_text = privacy_note.get_text(" ", strip=True).lower()
    assert "attorney-client relationship" in privacy_text
    assert "do not send highly sensitive details" in privacy_text
    assert "urgent or deadline-sensitive" in privacy_text
    message = form.select_one('textarea#message[name="message"]')
    assert message is not None
    assert message.get("aria-describedby") == "msgHint formPrivacyNote"
    hint = form.select_one("#msgHint")
    assert hint is not None
    hint_text = hint.get_text(" ", strip=True).lower()
    assert "conflict-safe summary" in hint_text
    assert "do not include privileged documents" in hint_text


def test_visible_public_intake_required_fields_expose_aria_required():
    form_specs = {
        "/": (ROOT / "index.html", "form#caseForm"),
        "/free-case-review/": (
            PUBLIC_PAGES["/free-case-review/"],
            'form[name="case-review"][aria-labelledby="caseReviewTitle"]',
        ),
        "/landing/truck-fleet-rideshare-accident-california/": (
            PUBLIC_PAGES["/landing/truck-fleet-rideshare-accident-california/"],
            'form[name="case-review"][aria-labelledby="caseReviewTitle"]',
        ),
        "/landing/garden-grove-chemical-leak/": (
            PUBLIC_PAGES["/landing/garden-grove-chemical-leak/"],
            'form[name="garden-grove-case-review"][aria-labelledby="gardenGroveCaseReviewTitle"]',
        ),
    }
    expected_required_names = {
        "/": {"firstName", "lastName", "phone", "email", "consent"},
        "/free-case-review/": {"firstName", "lastName", "phone", "email", "summary", "consent"},
        "/landing/truck-fleet-rideshare-accident-california/": {
            "firstName",
            "lastName",
            "phone",
            "email",
            "summary",
            "consent",
        },
        "/landing/garden-grove-chemical-leak/": {
            "firstName",
            "lastName",
            "phone",
            "email",
            "summary",
            "consent",
        },
    }
    for route, (path, selector) in form_specs.items():
        doc = page_doc(path)
        form = doc.select_one(selector)
        assert form is not None, f"{route} needs the visible public intake form"
        required_controls = form.select("input[required], textarea[required], select[required]")
        required_names = {str(control.get("name")) for control in required_controls}
        assert expected_required_names[route] == required_names
        for control in required_controls:
            control_name = str(control.get("name"))
            assert control.get("aria-required") == "true", (
                f"{route} required control {control_name} should expose aria-required"
            )


def test_public_html_has_working_phone_links_and_valid_markup_basics():
    expected_phone_href = "tel:+19096096685"
    expected_fax_href = "tel:+19098906043"
    expected_tel_labels = {
        expected_phone_href: "Call Berhe Jones LLP at 909-609-6685",
        expected_fax_href: "Fax Berhe Jones LLP at 909-890-6043",
    }
    redacted_tel_pattern = re.compile(r'tel:[^"\']*\*')
    for path in ROOT.rglob("*.html"):
        html = path.read_text(encoding="utf-8")
        assert not redacted_tel_pattern.search(html), (
            f"{path} contains a redacted/non-dialable tel: link"
        )
        assert "<p><p>" not in html and "</p></p>" not in html, f"{path} contains nested paragraph markup"
        assert 'id=""' not in html, f"{path} contains an empty id attribute"
        doc = BeautifulSoup(html, "html.parser")
        for tel in doc.select('a[href^="tel:"]'):
            href = str(tel.get("href"))
            assert href in expected_tel_labels, f"{path} has unexpected tel link: {href}"
            assert tel.get("aria-label") == expected_tel_labels[href], (
                f"{path} tel link should expose a specific accessible name: {href}"
            )


def test_public_phone_form_fields_trigger_mobile_phone_keyboards():
    for path in ROOT.rglob("*.html"):
        doc = page_doc(path)
        for phone in doc.select('input[type="tel"]'):
            assert phone.get("autocomplete") == "tel", f"{path} phone field should preserve tel autocomplete"
            assert phone.get("inputmode") == "tel", f"{path} phone field should request the mobile phone keyboard"


def test_public_email_form_fields_trigger_mobile_email_keyboards():
    for path in ROOT.rglob("*.html"):
        doc = page_doc(path)
        for email in doc.select('input[type="email"]'):
            assert email.get("autocomplete") == "email", f"{path} email field should preserve email autocomplete"
            assert email.get("inputmode") == "email", f"{path} email field should request the mobile email keyboard"


def test_visible_public_intake_text_fields_have_mobile_enter_key_hints():
    form_specs = {
        "/": (
            ROOT / "index.html",
            "form#caseForm",
            {
                "firstName": "next",
                "lastName": "next",
                "phone": "next",
                "email": "next",
                "message": "send",
            },
        ),
        "/free-case-review/": (
            PUBLIC_PAGES["/free-case-review/"],
            'form[name="case-review"][aria-labelledby="caseReviewTitle"]',
            {
                "firstName": "next",
                "lastName": "next",
                "phone": "next",
                "email": "next",
                "county": "next",
                "summary": "send",
            },
        ),
        "/landing/truck-fleet-rideshare-accident-california/": (
            PUBLIC_PAGES["/landing/truck-fleet-rideshare-accident-california/"],
            'form[name="case-review"][aria-labelledby="caseReviewTitle"]',
            {
                "firstName": "next",
                "lastName": "next",
                "phone": "next",
                "email": "next",
                "county": "next",
                "summary": "send",
            },
        ),
        "/landing/garden-grove-chemical-leak/": (
            PUBLIC_PAGES["/landing/garden-grove-chemical-leak/"],
            'form[name="garden-grove-case-review"][aria-labelledby="gardenGroveCaseReviewTitle"]',
            {
                "firstName": "next",
                "lastName": "next",
                "phone": "next",
                "email": "next",
                "affectedAddress": "next",
                "summary": "send",
            },
        ),
    }
    for route, (path, selector, expected_hints) in form_specs.items():
        doc = page_doc(path)
        form = doc.select_one(selector)
        assert form is not None, f"{route} needs the visible public intake form"
        for field_id, expected_hint in expected_hints.items():
            field = form.select_one(f"#{field_id}")
            assert field is not None, f"{route} needs #{field_id} in its visible intake form"
            assert field.get("enterkeyhint") == expected_hint, (
                f"{route} #{field_id} should request the mobile {expected_hint!r} enter key"
            )


def test_public_buttons_declare_explicit_safe_type():
    for path in ROOT.rglob("*.html"):
        doc = page_doc(path)
        for button in doc.select("button"):
            button_type = str(button.get("type") or "")
            assert button_type in {"button", "submit"}, (
                f"{path} button '{button.get_text(' ', strip=True)}' needs an explicit safe type"
            )
            if button_type == "submit":
                assert button.find_parent("form") is not None, f"{path} submit button must live inside a form"
            else:
                assert button_type == "button", f"{path} non-submit controls should be type=button"


def test_case_review_forms_expose_complete_mobile_autofill_contract():
    form_pages = [
        PUBLIC_PAGES["/free-case-review/"],
        PUBLIC_PAGES["/landing/truck-fleet-rideshare-accident-california/"],
    ]
    expected_fields = {
        "firstName": {"type": "text", "autocomplete": "given-name"},
        "lastName": {"type": "text", "autocomplete": "family-name"},
        "email": {"type": "email", "autocomplete": "email", "inputmode": "email"},
        "phone": {"type": "tel", "autocomplete": "tel", "inputmode": "tel"},
        "county": {"type": "text", "autocomplete": "address-level2"},
    }
    for path in form_pages:
        doc = page_doc(path)
        form = doc.select_one('form[name="case-review"]')
        assert form is not None, f"{path} needs the standard case review form"
        for field_id, attributes in expected_fields.items():
            field = form.select_one(f"#{field_id}")
            label = form.select_one(f'label[for="{field_id}"]')
            assert field is not None, f"{path} missing #{field_id}"
            assert label is not None, f"{path} field #{field_id} needs an explicit label"
            for attribute, expected in attributes.items():
                assert field.get(attribute) == expected, f"{path} #{field_id} needs {attribute}={expected}"
        consent = form.select_one('#consent[name="consent"][type="checkbox"]')
        assert consent is not None, f"{path} consent checkbox needs a stable id/name/type"
        assert form.select_one('label.consent[for="consent"]') is not None, f"{path} consent checkbox needs an explicit label"
        summary = form.select_one('textarea#summary[name="summary"]')
        assert summary is not None, f"{path} summary textarea needs a stable id/name"
        assert summary.get("aria-describedby") == "caseReviewPrivacyNote", (
            f"{path} summary textarea should reference the visible privacy notice"
        )


def test_garden_grove_form_exposes_complete_mobile_autofill_contract():
    path = PUBLIC_PAGES["/landing/garden-grove-chemical-leak/"]
    doc = page_doc(path)
    form = doc.select_one('form[name="garden-grove-case-review"]')
    assert form is not None, "Garden Grove page needs its live screening form"
    expected_fields = {
        "firstName": {"type": "text", "autocomplete": "given-name"},
        "lastName": {"type": "text", "autocomplete": "family-name"},
        "email": {"type": "email", "autocomplete": "email", "inputmode": "email"},
        "phone": {"type": "tel", "autocomplete": "tel", "inputmode": "tel"},
        "affectedAddress": {"type": "text"},
    }
    for field_id, attributes in expected_fields.items():
        field = form.select_one(f"#{field_id}")
        label = form.select_one(f'label[for="{field_id}"]')
        assert field is not None, f"Garden Grove form missing #{field_id}"
        assert label is not None, f"Garden Grove #{field_id} needs an explicit label"
        for attribute, expected in attributes.items():
            assert field.get(attribute) == expected, f"Garden Grove #{field_id} needs {attribute}={expected}"
    consent = form.select_one('#gardenGroveConsent[name="consent"][type="checkbox"]')
    assert consent is not None, "Garden Grove consent checkbox needs a stable id/name/type"
    assert form.select_one('label.consent[for="gardenGroveConsent"]') is not None
    summary = form.select_one('textarea#summary[name="summary"]')
    assert summary is not None, "Garden Grove summary textarea needs a stable id/name"
    assert summary.get("aria-describedby") == "gardenGroveUrgentNotice gardenGrovePrivacyNotice"


def test_public_images_have_intrinsic_dimensions_and_async_decoding():
    for path in ROOT.rglob("*.html"):
        doc = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        for img in doc.select("img"):
            assert img.get("width") and img.get("height"), f"{path} image {img.get('src')} needs intrinsic dimensions"
            assert img.get("decoding") == "async", f"{path} image {img.get('src')} should decode async"


def test_stage1_forms_are_live_netlify_intake_without_uploads():
    form_pages = [
        (PUBLIC_PAGES["/free-case-review/"], "case-review"),
        (PUBLIC_PAGES["/landing/truck-fleet-rideshare-accident-california/"], "case-review"),
        (PUBLIC_PAGES["/landing/garden-grove-chemical-leak/"], "garden-grove-case-review"),
    ]
    for path, form_name in form_pages:
        doc = page_doc(path)
        form = doc.select_one(f'form[name="{form_name}"]')
        assert form is not None, f"{path} needs live {form_name} form"
        assert str(form.get("method", "")).upper() == "POST"
        expected_action = (
            "https://docs.google.com/forms/d/e/1FAIpQLSeqsUsCXzzYV482zQLpw23RYZHnQqvX_EgK0Jjj4PjJMvDJaQ/formResponse"
            if form_name == "garden-grove-case-review"
            else "/success.html"
        )
        assert form.get("action") == expected_action
        assert form.get("enctype") == "application/x-www-form-urlencoded"
        assert form.get("data-netlify") == "true"
        assert form.has_attr("netlify")
        assert doc.select_one(f'input[name="form-name"][value="{form_name}"]') is not None
        assert not doc.select_one('input[type="file"]')
        honeypot = form.select_one('input[name="bot-field"]')
        assert honeypot is not None
        assert honeypot.get("type") == "text"
        assert honeypot.get("autocomplete") == "off"
        assert honeypot.get("tabindex") == "-1"
        text = form.get_text(" ", strip=True).lower()
        assert "do not include privileged" in text
        assert "attorney-client relationship" in text
        if form_name == "case-review":
            assert form.get("aria-labelledby") == "caseReviewTitle"
            assert form.get("aria-describedby") == "caseReviewPrivacyNote"
            assert doc.select_one("#caseReviewTitle") is not None
            assert doc.select_one("#caseReviewPrivacyNote.notice") is not None
        if form_name == "garden-grove-case-review":
            assert form.get("aria-labelledby") == "gardenGroveCaseReviewTitle"
            assert form.get("aria-describedby") == "gardenGroveUrgentNotice gardenGrovePrivacyNotice"
            assert doc.select_one("#gardenGroveCaseReviewTitle") is not None
            assert doc.select_one("#gardenGrovePrivacyNotice.notice") is not None
            assert doc.select_one("#gardenGroveUrgentNotice.notice") is not None


def test_homepage_declares_netlify_form_detection_stubs():
    doc = page_doc(ROOT / "index.html")
    hidden_forms = doc.select('div[hidden][aria-hidden="true"] form')
    names = {str(form.get("name")) for form in hidden_forms}
    assert {"case-review", "garden-grove-case-review", "garden-grove-updates"}.issubset(names)
    for name in ["case-review", "garden-grove-case-review", "garden-grove-updates"]:
        form = doc.select_one(f'div[hidden] form[name="{name}"]')
        assert form is not None
        assert str(form.get("method", "")).upper() == "POST"
        assert form.get("action") == "/success.html"
        assert form.get("enctype") == "application/x-www-form-urlencoded"
        assert form.get("data-netlify") == "true"
        assert form.has_attr("netlify")
        assert form.select_one(f'input[name="form-name"][value="{name}"]') is not None
        honeypot_name = str(form.get("netlify-honeypot") or "")
        assert honeypot_name
        honeypot = form.select_one(f'input[name="{honeypot_name}"]')
        assert honeypot is not None
        assert honeypot.get("type") == "text"
        assert honeypot.get("tabindex") == "-1"
        assert honeypot.get("autocomplete") == "off"


def test_html_pages_have_keyboard_skip_link_to_main_content():
    for path in ROOT.rglob("*.html"):
        if ".git" in path.parts:
            continue
        doc = page_doc(path)
        skip_link = doc.select_one('a.skip-link[href="#main"]')
        assert skip_link is not None, f"{path} needs a skip-to-main link"
        assert skip_link.get_text(" ", strip=True) == "Skip to main content"
        main = doc.select("main#main")
        assert len(main) == 1, f"{path} needs exactly one main#main landmark"
        style_text = "\n".join(style.get_text() for style in doc.select("style"))
        assert ".skip-link:focus" in style_text, f"{path} needs visible focus styling for skip link"


def test_html_pages_have_consistent_browser_branding_metadata():
    for path in ROOT.rglob("*.html"):
        if ".git" in path.parts:
            continue
        doc = page_doc(path)
        theme_tags = doc.select('meta[name="theme-color"]')
        assert len(theme_tags) == 1, f"{path} needs exactly one theme-color meta tag"
        assert theme_tags[0].get("content") == "#15212e"

        icon_tags = doc.select('link[rel="icon"]')
        assert len(icon_tags) == 1, f"{path} needs exactly one favicon link"
        assert icon_tags[0].get("href") == "/favicon.ico"
        assert icon_tags[0].get("sizes") == "any"

        apple_icons = doc.select('link[rel="apple-touch-icon"]')
        assert len(apple_icons) == 1, f"{path} needs exactly one apple-touch-icon link"
        assert apple_icons[0].get("href") == "/images/berhe-jones-icon.png"


def test_public_pages_have_complete_social_share_metadata():
    for route, path in {"/": ROOT / "index.html", **PUBLIC_PAGES, **SUPPORT_PAGES}.items():
        doc = page_doc(path)
        title = doc.select_one("title")
        description = doc.select_one('meta[name="description"]')
        canonical = doc.select_one('link[rel="canonical"]')
        assert title is not None, f"{route} needs a title"
        assert description is not None, f"{route} needs a meta description"
        assert canonical is not None, f"{route} needs a canonical"

        expected = {
            'meta[property="og:title"]': title.get_text(strip=True),
            'meta[property="og:description"]': description.get("content"),
            'meta[property="og:type"]': "website",
            'meta[property="og:url"]': canonical.get("href"),
            'meta[property="og:site_name"]': "Berhe Jones LLP",
            'meta[property="og:locale"]': "en_US",
            'meta[property="og:image"]': SOCIAL_IMAGE,
            'meta[property="og:image:width"]': "1200",
            'meta[property="og:image:height"]': "630",
            'meta[property="og:image:alt"]': SOCIAL_IMAGE_ALT,
            'meta[name="twitter:card"]': "summary_large_image",
            'meta[name="twitter:title"]': title.get_text(strip=True),
            'meta[name="twitter:description"]': description.get("content"),
            'meta[name="twitter:image"]': SOCIAL_IMAGE,
            'meta[name="twitter:image:alt"]': SOCIAL_IMAGE_ALT,
        }
        for selector, expected_content in expected.items():
            tags = doc.select(selector)
            assert len(tags) == 1, f"{route} needs exactly one {selector} tag"
            assert tags[0].get("content") == expected_content, f"{route} has wrong {selector} content"


def test_public_sitemap_pages_have_single_breadcrumb_schema():
    sitemap_text = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    public_routes = ["/"] + list(PUBLIC_PAGES) + list(SUPPORT_PAGES)
    for route in public_routes:
        assert f"https://berhelaw.com{route}" in sitemap_text

    for route, path in {**PUBLIC_PAGES, **SUPPORT_PAGES}.items():
        doc = page_doc(path)
        canonical = doc.select_one('link[rel="canonical"]')
        assert canonical is not None, f"{route} needs canonical URL for breadcrumb schema"

        breadcrumb_nodes = []
        for script in doc.select('script[type="application/ld+json"]'):
            data = json.loads(script.get_text())
            nodes = data if isinstance(data, list) else [data]
            breadcrumb_nodes.extend(
                node
                for node in nodes
                if isinstance(node, dict) and node.get("@type") == "BreadcrumbList"
            )

        assert len(breadcrumb_nodes) == 1, f"{route} needs exactly one BreadcrumbList schema"
        items = breadcrumb_nodes[0].get("itemListElement")
        assert isinstance(items, list) and len(items) >= 2, f"{route} breadcrumb needs home and current page"
        assert items[0].get("position") == 1
        assert items[0].get("name") == "Home"
        assert items[0].get("item") == "https://berhelaw.com/"
        assert items[-1].get("position") == len(items)
        assert items[-1].get("item") == canonical.get("href")


def test_practice_area_pages_have_substantive_safe_copy():
    practice_routes = [route for route in PUBLIC_PAGES if route.startswith("/practice-areas/")]
    assert len(practice_routes) == 8
    for route in practice_routes:
        html = PUBLIC_PAGES[route].read_text(encoding="utf-8")
        assert "—" not in html
        doc = page_doc(PUBLIC_PAGES[route])
        text = doc.get_text(" ", strip=True).lower()
        assert len(text.split()) >= 450, f"{route} copy is too thin"
        assert "deadlines" in text
        assert "signed written agreement" in text
        assert "attorney-client relationship" in text
        assert "no guarantee" in text or "does not guarantee" in text
        assert doc.select_one('a[href="/free-case-review/"]') is not None


def test_garden_grove_resource_center_keeps_public_ux_and_safety_markers():
    route = "/landing/garden-grove-chemical-leak/"
    path = PUBLIC_PAGES[route]
    html = path.read_text(encoding="utf-8")
    doc = page_doc(path)
    text = doc.get_text(" ", strip=True).lower()

    assert "telegram" not in text, "Public page should not expose internal Telegram alert routing"
    assert doc.select_one('button.nav-toggle[aria-controls="primaryNavLinks"]') is not None
    assert doc.select_one('#primaryNavLinks') is not None
    assert doc.select_one('#updatesFeed') is not None
    assert doc.select_one('#resourceGrid') is not None
    assert doc.select_one('#screeningStatus[role="status"][aria-live="polite"]') is not None
    assert "public-source update center" in text
    assert "no affiliation with emergency officials, gkn aerospace, or class action counsel" in text
    assert "no attorney-client relationship" in text
    assert "signed written agreement" in text

    updates_path = ROOT / "data" / "garden-grove-chemical-leak-updates.json"
    data = json.loads(updates_path.read_text(encoding="utf-8"))
    assert data["statusLabel"] == "Public-source update center"
    assert len(data["updates"]) <= 8
    assert len(data["updates"]) == 8, "public incident feed should render the full capped update set"
    feed_times = [u.get("timeUtc") for u in data["updates"]]
    assert feed_times == sorted(feed_times, reverse=True), "public incident feed should remain latest-first before the 8-item cap is rendered"
    assert any(u.get("category") == "Legal-action status" for u in data["updates"]), "at least one legal-action status item should remain visible in the capped public feed"
    latest_update = data["updates"][0]
    assert latest_update.get("sourceUrl") == "https://kfiam640.iheart.com/content/2026-05-28-legal-troubles-mount-for-garden-grove-aerospace-facility/"
    assert latest_update.get("category") == "Legal-action status"
    latest_summary = latest_update.get("summary", "").lower()
    assert "29 filings in orange county superior court" in latest_summary
    assert "about eight in federal court" in latest_summary
    assert "guadarrama" in latest_summary
    assert "30-2026-01572329-cu-po-cxc" in latest_summary
    assert "roa #2" in latest_summary
    assert "judge william d. claster" in latest_summary
    assert "not findings of liability" in latest_summary
    assert "not claiming affiliation" in latest_summary

    business_resource_updates = [
        u for u in data["updates"] if u.get("sourceUrl") == "https://ggcity.org/hazmat-incident/business-resources"
    ]
    assert len(business_resource_updates) == 1, "City business-resource update should stay visible after the legal-action count update"
    business_summary = business_resource_updates[0].get("summary", "").lower()
    assert business_resource_updates[0].get("category") == "Recovery / business resources"
    assert "last updated may 28 at 4:15 p.m." in business_summary
    assert "sba assistance worksheet" in business_summary
    assert "orange county sheriff's eoc team" in business_summary
    assert "may 29, 2026 at 9:00 a.m." in business_summary
    assert "english, spanish, vietnamese, and korean" in business_summary
    assert "federal, state, county, and local resources" in business_summary
    assert "not a compensation promise" in business_summary
    assert "not a legal finding" in business_summary
    assert "not a representation offer" in business_summary

    latimes_accountability_updates = [
        u
        for u in data["updates"]
        if u.get("sourceUrl")
        == "https://www.latimes.com/california/story/2026-05-28/politicians-demand-accountability-from-gkn-aerospace-after-hazmat-crisis"
    ]
    assert len(latimes_accountability_updates) == 1, "L.A. Times accountability item should stay visible after the newer ABC7 live update"
    latimes_summary = latimes_accountability_updates[0].get("summary", "").lower()
    assert "orange county board of supervisors" in latimes_summary
    assert "compensate evacuated residents" in latimes_summary
    assert "robert garcia" in latimes_summary
    assert "derek tran" in latimes_summary
    assert "produce documents by june 10" in latimes_summary
    assert "facility inspections" in latimes_summary
    assert "compliance history" in latimes_summary
    assert "maintenance logs" in latimes_summary
    assert "emergency protocols" in latimes_summary
    assert "district attorney todd spitzer opened a criminal investigation" in latimes_summary
    assert "more than half a dozen orange county superior court lawsuits" in latimes_summary
    assert "not findings of liability" in latimes_summary
    assert "not claiming affiliation" in latimes_summary

    older_latimes_business_updates = [
        u
        for u in data["updates"]
        if u.get("sourceUrl")
        == "https://www.latimes.com/business/story/2026-05-28/garden-grove-chemical-leak-plant-faces-lawsuits-supply-disruption"
    ]
    assert len(older_latimes_business_updates) == 0, "The newer L.A. Times accountability item should replace the older same-day business/litigation item under the 8-update cap"

    city_survey_updates = [
        u for u in data["updates"] if u.get("sourceUrl") == "https://ggcity.org/hazmat-incident/survey"
    ]
    assert len(city_survey_updates) == 1, "City recovery-survey update should stay visible after the L.A. Times update"
    city_survey_update = city_survey_updates[0]
    assert city_survey_update.get("category") == "Recovery / official survey"
    city_survey_summary = city_survey_update.get("summary", "").lower()
    assert "hazardous-materials incident survey" in city_survey_summary
    assert "residents, businesses, and community members" in city_survey_summary
    assert "chemical emergency and evacuation orders" in city_survey_summary
    assert "displacement, housing, business interruption" in city_survey_summary
    assert "unmet needs" in city_survey_summary
    assert "not a compensation promise" in city_survey_summary
    assert "claim approval" in city_survey_summary
    assert "berhe jones affiliation" in city_survey_summary

    abc7_updates = [
        u
        for u in data["updates"]
        if u.get("sourceUrl")
        == "https://abc7.com/live-updates/garden-grove-chemical-tank-emergency-leaking-toxic-chemicals-orange-county-will-spill-explode-officials-say/19152918/"
    ]
    assert len(abc7_updates) == 1, "ABC7 company/response item should stay visible after the City recovery-survey update"
    abc7_update = abc7_updates[0]
    assert (
        abc7_update.get("sourceUrl")
        == "https://abc7.com/live-updates/garden-grove-chemical-tank-emergency-leaking-toxic-chemicals-orange-county-will-spill-explode-officials-say/19152918/"
    )
    assert abc7_update.get("category") == "Company / response status"
    abc7_summary = abc7_update.get("summary", "").lower()
    assert "gkn aerospace released a statement" in abc7_summary
    assert "uncertainty and disruption" in abc7_summary
    assert "committed to understanding what occurred" in abc7_summary
    assert "all roads closed because of the incident had reopened" in abc7_summary
    assert "cleanup/removal planning" in abc7_summary
    assert "20 monitoring devices" in abc7_summary
    assert "exceedances above action levels" in abc7_summary
    assert "not an admission" in abc7_summary
    assert "not a claims process" in abc7_summary
    assert "finding of legal responsibility" in abc7_summary

    official_status_updates = [
        u
        for u in data["updates"]
        if u.get("sourceUrl")
        == "https://www.ocgov.com/page/garden-grove-chemical-spill-incident"
    ]
    assert len(official_status_updates) == 1, "County/City official status item should stay visible after the company-statement update"
    official_summary = official_status_updates[0].get("summary", "").lower()
    assert "care & shelter locations were closed" in official_summary
    assert "all road closures were lifted" in official_summary
    assert "150 feet around the gkn facility" in official_summary
    assert "all evacuation orders have been lifted" in official_summary
    assert "no chemical leak" in official_summary
    assert "no threat of explosion or fire" in official_summary
    assert "lampson avenue and western avenue are now open" in official_summary
    assert "sba assistance worksheet" in official_summary
    assert "small-business recovery" in official_summary
    assert "not a court finding" in official_summary

    caloes_updates = [
        u
        for u in data["updates"]
        if u.get("sourceUrl")
        == "https://www.news.caloes.ca.gov/community-resources-for-garden-grove-hazmat-incident/"
    ]
    assert len(caloes_updates) == 0, "County/City status now carries the shelter-closure status, so Cal OES can fall out of the 8-item cap"

    voice_updates = [
        u
        for u in data["updates"]
        if u.get("sourceUrl")
        == "https://voiceofoc.org/2026/05/oc-residents-impacted-by-faulty-chemical-tank-may-get-reimbursed/"
    ]
    assert len(voice_updates) == 0, "The time-sensitive City/SBDC business-resource webinar can push the older Voice of OC recovery/claims item out of the 8-update cap"

    nbc_business_updates = [
        u
        for u in data["updates"]
        if u.get("sourceUrl")
        == "https://www.nbclosangeles.com/news/local/garden-grove-chemical-tank-whats-next-financial-fallout/3895967/"
    ]
    assert len(nbc_business_updates) == 1, "NBC Los Angeles financial-impact item should stay visible in capped feed"
    assert nbc_business_updates[0].get("category") == "Recovery / business impact"
    nbc_summary = nbc_business_updates[0].get("summary", "").lower()
    assert "several businesses" in nbc_summary
    assert "losses above $10,000" in nbc_summary
    assert "$35,000 to $40,000" in nbc_summary
    assert "hotel, travel, food, and gas costs" in nbc_summary
    assert "orange county health and epa" in nbc_summary
    assert "waste removal" in nbc_summary
    assert "not a compensation promise" in nbc_summary
    assert "not a court finding" in nbc_summary
    assert "preserve receipts" in nbc_summary

    ggusd_updates = [
        u
        for u in data["updates"]
        if u.get("sourceUrl")
        == "https://www.ggusd.us/news/evacuation-orders-lifted-all-schools-reopen-tomorrowevacuation-orders-lifted-all-schools-reopen-tomorrow"
    ]
    assert len(ggusd_updates) == 0, "The newer NBC financial-impact item can push the final-day GGUSD school-operations item out of the 8-update cap"

    oc_register_updates = [
        u
        for u in data["updates"]
        if u.get("sourceUrl")
        == "https://www.ocregister.com/2026/05/26/chemical-tank-in-garden-grove-at-92-degrees-tuesday-a-m-crews-work-to-lower-it/"
    ]
    assert len(oc_register_updates) == 0, "The newer L.A. Times business/litigation item carries the cooling-system reference, so the older OC Register / OCFA item can fall out of the 8-update cap"

    official_city_updates = [u for u in data["updates"] if u.get("sourceUrl") == "https://ggcity.org/emergency"]
    assert len(official_city_updates) == 0, "The newer County/City status item should replace the older City duplicate under the 8-update cap"
    oc_register_lawsuit_updates = [
        u
        for u in data["updates"]
        if u.get("sourceUrl")
        == "https://www.ocregister.com/2026/05/26/70-people-suing-garden-grove-chemical-tank-owner-over-crisis-as-of-tuesday/"
    ]
    assert len(oc_register_lawsuit_updates) == 0, "City recovery-survey update can push the older OC Register / PacerMonitor legal-action item out of the 8-update cap"

    zimmerman_reed_updates = [
        u
        for u in data["updates"]
        if u.get("sourceUrl")
        == "https://kfiam640.iheart.com/content/2026-05-28-legal-troubles-mount-for-garden-grove-aerospace-facility/"
    ]
    assert len(zimmerman_reed_updates) == 1, "New KFI/CNS litigation-count and Guadarrama conformed-complaint update should stay visible in capped feed"
    assert zimmerman_reed_updates[0].get("category") == "Legal-action status"
    zimmerman_summary = zimmerman_reed_updates[0].get("summary", "").lower()
    assert "guadarrama" in zimmerman_summary
    assert "zimmerman reed" in zimmerman_reed_updates[0].get("sourceLabel", "").lower()
    assert "orange county superior court" in zimmerman_summary
    assert "30-2026-01572329-cu-po-cxc" in zimmerman_summary
    assert "electronically filed may 26, 2026 at 8:00 a.m." in zimmerman_summary
    assert "judge william d. claster" in zimmerman_summary
    assert "29 filings" in zimmerman_summary
    assert "about eight in federal court" in zimmerman_summary
    assert "unfair competition" in zimmerman_summary
    assert "federal filing counts were not individually docket-verified" in zimmerman_summary
    assert "not claiming affiliation" in zimmerman_summary

    old_zimmerman_pr_updates = [
        u
        for u in data["updates"]
        if u.get("sourceUrl")
        == "https://www.prnewswire.com/news-releases/orange-county-residents-file-class-action-over-garden-grove-chemical-tank-crisis-302783544.html"
    ]
    assert len(old_zimmerman_pr_updates) == 0, "The new conformed-complaint/count update should replace the older PRNewswire-only Zimmerman item under the 8-update cap"

    dicello_updates = [
        u
        for u in data["updates"]
        if u.get("sourceUrl")
        == "https://dicellolevitt.com/dicello-levitt-and-co-counsel-file-class-action-against-gkn-aerospace-over-garden-grove-chemical-emergency/"
    ]
    assert len(dicello_updates) == 1, "DiCello Levitt Carey complaint update should stay visible in capped feed"
    assert dicello_updates[0].get("category") == "Legal-action status"
    dicello_summary = dicello_updates[0].get("summary", "").lower()
    assert "courtney carey" in dicello_summary
    assert "complaint pdf" in dicello_summary
    assert "case no. line blank" in dicello_summary
    assert "negligence, private nuisance, and public nuisance" in dicello_summary
    assert "no public state-court case number was independently verified" in dicello_summary
    assert "not claiming affiliation" in dicello_summary

    assert len(data["resources"]) >= 10
    for resource in data["resources"]:
        assert {"category", "title", "description", "url", "cta"}.issubset(resource)

    static_resource_and_source_text = " ".join(
        node.get_text(" ", strip=True).lower()
        for node in [doc.select_one("#resourceGrid"), doc.select_one("#sources")]
        if node is not None
    )
    assert "reduced four-street evacuation zone" not in static_resource_and_source_text
    assert "evacuation-order lift" in static_resource_and_source_text
    assert "street-status updates" in static_resource_and_source_text
    assert "road-closure guidance" in static_resource_and_source_text

    assert "setInterval(loadUpdates,300000)" in html
    assert "data.updates.slice(0,8)" in html
    assert "data.resources.slice(0,11)" in html


def test_garden_grove_resources_include_official_orange_county_incident_page():
    oc_url = "https://www.ocgov.com/page/garden-grove-chemical-spill-incident"

    updates_path = ROOT / "data" / "garden-grove-chemical-leak-updates.json"
    data = json.loads(updates_path.read_text(encoding="utf-8"))
    oc_resources = [r for r in data["resources"] if r.get("url") == oc_url]
    assert len(oc_resources) == 1, "OC County official incident page must appear exactly once in JSON resources"
    oc_resource = oc_resources[0]
    assert oc_resource.get("category"), "OC County resource needs a category"
    assert oc_resource.get("title"), "OC County resource needs a title"
    assert oc_resource.get("description"), "OC County resource needs a description"
    assert oc_resource.get("cta"), "OC County resource needs a CTA label"
    description = oc_resource["description"].lower()
    assert "orange county" in oc_resource["title"].lower() or "orange county" in description
    assert "evacuation" in description or "incident" in description or "map" in description

    landing_path = PUBLIC_PAGES["/landing/garden-grove-chemical-leak/"]
    doc = page_doc(landing_path)
    resource_grid = doc.select_one("#resourceGrid")
    assert resource_grid is not None
    grid_hrefs = {str(a.get("href")) for a in resource_grid.select("a[href]")}
    assert oc_url in grid_hrefs, "static resource grid fallback must surface the OC County official page"

    sources = doc.select_one("#sources")
    assert sources is not None
    source_hrefs = {str(a.get("href")) for a in sources.select("a[href]")}
    assert oc_url in source_hrefs, "sources/citations list must cite the OC County official page"
