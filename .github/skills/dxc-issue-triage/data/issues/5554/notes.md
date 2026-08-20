# #5554 — C++11 enums don't work as integer constants as expected

## Summary of what was tested

The issue is a **multi-ask** thread (SKILL.md step 4) that changed shape three times. The
issue body's own godbolt link doesn't declare an `enum class` at all (confirmed at the time by
a maintainer comment), so the thread only reaches a real repro in later comments, and the
asks keep narrowing:

1. **Ask A** — `partiboi[KEK::WAIT]` (scoped-enum array index, no cast) and
   `test<KEK::COUNT>` (scoped-enum template argument for a plain `int` parameter, no cast)
   both rejected; reporter's own next comment shows both work once cast to `(uint)`.
2. **Ask B** — `template<KEK sz>`, i.e. the *template parameter itself* declared with a
   scoped-enum type, still rejects `test<KEK::COUNT>` even though no conversion is needed at
   all (the argument already has exactly the declared type).
3. **Ask C** — a generic `integral_constant<T, T val>` pattern instantiated with a plain enum
   (`godbolt.org/z/EGaesxvE1`, posted directly on #5554) reported "busted"; the duplicate
   issue #6706 (closed as a duplicate of #5554) narrows this to a clean scoped/unscoped
   contrast pair and carries a maintainer statement (`damyanp`): *"While we'd consider
   accepting PR that addresses this issue, we're not planning on investing in fixing this in
   DXC. This won't be an issue in clang."* That is a roadmap statement, not a claim the bug is
   fixed.
4. The thread's last comment (`llvm-beanz`, 2026-02-13, "Oops... wrong window. Sorry for the
   false hope.") is not a substantive update.

## What actually reproduces, and what doesn't

- **`variant-index-only.hlsl`** isolates the array-index half of Ask A with no template
  involved at all: `partiboi[KEK::WAIT]` (no cast) fails with
  `error: array subscript is not an integer`; `partiboi[(uint)KEK::WAIT]` on the same line
  compiles. **This matches standard C++**, confirmed against real gcc
  (`manual-case-cpp-control.txt`, case `array-index-no-cast`): gcc rejects the identical
  construct with the identical wording, because a scoped enum does not implicitly convert to
  an integral type for subscripting. Not a bug.
- **`variant-ask-a-no-cast.hlsl`** and **`variant-ask-b-enum-template-param.hlsl`** both fail
  with a *different* diagnostic from the array-index one:
  `error: non-type template argument of type 'KEK' is not an integral constant expression`,
  pointing at `test<KEK::COUNT>` — the template-argument use, not the array index. This is the
  same diagnostic text as the primary repro (`repro.hlsl`), just naming `KEK` instead of
  `ENUM`; `match.json`'s `\w+` deliberately covers both. Crucially, `variant-ask-b` uses
  `template<KEK sz>` — the parameter is declared with the *exact* enum type, so no implicit
  conversion is even in question. **Verified against real C++** (`manual-case-cpp-control.txt`,
  case `enum-as-exact-nontype-template-arg`): gcc accepts the identical pattern cleanly. So
  unlike Ask A's array-index half, this half is a genuine DXC/C++ divergence, not a design
  choice.
- **`variant-as-posted-integral-constant.hlsl`** (`repro.hlsl` before this triage renamed it) is
  the *exact* source posted as `godbolt.org/z/EGaesxvE1` directly on #5554. It uses a **plain**
  `enum Test`, not `enum class`, and it **compiles cleanly** (exit 0) — the "busted" claim does
  not hold for the literal posted repro. `--text-stale` is not warranted here, though: the
  filing predates neither the report date (Ask C's own comment is 2024-07-09) nor is the body
  itself wrong — the comment's own repro just doesn't demonstrate what the comment's prose
  claims, a fact worth surfacing in the comment.
- **`variant-unscoped-6706.hlsl`** (plain `enum`, otherwise byte-identical to `repro.hlsl`) is
  the anti-vacuity control and is confirmed clean at three points across the whole probed
  history: main-debug, v1.6.2112 (oldest probeable) and v1.9.2607 (newest stable) — the
  predicate discriminates specifically on scoped-vs-unscoped, not on the pattern in general.

## History

`bisect --linear` over `repro.hlsl` (`-HV 2021 -T cs_6_0 -E main`, chosen so the profile itself
doesn't gate the search — the original `cs_6_7`/`-spirv` combination from the thread's own
godbolt links needlessly narrowed it):

- v1.4.1907, v1.5.2010, v1.6.2104, v1.6.2106: `invalid-probe` — `Unknown HLSL version: 2021`.
  HLSL 2021 (which brought `enum class` and templates) did not exist yet; genuine feature
  absence, not evidence either way.
- v1.6.2112 (2021-12-08, the first release with `-HV 2021` and template support) through
  v1.8.2403.2: **repro**.
- **v1.8.2405: no-repro — but this is a confirmed invalid-probe, not a fix.** Its capture
  (`out-v1.8.2405.txt`) shows a *different* error entirely:
  `error: too many template parameters in template redeclaration`, because that release
  registers a builtin template named `integral_constant` (added by commit `d60dffef1` / PR
  #6156, "[SPIR-V] Implement SpirvType and SpirvOpaqueType") **in the default/global
  namespace**, colliding with this repro's own top-level `integral_constant`. Confirmed by
  re-running a byte-identical repro renamed to `my_integral_constant`
  (`variant-renamed-no-collision.hlsl`) against the *same* v1.8.2405 binary — it reproduces
  the real defect (`variant-renamed-no-collision-v1.8.2405.txt`). The namespace-pollution bug
  was itself fixed by commit `8b18659ae` / PR #6700 ("Avoid adding types to default
  namespace"), which is why v1.8.2407 onward show the real diagnostic again with no name
  collision. `d60dffef1` (2024-04-15) is an ancestor of v1.8.2405 and v1.8.2407 but not
  v1.8.2403.2 (`git merge-base --is-ancestor`); `8b18659ae` is the only commit in
  `v1.8.2405..v1.8.2407` touching `SemaHLSL.cpp`/`SemaTemplate.cpp`/`SemaDeclCXX.cpp`.
- v1.8.2407 through v1.9.2607 (current latest stable) and main-debug (`89e2f98e2`): **repro**.

So the corrected history is **always-repro'd, v1.6.2112..v1.9.2607 and main-debug** — the
`v1.8.2405` transition bisect reported is an instrument artifact from an unrelated,
already-fixed bug, not a regression-then-fix of this issue. v1.6.2112 (2021-12-08) predates
the 2023-08-05 filing by about 20 months, so this covers the issue's whole life on every
release that could even parse the input.

## Compiler Explorer

https://godbolt.org/z/bqbP386nM — `dxc_1_6_2112` (CE's oldest DXC) and `dxc_trunk` both show
the identical diagnostic. A `hlsl_clang_trunk` pane is also included and **compiles cleanly**
(only warnings, valid DXIL emitted) — confirming `damyanp`'s statement on #6706 that "this
won't be an issue in clang." Per SKILL.md step 8's guidance, `check-in-clang` is therefore
**not** proposed as a label: the comparison has already been run and reported, not left open.

## Labels

Kept `bug` and `hlsl2021` (both accurate). Added `type-system` — this is exactly the kind of
inconsistency that label describes: DXC's constant-expression evaluator does not treat a
scoped-enum enumerator as an integral constant expression in non-type-template-argument
contexts, while it does for a plain enum's enumerator of the same underlying type in the
identical position.

## Suggested action

`still-valid-keep-open`. This is a real, currently-reproducing DXC/C++ divergence (not a
design choice, unlike Ask A's array-index half), but a maintainer has already stated on the
duplicate #6706 that DXC itself will not receive further investment for it and that the
successor Clang front end does not have the gap — which this triage now confirms directly.
That is a roadmap decision already on record, not something this triage should second-guess;
it does not, however, mean the report is resolved on `main` today.

## What this triage could not determine

- Whether `enum class` as a non-type template parameter's *own declared type* (Ask B,
  `template<KEK sz>`) has ever been exercised by an internal test independent of the ICE
  question — both fail with the same ICE diagnostic here, so this triage cannot separate "the
  parameter type itself is rejected" from "the argument fails to convert" as two different
  underlying causes; they may be the same Sema code path or two.
- Whether any Clang-based `check-in-clang` HLSL test already covers this pattern by name (not
  searched; the CE `hlsl_clang_trunk` pane is corroborating but not exhaustive).

## Method note

See `method-notes.md` for the v1.8.2405 name-collision trap — it is a new specific instance
of the general "invalid-probe demotion misses an unrelated diagnosed error" class SKILL.md
already documents, worth flagging at collation because the marker that would catch it
("too many template parameters in template redeclaration") is not yet in
`UNSUPPORTED_MARKER_RE` and is arguably too repo-specific (tied to one now-fixed builtin
registration bug) to add there — a targeted control was cheaper here than a general marker.

Reviewed by: not yet run (step 10 is a batch/collation step, deliberately left for a
different-model review at collation time — see `reviewed_by` left blank in `verdict.json`).
