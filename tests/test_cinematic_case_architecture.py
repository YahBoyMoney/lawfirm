"""Contract tests for the Case Architecture cinematic homepage.

These lock the parts of the approved design spec that are checkable without a browser:
the provenance of the Higgsfield art, the responsive variant set and its budget, the scene
structure and its markers, the progressive-enhancement gating, and the preservation locks
(routes, intake contract, schema, NAP, legal copy, security headers, indexing posture).

Browser-side behaviour lives in tests/test_cinematic_browser.py.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from site_data import PRACTICES, ROUTES  # noqa: E402

CSS_SOURCE = (ROOT / "src/assets/site.css").read_text(encoding="utf-8")
JS_SOURCE = (ROOT / "src/assets/site.js").read_text(encoding="utf-8")
HOME = BeautifulSoup((ROOT / "index.html").read_text(encoding="utf-8"), "html.parser")

APPROVED_SOURCE = ROOT / "images/higgsfield-case-architecture-hero.png"
APPROVED_SHA256 = "b889acb291485cdabdc8833f4ed2e1024ca034989aec2cd12de972b671c83861"

# Scene order is the choreography from the approved spec, in document order.
SCENES = ("hero", "record", "practice", "evidence", "process", "resources", "intake")

# Budgets from the spec's performance section.
AVIF_BUDGET_KB = 300
WEBP_BUDGET_KB = 450
FALLBACK_BUDGET_KB = 700


def srcset_candidates(value):
    """Yield (path, width_descriptor_or_None) for each candidate in a srcset."""
    for candidate in value.split(","):
        parts = candidate.split()
        if not parts:
            continue
        width = None
        if len(parts) > 1 and parts[1].endswith("w"):
            width = int(parts[1][:-1])
        yield parts[0], width


def case_architecture_files():
    return sorted(ROOT.glob("images/case-architecture-*"))


# --- approved asset provenance ---------------------------------------------


def test_only_the_approved_higgsfield_derivative_is_the_public_image_source():
    digest = hashlib.sha256(APPROVED_SOURCE.read_bytes()).hexdigest()
    assert digest == APPROVED_SHA256, "public art must derive from the approved cleaned asset"
    with Image.open(APPROVED_SOURCE) as opened:
        assert opened.size == (2688, 1536)
    # The rejected original carried baked-in lettering; it must never reach the repo.
    generator = (ROOT / "scripts/make_case_architecture_assets.py").read_text(encoding="utf-8")
    assert APPROVED_SHA256 in generator, "the variant generator must pin the approved hash"
    assert "raise SystemExit" in generator, "a hash mismatch must stop the build"
    # The raw 2688px source is provenance only and is never referenced by a public page.
    for path in sorted(ROOT.glob("**/*.html")):
        assert "higgsfield-case-architecture-hero.png" not in path.read_text(encoding="utf-8"), path


def test_case_architecture_variants_cover_avif_webp_and_a_fallback_within_budget():
    files = case_architecture_files()
    assert files, "no Case Architecture variants were generated"
    suffixes = {path.suffix for path in files}
    assert {".avif", ".webp", ".png"} <= suffixes, f"missing modern/fallback formats: {suffixes}"

    planes = {path.name.rsplit("-", 1)[0] for path in files}
    assert {
        "case-architecture-world",
        "case-architecture-object",
        "case-architecture-mobile",
    } <= planes, f"missing a depth plane: {planes}"

    budgets = {".avif": AVIF_BUDGET_KB, ".webp": WEBP_BUDGET_KB, ".png": FALLBACK_BUDGET_KB}
    for path in files:
        kilobytes = path.stat().st_size / 1024
        assert kilobytes <= budgets[path.suffix], f"{path.name} is {kilobytes:.0f} KB"
        # Every variant must declare its real size and its filename width.
        with Image.open(path) as opened:
            declared = int(path.stem.rsplit("-", 1)[1])
            assert opened.width == declared, f"{path.name} is {opened.width}px wide"


def test_mobile_crop_is_a_deliberate_portrait_recomposition():
    with Image.open(ROOT / "images/case-architecture-mobile-1080.avif") as mobile:
        assert mobile.height > mobile.width, "the mobile crop must be portrait"
    with Image.open(ROOT / "images/case-architecture-world-1200.avif") as world:
        assert world.width > world.height, "the world plane stays landscape"
    # The object plane is a right-hand crop, so it is markedly narrower than the full frame.
    with Image.open(ROOT / "images/case-architecture-object-800.avif") as obj:
        assert obj.width / obj.height < 1.2, "the object plane must be a crop, not the full frame"
    # Smaller variants must actually be smaller files than their larger siblings.
    assert (ROOT / "images/case-architecture-world-1200.avif").stat().st_size < (
        ROOT / "images/case-architecture-world-2400.avif"
    ).stat().st_size


def test_hero_poster_uses_responsive_sources_and_a_mobile_crop():
    art = HOME.select_one(".home-hero-art picture")
    assert art is not None
    assert HOME.select_one(".home-hero-art")["aria-hidden"] == "true"

    avif = art.select('source[type="image/avif"]')
    webp = art.select('source[type="image/webp"]')
    assert avif and webp, "the hero must negotiate AVIF and WebP"
    # AVIF is offered before WebP so capable browsers take the smallest payload.
    assert str(art).index('type="image/avif"') < str(art).index('type="image/webp"')

    mobile_sources = [s for s in avif + webp if s.get("media")]
    assert mobile_sources, "the hero needs a mobile-specific crop source"
    for source in mobile_sources:
        assert "max-width" in source["media"]
        for path, _ in srcset_candidates(source["srcset"]):
            assert "case-architecture-mobile" in path, path

    for source in avif + webp:
        for path, width in srcset_candidates(source["srcset"]):
            target = ROOT / path.lstrip("/")
            assert target.is_file(), f"missing hero variant {path}"
            if width:
                with Image.open(target) as opened:
                    assert opened.width == width, f"{path} claims {width}w"

    fallback = art.select_one("img")
    assert fallback["src"].startswith("/images/case-architecture-")
    assert fallback["fetchpriority"] == "high" and fallback["decoding"] == "async"
    # Decorative per the approved asset brief: the headline lives in HTML, not in the art.
    assert fallback["alt"] == ""
    with Image.open(ROOT / fallback["src"].lstrip("/")) as opened:
        assert (int(fallback["width"]), int(fallback["height"])) == opened.size


def test_object_depth_plane_is_css_gated_and_not_loaded_on_small_screens():
    # The object plane is a decorative second depth layer. It is delivered through CSS
    # image-set so coarse-pointer and narrow viewports never pay for it.
    assert "case-architecture-object" in CSS_SOURCE
    assert "image-set(" in CSS_SOURCE
    assert "case-architecture-object" not in str(HOME), "the object plane must stay in CSS"
    gated = re.search(
        r"@media\(min-width:960px\) and \(hover:hover\) and \(pointer:fine\)\{(.*?)\n", CSS_SOURCE
    )
    assert gated, "the object plane needs a fine-pointer desktop gate"
    assert "case-architecture-object" in gated.group(1)


# --- cinematic scene structure ---------------------------------------------


def test_homepage_renders_every_directed_scene_in_order():
    scenes = [section["data-scene"] for section in HOME.select("[data-scene]")]
    assert scenes == list(SCENES), f"scene choreography drifted: {scenes}"
    for scene in HOME.select("[data-scene]"):
        assert scene.name == "section", f"{scene['data-scene']} must be a semantic section"
        assert scene.select_one("h1, h2"), f"{scene['data-scene']} needs a heading"


def test_decorative_scene_layers_are_hidden_from_assistive_technology():
    layers = HOME.select("[data-plane], .ghost-type")
    assert layers, "the directed world needs depth planes"
    for layer in layers:
        assert layer.get("aria-hidden") == "true", layer.get("class")
        assert not layer.get_text(strip=True) or layer.get("data-ghost"), layer.get("class")
    planes = {layer.get("data-plane") for layer in HOME.select("[data-plane]")}
    assert {"world", "lines", "ribbon"} <= planes, f"missing depth planes: {planes}"


def test_ghost_typography_is_decorative_only():
    ghosts = HOME.select(".ghost-type")
    assert len(ghosts) >= 3, "editorial ghost type is a structural device in the spec"
    words = {str(ghost.get("data-ghost", "")).upper() for ghost in ghosts}
    assert {"MATTER", "RECORD", "PROOF", "EVIDENCE"} <= words, words
    for ghost in ghosts:
        assert ghost.get("aria-hidden") == "true"
        assert not ghost.get_text(strip=True), "decorative words render only through CSS pseudo-content"
        # Ghost words must never be the only place a real word appears.
        assert ghost.name in {"span", "div", "p"}, ghost.name


def test_practice_progression_lists_all_seven_categories_in_document_flow():
    scene = HOME.select_one('[data-scene="practice"]')
    items = scene.select("[data-practice]")
    assert len(items) == len(PRACTICES) == 7
    for item, practice in zip(items, PRACTICES):
        assert item["data-practice"] == practice["slug"]
        text = item.get_text(" ", strip=True)
        assert practice["name"] in text
        # The sourced description stays in readable document flow, not only in a pinned stage.
        assert practice["card"][:40] in text, practice["slug"]
        assert item.select_one(f'a[href="/practice-areas/{practice["slug"]}/"]')
    stage = scene.select_one("[data-practice-stage]")
    assert stage is not None and stage.get("aria-hidden") == "true", "the pinned stage is decorative"


def test_evidence_scene_keeps_the_timing_statements_as_markers():
    scene = HOME.select_one('[data-scene="evidence"]')
    markers = scene.select("[data-evidence-marker]")
    assert len(markers) == 3
    for marker in markers:
        assert marker.select_one("strong, h3"), "each evidence marker needs a visible label"
        assert len(marker.get_text(" ", strip=True)) > 60
    text = scene.get_text(" ", strip=True).lower()
    assert "deadline" in text and "overwritten" in text
    # No countdown or universal deadline claim.
    assert "days left" not in text and "statute of limitations is" not in text


def test_process_scene_preserves_all_five_case_review_stages():
    scene = HOME.select_one('[data-scene="process"]')
    assert scene.has_attr("data-timeline"), "the process scene is the single timeline root"
    assert len(HOME.select("[data-timeline]")) == 1
    steps = scene.select("[data-timeline-step]")
    assert len(steps) == 5
    for position, step in enumerate(steps, 1):
        assert step["data-step"] == str(position)
        assert step.select_one("h3").get_text(strip=True)
        assert step.select_one(".case-step-bring").get_text(strip=True)
        assert not step.has_attr("data-active"), "no JS-only state in static output"
    text = scene.get_text(" ", strip=True).lower()
    # The stage copy's own no-promise language, preserved verbatim from the approved source.
    assert "written agreement is signed" in text
    assert "contact alone is not acceptance" in text
    assert "conflicts check" in text
    assert "nothing here is a promise about a result" in text


def test_resource_zone_is_the_calm_light_editorial_rest():
    scene = HOME.select_one('[data-scene="resources"]')
    classes = " ".join(scene.get("class", []))
    assert "scene--paper" in classes, "the resource zone is the ivory rest in the dark world"
    links = {a["href"] for a in scene.select('a[href^="/resources/"]')}
    assert len(links) >= 4, links
    assert scene.select_one('img[src="/images/tam-berhe.jpg"]'), "Tam Berhe portrait is preserved"
    assert scene.select(".faq-item"), "FAQs stay in the readable light zone"


def test_intake_scene_resolves_the_dark_world_around_the_real_form():
    scene = HOME.select_one('[data-scene="intake"]')
    form = scene.select_one("form[data-intake-form]")
    assert form is not None
    assert form["action"] == "https://admin.berhelaw.com/api/leads/case-review"
    assert form["method"] == "post"
    assert scene.select_one("[data-plane]"), "the object resolves into a frame around the panel"


def test_process_pin_uses_the_case_object_and_intake_notice_restores_paper_contrast():
    css = (ROOT / "src/assets/site.css").read_text(encoding="utf-8")
    assert ".cinema .process-pin-object" in css
    assert 'url("/images/case-architecture-object-1200.avif")' in css
    assert ".scene .intake-form .notice{background:var(--paper);color:var(--ink)}" in css


def test_intake_pages_are_marked_for_safe_no_javascript_mobile_layout():
    intake_pages = [
        ROOT / "free-case-review" / "index.html",
        ROOT / "landing" / "garden-grove-chemical-leak" / "index.html",
        ROOT / "landing" / "truck-fleet-rideshare-accident-california" / "index.html",
    ]
    for page in intake_pages:
        doc = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser")
        assert doc.body is not None
        assert 'class="has-intake-form"' in str(doc.body), page
    assert "html:not(.js) body.has-intake-form .mobile-actions{display:none}" in CSS_SOURCE
    assert "html:not(.js) .site-header{position:relative}" in CSS_SOURCE


# --- progressive enhancement gating ----------------------------------------


def test_enhanced_desktop_mode_checks_every_required_capability():
    for guard in (
        "'IntersectionObserver' in window",
        "typeof window.requestAnimationFrame === 'function'",
        "matchMedia('(prefers-reduced-motion: reduce)')",
        "(min-width: 960px)",
        "(hover: hover)",
        "(pointer: fine)",
    ):
        assert guard in JS_SOURCE, f"missing enhancement gate: {guard}"
    # The cinematic class is added in exactly one place and removed on any failure.
    assert JS_SOURCE.count("classList.add('cinema')") == 1
    assert "classList.remove('cinema')" in JS_SOURCE


def test_scene_progress_uses_one_scheduler_and_restrained_custom_properties():
    for prop in ("--hero-progress", "--practice-progress", "--process-progress", "--scroll-progress"):
        assert prop in JS_SOURCE, prop
        assert prop in CSS_SOURCE, prop
    assert JS_SOURCE.count("requestAnimationFrame(update)") == 1, "one rAF scheduler only"
    # Native scrolling only.
    for blocked in ("wheel", "touchmove", "scrollTo(", "preventDefault"):
        assert blocked not in JS_SOURCE, f"{blocked} would fight the native scroller"


def test_sticky_scenes_are_css_only_and_scoped_to_the_cinema_class():
    sticky_rules = [
        (selector, block)
        for selector, block in re.findall(r"([^{}]+)\{([^{}]*)\}", CSS_SOURCE)
        if "position:sticky" in block and "guide-aside" not in selector and "site-header" not in selector
    ]
    assert sticky_rules, "pinned scenes must use CSS position: sticky"
    for selector, _ in sticky_rules:
        assert ".cinema" in selector, f"sticky scene not gated on the enhancement class: {selector}"
    # No JavaScript scroll positioning anywhere.
    assert "scrollTop =" not in JS_SOURCE and "scroll-behavior" not in JS_SOURCE


def test_no_scene_rule_hides_content_outside_the_enhancement_classes():
    offenders = []
    for selector, block in re.findall(r"([^{}]+)\{([^{}]*)\}", CSS_SOURCE):
        if selector.strip() in {"from", "to"} or re.fullmatch(r"[\d.]+%", selector.strip()):
            continue
        hooks = ("[data-scene]", "[data-practice", "[data-evidence", "scene-copy", "scene-body")
        if not any(hook in selector for hook in hooks):
            continue
        hidden = re.search(r"opacity:0(?![.\d])", block) or "visibility:hidden" in block
        if hidden and ".motion" not in selector and ".cinema" not in selector and "!important" not in block:
            offenders.append(selector)
    assert not offenders, f"scene content hidden outside the enhancement classes: {offenders}"


def test_reduced_motion_disables_the_cinematic_layer():
    reduced = " ".join(re.findall(r"@media\(prefers-reduced-motion:reduce\)\{(.+?)\n", CSS_SOURCE + "\n"))
    assert "ghost-type" in reduced, "ghost type must stop animating under reduced motion"
    assert "position:static!important" in reduced, "pinned scenes must unpin under reduced motion"


# --- preservation locks -----------------------------------------------------


def test_routes_sitemap_and_indexing_posture_survive_the_rebuild():
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    for route in ROUTES:
        assert f"<loc>https://berhelaw.com{route}</loc>" in sitemap, route
    assert "/success.html" not in sitemap
    assert len(re.findall(r"<loc>", sitemap)) == len(ROUTES)
    assert HOME.select_one('meta[name="robots"]')["content"] == "index, follow"
    assert HOME.select_one('link[rel="canonical"]')["href"] == "https://berhelaw.com/"


def test_homepage_schema_and_nap_are_unchanged():
    graph = json.loads(HOME.select_one('script[type="application/ld+json"]').string)["@graph"]
    types = {node["@type"] for node in graph}
    assert {"WebSite", "LegalService", "WebPage", "FAQPage"} <= types, types
    firm = next(node for node in graph if node["@type"] == "LegalService")
    assert firm["name"] == "The Berhe Law Firm, APC"
    assert firm["telephone"] == "+1-909-609-6685"
    assert firm["address"]["streetAddress"] == "901 Via Piemonte, Suite 230"
    assert firm["address"]["postalCode"] == "91764-8500"
    footer = HOME.select_one("footer").get_text(" ", strip=True)
    assert "901 Via Piemonte, Suite 230, Ontario, CA 91764-8500" in footer
    assert HOME.select_one('footer a[href="tel:+19096096685"]')


def test_intake_field_contract_and_guidance_are_byte_for_byte_preserved():
    form = HOME.select_one("form[data-intake-form]")
    names = {field.get("name") for field in form.select("input, select, textarea")}
    assert {
        "firstName", "lastName", "phone", "email", "summary", "consent", "bot-field",
        "matterType", "page_url", "referrer", "campaign", "form_version", "consent_version",
    } <= names, names
    assert form.select_one('input[name="bot-field"]').find_parent(class_="honeypot")
    assert form.select_one('input[name="consent"]').has_attr("required")
    notice = form.select_one(".notice").get_text(" ", strip=True)
    assert "Do not send privileged" in notice and "909-609-6685" in notice
    consent = form.select_one("label.consent").get_text(" ", strip=True)
    assert "does not create an attorney-client relationship" in consent
    assert "signed written agreement" in consent
    assert form.select_one('button[type="submit"]'), "native no-JavaScript submission stays"


def test_legal_and_no_guarantee_language_survives_the_redesign():
    text = HOME.get_text(" ", strip=True)
    for phrase in (
        "Attorney advertising",
        "not legal advice",
        "does not create an attorney-client relationship",
        "conflicts review and a signed written agreement",
        "The Berhe Law Firm, APC is responsible for this website",
    ):
        assert phrase in text, phrase
    banned = (
        "guaranteed", "we win", "no fee guarantee", "award-winning", "best lawyer",
        "top-rated", "specialist in", "millions recovered", "within 24 hours",
    )
    lowered = text.lower()
    for phrase in banned:
        assert phrase not in lowered, f"unsupported claim reached the homepage: {phrase}"


def test_security_headers_and_authorized_logo_are_preserved():
    headers = (ROOT / "_headers").read_text(encoding="utf-8")
    for header in (
        "Strict-Transport-Security", "X-Content-Type-Options: nosniff", "X-Frame-Options: DENY",
        "Cross-Origin-Opener-Policy: same-origin", "Permissions-Policy",
    ):
        assert header in headers, header
    assert "form-action https://admin.berhelaw.com" in headers
    assert "unsafe-inline" not in headers and "unsafe-eval" not in headers
    # The public mark is a lossless responsive derivative of the hash-locked official source.
    logo = HOME.select_one('header img[src="/images/the-berhe-law-firm-apc-logo-white-320.webp"]')
    assert logo and (int(str(logo["width"])), int(str(logo["height"]))) == (320, 191)
    assert logo["alt"] == "The Berhe Law Firm, APC"
    assert "the-berhe-law-firm-apc-logo-white" not in CSS_SOURCE, "do not restyle the mark's pixels"
    assert HOME.head is not None
    head_script = HOME.head.select_one('script[src^="/assets/js/head."]')
    assert head_script and not head_script.has_attr("defer")
    assert "'sha256-" not in headers, "the early enhancement flag stays external under script-src self"
