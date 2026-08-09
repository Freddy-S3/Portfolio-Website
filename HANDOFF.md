# Handoff: resume cascade

Last updated: 2026-08-09, overnight session.
Branch: `resume-cascade`, pushed. Nothing merged to `master`.

## The one command

```powershell
.\tools\build-resume.ps1 -Open
```

Compiles `resume/resume.tex` to `Certificates/Freddy_Shaikh_Resume.pdf`, regenerates
`index.html` from the same `.tex` sources, and opens the PDF.
Verified working end to end.

For the job boards, add:

```
py tools/resume_export.py
```

## How it fits together

`resume/` (awesome-cv LaTeX) is the single source of truth. Everything else is generated.

```
resume/resume/*.tex
      |
      +-- tools/resume_to_site.py --> index.html (marked regions) + resume.data.json
      +-- tools/resume_export.py  --> exports/ (ATS text, JSON Resume, LinkedIn sheet)
      +-- tectonic / xelatex      --> Certificates/Freddy_Shaikh_Resume.pdf
```

`.github/workflows/resume.yml` runs all three on any push touching `resume/**` and
commits the results back. **Verified green** - run 31298163570.

Commented-out LaTeX is skipped everywhere. A `%` in front of a bullet removes it from
the PDF, the website, and every export in one edit. That is the whole point.

### Generated regions in index.html

Marked `<!-- resume:NAME:start -->` / `<!-- resume:NAME:end -->`.
Anything outside the markers is hand-written and preserved.
Regions: `summary`, `skills`, `timeline`, `projects`, `certifications`.

`tools/asset-map.json` supplies the images, links, icons, and display labels that
LaTeX does not carry. New certification in `awards.tex` means a new entry here.

## Verified

- One-line edit to `skills.tex` propagated to `index.html` and all four exports; reverting removed it cleanly.
- `resume_to_site.py` is idempotent; `--check` exits non-zero on drift.
- PDF: 2 pages, valid trailer, FontAwesome + Roboto + SourceSansPro all embedded.
- HTML nesting parses clean; every local `href`/`src` resolves to a real file.
- Generated `.skill-*` classes all have matching CSS rules.
- CI regenerated `index.html` and `exports/` byte-for-byte identical to the local run. Only the PDF differed, so the generators are platform-deterministic.

## Not verified

**Nobody has opened the page in a browser.** The Skill Areas block is new markup that
has never been rendered. Check it in both themes first thing - the theme toggle is
top right, and light mode is where the palette collides most easily.

## Local LaTeX

Uses **Tectonic 0.17.0** at `%LOCALAPPDATA%\tectonic\tectonic.exe`. Single self-contained
binary that fetches its own packages. Not on PATH; the build script finds it there.

MiKTeX is installed but **broken** and no longer used. Every package operation fails with
`invalid stoi argument`, including a bare `miktex packages list`, so it is a local MiKTeX
problem rather than a repo or mirror one.

Caveat on that diagnosis: a `winget install --force` repair was started but was killed
before it finished, so the reinstall was never actually completed and tested. If you want
MiKTeX back, finish that repair before concluding it is unfixable. Nothing here needs it -
the build script prefers Tectonic and only falls back to xelatex.

`resume/awesome-cv.cls` carries two portability patches, both needed:
- `\FA` is redefined conditionally. `fontawesome.sty` already defines it on TeX Live, which broke CI.
- `\RequirePackage{fontawesome}` is wrapped in `Path=fonts/, Extension=.ttf` so fontspec finds the bundled `resume/fonts/FontAwesome.ttf` instead of a system install.

## Job boards

`exports/PROFILE-SYNC.md` is the checklist. Read it before touching LinkedIn.

Short version: none of LinkedIn, Indeed, Glassdoor, or ZipRecruiter exposes a
candidate-profile write API, so no script can push these. Driving the logged-in UI
would need stored credentials and breaks their terms. What exists instead:

| File | Use |
|---|---|
| `exports/linkedin.md` | Paste sheet, every block pre-checked against LinkedIn's character limits |
| `exports/resume.txt` | ATS plain text. Upload this when a site's parser mangles the PDF - awesome-cv is icon-heavy and parses badly |
| `exports/jsonresume.json` | JSON Resume standard, for tools that ingest it |
| `Certificates/Freddy_Shaikh_Resume.pdf` | The upload for Indeed / Glassdoor / ZipRecruiter |

Turn off "Share profile updates" on LinkedIn before a bulk edit.

## Open items

1. Render the page in a browser, both themes.
2. **The resume is 2 pages.** `experience.tex` carries your note "Need to get rid of 5 lines to fit everything", so you probably want 1. Content call, left alone.
3. `AWS Certified Machine Learning Engineer - Associate` has no certificate file and no credential URL. Its link in `tools/asset-map.json` is a placeholder `"#"`.
4. `Certificates/AWS Certified AI Practitioner certificate.pdf` exists but is not in `awards.tex`, so it gets no card. Add it to the resume or delete the file.
5. `skills.tex` throws an overfull hbox, 53pt too wide - a skills line runs past the margin in the PDF.
6. Merge `resume-cascade` to `master` once the page looks right. Draft PR is open.
7. The PDF rebuilds byte-differently on each CI run, so it churns in git history. Harmless; drop it from the workflow's `git add` if it bothers you.

## Notes

- `resume.data.json` and `exports/` are committed deliberately, so a diff shows what changed in the resume without a LaTeX toolchain.
- SCSS is still the source of truth for CSS. `py tools/build_styles.py` compiles it via libsass. `-webkit-clip-path` is written explicitly in the SCSS because libsass does not autoprefix and the original CSS had been built by a toolchain that did.
