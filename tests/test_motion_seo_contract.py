"""Contract tests for the Opus 5 motion system, conversion surfaces, and resource SEO.

The motion rules exist to guarantee one thing: the page is complete before JavaScript
runs, and stays complete if JavaScript fails or the visitor asks for reduced motion.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from site_data import PRACTICES, RESOURCE_GUIDES, ROUTES  # noqa: E402

CSS_SOURCE = (ROOT / "src/assets/site.css").read_text(encoding="utf-8")
JS_SOURCE = (ROOT / "src/assets/site.js").read_text(encoding="utf-8")

NEW_RESOURCE_ROUTES = {
    "/resources/after-a-collision-first-steps/",
    "/resources/insurance-claim-communication/",
    "/resources/workplace-documentation/",
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


def documents():
    return {route_for(path): soup(path) for path in html_files()}


def css_rules(css):
    """Yield (selector, declarations) for every rule, including rules inside at-blocks."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    for match in re.finditer(r"([^{}]+)\{([^{}]+)\}", css):
        selector = " ".join(match.group(1).split())
        if selector.startswith("@"):
            continue
        yield selector, match.group(2).replace(" ", "")


def hides_content(declarations):
    return bool(
        re.search(r"opacity:0(?![.\d])", declarations)
        or "visibility:hidden" in declarations
        or re.search(r"display:none", declarations)
        or re.search(r"transform:translate3?d?\([^)]*[1-9]", declarations)
    )


# --- motion fails open ------------------------------------------------------

def test_no_css_rule_hides_content_unless_scoped_to_the_motion_class():
    offenders = []
    for selector, declarations in css_rules(CSS_SOURCE):
        if selector in {"from", "to"} or re.fullmatch(r"[\d.]+%", selector):
            continue
        targets_motion_content = any(
            hook in selector for hook in ("[data-reveal]", "[data-hero]", "case-step", "case-track-fill")
        )
        if targets_motion_content and hides_content(declarations) and ".motion" not in selector:
            if "!important" in declarations:  # reduced-motion and print overrides restore state
                continue
            offenders.append(selector)
    assert not offenders, f"content hidden outside html.motion: {offenders}"


def declarations_for(selector):
    return [block for rule, block in css_rules(CSS_SOURCE) if rule == selector]


def test_reveal_and_timeline_defaults_render_the_finished_state():
    # Unscoped defaults must be the finished state, so no-JS visitors see everything.
    assert any("scaleY(var(--timeline-progress,1))" in block for block in declarations_for(".case-track-fill"))
    assert any("scaleY(var(--timeline-progress,0))" in block for block in declarations_for(".motion .case-track-fill"))
    assert any("opacity:0" in block for block in declarations_for(".motion [data-reveal]"))
    assert not any(hides_content(block) for block in declarations_for(".case-step-dot:after"))
    assert not any(
        selector == "[data-reveal]" and hides_content(declarations)
        for selector, declarations in css_rules(CSS_SOURCE)
    )


def test_scroll_progress_is_decorative_and_inert_without_javascript():
    assert declarations_for(".scroll-progress")[0] == "display:none"
    assert any("display:block" in block for block in declarations_for(".motion .scroll-progress"))
    assert any("scaleX(var(--scroll-progress,0))" in block for block in declarations_for(".motion .scroll-progress-bar"))
    for route, doc in documents().items():
        bar = doc.select_one(".scroll-progress")
        assert bar, f"missing scroll progress element on {route}"
        assert bar.get("aria-hidden") == "true", route
        assert not bar.has_attr("role") and not bar.has_attr("tabindex"), route
        assert not bar.has_attr("aria-valuenow"), route
        assert bar.select_one("span.scroll-progress-bar"), route
        assert not bar.get_text(strip=True), route


def test_motion_javascript_guards_capability_preference_and_failure():
    assert "'IntersectionObserver' in window" in JS_SOURCE
    assert "typeof window.requestAnimationFrame === 'function'" in JS_SOURCE
    assert "matchMedia('(prefers-reduced-motion: reduce)')" in JS_SOURCE
    assert "reduceMotion.matches" in JS_SOURCE
    assert "addEventListener('change', applyPreference)" in JS_SOURCE
    assert "catch (error)" in JS_SOURCE and "failOpen();" in JS_SOURCE
    assert "root.classList.remove('motion')" in JS_SOURCE
    assert "OBSERVER_FALLBACK_MS" in JS_SOURCE
    # the class that hides content is added in exactly one place
    assert JS_SOURCE.count("classList.add('motion')") == 1


