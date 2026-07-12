#!/usr/bin/env python3
import argparse
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from site_data import DBA, DISCLAIMER, GARDEN_SOURCES, PHONE_DISPLAY, PHONE_HREF, PRACTICES, ROUTES

ADMIN_ACTION = "https://admin.berhelaw.com/api/leads/case-review"
RELEASE_DATE = "2026-07-11"
outputs = {}


def esc(value):
    return html.escape(str(value), quote=True)


def route_path(route):
    if route == "/":
        return ROOT / "index.html"
    if route.endswith("/"):
        return ROOT / route.lstrip("/") / "index.html"
    return ROOT / route.lstrip("/")


def asset(source_name, output_prefix):
    content = (ROOT / "src" / "assets" / source_name).read_text(encoding="utf-8")
    digest = hashlib.sha256(content.encode()).hexdigest()[:12]
    filename = f"{output_prefix}.{digest}.{source_name.rsplit('.', 1)[1]}"
    outputs[ROOT / "assets" / source_name.rsplit('.', 1)[1] / filename] = content
    return f"/assets/{source_name.rsplit('.', 1)[1]}/{filename}"


CSS = asset("site.css", "site")
SITE_JS = asset("site.js", "site")
INTAKE_JS = asset("intake.js", "intake")


NAV = [
    ("Practice areas", "/practice-areas/"), ("Attorney", "/attorney-tam-berhe/"),
    ("Process", "/case-review-process/"), ("Resources", "/resources/"),
    ("Referrals", "/referrals-co-counsel/"), ("Case review", "/free-case-review/"),
]


def active(route, href):
    if href == "/practice-areas/" and route.startswith("/practice-areas/"):
        return True
    return route == href


def header(route):
    links = "".join(
        f'<li><a href="{href}"' + (' aria-current="page"' if active(route, href) else '') + f'>{label}</a></li>'
        for label, href in NAV
    )
    return f'''<a class="skip-link" href="#main">Skip to main content</a>
<header class="site-header"><div class="header-inner">
  <a class="brand" href="/" aria-label="Berhe Jones LLP home"{' aria-current="page"' if route == '/' else ''}><img class="brand-logo" src="/images/berhe-jones-llp-logo-reverse.png" alt="Berhe Jones LLP" width="1305" height="308" decoding="async"></a>
  <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-navigation" aria-label="Open menu">Menu</button>
  <nav class="site-nav" id="site-navigation" aria-label="Primary navigation" data-open="false"><ul>{links}</ul></nav>
  <a class="header-call" href="{PHONE_HREF}" aria-label="Call Berhe Jones LLP at {PHONE_DISPLAY}">{PHONE_DISPLAY}</a>
</div></header>'''


def footer():
    practices = "".join(f'<li><a href="/practice-areas/{p["slug"]}/">{esc(p["name"])}</a></li>' for p in PRACTICES)
    return f'''<footer class="site-footer"><div class="footer-grid">
  <div><a class="brand" href="/" aria-label="Berhe Jones LLP home"><img class="brand-logo" src="/images/berhe-jones-llp-logo-reverse.png" alt="Berhe Jones LLP" width="1305" height="308" decoding="async"></a><p>{DBA}</p><p>Attorney-supervised screening for serious California civil matters.</p><p><a href="{PHONE_HREF}" aria-label="Call Berhe Jones LLP at {PHONE_DISPLAY}">{PHONE_DISPLAY}</a></p></div>
  <div><h2 class="eyebrow">Practice areas</h2><ul>{practices}<li><a href="/landing/truck-fleet-rideshare-accident-california/">Commercial vehicle matters</a></li></ul></div>
  <div><h2 class="eyebrow">Firm and resources</h2><ul><li><a href="/attorney-tam-berhe/">Tam Berhe</a></li><li><a href="/case-review-process/">Case review process</a></li><li><a href="/resources/">Resource library</a></li><li><a href="/living-trust/">Living trust planning</a></li><li><a href="/privacy.html">Privacy</a></li><li><a href="/disclaimer.html">Disclaimer</a></li><li><a href="/terms.html">Terms</a></li></ul></div>
</div><p class="legal-note">{DISCLAIMER}</p></footer>
<div class="mobile-actions" aria-label="Contact options"><a href="{PHONE_HREF}" aria-label="Call Berhe Jones LLP at {PHONE_DISPLAY}">Call now</a><a href="/free-case-review/">Case review</a></div>'''


def visible_breadcrumbs(body, route):
    match = re.search(r'<nav class="breadcrumbs"[^>]*><ol>(.*?)</ol></nav>', body)
    if not match:
        return []
    items = []
    for item in re.findall(r"<li>(.*?)</li>", match.group(1)):
        link = re.search(r'<a href="([^"]+)">(.*?)</a>', item)
        if link:
            items.append((html.unescape(re.sub(r"<[^>]+>", "", link.group(2))), html.unescape(link.group(1))))
        else:
            items.append((html.unescape(re.sub(r"<[^>]+>", "", item)), route))
    return items


def schema(route, title, description, body, kind="WebPage"):
    page = {
        "@context": "https://schema.org", "@type": kind,
        "@id": f"https://berhelaw.com{route}#page", "url": f"https://berhelaw.com{route}",
        "name": title, "description": description,
        "publisher": {"@id": "https://berhelaw.com/#firm"},
        "isPartOf": {"@id": "https://berhelaw.com/#website"},
    }
    if route == "/":
        faq_entities = [
            {"@type": "Question", "name": html.unescape(re.sub(r"<[^>]+>", "", question)), "acceptedAnswer": {"@type": "Answer", "text": html.unescape(re.sub(r"<[^>]+>", "", answer))}}
            for question, answer in re.findall(r'<details class="faq-item"><summary>(.*?)</summary><p>(.*?)</p></details>', body)
        ]
        firm = {
            "@type": "LegalService", "@id": "https://berhelaw.com/#firm", "name": "Berhe Jones LLP",
            "alternateName": "The Berhe Law Firm", "url": "https://berhelaw.com/", "telephone": "+1-909-609-6685",
            "image": "https://berhelaw.com/images/og-berhe-jones-llp.png", "areaServed": {"@type": "State", "name": "California"},
            "serviceType": ["Personal injury law", "Wrongful death law", "Employment law", "Civil rights law", "Consumer protection law", "Insurance bad faith litigation"],
        }
        graph = [
            {"@type": "WebSite", "@id": "https://berhelaw.com/#website", "url": "https://berhelaw.com/", "name": "Berhe Jones LLP"},
            firm,
            page,
        ]
        if faq_entities:
            graph.append({"@type": "FAQPage", "@id": "https://berhelaw.com/#frequently-asked-questions", "mainEntity": faq_entities})
        return json.dumps({"@context": "https://schema.org", "@graph": graph}, separators=(",", ":"))
    graph = [
        page,
        {"@type": "LegalService", "@id": "https://berhelaw.com/#firm", "name": "Berhe Jones LLP", "alternateName": "The Berhe Law Firm", "url": "https://berhelaw.com/", "telephone": "+1-909-609-6685"},
    ]
    breadcrumb_items = visible_breadcrumbs(body, route)
    if breadcrumb_items:
        graph.append({"@type": "BreadcrumbList", "@id": f"https://berhelaw.com{route}#breadcrumbs", "itemListElement": [
            {"@type": "ListItem", "position": position, "name": name, "item": f"https://berhelaw.com{href}"}
            for position, (name, href) in enumerate(breadcrumb_items, 1)
        ]})
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, separators=(",", ":"))


def document(route, title, description, body, *, robots="index, follow", kind="WebPage"):
    return f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="BerheLaw static builder"><meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="robots" content="{robots}"><title>{esc(title)}</title><meta name="description" content="{esc(description)}">
