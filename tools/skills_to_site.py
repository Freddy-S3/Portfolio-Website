"""Cascade the public harness's skills into the portfolio site's harness simulator.

The harness itself (~/Repo/agent-agnostic-harness) is a protected location and is not read
directly. Its public mirror (github.com/Freddy-S3/agent-agnostic-harness) is the
single source of truth for this generator: it is the version Freddy already
publishes, so nothing private can leak through the site.

Reads each skill's SKILL.md frontmatter plus the "Native Skills" routing table in
instructions/AGENTS.md, and writes skills.data.json. index.html embeds that JSON
verbatim inside a <script id="skills-data"> block (between markers, same pattern
as tools/resume_to_site.py) so the page renders the catalog and simulator from data
instead of hand-transcribed markup.

Usage:
    py tools/skills_to_site.py            # clone/refresh the mirror, write skills.data.json + index.html
    py tools/skills_to_site.py --check    # fail if index.html is out of date
    py tools/skills_to_site.py --no-fetch # reuse whatever is already in .harness-cache
"""

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".harness-cache", "agent-agnostic-harness")
REMOTE = "https://github.com/Freddy-S3/agent-agnostic-harness.git"
SKILLS_DIR = os.path.join(CACHE, "skills")
AGENTS_MD = os.path.join(CACHE, "instructions", "AGENTS.md")
INDEX = os.path.join(ROOT, "index.html")
DATA_OUT = os.path.join(ROOT, "skills.data.json")

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "with", "when",
    "use", "uses", "using", "is", "are", "it", "this", "that", "as", "at", "by",
    "be", "into", "from", "not", "any", "one", "so", "than", "then", "will",
    "own", "its", "their", "your", "you", "or", "no", "over", "across", "per",
}


def refresh_cache():
    # A cache directory that is not a checkout of REMOTE is discarded rather than reused.
    # Testing only for a .git subdirectory answers "does this look like a clone", not "is
    # this a clone of the repo we want", and the two differ exactly when the harness repo
    # is renamed: the old directory survives under the old name, a fresh one is created
    # under the new name, and any half-populated leftover makes `git clone` fail with
    # "destination path already exists" on every subsequent run.
    if os.path.isdir(CACHE) and _cache_tracks_remote():
        subprocess.run(["git", "-C", CACHE, "pull", "--ff-only"], check=True)
        return
    if os.path.isdir(CACHE):
        shutil.rmtree(CACHE, onerror=_drop_readonly)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", REMOTE, CACHE], check=True)


def _cache_tracks_remote():
    """True only when CACHE is a git checkout whose origin is REMOTE."""
    try:
        url = subprocess.run(
            ["git", "-C", CACHE, "remote", "get-url", "origin"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return False
    return url.rstrip("/").removesuffix(".git") == REMOTE.rstrip("/").removesuffix(".git")


def _drop_readonly(func, path, _exc):
    """git packs files read-only on Windows, which blocks rmtree."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


# ------------------------------------------------------------ frontmatter parsing

FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.S)


def parse_skill(path):
    with open(path, encoding="utf-8") as handle:
        source = handle.read()
    match = FRONTMATTER.match(source)
    if not match:
        return None
    fm_text, body = match.groups()
    fields = {}
    for line in fm_text.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip('"')
        fields[key.strip()] = value
    heading = re.search(r"^#\s+(.+)$", body, re.M)
    return {
        "name": fields.get("name", ""),
        "title": heading.group(1).strip() if heading else fields.get("name", ""),
        "description": fields.get("description", ""),
        "user_invocable": fields.get("user-invocable", "").lower() == "true",
        "auto_invocable": fields.get("disable-model-invocation", "").lower() != "true",
    }


def load_skills():
    skills = []
    for entry in sorted(os.listdir(SKILLS_DIR)):
        skill_md = os.path.join(SKILLS_DIR, entry, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue
        skill = parse_skill(skill_md)
        if skill and skill["name"]:
            skills.append(skill)
    return skills


def load_routing_table():
    with open(AGENTS_MD, encoding="utf-8") as handle:
        text = handle.read()
    section = re.search(r"## Native Skills\n\n(.*?)\n\n##", text, re.S)
    table = {}
    if not section:
        return table
    for line in section.group(1).splitlines():
        row = re.match(r"\|\s*(.+?)\s*\|\s*`/(.+?)`\s*\|", line)
        if row:
            task_label, command = row.groups()
            table[command] = task_label
    return table


def tokenize(text):
    words = re.findall(r"[a-z][a-z0-9'\-]{2,}", text.lower())
    return sorted({w for w in words if w not in STOPWORDS})


def build():
    skills = load_skills()
    routing = load_routing_table()
    data = []
    for skill in skills:
        data.append({
            "name": skill["name"],
            "command": "/" + skill["name"],
            "title": skill["title"],
            "description": skill["description"],
            "task": routing.get(skill["name"], ""),
            "userInvocable": skill["user_invocable"],
            "autoInvocable": skill["auto_invocable"],
            "keywords": tokenize(skill["description"] + " " + routing.get(skill["name"], "")),
        })
    data.sort(key=lambda s: (0 if s["task"] else 1, s["name"]))
    return data


def render_data_script(data):
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    return '<script id="skills-data" type="application/json">\n%s\n</script>' % payload


def inject(page, data):
    marker = re.compile(
        r"([ \t]*)(<!-- skills:data:start -->)(.*?)([ \t]*)(<!-- skills:data:end -->)",
        re.S,
    )
    match = marker.search(page)
    if not match:
        raise SystemExit("index.html is missing the skills:data markers")
    indent = match.group(1)
    rendered = "\n".join(indent + line for line in render_data_script(data).splitlines())
    return (
        page[: match.start()]
        + indent + match.group(2) + "\n"
        + rendered + "\n"
        + indent + match.group(5)
        + page[match.end():]
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit non-zero if index.html is out of date")
    parser.add_argument("--no-fetch", action="store_true", help="reuse the existing .harness-cache checkout")
    args = parser.parse_args()

    if not args.no_fetch:
        refresh_cache()

    data = build()
    with open(INDEX, encoding="utf-8") as handle:
        original = handle.read()
    updated = inject(original, data)

    if args.check:
        ok = updated == original
        print("index.html is up to date with the harness mirror" if ok else
              "index.html is out of date; run: py tools/skills_to_site.py")
        return 0 if ok else 1

    with open(DATA_OUT, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    if updated != original:
        with open(INDEX, "w", encoding="utf-8", newline="") as handle:
            handle.write(updated)
        print("index.html updated from the harness mirror (%d skills)" % len(data))
    else:
        print("index.html already matches the harness mirror")
    return 0


if __name__ == "__main__":
    sys.exit(main())