def test_motion_never_hijacks_scrolling_and_stays_compositor_safe():
    for blocked in ("wheel", "touchmove", "scrollTo(", "scrollIntoView(", "preventDefault"):
        assert blocked not in JS_SOURCE, f"{blocked} would fight the native scroller"
    assert JS_SOURCE.count("{passive: true}") >= 3
    assert "requestAnimationFrame(update)" in JS_SOURCE
    animated = {
        declarations
        for selector, declarations in css_rules(CSS_SOURCE)
        if selector.startswith(".motion") and "transition:" in declarations
    }
    for declarations in animated:
        for transition in re.findall(r"transition:([^;]+)", declarations):
            flattened = re.sub(r"\([^)]*\)", "", transition)
            for part in flattened.split(","):
                prop = re.match(r"[a-z-]+", part.strip())
                assert prop, part
                assert prop.group(0) in {"opacity", "transform", "border-color", "color", "background-color", "box-shadow"}, part


def test_reduced_motion_fallback_covers_every_motion_surface():
    reduced = re.findall(r"@media\(prefers-reduced-motion:reduce\)\{(.+?)\n", CSS_SOURCE + "\n")
    block = " ".join(reduced)
    assert "animation-duration:.01ms!important" in block
    assert "transition-duration:.01ms!important" in block
    assert "[data-reveal]{opacity:1!important" in block
    assert "scroll-progress{display:none!important}" in block
    assert "scaleY(1)!important" in block
    assert "[data-hero] *{animation:none!important}" in block


# --- conversion surfaces ----------------------------------------------------

def test_home_hero_leads_with_call_and_case_review_before_anything_else():
    home = soup(ROOT / "index.html")
    hero = home.select_one("section.home-hero[data-hero]")
    assert hero
    actions = hero.select_one(".home-hero-actions")
    call, review = actions.select("a")[:2]
    assert call["href"] == "tel:+19096096685"
    assert "Call now" in call.get_text(" ", strip=True)
    assert review["href"] == "/free-case-review/"
    # both actions precede every other section in document order
    body_html = str(home)
    assert body_html.index('class="home-hero-actions"') < body_html.index('class="proof-band"')


def test_all_pages_use_case_artwork_and_no_synthetic_team_photography():
    for path in html_files():
        markup = path.read_text(encoding="utf-8")
        for synthetic in ("berhe-jones-hero-team", "case-fit-team"):
            assert synthetic not in markup, f"{synthetic} is synthetic personnel imagery in {path}"
    home = soup(ROOT / "index.html")
    art = home.select_one(".home-hero-art picture")
    assert art is not None
    sources = art.select('source[type="image/webp"]')
    assert len(sources) == 2
    assert sources[0]["srcset"] == "/images/case-intelligence-hero-mobile.webp"
    assert sources[0]["media"] == "(max-width:600px)"
    assert sources[1]["srcset"] == "/images/case-intelligence-hero.webp"
    image = art.select_one("img")
    assert image["src"] == "/images/case-intelligence-hero.jpg"
    assert image["fetchpriority"] == "high" and image["decoding"] == "async"
    assert home.select_one(".home-hero-art")["aria-hidden"] == "true"
    portraits = {img["src"] for img in home.select("img")} - {"/images/case-intelligence-hero.jpg"}
    assert portraits <= {"/images/tam-berhe.jpg", "/images/the-berhe-law-firm-apc-logo-white.png"}


def test_case_evaluation_timeline_is_present_and_complete_without_javascript():
    home = soup(ROOT / "index.html")
    timelines = home.select("[data-timeline]")
    assert len(timelines) == 1
    timeline = timelines[0]
    steps = timeline.select("[data-timeline-step]")
    assert len(steps) == 5
    assert timeline.select_one(".case-track-fill")
    for position, step in enumerate(steps, 1):
        assert step["data-step"] == str(position)
        assert step.select_one("h3").get_text(strip=True)
        assert step.select_one(".case-step-bring").get_text(strip=True)
        # no step carries a JS-only active flag in the static output
        assert not step.has_attr("data-active")


