# BerheLaw V2 Visual-Departure Brief

Date: 2026-07-24
User feedback: the Opus 5 release still looks the same.

## Why the first redesign failed visually

The implementation changed content, artwork, motion behavior, SEO, resources, and intake logic, but retained the prior first-screen composition:

- dark navy header above a dark navy hero;
- white serif headline in the left column;
- gold call button and outlined case-review button in one row;
- attorney review card in the right column;
- four-item proof strip immediately below the hero;
- boxed/card-like content grammar through the page.

A visitor judging the first viewport reasonably sees the same site.

## V2 direction

Build a cinematic editorial legal site, not another variation of the old split hero.

1. Full-viewport, edge-to-edge evidence-architecture visual with an intentional image entrance.
2. Oversized asymmetric headline positioned in the open image field.
3. Architectural conversion dock or rail, not two conventional buttons in a row.
4. A purposeful transition into the page, not the old four-column proof strip.
5. Sticky or pinned evidence narrative with active chapters and visible progress.
6. Practice navigation as a numbered publication index with rules and typographic hierarchy, not cards.
7. Strong dark/light section rhythm, oversized numerals, editorial pull lines, and fewer boxes.
8. Native motion only. No scroll hijacking. Content visible before JavaScript. Complete reduced-motion fallback.
9. Mobile receives its own composition and crop. Case review, phone path, and urgency note remain visible at 390 x 844; primary action remains visible at 320 x 568.

## New visual assets

- `images/evidence-architecture-hero.webp`: 1536 x 864, 93,210 bytes.
- `images/evidence-architecture-hero.jpg`: 1536 x 864, 168,293 bytes.
- `images/evidence-architecture-hero-mobile.webp`: 600 x 900, 34,978 bytes.

The asset is original GPT Image 2 editorial artwork. It depicts abstract paper planes, chronology/redaction lines, and a brass architectural channel. It contains no people, client facts, text, courthouse, gavel, scales, logo, outcome, or implied real event.

## Objective approval gates

The V2 candidate fails if any gate is not met:

1. Homepage does not render the old `.hero-grid`, `.home-attorney-card`, or immediate `.proof-band` first-screen grammar.
2. Side-by-side desktop and mobile screenshots show a structural difference, not merely new copy, color, or background.
3. The full-screen image, asymmetric headline, conversion dock, and sticky narrative are visible without explanation.
4. Motion is perceptible during normal scrolling but all information remains visible and usable with JavaScript disabled or reduced motion enabled.
5. No overflow at 320, 390, 768, 1440, or 2560 pixels.
6. Primary conversion remains visible in the first 390 x 844 viewport, with a usable primary action at 320 x 568.
7. Existing legal, identity, intake, SEO, resource, sitemap, and security contracts remain passing.
8. Independent visual review must explicitly answer: “Could a reasonable visitor mistake this for the prior split-hero design?” The required answer is no.
