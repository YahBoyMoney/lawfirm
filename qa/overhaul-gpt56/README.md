# BerheLaw redesign QA

Release review date: 2026-07-12

## Completed gates

- `python3 scripts/build.py` — 30 generated files rebuilt with content-hashed CSS and JavaScript.
- `python3 -m pytest -q` — 42 passed, including WebKit browser coverage and call-first homepage regression assertions.
- `PLAYWRIGHT_BROWSER=webkit python3 scripts/visual_qa.py` — passed: 48 route/viewport checks, 7 focused assertions, 6 screenshots, 0 failures.
- Full-page Chromium screenshots were inspected on desktop and mobile after the passing WebKit run.
- Canonical/sitemap parity, internal links, fingerprinted assets, image dimensions, intake form contract, no-JavaScript form behavior, consent and phone validation, CSP/headers, metadata/schema, FAQPage parity, breadcrumbs, contrast, overflow, and sticky-action clearance remain covered.

## Conversion and SEO verification

- The homepage phone CTA is visually primary and the free case-review form is secondary.
- Both hero CTAs appear in the 390 x 844 first viewport, with no sticky-action overlap.
- The synthetic multi-person hero image is no longer used on the homepage.
- The homepage uses the identified Tam Berhe portrait only at its native 200 x 200 size or smaller.
- The bar number is absent from the homepage hero and proof band, while remaining on the attorney profile.
- Homepage title, description, Open Graph metadata, California service-area schema, service types, visible FAQs, and FAQPage schema were verified.
- No testimonials, outcomes, awards, office claims, response-time promises, specialist claims, or guarantees were added.

## Current visual thresholds

- Homepage hero: 72 px desktop heading and 927.2 px bottom at 1440 x 1000, within the 104 px / 950 px gate.
- Mobile secondary hero CTA bottom: 668.1 px in an 844 px viewport.
- All checked pages report one H1, HTTP 200, no horizontal overflow, and no console/page errors.
