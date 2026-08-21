"""End-to-end browser test for the portfolio site.

Renders index.html in real Chromium and checks what a human would check:
does every section show up, does the theme toggle work, does anything overflow
the viewport, are there console errors, do the images actually load.

Setup (once):
    py -m pip install playwright
    py -m playwright install chromium

Usage:
    py tools/test_site.py              # run, write screenshots to .screenshots/
    py tools/test_site.py --headed     # watch it drive
"""

import argparse
import os
import sys
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "index.html")
SHOTS = os.path.join(ROOT, ".screenshots")

VIEWPORTS = [("desktop", 1440, 900), ("tablet", 900, 1000), ("mobile", 390, 844)]

# Section id -> the nav button that reveals it. The site swaps .active rather
# than navigating, so every section lives in the same document.
SECTIONS = ["home", "about", "harness", "portfolio", "blogs", "contact"]

# Never publishable, whatever the mirror happens to contain on the day this runs.
PRIVATE_SKILLS = ["job-search", "pdev"]

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, (" - " + detail) if detail else ""))
    return ok


# --------------------------------------------------------------------------- interaction
# A control that renders and does nothing is invisible to every other check in this file.
# The suite passed 37/37 while the harness simulator's "Route this task" button produced no
# observable change at all, because presence and wiring were asserted and *effect* never was.
# An addEventListener that runs and writes back the same DOM is, to a visitor, a dead button.
#
# So: click the real control, fingerprint the page before and after, and demand a difference.

# Everything a visitor could actually perceive changing. Deliberately broad - a control is
# allowed to prove itself through any of these, and a control that moves none of them has
# no observable effect by definition.
OBSERVABLE = """() => {
    const active = document.querySelector('section.active, header.active');
    const txt = el => (el ? el.innerText : '').replace(/\\s+/g, ' ').trim();
    return JSON.stringify({
        bodyClass: document.body.className,
        activeSection: active ? active.id : null,
        activeNav: [...document.querySelectorAll('.control')].map(c => c.className).join('|'),
        hash: location.hash,
        activeText: txt(active).slice(0, 4000),
        landingResult: txt(document.querySelector('#lr-result')),
        simResult: txt(document.querySelector('#simulator-result')),
        chipState: [...document.querySelectorAll('.lr-chip')].map(c => c.className).join('|'),
        fieldValues: [...document.querySelectorAll('input, textarea, select')]
            .map(e => e.id + '=' + e.value).join('|'),
    });
}"""
# Deliberately NOT part of the fingerprint: document.activeElement. Clicking a button moves
# focus to it by definition, so including it made every click look like it had an effect and
# quietly defeated the whole detector - the dead Route button passed this check while doing
# nothing. A control has to prove itself by changing something a visitor can read.


def click_must_change(page, console_errors, name, selector, setup=None, index=0):
    """Click a real control and fail loudly unless the page observably changed.

    Also fails if the interaction logged a console error, since a silent exception in a
    handler is exactly how a button becomes decorative while still looking wired up.
    """
    target = page.locator(selector).nth(index)
    if target.count() == 0:
        return check("interaction: %s" % name, False, "control not found: %s" % selector)
    if not target.is_visible():
        return check("interaction: %s" % name, False, "control present but not visible: %s" % selector)

    if setup:
        setup()
        page.wait_for_timeout(150)

    errors_before = len(console_errors)
    before = page.evaluate(OBSERVABLE)
    target.click()
    page.wait_for_timeout(450)
    after = page.evaluate(OBSERVABLE)
    new_errors = console_errors[errors_before:]

    if new_errors:
        return check("interaction: %s" % name, False,
                     "console error during interaction: %s" % new_errors[0][:160])
    return check("interaction: %s" % name, before != after,
                 "clicked, but nothing observable changed - the control is decorative"
                 if before == after else "")


