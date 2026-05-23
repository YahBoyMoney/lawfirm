from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]

PUBLIC_PAGES = {
    "/attorney-tam-berhe/": ROOT / "attorney-tam-berhe" / "index.html",
    "/case-review-process/": ROOT / "case-review-process" / "index.html",
    "/free-case-review/": ROOT / "free-case-review" / "index.html",
    "/referrals-co-counsel/": ROOT / "referrals-co-counsel" / "index.html",
    "/landing/truck-fleet-rideshare-accident-california/": ROOT / "landing" / "truck-fleet-rideshare-accident-california" / "index.html",
}

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
    for route in PUBLIC_PAGES:
        assert f"https://berhelaw.com{route}" in sitemap_text
        assert route in footer_hrefs


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


def test_stage1_forms_are_live_netlify_intake_without_uploads():
    form_pages = [
        PUBLIC_PAGES["/free-case-review/"],
        PUBLIC_PAGES["/landing/truck-fleet-rideshare-accident-california/"],
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
