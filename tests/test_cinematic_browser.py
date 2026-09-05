"""Browser contract for the Case Architecture cinematic homepage.

Runs against every engine Playwright can launch here (Chromium and WebKit) and covers the
behaviour that static parsing cannot prove: enhancement gating, fail-open under reduced motion
and without JavaScript, responsive source selection, first-viewport CTA on small phones, and
the absence of overflow, trapped sticky layers, and console or page errors.

No test submits the intake form.
"""
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import pytest
from playwright.sync_api import Error as PlaywrightError, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://berhelaw.test"
ENGINES = ("chromium", "webkit")


@pytest.fixture(scope="module", params=ENGINES)
def engine(request):
    with sync_playwright() as playwright:
        launcher = getattr(playwright, request.param)
        try:
            browser = launcher.launch(headless=True)
        except PlaywrightError as error:
            pytest.skip(f"{request.param} unavailable: {error}")
        yield browser
        browser.close()


def local_file(pathname):
    path = ROOT / pathname.lstrip("/")
    if pathname.endswith("/"):
        path /= "index.html"
    if path.is_dir():
        path /= "index.html"
    return path


def install_routes(context):
    def serve(route):
        parsed = urlparse(route.request.url)
        if parsed.hostname != "berhelaw.test":
            route.abort()
            return
        path = local_file(parsed.path)
        if not path.is_file():
            route.fulfill(status=404, body="Not found", content_type="text/plain")
            return
        route.fulfill(
            status=200,
            body=path.read_bytes(),
            content_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        )

    context.route("**/*", serve)


def open_home(
    engine, *, width=1440, height=1000, reduced=False, javascript=True, touch=False, route="/"
):
    context = engine.new_context(
        viewport={"width": width, "height": height},
        reduced_motion="reduce" if reduced else "no-preference",
        java_script_enabled=javascript,
        has_touch=touch,
    )
    install_routes(context)
    page = context.new_page()
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("requestfailed", lambda r: errors.append(f"request failed: {r.url}"))
    page.goto(f"{ORIGIN}{route}", wait_until="load", timeout=15000)
    page.wait_for_timeout(400)
    return context, page, errors


# --- enhancement gating -----------------------------------------------------


def test_enhanced_desktop_mode_only_engages_on_capable_desktop(engine):
    context, page, errors = open_home(engine)
    assert page.evaluate("document.documentElement.classList.contains('cinema')")
    assert page.evaluate("document.documentElement.classList.contains('motion')")
    assert not errors, errors
    context.close()


def test_enhanced_mode_stays_off_for_narrow_and_coarse_pointer_visitors(engine):
    context, page, _ = open_home(engine, width=390, height=844, touch=True)
    assert not page.evaluate("document.documentElement.classList.contains('cinema')")
    # Base reveal motion may still run; nothing may stay hidden.
    hidden = page.evaluate(
        "[...document.querySelectorAll('[data-scene] h2')]"
        ".filter(n => parseFloat(getComputedStyle(n).opacity) < 1).length"
    )
    assert hidden == 0
    context.close()


def test_reduced_motion_removes_every_enhancement_class(engine):
    context, page, _ = open_home(engine, reduced=True)
    state = page.evaluate(
        """() => ({
            cinema: document.documentElement.classList.contains('cinema'),
            motion: document.documentElement.classList.contains('motion'),
            hidden: [...document.querySelectorAll('[data-reveal]')]
                .filter(n => parseFloat(getComputedStyle(n).opacity) < 1).length,
            sticky: [...document.querySelectorAll('[data-practice-stage], [data-scene] .scene-pin')]
                .filter(n => getComputedStyle(n).position === 'sticky').length,
        })"""
    )
    assert state == {"cinema": False, "motion": False, "hidden": 0, "sticky": 0}
    context.close()


