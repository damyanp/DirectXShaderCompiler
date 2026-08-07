---
name: dxc-issue-triage
description: Triage open DirectXShaderCompiler GitHub issues by determining whether each has a usable repro, whether it still reproduces against a current build, and which release fixed or regressed it. Use when asked to triage, audit, or spot-check DXC issues, to find stale/fixed issues in the backlog, or to check whether a specific issue still reproduces. Produces an evidence-backed report and makes no changes to issues or to DXC source.
---

# DXC issue triage

Determine, for each open DXC issue: **is there a usable repro, does it still reproduce, and
when did that change?** Produce a report backed by on-disk evidence.

## Hard rules

- **Read-only on GitHub.** Only `gh issue view/list`, `gh release list/view/download`,
  `gh api` GET. Never `gh issue edit|comment|close|reopen|label`, even if a verdict seems
  obvious. Drafting a comment is in scope; **posting it is not**. Recommending an action and
  taking it are different jobs.
- **Never modify DXC source** while triaging. The point is to measure the compiler as it is.
- **Only public repros go to Compiler Explorer.** `godbolt` uploads the shader to a public
  third-party service. Repros derived from public issues in this public repo are fine;
  anything from a private report, a customer, or unreleased work is not.
- **Evidence or it didn't happen.** Every verdict must be reproducible by a human from the
  files left behind: the repro, the exact command, and the captured output.
- **Batch and checkpoint.** Triage a handful of issues, then stop and let a human review
  before continuing. Verdict quality degrades silently; unattended full passes hide that.

## Setup

Artifacts and cache live in **two separate roots**, and the split is the whole storage
design:

| root | default | committed? |
| --- | --- | --- |
| `DXC_TRIAGE_ROOT` | `<skill>/data` | **yes** — repros, captured output, notes, verdicts |
| `DXC_TRIAGE_CACHE` | `<skill>/.cache` | no — release binaries (~1.2 GB) and the database |

Evidence is committed because a verdict nobody can re-check is just an assertion. The cache
is not, because it is either huge, machine-specific, or derived. `scripts/triage.py` is the
only tool you need.

```bash
python triage.py init                        # first time only
python triage.py reindex                     # after a fresh clone: rebuild db from data/
python triage.py catalog --seed-from <repo>/build/tools/clang/test/dxc_releases
```

`catalog` records every release that ships a `dxc` binary. Ordering uses the **build date
encoded in the asset name**, not the publish date — servicing patches ship long after the
snapshot they were built from. `--seed-from` adopts release trees the DXC test infrastructure
already downloaded, for free.

### `reindex` is a regression test over every past batch

Run verdicts are not stored and restored — they are **re-derived** by running today's
predicate code over the archived output. So a rebuild re-checks every probe ever captured
and reports two kinds of disagreement:

- **probes today's code scores differently.** A predicate bug found while triaging one issue
  is retroactively applied to every issue already triaged. Both wrong-verdict classes found
  so far — a release rejecting an unknown profile, and an absence predicate satisfied by a
  failed parse — would have surfaced here automatically, for free.
- **probes captured with a command `cmd.txt` no longer specifies.** Correcting a repro does
  not delete the outputs captured from the old one, and a superseded probe looks exactly as
  authoritative as a current one.

The second check found two real cases the moment it was written. Three #3873 probes still
held `-T ps_6_7` output after the profile was corrected to `ps_6_0` — `bisect` short-circuits
once both endpoints agree, so it never revisited them. Worse, **all 21** of #3768's probes
still carried the `-fcgl -Vd` workaround after it had been removed from `cmd.txt`: the
removal had been confirmed by hand but never re-recorded, so the entire published history
rested on a configuration the report said was no longer in use. Re-running both confirmed the
verdicts rather than overturning them — but neither gap was visible without this check, and
"the verdict happened to survive" is not the same as "the evidence supported it".

Run it at the end of every batch. A clean run prints `every probe re-scores as captured, and
none are stale`; anything else is a finding to explain before the batch is written up.

**Name auxiliary captures so they are not mistaken for probes.** `out-<compiler>.txt` means
"the primary repro, scored by `match.json`". A control shader, a compute-shader translation
or a hand-run command line is *not* that, and scoring it with the primary predicate produces
a spurious disagreement — #1702's compute variant legitimately emits an error the pixel
repro does not. Use `variant-*.txt` for controls and translations, `manual-case-*.txt` where
the repro is not a `dxc` invocation at all.

