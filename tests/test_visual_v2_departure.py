"""Rejection tests for the V2 visual departure.

The previous release was rejected because the first screen was inherited: a dark
navy bar over a dark navy split hero, a right-side attorney card, a gold and
outline button pair, and a four-column proof strip. Blurred grayscale structural
similarity against the pre-release screenshots was 0.796 desktop and 0.942 mobile.

These tests fail the build if any of that composition comes back, and they measure
the candidate against the same screenshots with the same method.
"""
import json
import re
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from structural_similarity import compare, dark_pixel_share  # noqa: E402

HOME = BeautifulSoup((ROOT / "index.html").read_text(encoding="utf-8"), "html.parser")
HOME_MARKUP = (ROOT / "index.html").read_text(encoding="utf-8")
CSS_SOURCE = (ROOT / "src/assets/site.css").read_text(encoding="utf-8")
QA = ROOT / "qa" / "visual-v2"

SSIM_CEILING = 0.55
DARK_PIXEL_CEILING = 0.55
EXPOSED_ART_FLOOR = 0.30

# Every structure the audit told us to remove or recompose.
REJECTED_CLASSES = (
    "hero-grid", "home-hero", "home-hero-inner", "home-hero-copy", "home-hero-lead",
    "home-hero-actions", "home-hero-urgency", "home-hero-art", "home-attorney-card",
    "proof-band", "home-practice-grid", "home-practice-card", "home-practice-number",
    "home-urgency", "home-urgency-grid", "home-reasons", "home-advocate", "home-advocate-grid",
    "home-portrait", "preserve-grid", "preserve-card", "home-inline-cta", "home-form-call",
    "button-call", "button-call-wide", "button-secondary-light", "case-step-dot",
    "home-stakes", "home-section-heading",
)


def test_no_rejected_homepage_class_survives_in_the_markup():
    present = [name for name in REJECTED_CLASSES if f'"{name}' in HOME_MARKUP or f' {name}"' in HOME_MARKUP]
    assert present == [], present
    for name in REJECTED_CLASSES:
        assert not HOME.select(f".{name}"), name


def test_no_rejected_first_screen_ladder_or_split():
    opening = HOME.select_one("section.opening[data-hero][data-opening]")
    assert opening
    # no split columns, no side card, no image inside the type field
    assert not opening.select("aside")
    assert not opening.select(".opening-field img")
    assert not opening.select("[class*=card]")
    # the old ladder was eyebrow, headline, lead, two buttons, disclaimer, attorney card
    assert not opening.select(".eyebrow")
    assert len(opening.select("a")) == 2, [a.get("class") for a in opening.select("a")]
    dock = opening.select_one(".opening-dock-band .opening-dock")
    call, review = dock.select("a")
    assert call["href"] == "tel:+19096096685" and "call-bar" in call["class"]
    assert review["href"] == "/free-case-review/" and "dock-link" in review["class"]
    assert "button" not in " ".join(review["class"])
    # a ruled four-question docket replaces the old marketing proof strip
    following = [tag.get("class") for tag in opening.find_next_siblings(class_=True)]
    assert following[0] == ["band", "docket"], following[:1]
    docket = HOME.select_one("#first-review-docket")
    assert docket
    assert len(docket.select(".docket-question")) == 4
    assert [heading.get_text(" ", strip=True) for heading in docket.select(".docket-question h3")] == [
        "Who is involved?", "What date matters?", "What proof still exists?",
        "What harm changed life, work, or property?",
    ]


