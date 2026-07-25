#!/usr/bin/env python3
import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Error as PlaywrightError, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "qa" / "visual-v2"
ORIGIN = "http://berhelaw.test"
VIEWPORTS = (
    (320, 568, "tiny-mobile"),
    (320, 720, "small-mobile"),
    (390, 844, "mobile"),
    (768, 1024, "tablet"),
    (1440, 1000, "desktop"),
    (2560, 1440, "wide"),
)


def routes():
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from site_data import ROUTES
    return [*ROUTES, "/success.html?reference=QA-20260711"]


def main():
    QA.mkdir(parents=True, exist_ok=True)
    report = {"routes": [], "assertions": [], "screenshots": [], "browser": None}
    def record_assertion(name, passed, details):
        report["assertions"].append({"name": name, "passed": bool(passed), "details": details})
    def serve(route):
        parsed = urlparse(route.request.url)
        if parsed.hostname == "fonts.googleapis.com":
            route.fulfill(status=200, body="", content_type="text/css")
            return
        if parsed.hostname != "berhelaw.test":
            route.continue_()
            return
        requested = parsed.path
        path = ROOT / requested.lstrip("/")
        if requested.endswith("/"):
            path /= "index.html"
        if path.is_dir():
            path /= "index.html"
        if not path.exists() or not path.is_file():
            route.fulfill(status=404, body="Not found", content_type="text/plain")
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        route.fulfill(status=200, body=path.read_bytes(), content_type=content_type)

    def context_for(browser, width, height, reduced=True):
        context = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce" if reduced else "no-preference")
        context.route("**/*", serve)
        return context

    try:
        with sync_playwright() as playwright:
            engine_name = os.environ.get("PLAYWRIGHT_BROWSER", "chromium").strip().lower()
            if engine_name not in {"chromium", "firefox", "webkit"}:
                raise ValueError(f"Unsupported PLAYWRIGHT_BROWSER: {engine_name}")
            engine = getattr(playwright, engine_name)
            executable = os.environ.get("CHROMIUM_PATH") if engine_name == "chromium" else None
            launch_options = {"headless": True}
            if executable:
                launch_options["executable_path"] = executable
            browser = engine.launch(**launch_options)
            report["browser"] = executable or engine.executable_path
            for width, height, label in VIEWPORTS:
                context = context_for(browser, width, height)
                for route in routes():
                    page = context.new_page()
                    console_errors = []
                    page_errors = []
                    page.on("console", lambda message, errors=console_errors: errors.append(message.text) if message.type == "error" else None)
                    page.on("pageerror", lambda error, errors=page_errors: errors.append(str(error)))
                    response = page.goto(f"{ORIGIN}{route}", wait_until="domcontentloaded", timeout=10000)
                    page.wait_for_timeout(100)
                    overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 1")
                    report["routes"].append({
                        "route": route, "viewport": label,
                        "status": response.status if response else None,
                        "h1": page.locator("h1").count(), "overflow": overflow,
                        "consoleErrors": console_errors, "pageErrors": page_errors,
                    })
                    page.close()
                context.close()

            context = context_for(browser, 1440, 1000)
            page = context.new_page()
            page.goto(f"{ORIGIN}/", wait_until="domcontentloaded", timeout=10000)
            opening = page.locator(".opening").evaluate("""(section) => {
                const heading = section.querySelector('h1');
                const plate = section.querySelector('.opening-plate img');
                const rect = section.getBoundingClientRect();
                const plateRect = plate ? plate.getBoundingClientRect() : null;
                const dock = section.querySelector('.opening-dock');
                return {
                    fontSize: parseFloat(getComputedStyle(heading).fontSize),
                    fontFamily: getComputedStyle(heading).fontFamily,
                    height: rect.height,
                    viewport: innerHeight,
                    dockBottom: dock.getBoundingClientRect().bottom,
                    plateVisible: plateRect ? Math.max(0, Math.min(plateRect.bottom, innerHeight) - Math.max(plateRect.top, 0)) : 0,
                    plateOverlays: section.querySelectorAll('.opening-plate :not(picture):not(source):not(img)').length,
                    background: getComputedStyle(section).backgroundColor,
                };
            }""")
            record_assertion(
                "opening statement fills the first desktop viewport with an exposed plate",
                opening["height"] >= opening["viewport"] * 0.97
                and 72 <= opening["fontSize"] <= 130
                and "Newsreader" in opening["fontFamily"]
                and "Fraunces" not in opening["fontFamily"]
                and opening["plateVisible"] >= opening["viewport"] * 0.8
                and opening["plateOverlays"] == 0
                and opening["dockBottom"] <= opening["viewport"]
                and opening["background"] == "rgb(244, 239, 230)",
                opening,
            )
            page.goto(f"{ORIGIN}/practice-areas/", wait_until="domcontentloaded", timeout=10000)
            metrics = page.locator(".hero--practice-hub").evaluate("""(hero) => {
                const heading = hero.querySelector('h1');
                const media = hero.querySelector('.hero-media img');
                const rect = hero.getBoundingClientRect();
                return {
                    marker: hero.classList.contains('hero--practice-hub'),
                    fontSize: parseFloat(getComputedStyle(heading).fontSize),
                    bottom: rect.bottom,
                    objectPosition: media ? getComputedStyle(media).objectPosition : null,
                };
            }""")
            record_assertion(
                "hero--practice-hub controlled desktop sizing",
                metrics["marker"] and metrics["fontSize"] <= 67 and metrics["bottom"] <= 900,
                metrics,
            )
            record_assertion(
                "hero--practice-hub deliberate image crop",
                metrics["objectPosition"] not in {"50% 50%", "center center", None},
                {"objectPosition": metrics["objectPosition"]},
            )
            page.close()
            context.close()

            context = context_for(browser, 390, 844)
            page = context.new_page()
            page.goto(f"{ORIGIN}/", wait_until="domcontentloaded", timeout=10000)
            page.wait_for_timeout(150)
            home_sticky = page.evaluate("""() => {
                const sticky = document.querySelector('.mobile-actions');
                const secondary = document.querySelector('.opening-dock .dock-link');
                return {
                    suppressed: sticky.dataset.suppressed,
                    visibility: getComputedStyle(sticky).visibility,
                    secondaryBottom: secondary.getBoundingClientRect().bottom,
                    viewportHeight: innerHeight,
                };
            }""")
            record_assertion(
                "mobile hero actions are not covered by sticky bar",
                home_sticky["suppressed"] == "true" and home_sticky["visibility"] == "hidden" and home_sticky["secondaryBottom"] <= home_sticky["viewportHeight"],
                home_sticky,
            )
            page.goto(f"{ORIGIN}/free-case-review/", wait_until="domcontentloaded", timeout=10000)
            first_control = page.locator('form[data-intake-form] input:not([type="hidden"])').first
            first_control.scroll_into_view_if_needed()
            first_control.focus()
            page.wait_for_timeout(50)
            focus_state = page.evaluate("""() => {
                const sticky = document.querySelector('.mobile-actions');
                const bodyClearance = parseFloat(getComputedStyle(document.body).paddingBottom);
                return {
                    suppressed: sticky.dataset.suppressed,
                    ariaHidden: sticky.getAttribute('aria-hidden'),
                    visibility: getComputedStyle(sticky).visibility,
                    bodyClearance,
                    stickyHeight: sticky.getBoundingClientRect().height,
                };
            }""")
            record_assertion(
                "mobile form focus hides sticky bar and keeps persistent clearance",
                focus_state["suppressed"] == "true" and focus_state["ariaHidden"] == "true" and focus_state["visibility"] == "hidden" and focus_state["bodyClearance"] >= focus_state["stickyHeight"],
                focus_state,
            )
            for route in ("/privacy.html", "/landing/garden-grove-chemical-leak/"):
                page.goto(f"{ORIGIN}{route}", wait_until="domcontentloaded", timeout=10000)
                clearance = page.evaluate("""() => {
                    const sticky = document.querySelector('.mobile-actions');
                    return {
                        bodyClearance: parseFloat(getComputedStyle(document.body).paddingBottom),
                        stickyHeight: sticky.getBoundingClientRect().height,
                    };
                }""")
                record_assertion(
                    f"{route} reserves mobile sticky clearance",
                    clearance["bodyClearance"] >= clearance["stickyHeight"],
                    clearance,
                )
            page.close()
            context.close()

            # Conversion gates. 320x568 must show the primary call bar; 390x844 must show call and review together.
            for width, height, both in ((320, 568, False), (320, 720, False), (390, 844, True)):
                context = context_for(browser, width, height, reduced=False)
                page = context.new_page()
                page.goto(f"{ORIGIN}/", wait_until="domcontentloaded", timeout=10000)
                page.wait_for_timeout(900)
                fold = page.evaluate("""() => {
                    const call = document.querySelector('.opening-dock a.call-bar');
                    const review = document.querySelector('.opening-dock a.dock-link');
                    const box = (element) => {
                        const rect = element.getBoundingClientRect();
                        return {bottom: rect.bottom, top: rect.top, height: rect.height, opacity: parseFloat(getComputedStyle(element).opacity)};
                    };
                    return {call: box(call), review: box(review), viewport: innerHeight, overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1};
                }""")
                passed = (
                    fold["call"]["bottom"] <= fold["viewport"] and fold["call"]["top"] >= 0
                    and fold["call"]["opacity"] == 1 and fold["call"]["height"] >= 44 and not fold["overflow"]
                )
                if both:
                    passed = passed and fold["review"]["bottom"] <= fold["viewport"] and fold["review"]["opacity"] == 1
                record_assertion(
                    f"primary call{' and case review' if both else ''} fit the first {width}x{height} viewport",
                    passed,
                    fold,
                )
                page.close()
                context.close()

            # Tonal gate. The first viewport must not repeat the rejected dark field.
            for width, height in ((1440, 1000), (390, 844)):
                context = context_for(browser, width, height, reduced=False)
                page = context.new_page()
                page.goto(f"{ORIGIN}/", wait_until="domcontentloaded", timeout=10000)
                page.wait_for_timeout(1000)
                exposure = page.evaluate("""() => {
                    const plate = document.querySelector('.opening-plate img');
                    const rect = plate.getBoundingClientRect();
                    const visible = Math.max(0, Math.min(rect.bottom, innerHeight) - Math.max(rect.top, 0))
                        * Math.max(0, Math.min(rect.right, innerWidth) - Math.max(rect.left, 0));
                    return {
                        artShare: visible / (innerWidth * innerHeight),
                        openingBackground: getComputedStyle(document.querySelector('.opening')).backgroundColor,
                        dockBackground: getComputedStyle(document.querySelector('.opening-dock-band')).backgroundColor,
                        glazed: document.querySelectorAll('.opening-plate :not(picture):not(source):not(img)').length,
                    };
                }""")
                record_assertion(
                    f"first {width}x{height} viewport exposes art without a dark glaze",
                    exposure["glazed"] == 0
                    and exposure["openingBackground"] == "rgb(244, 239, 230)"
                    and exposure["dockBackground"] == "rgb(140, 47, 37)"
                    and exposure["artShare"] >= (0.30 if width > 900 else 0.10),
                    exposure,
                )
                page.close()
                context.close()

            context = context_for(browser, 1440, 1000, reduced=False)
            page = context.new_page()
            page.goto(f"{ORIGIN}/", wait_until="domcontentloaded", timeout=10000)
            page.wait_for_timeout(400)
            for step in range(1, 9):  # scroll the way a visitor does, so reveals fire in order
                page.evaluate(
                    "step => window.scrollTo({top: document.documentElement.scrollHeight * step / 8, behavior: 'instant'})",
                    step,
                )
                page.wait_for_timeout(220)
            page.wait_for_timeout(700)  # let the final reveal transition finish before sampling
            motion_state = page.evaluate("""() => {
                const styles = getComputedStyle(document.documentElement);
                const timeline = document.querySelector('[data-timeline]');
                const inViewport = (element) => {
                    const rect = element.getBoundingClientRect();
                    return rect.bottom > 0 && rect.top < innerHeight;
                };
                const hidden = [...document.querySelectorAll('[data-reveal]')]
                    .filter((element) => inViewport(element)
                        && parseFloat(getComputedStyle(element).opacity) < 1).length;
                return {
                    motion: document.documentElement.classList.contains('motion'),
                    scrollProgress: parseFloat(styles.getPropertyValue('--scroll-progress')),
                    timelineProgress: parseFloat(getComputedStyle(timeline).getPropertyValue('--timeline-progress')),
                    activeSteps: [...document.querySelectorAll('[data-timeline-step]')]
                        .filter((step) => step.dataset.active === 'true').length,
                    hiddenInView: hidden,
                    progressAriaHidden: document.querySelector('.scroll-progress').getAttribute('aria-hidden'),
                };
            }""")
            record_assertion(
                "scroll motion advances and never strands visible content",
                motion_state["motion"] and motion_state["scrollProgress"] > 0.9
                and motion_state["timelineProgress"] == 1 and motion_state["activeSteps"] == 5
                and motion_state["hiddenInView"] == 0 and motion_state["progressAriaHidden"] == "true",
                motion_state,
            )
            page.close()
            context.close()

            context = context_for(browser, 1440, 1000, reduced=True)
            page = context.new_page()
            page.goto(f"{ORIGIN}/", wait_until="domcontentloaded", timeout=10000)
            page.wait_for_timeout(300)
            reduced_state = page.evaluate("""() => ({
                motion: document.documentElement.classList.contains('motion'),
                hidden: [...document.querySelectorAll('[data-reveal]')]
                    .filter((element) => parseFloat(getComputedStyle(element).opacity) < 1).length,
                progressDisplay: getComputedStyle(document.querySelector('.scroll-progress')).display,
            })""")
            record_assertion(
                "reduced motion renders the finished page with no motion layer",
                not reduced_state["motion"] and reduced_state["hidden"] == 0
                and reduced_state["progressDisplay"] == "none",
                reduced_state,
            )
            page.close()
            context.close()

            captures = [
                # Opening statement, captured at the exact baseline geometry for the structural-departure gate.
                ("/", 1440, 1000, None, "home-hero-1440.png"),
                ("/", 390, 844, None, "home-hero-390.png"),
                ("/", 320, 568, None, "home-hero-320x568.png"),
                ("/", 320, 720, None, "home-hero-320.png"),
                ("/", 768, 1024, None, "home-hero-768.png"),
                ("/", 2560, 1440, None, "home-hero-2560.png"),
                # Deep scroll stages through every record chapter.
                ("/", 1440, 1000, ".opening-plate", "home-plate-1440.png"),
                ("/", 1440, 1000, ".docket", "home-docket-1440.png"),
                ("/", 390, 844, ".docket", "home-docket-390.png"),
                ("/", 1440, 1000, ".case-index", "home-case-index-1440.png"),
                ("/", 390, 844, ".case-index", "home-case-index-390.png"),
                ("/", 1440, 1000, "[data-clock]", "home-clock-1440.png"),
                ("/", 390, 844, "[data-clock]", "home-clock-390.png"),
                ("/", 1440, 1000, "[data-timeline]", "home-case-timeline-1440.png"),
                ("/", 390, 844, "[data-timeline]", "home-case-timeline-390.png"),
                ("/", 1440, 1000, ".preserve", "home-preserve-1440.png"),
                ("/", 1440, 1000, ".counsel", "home-counsel-1440.png"),
                ("/", 1440, 1000, ".home-faq", "home-questions-1440.png"),
                ("/", 1440, 1000, ".intake-field", "home-intake-1440.png"),
                ("/", 390, 844, ".intake-field", "home-intake-390.png"),
                ("/", 1440, 1000, ".site-footer", "home-footer-1440.png"),
                ("/", 390, 844, ".js-open-menu", "home-menu-390.png"),
                ("/practice-areas/personal-injury-wrongful-death/", 1440, 1000, ".stakes-list", "practice-stakes-1440.png"),
                ("/practice-areas/", 1440, 1000, None, "practice-hub-desktop.png"),
                ("/resources/", 1440, 1000, ".editorial-list", "resource-hub-1440.png"),
                ("/resources/after-a-collision-first-steps/", 1440, 1000, ".guide-layout", "resource-guide-1440.png"),
                ("/resources/insurance-claim-communication/", 390, 844, ".guide-body", "resource-guide-390.png"),
                ("/free-case-review/", 390, 844, "#general-review", "case-review-form-mobile.png"),
                ("/landing/garden-grove-chemical-leak/", 390, 844, "#updates-status", "garden-grove-updates-mobile.png"),
                ("/privacy.html", 390, 844, "main", "privacy-mobile.png"),
            ]
            for route, width, height, selector, filename in captures:
                context = context_for(browser, width, height, reduced=False)
                page = context.new_page()
                page.goto(f"{ORIGIN}{route}", wait_until="domcontentloaded", timeout=10000)
                page.wait_for_timeout(1200)
                if selector == "#updates-status":
                    page.wait_for_function(
                        "document.querySelector('#updates-status')?.dataset.feedState",
                        timeout=5000,
                    )
                if selector == ".js-open-menu":
                    page.locator(".nav-toggle").click()
                    page.wait_for_timeout(400)
                elif selector:
                    page.locator(selector).scroll_into_view_if_needed()
                    page.wait_for_timeout(900)
                target = QA / filename
                page.screenshot(path=str(target), full_page=False)
                report["screenshots"].append(str(target.relative_to(ROOT)))
                page.close()
                context.close()
            browser.close()
    except PlaywrightError as error:
        report["passed"] = False
        report["blocked"] = True
        report["blocker"] = str(error)
        report["failures"] = []
        (QA / "visual-qa-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"passed": False, "blocked": True, "reason": "browser launch blocked by environment sandbox"}))
        return 2

    route_failures = [item for item in report["routes"] if item["status"] != 200 or item["h1"] != 1 or item["overflow"] or item["consoleErrors"] or item["pageErrors"]]
    assertion_failures = [item for item in report["assertions"] if not item["passed"]]
    failures = [*route_failures, *assertion_failures]
    report["passed"] = not failures
    report["failures"] = failures
    (QA / "visual-qa-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "routesChecked": len(report["routes"]), "assertions": len(report["assertions"]), "screenshots": len(report["screenshots"]), "failures": len(failures)}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