### The ground-truth compiler must be a clean Debug build

Build `dxc` in **Debug** from a clean checkout of the target branch. Debug matters: a large
share of old DXC issues are asserts, and Release builds have asserts compiled out.

```bash
cmake --build <build> --config Debug --target dxc --parallel
python triage.py compiler --id main-debug --exe <build>/Debug/bin/dxc --commit $(git rev-parse HEAD)
```

**Verify the version string before trusting anything.** DXC caches generated version headers
and does *not* regenerate them when you switch branches, so a freshly built binary can report
a stale branch and a spurious `-dirty`. If `dxc --version` does not match the commit you built:

```bash
rm <build>/utils/version/version.inc* <build>/utils/version/dxcversion.inc*
cmake --build <build> --config Debug --target dxc --parallel
```

Triage provenance is worthless if the binary misreports what it is.

## Per-issue workflow

### 1. Read the whole issue, comments included

```bash
python triage.py fetch --issue <N> --batch batch-001
```

Comments routinely hold the real repro, a smaller reproducer, a maintainer's design position,
or a prior "still repros in X" datapoint. They also frequently contradict the issue body —
which is itself a finding worth reporting.

### 2. Write down the symptom *before* running anything

Create `issues/<nnnn>/expected.md` stating what "this reproduces" means, derived from the
issue text. **Do this first.** If you run the compiler first, you will rationalise whatever it
printed into a verdict, and "does not reproduce" becomes unfalsifiable.

Record the repro quality honestly: `complete`, `partial`, `prose-only`, `none`, or
`agent-constructed`.

### 3. Build the repro

Write `repro.hlsl` (and any extra files) plus `cmd.txt` — one dxc invocation per line,
**arguments only**, no exe path, paths relative to the issue directory:

```
-T gs_6_0 -E main repro.hlsl
```

Every compiler gets the identical command, which is what makes bisection meaningful. SPIR-V
issues need `-spirv`. If the issue has no repro, construct a best-effort one and mark it
`agent-constructed` — a constructed repro that is clearly labelled is far more useful than
"no repro provided".

> **Reproduce the reporter's exact configuration, then question their workarounds.**
> Two failure modes, both seen on #3768:
>
> *Silently changing the configuration.* The issue was reported against `ps_6_0`; the test
> file's `RUN:` line said `cs_6_0`, and the repro was built from the `RUN:` line. That happened
> to behave identically, but it was luck — the profile is part of what was reported. Use what
> the reporter used, and if you also test something else, say so.
>
> *Inheriting a stale workaround.* #3768 was filed with `-fcgl -Vd` "to disable legalization,
> since there's a current spirv-tools issue that would crash and confuse issues". Copying that
> into `cmd.txt` silently disabled legalization and validation for the entire history search,
> so a whole phase of the compiler was never exercised. Re-test without such flags: the
> upstream bug they dodge is often long fixed. Here removing them changed nothing about the
> verdict, but it did widen the code under test and it revealed that the workaround had never
> been suppressing this defect anyway — the reported stack was in `Sema`, reached long before
> legalization runs.
>
> Keep the original as `cmd-as-filed.txt` and note in `cmd.txt` why it differs.

### 4. Define the symptom predicate

`match.json` encodes "the symptom is present" so the same test is applied to every compiler
and a human can re-check it later. Include a `note` explaining the choice.

| kind | present when |
| --- | --- |
| `internal_failure` | dxc failed internally — **use this for all crash/assert issues** |
| `regex` / `not_regex` | pattern (absent) in combined output |
| `contains` / `not_contains` | literal substring (absent) |
| `nonzero_exit`, `timeout` | exit code / hang |
| `any_of` / `all_of` | `value` is a list of sub-predicates — for one defect with several signatures |

Add `"invert": true` to negate.

> **Use `internal_failure` for anything crash-shaped.** This is the single biggest source of
> wrong verdicts. The *same* bug surfaces differently across builds — a trapped assert
> (0x80000003) in an assert-enabled Debug build, but an access violation (0xC0000005) or a
> stray `llvm::cast<X>() argument of incompatible type!` E_FAIL in Release release-binaries.
> A predicate matching the assert *message* reports every release as clean, producing a false
> "fixed" verdict. This affects every `crash`-labelled issue.

