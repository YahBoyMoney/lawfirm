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
    assert sitemap_text.count("<lastmod>2026-05-24</lastmod>") == 22
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


def test_public_html_has_working_phone_links_and_valid_markup_basics():
    expected_phone_href = "tel:+19096096685"
    expected_fax_href = "tel:+19098906043"
    for path in ROOT.rglob("*.html"):
        html = path.read_text(encoding="utf-8")
        assert "tel:+190****" not in html, f"{path} contains a redacted/non-dialable tel: link"
        assert "<p><p>" not in html and "</p></p>" not in html, f"{path} contains nested paragraph markup"
        assert 'id=""' not in html, f"{path} contains an empty id attribute"
        doc = BeautifulSoup(html, "html.parser")
        for tel in doc.select('a[href^="tel:"]'):
            href = str(tel.get("href"))
            assert href in {expected_phone_href, expected_fax_href}, f"{path} has unexpected tel link: {href}"


def test_stage1_forms_are_live_netlify_intake_without_uploads():
    form_pages = [
        PUBLIC_PAGES["/free-case-review/"],
        PUBLIC_PAGES["/landing/truck-fleet-rideshare-accident-california/"],
        PUBLIC_PAGES["/landing/garden-grove-chemical-leak/"],
    ]
    for path in form_pages:
        doc = page_doc(path)
        form = doc.select_one('form[name="case-review"]')
        assert form is not None, f"{path} needs live case-review form"
        assert str(form.get("method", "")).upper() == "POST"
        assert form.get("action") == "/success.html"
        assert form.get("data-netlify") == "true"
        assert doc.select_one('input[name="form-name"][value="case-review"]') is not None
        assert not doc.select_one('input[type="file"]')
        text = form.get_text(" ", strip=True).lower()
        assert "do not include privileged" in text
        assert "attorney-client relationship" in text


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
            'meta[name="twitter:card"]': "summary_large_image",
            'meta[name="twitter:title"]': title.get_text(strip=True),
            'meta[name="twitter:description"]': description.get("content"),
            'meta[name="twitter:image"]': SOCIAL_IMAGE,
        }
        for selector, expected_content in expected.items():
            tags = doc.select(selector)
            assert len(tags) == 1, f"{route} needs exactly one {selector} tag"
            assert tags[0].get("content") == expected_content, f"{route} has wrong {selector} content"


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
