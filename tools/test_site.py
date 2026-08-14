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
        page.on("requestfailed", lambda r: failed_requests.append(r.url))

        page.goto("file:///" + INDEX.replace("\\", "/"))
        page.wait_for_load_state("networkidle")

        # --- content generated from the resume actually rendered
        summary = page.locator(".resume-summary")
        check("resume summary rendered", summary.count() == 1 and len(summary.inner_text()) > 200,
              "%d chars" % len(summary.inner_text()) if summary.count() else "missing")

        # --- the landing router is the centrepiece: it must be live, above the fold,
        # and already showing a routed result before the visitor touches anything.
        router = page.locator("#landing-router")
        check("landing router present on home", router.count() == 1 and router.is_visible())

        box = router.bounding_box()
        check("landing router above the fold", bool(box) and box["y"] + 80 < 900,
              "top at y=%d" % box["y"] if box else "no box")

        first = page.locator("#lr-result .lr-command")
        check("landing router pre-routes on load",
              first.count() == 1 and first.inner_text().startswith("/"),
              first.inner_text() if first.count() else "no result rendered")

        check("landing router states it is a simulation",
              "no model runs on this page" in page.locator(".lr-note").inner_text().lower())

        # routing a typed task changes the verdict, i.e. it is computing not displaying
        before = first.inner_text()
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
