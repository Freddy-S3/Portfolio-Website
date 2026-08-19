"""Render the two changed regions at both widths in both themes, for review."""
import os
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "resume", "build", "renditions")
os.makedirs(OUT, exist_ok=True)

FREEZE = """() => {
    const s = document.createElement('style');
    s.textContent = '*,*::before,*::after{transition:none!important;animation:none!important}';
    document.head.appendChild(s);
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1440, "height": 900})
    page.goto("file:///" + os.path.join(ROOT, "index.html").replace("\\", "/"))
    page.wait_for_load_state("networkidle")
    page.evaluate(FREEZE)

    for width, height, wl in [(1440, 900, "desktop"), (375, 812, "375px")]:
        page.set_viewport_size({"width": width, "height": height})
        for theme in ["dark", "light"]:
            page.wait_for_timeout(350)
            for section, sel, name in [
                ("about", ".about-container", "about-stats-row"),
                ("contact", ".left-contact .contact-info", "contact-labels"),
            ]:
                page.click('.control[data-id="%s"]' % section)
                page.wait_for_timeout(350)
                page.locator(sel).screenshot(
                    path=os.path.join(OUT, "%s-%s-%s.png" % (name, wl, theme)))
            page.click(".theme-btn")
            page.wait_for_timeout(400)
        # The dark/light loop already toggles twice, which lands back on dark. An extra
        # click here silently inverted every label at the second width.

    b.close()
print("wrote screenshots to", OUT)