# ------------------------------------------------------------------------------- overlap
# Two elements whose boxes intersect, or two pills that butt together with no gap, are a
# defect no assertion in this file could see before: every element is present, visible, and
# correctly styled in isolation. The skill catalog's "user-invocable" and "auto-triggers"
# badges wrapped onto consecutive lines with zero vertical separation and read as one
# collided blob; Faruk reported it from the live site.
#
# Bounding-box intersection is the cheap reliable test. Ancestors are skipped (a parent
# always contains its child) and so are absolutely positioned and fixed elements, which are
# meant to sit on top of things - the fixed rail already has its own check.
OVERLAP = """(args) => {
    const [sel, minGap] = args;
    const els = [...document.querySelectorAll(sel)].filter(e => {
        const r = e.getBoundingClientRect();
        const cs = getComputedStyle(e);
        return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' &&
               cs.display !== 'none' && cs.position !== 'absolute' && cs.position !== 'fixed';
    });
    const hits = [];
    for (let i = 0; i < els.length; i++) {
        for (let j = i + 1; j < els.length; j++) {
            const a = els[i], b = els[j];
            if (a.contains(b) || b.contains(a)) continue;
            const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
            // Positive means the ranges overlap on that axis; negative is the clear gap.
            const ox = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
            const oy = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);

            // Strict intersection is NOT enough. The defect this was written for - the two
            // catalog badges - had a vertical gap of exactly 0: the pills touched, borders
            // flush, which reads as one collided blob and is what got reported. An
            // intersection-only predicate scored that as clean, and was verified to miss it.
            // So flag two things: boxes that genuinely overlap, and boxes that are stacked
            // along one axis with less than minGap of clearance on it.
            let reason = null, gap = 0;
            if (ox > 1 && oy > 1) {
                reason = 'overlap'; gap = Math.round(Math.min(ox, oy));
            } else if (ox > 1 && oy <= 1 && oy > -minGap) {
                reason = 'stacked, only ' + Math.round(-oy) + 'px apart'; gap = Math.round(-oy);
            } else if (oy > 1 && ox <= 1 && ox > -minGap) {
                reason = 'side by side, only ' + Math.round(-ox) + 'px apart'; gap = Math.round(-ox);
            }
            if (reason) {
                hits.push({ a: (a.innerText || a.className).trim().slice(0, 26),
                            b: (b.innerText || b.className).trim().slice(0, 26),
                            reason: reason, gap: gap });
            }
        }
    }
    return hits;
}"""

# Groups of siblings that must never collide, and the clearance each needs.
OVERLAP_GROUPS = [
    ("#skill-catalog .skill-card .badge", 2),
    ("#simulator-result .badge", 2),
    (".skill-card", 2),
    (".portfolio-item", 2),
    (".lr-chip", 2),
    (".btn-con .main-btn", 2),
    (".harness-stat", 2),
    (".harness-ops-stat", 2),
]
# Deliberately NOT listed: .contact-item. Those are full-width rows in a vertical list, and
# adjacent rows in a list abut by design - flagging them reports a defect that is not one,
# and a check that cries wolf gets muted, which costs more than it saves.

# CSS transitions are the other source of false positives here. The theme toggle animates
# colour and position, so a measurement taken while a transition is in flight reads a box
# that is on its way somewhere - .lr-chip measured 2px of clearance mid-transition against a
# declared 8px gap. Geometry assertions need the page to hold still.
FREEZE_ANIMATION = """() => {
    const style = document.createElement('style');
    style.id = 'test-freeze';
    style.textContent = `*, *::before, *::after {
        transition: none !important;
        animation: none !important;
    }`;
    document.head.appendChild(style);
}"""


# --------------------------------------------------------------------- text-flow crowding
# The overlap check above compares element boxes, and there is a whole class of collision it
# cannot see. In the contact rows the label and its value sat in a flex row with no gap: the
# two boxes were adjacent, never intersecting, so every bounding-box predicate scored them
# clean while "Languages" visually ran into its list of languages on the rendered page.
#
# The difference is that a box is not where the glyphs are. An element can be wider than its
# text, or narrower than its text, and only the second one is a defect you can see. So this
# measures the text itself with a Range, which reports the rectangles the glyphs actually
# occupy, and asserts two things a box comparison cannot:
#   1. a label and its value sharing a visual line keep a real horizontal gap between glyphs;
#   2. no text is painted outside the box that is supposed to contain it.
# Proven to fail before it was trusted: run against the pre-fix markup it reported the
# Location, Email, Mobile Number, Education and Languages rows at 0px of clearance.
TEXT_CROWDING = """(args) => {
    const [rowSel, labelSel, valueSel, minGap] = args;
    const visible = (e) => {
        const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
        return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none';
    };
    // Where the glyphs land, as opposed to where the element's box is.
    const textBox = (e) => {
        const range = document.createRange();
        range.selectNodeContents(e);
        const rects = [...range.getClientRects()].filter(r => r.width > 0 && r.height > 0);
        if (!rects.length) return null;
        return {
            left: Math.min(...rects.map(r => r.left)),
            right: Math.max(...rects.map(r => r.right)),
            top: Math.min(...rects.map(r => r.top)),
            bottom: Math.max(...rects.map(r => r.bottom)),
        };
    };
    const hits = [];
    let measured = 0;
    for (const row of document.querySelectorAll(rowSel)) {
        const label = row.querySelector(labelSel), value = row.querySelector(valueSel);
        if (!label || !value || !visible(label) || !visible(value)) continue;
        measured++;
        const lt = textBox(label), vt = textBox(value);
        if (!lt || !vt) continue;
        const name = (label.innerText || '').trim().slice(0, 24) || '(unlabelled)';

        // Sharing vertical space means they are on the same visual line and are therefore
        // competing for the same horizontal run. Stacked rows are not a collision.
        if (Math.min(lt.bottom, vt.bottom) - Math.max(lt.top, vt.top) > 1) {
            const gap = Math.round(vt.left - lt.right);
            if (gap < minGap) hits.push(name + ': label/value only ' + gap + 'px apart');
        }

        // Text wider than its own container has escaped the column and is being painted
        // over whatever sits next to it, which is exactly the reported symptom.
        for (const [el, tb, what] of [[label, lt, 'label'], [value, vt, 'value']]) {
            const box = el.getBoundingClientRect(), cs = getComputedStyle(el);
            const spill = Math.round(Math.max(
                (box.left + (parseFloat(cs.paddingLeft) || 0)) - tb.left,
                tb.right - (box.right - (parseFloat(cs.paddingRight) || 0))));
            if (spill > 1) hits.push(name + ': ' + what + ' text spills ' + spill + 'px past its box');
        }
    }
    return { measured: measured, hits: hits };
}"""

