# Renditions

Alternate cuts of the same career history, kept side by side so they can be compared as
PDFs. Build them all with `.\tools\build-renditions.ps1`; output lands in
`resume/build/renditions/` (gitignored).

## The default is `balanced`

As of 2026-08-11, **`balanced` is the general-purpose default**. Its content has been
migrated into the canonical `resume/resume/*.tex`, which is what cascades to
`Certificates/Freddy_Shaikh_Resume.pdf`, `index.html`, and the job-board exports.

So `renditions/balanced/` and `resume/resume/` now say the same thing, by design, and
`rendition-balanced.tex` exists mainly to show the one-page cut. If you edit one, edit the
other or the two drift - the canonical files are the ones that actually ship.

Everything else here is **reference material**, not a shipping document.

## What each one is for

| Rendition | Purpose | Trust |
|---|---|---|
| `balanced` | General-purpose default. Broad enough for most applications. | Trusted - one bullet held back, see below |
| `ai-forward` | Leads with AI/agentic work. For roles where the reader already wants an AI engineer. | Trusted |
| `google-concorde` | Targeted at a specific Google req. Scope-and-trade-offs framing, 1 page. | Trusted |
| `google-applied-ai` | Google Applied AI variant. Same framing, different emphasis. | Trusted |
| `ats-dense` | Keyword-dense for automated resume filters. Longest, 2 pages. | **NOT trusted - see warning** |

## Warning: `ats-dense` needs verification before use

**Roughly a third of `ats-dense`'s bullets originate in Freddy's commented-out example
palette, not in verified accomplishments.** Do not send it anywhere until he has confirmed
them individually.

Background: the original resume carried a large block of commented-out `\item` lines.
These were **example/placeholder text** he drafted against - his words: "not necessarily
things that I have." The tell is that the same bullet text appears verbatim under three
different employers, which is what a reuse palette looks like, not a record of results. On
2026-08-11 an automated session read them as disabled-but-true and promoted several into
live renditions. The quantified ones (75% repetitive tasks, 75% downtime, 80% deployment
time, "20+ emerging technologies") have all been removed. The unquantified ones have not,
because removing them is a content judgement only Freddy can make.

Specifically still live in `ats-dense/experience.tex` and traceable to commented lines in
the original:

| Bullet | Traces to |
|---|---|
| Splunk/SNS health-check automation and IAM security audits | `experience.tex:20`, `:21` |
| RESTful microservices in Java 8 and Spring Boot | `:63` |
| Automated unit/integration/API test suites for VR programs | `:60` |
| Hybrid cloud solution using AWS File Gateway | `:53` |
| "client training, and support" clause on the VR bullet | `:65`, `:66` |

And one held back from `balanced`, therefore absent from the canonical resume: the
"RESTful microservices in Java and Spring Boot ... with automated unit, integration, and
API test coverage" bullet (`:63` + `:60`). It is commented out in
`resume/resume/experience.tex` with a guard, pending his answer.

## The rule that came out of this

**Never uncomment, activate, or promote a commented-out line in these files without
Freddy's explicit, per-bullet permission.** Commented content is not disabled truth - treat
it as unverified. Deactivating is safe; activating and deleting are not.

The full palette is preserved as comments at the bottom of `resume/resume/experience.tex`
so the material survives future re-cuts.