def test_every_scene_is_readable_without_javascript(engine):
    context, page, _ = open_home(engine, javascript=False)
    state = page.evaluate(
        """() => {
            const scenes = [...document.querySelectorAll('[data-scene]')];
            return {
                count: scenes.length,
                cinema: document.documentElement.classList.contains('cinema'),
                invisible: scenes.filter(s => {
                    const style = getComputedStyle(s);
                    return style.display === 'none' || style.visibility === 'hidden'
                        || parseFloat(style.opacity) < 1;
                }).map(s => s.dataset.scene),
                practices: document.querySelectorAll('[data-practice]').length,
                stages: document.querySelectorAll('[data-timeline-step]').length,
                submit: !!document.querySelector('form[data-intake-form] button[type=submit]'),
            };
        }"""
    )
    assert state["count"] == 7
    assert state["cinema"] is False
    assert state["invisible"] == []
    assert state["practices"] == 7
    assert state["stages"] == 5
    assert state["submit"] is True
    context.close()


# --- responsive art ---------------------------------------------------------


def test_hero_selects_the_mobile_crop_on_phones_and_the_world_plane_on_desktop(engine):
    context, page, _ = open_home(engine, width=390, height=844, touch=True)
    page.wait_for_function("document.querySelector('.home-hero-art img').currentSrc !== ''")
    mobile_src = page.evaluate("document.querySelector('.home-hero-art img').currentSrc")
    assert "case-architecture-mobile" in mobile_src, mobile_src
    context.close()

    context, page, _ = open_home(engine, width=1440, height=1000)
    page.wait_for_function("document.querySelector('.home-hero-art img').currentSrc !== ''")
    desktop = page.evaluate(
        """() => {
            const img = document.querySelector('.home-hero-art img');
            return {src: img.currentSrc, w: img.naturalWidth, h: img.naturalHeight};
        }"""
    )
    assert "case-architecture-world" in desktop["src"], desktop
    assert desktop["w"] > desktop["h"], desktop
    context.close()


# --- small-screen usability -------------------------------------------------


@pytest.mark.parametrize("width", (320, 390))
def test_primary_case_review_cta_sits_in_the_first_mobile_viewport(engine, width):
    context, page, _ = open_home(engine, width=width, height=844, touch=True)
    fold = page.evaluate(
        """() => {
            const call = document.querySelector('.home-hero-actions a.button-call');
            const review = document.querySelector('.home-hero-actions a[href="/free-case-review/"]');
            const box = (el) => {
                const r = el.getBoundingClientRect();
                return {top: r.top, bottom: r.bottom, opacity: parseFloat(getComputedStyle(el).opacity)};
            };
            return {call: box(call), review: box(review), viewport: innerHeight};
        }"""
    )
    for key in ("call", "review"):
        assert fold[key]["top"] >= 0, (key, fold)
        assert fold[key]["bottom"] <= fold["viewport"], (key, fold)
        assert fold[key]["opacity"] == 1, (key, fold)
    context.close()


@pytest.mark.parametrize("width,height", ((320, 844), (390, 844), (768, 1024), (1440, 1000)))
def test_no_horizontal_overflow_at_any_supported_width(engine, width, height):
    context, page, _ = open_home(engine, width=width, height=height, touch=width < 700)
    page.evaluate("window.scrollTo({top: document.documentElement.scrollHeight, behavior: 'instant'})")
    page.wait_for_timeout(300)
    overflow = page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 1, f"{width}px overflows by {overflow}px"
    context.close()


def test_mobile_menu_opens_closes_with_escape_and_restores_focus(engine):
    context, page, _ = open_home(engine, width=390, height=844, touch=True)
    toggle = page.locator(".nav-toggle")
    toggle.click()
    assert toggle.get_attribute("aria-expanded") == "true"
    assert page.locator("#site-navigation").is_visible()
    page.keyboard.press("Escape")
    assert toggle.get_attribute("aria-expanded") == "false"
    assert page.evaluate("document.activeElement.classList.contains('nav-toggle')")
    context.close()