# Rows built as "label, then its value", and the clearance the glyphs must keep.
TEXT_CROWDING_GROUPS = [
    (".contact-item", ".icon span", "p", 12),
]


def check_no_text_crowding(page, label):
    for row_sel, label_sel, value_sel, gap in TEXT_CROWDING_GROUPS:
        res = page.evaluate(TEXT_CROWDING, [row_sel, label_sel, value_sel, gap])
        # A section that does not contain these rows would otherwise report a green tick for
        # having measured nothing, and a vacuous pass is worse than no check at all.
        if not res["measured"]:
            continue
        check("no label/value crowding in %s (%s)" % (row_sel, label),
              not res["hits"], "; ".join(res["hits"][:3]))


# A badge on a certification card has exactly two legitimate states, and the difference
# matters: a link that goes somewhere, or a mark that is visibly and audibly not a link
# yet. The state that must never exist is the middle one - something that looks clickable,
# invites the click, and does nothing. href="#" produced precisely that, which is why
# render_card now emits a span instead. A span alone is not enough though: .icon carries a
# pointer cursor and a hover response, so an unstyled span still reads as clickable to a
# sighted visitor and as nothing at all to a screen reader. This asserts the whole contract
# rather than the markup choice, so a deliberately inert badge passes and a broken one does
# not.
BADGE_STATES = """() => {
    const bad = [];
    for (const item of document.querySelectorAll('#portfolio .portfolio-item')) {
        const title = (item.querySelector('h3') || {}).innerText || '(untitled)';
        for (const badge of item.querySelectorAll('.icons > *')) {
            const tag = badge.tagName.toLowerCase();
            if (tag === 'a') {
                const href = (badge.getAttribute('href') || '').trim();
                if (!href || href === '#') bad.push(title + ': anchor with a dead href');
                continue;
            }
            // Not an anchor, so it must declare itself pending rather than merely be inert.
            if (!badge.classList.contains('icon-pending')) {
                bad.push(title + ': non-link badge not marked pending');
                continue;
            }
            const sr = badge.querySelector('.sr-only');
            if (!sr || sr.textContent.trim().length < 10) {
                bad.push(title + ': pending badge carries no text for assistive tech');
            }
            if (!(badge.getAttribute('title') || '').trim()) {
                bad.push(title + ': pending badge has no hover title');
            }
            if (getComputedStyle(badge).cursor === 'pointer') {
                bad.push(title + ': pending badge still shows a clickable cursor');
            }
        }
    }
    return bad;
}"""


def check_no_overlap(page, label):
    for selector, gap in OVERLAP_GROUPS:
        if page.locator(selector).count() < 2:
            continue
        hits = page.evaluate(OVERLAP, [selector, gap])
        detail = ""
        if hits:
            detail = "; ".join("%r/%r %s" % (h["a"], h["b"], h["reason"]) for h in hits[:3])
        check("no overlap in %s (%s)" % (selector, label), not hits, detail)


