"""Cascade the LaTeX resume in resume/ into index.html.

The .tex files are the single source of truth. Commented-out lines are skipped,
so toggling a bullet with % removes it from both the PDF and the website.

Usage:
    py tools/resume_to_site.py            # rewrite index.html, write resume.data.json
    py tools/resume_to_site.py --check    # fail if index.html is out of date
"""

import argparse
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESUME_DIR = os.path.join(ROOT, "resume", "resume")
INDEX = os.path.join(ROOT, "index.html")
ASSET_MAP = os.path.join(ROOT, "tools", "asset-map.json")
DATA_OUT = os.path.join(ROOT, "resume.data.json")


# ---------------------------------------------------------------- LaTeX parsing

def strip_comments(source):
    """Drop everything after an unescaped % on each line."""
    out = []
    for line in source.splitlines():
        cut = None
        i = 0
        while i < len(line):
            if line[i] == "\\":
                i += 2
                continue
            if line[i] == "%":
                cut = i
                break
            i += 1
        out.append(line if cut is None else line[:cut])
    return "\n".join(out)


def read_group(source, start):
    """Read a balanced {...} group beginning at or after index `start`.

    Returns (contents, index_after_group) or (None, start) if no group follows.
    """
    i = start
    while i < len(source) and source[i].isspace():
        i += 1
    if i >= len(source) or source[i] != "{":
        return None, start
    depth = 0
    begin = i
    while i < len(source):
        c = source[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return source[begin + 1:i], i + 1
        i += 1
    raise ValueError("unbalanced braces starting at offset %d" % begin)


def read_macros(source, name, arity):
    """Yield the argument lists of every \\name{...}x`arity` in `source`."""
    pattern = re.compile(r"\\" + name + r"(?![a-zA-Z])")
    pos = 0
    while True:
        match = pattern.search(source, pos)
        if not match:
            return
        i = match.end()
        args = []
        for _ in range(arity):
            arg, i = read_group(source, i)
            if arg is None:
                break
            args.append(arg)
        pos = i if args else match.end()
        if len(args) == arity:
            yield args


def read_env(source, name):
    """Return the body of the first \\begin{name}...\\end{name} environment."""
    match = re.search(
        r"\\begin\{" + name + r"\}(.*?)\\end\{" + name + r"\}", source, re.S
    )
    return match.group(1) if match else ""


# ------------------------------------------------------------ text conversion

REPLACEMENTS = [
    (r"\\&", "&"),
    (r"\\%", "%"),
    (r"\\_", "_"),
    (r"\\#", "#"),
    (r"\\\$", "$"),
    (r"\\ ", " "),
    (r"\\,", " "),
    (r"\\quad", " "),
    (r"\\textbar", "|"),
    (r"\\LaTeX", "LaTeX"),
]

HREF = re.compile(r"\\href\{(.*?)\}\{(.*?)\}", re.S)


def to_text(raw):
    """Flatten a LaTeX fragment to plain text, keeping link targets aside."""
    text, _ = to_text_and_links(raw)
    return text


def to_text_and_links(raw):
    """Return (plain text, [(url, label), ...]) for a LaTeX fragment."""
    links = []

    def capture(match):
        links.append((match.group(1).strip(), match.group(2).strip()))
        return match.group(2)

    text = HREF.sub(capture, raw)
    for pattern, repl in REPLACEMENTS:
        text = re.sub(pattern, repl, text)
    text = re.sub(r"\\[a-zA-Z]+\*?", "", text)      # any remaining commands
    text = text.replace("{", "").replace("}", "")
    text = text.replace("~", " ").replace("\u2011", "-")
    text = re.sub(r"(?<!-)--(?!-)", "\u2013", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text, links


def items_of(body):
    """Plain-text bullets from a cvitems environment."""
    return [to_text(arg[0]) for arg in read_macros(read_env(body, "cvitems"), "item", 1)]


# ------------------------------------------------------------------ extraction

def split_skills(text):
    """Split a skillset on commas, ignoring commas inside (parentheses)."""
    parts, depth, current = [], 0, []
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    parts.append("".join(current))
    return [part.strip() for part in parts if part.strip()]


def load(name):
    with open(os.path.join(RESUME_DIR, name), encoding="utf-8") as handle:
        return strip_comments(handle.read())


def extract():
    summary = to_text(read_env(load("summary.tex"), "cvparagraph"))

    skills = [
        {"category": to_text(category), "items": split_skills(to_text(items))}
        for category, items in read_macros(load("skills.tex"), "cvskill", 2)
    ]

    experience = []
    for title, org, location, dates, body in read_macros(load("experience.tex"), "cventry", 5):
        experience.append({
            "title": to_text(title),
            "organization": to_text(org),
            "location": to_text(location),
            "dates": to_text(dates),
            "bullets": items_of(body),
        })

    education = []
    for degree, school, location, dates, body in read_macros(load("education.tex"), "cventry", 5):
        education.append({
            "degree": to_text(degree),
            "school": to_text(school),
            "location": to_text(location),
            "dates": to_text(dates),
            "bullets": items_of(body),
        })

    awards = []
    for award, event, location, date in read_macros(load("awards.tex"), "cvhonor", 4):
        awards.append({
            "award": to_text(award),
            "event": to_text(event),
            "location": to_text(location),
            "date": to_text(date),
        })

    projects = []
    for _, name, _, _, body in read_macros(load("projects.tex"), "cventry", 5):
        title, links = to_text_and_links(name)
        title = re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()
        projects.append({
            "title": title,
            "url": links[0][0] if links else "",
            "bullets": items_of(body),
        })

    return {
        "summary": summary,
        "skills": skills,
        "experience": experience,
        "education": education,
        "awards": awards,
        "projects": projects,
    }


# ------------------------------------------------------------------- rendering

def esc(value):
    return html.escape(value, quote=True)


def asset(assets, title):
    return assets.get(title, {})


def year_of(dates):
    """'January 2025 - PRESENT' -> '2025 - present'."""
    years = re.findall(r"\b(19|20)\d{2}\b", dates)
    spans = re.findall(r"\b((?:19|20)\d{2})\b", dates)
    present = "present" if re.search(r"present", dates, re.I) else None
    if not spans:
        return dates.lower()
    if present:
        return "%s - present" % spans[0]
    if len(spans) > 1 and spans[0] != spans[-1]:
        return "%s - %s" % (spans[0], spans[-1])
    return spans[0]


def render_summary(data, assets, indent):
    paragraph = esc(data["summary"])
    return ['<p class="resume-summary">', "    " + paragraph, "</p>"]


def render_skills(data, assets, indent):
    lines = ['<div class="skill-categories">']
    for group in data["skills"]:
        lines.append('    <div class="skill-category">')
        lines.append('        <h5 class="skill-category-title">%s</h5>' % esc(group["category"]))
        lines.append('        <ul class="skill-tags">')
        for item in group["items"]:
            lines.append('            <li class="skill-tag">%s</li>' % esc(item))
        lines.append("        </ul>")
        lines.append("    </div>")
    lines.append("</div>")
    return lines


def render_timeline(data, assets, indent):
    lines = []
    entries = [(e, "fas fa-briefcase") for e in data["experience"]]
    entries += [(e, "fas fa-graduation-cap") for e in data["education"]]
    for entry, icon in entries:
        heading = entry.get("title") or entry.get("degree")
        org = entry.get("organization") or entry.get("school")
        lines.append('<div class="timeline-item">')
        lines.append('    <div class="tl-icon">')
        lines.append('        <i class="%s"></i>' % icon)
        lines.append("    </div>")
        lines.append('    <p class="tl-duration">%s</p>' % esc(year_of(entry["dates"])))
        lines.append("    <h5>%s<span> - %s</span></h5>" % (esc(heading), esc(org)))
        for bullet in entry["bullets"]:
            lines.append("    <p>")
            lines.append("        %s" % esc(bullet))
            lines.append("    </p>")
        lines.append("</div>")
    return lines


def render_card(title, image, href, icon, alt_text):
    return [
        '<div class="portfolio-item">',
        '    <div class="image">',
        '        <img src="%s" alt="%s">' % (esc(image), esc(alt_text)),
        "    </div>",
        '    <div class="hover-items">',
        "        <h3>%s</h3>" % esc(title),
        '        <div class="icons">',
        '            <a href="%s" target="_blank" class="icon">' % esc(href),
        '                <i class="%s"></i>' % esc(icon),
        "            </a>",
        "        </div>",
        "    </div>",
        "</div>",
    ]


def render_projects(data, assets, indent):
    lines = []
    for project in data["projects"]:
        meta = asset(assets, project["title"])
        lines += render_card(
            project["title"],
            meta.get("img", "img/hero.png"),
            meta.get("href") or project["url"] or "#",
            meta.get("icon", "fab fa-github"),
            project["title"],
        )
    return lines


def render_certifications(data, assets, indent):
    # The resume folds Education into the honors table to save a page, so awards.tex now
    # carries the degree as a \cvhonor row. On the site that degree already has a home in
    # the timeline (render_timeline reads education.tex), and a degree is not a
    # certification - rendered here it produced a duplicate card with a placeholder image
    # and a dead "#" link. Match on the degree title so the fold stays a resume-layout
    # decision and does not leak into the site.
    degrees = {e["degree"] for e in data["education"]}
    lines = []
    for award in data["awards"]:
        if award["award"] in degrees:
            continue
        meta = asset(assets, award["award"])
        lines += render_card(
            meta.get("label", award["award"]),
            meta.get("img", "img/hero.png"),
            meta.get("href", "#"),
            meta.get("icon", "fas fa-certificate"),
            award["award"],
        )
    return lines


RENDERERS = {
    "summary": render_summary,
    "skills": render_skills,
    "timeline": render_timeline,
    "projects": render_projects,
    "certifications": render_certifications,
}


# ------------------------------------------------------------------- injection

def inject(page, data, assets):
    missing = []
    for region, renderer in RENDERERS.items():
        marker = re.compile(
            r"([ \t]*)(<!-- resume:%s:start -->)(.*?)([ \t]*)(<!-- resume:%s:end -->)"
            % (region, region),
            re.S,
        )
        match = marker.search(page)
        if not match:
            missing.append(region)
            continue
        indent = match.group(1)
        body = renderer(data, assets, indent)
        rendered = "\n".join(indent + line for line in body)
        page = (
            page[: match.start()]
            + indent
            + match.group(2)
            + "\n"
            + rendered
            + "\n"
            + indent
            + match.group(5)
            + page[match.end():]
        )
    if missing:
        raise SystemExit("index.html is missing markers for: %s" % ", ".join(missing))
    return page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero if index.html is out of date")
    args = parser.parse_args()

    data = extract()
    with open(ASSET_MAP, encoding="utf-8") as handle:
        assets = json.load(handle)
    with open(INDEX, encoding="utf-8") as handle:
        original = handle.read()

    updated = inject(original, data, assets)

    if args.check:
        if updated != original:
            print("index.html is out of date; run: py tools/resume_to_site.py")
            return 1
        print("index.html is up to date with resume/")
        return 0

    with open(DATA_OUT, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    if updated != original:
        with open(INDEX, "w", encoding="utf-8", newline="") as handle:
            handle.write(updated)
        print("index.html updated from resume/")
    else:
        print("index.html already matches resume/")

    # Degrees folded into awards.tex are not rendered as cards (see
    # render_certifications), so they need no asset-map entry and must not warn.
    degrees = {e["degree"] for e in data["education"]}
    unmapped = sorted(
        ({a["award"] for a in data["awards"]} - degrees)
        | {p["title"] for p in data["projects"]}
    )
    unmapped = [title for title in unmapped if title not in assets]
    if unmapped:
        print("warning: no asset-map entry for: %s" % ", ".join(unmapped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
