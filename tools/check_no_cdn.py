"""Fail if the site loads any runtime asset from a third-party origin.

Freddy's site has to render for recruiters sitting behind corporate proxies that
block everything except his own domain. On 2026-09-01 it rendered without fonts or
icons on two work machines because index.html pulled Poppins from fonts.googleapis.com
and Font Awesome from cdnjs.cloudflare.com, and the proxy answered both with 403.

A link a visitor clicks is fine - GitHub, LeetCode, Amazon, Accredible. What is not
fine is anything the browser fetches on its own to render the page: a stylesheet, a
script, a font, an image, an iframe. That distinction is the whole check.

Usage:
    py tools/check_no_cdn.py     # exit 0 when clean, 1 with the list when not
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Origins the page may fetch from at render time. Same-origin only: the deployed site
# is freddyshaikh.com, so nothing here needs a host at all.
ALLOWED_HOSTS = set()

HTML_FILES = ["index.html"]
ASSET_DIRS = ["styles", "."]

# Attributes the browser fetches without the visitor doing anything. href is only a
# fetch when the tag is a <link>, which is why <link> is matched separately from <a>.
FETCH_ATTRS = ("src", "srcset", "data-src", "poster")

EXTERNAL = re.compile(r'(?:https?:)?//([a-zA-Z0-9.-]+)')


def _host(url):
    m = EXTERNAL.match(url.strip())
    return m.group(1).lower() if m else None


def html_violations(path):
    """External origins in tags the browser fetches on its own."""
    out = []
    src = open(path, encoding="utf-8").read()
    rel = os.path.relpath(path, ROOT)

    for tag in re.findall(r'<link\b[^>]*>', src, re.I):
        m = re.search(r'href\s*=\s*["\']([^"\']+)["\']', tag, re.I)
        if not m:
            continue
        host = _host(m.group(1))
        # preconnect/dns-prefetch fetch nothing themselves, but they only exist to
        # speed up a third-party fetch, so a surviving one means one was reintroduced.
        if host and host not in ALLOWED_HOSTS:
            out.append("%s: <link> -> %s" % (rel, m.group(1)))

    for tag in re.findall(r'<(?:script|img|iframe|video|audio|source|embed)\b[^>]*>', src, re.I):
        for attr in FETCH_ATTRS:
            for m in re.finditer(attr + r'\s*=\s*["\']([^"\']+)["\']', tag, re.I):
                for candidate in m.group(1).split(","):
                    host = _host(candidate.strip().split(" ")[0])
                    if host and host not in ALLOWED_HOSTS:
                        out.append("%s: %s -> %s" % (rel, attr, candidate.strip()))

    for m in re.finditer(r'@import\s+(?:url\()?["\']?((?:https?:)?//[^"\')\s]+)', src, re.I):
        host = _host(m.group(1))
        if host and host not in ALLOWED_HOSTS:
            out.append("%s: @import -> %s" % (rel, m.group(1)))

    return out


def css_violations(path):
    """External origins in url() - fonts and background images live here."""
    out = []
    rel = os.path.relpath(path, ROOT)
    src = open(path, encoding="utf-8").read()
    # Strip comments: Font Awesome's licence header carries fontawesome.com URLs
    # that nothing ever fetches, and flagging those would make the check unrunnable.
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    for m in re.finditer(r'url\(\s*["\']?((?:https?:)?//[^"\')\s]+)', src, re.I):
        host = _host(m.group(1))
        if host and host not in ALLOWED_HOSTS:
            out.append("%s: url() -> %s" % (rel, m.group(1)))
    for m in re.finditer(r'@import\s+(?:url\()?["\']?((?:https?:)?//[^"\')\s]+)', src, re.I):
        host = _host(m.group(1))
        if host and host not in ALLOWED_HOSTS:
            out.append("%s: @import -> %s" % (rel, m.group(1)))
    return out


def js_violations(path):
    """Runtime fetches from JS: fetch(), XHR, and dynamically injected assets."""
    out = []
    rel = os.path.relpath(path, ROOT)
    src = open(path, encoding="utf-8").read()
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    for m in re.finditer(
            r'(?:fetch|importScripts|\.open)\s*\(\s*["\']((?:https?:)?//[^"\']+)', src, re.I):
        host = _host(m.group(1))
        if host and host not in ALLOWED_HOSTS:
            out.append("%s: fetch -> %s" % (rel, m.group(1)))
    for m in re.finditer(r'\.(?:src|href)\s*=\s*["\']((?:https?:)?//[^"\']+)', src, re.I):
        host = _host(m.group(1))
        if host and host not in ALLOWED_HOSTS:
            out.append("%s: assigned .src/.href -> %s" % (rel, m.group(1)))
    return out


def violations():
    out = []
    for name in HTML_FILES:
        path = os.path.join(ROOT, name)
        if os.path.isfile(path):
            out += html_violations(path)
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs
                   if d not in (".git", "node_modules", ".screenshots", "resume",
                                "exports", "docs", "Certificates", "img", "fonts")]
        for f in files:
            path = os.path.join(root, f)
            if f.endswith(".css"):
                out += css_violations(path)
            elif f.endswith(".js"):
                out += js_violations(path)
    return sorted(set(out))


def main():
    bad = violations()
    if bad:
        print("External runtime dependencies found (the site will break behind a proxy):")
        for line in bad:
            print("  " + line)
        return 1
    print("no external runtime dependencies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
