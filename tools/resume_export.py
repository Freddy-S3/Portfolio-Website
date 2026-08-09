"""Export the LaTeX resume into formats the job boards actually accept.

None of LinkedIn, Indeed, Glassdoor, or ZipRecruiter expose a candidate-profile
write API, so this cannot push. It generates paste-ready and upload-ready
artifacts from the same .tex source the website is built from, so every channel
says the same thing.

Outputs (all under exports/):
    resume.txt        ATS-friendly plain text; what resume parsers read best
    jsonresume.json   JSON Resume standard (jsonresume.org) for tools that ingest it
    linkedin.md       Field-by-field LinkedIn content, ready to paste
    PROFILE-SYNC.md   Per-site checklist of where each artifact goes

Usage:
    py tools/resume_export.py
"""

import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from resume_to_site import extract  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "exports")

NAME = "Freddy Shaikh"
HEADLINE = "Senior Full Stack Software Engineer"
LOCATION = "Toronto, Canada"
EMAIL = "shaikhfh1@gmail.com"
PHONE = "+1 (437) 267-3291"
SITE = "https://freddyshaikh.com"
LINKEDIN = "https://www.linkedin.com/in/freddy-shaikh"
GITHUB = "https://github.com/Freddy-S3"

# LinkedIn caps these; exceeding them silently truncates on paste.
LIMITS = {"About": 2600, "Position description": 2000, "Headline": 220}


def write(name, text):
    path = os.path.join(OUT, name)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)
    print("wrote exports/%s (%d chars)" % (name, len(text)))


def rule(char="="):
    return char * 72


def build_txt(data):
    out = [NAME, HEADLINE, "%s | %s | %s" % (LOCATION, PHONE, EMAIL),
           "%s | %s | %s" % (SITE, LINKEDIN, GITHUB), "", rule(), "SUMMARY", rule(), "",
           data["summary"], ""]

    out += [rule(), "SKILLS", rule(), ""]
    for group in data["skills"]:
        out.append("%s: %s" % (group["category"], ", ".join(group["items"])))
    out.append("")

    out += [rule(), "EXPERIENCE", rule(), ""]
    for job in data["experience"]:
        out.append("%s" % job["title"])
        out.append("%s | %s | %s" % (job["organization"], job["location"], job["dates"]))
        for bullet in job["bullets"]:
            out.append("- %s" % bullet)
        out.append("")

    if data["projects"]:
        out += [rule(), "PROJECTS", rule(), ""]
        for project in data["projects"]:
            out.append(project["title"] + (" (%s)" % project["url"] if project["url"] else ""))
            for bullet in project["bullets"]:
                out.append("- %s" % bullet)
            out.append("")

    out += [rule(), "CERTIFICATIONS", rule(), ""]
    for award in data["awards"]:
        out.append("%s - %s, %s" % (award["award"], award["event"], award["date"]))
    out.append("")

    out += [rule(), "EDUCATION", rule(), ""]
    for school in data["education"]:
        out.append(school["degree"])
        out.append("%s | %s | %s" % (school["school"], school["location"], school["dates"]))
    out.append("")

    return "\n".join(out)


