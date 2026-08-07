# Method notes from #3686

For collation. Observations about the **method**, not about this issue's verdict.

This issue is a shape SKILL.md does not currently cover: **an issue answered from project and
release metadata rather than by running the compiler.** Everything below is about that gap.
Nothing here was true only of #3686 — an issue asking "which platforms do you ship?", "did that
PR ever land?", "is that documented yet?" or "is this policy still current?" hits all of it.

---

## 1. The first question is not always "does it still reproduce"

SKILL.md's spine is repro → predicate → probe → bisect. For an artifact/policy issue the right
question is **"is this still true?"**, and the difference is not cosmetic: it changes what
counts as evidence, what counts as a control, and what the history field means.

The trap is that the workflow *will* run for such an issue. You can write a `repro.hlsl`,
compile it, watch it succeed, and record `does-not-repro`. That verdict would be completely
wrong and completely well-formed. Here a clean compile is the *reported situation* — a `dxc`
that works and is never published — so the probe that looks like evidence is actively
anti-evidence.

**Suggested addition to step 5**, beside the existing `not-compiler-verifiable` guidance:

> Before writing `cmd.txt`, ask what a *clean* compile would prove. If a passing run is
> compatible with the report being entirely true, the compiler is not the instrument. Say so and
> gather the evidence the claim is actually about.

## 2. `not-compiler-verifiable` currently reads as "needs a GPU". It has a second population.

The table says "judging it needs a GPU, driver or runtime, not a compiler", and every existing
example is a rendering or driver issue. That framing made it briefly unclear whether it applied
here. It should: the defining property is **the compiler is not the instrument**, and there are
at least two reasons for that — the symptom is downstream of compilation (GPU/driver), or the
claim is not about compilation at all (release artifacts, packaging, documentation, policy,
process). Widening the gloss to "needs a GPU, driver, runtime, or project/process evidence
rather than a compiler" would cover both without adding a status.

## 3. An issue directory with no `out-*.txt` is ambiguous — resolve it on disk

A directory with no captured compiler output reads two ways: "deliberately not measured" or
"the worker never got that far". Nothing distinguishes them, and the second is the failure this
whole workflow exists to catch.

What worked: a `manual-case-ground-truth-version.txt` that records the ground-truth binary's
`--version`, names the files that *are* the evidence, and states why no probe exists. Costs one
command, and converts a suspicious absence into a documented decision. **Worth making a rule for
every `not-compiler-verifiable` verdict**, and `audit` could plausibly require it: an issue with
no probes and no stated reason for having none is exactly what a completeness check is for.

## 4. `history` is a free-text field and it should be used, not defaulted to `n/a`

#3150, the other `not-compiler-verifiable` issue, records `history: "n/a"`. But #2633, #2792,
#3092 and #8732 all carry long prose histories, so the field clearly accepts them.

For a metadata issue there usually *is* a real history and it is often the most valuable thing
found — here, "0 macOS assets across 26 releases spanning 2017-2026, while Linux first appeared
at v1.7.2212". Defaulting to `n/a` because `bisect` was not run throws that away. **The field
means "what does the history show", not "what did `bisect` print".** Worth saying so in step 11,
with the caveat that a non-bisect history must state that no release was probed, so it cannot be
mistaken for a scan result.

## 5. The control discipline transfers to metadata directly, and you must port it deliberately

Step 4's rules are written about symptom predicates, but every one of them has an exact
counterpart here, and skipping the translation is how a metadata triage produces a confident
wrong answer.

- **"0 macOS assets" is an absence predicate.** It needs the same positive control a
  `not_contains` needs. `collect-release-assets.py` runs its classifier over seven plausible
  macOS asset names (`...arm64.tar.gz`, `...apple-darwin...`, `osx`, `universal`, `.dmg`,
  `.pkg`); all seven classify as macOS, so the zero is a real zero rather than a classifier that
  cannot see what it is looking for. Without that, "0" and "my regex is broken" are the same
  output — the metadata twin of SKILL.md's "a control cannot catch a broken reader".
- **Prefer an exhaustive listing over a classifier where one is affordable.** 73 asset names fit
  on a page and fall into four obvious shapes, so the strongest form of the finding is the
  listing itself, with the classifier as a cross-check. A reader can audit the claim without
  trusting any code. Where the population is small, enumerate it.
- **Check the whole history, not the newest release.** The brief pushed for this and it paid:
  the Linux transition at v1.7.2212 is what turns "macOS is missing" into "the identical ask was
  granted for the other platform four years ago", which is a different and much more useful
  statement. Checking only `latest` would have produced a true but inert answer. This is the
  metadata analogue of `--linear`.

## 6. Every absence check needs a positive control **whose target is in file content**

The `grep`-false-zero warning already in SKILL.md is about the agent tool. The generator scripts
here use `git grep`, which is safe — but *choosing the control* turned out to be the real
hazard, and I got it wrong twice on the first run:

- `git grep -c -i azure -- azure-pipelines.yml` → **no hits**. The word "azure" is in the
  filename, not the file. Read as a tool failure, it would have invalidated a perfectly good
  absence result.
- `git grep -c -i linux -- gcp-pipelines` → **no hits**, same reason:
  `gcp-pipelines/x86_64-linux-clang.yml` contains no literal "linux".

Both were caught only because the control was *run and inspected* rather than assumed. Generalise
to: **a positive control must target a string known to be in file content, and a failing control
means discard the absence result above it, not "the control was badly chosen" — until you have
checked which.** Also: pick the control from the same tool, same pathspec, same flags. Anything
else and it is testing a different thing.

