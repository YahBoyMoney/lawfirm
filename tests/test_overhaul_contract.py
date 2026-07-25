import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def load_build_module():
    spec = importlib.util.spec_from_file_location("berhelaw_build", ROOT / "scripts/build.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXPECTED_ROUTES = {
    "/",
    "/attorney-tam-berhe/",
    "/case-review-process/",
    "/disclaimer.html",
    "/free-case-review/",
    "/landing/garden-grove-chemical-leak/",
    "/landing/truck-fleet-rideshare-accident-california/",
    "/living-trust/",
    "/practice-areas/",
    "/practice-areas/catastrophic-injury/",
    "/practice-areas/civil-rights-government-accountability/",
    "/practice-areas/consumer-protection-lemon-law/",
    "/practice-areas/employment-workplace-claims/",
    "/practice-areas/insurance-bad-faith/",
    "/practice-areas/personal-injury-wrongful-death/",
    "/practice-areas/select-civil-litigation/",
    "/privacy.html",
    "/referrals-co-counsel/",
    "/resources/",
    "/resources/after-a-collision-first-steps/",
    "/resources/commercial-vehicle-evidence-checklist/",
    "/resources/deadlines-and-early-review/",
    "/resources/insurance-claim-communication/",
    "/resources/prepare-for-case-review/",
    "/resources/workplace-documentation/",
    "/terms.html",
}


def html_files():
    return sorted(path for path in ROOT.rglob("*.html") if ".git" not in path.parts)


def soup(path):
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


def route_for(path):
    relative = path.relative_to(ROOT).as_posix()
    if relative == "index.html":
        return "/"
    if relative.endswith("/index.html"):
        return f'/{relative.removesuffix("index.html")}'
    return f"/{relative}"


def test_canonical_route_parity_and_success_exclusion():
    docs = {route_for(path): soup(path) for path in html_files()}
    public = set(docs) - {"/success.html"}
    assert public == EXPECTED_ROUTES
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    listed = {
        urlparse(url).path
        for url in re.findall(r"<loc>([^<]+)</loc>", sitemap)
    }
    assert listed == EXPECTED_ROUTES
    assert "/success.html" not in listed


def test_output_is_component_generated_and_has_no_inline_code():
    for path in html_files():
        doc = soup(path)
        assert doc.select_one('meta[name="generator"][content="BerheLaw static builder"]')
        assert not doc.find("style"), f"inline style in {path}"
        assert not [tag for tag in doc.find_all("script") if not tag.get("src") and tag.get("type") != "application/ld+json"]
        assert doc.select_one('link[rel="stylesheet"][href^="/assets/css/site."]')
        assert doc.select_one('script[src^="/assets/js/site."][defer]')


def test_intake_contract_is_normalized_and_never_uses_opaque_success():
    visible_forms = []
    for path in html_files():
        doc = soup(path)
        visible_forms.extend(doc.select("form[data-intake-form]"))
        assert "no-cors" not in path.read_text(encoding="utf-8")
    assert visible_forms
    required = {"form_version", "consent_version", "matterType", "firstName", "lastName", "phone", "email", "bot-field", "summary", "consent", "page_url", "referrer", "campaign"}
    for form in visible_forms:
        assert form.get("action") == "https://admin.berhelaw.com/api/leads/case-review"
        assert form.get("method", "").lower() == "post"
        assert not form.has_attr("data-netlify")
        names = {field.get("name") for field in form.select("input, select, textarea")}
        assert required <= names
        assert form.select_one('[name="page_url"]')["value"].startswith("https://berhelaw.com/")
        assert not any(name and name.startswith("entry.") for name in names)
        assert form.select_one('[name="matterType"]')
        assert form.select_one('[name="bot-field"][aria-hidden="true"]')
    intake_js = next((ROOT / "assets/js").glob("intake.*.js")).read_text(encoding="utf-8")
    assert "fetch(" not in intake_js
    assert "window.location.assign" not in intake_js
    assert "pageUrl.value = window.location.href" in intake_js
    assert "referrer.value = document.referrer" in intake_js


def test_representative_forms_use_keys_accepted_by_the_production_route():
    representatives = {
        ROOT / "free-case-review/index.html": {"caseType", "preferred_contact", "knownDeadline", "county"},
        ROOT / "landing/truck-fleet-rideshare-accident-california/index.html": {"preferred_contact", "county"},
        ROOT / "landing/garden-grove-chemical-leak/index.html": {"preferred_contact"},
    }
    for path, specialized in representatives.items():
        form = soup(path).select_one("form[data-intake-form]")
        names = {field.get("name") for field in form.select("input, select, textarea")}
        assert {"firstName", "lastName", "matterType", "bot-field", "summary", "consent", "page_url", "referrer", "campaign"} <= names
        assert specialized <= names