def run_quality_pass(page, console_errors, label):
    """Whole-site checks that must hold at every width and in every theme."""
    for section in SECTIONS:
        page.click('.control[data-id="%s"]' % section)
        page.wait_for_timeout(350)
        if section == "harness":
            try:
                page.wait_for_selector("#skill-catalog .skill-card", timeout=6000)
            except Exception:
                pass
            page.wait_for_timeout(400)
        check_no_overlap(page, "%s/#%s" % (label, section))
        check_no_text_crowding(page, "%s/#%s" % (label, section))

    # Images: decoded, and carrying alt text that says something. An empty alt on a
    # meaningful image is invisible to a screen reader and to anyone whose images fail.
    bad = page.eval_on_selector_all(
        "img",
        """els => els.map(e => {
            const alt = e.getAttribute('alt');
            const broken = !e.complete || e.naturalWidth === 0;
            const src = (e.getAttribute('src') || '').split('/').pop();
            if (broken) return src + ' (did not decode)';
            if (alt === null) return src + ' (no alt attribute)';
            if (alt.trim() === '') return src + ' (empty alt)';
            if (alt.trim().length < 4) return src + ' (alt too short: ' + alt + ')';
            return null;
        }).filter(Boolean)""",
    )
    check("images decode and carry meaningful alt (%s)" % label, not bad, "; ".join(bad[:4]))