A second contamination, same run: an absence pattern of `macos|darwin|release` over
`.github/workflows` "found" a hit — `CMAKE_BUILD_TYPE=Release`. A pattern loose enough to match
an unrelated word gives a false *positive* and hides the real absence. Splitting it into
`macos|darwin|apple` and `gh release|softprops|upload-release|create-release|actions/upload-artifact`
made both results meaningful. **Absence patterns need to be as carefully scoped as predicates.**

## 7. Distinguish the claims the thread conflates, explicitly and in writing

"macOS binaries are published", "macOS is buildable from source" and "someone else publishes
macOS builds" are three different propositions, and a 12-comment thread slid between them
repeatedly over four years — with third-party availability (Vulkan SDK, MonoGame) repeatedly
offered as though it answered the first.

Writing the three-column table into `expected.md` *before* looking at anything was what kept the
investigation honest; each piece of evidence had a column to land in, and evidence for the wrong
column could not be mistaken for progress. **Recommend this as the metadata-issue analogue of
"write down the symptom before running anything": enumerate the distinct propositions the thread
contains, before checking any of them.**

## 8. Repo configuration answers "what is intended"; release metadata answers "what happened"

They are different sources and they disagree in informative ways. Here: the repo builds and
tests macOS on every PR, and has since 2018 — while zero macOS binaries have ever been
published. Neither source alone gets that.

There is also a hard limit worth stating as a rule: **`git grep -i linux_dxc` over the whole
tree returns nothing**, even though that name is on 18 releases. The release packaging is not in
the repo. So for "what does this project ship?", repo configuration is *corroborating* evidence
and the release list is *primary* — and checking repo config alone would have produced a
confident answer about a pipeline that does not live there. Worth a line in SKILL.md: **check
whether the thing you are reasoning about is actually configured in the tree before treating the
tree as authoritative about it.**

## 9. `godbolt --skip` needs the reason to say why a link would *mislead*, not just why it is absent

"Nothing to see" is the existing idiom. Here the stronger and more useful reason is that a link
*would* show something — `dxc` compiling a shader perfectly — and that showing it invites the
reader to conclude the ask has been met. A skip reason that names the misreading it prevents is
worth more than one that reports an absence.

## 10. Read the thread for what has been *decided*, not only for what was reported

SKILL.md already says this for #2427 ("check what happened to the resolution"). It generalises
further: on a long-lived request the highest-value findings were all thread archaeology, and
none needed a compiler.

- A **maintainer re-titled the issue in 2023** to narrow its scope. That is checkable —
  `gh api .../timeline --jq 'select(.event=="renamed")'` returns the exact from/to and
  timestamp — and it settles a title/body mismatch that would otherwise look like staleness. If
  a body and title disagree, **check the rename events before recording `text_stale`.**
- The **stated blocker moved** over the issue's life: DXIL signing (now in-tree, #6770 closed)
  → Apple code signing. Reporting "still open" without that is true and useless; the movement is
  the news.
- Two commenters' claims are outdated, but **each was corrected in-thread by the next comment**,
  so nothing wrong is left standing and `text_stale` does not apply. This is worth recording as a
  worked negative example: SKILL.md holds `text_stale` to a high bar, and "an in-thread
  correction immediately below it" is a clean reason to withhold it. `text_stale` is for text
  a top-down reader would *believe*.

## 11. `needs-human-judgement` vs `still-valid-keep-open` when a maintainer has already answered

Worth an explicit rule, because the two are easy to swap. The facts said "still an open gap",
which points at `still-valid-keep-open`. But a maintainer had already stated a position ("no
plans", resourcing + code signing), so the only live question is whether an issue tracking a
declined ask should stay open — a policy call, not a measurement. `needs-human-judgement`, and
`overview.md` sorts it into the tier where a person is needed.

Proposed rule: **if the remaining question is one a maintainer would answer by deciding rather
than by measuring, it is `needs-human-judgement` regardless of which way the facts point.**
`still-valid-keep-open` should mean "confirmed broken, waiting on a fix, nothing to decide".

The same reasoning applied to labels: the evidence would support `wont-fix`, but proposing it
pre-empts the decision. Proposed `enhancement` only, and recorded in `notes.md` why `wont-fix`
and `ci` were considered and declined — a rejected proposal with a reason is more useful to the
next person than a silent omission.

## 12. Small tooling frictions

- An empty draft tag is not a usable `gh release view` key. Measured here,
  `gh release view ""` silently returned the latest published release and its three assets;
  querying the draft by REST release ID showed zero. A release census must separate drafts
  before dereferencing tags or it can double-count the latest release with no error.
- `triage.py fetch` crashed on this issue with `UnicodeDecodeError: 'charmap' codec can't decode
  byte 0x81` — `subprocess.check_output(..., text=True)` in `gh()` picks up the Windows ANSI code
  page, and comment 3 contains an emoji. `$env:PYTHONUTF8='1'` works around it, but the fix
  belongs in `triage.py`: pass `encoding="utf-8"` (and `errors="replace"`) to every `subprocess`
  call that reads `gh` output. Any issue whose thread contains non-Latin-1 text hits this, so it
  is a latent blocker on an arbitrary subset of the backlog rather than a one-off.
- `triage.py sql "SELECT ... FROM compilers"` needed a `SELECT *` first to discover the column is
  `exe_path`, not `exe`. A `triage.py schema` or a note in `--help` would save the round trip.
