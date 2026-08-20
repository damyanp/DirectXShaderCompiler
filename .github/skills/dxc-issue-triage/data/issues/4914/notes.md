# Notes — #4914 "[feature request] Copying \"this\" fails"

## Summary

Confirmed reproduces on `main-debug` and on every one of the 20 stable DXC releases from
v1.4.1907 (2019-07, three and a half years before the report) through v1.9.2607 (2026-07-29):
a member function that returns `this` by value, or assigns `this` into an out-parameter by
value, fails with the exact diagnostic quoted in the issue,

```
error: cannot compile this aggregate expression yet
```

This is an ordinary Clang diagnostic delivered through the normal diagnostics engine (process
exit `0x80004005`/E_FAIL), not a crash or an assert — `match.json` uses `contains`, not
`internal_failure`.

## Repro

`repro.hlsl` is agent-constructed (the issue's own link is a third-party
shader-playground host and is not reproduced verbatim, per this skill's policy against
depending on non-public/third-party evidence). It declares:

```hlsl
struct S {
    int value;
    S getThis() { return this; }
    void copyThisInto(out S dst) { dst = this; }
};
```

and calls both from a trivial `[numthreads(1,1,1)]` compute shader (`cs_6_0`) that stores the
copied struct's field into an `RWStructuredBuffer<int>`. Both call sites fail identically:

```
$ dxc -T cs_6_0 -E main repro.hlsl
repro.hlsl:10:16: error: cannot compile this aggregate expression yet
        return this;
               ^~~~
repro.hlsl:14:15: error: cannot compile this aggregate expression yet
        dst = this;
              ^~~~
```

(`out-main-debug.txt`, `main-debug` = `dxc --version` self-reports
`1.9.0.5465 (triage, 7665270b9)`; see "Ground truth" below for why `7665270b9` rather than the
public upstream SHA is what the binary prints.)

## Where the gap lives (source reading, not just observation)

- `tools/clang/lib/Sema/SemaExprCXX.cpp`'s `genereateHLSLThis` (called from `ActOnCXXThis`)
  rewrites HLSL's `this` from `T*`/`T&` (standard C++) to a plain **lvalue of type `T`**
  (`ResultExpr->setValueKind(ExprValueKind::VK_LValue)`). So in HLSL, using `this` as a whole
  value — not just `this.member` — is an **aggregate expression** for any struct type `S`,
  not a pointer load.
- `tools/clang/lib/CodeGen/CGExprScalar.cpp:446` has `VisitCXXThisExpr` (used for scalar/handle
  `this` values), but `tools/clang/lib/CodeGen/CGExprAgg.cpp`'s `AggExprEmitter` has **no**
  `VisitCXXThisExpr` override. A `CXXThisExpr` node reached through the aggregate emitter
  therefore falls through to the generic `AggExprEmitter::VisitStmt`
  (`CGExprAgg.cpp:108-110`), which calls `CGF.ErrorUnsupported(S, "aggregate expression")` —
  the `CodeGenModule.cpp` format string is `"cannot compile this %0 yet"`, which is exactly the
  diagnostic quoted in the issue.
- The aggregate emitter is not blind to `CXXThisExpr` everywhere: its `CK_FlatConversion` /
  `CK_HLSLDerivedToBase` cast handler (`CGExprAgg.cpp:748`) special-cases
  `isa<CXXThisExpr>(Src)` and calls `CGF.EmitLValue(Src)` directly. That path is not reached by
  a plain `return this;` or `dst = this;`, which is why the failure is specific to using `this`
  as a bare aggregate value rather than universal.
- `tools/clang/test/HLSL/cpp-errors.hlsl:562-563` (an existing, currently-passing
  `-fsyntax-only -verify` test, i.e. Sema only, no CodeGen) already contains
  `CInternal getSelf() { return this; }` with **no** `expected-error` annotation on that line —
  confirming Sema raises no diagnostic for this construct at all. Consistent with the source
  reading: the gap is CodeGen-only. Verified directly: `dxc -fcgl` (front-end codegen, the
  earliest CodeGen stage) already reproduces the same error, while nothing upstream of CodeGen
  complains.

Net: this reads as a straightforward, narrow, unimplemented CodeGen path (one missing visitor
method) rather than a deep semantic or language-design gap — Sema, FXC and DXC's own SPIR-V
backend all already treat "copy the whole `this`" as ordinary, well-defined code (see below).

## Controls

- `variant-control-member-main-debug.txt` (`--expect no-match`, **passed**): the same shape
  using `this.value` (member access through `this`, the already-working path the issue itself
  calls out) compiles cleanly, exit 0. Confirms the predicate is not simply matching "any use
  of `this`", and that the specific defect is "whole aggregate", not "any use of `this`".
- `variant-spirv-main-debug.txt` (`--expect no-match`, **passed**): the *exact same*
  `repro.hlsl`, same command, with `-spirv` added, compiles cleanly to valid SPIR-V (exit 0)
  and folds both stores to constant `5`. This directly re-measures (rather than merely
  trusting) the maintainer (Keenuts, COLLABORATOR)'s 2023-01-06 comment claim that "building to
  SPIR-V ... actually works" — confirmed on the identical source, not just "some shader like
  this one".