def test_shared_accessibility_and_legal_markers():
    for path in html_files():
        doc = soup(path)
        assert doc.html.get("lang") == "en"
        assert len(doc.select("h1")) == 1
        assert doc.select_one('a.skip-link[href="#main"]')
        assert doc.select_one("main#main")
        assert doc.select_one('button.nav-toggle[type="button"][aria-expanded="false"]')
        assert doc.select_one('nav#site-navigation[aria-label="Primary navigation"]')
        assert doc.select_one("footer.site-footer")
        assert doc.select_one('meta[name="theme-color"][content="#8c2f25"]')
        text = doc.get_text(" ", strip=True).lower()
        if path.name == "success.html":
            continue
        assert "berhe jones is a dba of the berhe law firm" in text
        assert "signed written agreement" in text
        assert "attorney-client relationship" in text


def test_no_unsupported_marketing_claims_or_internal_labels():
    prohibited = (
        "guaranteed outcome", "millions recovered", "certified specialist",
        "best lawyer", "top attorney", "file · 2026", "fable 5",
        "additional facts not claimed here", "verified profile detail",
    )
    for path in html_files():
        text = soup(path).get_text(" ", strip=True).lower()
        for phrase in prohibited:
            assert phrase not in text, f"{phrase!r} in {path}"


def test_internal_links_and_assets_resolve():
    for path in html_files():
        doc = soup(path)
        for tag, attribute in (("a", "href"), ("img", "src"), ("script", "src"), ("link", "href")):
            for element in doc.find_all(tag):
                value = element.get(attribute)
                if not value or not value.startswith("/") or value.startswith("//"):
                    continue
                local = value.split("#", 1)[0].split("?", 1)[0]
                if not local:
                    continue
                target = ROOT / local.lstrip("/")
                if local.endswith("/"):
                    target /= "index.html"
                assert target.exists(), f"broken {value} in {path}"
        for image in doc.find_all("img"):
            assert image.get("width") and image.get("height")
            assert image.get("decoding") == "async"
            assert image.has_attr("alt")

    for asset in (ROOT / "images").iterdir():
        if not asset.is_file():
            continue
        with Image.open(asset) as image:
            image.verify()
    for path in html_files():
        for image in soup(path).select('img[src^="/images/"]'):
            with Image.open(ROOT / image["src"].lstrip("/")) as source:
                assert int(image["width"]) == source.width
                assert int(image["height"]) == source.height


def test_phone_links_use_the_verified_number():
    for path in html_files():
        phone_links = soup(path).select('a[href^="tel:"]')
        assert phone_links, f"missing phone link in {path}"
        assert all(link.get("href") == "tel:+19096096685" for link in phone_links)


def test_metadata_and_schema_are_complete_and_consistent():
    titles = set()
    descriptions = set()
    for path in html_files():
        doc = soup(path)
        route = route_for(path)
        title = doc.title.get_text(strip=True)
        description = doc.select_one('meta[name="description"]')["content"]
        assert title not in titles
        assert description not in descriptions
        titles.add(title)
        descriptions.add(description)
        canonical = doc.select_one('link[rel="canonical"]')
        assert canonical and canonical["href"] == f"https://berhelaw.com{route}"
        for selector in (
            'meta[property="og:title"]', 'meta[property="og:description"]',
            'meta[property="og:url"]', 'meta[property="og:image"]',
            'meta[name="twitter:card"]', 'meta[name="twitter:title"]',
            'meta[name="twitter:description"]', 'meta[name="twitter:image"]',
        ):
            assert doc.select_one(selector), f"missing {selector} in {path}"
        data = json.loads(doc.select_one('script[type="application/ld+json"]').string)
        graph = data.get("@graph", [])
        assert any(node.get("@id") == "https://berhelaw.com/#firm" for node in graph)
        visible = doc.select(".breadcrumbs li")
        breadcrumb_nodes = [node for node in graph if node.get("@type") == "BreadcrumbList"]
        assert bool(breadcrumb_nodes) == bool(visible)
        if visible:
            expected = []
            for position, item in enumerate(visible, 1):
                link = item.find("a")
                href = link["href"] if link else route
                expected.append({"@type": "ListItem", "position": position, "name": item.get_text(" ", strip=True), "item": f"https://berhelaw.com{href}"})
            assert breadcrumb_nodes[0]["itemListElement"] == expected