# --- scene choreography -----------------------------------------------------


def test_scene_progress_properties_advance_with_native_scrolling(engine):
    context, page, errors = open_home(engine)
    readings = []
    for step in range(0, 9):
        page.evaluate(
            "s => window.scrollTo({top: document.documentElement.scrollHeight * s / 8, behavior: 'instant'})",
            step,
        )
        page.wait_for_timeout(220)
        readings.append(
            page.evaluate(
                """() => {
                    const s = getComputedStyle(document.documentElement);
                    const read = (n) => parseFloat(s.getPropertyValue(n)) || 0;
                    return {
                        scroll: read('--scroll-progress'),
                        hero: read('--hero-progress'),
                        practice: read('--practice-progress'),
                        process: read('--process-progress'),
                    };
                }"""
            )
        )
    assert readings[0]["scroll"] < 0.05
    assert readings[-1]["scroll"] > 0.9
    for name in ("hero", "practice", "process"):
        values = [r[name] for r in readings]
        assert max(values) > 0.5, f"--{name}-progress never advanced: {values}"
        assert all(0 <= v <= 1 for v in values), f"--{name}-progress left 0..1: {values}"
    assert not errors, errors
    context.close()


def test_practice_stage_tracks_scroll_and_keyboard_focus(engine):
    context, page, _ = open_home(engine)
    page.locator('[data-scene="practice"]').scroll_into_view_if_needed()
    page.wait_for_timeout(400)
    assert page.evaluate("document.querySelectorAll('[data-practice][data-active=true]').length") >= 1

    last = page.locator("[data-practice]").last
    last.locator("a").first.focus()
    page.wait_for_timeout(250)
    assert last.get_attribute("data-active") == "true", "focus must advance the stage"
    # The pinned stage never becomes the only copy of a practice description: every item
    # keeps real layout height in document flow.
    assert page.evaluate(
        """() => [...document.querySelectorAll('[data-practice]')]
            .every(n => n.getBoundingClientRect().height > 40)"""
    )
    # A jump past the scene must never strand an item at opacity 0. The wait clears the
    # longest staggered reveal (0.42s delay plus a 0.62s transition).
    page.evaluate("window.scrollTo({top: document.documentElement.scrollHeight, behavior: 'instant'})")
    page.wait_for_timeout(1500)
    stranded = page.evaluate(
        """() => [...document.querySelectorAll('[data-practice]')]
            .filter(n => parseFloat(getComputedStyle(n).opacity) < 1)
            .map(n => n.dataset.practice)"""
    )
    assert stranded == [], stranded
    context.close()


def test_sticky_scenes_release_and_never_cover_the_footer(engine):
    context, page, _ = open_home(engine)
    page.evaluate("window.scrollTo({top: document.documentElement.scrollHeight, behavior: 'instant'})")
    page.wait_for_timeout(500)
    state = page.evaluate(
        """() => {
            const footer = document.querySelector('.site-footer');
            const rect = footer.getBoundingClientRect();
            const covering = [...document.querySelectorAll('[data-scene] *')].filter(el => {
                const style = getComputedStyle(el);
                if (style.position !== 'sticky' && style.position !== 'fixed') return false;
                const r = el.getBoundingClientRect();
                return r.bottom > rect.top + 4 && r.top < rect.bottom && r.height > 0;
            }).length;
            return {footerVisible: rect.top < innerHeight, covering};
        }"""
    )
    assert state["footerVisible"], "footer must be reachable at the end of the document"
    assert state["covering"] == 0, "a pinned layer is still trapped over the footer"
    context.close()


def test_home_loads_without_console_page_or_request_errors(engine):
    context, page, errors = open_home(engine)
    page.evaluate("window.scrollTo({top: document.documentElement.scrollHeight, behavior: 'instant'})")
    page.wait_for_timeout(600)
    assert not errors, errors
    context.close()
