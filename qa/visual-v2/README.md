# BerheLaw Visual V2 QA

Review date: 2026-07-24
Branch: `redesign/visual-departure-v2`
Direction: **The Record**

## Why V2 exists

The first Opus release improved content, SEO, resources, intake behavior, performance, and motion, but retained the old first-screen composition. Independent measurement found blurred grayscale structural similarity of 0.796 desktop and 0.942 mobile. The user correctly rejected it as looking the same.

V2 removes the inherited dark split hero, right-side attorney card, gold and outline CTA pair, and four-column proof strip. It replaces them with a paper, ink, and oxblood editorial system, a full-screen Opening Statement, exposed evidence-architecture artwork, a conversion rail, a two-by-two First Review Docket, a seven-row Case Index, sticky Clock chapters, Five Chapters process storytelling, broad preservation bands, a later counsel chapter, and an unboxed intake surface.

## Objective visual-departure results

Required structural-similarity ceiling: **0.55** using grayscale screenshots, 24px Gaussian blur, and SSIM.

- V2 desktop vs rejected Opus desktop: **0.3679**
- V2 desktop vs pre-Opus desktop: **0.4368**
- V2 mobile vs rejected Opus mobile: **0.4832**
- V2 mobile vs pre-Opus mobile: **0.4174**

For comparison, the rejected release measured 0.7764 desktop and 0.9355 mobile using the same local implementation.

First-viewport dark-pixel share:

- Desktop: **21.09%**
- Mobile 390 x 844: **4.89%**
- Mobile 320 x 568: **2.90%**

## Verification

- Deterministic static build: **33 generated files current**
- Pytest: **108 passed**
- WebKit visual QA: **162 route checks, 14 focused assertions, 30 screenshots, zero failures**
- Python compilation: passed
- `git diff --check`: passed
- Independent final blocker review: **PASS**
- No horizontal overflow at 320, 390, 768, 1440, or 2560 widths
- Primary phone action fully visible at 320 x 568
- Phone and free-review routes visible at 390 x 844
- JavaScript-disabled and reduced-motion states keep content visible, chapters in document flow, and motion indicators disabled

## Lighthouse mobile

- Performance: **93**
- Accessibility: **100**
- Best Practices: **100**
- SEO: **100**
- First Contentful Paint: **1.1 s**
- Largest Contentful Paint: **3.2 s**
- Cumulative Layout Shift: **0.059**
- Total Blocking Time: **0 ms**
- Speed Index: **1.1 s**

## Asset safeguards

- New GPT Image 2 evidence-architecture artwork is abstract and non-deceptive. It contains no people, attorneys, clients, case facts, readable text, courthouse, gavel, scales, outcome, or implied real event.
- Separate 1536 x 864 desktop WebP/JPEG and 600 x 900 mobile WebP assets are provided.
- Newsreader, IBM Plex Sans, and IBM Plex Mono are self-hosted under included SIL Open Font License files.
- The only person shown is the authentic 200 x 200 Tam Berhe portrait, displayed at a modest square size.

## Preserved contracts

All routes, approved legal-resource content, Article/FAQ/LegalService schema, canonical metadata, sitemap parity, responsible APC entity, DBA disclosure, intake endpoint and exact fields, conflict warning, no-attorney-client disclaimer, incident citations, security headers, and noindex/no-store behavior remain regression-tested.
