"""Fail the build when the committed resume PDF no longer matches a fresh build.

`Certificates/Freddy_Shaikh_Resume.pdf` is a tracked binary because the site deploy
syncs the git tree straight to S3 - nothing in that pipeline compiles LaTeX, so the
file cannot simply be generated at deploy time without breaking the published URL.
Tracking it means it can fall behind `resume/` without anyone noticing, which is what
this check exists to stop. It ran behind twice on 2026-08-14 alone.

Byte comparison is not available: xelatex emits a byte-different PDF on every run even
with SOURCE_DATE_EPOCH pinned, so a hash check would fail on every build and teach
everyone to ignore it. Instead this compares what a reader actually sees:

  1. Page count      - a one-page resume that built to two pages is the loudest drift.
  2. Text layer      - normalised extracted text, per page. Catches stale wording, a
                       dropped certification, an un-cascaded edit.
  3. Ink geometry    - rasterised blank-pixel-row counting for the top margin, the
                       bottom margin and the total content height. Catches spacing and
                       layout drift that leaves the words identical. Rasterised rather
                       than block bounding boxes on purpose: a block box stops at the
                       last line's descender and hides exactly this class of change.

Channel 3 is opt-in via --check-geometry, and deliberately NOT used in CI. Measured on
2026-08-14: the GitHub runner's TeX Live and the local install compile identical sources
and identical embedded fonts into layouts that differ by 55.2pt, accumulating in steps at
entry boundaries. Text and page count agree exactly. So geometry is only a valid signal
when both PDFs come from the same toolchain - comparing a runner build against a locally
built commit would fail every run and be ignored within a week. Use --check-geometry from
tools/build-resume.ps1, where both sides are local; leave it off in the workflow.

Usage:
    py tools/check_resume_drift.py <fresh.pdf> <committed.pdf> [--check-geometry]

Exits non-zero and prints every difference. Silence means the committed copy is current.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pymupdf

# Rasterisation density for the ink profile. High enough that a 1pt shift is several
# pixels, low enough to stay fast in CI.
DPI = 300

# A pixel darker than this counts as ink. Anti-aliasing puts genuine edge pixels well
# below it, while JPEG-ish noise in an embedded image stays above.
INK_THRESHOLD = 245

# Allowed drift, in points, on each measured margin and on content height. A rebuild of
# unchanged sources reproduces these exactly; the tolerance only absorbs a renderer
# patch release, not an actual layout change.
GEOMETRY_TOLERANCE_PT = 1.0


def normalise_text(text: str) -> str:
    """Collapse whitespace so line-wrap noise is not reported as a content change."""
    return re.sub(r"\s+", " ", text).strip()


def ink_profile(page: pymupdf.Page) -> tuple[float, float, float] | None:
    """Return (top margin, bottom margin, content height) in points, or None if blank.

    Measured by scanning rasterised rows for ink rather than by reading text block
    boxes, so a descender, a rule, or a graphic all count.
    """
    pix = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
    scale = DPI / 72.0
    rows = pix.height
    stride = pix.stride
    data = pix.samples

    first = last = None
    for y in range(rows):
        if min(data[y * stride : y * stride + pix.width]) < INK_THRESHOLD:
            if first is None:
                first = y
            last = y
    if first is None:
        return None
    return (first / scale, (rows - 1 - last) / scale, (last - first + 1) / scale)


def compare(fresh: Path, committed: Path, check_geometry: bool) -> list[str]:
    problems: list[str] = []

    for path in (fresh, committed):
        if not path.exists():
            return [f"{path}: not found; cannot compare against a fresh build"]

    a = pymupdf.open(fresh)
    b = pymupdf.open(committed)

    if a.page_count != b.page_count:
        return [
            f"{committed} is stale: {b.page_count} page(s), a fresh build of resume/ "
            f"produces {a.page_count}. Run tools/build-resume.ps1 and commit the result."
        ]

    for pno in range(a.page_count):
        pa, pb = a[pno], b[pno]

        ta = normalise_text(pa.get_text())
        tb = normalise_text(pb.get_text())
        if ta != tb:
            problems.append(
                f"{committed} page {pno + 1}: text layer differs from a fresh build of "
                f"resume/. The committed PDF does not carry the current sources."
            )
            for line in _first_difference(tb, ta):
                problems.append(f"    {line}")

        if not check_geometry:
            continue

        ga, gb = ink_profile(pa), ink_profile(pb)
        if ga is None or gb is None:
            if ga != gb:
                problems.append(f"{committed} page {pno + 1}: one copy is blank, the other is not")
            continue

        for label, va, vb in zip(("top margin", "bottom margin", "content height"), ga, gb):
            if abs(va - vb) > GEOMETRY_TOLERANCE_PT:
                problems.append(
                    f"{committed} page {pno + 1}: {label} is {vb:.2f}pt but a fresh "
                    f"build gives {va:.2f}pt ({va - vb:+.2f}pt). Layout drift - the "
                    f"committed PDF predates a spacing change in resume/."
                )

    if problems:
        problems.append(
            "Fix: rebuild with tools/build-resume.ps1 and commit "
            "Certificates/Freddy_Shaikh_Resume.pdf alongside the resume/ change."
        )
    return problems


def _first_difference(committed: str, fresh: str) -> list[str]:
    """Show the first place the two text layers diverge, with a little context."""
    limit = min(len(committed), len(fresh))
    i = next((i for i in range(limit) if committed[i] != fresh[i]), limit)
    start = max(0, i - 40)
    return [
        f"committed: ...{committed[start:i + 60]}...",
        f"fresh:     ...{fresh[start:i + 60]}...",
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fresh", type=Path, help="PDF just built from resume/")
    ap.add_argument("committed", type=Path, help="tracked copy the site deploy publishes")
    ap.add_argument(
        "--check-geometry",
        action="store_true",
        help="also compare ink geometry. Only valid when both PDFs were built by the "
        "same toolchain; see the module docstring.",
    )
    args = ap.parse_args()

    problems = compare(args.fresh, args.committed, args.check_geometry)
    if problems:
        print(f"Resume drift check FAILED ({len(problems)} finding(s)):", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1

    print("Resume drift check passed: the committed PDF matches a fresh build.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
