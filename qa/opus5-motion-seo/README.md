# BerheLaw Opus 5 motion, conversion, and SEO release QA

Release review date: 2026-07-24
Branch: `redesign/opus5-motion-seo`

## Implementation

- Claude Opus 5 completed the principal redesign implementation in an isolated worktree.
- The homepage now uses a restrained native CSS/JavaScript scroll-motion system, case-review timeline, call-first conversion hierarchy, attorney-led trust surface, and progressive enhancement.
- Motion fails open without JavaScript and is disabled under `prefers-reduced-motion: reduce`.
- Primary call and case-review actions are visible in the first mobile viewport.
- Three new substantive client resources cover first steps after a collision, insurer communications, and workplace documentation.
- Practice pages include problem-specific stakes, evidence, evaluation, FAQ, related-resource, and matter-prefilled intake paths.
- Article, FAQ, breadcrumb, LegalService, canonical, Open Graph, sitemap, and internal-link contracts are regression tested.

## Image and identity safeguards

- The visible hero artwork is an original non-figurative GPT Image 2 asset. It contains no people, attorneys, clients, courthouse, gavel, scales, outcome, testimonial, or implied real event.
- A 69 KB responsive mobile crop prevents the desktop asset from being transferred on small screens.
- All synthetic team/personnel files were removed from the repository.
- The only visible person is the authentic Tam Berhe portrait, used at its native 200 x 200 size or smaller.
- Responsible firm disclosure and firm schema identify **The Berhe Law Firm, APC**. The DBA and attorney-advertising disclosures remain visible.

## Verification results

- `python3 scripts/build.py --check`: **33 generated files current**.
- `python3 -m pytest -q`: **77 passed**.
- `PLAYWRIGHT_BROWSER=webkit python3 scripts/visual_qa.py`: **passed**, 27 routes at five viewport classes, 135 route/viewport checks, 11 focused assertions, 16 screenshots, zero failures.
- Visual inspection covered desktop and mobile hero, case-review timeline, evidence-preservation section, practice-area stakes, resource hub, and a full mobile resource guide.
- The independent visual gate found and corrected one collapsed practice-page callout before release.
- Independent legal-marketing and code review found and corrected synthetic imagery, entity schema, categorical guide wording, unsupported absolutes, intake-context loss, Article schema, motion fallback, and small-mobile overflow issues.
- Final independent release review: **PASS**, no P0/P1 blocker.
- `git diff --check` and Python compilation: **passed**.

## Lighthouse mobile

- Performance: **95**
- Accessibility: **100**
- Best Practices: **100**
- SEO: **100**
- First Contentful Paint: **1.2 s**
- Largest Contentful Paint: **2.9 s**
- Cumulative Layout Shift: **0**
- Total Blocking Time: **0 ms**
- Speed Index: **1.3 s**

The site self-hosts licensed Fraunces and Inter WOFF2 files under their included OFL licenses. `font-display: optional`, font preloads, and the responsive hero crop eliminate layout shift and external font render-blocking.

## Legal-marketing guardrails

- No testimonials, case outcomes, recovered-dollar figures, rankings, awards, specialist claims, guarantees, response-time promises, or fabricated credentials were added.
- Resource guides expressly remain general information, do not calculate deadlines, and do not create an attorney-client relationship.
- Fact-dependent language replaced categorical legal and medical directives.
- Public form endpoint, canonical field contract, consent language, conflict warning, and native no-JavaScript submission behavior remain intact.
