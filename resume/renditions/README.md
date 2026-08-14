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
| `ats-dense` | Keyword-dense for automated resume filters. Longest, 2 pages. | One unreviewed clause - see below |

## `ats-dense` needs review before use

**Several of `ats-dense`'s bullets originated in commented-out draft text rather than
reviewed copy.** Most have since been ruled on individually - see the status table below.
One clause remains unreviewed.

Background: the original resume carried a large block of commented-out `\item` lines.
These are **draft content** - wording in progress rather than reviewed copy. The tell is
that the same bullet text appears verbatim under three different employers, which is what a
reuse palette looks like rather than a record of results. On 2026-08-11 an automated pass
treated them as disabled-but-current and promoted several into live renditions. The quantified ones (75% repetitive tasks, 75% downtime, 80% deployment
time, "20+ emerging technologies") have all been removed. The unquantified ones have not,
because removing them is a content judgement that needs a human review.

### Status as of 2026-08-11: four of the five are resolved

The table below was written when all five were open. Freddy has since ruled on four of
them, so the untrusted surface is one clause, not a third of the rendition. Verified
against the files rather than carried forward from the earlier wording.

| Bullet | Traces to | Status |
|---|---|---|
| Splunk/SNS health-check automation and IAM security audits | `experience.tex:20`, `:21` | **Accurate.** Held back on relevance, not accuracy. Commented in `ats-dense/experience.tex:25` |
| Automated unit/integration/API test suites for VR programs | `:60` | **Accurate.** Held back on relevance. Commented at `:54` |
| Hybrid cloud solution using AWS File Gateway | `:53` | **Accurate.** Held back on relevance. Commented at `:61` |
| RESTful microservices in Java 8 and Spring Boot | `:63` | **Not applicable to that employer.** Removed from every rendition. The Java and Spring Boot skills rows stay - they are real, from personal projects |
| "client training, and support" clause on the VR bullet | `:65`, `:66` | **Still unverified.** The only one outstanding. Live in `ats-dense/experience.tex:38`; the canonical bullet ends at "primary technical decision-maker" and does not carry it |

The three marked accurate are **verified-true and deliberately unused**. A later pass must
not re-flag them as suspect, and must not activate them either - "accurate" and "wanted on
the resume" are different questions, and only the first is settled.

Because they are accurate, they are the natural first candidates for the long-form CV,
where there is no page pressure. See the CV item in `QUEUE-PC.md`.

The bullet formerly held back from `balanced` was the Java/Spring Boot one, now resolved
above. The guarded comment for it remains in `resume/resume/experience.tex`.

## The rule that came out of this

**Never uncomment, activate, or promote a commented-out line in these files without
explicit, per-bullet confirmation.** Commented content is draft material, not disabled
truth - treat it as unverified. Deactivating is safe; activating and deleting are not.

The full palette is preserved as comments at the bottom of `resume/resume/experience.tex`
so the material survives future re-cuts.