<link rel="canonical" href="https://berhelaw.com{route}"><link rel="icon" href="/favicon.ico"><meta name="theme-color" content="#0b151d">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&amp;family=Inter:wght@400;500;600;700&amp;display=swap" referrerpolicy="no-referrer">
<link rel="stylesheet" href="{CSS}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="https://berhelaw.com{route}"><meta property="og:type" content="website"><meta property="og:site_name" content="Berhe Jones LLP"><meta property="og:locale" content="en_US"><meta property="og:image" content="https://berhelaw.com/images/og-berhe-jones-llp.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="Berhe Jones LLP branded social preview image for California legal services."><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(description)}"><meta name="twitter:image" content="https://berhelaw.com/images/og-berhe-jones-llp.png"><meta name="twitter:image:alt" content="Berhe Jones LLP branded social preview image for California legal services.">
<script type="application/ld+json">{schema(route, title, description, body, kind)}</script>
</head><body id="top">{header(route)}{body}{footer()}<script src="{SITE_JS}" defer></script><script src="{INTAKE_JS}" defer></script></body></html>'''


def breadcrumbs(items):
    all_items = [("Home", "/"), *items]
    rendered = "".join(
        f'<li><a href="{esc(href)}">{esc(label)}</a></li>' if index < len(all_items) - 1 else f'<li>{esc(label)}</li>'
        for index, (label, href) in enumerate(all_items)
    )
    return f'<nav class="breadcrumbs" aria-label="Breadcrumb"><ol>{rendered}</ol></nav>'


def picture(name="hero", alt="Berhe Jones LLP team in a professional office setting"):
    if name == "fit":
        return '<picture><source srcset="/images/case-fit-team.webp" type="image/webp"><img src="/images/case-fit-team.jpg" alt="Berhe Jones LLP team working together" width="960" height="720" decoding="async" fetchpriority="high"></picture>'
    return '<picture><source media="(max-width:600px)" srcset="/images/berhe-jones-hero-team-mobile.webp" type="image/webp"><source srcset="/images/berhe-jones-hero-team.webp" type="image/webp"><source media="(max-width:600px)" srcset="/images/berhe-jones-hero-team-mobile.jpg"><img src="/images/berhe-jones-hero-team.jpg" alt="'+esc(alt)+'" width="1280" height="720" decoding="async" fetchpriority="high"></picture>'


def hero(h1, lead, eyebrow="California civil counsel", image="hero", primary="Request a case review", primary_href="/free-case-review/", marker=""):
    classes = "hero" + (f" hero--{marker}" if marker else "") + (" hero--fit-image" if image == "fit" else "")
    return f'''<section class="{classes}"><div class="hero-grid"><div class="hero-copy"><span class="eyebrow">{esc(eyebrow)}</span><h1>{esc(h1)}</h1><p class="lead">{esc(lead)}</p><div class="actions"><a class="button button-primary" href="{primary_href}">{esc(primary)}</a><a class="button button-secondary" href="{PHONE_HREF}" aria-label="Call Berhe Jones LLP at {PHONE_DISPLAY}">Call {PHONE_DISPLAY}</a></div></div><div class="hero-media">{picture(image)}</div></div></section>'''


def proof_band():
    return f'''<aside class="proof-band" aria-label="Firm review facts"><div class="inner"><span><strong>Free first review</strong>No fee to tell us what happened</span><span><strong>Attorney-led</strong>Serious matters reviewed by counsel</span><span><strong>California matters</strong>Injury, work, rights, insurance, consumer</span><span><strong>Talk to the firm</strong><a href="{PHONE_HREF}" aria-label="Call Berhe Jones LLP at {PHONE_DISPLAY}">{PHONE_DISPLAY}</a></span></div></aside>'''


def editorial(items):
    return '<div class="editorial-list">' + ''.join(f'<article class="editorial-item"><h3>{esc(title)}</h3><div><p>{esc(text)}</p>{f"<a href={esc(href)!r}>Read more</a>" if href else ""}</div></article>' for title, text, href in items) + '</div>'


def intake_form(form_id="case-review", matter="General civil matter", campaign="general", heading="Case review request", extra="", source_route="/"):
    return rf'''<form class="intake-form" id="{form_id}" name="{form_id}" data-intake-form action="{ADMIN_ACTION}" method="post" accept-charset="UTF-8" aria-labelledby="{form_id}-heading" aria-describedby="{form_id}-notice">
<h2 id="{form_id}-heading">{esc(heading)}</h2><p id="{form_id}-notice" class="notice">Do not send privileged, highly sensitive, or urgent information here. If timing may matter, call {PHONE_DISPLAY}.</p>
<input type="hidden" name="form_version" value="2026-07-11.2"><input type="hidden" name="consent_version" value="2026-07-11"><input type="hidden" name="matterType" value="{esc(matter)}"><input type="hidden" name="page_url" value="https://berhelaw.com{esc(source_route)}"><input type="hidden" name="referrer" value=""><input type="hidden" name="campaign" value="{esc(campaign)}">
<div class="honeypot" aria-hidden="true"><label>Leave this field blank <input type="text" name="bot-field" tabindex="-1" autocomplete="off" aria-hidden="true"></label></div>
<div class="field-grid"><div class="field"><label for="{form_id}-first">First name</label><input type="text" id="{form_id}-first" name="firstName" autocomplete="given-name" autocapitalize="words" enterkeyhint="next" required aria-required="true"></div><div class="field"><label for="{form_id}-last">Last name</label><input type="text" id="{form_id}-last" name="lastName" autocomplete="family-name" autocapitalize="words" enterkeyhint="next" required aria-required="true"></div></div>
<div class="field-grid"><div class="field"><label for="{form_id}-phone">Phone</label><input id="{form_id}-phone" name="phone" type="tel" autocomplete="tel" inputmode="tel" enterkeyhint="next" minlength="7" maxlength="25" pattern="\+?[0-9](?:(?:\s|\.|\(|\)|-)*[0-9]){{6,14}}" title="Enter a phone number with 7 to 15 digits" required aria-required="true" aria-describedby="{form_id}-phone-error"><p class="field-error" id="{form_id}-phone-error" data-phone-error aria-live="polite"></p></div><div class="field"><label for="{form_id}-email">Email</label><input id="{form_id}-email" name="email" type="email" autocomplete="email" inputmode="email" enterkeyhint="next" required aria-required="true"></div></div>
{extra}<div class="field"><label for="{form_id}-summary">Short, conflict-safe summary</label><textarea id="{form_id}-summary" name="summary" autocapitalize="sentences" enterkeyhint="done" required aria-required="true" aria-describedby="{form_id}-notice"></textarea></div>
<label class="consent"><input type="checkbox" name="consent" value="yes" required aria-required="true"><span>I confirm this information is mine to share. I understand submission does not create an attorney-client relationship and representation begins only after conflicts review and a signed written agreement.</span></label>
<button class="button button-primary" type="submit">Send request</button><p class="form-status" data-form-status role="status" aria-live="polite" tabindex="-1"></p></form>'''


def homepage():
    practice_cards = "".join(
        f'''<article class="home-practice-card"><span class="home-practice-number">{index:02d}</span><h3><a href="/practice-areas/{p["slug"]}/">{esc(p["name"])}</a></h3><p>{esc(p["lead"])}</p><a class="text-link" href="/practice-areas/{p["slug"]}/">See how we review these cases <span aria-hidden="true">→</span></a></article>'''
        for index, p in enumerate(PRACTICES, 1)
    )
    faqs = [
        ("How much does it cost to call about my case?", "There is no fee to tell the firm what happened and request an initial case review. If representation is offered, fees, costs, and scope are explained in a written agreement before representation begins."),
        ("What kinds of cases does Berhe Jones LLP review?", "The firm reviews serious California personal injury and wrongful death, employment, civil rights, consumer and Lemon Law, insurance bad faith, catastrophic injury, and select civil litigation matters."),
        ("Why should I call instead of waiting?", "Some claims involve short notice periods, filing deadlines, disappearing video, changing accident scenes, unavailable witnesses, or records that can be overwritten. A prompt call helps identify whether timing or preservation needs immediate attention."),
        ("What should I have ready when I call?", "Be ready to identify the people and organizations involved, key dates, what happened, the harm or loss, any treatment or written notices, and any deadline you know about. You do not need to organize the entire file before calling."),
        ("Does a call or form submission make the firm my lawyer?", "No. Contact does not create an attorney-client relationship. Representation begins only after conflicts review and a signed written agreement."),
    ]
    faq_html = "".join(f'<details class="faq-item"><summary>{esc(question)}</summary><p>{esc(answer)}</p></details>' for question, answer in faqs)
    body = f'''<main id="main">
