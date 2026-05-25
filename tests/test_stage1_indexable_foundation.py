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
    assert sitemap_text.count("<lastmod>2026-05-25</lastmod>") == 22
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
        text = form.get_text(" ", strip=True).lower()
        assert "do not include privileged" in text
        assert "attorney-client relationship" in text


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
    assert len(data["resources"]) >= 10
    for resource in data["resources"]:
        assert {"category", "title", "description", "url", "cta"}.issubset(resource)

    assert "setInterval(loadUpdates,300000)" in html
    assert "data.updates.slice(0,8)" in html