def run_interaction_suite(page, console_errors):
    """Click every interactive control on the page and assert each one does something."""
    # The harness simulator is where the dead button lived. Its empty state is the state
    # every visitor arrives in, so it is tested first and explicitly.
    #
    # This has to run against a FRESH load. Clicking Route on an empty box after some
    # earlier result is on screen replaces that result with the placeholder, which is a
    # real change and passes a generic before/after diff - so the generic check alone
    # cannot see this bug. The failing path is the arrival path: land, click, and the
    # placeholder is already what is showing, so nothing moves. Reload to reproduce it.
    page.reload()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(400)
    click_must_change(
        page, console_errors,
        "homepage Route button opens the AI skill catalog from a cold arrival state",
        "#lr-btn",
    )
    check("homepage Route button activates the AI skill catalog",
          "active" in (page.locator("#harness").get_attribute("class") or ""))
    page.click('.control[data-id="home"]')
    page.wait_for_timeout(400)
    page.click('.control[data-id="harness"]')
    # The catalog and the example list render on requestIdleCallback. Until they settle,
    # every snapshot differs from the last for reasons that have nothing to do with the
    # control under test, which is enough to mask a genuinely dead button. Wait for the
    # async work to finish so a detected change is attributable to the click.
    page.wait_for_selector("#skill-catalog .skill-card", timeout=5000)
    page.wait_for_function(
        "() => document.querySelectorAll('#task-select option').length > 1", timeout=5000)
    page.wait_for_timeout(400)

    click_must_change(
        page, console_errors,
        "Route this task from a cold arrival state (empty box, untouched page)",
        "#route-btn",
    )
    # The regression in its own words: the empty-state response must not be the idle
    # placeholder text, or the button is back to looking broken.
    empty_state = page.locator("#simulator-result").inner_text().strip()
    check("empty-state response differs from the idle placeholder",
          "Pick or type a task" not in empty_state, empty_state[:80])

    click_must_change(
        page, console_errors,
        "Route this task with a typed task",
        "#route-btn",
        setup=lambda: page.fill("#task-input", "Draft a Confluence page documenting our new auth flow."),
    )
    check("typed task routes to a named skill",
          page.locator("#simulator-result .result-command").inner_text().startswith("/"),
          page.locator("#simulator-result .result-command").inner_text())

    # Choosing an example is a control too, and it silently filled a box before.
    errors_before = len(console_errors)
    before = page.evaluate(OBSERVABLE)
    page.select_option("#task-select", index=3)
    page.wait_for_timeout(400)
    check("interaction: example select routes on change",
          page.evaluate(OBSERVABLE) != before and not console_errors[errors_before:])

    # --- the landing console, the first thing anyone touches
    page.click('.control[data-id="home"]')
    page.wait_for_timeout(500)

    # Each chip is checked from a state it is not already in - chip 0 is pre-selected on
    # load, so clicking it first would correctly change nothing and read as a dead control.
    # "Already in the target state" is not the same defect as "does nothing", and the suite
    # has to be able to tell them apart or it will cry wolf.
    chip_count = page.locator(".lr-chip").count()
    check("landing chips rendered", chip_count > 0, "found %d" % chip_count)
    for i in range(chip_count):
        label = page.locator(".lr-chip").nth(i).inner_text().strip()
        other = (i + 1) % chip_count
        click_must_change(page, console_errors,
                          'landing chip "%s"' % label, ".lr-chip", index=i,
                          setup=lambda o=other: page.locator(".lr-chip").nth(o).click())

    click_must_change(
        page, console_errors,
        "landing Route button with typed input",
        "#lr-btn",
        setup=lambda: page.fill("#lr-input", "Turn this rough plan into vertical-slice tracker tickets."),
    )
    click_must_change(
        page, console_errors,
        "landing Route button with an empty input",
        "#lr-btn",
        setup=lambda: page.fill("#lr-input", ""),
    )

    # --- navigation: every nav control must actually swap the section. Each is approached
    # from a different section for the same reason as the chips above.
    for section in SECTIONS:
        away = "about" if section != "about" else "contact"
        click_must_change(page, console_errors,
                          "nav control -> #%s" % section,
                          '.control[data-id="%s"]' % section,
                          setup=lambda a=away: page.click('.control[data-id="%s"]' % a))
        check("nav control -> #%s activates the right section" % section,
              "active" in (page.locator("#%s" % section).get_attribute("class") or ""))

    # --- theme toggle, both directions, since only one may be wired
    click_must_change(page, console_errors, "theme toggle (first press)", ".theme-btn")
    click_must_change(page, console_errors, "theme toggle (press back)", ".theme-btn")

    # --- anything with an in-page target: it must move the document, not sit there
    page.click('.control[data-id="home"]')
    page.wait_for_timeout(400)
    anchors = page.locator('a[href^="#"]:not([href="#"])')
    for i in range(anchors.count()):
        href = anchors.nth(i).get_attribute("href")
        if anchors.nth(i).is_visible():
            click_must_change(page, console_errors,
                              'in-page link %s' % href, 'a[href^="#"]:not([href="#"])', index=i)

    # --- a link with no destination is a control that invites a click and does nothing.
    # Clicking it cannot be fingerprinted (a real link navigates away), so this is asserted
    # statically. "javascript:" hrefs are judged by the handler check below instead.
    dead = page.eval_on_selector_all(
        "a[href]",
        """els => els.filter(e => {
            const h = (e.getAttribute('href') || '').trim();
            return h === '' || h === '#';
        }).map(e => {
            const card = e.closest('.portfolio-item');
            const label = card ? card.innerText.split('\\n')[0] : (e.innerText || e.className);
            return (label || e.tagName).trim().slice(0, 50);
        })""",
    )
    check("no links that go nowhere", not dead, ", ".join(dead))

    # --- an inline on* attribute that names a function which is not actually reachable
    # throws on every press. The click may still work through a separate addEventListener,
    # which is what makes this survive review: the button behaves, and quietly logs a
    # ReferenceError each time. Run each inline handler and require it to resolve.
    broken_inline = page.eval_on_selector_all(
        "[onclick]",
        """els => els.map(e => {
            const src = e.getAttribute('onclick');
            try { new Function(src).call(e); return null; }
            catch (err) {
                if (err instanceof ReferenceError || err instanceof TypeError) {
                    return ((e.innerText || e.tagName).trim().slice(0, 30)) + ' -> ' + src + ' (' + err.message + ')';
                }
                return null;
            }
        }).filter(Boolean)""",
    )
    check("inline handlers resolve to real functions", not broken_inline, "; ".join(broken_inline))

    # --- the contact route. The form that used to live here never had a backend: from the
    # initial commit its action was empty, later a mailto:, so a submitted message was either
    # discarded by a page reload or handed to a mail client the visitor might not have. It was
    # removed on 2026-08-15. These assertions stop it, or anything like it, coming back.
    page.click('.control[data-id="contact"]')
    page.wait_for_timeout(500)
    forms = page.locator("form").count()
    check("no form posts to a backend that does not exist", forms == 0,
          "%d form(s) still on the page" % forms)

    mailtos = page.eval_on_selector_all(
        'a[href^="mailto:"]', "els => els.map(e => e.getAttribute('href'))")
    check("a working mailto route exists", len(mailtos) >= 1, ", ".join(mailtos[:2]))
    check("contact section offers a reachable route",
          page.locator('#contact a[href^="mailto:"], #contact a[href*="linkedin"], '
                       '#contact a[href*="github"]').count() >= 3,
          "found %d direct contact links" % page.locator(
              '#contact a[href^="mailto:"], #contact a[href*="linkedin"], '
              '#contact a[href*="github"]').count())