def test_new_record_chapters_are_all_present_and_in_order():
    sections = [tag.get("id") for tag in HOME.select("main > section")]
    assert sections == [
        "opening-statement", "first-review-docket", "case-index", "clock", "how-review-works",
        "preserve", "counsel", "questions", "start-with-the-facts",
    ], sections
    assert len(HOME.select(".case-index .index-rows > .index-row")) == 7
    assert len(HOME.select("[data-clock] [data-clock-step]")) == 3
    assert HOME.select_one("[data-clock] .clock-meter-fill")
    assert len(HOME.select("[data-timeline] .case-step")) == 5
    assert len(HOME.select("[data-timeline] .case-step-number")) == 5
    assert len(HOME.select(".preserve .preserve-bands > .preserve-band")) == 4
    assert HOME.select_one(".counsel .counsel-portrait img")["width"] == "200"
    assert HOME.select_one(".intake-field .call-first")
    assert HOME.select_one(".opening-plate img")["src"] == "/images/evidence-architecture-hero.jpg"
    assert len(HOME.select(".home-faq article.record-question")) == 8
    assert not HOME.select(".home-faq details")
    # oversized folio numbering runs through the record
    folios = [tag.get_text(" ", strip=True) for tag in HOME.select("main .folio")]
    assert sum(folio.lower().startswith("section 0") for folio in folios) == 8


def test_case_index_rows_keep_every_practice_destination_and_label():
    sys.path.insert(0, str(ROOT / "src"))
    from site_data import PRACTICES

    rows = HOME.select(".case-index .index-row")
    assert len(rows) == len(PRACTICES)
    for index, (row, practice) in enumerate(zip(rows, PRACTICES), 1):
        link = row.select_one("a.index-row-link")
        assert link["href"] == f'/practice-areas/{practice["slug"]}/'
        assert row.select_one(".index-row-number").get_text(strip=True) == f"{index:02d}"
        assert row.select_one(".index-row-title").get_text(strip=True) == practice["name"]
        assert row.select_one(".index-row-copy").get_text(strip=True) == practice["card"]
        assert row.select_one(".index-row-mark").get_text(strip=True) == "How this review works"


def test_headline_typography_leaves_the_rejected_display_face():
    assert "Fraunces" not in CSS_SOURCE
    assert "Georgia" not in CSS_SOURCE
    display = re.search(r"--display:([^;]+);", CSS_SOURCE)
    assert display and display.group(1).startswith("Newsreader")
    assert "Georgia" not in display.group(1)
    headline = HOME.select_one(".opening-headline")
    lines = [tag.get_text(strip=True) for tag in headline.select(".mask-line")]
    assert lines == [
        "Something serious happened.", "What you do next", "can shape", "what you can prove.",
    ]
    # the approved H1 copy is unchanged, only its silhouette is
    assert headline.get_text(" ", strip=True) == (
        "Something serious happened. What you do next can shape what you can prove."
    )
    assert "mask-line--marked" in headline.select(".mask-line")[-1]["class"]
    assert ".opening-headline .mask--i2{padding-left:14%}" in CSS_SOURCE


def test_shape_language_has_no_glass_gradients_or_floating_cards():
    banned = ("backdrop-filter", "linear-gradient", "radial-gradient", "border-radius:50%", "border-radius:4px")
    for token in banned:
        assert token not in CSS_SOURCE, token
    # square corners everywhere
    assert "--radius:0" in CSS_SOURCE
    radii = set(re.findall(r"border-radius:([^;}]+)", CSS_SOURCE))
    assert radii <= {"0"}, radii
    # the only elevation left is the mobile menu sheet
    shadows = re.findall(r"box-shadow:([^;}]+)", CSS_SOURCE)
    assert shadows == ["0 18px 40px rgba(18,24,22,.18)"], shadows


def test_footer_is_paper_with_a_thick_oxblood_top_rule():
    footer = re.search(r"\.site-footer\{([^}]+)\}", CSS_SOURCE)
    assert footer
    declarations = footer.group(1)
    assert "background:var(--paper)" in declarations
    assert "border-top:10px solid var(--oxblood)" in declarations
    assert HOME.select_one('footer.site-footer img[src="/images/berhe-jones-llp-logo.png"]')


# --- measured gates ---------------------------------------------------------