- Compiler Explorer (`manual-case-godbolt-verify.txt`, link below): `fxc_10_0_19041` (run at
  `-T cs_5_0`, since FXC has no `cs_6_0` profile) compiles the identical struct/member-function
  shape **successfully** (real FXC banner, real DXBC disassembly with resource bindings) — the
  FXC/DXC disagreement the issue reports, reproduced directly rather than taken from the issue
  text. `dxc_1_6_2112` (CE's oldest DXC) and `dxc_trunk` both fail with the identical
  diagnostic at the identical source line. `hlsl_clang_trunk` (the new Clang-based HLSL front
  end/backend) **also fails with the byte-identical diagnostic text and line numbers** —
  the gap is not DXC-legacy-specific; it is present, unchanged, in the successor toolchain too.
  This directly informs the `check-in-clang` label question (see Labels below): the comparison
  has now been made, and the answer is "still broken there too", not "already fixed upstream".

## History

```
python scripts/triage.py bisect --issue 4914 --linear
```

`always-repro'd across v1.4.1907..v1.9.2607` — full linear scan, all 20 probeable stable
releases (v1.2.0-alpha has no usable asset; 5 prereleases excluded from the search by policy
per `release-policy.json` non-adoption — none is named by the issue text). **Every single
release reproduces**, with **zero `invalid-probe` results anywhere in the range** — this
construct (a struct with a member function, `numthreads`, `RWStructuredBuffer`) uses nothing
that postdates v1.4.1907 (2019-07), so there is no feature-absence trap to account for, and no
hidden clean window is plausible for a linear-scanned, always-failing, source-explained gap.
v1.4.1907 predates the 2023-01-05 report by three and a half years, so the full checkable
history — and, per the `git log -S` search below, the entire history of the relevant source —
shows this as a permanent gap rather than a regression.

`git log --all -S VisitCXXThisExpr -- tools/clang/lib/CodeGen/CGExprAgg.cpp` and
`git log --all --oneline --grep="copying this" -i` both return **no commits** — the visitor
was never added to the aggregate emitter at any point in this repository's history, and no
commit or PR message anywhere in the tree's history mentions "copying this". No fix was ever
attempted and reverted; this is consistent with "always-repro'd", not a fix/revert cycle, so
`--linear` was run for the population-claim reason (rule out a hidden clean window) rather than
because a fix/revert was suspected.

## Not-compiler-verifiable aspects

None. The whole reported symptom is a compile-time diagnostic difference between FXC and DXC,
fully answerable by running `dxc`/`fxc` alone; no GPU, driver or runtime evidence is needed.

## Ground truth

`main-debug` is registered at the public upstream commit
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`. The local binary's `dxc --version` self-reports a
different, fork-local commit (`7665270b9`, from a `Merge remote-tracking branch 'origin/main'
into triage` commit) because DXC bakes the building commit's SHA into the version string, and
the working tree used for triage carries this skill's own data as an extra commit. Verified
directly rather than assumed:

```
git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df
  -> 0 files outside .github/skills/dxc-issue-triage/
git diff --name-only 7665270b9 "89e2f98e29c289ae8ad9e00dd310104fea9fd7df~50"   # CONTROL
  -> 115 files outside .github/skills/dxc-issue-triage/
```

The control confirms the diff detection is meaningful (it does find differences against an
older commit) rather than a null check, so the zero-diff result against the registered
upstream commit is real equivalence, not an inability to detect a difference.

## Labels

Current: `enhancement, question, dxil, fxc-disagrees`.

- `dxil` and `fxc-disagrees` are well-supported: the defect is DXIL-CodeGen-specific (SPIR-V
  compiles the identical repro cleanly) and is a genuine FXC/DXC disagreement (FXC compiles the
  identical shape cleanly).
- `question`/`enhancement` reflect the maintainer's 2023-01-06 comment that this "would be a
  pointer [in C++], which in the shader-world is kinda problematic" and their uncertainty
  whether it should be supported at all — a legitimate concern at the time. This triage's
  direct measurements (FXC already compiles it; DXC's own SPIR-V backend already compiles it;
  Sema raises no objection; the gap is one missing CodeGen visitor, not a Sema/ABI/pointer
  question) narrow that uncertainty considerably: two independent compilers/backends already
  treat "copy the whole `this`" as ordinary, well-defined code. That does not retroactively
  make the maintainer's caution wrong at the time, so no label removal is proposed here — but
  it is worth a maintainer re-read given the new cross-compiler evidence, and `bug` alongside
  `enhancement` seems supportable given a working reference implementation exists in both FXC
  and DXC's SPIR-V path. Proposed: **add `bug`**; leave everything else as-is.
- `check-in-clang` is **not** proposed, per the skill's rule against proposing a label whose
  description is a to-do once that work is already done: the Clang-vs-DXC comparison has now
  been run (see Controls) and is reported above, rather than left outstanding.

## Suggested action

`still-valid-keep-open`. This is a real, always-reproducing, source-explained gap with
supporting cross-compiler evidence on both sides (a working FXC reference and a working DXC
SPIR-V reference) — not a stale report and not something this triage can close as fixed.
Whether to implement it remains a maintainer decision (effort/priority, given the `Dormant`
milestone already assigned on 2024-08-22), which this triage does not pre-empt.
