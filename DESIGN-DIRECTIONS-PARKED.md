# Portfolio design directions — parked

Status: **parked at Freddy's request.** Four design directions were explored and
rendered but nothing was built. No production file was modified.

## Where the artifacts are

**Renders (16 PNGs, 2x, full-page):**
`resume/build/renditions/design-{a,b,c,d}-{desktop,mobile}.png`
plus a `-dark` variant of each.

> ⚠️ That directory is gitignored and is a *build output* path — a clean or a
> rebuild may remove it. Move these somewhere durable before relying on them.

**Mockup HTML + write-up (AT RISK — temp directory, may be cleaned by the OS):**
`C:\Users\faruk\AppData\Local\Temp\claude\C--Users-faruk-Repo\af63adaa-f864-4f40-a3a2-641416012b38\scratchpad\designs\`
containing `DESIGN-DIRECTIONS.md` and the four standalone mockup HTML files.

**First action on resuming: move that temp folder into a permanent location.**

## The four directions

| | Name | Look | Aimed at | Main risk |
|---|---|---|---|---|
| A | Recruiter Card | warm grey/green, single narrow column | recruiter skimming on a phone | reads as a good *generic* candidate page, not distinctly his |
| B | The Router | near-black/amber, monospace, console is the hero | senior engineers, AI-platform managers | non-technical recruiter sees slash commands before "Morningstar"; resume link ends up in the footer; console clips its prompt on mobile |
| C | Editorial Case Study | paper cream, serif, drop cap, sticky fact rail | a manager who already gave him 10 minutes | only direction whose content can't come from the generator, so it rots when his role changes |
| D | System Map | slate/cobalt, inline SVG diagram of the real pipeline | platform / applied-AI readers | a diagram looks authoritative whether or not it's true — boxes must stay honest |

## Recommendation on the table

**A's hero + D's system diagram on the homepage; B promoted to a dedicated
`/harness` page; C published as a post on The Compounding Engineer.**

Reasoning: the first fifteen seconds belong to a recruiter and that can't be
engineered around — but A alone wastes the harness, which is the thing that makes
him non-substitutable, so the system diagram belongs as the second block rather
than one card in a row. B is too narrow for a front page and too good to discard;
behind the existing "Try the Skill Router" button its audience has self-selected.

Side benefit: all four directions drop the hero photo, which eliminates the
1 MB `img/hero.png` problem outright rather than optimising it.

## Open question that changes the most

Is the site's headline "Senior Full-Stack Engineer", or an applied-AI framing?
Given the Google Cloud Applied AI target, an applied-AI framing is probably
right — it's where he's aiming and it's what the harness actually evidences.

Five further open questions are in `DESIGN-DIRECTIONS.md` and were written to
`QUEUE-PHONE.md` as a blocked entry.

## Constraints that must survive into the build

- No invented content: no fake metrics, no fabricated testimonials, no
  "trusted by" logos. Every claim traceable to real content.
- Nothing that can't be generated from the single-source-of-truth pipeline.
  A design needing hand-maintained per-page content will rot.
- Keep the "deterministic simulation — no model runs on this page" disclaimer.
- The private career skill (`job-search`) must stay absent from the catalog.
- Accessibility: real contrast, meaningful alt text, keyboard-reachable controls.