<section class="home-hero"><div class="home-hero-inner"><div class="home-hero-copy"><span class="eyebrow">California civil law firm</span><h1>When something serious has happened, your next move matters.</h1><p class="home-hero-lead">Injured. Wrongfully terminated. Denied by an insurer. Harmed by misconduct. Berhe Jones LLP helps Californians take the first step toward answers, accountability, and a practical path forward.</p><div class="home-hero-actions"><a class="button button-call" href="{PHONE_HREF}" aria-label="Call Berhe Jones LLP now at {PHONE_DISPLAY}"><span>Call now</span><strong>{PHONE_DISPLAY}</strong></a><a class="button button-secondary-light" href="/free-case-review/">Start a free case review</a></div><p class="home-hero-urgency"><strong>Deadlines and evidence do not wait.</strong> If the matter is urgent, call now. A call does not create an attorney-client relationship.</p></div><aside class="home-attorney-card" aria-label="Attorney-led case review"><img src="/images/tam-berhe.jpg" alt="Tam Berhe, California attorney" width="200" height="200" decoding="async"><div><span class="eyebrow">Attorney-led review</span><h2>Tell us what happened.</h2><p>Start with the event, the people or organizations involved, the harm, and any deadline. You do not need every document before you call.</p><a class="text-link text-link-light" href="/attorney-tam-berhe/">Meet Tam Berhe <span aria-hidden="true">→</span></a></div></aside></div></section>
{proof_band()}
<section class="section home-stakes"><div class="section-inner"><div class="home-section-heading"><div><span class="eyebrow">Serious problems. Focused legal review.</span><h2>When the stakes are high, start here.</h2></div><p>People usually call because something has already changed their health, work, family, finances, or freedom. Choose the issue closest to yours, or call if you are not sure where it fits.</p></div><div class="home-practice-grid">{practice_cards}</div><div class="home-inline-cta"><p><strong>Not sure which category fits?</strong> Tell us what happened. The first conversation starts with your facts, not a legal label.</p><a class="button button-primary" href="{PHONE_HREF}">Call {PHONE_DISPLAY}</a></div></div></section>
<section class="home-urgency"><div class="section-inner home-urgency-grid"><div><span class="eyebrow">Why call now</span><h2>The facts can stay the same while your options get smaller.</h2></div><div class="home-reasons"><article><strong>Deadlines can be short</strong><p>Government claims, agency matters, insurance notices, and court deadlines may require action sooner than expected.</p></article><article><strong>Evidence can disappear</strong><p>Video can be overwritten. Vehicles can be repaired. Scenes change. Witnesses become harder to locate.</p></article><article><strong>Early choices matter</strong><p>Recorded statements, releases, workplace responses, and insurer communications can affect what happens next.</p></article><a class="button button-call button-call-wide" href="{PHONE_HREF}" aria-label="Call Berhe Jones LLP now at {PHONE_DISPLAY}"><span>Talk to the firm</span><strong>{PHONE_DISPLAY}</strong></a></div></div></section>
<section class="section home-advocate"><div class="section-inner home-advocate-grid"><div class="home-portrait"><img src="/images/tam-berhe.jpg" alt="Tam Berhe, California attorney" width="200" height="200" decoding="async" loading="lazy"></div><div><span class="eyebrow">Your first step is attorney-led</span><h2>A serious matter deserves more than a generic intake script.</h2><p class="section-intro">Tam Berhe reviews selected California civil matters for conflicts, urgency, legal fit, available proof, and the next practical move. The goal of the first review is clarity: what matters now, what should be preserved, and whether the firm may be able to help.</p><div class="actions"><a class="button button-primary" href="{PHONE_HREF}">Call {PHONE_DISPLAY}</a><a class="button button-secondary" href="/attorney-tam-berhe/">Attorney profile</a></div></div></div></section>
<section class="section paper home-faq"><div class="section-inner"><div class="home-section-heading"><div><span class="eyebrow">Before you call</span><h2>Questions people ask at the beginning.</h2></div><p>You do not need to know the legal name of your claim. Start with what happened and what changed because of it.</p></div><div class="faq-list">{faq_html}</div></div></section>
<section class="section deep"><div class="section-inner intake-wrap"><div><span class="eyebrow">Prefer to start online?</span><h2>Send a short summary for a free case review.</h2><p class="section-intro">Name the parties, key dates, what happened, the harm, and any deadline you know about. Do not send privileged or highly sensitive records through this public form. If time may matter, call {PHONE_DISPLAY} instead.</p><a class="home-form-call" href="{PHONE_HREF}">Call now: {PHONE_DISPLAY}</a></div>{intake_form("home-review", heading="Request a free case review", source_route="/")}</div></section>
</main>'''
    return document("/", "California Personal Injury & Civil Rights Lawyer | Berhe Jones LLP", "Injured, mistreated at work, denied insurance, or harmed by misconduct? Call Berhe Jones LLP at 909-609-6685 for a free California case review.", body)


def practice_page(p):
    route = f'/practice-areas/{p["slug"]}/'
    evaluation_items = editorial([(item, "The weight of this factor depends on the complete facts, available law, and recoverable proof.", None) for item in p["evaluation"]])
    resource_href = p["resource"]
    matter_slug = p["slug"]
    body = f'<main id="main">{breadcrumbs([("Practice areas","/practice-areas/"),(p["name"],route)])}{hero(p["h1"],p["lead"],p["name"]) }{proof_band()}'
    body += f'<section class="section"><div class="section-inner split"><div><span class="eyebrow">When this may fit</span><h2>Start with a fact pattern, not a conclusion.</h2><p class="section-intro">A page cannot decide whether a claim exists. These are the kinds of facts that help the firm decide whether a closer review is appropriate.</p></div><div>{editorial([(item,"",None) for item in p["fit"]])}</div></div></section>'
    body += f'<section class="section paper"><div class="section-inner"><span class="eyebrow">Evidence to preserve</span><h2>Keep the records that make the chronology testable.</h2>{editorial([(item,"Preserve the original, note where it came from, and keep a simple date index. Do not send sensitive records through a public form.",None) for item in p["evidence"]])}</div></section>'
    body += f'<section class="section"><div class="section-inner split"><div><span class="eyebrow">Evaluation</span><h2>How the first review tests the matter.</h2></div><div>{evaluation_items}<p class="notice">Deadlines vary by claim, party, forum, and facts. This page does not calculate a filing or notice deadline. If timing may matter, call promptly.</p><a class="button button-secondary" href="{resource_href}">Open the related preparation guide</a></div></div></section>'
    body += f'<section class="section deep"><div class="section-inner"><span class="eyebrow">First review</span><h2>Send a short chronology and the parties involved.</h2><p class="section-intro">The firm may accept, refer, co-counsel, or decline a matter after conflicts and fit review. Contact alone is not representation.</p><div class="actions"><a class="button button-primary" href="/free-case-review/?matter={matter_slug}">Request case review</a><a class="button button-secondary" href="{PHONE_HREF}">Call {PHONE_DISPLAY}</a></div></div></section></main>'
    return document(route, p["title"], p["description"], body, kind="LegalService")


def practice_hub():
    items = [(p["name"], p["lead"], f'/practice-areas/{p["slug"]}/') for p in PRACTICES]
    body = '<main id="main">' + breadcrumbs([("Practice areas","/practice-areas/")]) + hero("Find the right review path for a serious California civil matter.", "Different problems require different proof. Every first review still asks the same four questions: timing, responsibility, harm, and a realistic recovery source.", "Practice areas", "fit", marker="practice-hub") + proof_band()
    body += f'<section class="section"><div class="section-inner"><span class="eyebrow">Client problem index</span><h2>Choose the page closest to your facts.</h2>{editorial(items)}</div></section>'
    body += f'<section class="section paper"><div class="section-inner split"><div><h2>May fit.</h2><p>Specific conduct, documented harm, identifiable parties, usable evidence, and a viable recovery path support closer review.</p></div><div><h2>May not fit.</h2><p>Minor or undocumented harm, no identifiable responsible party, no practical recovery source, or a mismatch with the firm may lead to referral or decline.</p><p class="notice">Act promptly when a deadline, government entity, disappearing evidence, release, claim notice, or pending agency process may be involved.</p></div></div></section></main>'
    return document("/practice-areas/", "California Civil Trial Practice Areas | Berhe Jones LLP", "Berhe Jones LLP reviews California civil matters: injury, wrongful death, employment, civil rights, consumer, insurance, and litigation. Call 909-609-6685.", body, kind="CollectionPage")


def attorney():
    body = '<main id="main">' + breadcrumbs([("Tam Berhe","/attorney-tam-berhe/")]) + hero("Tamerat S. Berhe", "Tam Berhe is a California attorney and founder of Berhe Jones LLP. He reviews selected serious civil matters for fit, conflicts, deadlines, proof, and the next practical step.", "Attorney profile") + proof_band()
    body += f'''<section class="section"><div class="section-inner split"><div class="portrait"><img src="/images/tam-berhe.jpg" alt="Tam Berhe, California attorney" width="200" height="200" decoding="async"></div><div><span class="eyebrow">Profile</span><h2>Attorney-led review with a deliberately narrow first step.</h2><p>The first screen is built for practical decisions: preserve what matters, identify urgency, assess conflicts and fit, and decide whether the path is representation, co-counsel, referral, or decline.</p><dl><dt>Full name</dt><dd>Tamerat S. Berhe (Tam Berhe)</dd><dt>Admission</dt><dd>State Bar of California</dd><dt>Bar number</dt><dd>298992</dd><dt>Public firm identity</dt><dd>{DBA}</dd></dl><p class="notice">Visiting, calling, or submitting information does not create an attorney-client relationship. Representation begins only after conflicts review and a signed written agreement.</p></div></div></section>'''
    body += f'<section class="section paper"><div class="section-inner"><span class="eyebrow">Matter selection</span><h2>What the attorney screen looks for.</h2>{editorial([("Conflicts and parties","Identify adverse parties and relevant relationships before a detailed review.",None),("Deadlines and urgency","Flag any known hearing, notice, claim, filing, preservation, or response date.",None),("Evidence and documents","Organize basic facts and a chronology first; hold privileged or highly sensitive material.",None),("Practice fit","Selected matters may be accepted, referred, co-counseled, or declined case by case.",None),("Written scope","Fees, costs, responsibility, and scope are governed by a written agreement if accepted.",None)])}</div></section></main>'
    return document("/attorney-tam-berhe/", "Tam Berhe, California Attorney | Berhe Jones LLP", "Tam Berhe, California attorney and founder of Berhe Jones LLP, reviews serious injury, employment, civil rights, consumer, and complex civil matters.", body, kind="ProfilePage")


def process_page():
    steps = [("Deadline and conflicts screen","The firm first identifies parties, adverse relationships, known dates, and whether urgent independent action may be needed."),("Fit, evidence, and damages review","The attorney screen considers responsibility, available proof, documented harm, and a practical recovery source."),("Focused information request","If a closer look is appropriate, the firm may request specific records through an approved channel. Do not send a full file through the public form."),("Clear next-step decision","The matter may proceed to an engagement discussion, referral, co-counsel review, a request for more information, or decline. No response-time or acceptance promise is made.")]
    body = '<main id="main">' + breadcrumbs([("Case review process","/case-review-process/")]) + hero("A clear path from first facts to the next move.", "The review is designed to surface urgency, conflicts, evidence, damages, and fit before anyone treats contact as representation.", "Case review process", "fit") + proof_band()
    body += '<section class="section"><div class="section-inner split"><div><span class="eyebrow">Four stages</span><h2>The same order, for every matter.</h2><p class="section-intro">Channel and next-step details depend on the matter. The firm does not promise a response time or outcome.</p></div><ol class="steps">' + ''.join(f'<li><div><h3>{esc(t)}</h3><p>{esc(d)}</p></div></li>' for t,d in steps) + '</ol></div></section>'
    body += f'<section class="section deep"><div class="section-inner"><h2>If a deadline may be close, do not wait on a form.</h2><p class="section-intro">Call {PHONE_DISPLAY} and consider contacting another qualified attorney promptly. A submission is not representation and does not stop a deadline.</p><div class="actions"><a class="button button-primary" href="/resources/prepare-for-case-review/">Prepare the first facts</a><a class="button button-secondary" href="{PHONE_HREF}">Call now</a></div></div></section></main>'
    return document("/case-review-process/", "How Our California Case Review Works | Berhe Jones LLP", "What happens after you contact Berhe Jones LLP: conflict-safe intake, deadline and evidence screen, fit review, and a clear written next step.", body)


def free_review():
    extra = '''<div class="field-grid"><div class="field"><label for="general-matter">Matter type</label><select id="general-matter" name="caseType" required aria-required="true"><option value="">Choose one</option><option>Personal injury or wrongful death</option><option>Employment or workplace</option><option>Civil rights or government accountability</option><option>Consumer protection or Lemon Law</option><option>Insurance bad faith</option><option>Catastrophic injury</option><option>Select civil litigation</option><option>Commercial vehicle accident</option><option>Other</option></select></div><div class="field"><label for="general-contact">Preferred contact</label><select id="general-contact" name="preferred_contact"><option>Phone</option><option>Email</option><option>Either</option></select></div></div><div class="field-grid"><div class="field"><label for="general-county">California county</label><input type="text" id="general-county" name="county" autocomplete="address-level2" autocapitalize="words"></div><div class="field"><label for="general-deadline">Known deadline or urgent date</label><input type="text" id="general-deadline" name="knownDeadline" placeholder="If known"></div></div>'''
    body = '<main id="main">' + breadcrumbs([("Free case review","/free-case-review/")]) + hero("Get the right case screen before proof goes cold.", "Send the parties, key dates, what happened, the documented harm, and any known deadline. Keep the first message short and conflict-safe.", "Canonical intake") + proof_band()
    body += f'<section class="section"><div class="section-inner intake-wrap"><div><span class="eyebrow">Before you submit</span><h2>The essentials are enough to begin.</h2>{editorial([("Timing","Include the event date and every known notice, hearing, agency, claim, or filing date.",None),("Parties","Name the people, employers, agencies, insurers, companies, or other organizations involved.",None),("Proof","Describe the strongest documents, witnesses, medical records, communications, or video without uploading sensitive material.",None),("Harm and recovery","Summarize the injury, loss, employment impact, business loss, or other damages and any known insurance or recovery source.",None)])}</div>{intake_form("general-review", extra=extra, source_route="/free-case-review/")}</div></section></main>'
    return document("/free-case-review/", "Free California Case Review | Berhe Jones LLP", "Free, attorney-led case review for serious California injury, employment, civil rights, consumer, and select civil litigation matters. Call 909-609-6685.", body)


def resource(route, title, description, h1, lead, sections):
    content = ''.join(f'<h2 id="{esc(anchor)}">{esc(heading)}</h2><p>{esc(intro)}</p><ul>' + ''.join(f'<li>{esc(item)}</li>' for item in items) + '</ul>' for anchor,heading,intro,items in sections)
    body = f'<main id="main">{breadcrumbs([("Resources","/resources/"),(h1,route)])}{hero(h1,lead,"Reviewed resource", "fit", "Request case review") }<section class="section"><article class="section-inner prose"><p class="eyebrow">Reviewed July 11, 2026 · Berhe Jones LLP</p><p class="notice">General information only. This guide is not legal advice, does not calculate a deadline, and does not create an attorney-client relationship. Representation begins only after conflicts review and a signed written agreement.</p>{content}<h2>Keep the first message short and conflict-safe.</h2><p>Use a date list, party list, concise event summary, and description of the records you have. Do not send privileged, highly sensitive, or urgent information through a public form.</p><div class="actions"><a class="button button-primary" href="/free-case-review/">Request case review</a><a class="button button-secondary" href="/practice-areas/">Find a practice area</a></div></article></section></main>'
    return document(route,title,description,body,kind="Article")


def resources_hub():
    items=[("What to prepare before a case review","Organize parties, dates, documents, harm, and the question you need reviewed.","/resources/prepare-for-case-review/"),("Commercial-vehicle accident evidence checklist","Preserve scene, vehicle, company, app, insurance, witness, medical, and deadline-sensitive information.","/resources/commercial-vehicle-evidence-checklist/"),("Deadlines and early case review","Understand why public entities, agencies, insurance communications, and disappearing evidence can make early review important.","/resources/deadlines-and-early-review/")]
    body='<main id="main">'+breadcrumbs([("Resources","/resources/")])+hero("Prepare the facts that make a case review stronger.","Short, organized information helps an attorney identify timing, responsibility, proof, harm, and a practical recovery path.","Editorial resource library","fit")+f'<section class="section"><div class="section-inner"><span class="eyebrow">Reviewed July 11, 2026</span><h2>Resource library</h2>{editorial(items)}<p class="notice">These guides provide general information, not individualized legal advice or a limitation calculation. Contact does not create an attorney-client relationship. Representation begins only after conflicts review and a signed written agreement.</p></div></section></main>'
    return document("/resources/","California Case Review Resource Guides | Berhe Jones LLP","Free guides from Berhe Jones LLP on California case review preparation, commercial-vehicle evidence, and deadline-aware early review. Not legal advice.",body,kind="CollectionPage")


def truck_page():
    extra='''<div class="field-grid"><div class="field"><label for="truck-contact">Preferred contact</label><select id="truck-contact" name="preferred_contact"><option>Phone</option><option>Email</option><option>Either</option></select></div><div class="field"><label for="truck-county">California county</label><input type="text" id="truck-county" name="county" autocomplete="address-level2" autocapitalize="words"></div></div>'''
    categories=[("Driver","Identity, license, employer or platform, statements, hours, and phone or app activity."),("Carrier or platform","Dispatch, trip, hiring, training, supervision, insurance, and electronic records."),("Vehicle owner","Ownership, permission, leasing, registration, and coverage."),("Maintenance","Inspection, repair, tire, brake, service, and defect records."),("Electronic data","Logs, telematics, app data, event recorder, GPS, dash camera, and nearby video."),("Scene and treatment","Reports, witnesses, photos, damaged vehicles, medical timeline, and work impact.")]
    body='<main id="main">'+breadcrumbs([("Practice areas","/practice-areas/"),("Commercial vehicle accidents","/landing/truck-fleet-rideshare-accident-california/")])+hero("Truck, fleet, delivery, or rideshare crash? Preserve evidence before it disappears.","Commercial-vehicle matters can involve several responsible parties and records that are routinely overwritten or dispersed.","Evidence-preservation review","fit")+proof_band()
    body+=f'<section class="section"><div class="section-inner"><span class="eyebrow">Evidence map</span><h2>Look beyond the driver and the visible vehicle.</h2>{editorial([(a,b,None) for a,b in categories])}<a class="button button-secondary" href="/resources/commercial-vehicle-evidence-checklist/">Open the commercial vehicle checklist</a></div></section>'
    body+=f'<section class="section deep"><div class="section-inner intake-wrap"><div><h2>Send a short crash chronology.</h2><p class="section-intro">Include vehicle or platform type, date, location, parties, report details, treatment, communications, and any known preservation concern. Deadlines and evidence-retention periods vary.</p></div>{intake_form("truck-review","Commercial vehicle accident","commercial-vehicle",extra=extra,source_route="/landing/truck-fleet-rideshare-accident-california/")}</div></section></main>'
    return document("/landing/truck-fleet-rideshare-accident-california/","Truck, Fleet, Rideshare Accident Case Review | Berhe Jones LLP","Free California case review for serious truck, fleet, delivery, company-vehicle, Uber, and Lyft accident injury matters. Call 909-609-6685.",body,kind="LegalService")


def living_trust():
    extra='''<div class="field-grid"><div class="field"><label for="trust-county">California county</label><input type="text" id="trust-county" name="county" autocomplete="address-level2" autocapitalize="words"></div><div class="field"><label for="trust-property">California real property</label><select id="trust-property" name="real_property"><option>Yes</option><option>No</option><option>Not sure</option></select></div></div><div class="field"><label for="trust-timeline">Planning timeline</label><select id="trust-timeline" name="timeline"><option>Exploring</option><option>Ready to begin</option><option>Existing plan needs review</option></select></div>'''
    body='<main id="main">'+breadcrumbs([("Living trust planning","/living-trust/")])+hero("Protect the plan before life gets complicated.","Attorney-led California living trust planning begins with family, property, decision-maker, and transfer goals—not a one-size-fits-all document.","Estate planning service","fit","Request the Starter Guide","#trust-request")
    body+=f'<section class="section"><div class="section-inner"><span class="eyebrow">Planning scope</span><h2>A trust is part of an organized transfer plan.</h2>{editorial([("Trust agreement","A revocable living trust can organize ownership and instructions, subject to the approved scope of engagement.",None),("Supporting documents","A planning package may involve related incapacity and transfer documents based on the attorney-approved scope.",None),("Funding work","A signed trust must be coordinated with asset ownership. A funding checklist is guidance, not proof every asset was transferred.",None),("Planning process","Guide request, conflict-safe screen, intake, drafting, review, signing, and funding steps are addressed in sequence.",None)])}<p class="notice">This is a distinct estate-planning service, not a contingency case review. Fees and scope are provided only through an approved written agreement. No public fee amount is stated here.</p></div></section>'
    body+=f'<section class="section paper" id="trust-request"><div class="section-inner intake-wrap"><div><span class="eyebrow">Starter Guide</span><h2>Request the Living Trust Starter Guide.</h2><p class="section-intro">The request starts a conflict-safe planning screen and asks the firm to provide its introductory planning guide. It does not create representation or guarantee that a planning engagement will be offered.</p></div>{intake_form("trust-guide","Living trust planning","living-trust", "Living Trust Starter Guide request",extra,"/living-trust/")}</div></section></main>'
    return document("/living-trust/","California Living Trust Planning | Berhe Jones LLP","Attorney-led California living trust planning. Request the Living Trust Starter Guide and a conflict-safe estate planning screen from Berhe Jones LLP.",body,kind="LegalService")


def referrals():
    extra='''<div class="field-grid"><div class="field"><label for="referral-jurisdiction">Jurisdiction</label><input type="text" id="referral-jurisdiction" name="jurisdiction" autocapitalize="words" required aria-required="true"></div><div class="field"><label for="referral-stage">Matter stage</label><input type="text" id="referral-stage" name="matter_stage"></div></div><div class="field"><label for="referral-parties">Parties for conflicts</label><textarea id="referral-parties" name="conflict_parties" autocapitalize="sentences" required aria-required="true"></textarea></div><div class="field"><label for="referral-role">Potential role</label><select id="referral-role" name="potential_role"><option>Referral</option><option>Co-counsel</option><option>Local counsel</option><option>Other attorney inquiry</option></select></div>'''
    body='<main id="main">'+breadcrumbs([("Referrals and co-counsel","/referrals-co-counsel/")])+hero("California co-counsel and referral inquiries for serious civil matters.","The firm reviews jurisdiction, matter profile, posture, deadlines, parties, available records, proposed role, and client-protection requirements before any arrangement is discussed.","Attorney-to-attorney","fit","Send an attorney inquiry","#attorney-inquiry")
    body+=f'<section class="section"><div class="section-inner"><h2>Conflict-safe routing comes first.</h2>{editorial([("Matter profile and posture","Provide the general category, jurisdiction, court or agency posture, and urgent dates without privileged strategy.",None),("Parties for conflicts","Identify known clients, adverse parties, insurers, employers, agencies, platforms, or companies.",None),("Records held back","Describe available records, but do not send privileged, highly sensitive, or client-confidential materials until an approved process exists.",None),("Role and written terms","Any referral, co-counsel, local-counsel, fee, cost, or responsibility allocation is case-specific and documented as required.",None),("Client protection","Disclosure and consent requirements are addressed where applicable before an arrangement proceeds.",None)])}</div></section>'
    body+=f'<section class="section deep" id="attorney-inquiry"><div class="section-inner intake-wrap"><div><h2>Dedicated attorney inquiry.</h2><p class="section-intro">Not every matter is accepted, referred, or co-counseled. Conflicts, fit, deadlines, economics, and professional-conduct requirements control the next step.</p></div>{intake_form("attorney-referral","Attorney referral or co-counsel","attorney-referral","Attorney referral or co-counsel inquiry",extra,"/referrals-co-counsel/")}</div></section></main>'
    return document("/referrals-co-counsel/","California Co-Counsel and Attorney Referrals | Berhe Jones LLP","Lawyer-to-lawyer co-counsel, referral, and local-counsel inquiries for serious California civil matters. Conflict-safe first contact. Call 909-609-6685.",body)


GARDEN_FEED_PATH = ROOT / "data" / "garden-grove-chemical-leak-updates.json"


def _parse_utc(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing UTC timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _garden_feed(path):
    try:
        feed_data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return {"updates": [], "resources": []}, None, None, "unavailable"
    except json.JSONDecodeError:
        return {"updates": [], "resources": []}, None, None, "malformed"
    try:
        verified = _parse_utc(feed_data["lastVerifiedUtc"])
        snapshot = _parse_utc(feed_data["snapshotAsOfUtc"])
        updates = feed_data["updates"]
        resources = feed_data["resources"]
        if not isinstance(updates, list) or not updates or not isinstance(resources, list):
            raise ValueError("missing feed collections")
        update_keys = ("timeUtc", "title", "summary", "sourceLabel", "sourceUrl")
        resource_keys = ("category", "title", "description", "url", "cta")
        for item in updates:
            if not isinstance(item, dict) or not all(isinstance(item.get(key), str) and item[key].strip() for key in update_keys):
                raise ValueError("malformed update")
            _parse_utc(item["timeUtc"])
        for item in resources:
            if not isinstance(item, dict) or not all(isinstance(item.get(key), str) and item[key].strip() for key in resource_keys):
                raise ValueError("malformed resource")
        return feed_data, verified, snapshot, None
    except (KeyError, TypeError, ValueError):
        return {"updates": [], "resources": []}, None, None, "malformed"


def _utc_date_label(value):
    return f"{value.strftime('%B')} {value.day}, {value.year}"


def garden():
    sources=''.join(f'<li><a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(label)}</a></li>' for label,url in GARDEN_SOURCES)
    feed_data, verified, snapshot, feed_error = _garden_feed(GARDEN_FEED_PATH)
    if feed_error:
        feed_state = feed_error
        status_class = "notice feed-status--stale"
        status_role = "alert"
        status_text = (
            "The stored update feed is malformed and cannot be verified. Use the cited official City and County sources below for current instructions."
            if feed_error == "malformed" else
            "The local update feed is unavailable. Use the cited official City and County sources below for current instructions."
        )
    else:
        assert verified is not None and snapshot is not None
        verified_label = _utc_date_label(verified)
        stale = (snapshot - verified).total_seconds() > 14 * 24 * 60 * 60
        feed_state = "stale" if stale else "fresh"
        status_class = "notice feed-status--stale" if stale else "notice"
        status_role = "alert" if stale else "status"
        status_text = (
            f"Update feed is stale. Last verified {verified_label}. Follow the official City and County sources below for current instructions."
            if stale else
            f"Update feed last verified {verified_label}. Official emergency sources remain primary."
        )
    update_items = []
    for item in feed_data["updates"]:
        update_label = _utc_date_label(_parse_utc(item["timeUtc"]))
        update_items.append(
            f'<li><time datetime="{esc(item["timeUtc"])}">{esc(update_label)}</time>'
            f'<h3>{esc(item["title"])}</h3><p>{esc(item["summary"])}</p>'
            f'<a href="{esc(item["sourceUrl"])}" target="_blank" rel="noopener noreferrer">Source: {esc(item["sourceLabel"])}</a></li>'
        )
    updates = "".join(update_items)
    resources = "".join(
        f'<article class="editorial-item"><div><span class="eyebrow">{esc(item["category"])}</span><h3>{esc(item["title"])}</h3></div><div><p>{esc(item["description"])}</p><a href="{esc(item["url"])}">{esc(item["cta"])}</a></div></article>'
        for item in feed_data["resources"]
    ) or '<p class="notice">The local resource index is unavailable. Use the cited official City and County sources below.</p>'
    extra='''<div class="field-grid"><div class="field"><label for="garden-contact">Preferred contact</label><select id="garden-contact" name="preferred_contact"><option>Phone</option><option>Email</option><option>Either</option></select></div><div class="field"><label for="garden-city">Affected city</label><input type="text" id="garden-city" name="affected_city" autocapitalize="words"></div></div><div class="field-grid"><div class="field"><label for="garden-impact">Primary impact</label><select id="garden-impact" name="impact_type"><option>Evacuation or displacement</option><option>Health symptoms or care</option><option>Work or business loss</option><option>Property or cleanup</option><option>Multiple impacts</option></select></div><div class="field"><label for="garden-counsel">Already represented for this matter?</label><select id="garden-counsel" name="already_represented"><option>No</option><option>Yes</option><option>Not sure</option></select></div></div>'''
    body='<main id="main">'+breadcrumbs([("Garden Grove chemical incident","/landing/garden-grove-chemical-leak/")])+hero("Garden Grove chemical incident: cited updates and careful next steps.","A public-source resource for affected residents, workers, parents, schools, and businesses. Follow emergency officials first and use the source record to verify incident facts.","Public-source incident resource","fit","View public updates","#updates")
    body+=f'''<section class="section paper" id="updates"><div class="section-inner"><span class="eyebrow">Public-source monitoring</span><h2>Updates stored with source attribution.</h2><p id="updates-status" class="{status_class}" role="{status_role}" data-feed-state="{feed_state}">{esc(status_text)}</p><button class="button button-secondary" id="refresh-updates" type="button" aria-controls="updates-feed">Refresh updates</button><ol class="updates-list" id="updates-feed">{updates}</ol></div></section>'''
    body+=f'<section class="section"><div class="section-inner"><span class="eyebrow">Official and practical routes</span><h2>Incident resources in one place.</h2><div class="editorial-list" id="resource-grid">{resources}</div></div></section>'
    body+=f'<section class="section" id="proof"><div class="section-inner"><span class="eyebrow">Proof preservation</span><h2>Preserve records before sending a short summary.</h2>{editorial([("Evacuation and location","Save alerts, address or cross streets, hotel or shelter receipts, mileage, childcare, pet boarding, and displacement records.",None),("Symptoms and health","Keep a dated symptom timeline, visit summaries, prescriptions, follow-up instructions, and relevant pediatric or respiratory records.",None),("Work and business loss","Preserve missed-work records, payroll or PTO use, closure notices, customer messages, POS reports, refunds, inventory loss, and supplier notes.",None),("Property and cleanup","Keep time-stamped photos, odor or residue notes, air-quality readings, HVAC or remediation invoices, and damaged-property records.",None)])}</div></section>'
    body+=f'<section class="section paper"><div class="section-inner"><span class="eyebrow">Source record</span><h2>Public sources cited on this page.</h2><p>No affiliation with emergency officials, GKN Aerospace, plaintiffs, filed actions, or class action counsel is claimed. Allegations, investigations, and filed cases are not findings of liability.</p><ul class="source-list">{sources}</ul></div></section>'
    body+=f'<section class="section deep" id="case-review"><div class="section-inner intake-wrap"><div><h2>Request a Garden Grove incident screening.</h2><p class="section-intro">The initial screening is free. Keep the summary short. Representation, fees, costs, and scope exist only through a signed written agreement after conflicts review.</p></div>{intake_form("garden-review","Garden Grove chemical incident","garden-grove-chemical","Garden Grove incident screening",extra,"/landing/garden-grove-chemical-leak/")}</div></section></main>'
    return document("/landing/garden-grove-chemical-leak/","Garden Grove Chemical Leak Updates | Berhe Jones LLP","Public-source updates, official resources, and free Berhe Jones LLP screening for Garden Grove GKN Aerospace methyl methacrylate incident claims.",body)


def legal_page(route, title, description, h1, paragraphs):
    toc=''.join(f'<li><a href="#section-{i}">{esc(heading)}</a></li>' for i,(heading,_) in enumerate(paragraphs,1))
    sections=''.join(f'<section id="section-{i}"><h2>{esc(heading)}</h2>{"".join(f"<p>{esc(p)}</p>" for p in texts)}</section>' for i,(heading,texts) in enumerate(paragraphs,1))
    body=f'<main id="main">{breadcrumbs([(h1,route)])}<section class="section"><article class="section-inner prose"><span class="eyebrow">Effective July 11, 2026</span><h1>{esc(h1)}</h1><nav class="notice" aria-label="On this page"><h2>On this page</h2><ol>{toc}</ol></nav>{sections}<p><a class="button button-secondary" href="/">Back to Berhe Jones LLP home</a></p></article></section></main>'
    return document(route,title,description,body)


def success():
    route="/success.html"
    body=f'''<main id="main"><section class="section"><div class="section-inner prose"><span class="eyebrow">Submission status</span><h1>This page alone does not confirm delivery.</h1><p>A confirmed receipt is shown directly by the secure BerheLaw intake service only after it accepts and records a request. Opening or bookmarking this page does not prove that a submission was received.</p><h2>If you just submitted a request</h2><p>Return to the case-review form and submit again only if the intake service did not display a receipt. Do not include privileged, highly sensitive, or urgent information in a public form.</p><p class="notice">If timing may matter, do not rely on a website submission. Call {PHONE_DISPLAY} and consider contacting another qualified attorney promptly.</p><div class="actions"><a class="button button-primary" href="/free-case-review/">Return to case review</a><a class="button button-secondary" href="{PHONE_HREF}">Call {PHONE_DISPLAY}</a></div></div></section></main>'''
    return document(route,"Berhe Jones LLP | Submission Status","A Berhe Jones LLP intake receipt is confirmed only by the secure intake service after acceptance.",body,robots="noindex, nofollow")


def build_pages():
    outputs[route_path("/")] = homepage()
    outputs[route_path("/attorney-tam-berhe/")] = attorney()
    outputs[route_path("/case-review-process/")] = process_page()
    outputs[route_path("/free-case-review/")] = free_review()
    outputs[route_path("/practice-areas/")] = practice_hub()
    for practice in PRACTICES:
        outputs[route_path(f'/practice-areas/{practice["slug"]}/')] = practice_page(practice)
    outputs[route_path("/resources/")] = resources_hub()
    outputs[route_path("/resources/prepare-for-case-review/")] = resource(
        "/resources/prepare-for-case-review/", "What to Prepare Before a Case Review | Berhe Jones LLP",
        "Conflict-safe checklist from Berhe Jones LLP for preparing a California civil matter: organize parties, dates, documents, and harm. General information only.",
        "What to prepare before a case review.", "Organize the facts that let an attorney see timing, responsibility, harm, evidence, and a practical recovery route.",
        [("basic-facts","The basic facts to organize","A useful first request is specific and short.",["Who is involved and who may be adverse","What happened, where, and on what dates","What changed afterward and what harm resulted","What documents, witnesses, photographs, video, or records exist","What deadlines, notices, hearings, or agency dates may exist","What question or outcome you want reviewed"]),("hold-back","What not to send through a public form","Keep sensitive material for an approved follow-up channel.",["Do not send a full records dump","Do not send passwords, credentials, Social Security numbers, or financial account details","Do not send privileged communications or rely on a form for urgent action"])])
    outputs[route_path("/resources/commercial-vehicle-evidence-checklist/")] = resource(
        "/resources/commercial-vehicle-evidence-checklist/", "Commercial Vehicle Accident Evidence Checklist | Berhe Jones LLP",
        "Evidence checklist from Berhe Jones LLP for California truck, fleet, delivery, and rideshare crashes: scene records, app data, witnesses, and preservation steps.",
        "Commercial-vehicle accident evidence checklist.", "Commercial vehicle evidence can be distributed across a driver, carrier, platform, owner, maintenance provider, insurers, devices, and nearby cameras.",
        [("scene","Crash scene and vehicle proof","Preserve what identifies the event and every involved entity.",["Scene, vehicle, cargo, road, damage, and visible-company photographs or video","License plates, DOT numbers, company markings, driver information, app or trip details","Witness names, report number, responding agency, nearby businesses, and camera locations"]),("records","Company, insurance, and medical organization","Build a date-indexed record without altering originals.",["Insurance communications and requests for statements or releases","Treatment timeline, restrictions, bills, wage impact, and follow-up plans","Dispatch, app, GPS, event-recorder, log, maintenance, inspection, and preservation concerns","Known government, claim, insurer, or court dates"])])
    outputs[route_path("/resources/deadlines-and-early-review/")] = resource(
        "/resources/deadlines-and-early-review/", "Deadlines and Early Case Review | Berhe Jones LLP",
        "Why early review matters in serious California civil matters: government-claim notices, evidence preservation, insurance requests, and filing windows.",
        "Why early review can matter when deadlines are unclear.", "No general guide can calculate an individualized deadline. Early organization helps counsel identify which dates and procedures need immediate attention.",
        [("timing","Situations where timing can matter","Different facts can trigger different notices, agency steps, contracts, or filing rules.",["Public entities, government actors, or government claim procedures","Employment complaints, administrative agencies, internal notices, or right-to-sue processes","Insurance notices, examinations, proofs of loss, releases, or claim communications","Video, app data, logs, surveillance, messages, physical evidence, or witnesses that may disappear"]),("organize","How to organize timing facts","Create a record another person can verify.",["Build a date list from the event through the present","Save dated notices, letters, envelopes, emails, texts, filings, and agency records","List who contacted you, when, how, and what was requested","Flag anything signed and every date someone told you to respond"])])
    outputs[route_path("/landing/truck-fleet-rideshare-accident-california/")] = truck_page()
    outputs[route_path("/landing/garden-grove-chemical-leak/")] = garden()
    outputs[route_path("/living-trust/")] = living_trust()
    outputs[route_path("/referrals-co-counsel/")] = referrals()
    outputs[route_path("/privacy.html")] = legal_page(
        "/privacy.html", "Berhe Jones LLP | Privacy Policy", "Read the Berhe Jones LLP privacy policy for website, contact-form, and case-review information submitted to the California civil practice.", "Privacy Policy",
        [("Information collected",["Berhe Jones LLP may collect identifiers and contact information you choose to provide, including your name, phone number, email address, matter type, parties, location, and the message you submit. The intake form also transmits the page URL, referrer, campaign, form version, consent version, and matter category to the firm's intake service at admin.berhelaw.com.","The site may receive ordinary device, browser, referral, security, and usage information from hosting and form-processing providers. The current public release does not send separate CTA telemetry."]),("Use, service providers, and retention",["Information may be used to respond to inquiries, evaluate whether the firm may be able to help, perform conflict checks, route the matter, maintain intake records, secure and improve the site, and communicate about the request.","The firm may disclose information to service providers that host the site, process form submissions, maintain systems or records, or as required by law. Retention depends on intake, conflict, legal, security, and professional obligations; this public policy does not promise a fixed deletion date."]),("Sale, sharing, and security limits",["Berhe Jones LLP does not sell personal information submitted through this website and does not knowingly share website inquiry information for cross-context behavioral advertising.","No internet transmission or public form is guaranteed secure. Do not send privileged documents, full medical records, Social Security numbers, financial account details, credentials, highly sensitive records, or urgent safety requests through a public form."]),("California privacy requests",["California residents may request access to, correction of, or deletion of personal information, subject to legal and professional obligations that may require preservation of certain records.","To make a privacy request, call 909-609-6685 or write to Berhe Jones LLP, 901 Via Piemonte, Suite 230, Ontario, CA 91764-8500. Contacting the firm does not create an attorney-client relationship; representation begins only after conflicts review and a signed written agreement."])])
    outputs[route_path("/terms.html")] = legal_page(
        "/terms.html", "Berhe Jones LLP | Terms of Service", "Terms of service for using the Berhe Jones LLP website, public legal resources, case-review forms, and California civil practice pages.", "Terms of Service",
        [("General information",["This website provides general information about Berhe Jones LLP and California legal services. The site is not legal advice and does not guarantee any result."]),("No representation",["Use of this website, a form, phone call, email, text, guide, or checklist does not create an attorney-client relationship. Representation begins only after conflicts review and a signed written agreement."]),("Permitted use and updates",["You may not use this website in a way that interferes with its operation, attempts unauthorized access, or misrepresents your identity. Berhe Jones LLP may update these terms from time to time."]),("Contact",["For questions, call 909-609-6685 or write to Berhe Jones LLP, 901 Via Piemonte, Suite 230, Ontario, CA 91764-8500."])])
    outputs[route_path("/disclaimer.html")] = legal_page(
        "/disclaimer.html", "Berhe Jones LLP | Legal Disclaimer", "Legal disclaimer for Berhe Jones LLP website content, case-review forms, attorney-client relationship limits, and California legal information.", "Legal Disclaimer",
        [("Attorney advertising",["Attorney advertising. The information on this website is for general informational purposes only and is not legal advice. Every case is different. Descriptions of legal services do not guarantee a similar outcome."]),("No attorney-client relationship",["Contacting Berhe Jones LLP through this website, by phone, email, text, guide, or checklist request does not create an attorney-client relationship. An attorney-client relationship is formed only after conflicts review and a signed written agreement."]),("Deadlines and source information",["Deadlines vary. Do not rely on this site to calculate a filing, notice, agency, insurance, or other deadline. Public-source incident information should be verified through its cited source."]),("Contact",["For questions, call 909-609-6685 or write to Berhe Jones LLP, 901 Via Piemonte, Suite 230, Ontario, CA 91764-8500."])])
    outputs[ROOT / "success.html"] = success()


def infrastructure():
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for route in ROUTES:
        sitemap.append(f'  <url><loc>https://berhelaw.com{route}</loc><lastmod>{RELEASE_DATE}</lastmod></url>')
    sitemap.append('</urlset>')
    outputs[ROOT / "sitemap.xml"] = "\n".join(sitemap) + "\n"
    outputs[ROOT / "_headers"] = '''/*
  Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: DENY
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Resource-Policy: same-origin
  Origin-Agent-Cluster: ?1
  X-DNS-Prefetch-Control: on
  X-Permitted-Cross-Domain-Policies: none
  Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=(), browsing-topics=(), payment=(), usb=(), magnetometer=(), accelerometer=(), gyroscope=()
  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self' https://admin.berhelaw.com; form-action https://admin.berhelaw.com; object-src 'none'; frame-src 'none'; base-uri 'self'; frame-ancestors 'none'; upgrade-insecure-requests

/assets/*
  Cache-Control: public, max-age=31536000, immutable

/images/*
  Cache-Control: public, max-age=604800

/success.html
  X-Robots-Tag: noindex, nofollow
  Cache-Control: no-store
'''
    outputs[ROOT / "README.md"] = '''# BerheLaw public site

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

## Content guardrails

Do not add outcomes, testimonials, ratings, awards, locations, response-time promises, specialist claims, imagery, or professional facts without written provenance. Preserve the DBA disclosure, advertising disclaimer, conflict-review language, signed-written-agreement requirement, and Garden Grove citations. `success.html` remains excluded from the sitemap and noindexed/no-store in `_headers`.
'''


def write(check=False):
    build_pages(); infrastructure()
    expected_assets = {p for p in outputs if p.parent.name in {"css", "js"} and p.parent.parent.name == "assets"}
    stale = set()
    for folder in (ROOT / "assets" / "css", ROOT / "assets" / "js"):
        if folder.exists(): stale |= {p for p in folder.iterdir() if p.is_file() and p not in expected_assets}
    def differs(path, content):
        if not path.exists():
            return True
        try:
            return path.read_text(encoding="utf-8") != content
        except UnicodeDecodeError:
            return True
    mismatches = [path for path, content in outputs.items() if differs(path, content)]
    if check:
        if mismatches or stale:
            for path in mismatches: print(f"out of date: {path.relative_to(ROOT)}")
            for path in stale: print(f"stale generated asset: {path.relative_to(ROOT)}")
            return 1
        print(f"generated output current: {len(outputs)} files")
        return 0
    for path in stale: path.unlink()
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(f"generated {len(outputs)} files")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    raise SystemExit(write(args.check))