def test_forms_have_mobile_and_accessibility_contract():
    for path in html_files():
        doc = soup(path)
        for field in doc.select("input"):
            assert field.get("type"), f"input type missing in {path}"
        for form in doc.select("form[data-intake-form]"):
            assert form.get("accept-charset") in ("UTF-8", ["UTF-8"])
            for required in form.select("[required]"):
                assert required.get("aria-required") == "true"
            for phone in form.select('input[type="tel"]'):
                assert phone.get("autocomplete") == "tel"
                assert phone.get("inputmode") == "tel"
                assert phone.get("minlength") == "7"
                assert phone.get("pattern")
                error_id = phone.get("aria-describedby")
                assert error_id and form.select_one(f"#{error_id}[data-phone-error][aria-live]")
            for email in form.select('input[type="email"]'):
                assert email.get("autocomplete") == "email"
                assert email.get("inputmode") == "email"
            for summary in form.select('textarea[name="summary"]'):
                assert summary.get("autocapitalize") == "sentences"
                assert summary.get("aria-describedby")


def test_visual_qa_markers_and_mobile_sticky_contract():
    home = soup(ROOT / "index.html")
    practice_hub = soup(ROOT / "practice-areas" / "index.html")
    assert home.select_one("section.opening[data-hero][data-opening]")
    assert practice_hub.select_one("section.hero.hero--practice-hub.hero--case-art")

    headline = home.select_one(".opening-headline").get_text(" ", strip=True)
    assert headline == "Something serious happened. What you do next can shape what you can prove."
    primary_call = home.select_one('.opening-dock a.call-bar[href^="tel:"]')
    assert primary_call and "909-609-6685" in primary_call.get_text(" ", strip=True)
    assert home.select_one('.opening-dock a.dock-link[href="/free-case-review/"]')
    assert "298992" not in home.select_one(".opening").get_text(" ", strip=True)
    assert len(home.select(".faq-item")) >= 5

    metadata = json.loads(home.select_one('script[type="application/ld+json"]').string)
    faq_nodes = [node for node in metadata.get("@graph", []) if node.get("@type") == "FAQPage"]
    assert len(faq_nodes) == 1 and len(faq_nodes[0]["mainEntity"]) >= 5
    firm = next(node for node in metadata["@graph"] if node.get("@id") == "https://berhelaw.com/#firm")
    assert firm["areaServed"]["name"] == "California"
    assert "Personal injury law" in firm["serviceType"]
    assert home.title.get_text(strip=True) == "California Personal Injury & Civil Rights Lawyer | Berhe Jones LLP"
    assert "free California case review" in home.select_one('meta[name="description"]')["content"]

    css = next((ROOT / "assets" / "css").glob("site.*.css")).read_text(encoding="utf-8")
    assert "--mobile-action-height:3.5rem" in css
    assert ".hero--practice-hub h1" in css
    assert ".hero-media picture{position:absolute;inset:0;display:block}" in css
    assert ".mobile-actions[data-suppressed=true]" in css
    assert "body{padding-bottom:var(--mobile-action-height)}" in css

    site_js = next((ROOT / "assets" / "js").glob("site.*.js")).read_text(encoding="utf-8")
    assert "hero-actions-visible" in site_js
    assert "form-control-focused" in site_js
    assert "aria-hidden" in site_js


def relative_luminance(color):
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    channels = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(first, second):
    lighter, darker = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def record_tokens():
    css = (ROOT / "src/assets/site.css").read_text(encoding="utf-8")
    tokens = dict(re.findall(r"--([a-z-]+):(#[0-9a-fA-F]{6})", css))
    return css, tokens


def test_record_palette_tokens_meet_wcag_contrast():
    """The Record palette replaces gold. Every text pairing that ships must still clear WCAG AA."""
    css, tokens = record_tokens()
    required = {"paper", "ink", "oxblood", "oxblood-on-ink", "archive", "muted", "cream", "muted-on-ink"}
    assert required <= set(tokens), sorted(required - set(tokens))
    paper, ink, oxblood = tokens["paper"], tokens["ink"], tokens["oxblood"]
    archive, cream = tokens["archive"], tokens["cream"]

    assert contrast(ink, paper) >= 7            # body and headline ink on paper
    assert contrast(tokens["muted"], paper) >= 4.5   # supporting copy on paper
    assert contrast(oxblood, paper) >= 4.5      # folios, indexes and links on paper
    assert contrast(cream, oxblood) >= 4.5      # call bar and note on the oxblood conversion band
    assert contrast(ink, cream) >= 7            # call bar label on the cream bar
    assert contrast(ink, archive) >= 4.5        # preservation bands
    assert contrast(cream, ink) >= 7            # ink chapters
    assert contrast(tokens["muted-on-ink"], ink) >= 4.5
    assert contrast(tokens["oxblood-on-ink"], ink) >= 4.5   # highlighted operative words

    focus = re.search(r":focus-visible\{outline:3px solid var\(--([a-z-]+)\)", css)
    assert focus and focus.group(1) == "oxblood"
    assert contrast(oxblood, paper) >= 3
    assert ".deep :focus-visible,.band--ink :focus-visible,.intake-field :focus-visible{outline-color:var(--cream)}" in css
    assert ".opening-dock-band{order:2}" in css   # the conversion band rises directly under the mobile headline


