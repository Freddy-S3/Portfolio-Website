"""Render the site with every third-party origin blocked, as a corporate proxy does.

The site is the link Freddy hands recruiters, and they open it from inside work networks.
On 2026-09-01 it rendered on two of those with no fonts and no icons: the proxy answered
fonts.googleapis.com and cdnjs.cloudflare.com with 403, and the page had no local fallback.

This serves the site over loopback, aborts every request that is not same-origin, and then
demands what a visitor would notice - each @font-face actually loads, and every visible icon
occupies real space in a real Font Awesome face - across both themes at desktop and 375px.

`tools/check_no_cdn.py` reads the source for external references; this one proves the page
still looks right when those references are unreachable. Neither substitutes for the other.

Usage:
    py tools/check_offline_render.py     # exit 0 on pass, screenshots to .screenshots/offline/
"""
import functools, http.server, os, socketserver, threading, sys
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, ".screenshots", "offline")
os.makedirs(OUT, exist_ok=True)
PORT = 8731

Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
http.server.SimpleHTTPRequestHandler.log_message = lambda *a, **k: None
Handler.log_message = lambda *a, **k: None
httpd = socketserver.TCPServer(("127.0.0.1", PORT), Handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

blocked, failed, errors = [], [], []
ok = True

with sync_playwright() as p:
    b = p.chromium.launch()
    for theme in ("light", "dark"):
        for label, w, h in (("desktop", 1440, 900), ("mobile", 375, 812)):
            page = b.new_page(viewport={"width": w, "height": h})
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append("uncaught: %s" % e))
            page.on("requestfailed", lambda r: failed.append(r.url))

            def route(r):
                # Simulate the corporate proxy: only his own host is reachable.
                if "127.0.0.1:%d" % PORT in r.request.url:
                    return r.continue_()
                blocked.append(r.request.url)
                return r.abort()
            page.route("**/*", route)

            page.goto("http://127.0.0.1:%d/index.html" % PORT)
            page.wait_for_load_state("networkidle")
            if theme == "dark":
                page.click(".theme-btn")
                page.wait_for_timeout(600)

            name = "%s-%s" % (theme, label)
            # Screenshot before anything below mutates the DOM: the icon sweep toggles
            # .active across sections and leaves the page in a state no visitor sees.
            page.screenshot(path=os.path.join(OUT, name + ".png"), full_page=(label == "desktop"))

            # fonts.check() is false for a face the browser has not lazily loaded yet,
            # which says nothing about whether the file is reachable. Force each face to
            # load and require it to actually resolve.
            fonts = page.evaluate("""async () => {
                const want = [
                    ...[400,500,600,700,800].map(w => w + ' 16px Poppins'),
                    '900 16px "Font Awesome 5 Free"',
                    '400 16px "Font Awesome 5 Free"',
                    '400 16px "Font Awesome 5 Brands"',
                ];
                const out = {};
                for (const spec of want) {
                    try { out[spec] = (await document.fonts.load(spec)).length > 0; }
                    catch (e) { out[spec] = false; }
                }
                out.bodyFont = getComputedStyle(document.body).fontFamily;
                return out;
            }""")
            bodyFont = fonts.pop("bodyFont")
            badFonts = [k for k, v in fonts.items() if not v]

            icons = {"total": 0, "bad": []}
            for sec in ("home", "about", "harness", "portfolio", "blogs", "contact"):
                page.evaluate("""(id) => {
                    document.querySelectorAll('section, header').forEach(
                        s => s.classList.toggle('active', s.id === id));
                }""", sec)
                page.wait_for_timeout(700)
                r = page.evaluate("""() => {
                    const bad = [];
                    let n = 0;
                    for (const el of document.querySelectorAll('i[class*="fa-"]')) {
                        if (el.offsetParent === null) continue;
                        n++;
                        // offsetWidth/Height, not getBoundingClientRect: sections animate
                        // in with a transform, and the visual rect is mid-scale for a moment.
                        const b = {width: el.offsetWidth, height: el.offsetHeight};
                        const fam = getComputedStyle(el, ':before').fontFamily || '';
                        if (b.width < 4 || b.height < 4 || !/Font Awesome/i.test(fam)) {
                            bad.push(el.className + ' w=' + b.width.toFixed(1) + ' h=' + b.height.toFixed(1) + ' fam=' + fam + ' disp=' + getComputedStyle(el).display);
                        }
                    }
                    return {n, bad};
                }""")
                icons["total"] += r["n"]
                icons["bad"] += r["bad"]
            page.evaluate("""() => {
                document.querySelectorAll('section, header').forEach(
                    s => s.classList.toggle('active', s.id === 'home'));
            }""")
            page.wait_for_timeout(300)

            name = "%s-%s" % (theme, label)
            good = not badFonts and not icons["bad"]
            ok = ok and good
            print("%-16s fonts=%d/%d loaded  icons=%d bad=%d  body=%s  %s"
                  % (name, len(fonts) - len(badFonts), len(fonts),
                     icons["total"], len(icons["bad"]), bodyFont, "OK" if good else "BROKEN"))
            for x in badFonts:
                print("    font failed to load:", x)
            for x in icons["bad"][:5]:
                print("    bad icon:", x)
            page.close()
    b.close()
httpd.shutdown()
print("\nblocked external requests attempted:", sorted(set(blocked)) or "none")
print("failed requests:", sorted(set(failed)) or "none")
print("console errors:", errors[:5] or "none")
print("RESULT:", "PASS" if (ok and not failed and not errors) else "FAIL")
sys.exit(0 if (ok and not failed and not errors) else 1)