> **Do not equate "nonzero exit" with "crashed".** On Windows dxc returns **E_FAIL
> (0x80004005) for ordinary diagnosed errors** — a plain syntax error, an invalid target
> profile and a DXIL validation failure all exit with it. A predicate of "anything that is not
> 0 or 1 is a crash" therefore reports essentially every failing compile as an internal
> failure. That is the more dangerous direction of error, because it *invents* bugs rather
> than missing them. `is_internal_failure()` instead tests the specific status codes dxc's own
> exception filter recognises (`tools/clang/tools/dxclib/dxc.cpp`): 0xC0000005, 0xC00000FD,
> 0x80000003, 0xE0000001-3, any other 0xC/0xE structured exception, and POSIX signal exits
> (139 = SIGSEGV) for Compiler Explorer's Linux builds.

**Exit codes, measured — not assumed:**

| Outcome | Exit | Internal failure? |
| --- | --- | --- |
| success | 0 | no |
| input file not found | 1 | no |
| syntax error, invalid profile, **DXIL validation failure** | 0x80004005 (E_FAIL) | **no** |
| assert fires (Debug) | 0x80000003 | yes |
| access violation | 0xC0000005 | yes |
| `llvm_unreachable` / `report_fatal_error` | 0xE0000002 / 0xE0000003 | yes |
| killed by signal (Linux/CE) | 139, 134 | yes |

> Unrecognised `/`-style flags are **silently ignored** — `/ZZZNONSENSE` exits 0. Never infer
> that a flag was honoured from a clean exit; make it fail (point it at a missing file) to
> prove it was parsed at all.

> **Message text is not portable.** The same failure is worded differently across platforms:
> the Windows build prints `llvm::cast<X>()` where the Linux build behind Compiler Explorer
> prints plain `cast<X>()`. Any marker you add must be build-agnostic, or it will score a real
> crash as clean on some builds. Prefer the exit code; treat text markers as a backstop, and
> assume a predicate tested against a single build is not yet tested.

**An issue may need more than one predicate.** When the reported symptom differs from current
behaviour, add e.g. `match-crash.json` and bisect each separately. That is how you distinguish
"this was fixed" from "this changed shape but is still broken" — a distinction that collapses
into a misleading single verdict otherwise.

**One defect can have two signatures — compose predicates with `any_of` / `all_of`.** A bug
whose Release manifestation differs from its Debug one needs a disjunction, or whichever build
you happen to run will report it fixed:

```json
{ "kind": "any_of",
  "value": [ { "kind": "timeout" }, { "kind": "internal_failure" } ] }
```

> Measured on #3873: a Release build **hangs unboundedly** on the repro, while the clean `main`
> **Debug** build trips an LLVM assert in ~2 seconds on the same input — Debug asserts on the
> broken state that Release spins on. A bare `timeout` predicate scores the Debug ground truth
> as `no-repro` and reports this open, always-reproducing bug as **fixed**. Neither signature
> alone is the symptom; failing to compile a valid shader is.

**Give every text-based predicate a control.** The control discipline in step 7 applies to
predicates too: run the predicate against an input you *know* is good, and require it not to
match. A predicate that matches everything is indistinguishable from a bug that reproduces
everywhere.

> Measured on #3009: a predicate matching any `undef` operand of any `dx.op` **also matched a
> fully-correct shader**, because several DXIL ops carry structurally-undef operands in
> perfectly valid code — `loadInput`'s trailing `gsVertexAxis` is `undef` in every non-GS
> shader, and `bufferStore`'s unused coordinates are `undef` for non-structured buffers.
> Narrowing it to `undef` reaching an *arithmetic* op made it discriminate. Record the control
> in the predicate's `note` so the next person does not have to rediscover it.

### 5. Run against the ground-truth build

```bash
python triage.py run --issue <N>
python triage.py run --issue <N> --match match-crash.json   # extra predicate
```

Then classify against `expected.md`:

| status | meaning |
| --- | --- |
| `repros` | reported symptom still observed |
| `does-not-repro` | repro runs clean, symptom gone |
| `changed-behavior` | still misbehaves, differently than reported |
| `not-compiler-verifiable` | needs GPU/runtime/driver/D3D execution to judge |
| `inconclusive` | repro too ambiguous to judge |