def test_every_page_offers_a_call_and_a_case_review_path():
    for route, doc in documents().items():
        assert doc.select_one('footer a[href^="tel:"]'), route
        if route.endswith(".html"):  # legal and status pages keep the footer call path only
            continue
        main = doc.select_one("main#main")
        assert main.select_one('a[href^="tel:"]'), route
        assert main.select_one('a[href^="/free-case-review/"], form[data-intake-form]'), route


def test_responsible_firm_address_is_global_in_footer_and_legalservice_schema():
    expected = {
        "@type": "PostalAddress",
        "streetAddress": "901 Via Piemonte, Suite 230",
        "addressLocality": "Ontario",
        "addressRegion": "CA",
        "postalCode": "91764-8500",
        "addressCountry": "US",
    }
    for route, doc in documents().items():
        footer = doc.select_one("footer.site-footer")
        assert footer, route
        footer_text = footer.get_text(" ", strip=True)
        assert "The Berhe Law Firm, APC" in footer_text, route
        assert "901 Via Piemonte, Suite 230" in footer_text, route
        assert "Ontario, CA 91764-8500" in footer_text, route
        schema_script = doc.select_one('script[type="application/ld+json"]')
        assert schema_script and schema_script.string, route
        graph = json.loads(schema_script.string)["@graph"]
        legal_services = [node for node in graph if node.get("@type") == "LegalService"]
        assert legal_services, route
        responsible_firm = [node for node in legal_services if node.get("@id") == "https://berhelaw.com/#firm"]
        assert len(responsible_firm) == 1 and responsible_firm[0].get("name") == "The Berhe Law Firm, APC", route
        assert all(node.get("address") == expected for node in legal_services), route


def test_intake_forms_are_preserved_exactly():
    expected = {
        "home-review": set(),
        "general-review": {"caseType", "preferred_contact", "county", "knownDeadline"},
        "truck-review": {"preferred_contact", "county"},
        "garden-review": {"preferred_contact", "affected_city", "impact_type", "already_represented"},
        "trust-guide": {"county", "real_property", "timeline"},
        "attorney-referral": {"jurisdiction", "matter_stage", "conflict_parties", "potential_role"},
    }
    canonical = {
        "form_version", "consent_version", "matterType", "page_url", "referrer", "campaign",
        "bot-field", "firstName", "lastName", "phone", "email", "summary", "consent",
    }
    seen = {}
    for doc in documents().values():
        for form in doc.select("form[data-intake-form]"):
            names = {field.get("name") for field in form.select("input, select, textarea")}
            seen[form["id"]] = names
    assert set(seen) == set(expected)
    for form_id, extras in expected.items():
        assert seen[form_id] == canonical | extras, form_id


# --- resource architecture and SEO -----------------------------------------

def test_new_resource_routes_are_wired_into_routes_sitemap_hub_and_schema():
    assert NEW_RESOURCE_ROUTES <= set(ROUTES)
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    hub = soup(ROOT / "resources/index.html")
    hub_links = {link["href"] for link in hub.select("main a[href]")}
    for route in NEW_RESOURCE_ROUTES:
        assert f"<loc>https://berhelaw.com{route}</loc>" in sitemap
        assert route in hub_links, f"{route} missing from the resource hub"
        doc = soup(ROOT / route.strip("/") / "index.html")
        graph = json.loads(doc.select_one('script[type="application/ld+json"]').string)["@graph"]
        articles = [node for node in graph if node.get("@type") == "Article"]
        assert len(articles) == 1
        article = articles[0]
        for field in ("headline", "author", "image", "datePublished", "dateModified", "mainEntityOfPage"):
            assert article.get(field), f"{route} missing Article.{field}"
        assert doc.select_one('meta[property="og:type"]')["content"] == "article"
        assert doc.select_one('meta[property="article:published_time"]')
        assert doc.select_one('meta[property="article:modified_time"]')
        assert any(node.get("@type") == "BreadcrumbList" for node in graph)
        crumbs = [item.get_text(" ", strip=True) for item in doc.select(".breadcrumbs li")]
        assert crumbs[:2] == ["Home", "Resources"]


