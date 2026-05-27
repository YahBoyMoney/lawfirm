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


def test_stage1_pages_are_in_sitemap_and_homepage_footer():
    sitemap_text = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    home_doc = page_doc(ROOT / "index.html")
    footer_hrefs = {str(a.get("href")) for a in home_doc.select("footer.site a[href]")}
    assert sitemap_text.count("<lastmod>2026-05-25</lastmod>") == 21
    assert sitemap_text.count("<lastmod>2026-05-27</lastmod>") == 1
    assert (
        "<loc>https://berhelaw.com/landing/garden-grove-chemical-leak/</loc>\n"
        "    <lastmod>2026-05-27</lastmod>"
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
    sticky_call = doc.select_one('.mobile-sticky-cta a[href="tel:+19096096685"]')
    assert sticky_call is not None
    assert sticky_call.get_text(" ", strip=True) == "Call now"
    assert sticky_call.get("aria-label") == "Call Berhe Jones LLP at 909-609-6685"


def test_public_html_has_working_phone_links_and_valid_markup_basics():
    expected_phone_href = "tel:+19096096685"
    expected_fax_href = "tel:+19098906043"
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
            assert href in {expected_phone_href, expected_fax_href}, f"{path} has unexpected tel link: {href}"


def test_public_phone_form_fields_trigger_mobile_phone_keyboards():
    for path in ROOT.rglob("*.html"):
        doc = page_doc(path)
        for phone in doc.select('input[type="tel"]'):
            assert phone.get("autocomplete") == "tel", f"{path} phone field should preserve tel autocomplete"
            assert phone.get("inputmode") == "tel", f"{path} phone field should request the mobile phone keyboard"


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
    latest_update = data["updates"][0]
    assert (
        latest_update.get("sourceUrl")
        == "https://www.ggusd.us/news/evacuation-orders-lifted-all-schools-reopen-tomorrowevacuation-orders-lifted-all-schools-reopen-tomorrow"
    )
    assert latest_update.get("category") == "Schools / operations"
    latest_summary = latest_update.get("summary", "").lower()
    assert "all schools would be open wednesday" in latest_summary
    assert "students unable to attend" in latest_summary
    assert "not be penalized" in latest_summary
    assert "held harmless" in latest_summary

    oc_register_updates = [
        u
        for u in data["updates"]
        if u.get("sourceUrl")
        == "https://www.ocregister.com/2026/05/26/chemical-tank-in-garden-grove-at-92-degrees-tuesday-a-m-crews-work-to-lower-it/"
    ]
    assert len(oc_register_updates) == 1, "OC Register / OCFA cooling-system update should stay visible in capped feed"
    assert oc_register_updates[0].get("category") == "Investigation / tank operations"
    oc_register_summary = oc_register_updates[0].get("summary", "").lower()
    assert "cooling system" in oc_register_summary
    assert "facility team to call 911" in oc_register_summary
    assert "do not yet know why the cooling system stopped working" in oc_register_summary
    assert "not a final finding of legal fault" in oc_register_summary

    official_lift_updates = [u for u in data["updates"] if u.get("sourceUrl") == "https://ggcity.org/emergency"]
    assert len(official_lift_updates) == 1, "City evacuation-lift update should stay visible in capped feed"
    official_summary = official_lift_updates[0].get("summary", "").lower()
    assert official_lift_updates[0].get("category") == "Official safety status"
    assert "all evacuation orders" in official_summary
    assert "no chemical leak" in official_summary
    assert "no threat of explosion or fire" in official_summary
    assert "western avenue between chapman avenue and garden grove boulevard remains closed" in official_summary
    assert "exclusion zone" in official_summary
    legal_status_updates = [u for u in data["updates"] if u.get("sourceUrl") == "https://www.gkngardengrove.com/"]
    assert len(legal_status_updates) == 1, "public legal-action feed should cite the GKN Garden Grove class-action status source once"
    assert legal_status_updates[0].get("category") == "Legal-action status"
    assert "not claiming affiliation" in legal_status_updates[0].get("summary", "").lower()

    daily_journal_updates = [
        u
        for u in data["updates"]
        if u.get("sourceUrl")
        == "https://www.dailyjournal.com/article/391685-garden-grove-chemical-emergency-spurs-new-plaintiffs-legal-coalition"
    ]
    assert len(daily_journal_updates) == 1, "Daily Journal plaintiffs-coalition update should stay visible in capped feed"
    assert daily_journal_updates[0].get("category") == "Legal-action status"
    assert "not claiming affiliation" in daily_journal_updates[0].get("summary", "").lower()
    assert "court case number" in daily_journal_updates[0].get("summary", "").lower()

    kfi_updates = [
        u
        for u in data["updates"]
        if u.get("sourceUrl")
        == "https://kfiam640.iheart.com/content/2026-05-26-lawsuit-filed-against-gkn-aerospace-over-chemical-leak/"
    ]
    assert len(kfi_updates) == 1, "KFI federal-lawsuit update should stay visible in capped feed"
    assert kfi_updates[0].get("category") == "Legal-action status"
    assert "source-attributed" in kfi_updates[0].get("summary", "").lower()
    assert "not claiming affiliation" in kfi_updates[0].get("summary", "").lower()
    assert "court case number" in kfi_updates[0].get("summary", "").lower()

    abc7_epa_updates = [
        u
        for u in data["updates"]
        if u.get("sourceUrl")
        == "https://abc7.com/post/check-enforcement-compliance-history-chemical-facilities-area-epas-interactive-map/19176249/"
    ]
    assert len(abc7_epa_updates) == 1, "ABC7 EPA compliance-map update should stay visible in capped feed"
    assert abc7_epa_updates[0].get("category") == "Regulatory history"
    abc7_epa_summary = abc7_epa_updates[0].get("summary", "").lower()
    assert "131,000 pounds" in abc7_epa_summary
    assert "generator-related violations" in abc7_epa_summary
    assert "does not, by itself, establish the cause" in abc7_epa_summary

    ocde_updates = [
        u
        for u in data["updates"]
        if u.get("sourceUrl")
        == "https://newsroom.ocde.us/several-garden-grove-unified-campuses-closed-following-chemical-leak-response/"
    ]
    assert len(ocde_updates) == 1, "OCDE school/recovery update should stay visible in capped feed"
    assert ocde_updates[0].get("category") == "Schools / recovery resources"
    ocde_summary = ocde_updates[0].get("summary", "").lower()
    assert "supplybank.org disaster relief fund" in ocde_summary
    assert "j-13a waivers" in ocde_summary
    assert "district-by-district" in ocde_summary
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
