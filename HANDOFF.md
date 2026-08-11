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

## Browser verified (locally AND in CI)

`.github/workflows/resume.yml` installs `requirements.txt`, installs Chromium, and runs
`tools/test_site.py` after the cascade step, so the suite checks the `index.html` that run
just generated. A failing check fails the workflow.

This was not always true. The suite had never run in CI until 2026-08-11, while this file
claimed otherwise - and when it was finally wired up it came back **18/20**, because two
hardcoded count assertions had gone stale as content grew (skill categories 3 -> 4,
portfolio cards 8 -> 9). Neither was a real defect, but the stale "20/20" claim had been
sitting here masking the fact that nothing was checking.

`py tools/test_site.py` renders the page in real Chromium: 20/20 checks pass. It covers
element counts, image decoding, every nav control, the theme toggle, contrast ratios in
both themes, horizontal overflow at three widths, console errors, and failed requests.
Screenshots land in `.screenshots/` (gitignored).

It caught one real bug, now fixed: the Skill Areas grid never stacked on mobile. Both
responsive overrides were scoped `.about-stats .skill-categories`, but the generated
block sits outside `.about-stats`, so neither rule matched and the page overflowed 23px
at 390px wide.

Setup, once per machine:

```
py -m pip install playwright
py -m playwright install chromium
```

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
candidate-profile write API, so nothing can push these headlessly. Driving your own
logged-in Chrome session with Claude in Chrome is possible and stores no credentials,
but do it with you watching - LinkedIn in particular restricts accounts it thinks are
automated, which is expensive mid-search. What exists instead:

| File | Use |
|---|---|
| `exports/linkedin.md` | Paste sheet, every block pre-checked against LinkedIn's character limits |
| `exports/resume.txt` | ATS plain text. Upload this when a site's parser mangles the PDF - awesome-cv is icon-heavy and parses badly |
| `exports/jsonresume.json` | JSON Resume standard, for tools that ingest it |
| `Certificates/Freddy_Shaikh_Resume.pdf` | The upload for Indeed / Glassdoor / ZipRecruiter |

Turn off "Share profile updates" on LinkedIn before a bulk edit.

## Open items

Items here are cross-referenced with the idea queue at `~/.claude-harness/queue/`
(`QUEUE-PC.md` for anything needing the local toolchain, `QUEUE-PHONE.md` for the rest).
When you close one here, close it there too - two lists that drift are worse than one.

Resolved since this list was written, kept short rather than deleted so the trail survives:
~~1. The resume is 2 pages.~~ The renditions are 1 page (PR #5, #8, #10). The canonical
   build still runs to 2 pages, because it carries a separate education section and a
   longer certifications block that the one-page cuts drop; see open item 4.
~~4. `skills.tex` overfull hbox.~~ Fixed in PR #4.
~~5. Merge `resume-cascade`.~~ Merged; PRs #1-#10 are all merged as of 2026-08-11.
~~6. Which rendition is the default?~~ `balanced` (PR #16). Its content is migrated into
   the canonical `resume/resume/*.tex`, so the site, the published PDF, and the three
   job-board exports all cascade from it. `renditions/balanced/` is kept as the one-page
   cut; see `resume/renditions/README.md`.

Still open:

1. `AWS Certified Machine Learning Engineer - Associate` has no certificate file and no credential URL. Its link in `tools/asset-map.json` is a placeholder `"#"`.
2. `Certificates/AWS Certified AI Practitioner certificate.pdf` exists but is not in `awards.tex`, so it gets no card. Add it to the resume or delete the file.
3. The PDF rebuilds byte-differently on each CI run, so it churns in git history. Harmless; it is already excluded from the workflow's `git add` for this reason.
4. **Resume polish, next iteration.** Tracked in `QUEUE-PC.md` (needs tectonic + eyes on the PDF):
   - The certifications row renders as "2023-2026 Certifications, Google Cloud..." - a table row pretending to be a sentence. Restructure it.
   - That row also carries location "Toronto, Canada". Meaningless for vendor certs, and it sits directly above McMaster's "Hamilton, Canada" so the two read as parallel facts. Blank it.
   - Projects has only ONE entry (Agentic Engineering Harness). Consider restoring The Compounding Engineer - it was added in PR #7 and has since been dropped, so the content is recoverable from history.
   - The Santoku VR bullet ends with the dead tail "...implementation, automated unit/integration testing, launch, and five and a half years of production maintenance". Cut or rewrite it.
6. **Commit a `requirements.txt`** pinning `pymupdf`, `playwright`, and `libsass`. These are currently documented only in tool docstrings and in this file - they are knowledge, not artifacts, which is exactly why this repo's tooling broke after the machine migration. Tracked in `QUEUE-PHONE.md`.
7. **Wire Playwright into `resume.yml`** so `tools/test_site.py` actually runs in CI. See the "Browser verified" section above: the suite has never run in CI. Tracked in `QUEUE-PHONE.md` alongside item 6.
8. **Supervised job-board profile pass** (LinkedIn / Indeed / ZipRecruiter / Glassdoor). Read `exports/PROFILE-SYNC.md` first. Two gotchas: turn OFF "Share profile updates" before bulk edits, and LinkedIn pins the first three skills so their order matters. None of these sites has a candidate-profile write API, so this is a supervised browser pass by necessity - do not automate around bot detection. Gated on items 4 and 5. Tracked in `QUEUE-PC.md`.

## Notes

- `resume.data.json` and `exports/` are committed deliberately, so a diff shows what changed in the resume without a LaTeX toolchain.
- SCSS is still the source of truth for CSS. `py tools/build_styles.py` compiles it via libsass. `-webkit-clip-path` is written explicitly in the SCSS because libsass does not autoprefix and the original CSS had been built by a toolchain that did.