`not-compiler-verifiable` is a legitimate, useful outcome — not a failure. Do not force a
verdict on a rendering-artifact or driver-behaviour issue by compiling it.

> **Sometimes `repros` is the uninteresting half of the answer.** #2427's command line still
> fails exactly as filed — but the thread had already established in 2019 that this is the
> platform's argv splitting, before dxc sees anything, and that FXC does the same. Reporting
> "confirmed, still broken" would have been true and actively misleading. The finding was that
> the *agreed fix* had lapsed: no directory-taking flag was ever added, and the PR carrying it
> (`Fixes #2427`) was closed unmerged by an inactivity sweep six weeks before this triage. When
> a thread has already diagnosed the behaviour, re-confirming it adds nothing; check what
> happened to the resolution instead — the linked PRs, the planned doc change, the proposed
> flag. `gh api repos/<repo>/issues/<N>/timeline` lists every cross-reference.

> **Not every repro is a shader.** Command-line, build-system and API issues are still
> triageable, but `cmd.txt` assumes one dxc invocation over HLSL, and a shell will rewrite the
> very thing under test. #2427 had to be driven through `cmd.exe` verbatim, because PowerShell
> re-quotes arguments and silently repairs the bug. Keep the raw invocation in its own script
> next to the issue, and record which shell produced the result.

**Judge a `does-not-repro` against the configuration the reporter used.** A Debug build is the
right ground truth for asserts, but it is the *wrong* one for issues the reporter says only
fail in Release. Where the report is configuration-dependent or non-deterministic, test the
release binaries and repeat the run; a single clean pass is not evidence of a fix. Prefer
`inconclusive` over an unearned `does-not-repro`.

> **A nondeterministic bug makes single-run probes worthless — use `--repeat`.**
>
> ```bash
> python triage.py run    --issue <N> --repeat 25
> python triage.py bisect --issue <N> --repeat 10 --linear
> ```
>
> `--repeat` runs the repro up to N times and reports the symptom if *any* run shows it,
> short-circuiting on the first sighting so a reproducing release stays cheap.
>
> Measured on #3768, whose heap corruption fires on 68–82% of runs in the affected releases:
> a one-shot probe calls a *reproducing* release clean roughly a quarter of the time. During a
> linear scan that does not just add noise, it **invents release boundaries that do not
> exist** — an unlucky probe looks exactly like a fix.
>
> Repeats are also what converts a clean result into evidence. Absence of a crash means
> nothing until you know the per-run hit rate: at ~70%, thirty consecutive clean runs has
> probability ~2e-15, so it is a real finding rather than an absence of one. Measure the rate
> on a known-bad release first, then quote it.
>
> Reach for it whenever the reporter says "intermittent", "sometimes", "flaky", or names heap
> corruption, uninitialised memory, ASLR or threading. Do not use it as a blanket default —
> it multiplies the cost of every probe.

### 6. Locate the transition

```bash
python triage.py bisect --issue <N>
python triage.py bisect --issue <N> --linear    # non-monotonic history
python triage.py bisect --issue <N> --repeat 10 # nondeterministic symptom
```

Checks both endpoints first and short-circuits when they agree, so an always-broken or
never-implemented issue costs only two runs. Reports `fixed-in <tag>`, `regressed-in <tag>`,
`always-repro'd`, or `never-repro'd-in-releases`. Releases download lazily and are cached
across issues.

> **A probe only counts if that release actually compiled the repro.** A release that predates
> the target profile, or that lacks the feature entirely, rejects the input without ever
> reaching the code under test — and fails in a way no symptom predicate matches, so it scores
> as `no-repro` and **fakes a regression**. The runner classifies these as `invalid-probe`;
> `bisect` trims them off the ends of the range and reports how many it skipped.
>
> Measured on #3873: every release up to v1.6.2112 "fixed" it purely because its repro targeted
> `ps_6_7`, which did not exist yet — `error: invalid profile ps_6_7`. Retested at `ps_6_0`,
> the oldest release hangs, so it had in fact always reproduced. On #3768 the same trap wore a
> different face: v1.4.1907 answers `SPIR-V CodeGen not available`.
>
> **Prevention:** target the repro at the oldest profile and flag set that still shows the
> symptom, not the newest one the reporter happened to use.

