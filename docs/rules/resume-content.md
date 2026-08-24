# Resume Content Rules

**Read this before the first edit to any resume content, not after drafting.**

## When this fires

Any of the following, in any repository, including every `Portfolio-Website-*` and `PW-*`
worktree and the `job-applications` repository:

- `resume.data.json` - the authoritative source
- anything under `resume/`, including `resume/renditions/<target>/` and `resume/resume.tex`
- anything under `exports/` (`resume.txt`, `jsonresume.json`, job-board exports) or `Certificates/`
- any build, export, or sync script for the above (`tools/build-resume.ps1`, `tools/resume_export.py`,
  `tools/resume_to_site.py`, `tools/check_resume.py`)
- the resume section of the live site, and any published rendition or PDF
- job-application profile text, cover letters, or screening answers that restate his experience

Reading counts as a trigger, not only writing. These rules decide what you are allowed to
conclude from what you read, and the failure below happened at the point of interpretation.

These rules live here rather than in the harness core because they apply only to this work.
`~/Repo/agent-agnostic-harness/instructions/AGENTS.md` carries a trigger row pointing here, so
a session in any repository still reaches them.

## The rules

- Never uncomment, activate, or promote a commented-out line in Freddy's resume files without his explicit, per-bullet permission. Commented content is NOT disabled truth - treat it as unverified. His commented bullets are example/placeholder text he was drafting against, and several appear verbatim under three different employers, which is what a reuse palette looks like, not a record of results. On 2026-08-11 a session read them as real-but-disabled and activated two metric claims (75% repetitive-task reduction, 75% downtime reduction); they reached a built PDF, two renditions, the live site, and all three job-board exports before anyone caught it, on a resume headed to Google. The same session deleted ~30 other commented bullets as "dead comments" - also not ours to judge. Deactivating is safe; activating and deleting are not.
- **Resume content drafting gate.** Before changing any resume content - including a summary, skill, bullet, project, title, section order, or certification - prepare at least two distinct copy drafts as review artifacts. Show the current wording alongside each draft and highlight material differences. Keep the authoritative source and generated cascade unchanged while Faruk decides; edit the source and regenerate only after he selects or approves a draft. This gate applies even when the proposed wording is a small or obviously reversible improvement.
- **Resume positioning preference.** Present Faruk's verified experience in its strongest accurate light for employers. Lead with supported leadership, ownership, and technical scope - such as a designated technical-lead role - rather than underselling the work with generic phrasing. Keep titles, metrics, and responsibilities truthful; strengthen framing, not facts.

## Why the three sit together

They pull in different directions on purpose, and that is the point. The positioning rule pushes
toward the strongest accurate framing; the first two bound what "accurate" is allowed to mean and
who gets to decide. Applying the positioning rule without the other two is how unverified text
becomes a claim: the 2026-08-11 incident was not a session inventing a metric, it was a session
finding plausible-looking text already in the file and deciding it counted as true.

Strengthen framing, never facts. When the two conflict, the gate wins and Faruk decides.

## The cascade

`resume.data.json` is the source. Renditions, the site, PDFs, and every export are generated from
it. A change made directly to a generated file is lost on the next build and, worse, looks
authoritative until then. Edit the source and regenerate; never hand-edit the cascade.

Note that a build is a write into whatever tree it runs in - `tools/build-resume.ps1` rewrites
`Certificates/*.pdf`, `index.html` and `exports/`. Run it in a worktree you hold, never in a tree
another session may be editing.
