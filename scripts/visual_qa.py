#!/usr/bin/env python3
import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Error as PlaywrightError, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "qa" / "overhaul-gpt56"
ORIGIN = "http://berhelaw.test"


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
            for width, height, label in ((1440, 1000, "desktop"), (390, 844, "mobile")):
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
            for route, marker, max_font, max_bottom in (
                ("/", "hero--home", 74, 820),
                ("/practice-areas/", "hero--practice-hub", 67, 870),
            ):
                page.goto(f"{ORIGIN}{route}", wait_until="domcontentloaded", timeout=10000)
                metrics = page.locator(f".{marker}").evaluate("""(hero, marker) => {
                    const heading = hero.querySelector('h1');
                    const media = hero.querySelector('.hero-media img');
                    const rect = hero.getBoundingClientRect();
                    return {
                        marker: hero.classList.contains(marker),
                        fontSize: parseFloat(getComputedStyle(heading).fontSize),
                        bottom: rect.bottom,
                        objectPosition: getComputedStyle(media).objectPosition,
                    };
                }""", marker)
                passed = metrics["marker"] and metrics["fontSize"] <= max_font and metrics["bottom"] <= max_bottom
                record_assertion(f"{marker} controlled desktop sizing", passed, metrics)
                crop_passed = metrics["objectPosition"] not in {"50% 50%", "center center"}
                record_assertion(f"{marker} deliberate image crop", crop_passed, {"objectPosition": metrics["objectPosition"]})
            page.close()
            context.close()

            context = context_for(browser, 390, 844)
            page = context.new_page()
            page.goto(f"{ORIGIN}/", wait_until="domcontentloaded", timeout=10000)
            page.wait_for_timeout(150)
            home_sticky = page.evaluate("""() => {
                const sticky = document.querySelector('.mobile-actions');
                const secondary = document.querySelector('.hero .button-secondary');
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

            captures = [
                ("/", 1440, 1000, None, "home-desktop.png"),
                ("/", 390, 844, None, "home-mobile.png"),
                ("/practice-areas/", 1440, 1000, None, "practice-hub-desktop.png"),
                ("/free-case-review/", 390, 844, "#general-review", "case-review-form-mobile.png"),
                ("/landing/garden-grove-chemical-leak/", 390, 844, "#updates-status", "garden-grove-updates-mobile.png"),
                ("/privacy.html", 390, 844, "main", "privacy-mobile.png"),
            ]
            for route, width, height, selector, filename in captures:
                context = context_for(browser, width, height, reduced=False)
                page = context.new_page()
                page.goto(f"{ORIGIN}{route}", wait_until="domcontentloaded", timeout=10000)
                page.wait_for_timeout(150)
                if selector == "#updates-status":
                    page.wait_for_function(
                        "document.querySelector('#updates-status')?.dataset.feedState",
                        timeout=5000,
                    )
                if selector:
                    page.locator(selector).scroll_into_view_if_needed()
                    page.wait_for_timeout(250)
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
