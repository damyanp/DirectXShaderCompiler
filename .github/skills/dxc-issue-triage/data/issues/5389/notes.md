# Notes — #5389: `as` casts on integer constant swizzles produce invalid DXIL

## Ground truth

`main-debug` registered at `git_commit` **89e2f98e29c289ae8ad9e00dd310104fea9fd7df**
(public upstream, verified `git merge-base --is-ancestor` against `upstream/main`, exit 0).
Local binary self-reports a fork-local commit fragment (`triage, 7665270b9`) that does not
resolve publicly; equivalence to the cited public commit was proven with a controlled diff:
`git diff --name-only 7665270b990f 89e2f98e29c2` returns **nothing outside
`.github/skills/dxc-issue-triage/`**, while the same diff against the skill's previously-used
ground truth `13730886e` (the control) returns 21 real source/test files
(`lib/DxilValidation/DxilValidation.cpp`, `tools/clang/lib/AST/HlslTypes.cpp`, etc.) —
confirming the diff is capable of detecting a difference and that none exists against the
cited commit. `dxc --version` on the build:
`dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)`.

## Repro

`repro.hlsl` is the reporter's own minimal case, taken verbatim from the 2024-09-05 comment
(https://github.com/microsoft/DirectXShaderCompiler/issues/5389#issuecomment-2332351850):

```hlsl
RWByteAddressBuffer sb : register(u0);
[numthreads(1, 1, 1)]
void main() {
  sb.Store(0, asuint(int2(123, 123))); // Okay
  sb.Store(0, asuint((123).xx)); // Boom
}
```

`cmd.txt`: `-T cs_6_0 -E main repro.hlsl` (the reporter's target profile; no `-HV`, i.e.
default/pre-2021 language mode, matching every one of the thread's own repros).

`control-typed-literal.hlsl` keeps only the first ("Okay") line — an explicitly int32-typed
literal (`int2(123, 123)`) fed to the same `asuint` — as the negative control. It compiles
clean on `main-debug` (`variant-control-typed-main-debug.txt`, `--expect no-match`, passed).

`case-scalar-x-helper-fn.hlsl` reproduces a second, narrower repro from the thread (the
`f(b)/f(c)/f(d)` helper-function case using scalar `.x`, not `.xx`) for a specific claim check
(see "Checking a specific maintainer claim" below).

## Predicate

`match.json` is `any_of[internal_failure, all_of[contains "Invalid record", contains
"Validation failed"]]`. Rationale (see the predicate's own `note`): the same root cause has
two build-config-dependent signatures. In a Debug/assert-enabled build (our ground truth),
`CallInst::init`'s "Calling a function with a bad signature!" assert fires before DXIL
validation ever runs — an `internal_failure` (measured: exit `3758096385` =
`0xE0000001`, `internal_failure`'s C++-exception form, stderr
`Internal compiler error: LLVM Assert`, see `out-main-debug.txt`). In a Release/NDEBUG build
(every stable release binary, and Compiler Explorer), the assert is compiled out, the
malformed call reaches the DXIL bitcode writer/reader, and DXIL validation catches it as
`Invalid record` / `Validation failed.` (measured on every one of the 20 stable release
captures, e.g. `out-v1.4.1907.txt`, `out-v1.6.2112.txt`). Neither clause alone would cover
both build configurations. The predicate's self-test (`control-typed-literal.hlsl`) confirms
it does not fire on the explicitly-typed control.

## Ground-truth run and bisection

`run --issue 5389` on `main-debug`: **repro** (`out-main-debug.txt`, exit `0xE0000001`,
internal failure).

`bisect --issue 5389 --linear` (linear scan chosen because this is an "always reproduces,
maintainer proposes closing" style issue and endpoint-only binary search could hide a
narrower window — though in the event every release agreed): **always-repro'd across
v1.4.1907..v1.9.2607**, all 20 probeable stable releases score `repro`, **zero
invalid-probes** (RWByteAddressBuffer/asuint/cs_6_0 have existed since the bisection floor,
so nothing here predates a feature). 5 prereleases correctly excluded from the search by
policy (none of them are named by the issue text, so no `release-policy.json` opt-in).
1 release (`v1.2.0-alpha`) skipped as having no usable `dxc` asset. This is a defect that has
existed for the entire probeable release history and, per the maintainer's own comments
below, was never targeted for a backport fix.

## Compiler Explorer corroboration

Link: https://godbolt.org/z/Y45Yhd3P5 (verified via shortlink read-back, no warning).
4 panes over `repro.hlsl` (all `-T cs_6_6 -E main`, CE's oldest DXC plus current trunk):

| pane | args | exit | result |
| --- | --- | --- | --- |
| `dxc_1_6_2112` | (default) | 5 | fails: `Call parameter type does not match function signature!` / `Validation failed.` |
| `dxc_trunk` | (default) | 5 | fails: `Invalid record` / `Validation failed.` |
| `dxc_trunk` | `-HV 2021` | 5 | **still fails**, same as default |
| `dxc_trunk` | `-HV 202x` | 0 | clean |

(`manual-case-godbolt-verify.txt` has the full text of every pane.) This corroborates the
local ground truth: the bug is present today on CE's rolling trunk build in the default
language mode used by every repro in the thread, and — importantly — **`-HV 2021` alone
does not fix it**; the fix damyanp linked
(https://github.com/microsoft/DirectXShaderCompiler/issues/5389#issuecomment-2341556277,
shortlink `vdnde81co`, fetched via `GET /api/shortlinkinfo/vdnde81co` and confirmed to compile
this exact source with `-T cs_6_6 -HV 202x`) uses the newer, still-experimental `202x` mode,
not the shipped HLSL 2021 (`-HV 2021`). Locally reproduced the same distinction on
`main-debug`: `variant-hv2021-main-debug.txt` still scores `repro` (a declared
`--hypothesis`, refuted — I expected `-HV 2021` to fix it per a loose reading of the thread,
and it does not), `variant-hv202x-main-debug.txt` scores `no-repro` (`--expect no-match`,
passed). This distinction (2021 vs 202x) is worth stating plainly in the draft, since a
reader skimming "resolved in HLSL 2021" (a plausible paraphrase of the thread) would be wrong.

Two message-text observations, informational only (not scored — CE panes are not `run`
probes): CE's Linux `dxc_1_6_2112` prints a different, more specific diagnostic (`Call
parameter type does not match function signature!`) than the literal `Invalid record` every
Windows build (local ground truth and all 20 release captures) prints for the same defect —
consistent with the skill's standing warning that validator message text is not portable
across platforms. Both wordings still satisfy the "fails DXIL validation" characterization
used in the draft; only the literal-string predicate clause is platform-specific, which is
exactly why `main-debug`'s own probes (not the CE panes) drive the bisection verdict.

No Clang pane was published as a meaningful comparison. Clang's independent (in-progress)
HLSL front end targets its own `dxil-unknown-shadermodel` triple with a from-scratch
intrinsic/type implementation (its output for this shader is a completely different
generated-IR shape — `llvm.dx.resource.handlefrombinding`, etc. — with no clang.hl-style
literal-folding to compare against DXC's legacy 64-bit-literal rule at all). Comparing
Clang's result would answer a different question ("does the from-scratch reimplementation
avoid the same class of bug") rather than corroborate whether *this specific pre-2021
literal-typing rule* still misbehaves, so it is omitted rather than published as noise; see
`manual-case-godbolt-verify.txt`'s `hlsl_clang_trunk` pane for the raw output if useful later.

## Checking a specific maintainer claim

damyanp separately said one specific repro from the thread — the `f(b)/f(c)/f(d)` helper-
function case using scalar `.x` (comment
https://github.com/microsoft/DirectXShaderCompiler/issues/5389#issuecomment-2332484091,
CE shortlink `TK15ajfaa`, fetched and confirmed to be `-T cs_6_6`, **no** `-HV` override, i.e.
default language mode) — "doesn't repro on the latest DXC". Testing that exact case (as
`case-scalar-x-helper-fn.hlsl`) on today's CE (`dxc_1_6_2112` and `dxc_trunk`, both default
mode) confirms this: both compile clean (`out=0`), with the value stored as a plain
`float 123.0` — no bitcast, no vector at all, because `.x` on a scalar is an identity
operation and does not force a vector-typed intermediate the way `.xx` does. Testing the
*same* case on `main-debug` (`variant-scalarx-default-main-debug.txt`,
`variant-scalarx-cs66-default-main-debug.txt`, `variant-scalarx-cs66-zi-main-debug.txt`,
each declared `--hypothesis --expect no-match`) **still asserts** — all three hypotheses were
refuted. No source diff exists between the ground-truth commit and CE's self-reported trunk
commit (`3bc198b55`, confirmed a descendant of `89e2f98e` by
`git merge-base --is-ancestor`) that touches literal typing, swizzles, `asuint`, or bitcasts
(`git diff --stat 89e2f98e29c2 3bc198b55` — 22 commits, all LinAlg/SM6.10 test/tooling
changes, zero touching `tools/clang/lib/{Sema,CodeGen,AST}` or `lib/HLSL`), and CE panes with
the same `-Zi -Qembed_debug` flags CE always appends did not change the local result either.
This narrower discrepancy (scalar `.x` case: clean on CE's Release Linux build, asserts on
local Debug Windows build) is left **unresolved** — it does not affect the headline verdict,
since the primary, thread-titled repro (the `.xx` vector case) reproduces identically on
every measured build, Debug and Release, old release and current trunk — but it means
damyanp's narrow claim about that one variant is corroborated for a Release build and not
contradicted for Debug; a Debug-vs-Release difference for that specific scalar sub-case is
plausible but not proven here and is flagged as an open question rather than asserted either
way.

## Reading the issue thread

Chronology, condensed: filed 2023-07-05 with a Dawn/Tint-generated repro and a "warning" +
"Invalid record"/"Validation failed" (Release-build) failure. s-perron (2023-07-05) and
amaiorano (2023-08-25, 2023-08-25) narrow it to `(0).xx`/`(123).xx` vs. `int2(...)`/`(0u).xx`.
amaiorano (2023-08-28) finds the Debug assert and its exact text/line, and notes
`amaiorano` (2023-09-05) also affects `RWByteAddressBuffer` calls directly (not just
textures), and that it needs a non-zero literal for the buffer-store form. amaiorano links a
duplicate, #5082 (filed by ben-clayton), on 2023-09-05. amaiorano revisits a year later
(2024-09-05, twice) with the minimal `(123).xx`/scalar-`.x` cases and the IR excerpt showing
the `<2 x i64>` vs `<2 x i32>` mismatch, and proposes 3 candidate fixes (constant-swizzle
should stay 32-bit / `asuint` should truncate 64-bit / `ParseAST` should insert an implicit
cast). damyanp (2024-09-10) replies this is fixed by HLSL 2021 -- 202x is what was actually
tested — and separately that the scalar `.x` case doesn't repro on the-then-latest DXC (see
above; this is a narrower claim than "the issue is fixed" and is treated as such).
amaiorano (2024-09-10) pushes back that non-2021 mode is still broken and should count as a
bug. damyanp (2024-09-12) moves the issue to "dormant": the fix is the HLSL 2021 language
change (i.e., no backport planned for the legacy literal-typing rules), but "if someone wants
to attempt to fix this specific codegen/assert issue then we'd consider reviewing and
accepting it" — an explicit invitation for a community contribution, not a "won't fix".

Note the "resolved in HLSL 2021" phrasing in damyanp's comment is a plausible loose
paraphrase for "resolved by the same-era language change", but the actual tested/linked mode
is `-HV 202x`, and `-HV 2021` itself does not fix the defect (measured above) — worth
surfacing explicitly since a reader could otherwise assume the stable `-HV 2021` flag is a
usable workaround.

## text_stale

None. The issue title and body accurately describe the current behavior (both the release
validation failure and the Debug assert still occur exactly as described), and the thread's
own later comments (through 2024-09-12) already correctly track the current state — nothing
in the visible thread is stale relative to what was measured here.

## The linked duplicate, #5082, was closed for the same underlying defect

amaiorano's 2023-09-05 comment links #5082
(https://github.com/microsoft/DirectXShaderCompiler/issues/5082, filed 2023-03-06 by
ben-clayton, i.e. **earlier** than #5389) as reporting "this issue... a while ago". Reading
#5082 (read-only `gh issue view`) confirms it is the same underlying defect at a different
call site: a bare unsuffixed integer literal swizzle (`(1).xx`, `(1).xxx`) passed as a texture
sampling intrinsic's `offset` argument keeps a 64-bit type and produces the identical
"Call parameter type does not match function signature!" / "Module bitcode is invalid." DXIL
validation failure. #5082 was **closed as `COMPLETED`** on 2024-08-28, on damyanp's comment
"This is resolved in HLSL 202x" with a godbolt link — the same reasoning pattern later
applied to #5389 on 2024-09-10. The difference is what happened next: on #5389, amaiorano
pushed back that the default/legacy mode remains broken, and damyanp's follow-up (2024-09-12)
kept #5389 open as "dormant" rather than closing it, explicitly distinguishing "the language
mode fixes this" from "the codegen/assert bug in the legacy mode is fixed". #5082 received no
equivalent push-back and was closed. This is stated here as an observed fact about the two
threads, not a recommendation to reopen #5082 or to change #5389's status — that is a
maintainer call, not a triage one — but it is relevant context: the same class of defect has
recently been treated as both "resolved" and "still open, dormant" depending on which thread
a reader lands on.

## Verdict summary

- status: `repros`
- repro-quality: `complete` (reporter's own minimal, exact HLSL and command line)
- history: `always-repro'd` v1.4.1907..v1.9.2607 (linear scan, no invalid probes), corroborated
  today on Compiler Explorer's `dxc_trunk`
- confidence: `high`
- suggested action: `still-valid-keep-open` — the maintainer has already stated a position
  (dormant; fixable only by contributed patch or the 202x language change) and there is
  nothing left for triage to add beyond confirming the bug is unchanged; this is not a
  "needs human judgement" case since the maintainer's judgement is already recorded in the
  thread, and it is not `close-fixed`/`duplicate-of` since #5389 predates and is more
  thoroughly documented than #5082 (which the thread itself links as the duplicate of *this*
  issue, not the other way around).
