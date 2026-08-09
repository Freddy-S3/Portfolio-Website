# Handoff

## Where things stand

The resume pipeline is in place but uncommitted. Everything below is working tree only.

Modified: `.gitignore`, `index.html`, `styles/_media.scss`, `styles/styles.css`, `styles/styles.css.map`, `styles/styles.scss`
New and untracked: `.github/`, `resume/`, `tools/`, `resume.data.json`

## The pipeline

`resume/resume.tex` (awesome-cv) is the source of truth.

1. `tools/build-resume.ps1` runs xelatex twice, copies the PDF to `Certificates/Freddy_Shaikh_Resume.pdf` where both "Download CV" buttons point, then runs the cascade.
2. `tools/resume_to_site.py` regenerates `index.html` and `resume.data.json` from the `.tex` sources, using `tools/asset-map.json`.
3. `tools/build_styles.py` compiles `styles/styles.scss` to `styles/styles.css`.
4. `.github/workflows/resume.yml` does the same on `ubuntu-latest` via `xu-cheng/latex-action` and commits the refreshed PDF and site back. Triggers on pushes touching `resume/**`, `tools/resume_to_site.py`, or `tools/asset-map.json`.

## Known state

- A crash corrupted `.git/index` and truncated this file. The index was rebuilt with `git reset`; no work was lost.
- `resume/awesome-cv.cls` was patched: `fontawesome.sty` asks for the `FontAwesome` font by name, which only resolves for a system-wide install, so the `\RequirePackage{fontawesome}` is now wrapped in `\defaultfontfeatures{Path=fonts/}` to pick up the bundled copy in `resume/fonts/`.
- The local MiKTeX install is broken independently of this repo. Every package operation fails with `invalid stoi argument`, including `packages list` and `update-package-database`. Alternate mirrors and rebuilding the package db did not help. Repair with `winget install MiKTeX.MiKTeX --force`.
- Local xelatex is therefore blocked. CI is not; the workflow builds the PDF on push.

## Verified

- `py tools/resume_to_site.py` exits 0, reports `index.html already matches resume/`
- `py tools/build_styles.py` exits 0, compiles `styles/styles.css`

## Next

Repair MiKTeX, or push and let the workflow produce the PDF.
