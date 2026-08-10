# #4350 — Internal Compiler error: calling method that modifies const object

**Verdict: still reproduces, on every stable release that can be probed and on `main`.**

- Filed 2022-03-25 by tex3d. Labels `bug`, `hlsl-next`. Open.
- Ground truth: `main-debug`, Debug build, `dxc --version` reports
  `dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)`.
  The version string embeds a fork-local merge SHA that resolves nowhere public; the
  corresponding upstream commit is **13730886e**. Verified:
  `git diff --name-only 13730886e HEAD` reports nothing outside `.github/skills/`, and the
  control `git diff --name-only 3bbe1e9f8~50 13730886e` does list compiler source
  (`docs/DXIL.rst`, `external/SPIRV-Tools`, …), so the query can detect differences.

## Repro

`repro.hlsl` is the issue body verbatim, including its `-T vs_6_0` RUN line. Repro quality
**complete**: the body carries a self-contained shader and the exact command.

```
dxc -T vs_6_0 repro.hlsl
exit 0x80004005
error: llvm::cast<X>() argument of incompatible type!
```

`Obj` is declared at file scope, so it is implicitly const and lives in `$Globals`. `Set()`
is not marked `const` and writes a member.

## What actually fails, and where

`manual-case-cast-stack.txt` (regenerate with `capture-stack.py`) puts the failure in DXIL
lowering, not in the front end:

```
dxcompiler!llvm::llvm_cast_assert_internal
dxcompiler!llvm::cast<llvm::GetElementPtrInst,llvm::Instruction>
dxcompiler!`anonymous namespace'::TranslateCBAddressUserLegacy
dxcompiler!`anonymous namespace'::TranslateCBGepLegacy
dxcompiler!`anonymous namespace'::TranslateCBAddressUserLegacy
dxcompiler!`anonymous namespace'::TranslateCBOperationsLegacy
dxcompiler!TranslateHLSubscript
```

That cast is `lib/HLSL/HLOperationLower.cpp:8847`, directly under the comment
`// Must be GEP here`. The throw is `hlsl::Exception(DXC_E_LLVM_CAST_ERROR, …)` from
`lib/Support/ErrorHandling.cpp:144`, which the driver surfaces as E_FAIL.

`variant-fcgl-main-debug.txt` shows the front end is what lets it through. Under `-fcgl`,
which stops before DXIL lowering, the compile **succeeds** (exit 0) and the IR contains:

```
@"$Globals" = external constant %"$Globals"
%2 = call %"$Globals"* @"dx.hl.subscript.cb.rn…"(i32 6, %dx.types.Handle %1, i32 0)
%3 = getelementptr inbounds %"$Globals", %"$Globals"* %2, i32 0, i32 0
call void @"\01?Set@MyStruct@@QAAXXZ"(%struct.MyStruct* dereferenceable(4) %3)
…
store i32 1, i32* %Idx, align 4
```

So Sema accepts a call that stores into a constant buffer, and the lowering that walks the
users of a cbuffer address — which assumes they are GEPs and loads — meets something that is
not a GEP and throws. No diagnostic is emitted at any point.

**DXC never diagnoses the const violation at all**, and that is separable from the crash.
`control-const-local.hlsl` performs the same violation on a `const` **local** object and
compiles to exit 0 with no diagnostic and no warning. A local is an alloca, so the
undiagnosed store is representable and lowering has nothing to choke on. The internal error
is therefore specific to the object being cbuffer-backed; the missing const checking is not.

## Predicate

`match.json` is `internal_failure`. This issue is the reason that rule exists: **the same
defect wears four faces across the release history and is silent on two of them.**

| releases | exit | stderr |
| --- | --- | --- |
| v1.4.1907, v1.5.2010 | 0xC0000005 | **completely empty** |
| v1.6.2104 | 0xC0000005 | `Internal compiler error: access violation. Attempted to read from address …` |
| v1.6.2106, v1.6.2112 | 0x80AA001D | `Internal Compiler error: llvm::cast<X>() argument of incompatible type!` |
| v1.7.2207 … v1.9.2607, `main` | 0x80004005 | `error: llvm::cast<X>() argument of incompatible type!` |

`check-predicate-counterfactual.py` re-scores every committed capture under five predicates
and writes `manual-case-predicate-counterfactual.txt`. Measured:

| predicate | history it would report | releases scored repro |
| --- | --- | --- |
| P1 `internal_failure` (used) | always repro'd | 20 of 20 |
| P2 exit status only, no text markers | repro → clean at **v1.7.2207** | 5 of 20 |
| P3 contains the reporter's quoted message | clean → repro at **v1.6.2106** | 17 of 20 |
| P4 contains `internal compiler error` (the title's phrase) | clean → repro at v1.6.2104; repro → clean at v1.7.2207 | 3 of 20 |
| P5 nonzero exit | always repro'd | 20 of 20 |

P2 is the failure the brief warned about, measured: an exit-status-only predicate reports this
still-open issue as **fixed at v1.7.2207 (2022-07)** — four months after it was filed and four
years before this triage. P3 and P4 invent regressions at releases where only the wording
changed.

P5 gets this issue's history right and is still wrong, which is why the counterfactual also
scores the controls: `control-syntax-error.hlsl` exits **0x80004005, the same status as the
repro**, and P5 fires on it. Both halves of `is_internal_failure()` are load-bearing here —
the status codes carry v1.4.1907..v1.6.2112, the build-agnostic `cast<…>() argument` marker
carries v1.7.2207..`main`.

## Controls

All against `main-debug`, all captured:

| control | expect | result |
| --- | --- | --- |
| `control-static-obj.hlsl` — repro with `static`, so mutable | no-match | exit 0 |
| `control-member-fn.hlsl` — member function on a mutable local (feature presence) | no-match | exit 0 |
| `control-const-local.hlsl` — same violation on a `const` local | no-match | exit 0, **no diagnostic** |
| `control-syntax-error.hlsl` — ordinary diagnosed error | no-match | 0x80004005, `error: expected ';'` |
| `variant-cs66.hlsl` `-DCONTROL_MUTABLE` | no-match | exit 0 |

Language version is not a factor: `-HV 2018` and `-HV 2021` both reproduce
(`variant-hv2018-*`, `variant-hv2021-*`), so the move of the default language version does not
confound the history. Nor is the shader stage: the compute restating reproduces
(`variant-cs66-*`).

## History

`bisect --linear` over all 20 stable releases: **always-repro'd across v1.4.1907..v1.9.2607.**
Linear rather than binary because a population claim ("no shipped release has ever compiled
this") needs every release visited, not endpoint agreement. Skipped: 5 prereleases by policy
(v1.5.2003, v1.8.2306-preview, v1.8.2405-mesh-nodes-preview, v1.10.2605.2, v1.10.2605.24) and
v1.2.0-alpha, which ships no usable `dxc`.

v1.4.1907 (2019-07) is the bisection floor, so "always" means "for as long as it is possible
to check", not "since HLSL gained member functions".

`release-matrix.py` runs the repro and three controls on every one of those 20 releases with
the repro's exact arguments — **80 runs, SELFTEST=pass, every one as expected**
(`manual-case-release-matrix.txt`). This is what rules out the quiet `invalid-probe`: on every
release the feature the repro needs was present (`memberfn` clean), the predicate declined to
fire on the near-identical mutable shader (`static` clean), and an ordinary diagnosed error was
not counted as a crash (`syntaxerr` nonzero but not internal). No release could have been
answering a different question.

## Compiler Explorer

https://godbolt.org/z/TEcGjnve7 — four panes, read back through
`GET /api/shortlinkinfo/TEcGjnve7` and confirmed to hold all four. Full text in
`manual-case-godbolt-verify.txt`.

- `dxc_1_6_2112` `-T cs_6_6` → exit 29, `Internal Compiler error: cast<X>() argument of incompatible type!`
- `dxc_trunk` `-T cs_6_6` → exit 5, `error: cast<X>() argument of incompatible type!`
- `hlsl_clang_trunk` `-T cs_6_6 -fsyntax-only` → exit 1,
  `error: 'this' argument to member function 'Set' has type 'const MyStruct', but function is not marked const`, plus a note pointing at the declaration
- `hlsl_clang_trunk` `-T cs_6_6 -fsyntax-only -DCONTROL_MUTABLE` → **exit 0**

CE's Linux exits are the low byte of the Windows HRESULT: 29 = 0x1D of 0x80AA001D and
5 = 0x05 of 0x80004005, matching the local v1.6.2112 and `main` captures respectively.

The fourth pane is the control the Clang finding needs. Same compiler, same source, one define
different: with the object mutable Clang compiles it. So Clang's error is a real diagnosis of
this construct and not Clang failing on the shader for its own reasons. `-fsyntax-only` is used
because the symptom is a front-end question and Clang's DXIL backend is incomplete.

That result bears directly on llvm-beanz's 2024-07-24 comment that "HLSL's overload resolution
doesn't handle const-ness of the implicit object": in the Clang-based HLSL front end it does,
today, and produces the diagnostic. Whether that settles the design question tracked by
`hlsl-specs` proposal 0007 is a maintainer call, not a triage finding.

## Assessment

- **Status**: `repros`.
- **Repro quality**: `complete`.
- **History**: `always-repro'd` (v1.4.1907 onward, the checkable range).
- **Confidence**: high. 20/20 releases, 80/80 matrix runs, a stack that names the failing
  cast, and the source line it corresponds to.
- **Text stale**: no. The title and body describe exactly what the compiler does, including
  the message on current builds. Filed by a maintainer who wrote it precisely.
- **Suggested action**: `still-valid-keep-open`. The issue is correctly labelled and already
  milestoned; nothing about it needs re-triage. The one thing worth surfacing is that the
  crash and the language question are separable — a shader that violates const on a
  `$Globals` object is an internal compiler error today, whereas the same violation on a local
  is accepted silently, so a diagnostic could replace the ICE regardless of where proposal
  0007 lands. That is a product decision and the draft does not pre-empt it.

## Labels

Now: `bug`, `hlsl-next`. Proposed additions:

- **`crash`** ("DXC crashing or hitting an assert") — 20 of 20 releases and `main` fail
  internally; three of them with an access violation. `bug` alone understates it, and the
  backlog's crash queries do not find it.
- **`incorrect-code`** ("Issues relating to handling of incorrect code") — the input is
  invalid HLSL and the compiler's handling of it is the defect.

No removals: `hlsl-next` reflects a deliberate maintainer decision (milestoned, with the
hlsl-specs proposal linked), and `bug` is accurate.

`check-in-clang` is deliberately **not** proposed: its description is a to-do ("See if this
repros in clang as well"), and that comparison has now been run and is in the draft.
