"""Fail the resume build when empty content would render as blank space.

Four independent checks, because each one catches a different way the bug shows up:

  1. Source scan   - an empty required argument in the .tex sources
                     (\\cvskill{}{...}, \\item {}, \\cvhonor{}{...}), and any row-based
                     table left on awesome-cv's vertically centred m{} columns.
  2. Log scan    - "BLANK ENTRY SKIPPED" warnings raised by resume/hardening.tex,
                     which catch empties that survive a macro expansion the source
                     scan cannot see.
  3. PDF scan      - whitespace-only text blocks, oversized vertical gaps, near-empty
                     final pages, and rows whose label has drifted off the baseline of
                     its own content. That last one is the original Skills bug:
                     awesome-cv's m{} column vertically centres a wrapped cell, pushing
                     the label into the middle and opening a blank band beside it.
                     This is the backstop: it does not care *why* the space is there.

Usage:
    py tools/check_resume.py <pdf> [--sources DIR ...] [--log FILE] [--max-pages N]

Exits non-zero and prints every failure. Silence means the PDF is clean.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pymupdf

# Gap, in points, between the bottom of one text block and the top of the next that
# is treated as suspicious. A section heading opens ~15pt; anything beyond 26pt is a
# hole, not layout.
GAP_LIMIT_PT = 26.0

# Two side-by-side lines sharing a table row must sit on the same top edge. More than
# this much drift means the row is vertically centred against a wrapped neighbour.
ROW_DRIFT_LIMIT_PT = 2.0

# Only compare lines that genuinely overlap vertically, or every adjacent pair of rows
# reads as a mismatch.
ROW_OVERLAP_RATIO = 0.5

# A skills row that wraps and leaves a stub on the last line reads as a hole in the
# section even when the alignment is correct. Flag a final wrap line narrower than this
# fraction of the cell.
ORPHAN_WRAP_RATIO = 0.25

# Macros whose listed argument positions (1-based) must not be blank.
GUARDED_MACROS = {
    "cvskill": (1, 2),
    "cvhonor": (1,),
    "cvitemx": (1,),
}


def strip_comments(text: str) -> str:
    """Drop LaTeX comments so commented-out entries are not reported as empty."""
    out = []
    for line in text.splitlines():
        idx = 0
        while True:
            idx = line.find("%", idx)
            if idx == -1:
                out.append(line)
                break
            if idx > 0 and line[idx - 1] == "\\":
                idx += 1
                continue
            out.append(line[:idx])
            break
    return "\n".join(out)


def read_args(text: str, pos: int, count: int):
    """Read `count` brace groups starting at `pos`. Returns (args, end) or None."""
    args = []
    i = pos
    for _ in range(count):
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text) or text[i] != "{":
            return None
        depth, start = 0, i
        while i < len(text):
            if text[i] == "{" and text[i - 1] != "\\":
                depth += 1
            elif text[i] == "}" and text[i - 1] != "\\":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        if i >= len(text):
            return None
        args.append(text[start + 1 : i])
        i += 1
    return args, i


def check_sources(dirs: list[Path]) -> list[str]:
    problems = []
    files = sorted({f for d in dirs for f in d.rglob("*.tex")})
    for path in files:
        text = strip_comments(path.read_text(encoding="utf-8"))

        for macro, required in GUARDED_MACROS.items():
            for m in re.finditer(r"\\" + macro + r"\b", text):
                got = read_args(text, m.end(), max(required))
                if got is None:
                    continue
                args, _ = got
                for n in required:
                    if not args[n - 1].strip():
                        line = text.count("\n", 0, m.start()) + 1
                        problems.append(
                            f"{path}:{line}: \\{macro} argument {n} is empty"
                        )

        # A bare \item with an empty or whitespace-only group.
        for m in re.finditer(r"\\item\s*\{\s*\}", text):
            line = text.count("\n", 0, m.start()) + 1
            problems.append(f"{path}:{line}: \\item has empty content")

    return problems


# Tables that must be rebuilt on top-aligned p{} columns in resume/hardening.tex.
# awesome-cv builds both on m{} columns, which vertically centre every cell in a row
# the moment one of them wraps. The PDF scan below only catches this once a cell
# actually wraps, so shortening the content silently removes the regression guard;
# this check holds the fix in place regardless of the content of the day.
TOP_ALIGNED_TABLES = ("cvskills", "cvhonors")

# awesome-cv's vertically centred column types. None may appear in a rebuilt table.
CENTRED_COLUMN_TYPES = ("L", "C", "R")


def check_alignment_overrides(dirs: list[Path]) -> list[str]:
    """Verify every row-based table is rebuilt on top-aligned columns."""
    # --sources points at a rendition's content directory; hardening.tex sits above it.
    files = set()
    for d in dirs:
        for base in [d, *d.resolve().parents]:
            found = sorted(base.glob("hardening.tex"))
            if found:
                files.update(found)
                break
    files = sorted(files)
    if not files:
        return ["hardening.tex not found; cannot verify row alignment overrides"]

    problems = []
    for path in files:
        text = strip_comments(path.read_text(encoding="utf-8"))
        for table in TOP_ALIGNED_TABLES:
            m = re.search(
                r"\\renewenvironment\{" + table + r"\}(.*?)\\end\{tabular\*\}",
                text,
                re.S,
            )
            if m is None:
                problems.append(
                    f"{path}: {table} is not rebuilt on top-aligned columns; "
                    "awesome-cv's m{} columns centre a row whose cell wraps"
                )
                continue
            spec = re.search(r"\\begin\{tabular\*\}.*?\}\{(.*?)\}\s*$", m.group(1), re.S | re.M)
            if spec is None:
                problems.append(f"{path}: cannot read the column spec of {table}")
                continue
            for col in CENTRED_COLUMN_TYPES:
                if re.search(r"(?<![A-Za-z])" + col + r"\{", spec.group(1)):
                    problems.append(
                        f"{path}: {table} still uses the vertically centred "
                        f"{col}{{}} column type"
                    )
    return problems


def check_log(log: Path) -> list[str]:
    if not log.exists():
        return [f"{log}: log not found; cannot verify blank-entry warnings"]
    text = log.read_text(encoding="utf-8", errors="replace")
    return [
        f"{log}: {m.group(0).strip()}"
        for m in re.finditer(r"BLANK ENTRY SKIPPED:[^\n]*", text)
    ]


def check_row_alignment(page, pno: int, pdf: Path) -> list[str]:
    """Flag misaligned label/value rows, and value cells that wrap to a stub line.

    Both are Skills-table failure modes. Only blocks that actually sit to the right of
    a label are examined, so ordinary body bullets ending on a short line are ignored.
    """
    blocks = [b for b in page.get_text("dict")["blocks"] if b["type"] == 0]
    lines = [line for block in blocks for line in block["lines"]]

    problems = []
    value_lines = []
    for left in lines:
        lx0, ly0, lx1, ly1 = left["bbox"]
        for right in lines:
            if right is left:
                continue
            rx0, ry0, rx1, ry1 = right["bbox"]
            if lx1 > rx0:  # not side by side
                continue
            overlap = min(ly1, ry1) - max(ly0, ry0)
            if overlap <= ROW_OVERLAP_RATIO * min(ly1 - ly0, ry1 - ry0):
                continue  # different rows
            value_lines.append(right)

            drift = abs(ly0 - ry0)
            if drift > ROW_DRIFT_LIMIT_PT:
                label = "".join(s["text"] for s in left["spans"])[:40]
                value = "".join(s["text"] for s in right["spans"])[:40]
                problems.append(
                    f"{pdf}: p{pno}: row label {label!r} sits {drift:.1f}pt off its "
                    f"content {value!r} - wrapped cell is vertically centred"
                )

    # A wrapped skills value continues in its own block on the following line, at the
    # same left edge as the value column. When that continuation is a lone stub word it
    # leaves a near-empty line across the section.
    for value_line in value_lines:
        vx0, _, vx1, vy1 = value_line["bbox"]
        cell_width = vx1 - vx0
        if cell_width <= 0:
            continue
        for block in blocks:
            if len(block["lines"]) != 1:
                continue
            bx0, by0, bx1, _ = block["bbox"]
            if abs(bx0 - vx0) > 2.0 or not (0 <= by0 - vy1 < 6.0):
                continue  # not the line directly below, in the same column
            stub = bx1 - bx0
            if stub < ORPHAN_WRAP_RATIO * cell_width:
                text = "".join(s["text"] for s in block["lines"][0]["spans"])[:40]
                problems.append(
                    f"{pdf}: p{pno}: skills value wraps to a stub line {text!r} "
                    f"({stub / cell_width:.0%} of the cell) - shorten the entry"
                )

    return problems


# A lowercase letter sandwiched inside an uppercase run, e.g. "SENiOR", "ENGiNEER".
# Headings used \scshape until 2026-08-11; Source Sans Pro's small-cap i maps back to
# lowercase through its ToUnicode table while its other small caps map to uppercase, so
# the text layer an ATS reads said "SENiOR FULL STACK SOFTWARE ENGiNEER" and no exact
# keyword match on the title could ever land. The class now renders real uppercase.
# This guard exists so the regression is caught at build time rather than by noticing
# months of silence from recruiters.
MIXED_CASE_RUN = re.compile(r"[A-Z]{2,}[a-z][A-Z]{2,}")

# Codepoints that render as an ASCII character but do not decode as one, so an exact
# keyword match silently misses. Same failure shape as the small-caps bug above: the
# page looks perfect and only the text layer is wrong.
#
# Until 2026-08-14 the PDF carried 38 of these against 3 real hyphens, because Source
# Sans Pro's cmap maps U+002D, U+00AD, U+2010 and U+2011 onto the one `hyphen` glyph
# and xdvipdfmx keeps the highest codepoint when it inverts that map for /ToUnicode.
# "Solutions Architect - Professional", "end-to-end", "cloud-native" and the rest all
# read as U+2011 to anything doing a literal match. Fixed at source by vendoring
# cmap-patched faces - see tools/patch_font_cmap.py and resume/hardening.tex.
#
# En dash and em dash are deliberately NOT listed. They are intentional typography
# rather than invisible substitutes for an ASCII character, and flagging them would
# make this guard fire on correct output.
ASCII_LOOKALIKES = {
    "‐": "HYPHEN (use ASCII '-')",
    "‑": "NON-BREAKING HYPHEN (use ASCII '-')",
    "‒": "FIGURE DASH (use ASCII '-')",
    "­": "SOFT HYPHEN (invisible; use ASCII '-')",
    " ": "NO-BREAK SPACE (use a plain space)",
}
# Deliberately NOT listed: U+00CA. It doubles as a legacy Mac no-break space, but it is
# also the letter E-circumflex, and failing a build over a real letter in a real name is
# a worse outcome than the case it would catch.


def check_text_layer(pdf: Path, doc) -> list[str]:
    """Fail on glyph-mapping corruption in the extracted text, not on the rendered page.

    Renders identically either way, which is exactly why this needs a machine check.
    """
    text = "".join(page.get_text() for page in doc)
    problems = []

    hits = sorted(set(MIXED_CASE_RUN.findall(text)))
    if hits:
        problems.append(
            f"{pdf}: text layer has lowercase letters inside uppercase words "
            f"({', '.join(hits[:6])}) - a font's small-caps ToUnicode mapping is "
            "corrupting what an ATS reads; render real uppercase instead"
        )

    for char, label in sorted(ASCII_LOOKALIKES.items()):
        count = text.count(char)
        if not count:
            continue
        sample = sorted({w for w in text.split() if char in w})[:4]
        problems.append(
            f"{pdf}: text layer has {count} x U+{ord(char):04X} {label} "
            f"{'(' + ', '.join(sample) + ') ' if sample else ''}"
            "- renders like ASCII but will not match an exact keyword search; "
            "regenerate the vendored fonts with tools/patch_font_cmap.py"
        )

    return problems


def check_pdf(pdf: Path, max_pages: int | None, allow_orphan_page: bool) -> list[str]:
    problems = []
    doc = pymupdf.open(pdf)

    problems += check_text_layer(pdf, doc)

    if max_pages is not None and doc.page_count > max_pages:
        problems.append(
            f"{pdf}: {doc.page_count} pages, expected at most {max_pages}"
        )
    if doc.page_count == 0:
        return problems + [f"{pdf}: no pages"]

    for pno, page in enumerate(doc, start=1):
        blocks = page.get_text("blocks")
        for b in blocks:
            if b[4] and not b[4].strip() and (b[3] - b[1]) > 4:
                problems.append(f"{pdf}: p{pno}: whitespace-only text block at y={b[1]:.0f}")

        problems += check_row_alignment(page, pno, pdf)

        laid = sorted((b for b in blocks if b[4].strip()), key=lambda b: b[1])
        for prev, cur in zip(laid, laid[1:]):
            gap = cur[1] - prev[3]
            if gap > GAP_LIMIT_PT:
                problems.append(
                    f"{pdf}: p{pno}: {gap:.0f}pt vertical hole after "
                    f"{prev[4].strip().splitlines()[0][:40]!r}"
                )

        # A page carrying almost nothing is the orphan-section symptom.
        if allow_orphan_page:
            continue
        if pno == doc.page_count and doc.page_count > 1:
            chars = sum(len(b[4].strip()) for b in blocks)
            if chars < 120:
                problems.append(
                    f"{pdf}: p{pno}: near-empty final page ({chars} chars) - "
                    "a section orphaned across the page break"
                )

    doc.close()
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--sources", type=Path, nargs="*", default=[])
    ap.add_argument("--log", type=Path)
    ap.add_argument("--max-pages", type=int)
    ap.add_argument(
        "--allow-orphan-page",
        action="store_true",
        help=(
            "Permit a near-empty final page. Used only by the canonical resume build, "
            "whose one-page layout is pending a rendition choice."
        ),
    )
    args = ap.parse_args()

    problems = []
    if args.sources:
        problems += check_sources(args.sources)
        problems += check_alignment_overrides(args.sources)
    if args.log:
        problems += check_log(args.log)
    problems += check_pdf(args.pdf, args.max_pages, args.allow_orphan_page)

    if problems:
        print(f"FAIL {args.pdf.name}", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1

    print(f"OK   {args.pdf.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
