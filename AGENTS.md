## Harness rules - read this first

This repository is operated by agents under a shared harness. The authoritative operating
rules are not in this file and are deliberately not copied into it:

    $HOME/Repo/agent-agnostic-harness/instructions/AGENTS.md

Open that file and read it before your first write in this repository. It carries the rules
that cannot be inferred from the code here: working-tree claims, queue compare-and-swap,
the write-ahead ledger, worktree isolation, the branch check that runs before the first read
rather than the first write, and how findings are persisted so they reach a dashboard rather
than only a chat transcript.

It is a pointer and not an include, because no include exists. Codex resolves `AGENTS.md`
per directory tree, from the working directory up to the repository root, and has no import
directive - so the file named above will not be in your context until you open it. Claude
Code sessions do receive it through `~/.claude/CLAUDE.md`, which imports it live; read it
here anyway rather than assuming your host did.

A copy would have been easier and is the thing to avoid. A snapshot of those rules goes
stale silently, and this file has no way to tell you that it has.

Before your first write in this working tree:

    pwsh -NoProfile -File $HOME/Repo/agent-agnostic-harness/tools/claim.ps1 \
      acquire -Tree <this tree> -Session $HARNESS_SESSION

Exit code 3 means a peer holds it: create your own worktree off the default branch and
claim that instead. A `pre-commit` hook enforces this, so an unclaimed agent commit in this
tree is refused rather than merely discouraged.

Everything below is specific to this repository. It adds to the rules above and does not
replace them.

# Portfolio Website Working Agreement

Keep work agent-agnostic so Codex, Claude Code, and other hosts can resume from this repository.

## Scope

This repository is the single logical Portfolio Website project.
Temporary `Portfolio-Website-*` and `PW-*` worktrees are execution copies, not separate products.

## Resume content - read the rules before touching it

Editing, generating, or publishing any resume content requires
[`docs/rules/resume-content.md`](docs/rules/resume-content.md). Read it before the first edit,
not after drafting. It covers `resume.data.json`, everything under `resume/`, `exports/` and
`Certificates/`, the build and export scripts, the published renditions, and job-application
text that restates his experience. Reading resume files counts as a trigger, because the rules
govern what you may conclude from what you read.

This is not boilerplate. On 2026-08-11 a session treated commented-out draft bullets as
disabled-but-true and activated two unverified metric claims; they reached a built PDF, two
renditions, the live site, and all three job-board exports, on a resume headed to Google. The
three rules in that file are what stops a repeat, and the third of them - present his experience
in its strongest accurate light - is the one that makes reading the other two mandatory rather
than optional.

## Source of truth

- Treat tracked source files, resume data, tests, and pull requests as authoritative.
- Do not invent credentials, employment claims, metrics, or project outcomes.
- Never activate commented-out resume content without explicit per-bullet approval. The full rule, its incident, the drafting gate, and the positioning preference are in [`docs/rules/resume-content.md`](docs/rules/resume-content.md).
- `resume.data.json` is the source; renditions, the site, PDFs and exports are generated from it. Never hand-edit the generated cascade.

## Workflow

- Work from the exact repository or isolated worktree that owns the outcome.
- Keep one active writing agent per worktree by default.
- For HTML, CSS, or client-side JavaScript changes, render the site in a real browser and check responsive layouts before completion.
- Verify interactive controls produce observable results.
- Keep public-facing writing concise, accurate, and recruiter-readable.
