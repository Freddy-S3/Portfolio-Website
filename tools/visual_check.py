"""Render the site at real viewport widths and fail on layout defects.

Catches the things a human notices immediately and a diff never shows:
content sliding under fixed overlays, horizontal overflow, and text clipped
by its own container. Run it before claiming any HTML/CSS/JS change is done.

    python tools/visual_check.py                 # serve ./ and check
    python tools/visual_check.py --shots out/    # also save screenshots

Exit code 1 means at least one defect was found.
"""

import argparse
import functools
import http.server
import json
import socket
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent

# Widths that matter: laptop, common desktop, wide desktop, ultrawide, then the
# responsive breakpoints this stylesheet actually declares.
WIDTHS = [1280, 1440, 1600, 1920, 2560, 1250, 1070, 970, 768, 600, 390]

# Elements pinned over the page. Anything scrolling under them is a defect.
OVERLAY_SELECTORS = [".controls", ".theme-btn"]

PROBE = """
() => {
  const overlays = %OVERLAYS%
    .flatMap(s => [...document.querySelectorAll(s)])
    .map(e => ({ sel: e.className, box: e.getBoundingClientRect() }))
    .filter(o => o.box.width > 0);

  const defects = [];
  const label = e => {
    const cls = (e.className || '').toString().trim().split(/\\s+/).filter(Boolean).slice(0, 2).join('.');
    return e.tagName.toLowerCase() + (cls ? '.' + cls : '') + (e.id ? '#' + e.id : '');
  };
  const text = e => (e.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 60);

  // The overlay rail is fixed, so its viewport x-band is reserved at every
  // scroll position. Any in-flow content entering that band collides.
  // Only right-edge rails reserve a band. Below the mobile breakpoint these
  // overlays relocate to a bottom bar, where a horizontal reserve is meaningless.
  const rails = overlays.filter(o =>
    o.box.left > innerWidth * 0.6 && o.box.width < innerWidth * 0.3);
  const reserved = rails.length ? Math.min(...rails.map(o => o.box.left)) : Infinity;

  for (const e of document.querySelectorAll('body *')) {
    if (e.closest(%OVERLAYS_JOINED%)) continue;
    const cs = getComputedStyle(e);
    if (cs.position === 'fixed' || cs.visibility === 'hidden' || cs.display === 'none') continue;
    const b = e.getBoundingClientRect();
    if (b.width < 8 || b.height < 8) continue;

    // Only leaf-ish nodes: a wide wrapper whose text is safely inset is fine.
    const leaf = ![...e.children].some(c => c.getBoundingClientRect().width > 8);
    if (leaf && b.right > reserved + 1) {
      defects.push({ kind: 'overlay-collision', el: label(e), right: Math.round(b.right),
                     reserved: Math.round(reserved), text: text(e) });
    }
    if (b.right > innerWidth + 1 || b.left < -1) {
      defects.push({ kind: 'viewport-overflow', el: label(e), left: Math.round(b.left),
                     right: Math.round(b.right), vw: innerWidth, text: text(e) });
    }
    if (e.scrollWidth > e.clientWidth + 1 && cs.overflowX === 'visible' && leaf) {
      defects.push({ kind: 'clipped-text', el: label(e),
                     scrollWidth: e.scrollWidth, clientWidth: e.clientWidth, text: text(e) });
    }
  }

  // An icon name the loaded icon font does not carry renders as a blank box.
  // It looks fine in the markup and is invisible in a diff.
  for (const e of document.querySelectorAll('i[class*="fa-"]')) {
    const cs = getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const glyph = getComputedStyle(e, '::before').content;
    if (!glyph || glyph === 'none' || glyph === 'normal' || glyph === '""') {
      defects.push({ kind: 'missing-icon-glyph', el: label(e), content: glyph });
    }
  }

  const docOverflow = document.documentElement.scrollWidth > innerWidth + 1;
  if (docOverflow) {
    defects.push({ kind: 'page-scrolls-horizontally', el: 'html',
                   scrollWidth: document.documentElement.scrollWidth, vw: innerWidth });
  }
  return defects;
}
"""


def build_probe():
    overlays = json.dumps(OVERLAY_SELECTORS)
    return PROBE.replace("%OVERLAYS_JOINED%", json.dumps(",".join(OVERLAY_SELECTORS))).replace(
        "%OVERLAYS%", overlays
    )


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def serve(directory, port):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    handler = functools.partial(Quiet, directory=str(directory))
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="check a live URL instead of serving the repo")
    ap.add_argument("--shots", help="directory to write a screenshot per width")
    ap.add_argument("--widths", help="comma-separated widths to override the default sweep")
    args = ap.parse_args()

    widths = [int(w) for w in args.widths.split(",")] if args.widths else WIDTHS
    httpd = None
    url = args.url
    if not url:
        port = free_port()
        httpd = serve(ROOT, port)
        url = f"http://127.0.0.1:{port}/index.html"

    shots = Path(args.shots) if args.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)

    probe = build_probe()
    failures = 0
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for width in widths:
                page = browser.new_page(viewport={"width": width, "height": 900})
                page.goto(url, wait_until="networkidle")
                page.wait_for_timeout(400)
                defects = page.evaluate(probe)
                if shots:
                    page.screenshot(path=str(shots / f"{width}.png"), full_page=True)

                if defects:
                    failures += 1
                    print(f"\nFAIL {width}px - {len(defects)} defect(s)")
                    seen = set()
                    for d in defects:
                        key = (d["kind"], d["el"])
                        if key in seen:
                            continue
                        seen.add(key)
                        print(f"  [{d['kind']}] {d['el']}")
                        for k, v in d.items():
                            if k not in ("kind", "el"):
                                print(f"      {k}: {v}")
                else:
                    print(f"ok   {width}px")
                page.close()
            browser.close()
    finally:
        if httpd:
            httpd.shutdown()

    if failures:
        print(f"\n{failures} width(s) failed.")
        return 1
    print("\nAll widths clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