MONTHS = {m: i + 1 for i, m in enumerate([
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"])}


def iso_dates(dates):
    """'August 2019 - January 2025' -> ('2019-08', '2025-01'); PRESENT -> ''."""
    parts = re.split(r"\s*[-–]\s*", dates)

    def one(part):
        part = part.strip()
        if not part or re.match(r"present", part, re.I):
            return ""
        month = re.search(r"[A-Za-z]+", part)
        year = re.search(r"(19|20)\d{2}", part)
        if not year:
            return ""
        if month and month.group(0).lower() in MONTHS:
            return "%s-%02d" % (year.group(0), MONTHS[month.group(0).lower()])
        return year.group(0)

    start = one(parts[0]) if parts else ""
    end = one(parts[1]) if len(parts) > 1 else ""
    return start, end


def build_jsonresume(data):
    keywords = []
    for group in data["skills"]:
        keywords.extend(group["items"])

    resume = {
        "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
        "basics": {
            "name": NAME,
            "label": HEADLINE,
            "email": EMAIL,
            "phone": PHONE,
            "url": SITE,
            "summary": data["summary"],
            "location": {"city": "Toronto", "countryCode": "CA"},
            "profiles": [
                {"network": "LinkedIn", "username": "freddy-shaikh", "url": LINKEDIN},
                {"network": "GitHub", "username": "Freddy-S3", "url": GITHUB},
            ],
        },
        "work": [],
        "education": [],
        "certificates": [],
        "projects": [],
        "skills": [
            {"name": group["category"], "keywords": group["items"]}
            for group in data["skills"]
        ],
    }

    for job in data["experience"]:
        start, end = iso_dates(job["dates"])
        entry = {
            "name": job["organization"],
            "position": job["title"],
            "location": job["location"],
            "startDate": start,
            "summary": "",
            "highlights": job["bullets"],
        }
        if end:
            entry["endDate"] = end
        resume["work"].append(entry)

    for school in data["education"]:
        start, end = iso_dates(school["dates"])
        degree = school["degree"]
        area = degree.split("-", 1)[1].strip() if "-" in degree else degree
        entry = {
            "institution": school["school"],
            "studyType": degree.split("-", 1)[0].strip(),
            "area": area,
            "startDate": start,
        }
        if end:
            entry["endDate"] = end
        resume["education"].append(entry)

    for award in data["awards"]:
        resume["certificates"].append({
            "name": award["award"],
            "issuer": award["event"],
            "date": award["date"],
        })

    for project in data["projects"]:
        resume["projects"].append({
            "name": project["title"],
            "description": " ".join(project["bullets"]),
            "highlights": project["bullets"],
            "url": project["url"],
        })

    return json.dumps(resume, indent=2, ensure_ascii=False) + "\n"


def budget(label, text):
    limit = LIMITS.get(label)
    if not limit:
        return ""
    state = "OK" if len(text) <= limit else "OVER BY %d" % (len(text) - limit)
    return "  <!-- %d / %d chars - %s -->" % (len(text), limit, state)


def build_linkedin(data):
    out = ["# LinkedIn paste sheet", "",
           "Generated from `resume/resume/*.tex`. Do not edit by hand - rerun `py tools/resume_export.py`.",
           "Character counts against LinkedIn's limits are noted inline.", "",
           "## Headline", "", "```", HEADLINE, "```", budget("Headline", HEADLINE), "",
           "## About", "", "```", data["summary"], "```", budget("About", data["summary"]), ""]

    out += ["## Experience", ""]
    for job in data["experience"]:
        start, end = iso_dates(job["dates"])
        body = "\n".join("- %s" % bullet for bullet in job["bullets"])
        out += ["### %s - %s" % (job["title"], job["organization"]), "",
                "%s | %s to %s" % (job["location"], start or "?", end or "Present"), "",
                "```", body, "```", budget("Position description", body), ""]

    out += ["## Skills", "",
            "LinkedIn allows 50 skills. Add in this order - the first three show on your profile.", ""]
    seen, ordered = set(), []
    for group in data["skills"]:
        for item in group["items"]:
            base = re.sub(r"\s*\(.*?\)", "", item).strip()
            if base.lower() not in seen:
                seen.add(base.lower())
                ordered.append(base)
    for i, skill in enumerate(ordered[:50], 1):
        out.append("%d. %s" % (i, skill))
    if len(ordered) > 50:
        out.append("")
        out.append("Over the 50 limit, not listed: %s" % ", ".join(ordered[50:]))
    out.append("")

    out += ["## Licenses & certifications", ""]
    for award in data["awards"]:
        out.append("- **%s** - %s, issued %s" % (award["award"], award["event"], award["date"]))
    out.append("")

    out += ["## Projects", ""]
    for project in data["projects"]:
        out.append("- **%s** (%s)" % (project["title"], project["url"] or "no link"))
        for bullet in project["bullets"]:
            out.append("  - %s" % bullet)
    out.append("")

    return "\n".join(out)


SYNC_DOC = """# Profile sync checklist

Generated by `py tools/resume_export.py`. The LaTeX in `resume/` is the source of truth.

## Why this is a checklist and not a script

None of these sites lets a third party write to a candidate profile:

| Site | Public API | Can a script update the profile? |
|---|---|---|
| LinkedIn | Marketing, Share, Sign-In only | No. There is no profile-edit endpoint. Positions, skills, and About are not writable. |
| Indeed | Employer / ATS job APIs | No candidate-profile write. Resume upload is manual. |
| Glassdoor | Employer branding and job feeds | No candidate-profile write. |
| ZipRecruiter | Employer job-posting partner API | No candidate-profile write. |

Driving the logged-in UI with a browser automation tool would need stored
credentials, breaks each site's terms of use, and silently rots whenever they
change their markup. Not worth it for a profile you touch a few times a year.

So: the generated artifacts below make the paste mechanical and keep every
channel consistent with the resume. Budget about ten minutes.

## Order of operations

1. Rebuild everything: `.\\tools\\build-resume.ps1` (PDF + website), then `py tools/resume_export.py`.
2. Work the list below.

## LinkedIn

Source: `exports/linkedin.md`. Every block is sized against LinkedIn's limits.

- [ ] Headline
- [ ] About
- [ ] Each position description
- [ ] Skills - order matters, first three are pinned to the profile
- [ ] Licenses & certifications - add new ones, they do not sync from anywhere
- [ ] Featured section: link `https://freddyshaikh.com`
- [ ] Turn OFF "Share profile updates" before a bulk edit, or your network gets a notification per change

## Indeed

Profile at `indeed.com/me`. Indeed parses an uploaded file rather than taking structured input.

- [ ] Upload `Certificates/Freddy_Shaikh_Resume.pdf`
- [ ] Check what the parser extracted - it mangles two-column and icon-heavy layouts, and awesome-cv is icon-heavy
- [ ] If the parse is poor, upload `exports/resume.txt` instead; plain text parses most reliably
- [ ] Fix the Skills section by hand afterwards

## Glassdoor

Glassdoor shares an account system with Indeed, so the resume often carries over.

- [ ] Confirm the resume synced from Indeed; if not, upload the same file
- [ ] Update the headline to match `exports/linkedin.md`

## ZipRecruiter

- [ ] Upload `Certificates/Freddy_Shaikh_Resume.pdf`
- [ ] Review the parsed work history, ZipRecruiter re-parses on every upload
- [ ] Update the "Desired job title" field to match the headline

## What is actually automatable, if you want it later

- `exports/jsonresume.json` follows the JSON Resume standard, which several
  job tools and static resume sites ingest directly.
- The website cascade already runs in CI on every push to `resume/**`.
- A scheduled job could diff `resume.data.json` against its last committed
  version and email you a reminder listing which profiles need the paste.
  That is a real option and needs no credentials.
"""


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    data = extract()
    write("resume.txt", build_txt(data))
    write("jsonresume.json", build_jsonresume(data))
    write("linkedin.md", build_linkedin(data))
    write("PROFILE-SYNC.md", SYNC_DOC)
    return 0


if __name__ == "__main__":
    sys.exit(main())