def test_faq_schema_matches_visible_questions_on_every_page():
    pages_with_faq = 0
    for route, doc in documents().items():
        visible = doc.select(".faq-item")
        graph = json.loads(doc.select_one('script[type="application/ld+json"]').string)["@graph"]
        faq_nodes = [node for node in graph if node.get("@type") == "FAQPage"]
        assert len(faq_nodes) == (1 if visible else 0), route
        if not visible:
            continue
        pages_with_faq += 1
        questions = [item.select_one("summary").get_text(" ", strip=True) for item in visible]
        answers = [item.select_one("p").get_text(" ", strip=True) for item in visible]
        entities = faq_nodes[0]["mainEntity"]
        assert [entity["name"] for entity in entities] == questions, route
        assert [entity["acceptedAnswer"]["text"] for entity in entities] == answers, route
        assert all(len(answer.split()) >= 15 for answer in answers), route
    assert pages_with_faq >= 15


def test_resource_guides_are_substantive_and_cross_linked():
    for guide in RESOURCE_GUIDES:
        route = f'/resources/{guide["slug"]}/'
        doc = soup(ROOT / route.strip("/") / "index.html")
        main = doc.select_one("main#main")
        words = len(main.get_text(" ", strip=True).split())
        assert words >= 700, f"{route} is thin at {words} words"
        assert len(doc.select(".guide-section")) >= 5
        assert len(doc.select(".checklist-items li")) >= 16
        assert len(doc.select(".faq-item")) >= 3
        assert len(doc.select(".expect-list li")) >= 4
        assert len(doc.select(".related-links a")) >= 3
        assert doc.select_one(".guide-toc")
        toc_targets = {link["href"].lstrip("#") for link in doc.select(".guide-toc a")}
        assert all(doc.select_one(f"#{target}") for target in toc_targets)
        assert "not legal advice" in main.get_text(" ", strip=True).lower()
        assert main.select_one('a[href^="tel:"]')


def test_practice_pages_carry_stakes_faq_and_internal_links():
    for practice in PRACTICES:
        route = f'/practice-areas/{practice["slug"]}/'
        doc = soup(ROOT / route.strip("/") / "index.html")
        main = doc.select_one("main#main")
        assert len(doc.select(".stakes-list li")) >= 3, route
        assert len(doc.select(".faq-item")) == len(practice["faqs"]), route
        assert len(doc.select(".related-links a")) == len(practice["related"]), route
        assert len(main.get_text(" ", strip=True).split()) >= 700, route
        internal = {link["href"] for link in doc.select(".related-links a")}
        assert all(target.startswith("/") for target in internal)
        for _, href in practice["related"]:
            assert href in internal


def test_titles_and_descriptions_are_unique_and_search_intent_sized():
    titles, descriptions = {}, {}
    for route, doc in documents().items():
        title = doc.title.get_text(strip=True)
        description = doc.select_one('meta[name="description"]')["content"]
        assert title not in titles, f"duplicate title on {route} and {titles.get(title)}"
        assert description not in descriptions, f"duplicate description on {route}"
        titles[title] = route
        descriptions[description] = route
        assert 20 <= len(title) <= 75, f"{route} title length {len(title)}"
        assert 70 <= len(description) <= 175, f"{route} description length {len(description)}"


def test_every_resource_guide_is_reachable_from_more_than_the_hub():
    inbound = {route: 0 for route in (f'/resources/{guide["slug"]}/' for guide in RESOURCE_GUIDES)}
    for route, doc in documents().items():
        if route.startswith("/resources/") and route != "/resources/":
            continue
        for link in doc.select("main a[href]"):
            href = link["href"].split("#")[0].split("?")[0]
            if href in inbound:
                inbound[href] += 1
    for route, count in inbound.items():
        assert count >= 2, f"{route} only has {count} inbound link(s)"


# --- content guardrails -----------------------------------------------------

# Cited third-party incident reporting on the Garden Grove page includes public
# settlement figures. Those are sourced facts about other parties, not firm results.
MONEY_EXEMPT_ROUTES = {"/landing/garden-grove-chemical-leak/"}
MONEY_PATTERN = r"\$\s?\d"

