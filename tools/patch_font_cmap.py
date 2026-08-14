"""Vendor Source Sans Pro with an unambiguous character map.

WHY THIS EXISTS
---------------
The PDF text layer is what an ATS and a recruiter's keyword search actually read, and
it was rendering every in-word hyphen as U+2011 NON-BREAKING HYPHEN instead of an
ASCII "-". A literal search for "Solutions Architect - Professional" missed the
certification; so did "end-to-end", "cloud-native", "AI-driven", and the rest.

The cause is in the font, not in the sources - no .tex file contains a U+2011:

  Source Sans Pro's cmap maps FOUR codepoints onto the single glyph named `hyphen`:
  U+002D, U+00AD, U+2010 and U+2011. xdvipdfmx builds the PDF's /ToUnicode table by
  inverting that cmap, and where several codepoints share one glyph it keeps the last
  one it walks past - the highest. So glyph `hyphen` (GID 0x4FF) was recorded as
  U+2011 and every hyphen in the body text decoded as a non-breaking hyphen.

  Roboto is unaffected and is why the header's phone number stayed ASCII: it maps
  only U+002D onto `hyphen`, so the inversion is unambiguous.

Dropping the package's `opentype` option was tried first and is a no-op: the package
loads the OTFs under XeTeX whatever that option says, and the rebuilt PDF was
identical. Rewriting /ToUnicode in the finished PDF was rejected - it fixes the
artifact and leaves the toolchain still emitting the defect.

This is the same defect class as the small-cap "i" documented in resume/awesome-cv.cls,
and it takes the same remedy: make the text layer correct by construction rather than
rely on a mapping the font happens to get right.

WHAT IT DOES
------------
Copies the upstream OTFs into resume/fonts/ with the redundant cmap entries removed,
so each patched glyph is reachable from exactly one codepoint and the inversion has
only one answer. Only the cmap changes - the outlines, widths and kerning are the
upstream bytes, so the typeset page is identical and the one-page fit cannot move.

  hyphen  U+002D, U+00AD, U+2010, U+2011  ->  U+002D

ONLY `hyphen`. The other seven ambiguous glyphs are left alone, and the two that were
tried and reverted are the reason this list is per-glyph reasoning rather than a rule:

  `space` carries U+0020, U+0009, U+000D, U+00A0 and U+00CA, so by the "it picks the
  highest" story it should have decoded as U+00CA. It does not - it already decodes as
  U+0020. Patching it fixed nothing and broke something: dropping U+00A0 left the real
  non-breaking space in the google-applied-ai rendition with no glyph to render, so the
  character was silently deleted from the page and the text layer both. Caught only by
  diffing the rebuilt text against a control build.

  `quoteright` carries U+02BC and U+2019, and there the HIGHER codepoint is the correct
  answer. A blanket "keep the lowest" rule would corrupt the one apostrophe in the
  resume.

So the inversion rule is not simply "highest wins", and this file must not be extended
by pattern-matching on that assumption. Add a glyph here only with a control build
showing the text layer is wrong before and right after.

USAGE
-----
    py tools/patch_font_cmap.py [--source-dir DIR] [--check]

Run it only when the vendored fonts need regenerating. The output is committed, so a
normal build never invokes it. --check re-verifies the committed files in place and
is what tools/check_resume.py leans on staying true.

Needs fonttools (see requirements.txt). The upstream OTFs come from the Tectonic
bundle cache by default, which is where the build already gets them.
"""

from __future__ import annotations

import argparse
import glob
import os
import shutil
import sys

from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "resume", "fonts")

# The faces resume/hardening.tex names. fontspec resolves all four faces of a family
# eagerly, so a family's Semibold must be present even when nothing bold-in-light is
# typeset - dropping it fails the build rather than falling back.
FACES = [
    "Regular", "RegularIt", "Bold", "BoldIt",
    "Light", "LightIt", "Semibold", "SemiboldIt",
]

# glyph name -> the single codepoint it should remain reachable from.
# See the module docstring: this list is per-glyph reasoning, not a rule to extend.
KEEP = {
    "hyphen": 0x002D,
}


def source_dir(explicit=None):
    if explicit:
        return explicit
    pattern = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "TectonicProject", "Tectonic", "cache", "bundles", "data", "*",
        "SourceSansPro-Regular.otf",
    )
    hits = sorted(glob.glob(pattern))
    if not hits:
        sys.exit(
            "Could not find the upstream Source Sans Pro OTFs in the Tectonic bundle "
            "cache. Build the resume once so Tectonic fetches them, or pass "
            "--source-dir explicitly."
        )
    return os.path.dirname(hits[-1])


def ambiguous(font):
    """Codepoints that must be dropped for the KEEP glyphs, per cmap subtable."""
    drops = []
    for table in font["cmap"].tables:
        for cp, name in list(table.cmap.items()):
            if name in KEEP and cp != KEEP[name]:
                drops.append((table, cp, name))
    return drops


def patch(src, dst):
    font = TTFont(src)
    drops = ambiguous(font)
    # Several cmap subtables (format 4 and format 12) can share one backing dict, so a
    # delete through one is already visible through the next. Guard rather than assume.
    for table, cp, _name in drops:
        table.cmap.pop(cp, None)
    font.save(dst)
    font.close()
    return sorted({(name, cp) for _t, cp, name in drops})


def verify(path):
    """Every KEEP glyph present in the file is reachable from exactly one codepoint."""
    font = TTFont(path)
    try:
        problems = []
        for table in font["cmap"].tables:
            for cp, name in table.cmap.items():
                if name in KEEP and cp != KEEP[name]:
                    problems.append("%s reachable from U+%04X" % (name, cp))
        return problems
    finally:
        font.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", help="directory holding the upstream SourceSansPro-*.otf")
    ap.add_argument("--check", action="store_true",
                    help="verify the committed fonts instead of regenerating them")
    args = ap.parse_args()

    if args.check:
        failed = False
        for face in FACES:
            path = os.path.join(DEST, "SourceSansPro-%s.otf" % face)
            if not os.path.exists(path):
                print("MISSING %s" % path)
                failed = True
                continue
            for problem in verify(path):
                print("FAIL %s: %s" % (os.path.basename(path), problem))
                failed = True
        if not failed:
            print("OK   %d vendored faces have an unambiguous cmap" % len(FACES))
        return 1 if failed else 0

    src_dir = source_dir(args.source_dir)
    if not os.path.isdir(DEST):
        os.makedirs(DEST)
    print("source: %s" % src_dir)
    for face in FACES:
        name = "SourceSansPro-%s.otf" % face
        src = os.path.join(src_dir, name)
        if not os.path.exists(src):
            sys.exit("missing upstream face: %s" % src)
        dst = os.path.join(DEST, name)
        dropped = patch(src, dst)
        detail = ", ".join("%s U+%04X" % (n, c) for n, c in dropped) or "nothing to drop"
        print("  %-32s %s" % (name, detail))
    print("wrote %d faces to resume/fonts/" % len(FACES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
