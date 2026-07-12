# Overhaul QA

Release review date: 2026-07-11

## Completed gates

- `python3 -m pytest -q` — 41 passed (3 security, 17 contract, and 21 Playwright WebKit E2E cases), including JavaScript-enabled and no-JavaScript paths.
- `python3 scripts/build.py --check` — 30 generated files current.
- `PLAYWRIGHT_BROWSER=webkit python3 scripts/visual_qa.py` — passed with WebKit 26.4: 48 canonical route/viewport checks, 8 focused assertions, 6 screenshots, 0 failures.
- `python3 -m py_compile scripts/build.py scripts/visual_qa.py src/site_data.py` — passed.
- `git diff --check` — passed.
- Canonical/sitemap parity, internal links, referenced assets, image signatures and dimensions, production-compatible native POST forms, JavaScript-disabled submission, failure handling, phone and consent validation, Garden Grove feed states, CSP/headers, accessibility markers, metadata/schema, breadcrumb parity, contrast, and deterministic output are covered by the automated suite.

## Visual gate

The WebKit gate crawls every canonical route at desktop and mobile sizes, checks the focused-form sticky-bar contract and persistent mobile clearance, verifies explicit homepage and practice-hub hero sizing/crop markers, and writes `visual-qa-report.json` plus six representative screenshots to this directory.

Current report: passed. Desktop hero thresholds remain 820px for the homepage and 870px for the practice hub. Representative desktop/mobile screenshots were visually inspected after the passing run, including homepage, practice hub, case-review form, Garden Grove stale-feed alert, and privacy page. No release-blocking clipping, overflow, sticky-action overlap, or hierarchy defects were observed.

## External release gates

- Run one controlled synthetic staging submission to verify the server-owned post-insert receipt and resulting lead record.
- Complete attorney review of advertising, privacy, and incident-response copy before production publication.