> **The same trap fires one level up, in the front end.** A release predating a language
> *feature* — a type, an intrinsic, an attribute — rejects the repro with an ordinary semantic
> diagnostic, not a profile error. Measured on #3038: v1.4.1907 answers `use of undeclared
> identifier 'RayQuery'` because DXR 1.1 did not exist yet. Scored as a clean run, that turns
> "always reproduced as far back as is checkable" into a spurious "regressed in v1.5.2010".
> `invalid-probe` detection therefore also matches `use of undeclared identifier`,
> `unknown type name`, `no member named` and `no matching function for call to`.

> **An absence-based predicate is satisfied for free by a compile that never got started.**
> If the symptom is that something is *missing* (`not_contains`, `not_regex`, or an inverted
> `contains`), then any release that fails to parse the repro emits no match either — and
> scores as a textbook reproduction. #1877's predicate is `not_contains fptosi`; a release that
> rejected the input would have "reproduced" it perfectly. The runner now reclassifies such a
> probe as `invalid-probe` when the compile also failed. Prefer a positive predicate where one
> exists, and always confirm the probe actually emitted DXIL.

> **Binary search assumes the symptom is monotonic. Fix-then-revert issues are not.** With a
> non-monotonic history, binary search returns an arbitrary boundary — and when both endpoints
> agree it short-circuits to "never reproduced", missing a real window entirely. Use `--linear`
> whenever the issue history mentions a fix, a revert, or a re-opening. It costs one run per
> release, but every release is cached after the first issue that needs it.
>
> Measured on #3768: clean → **broken in v1.6.2104 and v1.6.2106** → clean from v1.6.2112. A
> binary search sees a clean v1.5.2010 and a clean v1.9.2607 and concludes the bug never
> existed. The linear scan found the two-release window, which matched the report date and
> turned the issue into the batch's one closable result.
>
> `--linear` and `--repeat` compose, and on #3768 both were needed: the scan has to visit every
> release *and* probe each one enough times, or an unlucky run inside the broken window closes
> it prematurely and reports a one-release blip.

**The bisection floor is v1.4.1907 (2019-07)** — the oldest release shipping a usable `dxc`.
For issues predating it, `always-repro'd` means "for as long as it is possible to check", and
must be reported that way rather than as "since it was filed". For SPIR-V issues the floor is
higher still, since v1.4.1907 has no SPIR-V codegen.

### 7. Publish a shareable repro

```bash
python triage.py godbolt --issue <N>
```

