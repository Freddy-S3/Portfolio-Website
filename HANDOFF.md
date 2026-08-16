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
commits the results back. On a source push it also rebuilds and commits
`Certificates/Freddy_Shaikh_Resume.pdf`; the generated PDF-only bot commit is excluded
from pull-request path filters so it cannot create an approval-required GitHub Actions
run. Pull requests that touch resume sources still fail the drift gate when the
committed PDF is stale. CI uses the pinned Tectonic 0.17.0 binary so its layout matches
the local publishing path.
**Verified green** - run 31298163570.

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
- PDF: 1 page, valid trailer, FontAwesome + Roboto + SourceSansPro all embedded.
- HTML nesting parses clean; every local `href`/`src` resolves to a real file.
- Generated `.skill-*` classes all have matching CSS rules.
- CI regenerates `index.html` and `exports/` byte-for-byte identical to the local run. The PDF is rebuilt and committed by CI after source changes because its binary bytes vary by toolchain.

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

`.\tools\build-renditions.ps1` now publishes each rendition's PDF next to its own sources
as `resume/renditions/<slug>/<slug>.pdf`, in addition to the `resume/build/renditions/`
copy. `resume/build/` is gitignored, so the published copy is the committed one and the
one to hand to a job board. Page counts as of 2026-08-11: `balanced` 1, `ai-forward` 1,
`google-concorde` 1, `ats-dense` 2, `google-applied-ai` 2.

Note `balanced.pdf` is one page and `balanced` is the default rendition, so it is a
better board upload than the 2-page canonical `Certificates/Freddy_Shaikh_Resume.pdf`
until open item 10 is resolved. All of them still carry the open item 11 text-layer
defect - it comes from awesome-cv, so no rendition escapes it.

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
8. **Supervised job-board profile pass** (LinkedIn / Indeed / ZipRecruiter / Glassdoor). Read `exports/PROFILE-SYNC.md` first. Two gotchas: turn OFF "Share profile updates" before bulk edits, and LinkedIn pins the first three skills so their order matters. None of these sites has a candidate-profile write API, so this runs as a browser pass against the logged-in session, no stored credentials. **In progress 2026-08-11**: driven via Claude in Chrome, with logins, CAPTCHAs, and the first Save on each site left to Faruk. The risk is not uniform across the four - Indeed, Glassdoor, and ZipRecruiter are upload-and-parse flows that tolerate automation fine; LinkedIn fingerprints it and is the only one paced deliberately. Gated on items 4 and 5. Tracked in `QUEUE-PC.md`.

9. **Automate job applications on Indeed, Glassdoor, and ZipRecruiter.** Follows directly from item 8: those three are upload-and-parse flows with no meaningful automation detection, so the apply path is scriptable against the logged-in session in the same way the profile path is. LinkedIn is explicitly out of scope - it is the one platform where this would put the account at risk mid-search. Wants a per-site look at what "apply" actually submits (Indeed Quick Apply and ZipRecruiter 1-Click both vary by employer, and some hand off to an external ATS, which is where automation stops being safe or useful). To be added to the top of `QUEUE-PC.md` by Faruk.

~~10. **The published PDF is 2 pages, and that is what the job boards now hold.**~~ **RESOLVED 2026-08-16.** The canonical PDF is now the approved one-page build, and PR #43 publishes the refreshed artifact. CI now rebuilds and commits the PDF automatically whenever `resume/` changes, so source/PDF drift cannot persist after a merge. Re-upload the refreshed one-page file to every job board touched in the earlier cascade.

~~11. Small caps corrupt the PDF text layer, and it is ATS-breaking.~~ **FIXED 2026-08-11.**
   Every small-caps word extracted with a lowercase `i` - `SENiOR`, `ENGiNEER`, `ENGLiSH`,
   `SCiENCE`, `KiNESiOLOGY` - because Source Sans Pro's small-cap `i` maps back to lowercase
   through its ToUnicode table while its other small caps map to uppercase. An exact-match
   recruiter search for "Senior Software Engineer" could not hit the title. Present in all
   five renditions plus the canonical build, so it came from the class, not from any one cut.

   `awesome-cv.cls` now renders those five heading styles as real uppercase via `\acvupper`
   instead of `\scshape`, which avoids the small-cap glyphs entirely and makes the text layer
   correct by construction rather than by trusting a font's mapping. Visually near-identical
   at these sizes; `balanced` is still one page.

   `\XeTeXgenerateactualtext=1` was tried first and is **not viable on this toolchain** - this
   XeTeX build emits a malformed `/ActualText` span that destroys the entire text layer
   (extraction returned `'c\nc祢\nc祢...'`). `check_resume.py`'s vertical-hole check caught it.
   Do not reach for it again without testing extraction.

   Guarded by `check_resume.py`'s `MIXED_CASE_RUN` check, which fails any build whose text
   layer has a lowercase letter inside an uppercase run. Verified both directions: it fails a
   pre-fix PDF and passes a rebuilt one. The page renders identically either way, which is
   exactly why it needs a machine check rather than an eyeball.

## Notes

- `resume.data.json` and `exports/` are committed deliberately, so a diff shows what changed in the resume without a LaTeX toolchain.
- SCSS is still the source of truth for CSS. `py tools/build_styles.py` compiles it via libsass. `-webkit-clip-path` is written explicitly in the SCSS because libsass does not autoprefix and the original CSS had been built by a toolchain that did.
