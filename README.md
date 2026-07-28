# BerheLaw public site

Component-generated static site for `https://berhelaw.com`.

## Build and test

```bash
python3 scripts/build.py
python3 scripts/build.py --check
pytest -q
```

The Python standard-library builder owns every public HTML document, the sitemap, security headers, and content-hashed CSS/JS assets. Edit source under `src/`, then rebuild. Canonical routes are fixed in `src/site_data.py` and guarded by tests.

## Intake contract

All visible forms submit a native browser POST to `https://admin.berhelaw.com/api/leads/case-review`. The admin endpoint owns acceptance and renders a server-side, no-store receipt only after the request is recorded; client JavaScript and the static public site never claim success. The canonical public contract uses the deployed keys `firstName`, `lastName`, `matterType`, `phone`, `email`, `bot-field`, `summary`, and `consent`, plus `page_url`, `referrer`, and `campaign`. Specialized forms use accepted compatibility keys: `caseType` for a selected matter category, `preferred_contact`, `knownDeadline`, and `county`. Version metadata remains in `form_version` and `consent_version`.

The route also accepts legacy aliases (`first_name`, `last_name`, `matter_type` or `practice_area`, `contactMethod`, and `deadline`); new public forms should use the canonical keys above. Contract tests submit representative general and campaign forms with JavaScript disabled and assert the actual encoded POST keys.

The endpoint does not require cross-origin JavaScript because forms use native browser navigation. Production integration remains an external release gate and must verify the server-owned receipt and resulting lead with a controlled synthetic submission. `/success.html` is a neutral legacy status page and explicitly does not confirm delivery.

The Garden Grove local feed is fresh for 14 days after `lastVerifiedUtc`. After that window, or when the feed is malformed or unavailable, the page displays a prominent alert with the last verified date when available and directs visitors to the cited official City and County sources.

## Motion contract

Scroll motion is native CSS and JavaScript with no library. `site.js` adds the `motion` class to
`<html>` only when IntersectionObserver, requestAnimationFrame, and a no-preference reduced-motion
setting are all present, and that class is the only thing that hides or offsets content. Without
JavaScript, on any failure, or under `prefers-reduced-motion: reduce`, every page renders in its
finished state: reveals are visible, the case-review timeline is fully drawn, and the decorative
scroll-progress bar is hidden. Motion animates transform and opacity only, never intercepts the
scroller, and is covered by `tests/test_motion_seo_contract.py` and the WebKit motion tests.

## Content guardrails

Do not add outcomes, testimonials, ratings, awards, locations, response-time promises, specialist claims, privilege or confidentiality promises, dollar figures, em dashes, imagery, or professional facts without written provenance. Preserve the responsible-firm identity, advertising disclaimer, conflict-review language, signed-written-agreement requirement, and Garden Grove citations. `success.html` remains excluded from the sitemap and noindexed/no-store in `_headers`.