def run(headed):
    from playwright.sync_api import sync_playwright

    if not os.path.isdir(SHOTS):
        os.makedirs(SHOTS)

    console_errors = []
    failed_requests = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        # An uncaught exception in a click handler never reaches page.on("console"), so
        # without this a handler could throw on every press and the suite would stay green.
        page.on("pageerror", lambda e: console_errors.append("uncaught: %s" % e))
        page.on("requestfailed", lambda r: failed_requests.append(r.url))

        page.goto("file:///" + INDEX.replace("\\", "/"))
        page.wait_for_load_state("networkidle")

        # --- content generated from the resume actually rendered
        summary = page.locator(".resume-summary")
        check("resume summary rendered", summary.count() == 1 and len(summary.inner_text()) > 200,
              "%d chars" % len(summary.inner_text()) if summary.count() else "missing")

        # --- the landing router is the centrepiece: it must be live, above the fold,
        # and ready for the visitor's first action without pretending a task was routed.
        router = page.locator("#landing-router")
        check("landing router present on home", router.count() == 1 and router.is_visible())

        box = router.bounding_box()
        check("landing router above the fold", bool(box) and box["y"] + 80 < 900,
              "top at y=%d" % box["y"] if box else "no box")

        first = page.locator("#lr-result .lr-command")
        check("landing router starts with no task selected",
              page.locator("#lr-input").input_value() == "" and first.count() == 0,
              first.inner_text() if first.count() else "empty")

        check("landing router states it is a simulation",
              "no model runs on this page" in page.locator(".lr-note").inner_text().lower())

        # routing a typed task changes the verdict, i.e. it is computing not displaying
        before = page.locator("#lr-result").inner_text()
        page.fill("#lr-input", "Something in the login flow is throwing errors, help me investigate the unexpected behavior.")
        page.click("#lr-btn")
        page.wait_for_timeout(300)
        after = page.locator("#lr-result .lr-command").inner_text()
        check("landing router responds to typed input", after != before,
              "%s -> %s" % (before, after))
        # the example chips are the first thing anyone clicks, so each must reach the
        # skill its label promises rather than winning on one stray shared word
        check("debug example routes to /debugging", after == "/debugging", after)

        # a one-term match is a coin flip and the card has to admit it
        page.fill("#lr-input", "I have an idea.")
        page.click("#lr-btn")
        page.wait_for_timeout(300)
        check("weak matches are labelled as weak",
              page.locator("#lr-result .lr-weak").count() == 1)

        page.locator(".lr-chip").nth(2).click()
        page.wait_for_timeout(300)
        check("landing router example chips route",
              page.locator("#lr-result .lr-command").inner_text().startswith("/"))

        # --- the private career skill must not be published, in data or in markup
        html = page.content()
        leaked = [n for n in PRIVATE_SKILLS if n in html]
        check("no private skill in rendered page", not leaked, ", ".join(leaked))

        page.click('.control[data-id="about"]')
        page.wait_for_timeout(600)

        cats = page.locator(".skill-category")
        check("skill categories rendered", cats.count() == 4, "found %d, expected 4" % cats.count())

        tags = page.locator(".skill-tag")
        check("skill tags rendered", tags.count() >= 25, "found %d" % tags.count())
        check("skill tags visible", tags.count() > 0 and tags.first.is_visible())

        items = page.locator(".timeline-item")
        check("timeline items rendered", items.count() == 4, "found %d, expected 4" % items.count())

        # --- the full catalog still exists in depth, rendered from the same data
        page.click('.control[data-id="harness"]')
        page.wait_for_timeout(900)
        catalog = page.locator("#skill-catalog .skill-card")
        check("full skill catalog rendered", catalog.count() >= 30, "found %d" % catalog.count())
        check("harness disclaimer still present",
              "simulation, not a live agent" in page.locator(".harness-disclaimer").inner_text())
        operations = page.locator("#harness-operations")
        check("portable project model rendered", operations.count() == 1 and operations.is_visible())
        check("portable project model explains host reuse",
              "ChatGPT, Claude Code, and Codex" in operations.inner_text())
        flow = operations.locator(".harness-flow li")
        check("portable project workflow rendered", flow.count() == 4, "found %d, expected 4" % flow.count())

        page.click('.control[data-id="portfolio"]')
        page.wait_for_timeout(600)
        cards = page.locator(".portfolio-item")
        check("portfolio cards rendered", cards.count() == 9, "found %d, expected 9" % cards.count())

        # --- every image decoded, not just requested
        broken = page.eval_on_selector_all(
            "img",
            "els => els.filter(e => !e.complete || e.naturalWidth === 0).map(e => e.getAttribute('src'))",
        )
        check("all images loaded", not broken, ", ".join(broken) if broken else "")

        # --- navigation swaps the active section
        for section in SECTIONS:
            page.click('.control[data-id="%s"]' % section)
            page.wait_for_timeout(400)
            active = page.locator("#%s" % section)
            check("nav shows #%s" % section, "active" in (active.get_attribute("class") or ""))

        # --- theme toggle, and text stays legible after it
        page.click('.control[data-id="about"]')
        page.wait_for_timeout(400)

        def tag_contrast():
            return page.eval_on_selector(
                ".skill-tag",
                """el => {
                    const s = getComputedStyle(el);
                    const bg = getComputedStyle(document.body).backgroundColor;
                    const lum = c => {
                        const [r,g,b] = c.match(/\\d+/g).slice(0,3).map(Number)
                            .map(v => { v/=255; return v <= .03928 ? v/12.92 : Math.pow((v+.055)/1.055, 2.4); });
                        return .2126*r + .7152*g + .0722*b;
                    };
                    const a = lum(s.color), b2 = lum(bg);
                    return (Math.max(a,b2) + .05) / (Math.min(a,b2) + .05);
                }""",
            )

        def router_input_contrast():
            return page.eval_on_selector(
                "#lr-input",
                """el => {
                    const s = getComputedStyle(el);
                    const lum = c => {
                        const [r,g,b] = c.match(/\\d+/g).slice(0,3).map(Number)
                            .map(v => { v/=255; return v <= .03928 ? v/12.92 : Math.pow((v+.055)/1.055, 2.4); });
                        return .2126*r + .7152*g + .0722*b;
                    };
                    const a = lum(s.color), b = lum(s.backgroundColor);
                    return (Math.max(a,b) + .05) / (Math.min(a,b) + .05);
                }""",
            )

        dark_ratio = tag_contrast()
        check("skill tag contrast in dark mode", dark_ratio >= 4.5, "ratio %.2f" % dark_ratio)
        page.screenshot(path=os.path.join(SHOTS, "about-dark.png"), full_page=True)

        page.click(".theme-btn")
        page.wait_for_timeout(700)
        check("theme toggle applies light-mode",
              "light-mode" in (page.locator("body").get_attribute("class") or ""))
        light_ratio = tag_contrast()
        check("skill tag contrast in light mode", light_ratio >= 4.5, "ratio %.2f" % light_ratio)

        # The router field sets its own background, so it can miss a theme swap while
        # every surrounding element flips correctly.
        page.click('.control[data-id="home"]')
        page.wait_for_timeout(300)
        lr_light = router_input_contrast()
        check("router input contrast in light mode", lr_light >= 4.5, "ratio %.2f" % lr_light)
        page.click('.control[data-id="about"]')
        page.wait_for_timeout(300)
        page.screenshot(path=os.path.join(SHOTS, "about-light.png"), full_page=True)

        page.click(".theme-btn")
        page.wait_for_timeout(500)

        # --- nothing spills sideways at any width
        for label, width, height in VIEWPORTS:
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(500)
            overflow = page.evaluate(
                "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
            )
            check("no horizontal overflow on %s" % label, overflow <= 1, "%dpx over" % overflow)
            page.screenshot(path=os.path.join(SHOTS, "about-%s.png" % label), full_page=True)

            # The router makes the hero column much taller, and content pushed off the TOP
            # is invisible to every other check here: no overflow, no console error, every
            # element still "visible". Assert the landing actually starts at the name.
            page.click('.control[data-id="home"]')
            page.wait_for_timeout(400)
            # Offset within the header, not the viewport: scroll position varies with what
            # the run clicked last, layout does not, and layout is the thing under test.
            name_offset = page.evaluate(
                """() => {
                    const h = document.querySelector('#home').getBoundingClientRect();
                    const n = document.querySelector('#home .name').getBoundingClientRect();
                    return Math.round(n.top - h.top);
                }"""
            )
            check("hero name not cropped on %s" % label, name_offset >= -1,
                  "name sits %dpx from the top of the hero" % name_offset)

        # --- the whole point of the change: on a phone, a visitor must be able to reach
        # the router without scrolling. Checked at 375px, narrower than the 390 above.
        page.set_viewport_size({"width": 375, "height": 812})
        page.click('.control[data-id="home"]')
        page.wait_for_timeout(600)
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(200)
        # "Inside the viewport" is not the test: the nav bar is fixed to the bottom on
        # mobile and covers ~90px, so the usable fold ends where the nav begins.
        chips_bottom, nav_top = page.evaluate(
            """() => [
                document.querySelector('#lr-chips').getBoundingClientRect().bottom,
                document.querySelector('.controls').getBoundingClientRect().top,
            ]"""
        )
        check("router reachable without scrolling at 375px", 0 < chips_bottom <= nav_top,
              "example chips end at y=%d, nav bar starts at y=%d" % (chips_bottom, nav_top))
        page.screenshot(path=os.path.join(SHOTS, "landing-375.png"))

        # --- every control, clicked for real, at a normal desktop size
        page.set_viewport_size({"width": 1440, "height": 900})
        page.wait_for_timeout(400)
        run_interaction_suite(page, console_errors)

        # --- whole-site quality pass: overlap and images, at both widths and in both themes.
        # Each of these has to hold independently - a collision that only appears at 375px, or
        # only in light mode, is still a collision a visitor sees.
        page.evaluate(FREEZE_ANIMATION)
        for width, height, wlabel in [(1440, 900, "desktop"), (375, 812, "375px")]:
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(400)
            run_quality_pass(page, console_errors, "%s dark" % wlabel)
            page.click(".theme-btn")
            page.wait_for_timeout(500)
            run_quality_pass(page, console_errors, "%s light" % wlabel)
            page.click(".theme-btn")
            page.wait_for_timeout(400)

        # --- every local file a link points at must actually exist on disk. A 404 on a
        # certificate PDF is invisible in a diff and only shows up as a broken tab.
        page.set_viewport_size({"width": 1440, "height": 900})
        local_hrefs = page.eval_on_selector_all(
            "a[href]",
            """els => els.map(e => e.getAttribute('href'))
                .filter(h => h && !/^(https?:|mailto:|tel:|#|javascript:)/i.test(h))""",
        )
        missing = []
        for href in sorted(set(local_hrefs)):
            target = os.path.join(ROOT, unquote(href.split("#")[0].split("?")[0]))
            if not os.path.exists(target):
                missing.append(href)
        check("every local link resolves to a real file", not missing,
              "missing: %s" % "; ".join(missing[:4]))

        # --- certification badges: linked, or explicitly pending, never dead-but-clickable.
        page.click('.control[data-id="portfolio"]')
        page.wait_for_timeout(400)
        bad_badges = page.evaluate(BADGE_STATES)
        check("catalog badges are linked or marked pending", not bad_badges,
              "; ".join(bad_badges[:4]))

        # The pending state has to actually be in use, or the check above is satisfied by a
        # page that simply has no pending badges and would pass just as well if the feature
        # were deleted.
        pending = page.locator("#portfolio .icon-pending")
        check("the pending badge state is exercised by a real card", pending.count() >= 1,
              "%d pending badges" % pending.count())

        # The GCP card links at the certificate PDF rather than the issuer badge page, and
        # the file is really there - it was untracked on disk before this change, so the
        # href resolved locally for whoever added it and 404'd for everyone else.
        gcp = page.locator('#portfolio a[href$="GCPCloudArchitectCertification.pdf"]')
        check("GCP card links to the certificate PDF", gcp.count() == 1,
              "%d matching anchors" % gcp.count())
        check("the GCP certificate PDF exists on disk",
              os.path.exists(os.path.join(ROOT, "Certificates",
                                          "GCPCloudArchitectCertification.pdf")))

        # Evidence the repaired button actually responds, kept next to the other shots.
        page.click('.control[data-id="harness"]')
        page.wait_for_timeout(700)
        page.fill("#task-input", "")
        page.click("#route-btn")
        page.wait_for_timeout(400)
        page.locator(".harness-simulator").screenshot(
            path=os.path.join(SHOTS, "route-button-empty-state.png"))
        page.fill("#task-input", "Review this pull request like a strict senior engineer would.")
        page.click("#route-btn")
        page.wait_for_timeout(400)
        page.locator(".harness-simulator").screenshot(
            path=os.path.join(SHOTS, "route-button-routed.png"))

        browser.close()

    check("no console errors", not console_errors, "; ".join(console_errors[:3]))
    real_failures = [u for u in failed_requests if not u.startswith("https://fonts.")]
    check("no failed requests", not real_failures, "; ".join(real_failures[:3]))

    failed = [name for name, ok, _ in results if not ok]
    print("\n%d/%d checks passed" % (len(results) - len(failed), len(results)))
    print("screenshots: .screenshots/")
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headed", action="store_true", help="show the browser window")
    args = parser.parse_args()
    try:
        return run(args.headed)
    except ImportError:
        print("Playwright missing. Run:")
        print("  py -m pip install playwright")
        print("  py -m playwright install chromium")
        return 1


if __name__ == "__main__":
    sys.exit(main())