BASELINES = {
    "home-hero-1440.png": ("qa/opus5-motion-seo/home-hero-1440.png", "qa/overhaul-gpt56/home-desktop.png"),
    "home-hero-390.png": ("qa/opus5-motion-seo/home-hero-390.png", "qa/overhaul-gpt56/home-mobile.png"),
}


def require_capture(name):
    path = QA / name
    if not path.is_file():
        pytest.skip(f"{path.relative_to(ROOT)} missing: run scripts/visual_qa.py first")
    return path


@pytest.mark.parametrize(
    ("candidate", "baseline"),
    [(candidate, baseline) for candidate, baselines in BASELINES.items() for baseline in baselines],
)
def test_blurred_structural_similarity_clears_the_departure_gate(candidate, baseline):
    """Grayscale plus 24px Gaussian blur, then SSIM. The rejected release scored 0.796 and 0.942."""
    score = compare(require_capture(candidate), ROOT / baseline)
    assert score <= SSIM_CEILING, f"{candidate} vs {baseline} scored {score:.4f}"


def test_the_measurement_still_reproduces_the_rejected_scores():
    """Guards the gate itself: the same method must still flag the release that was rejected."""
    desktop = compare(ROOT / "qa/opus5-motion-seo/home-hero-1440.png", ROOT / "qa/overhaul-gpt56/home-desktop.png")
    mobile = compare(ROOT / "qa/opus5-motion-seo/home-hero-390.png", ROOT / "qa/overhaul-gpt56/home-mobile.png")
    assert desktop > SSIM_CEILING and mobile > SSIM_CEILING
    assert desktop > 0.7 and mobile > 0.9


@pytest.mark.parametrize("capture", ["home-hero-1440.png", "home-hero-390.png", "home-hero-320x568.png"])
def test_first_viewport_is_not_another_dark_field(capture):
    """Exposed art of at least 30 percent, or no more than 55 percent dark pixels."""
    path = require_capture(capture)
    dark = dark_pixel_share(path)
    art = exposed_art_share(capture)
    assert dark <= DARK_PIXEL_CEILING or art >= EXPOSED_ART_FLOOR, {"dark": dark, "art": art}
    assert dark <= DARK_PIXEL_CEILING, f"{capture} is {dark:.1%} dark"


def exposed_art_share(capture):
    report = QA / "visual-qa-report.json"
    if not report.is_file():
        return 0.0
    data = json.loads(report.read_text(encoding="utf-8"))
    size = capture.removeprefix("home-hero-").removesuffix(".png")
    width = size.split("x")[0]
    for assertion in data.get("assertions", []):
        if assertion["name"].startswith(f"first {width}x") and "artShare" in assertion.get("details", {}):
            return float(assertion["details"]["artShare"])
    return 0.0


def test_visual_qa_report_covers_the_deep_scroll_stages():
    report = QA / "visual-qa-report.json"
    if not report.is_file():
        pytest.skip("run scripts/visual_qa.py first")
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["passed"], data["failures"]
    captured = {Path(name).name for name in data["screenshots"]}
    expected = {
        "home-hero-1440.png", "home-hero-390.png", "home-hero-320x568.png", "home-hero-320.png",
        "home-hero-768.png", "home-hero-2560.png", "home-plate-1440.png",
        "home-docket-1440.png", "home-docket-390.png",
        "home-case-index-1440.png", "home-case-index-390.png", "home-clock-1440.png",
        "home-clock-390.png", "home-case-timeline-1440.png", "home-case-timeline-390.png",
        "home-preserve-1440.png", "home-counsel-1440.png", "home-questions-1440.png",
        "home-intake-1440.png", "home-intake-390.png", "home-footer-1440.png", "home-menu-390.png",
    }
    assert expected <= captured, sorted(expected - captured)
    assert not [item for item in data["routes"] if item["overflow"]]
    assert not [item for item in data["routes"] if item["consoleErrors"] or item["pageErrors"]]