def test_gold_is_gone_from_the_action_system():
    """The rejected release used brass and gold as its dominant action colour. It must not survive."""
    css, tokens = record_tokens()
    for retired in ("--brass", "--brass-on-dark", "--deep:", "--clean:", "--stone:"):
        assert retired not in css, f"{retired} is a rejected token"
    for gold in ("#d4b66d", "#e1c883", "#74520b", "#a67f16", "#f2e2b4", "#735500"):
        assert gold not in css.lower(), f"{gold} is a rejected gold value"
    # nothing in the shipped homepage renders a gold call button
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "button-call" not in home
    assert "button-secondary-light" not in home


def test_garden_grove_preserves_feed_resources_and_source_citations():
    path = ROOT / "landing/garden-grove-chemical-leak/index.html"
    doc = soup(path)
    data = json.loads((ROOT / "data/garden-grove-chemical-leak-updates.json").read_text())
    assert doc.select_one("#updates-feed")
    assert doc.select_one('button#refresh-updates[type="button"][aria-controls="updates-feed"]')
    assert len(doc.select("#resource-grid > article")) == len(data["resources"])
    source_hrefs = {link.get("href") for link in doc.select(".source-list a[href]")}
    assert len(source_hrefs) == 19
    assert "https://ggcity.org/emergency" in source_hrefs
    assert "https://www.ocgov.com/page/garden-grove-chemical-spill-incident" in source_hrefs
    site_js = (ROOT / "src/assets/site.js").read_text(encoding="utf-8")
    assert "14 * 24 * 60 * 60 * 1000" in site_js
    assert "Update feed is stale" in site_js


def test_csp_and_cache_headers_are_strict():
    headers = (ROOT / "_headers").read_text(encoding="utf-8")
    assert "'unsafe-inline'" not in headers
    assert "script-src 'self'" in headers
    assert "style-src 'self'" in headers
    assert "font-src 'self'" in headers
    assert "fonts.googleapis.com" not in headers and "fonts.gstatic.com" not in headers
    assert "form-action https://admin.berhelaw.com" in headers
    assert "/assets/*" in headers and "immutable" in headers
    assert "/success.html" in headers
    assert "X-Robots-Tag: noindex, nofollow" in headers
    assert "Cache-Control: no-store" in headers


def test_generated_output_is_current():
    result = subprocess.run(
        [sys.executable, "scripts/build.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_garden_feed_dates_are_utc_and_snapshot_deterministic():
    build = load_build_module()

    data = json.loads((ROOT / "data/garden-grove-chemical-leak-updates.json").read_text(encoding="utf-8"))
    feed, verified, snapshot, error = build._garden_feed(build.GARDEN_FEED_PATH)
    assert error is None
    assert verified is not None and snapshot is not None
    assert feed == data
    assert build._utc_date_label(verified) == "May 31, 2026"
    assert snapshot.isoformat() == "2026-07-11T12:00:00+00:00"
    assert "datetime.now" not in build.garden.__code__.co_names


def test_garden_build_fails_safe_for_malformed_and_unavailable_feed(tmp_path, monkeypatch):
    build = load_build_module()

    malformed = tmp_path / "malformed.json"
    malformed.write_text(json.dumps({
        "lastVerifiedUtc": "2026-05-31T00:28:03Z",
        "snapshotAsOfUtc": "2026-07-11T12:00:00Z",
        "updates": [{"timeUtc": "not-a-date"}],
        "resources": [],
    }), encoding="utf-8")
    monkeypatch.setattr(build, "GARDEN_FEED_PATH", malformed)
    malformed_page = build.garden()
    assert 'data-feed-state="malformed"' in malformed_page
    assert "cannot be verified" in malformed_page
    assert "official City and County sources" in malformed_page

    monkeypatch.setattr(build, "GARDEN_FEED_PATH", tmp_path / "missing.json")
    unavailable_page = build.garden()
    assert 'data-feed-state="unavailable"' in unavailable_page
    assert "local update feed is unavailable" in unavailable_page
    assert "official City and County sources" in unavailable_page