PROHIBITED_PATTERNS = (
    r"—",
    r"\bmillions?\s+(recovered|won)\b",
    r"\bno fee unless\b",
    r"\bwe (guarantee|win|promise)\b",
    r"\bguaranteed (outcome|result|recovery|response)\b",
    r"\b(award[- ]winning|top[- ]rated|best (law firm|lawyer|attorney)|#1|super lawyer)\b",
    r"\bcertified specialist\b|\bspecialist in\b|\bboard[- ]certified\b",
    r"\b(we will respond|respond) within \d+\b|\bsame[- ]day response\b|\b24/7\b",
    r"\b(everything you tell us|your information) is confidential\b",
    r"\bprotected by attorney[- ]client privilege\b|\bconfidential consultation\b",
    r"\b(testimonial|client review|five[- ]star|5[- ]star)\b",
    r"\b(verdict|settlement) of\b|\brecovered \$",
    r"\bour offices in\b|\boffices throughout\b",
)


def test_no_unsupported_claims_promises_or_em_dashes():
    for route, doc in documents().items():
        text = doc.get_text(" ", strip=True)
        patterns = PROHIBITED_PATTERNS if route in MONEY_EXEMPT_ROUTES else (*PROHIBITED_PATTERNS, MONEY_PATTERN)
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            assert not match, f"{pattern!r} matched {match.group(0)!r} on {route}"


def test_source_copy_avoids_em_dashes_and_inline_styles():
    for path in (ROOT / "src/site_data.py", ROOT / "scripts/build.py", CSS_SOURCE and ROOT / "src/assets/site.css"):
        assert "—" not in path.read_text(encoding="utf-8"), path
    for route, doc in documents().items():
        assert not doc.select("[style]"), f"inline style attribute on {route} violates the CSP"


def test_disclaimers_and_responsible_firm_identity_survive_the_redesign():
    for route, doc in documents().items():
        if route == "/success.html":
            continue
        text = doc.get_text(" ", strip=True)
        assert "The Berhe Law Firm, APC is responsible for this website." in text, route
        assert "signed written agreement" in text, route
        assert "does not create an attorney-client relationship" in text.lower() or "not create an attorney-client relationship" in text.lower(), route
    guide = soup(ROOT / "resources/after-a-collision-first-steps/index.html")
    assert "does not calculate a deadline" in guide.get_text(" ", strip=True)


def test_every_image_declares_its_real_dimensions_and_has_a_webp_source():
    pairs = {}
    for route, doc in documents().items():
        for image in doc.select("img"):
            source = image["src"].lstrip("/")
            with Image.open(ROOT / source) as opened:
                assert (int(image["width"]), int(image["height"])) == opened.size, f"{source} on {route}"
            assert image.has_attr("alt") and image.get("decoding") == "async"
            pairs[source] = opened.size
    for picture in soup(ROOT / "index.html").select("picture"):
        webp = picture.select_one('source[type="image/webp"]:not([media])')
        fallback = picture.select_one("img")
        assert webp and fallback
        with Image.open(ROOT / webp["srcset"].lstrip("/")) as modern:
            with Image.open(ROOT / fallback["src"].lstrip("/")) as legacy:
                assert modern.size == legacy.size


def test_build_module_stays_deterministic_and_content_hashed():
    spec = importlib.util.spec_from_file_location("berhelaw_build_motion", ROOT / "scripts/build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    first = module.homepage()
    second = module.homepage()
    assert first == second
    assert re.search(r'/assets/css/site\.[0-9a-f]{12}\.css', first)
    assert re.search(r'/assets/js/site\.[0-9a-f]{12}\.js', first)

def test_fonts_are_self_hosted_and_mobile_art_is_optimized():
    for path in (ROOT / "fonts/fraunces-latin.woff2", ROOT / "fonts/inter-latin.woff2", ROOT / "images/case-intelligence-hero-mobile.webp"):
        assert path.is_file() and path.stat().st_size > 1000, path
    assert "fonts.googleapis.com" not in (ROOT / "index.html").read_text(encoding="utf-8")
    assert "font-display:optional" in CSS_SOURCE
    assert "/fonts/fraunces-latin.woff2" in CSS_SOURCE
    assert "/fonts/inter-latin.woff2" in CSS_SOURCE
    assert (ROOT / "images/case-intelligence-hero-mobile.webp").stat().st_size < (ROOT / "images/case-intelligence-hero.webp").stat().st_size