Compiles the repro on [Compiler Explorer](https://godbolt.org), prints the result per
compiler, and stores a short link on the issue row. Default compilers are `dxc_1_6_2112`
(CE's oldest) and `dxc_trunk`. **The link is verified before it is handed over** — never
publish one without checking it shows what you claim.

**Always write `issues/<nnnn>/godbolt-note.txt`.** It is prepended to the shared source as a
`// What to look for` banner. A bare link to a shader that compiles "fine" invites the reader
to conclude the bug is gone — name the exact thing to check: the `HLSL Bind` column, the empty
`main()`, the abnormal exit code. Keep it in its own file rather than in `repro.hlsl`, so the
repro stays exactly what was tested locally; the banner is presentation, not evidence.

**Not every issue deserves a link.** If the whole behaviour is a one-line error, or the issue
is a pure feature request with nothing to see, record that decision instead of forcing one:

```bash
python triage.py godbolt --issue <N> --skip "pure feature request; nothing to see"
```

But revisit that call once you have tried a Clang pane. #1627 was skipped as "just an
unknown-argument error" — until Clang turned out to *have* the capability, reachable as
`-Xclang -include`, which reframed the request from "add a feature" to "expose an existing one
at the driver level". A comparison can create something worth seeing where there was nothing.

Use `--compilers` for anything more interesting; the spec is saved to the issue's
`godbolt.txt` and reused afterwards. `id:<args>` overrides the arguments for one compiler,
which is how a contrasting compiler is placed beside DXC:

```bash
# "FXC diagnoses this and DXC does not" — shown, not asserted
python triage.py godbolt --issue 1306 \
  --compilers "fxc_10_0_19041:/T cs_5_0 /E main,dxc_1_6_2112,dxc_trunk"
```

A link that makes the bug *visible* beats one that merely reproduces it. For wrong-code
issues, point at the evidence in the DXIL; output filters are deliberately configured to keep
DXC's comment-based tables, which CE strips by default.

**Consider adding a Clang pane.** CE carries `hlsl_clang_trunk` and
`hlsl_clang_assertions_trunk`. Because HLSL support is being rebuilt in Clang, "does this still
reproduce in DXC?" and "has the successor compiler already answered this?" are different
questions, and the second is often the more useful one for an old issue:

```bash
python triage.py godbolt --issue 708 \
  --compilers "dxc_1_6_2112,dxc_trunk,hlsl_clang_trunk"
```

Worth doing when the issue is a missing diagnostic, an FXC/DXC disagreement, a language-design
question, or is labelled `check-in-clang`. Clang may reject what DXC accepts (which answers an
open design question), or share the gap (which shows it is still live in the new front end).
The two Clang builds usually agree; prefer one pane unless they differ.

**When Clang cannot compile the repro's shader stage, translate it — or omit the pane.**
Clang's stage support is uneven: compute is complete, pixel parses but the backend cannot lower
any shader writing `SV_Target`, and geometry is not supported at all. A pane full of errors
about the stage says nothing about the issue, so:

1. **Prefer a compute-shader translation.** If the construct under test is not stage-specific,
   restate it as a `[numthreads]` entry point writing to an `RWBuffer`. All three compilers
   then answer the same question on the same input. This is usually *stronger* evidence, not a
   compromise — #1702's compute variant made DXC emit `float undef` stores that its own
   validator rejects, where the pixel version merely produced an empty `main`.
2. **Otherwise omit the pane.** #1768 is inherently GS-specific (`PointStream`,
   `maxvertexcount`) and its construct compiles cleanly as a compute shader in both compilers,
   confirming a translation would exercise a different path and mislead.

**A missing Clang repro is better than a noisy, useless one.** Check the translation still
reproduces before adopting it, and keep the stage-accurate original as the local evidence.

> **A Clang error is not evidence until you have a control.** Clang's DXIL backend is
> incomplete, so it fails on inputs that have nothing to do with the issue. #1702 looked like
> Clang diagnosed it — `Unsupported intrinsic llvm.dx.store.output.v4f32 for DXIL lowering` —
> until a one-line `float4 main() : SV_Target { return 0; }` produced the *same* error.
> **Before believing any cross-compiler difference, compile something trivial with the same
> flags and confirm the difference does not survive.** Where the backend is the blocker,
> `-fsyntax-only` asks the narrower question the front end can still answer.

The same discipline applies to argument handling: `dxc_trunk` appears to accept `/FI` silently,
but so does `/ZZZNONSENSE` — on CE's Linux builds a `/`-prefixed argument looks like a path, so
MSVC-style flags are not testable there at all.

Three limits, all of which bound how much the link can be trusted:

| Limit | Consequence |
| --- | --- |
| CE runs **Release** builds | Debug-only asserts look clean. CE corroborates the local build, never overrules it |
| CE's oldest DXC is **1.6.2112** | Cannot date a fix older than that; use `bisect` for history |
| CE is **single-file** | Multi-file repros are partial at best; say so in the notes |

`dxc_trunk` is a rolling build and is not reproducible over time. It can even vary between
runs of the same input — #1768 alternates between `SIGSEGV` and a bad-cast error. Do not pin
an exact trunk symptom in anything you publish; describe the class of failure instead.

### 8. Review the labels

```bash
python triage.py labels --refresh          # re-fetch the taxonomy, then list it
python triage.py labels --issue <N>        # current vs proposed for one issue
```

**Never hardcode a label list, and never work from memory or from a previous batch.** Labels
get added, renamed and retired; the taxonomy is repo state. `labels` re-fetches it, warns when
the cache is over a day old, and flags labels on an issue that no longer exist.

Proposals are recorded through `verdict` and **validated against the live set** — an unknown
label is rejected with a near-miss suggestion rather than silently stored:

```bash
python triage.py verdict --issue 1702 \
  --labels-now "bug,shader-linking" \
  --labels-add "fxc-disagrees,incorrect-code,correctness,check-in-clang" \
  --labels-remove "shader-linking"
```

What to look for, having just established what the issue actually does:

- **Severity that the triage contradicts.** A crash labelled only `bug` understates it.
- **Labels the evidence does not support.** Removals need a reason from the issue itself, not
  a hunch — check the body and every comment before proposing one, and say in the draft that
  you may be missing history.
- **Labels that record the *finding*,** e.g. an FXC/DXC difference, or "the fix belongs in
  Clang". These are the ones that make the backlog searchable later.
- **Missing routing labels** on issues that are really feature requests.

Read the label *descriptions*, not just the names — several are narrower than they sound. For
example `validation` means **DXIL validation** specifically, not "the compiler should validate
this"; a request for a compile-time diagnostic is mislabelled by it.

Recorded, **never applied**.

### 9. Draft the issue comment

Write `issues/<nnnn>/comment.md` — what a maintainer could post, ready to use. Open it with
a **rendered** warning callout, not an HTML comment: these files are committed and browsable
on github.com, where `<!-- ... -->` is invisible to exactly the audience that most needs to
know a draft is a draft.

```markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#1803](https://github.com/microsoft/DirectXShaderCompiler/issues/1803).
```

Name the issue, so a file found on its own is traceable. Claim only what the file can know:
"unposted" is not verifiable by a file that outlives its own posting.

- Lead with the verdict and the version tested (`still reproduces on main (…, <sha>)`).
- Show the evidence: the annotated link, and the two or three lines of output that matter.
- Say what changed since the report if the symptom has moved — that is often the single most
  useful thing in the comment.
- Close with the label suggestion and its one-line justification.
- Where the next step is a product or language decision, say so; do not pre-empt it, and
  never promise a fix or a timeline.
- Quote compiler output **verbatim and verified**, not from memory. Re-run it.
- **Be concise.** Do not restate what the code block or the linked page already shows. Cut
  hedging, preamble, and any sentence that survives only to introduce the next one.

**End every draft with the AI-assistance disclosure.** These comments land on other people's
issues, and a reader is entitled to know how the evidence was produced — not least because it
tells them what kind of mistake to look for. Use a consistent trailer, separated by a rule:

```markdown
---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
```

Keep it short and factual. It is a provenance note, not an apology or a disclaimer — do not
hedge the findings themselves, which are verified by running the compiler. The invitation to
flag errors is the useful part: it is what turns disclosure into something the reader can act
on.

These are drafts for a human to review and post. **Posting them is not part of this skill.**

### 10. Have a different model review the drafts

**Required, not optional.** Before the drafts go anywhere near a human reviewer, hand them to
a separate agent running a *different* model. The author of a draft is the worst judge of its
length: you already know why every sentence is there, so the redundant ones still read as
necessary.

Send the reviewer:

- the paths to every `comment.md` in the batch, and the `notes.md` files as background;
- who the audience is — maintainers plus original reporters, on a public repo, some threads
  years old;
- that **concision is the primary criterion**, and that the goal is subtraction: it must not
  propose new sections or new information;
- what is off-limits to cut — the specific technical evidence (error codes, version numbers,
  symbol and file names, IR snippets) and any finding that the issue text is stale;
- a demand for quoted current text plus exact replacement text, not general advice.

Then **apply the review with judgement, not wholesale**. In practice it is reliably right
about verbosity and about unsupported claims, and unreliable about domain specifics — expect
it to propose reverting a correction it lacks the context for, and to flag genuine hedging that
is actually deserved caution. Two categories worth accepting almost every time:

- **Speculative root-cause or effort claims.** "Suggests memory corruption", "looks cheap",
  "was probably a development-branch symptom". State the observation and the limits of what
  was tested; drop the diagnosis.
- **Adverbs the evidence no longer supports.** "Silently" is wrong the moment the compiler
  emits any warning at all.

Where you reject a suggestion, know why. Record anything that changes the method in the batch
report.

**Re-run the review when a draft changes materially.** A draft rewritten after new evidence has
not been reviewed, and the second pass finds different things than the first. Brief the reviewer
with the *current* evidence — it flags anything absent from its brief as unsupported, so an
under-briefed reviewer generates false positives against claims you have in fact verified. Two
recurring classes worth accepting:

- **Scope creep in claims about history.** "Gone from every release" when only v1.4.1907 onward
  was tested; "unchanged since 2019" when the endpoints, not every release, were checked.
- **Rhetorical flourishes.** A comment landing on a stranger's multi-year-old issue should read
  as a report, not an argument. Keep the finding, drop the point-scoring.

And two it gets wrong often enough to check: it will paraphrase away literal diagnostic text
(`error X3072: ...`) that people actually search for, and it will read a caveat aimed at future
triagers as an accusation against past ones. It also tends to cut *actionable* caveats — the
one remaining test that would settle a verdict, or a warning about a trap that has already
produced a wrong answer once. Those earn their space; cut the epistemics around them instead.

A third pattern, seen in batch 002: it is good at catching claims that are subtly **wrong about
what correct behaviour would be**. "No release has ever compiled this correctly" is wrong when
the input is invalid and *should* be rejected; "only DXC fails to say so" is wrong when DXC does
emit an error, just a bad one. These read fine until someone who knows the compiler reads them.

**Check the review in both directions: it can introduce an error while removing one.** Batch 003
tightened #2427 to "Through `cmd.exe`, the trailing backslash escapes the closing quote" — but
the escaping is CRT and shell argv splitting generally, not a `cmd.exe` quirk; `cmd.exe` was
only the harness that reproduced it faithfully. Concision pressure pulls toward attributing a
general behaviour to whatever specific thing the sentence already mentions. Re-read every
accepted rewrite against the evidence, not just against the original wording.

### 11. Write it up

Create `issues/<nnnn>/notes.md` — what was tested, what happened, on which compilers, and the
assessment. Corroborate from source where you can: showing that a field is parsed but never
read is far stronger evidence than an output observation. Then record the verdict:

> **A negative result from a command that errored is not a negative result.** Attributing
> #3038's fix to a PR, `git merge-base --is-ancestor <sha> origin/release-1.8.2505` exited
> non-zero and was briefly read as "the fix is not in that release" — refuting the hypothesis.
> In fact the ref did not exist locally, because the release branches had never been fetched.
> The command was answering a different question. Once fetched, the ancestry check confirmed
> the opposite. Before believing a negative, check that every input to it resolved: that the
> ref exists, the file was found, the flag was parsed. This is the same failure as the
> `invalid-probe` trap, one layer out — a tool that never ran the test still returns something
> that looks like an answer.

> **When attributing a fix to a specific change, state the size of the window.** A verified
> ancestry check proves a commit is *in* the fixing release, not that it *is* the fix. #3038's
> window between v1.8.2502 and v1.8.2505 holds 162 commits. Say so, and call the attribution
> strong rather than certain unless you built at the commit and tested it.

```bash
python triage.py verdict --issue <N> --status repros --repro-quality complete \
  --history "always-repro'd" --confidence high --suggested-action still-valid-keep-open \
  --summary "..." --notes-path issues/<nnnn>/notes.md --triaged-with-commit <sha>
```

Suggested actions (recorded, **never applied**): `close-fixed`,
`needs-repro-from-reporter`, `still-valid-keep-open`, `needs-human-judgement`,
`duplicate-of #N`, `enhancement-not-bug`.

## Batch report

Write `reports/batch-NNN.md` covering: ground truth used (commit + version), a summary table
with a Compiler Explorer link per issue, per-issue findings, the **draft comments**, and —
importantly — **what the batch taught you about the method**. Predicate bugs and methodology
gaps found while triaging are as valuable as the verdicts, and should change how the next
batch is run.

Splice the drafts in from their source files rather than copying them, so the report and the
artifacts cannot drift:

```bash
python scripts/render_comments.py <batch>     # e.g. 002
```

Re-run it after **every** edit to a `comment.md`.

Flag prominently any issue whose **text no longer matches its behaviour**. These are the
highest-value findings: the defect is real, but anyone spot-checking against the description
will wrongly conclude "cannot reproduce". This includes the **title**: #3444 has claimed since
2021 that `float2`/`float3`/`float4` work, and none of them do.

Always state the sampling bias. Verdicts from the oldest issues do not generalise to the
backlog.

## Useful queries

```bash
python triage.py status
python triage.py sql "SELECT number, status, history FROM issues WHERE status='does-not-repro'"
python triage.py sql "SELECT number, fixed_in FROM issues WHERE history='fixed'"
```

## Selecting a batch

```bash
gh issue list --repo microsoft/DirectXShaderCompiler --state open --limit 20 \
  --search "sort:created-asc" --json number,title,createdAt,labels
```

Mix the batch deliberately — an all-oldest batch is unrepresentative and may not exercise
bisection at all. Include `crash`, `spirv`, and mid-age issues so the workflow is tested where
"no longer reproduces" is actually plausible.
