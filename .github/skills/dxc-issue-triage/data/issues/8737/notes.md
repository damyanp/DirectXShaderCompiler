# #8737 — Atomics on RWTexture2DMS result in silent UB or ICE

**Verdict: `repros`** — both claimed symptoms, on every release that can compile the repro.

Ground truth: `build/Debug/bin/dxc.exe`, `1.9.0.15422 (main, eff900d54)`, commit `eff900d5`
(captured in `manual-ground-truth-version.txt`, which also shows that the working tree has moved
on to `f8220ace` — but only by triage-workspace commits, with **no compiler source changed**
between the two, so the source line numbers cited below are valid at `eff900d5`).
Reporter used 1.10.2605.24. Issue filed 2026-08-04 by @Maraneshi, **no comments** — nothing in
the thread contradicts or extends the body. `expected.md` was written before anything ran.

## Where each claim's evidence lives

Every measurement quoted below resolves to a file in this directory. Probes run through
`triage.py` are `out-*.txt` (the `cmd.txt` repro, one per compiler) and `variant-*.txt` (a named
variant or control). Measurements taken by hand are `manual-*.txt`, and the two scripts that
produced the Compiler Explorer ones are checked in beside them so they can be re-run:

| claim in this file | backing file |
| --- | --- |
| ground-truth compiler identity; citation provenance | `manual-ground-truth-version.txt` |
| the five DXC source citations, quoted verbatim | `manual-source-citations.txt` |
| "no test combines `RWTexture2DMS` with `Interlocked`" | `manual-testsuite-search.txt` |
| all three CE panes compile clean and show the defect | `manual-godbolt-verification.txt` (`verify-godbolt.py`) |
| why there is no Clang pane and no RGA pane | `manual-godbolt-rejected-panes.txt` (`verify-godbolt-rejected.py`) |
| release publication dates | the workspace release catalogue (`triage.py sql`) |
| the completeness audit of this directory | `manual-completeness-audit.txt` (`selfcheck.py`, `rescore.py`) |

`triage.py reindex` was **not** used as the final check. It defaults to `--reset`, which deletes
and rebuilds the shared `issues`/`runs` tables, so in a parallel batch it destroys other workers'
in-flight rows; the orchestrator withdrew it mid-batch (see `method-notes.md` §6/§6a). The two
scripts above replace it: `selfcheck.py` verifies the deliverables and that every file cited in
this write-up exists (43/43 pass), and `rescore.py` re-scores all 46 captures with `triage.py`'s
own `classify()` — no drift from what was recorded, no violated control expectation — while
asserting the database is byte-identical before and after.

## What was tested

`cmd.txt` is one line, the reporter's own command: `-T ps_6_7 -E PSMain repro.hlsl`.

The report describes **two symptoms from two different source lines**, so they are two
translation units. They cannot share one: an internal failure aborts the compile, so with both
lines live the ICE would destroy the DXIL that the silent case is about.

| file | what it is | predicate | result on `main-debug` |
| --- | --- | --- | --- |
| `repro.hlsl` | case B, `InterlockedMax(tex.sample[s][uv], …)` | `match.json` (`internal_failure`) | **repro**, exit `0x80004005` |
| `repro-implicit-sample.hlsl` | case A, the reporter's file **verbatim** | `match-silent-ub.json` | **repro**, exit 0 |
| `const-sample-atomic.hlsl` | `InterlockedAdd(tex.sample[0][uv], …)` | `match.json` | **repro** — constant sample index, different atomic, same failure |
| `msarray-explicit-sample.hlsl` | case B on `RWTexture2DMSArray` | `match.json` | **repro** |
| `msarray-implicit-sample.hlsl` | case A on `RWTexture2DMSArray` | `match.json` / `match-silent-ub.json` | no-match / no-match — compiles silently, but differently (below) |
| `control-sample-store.hlsl` | `tex.sample[s][uv] = v` only, no atomic | `match.json`, `--expect no-match` | ✅ clean |
| `control-rwtexture2d-atomic.hlsl` | same atomic on a plain `RWTexture2D` | `match-silent-ub.json`, `--expect no-match` | ✅ clean |
| `variant-diagnosed-error-not-ice` | `-validator-version 1.0`, an ordinary error | `match.json`, `--expect no-match` | ✅ clean |
| `variant-full-container-validated` | `-Fo NUL` on case A | `match.json`, `--expect no-match` | ✅ clean, exit 0 |

## Symptom B — the ICE. Confirmed.

```
$ dxc -T ps_6_7 -E PSMain repro.hlsl
[exit] 2147500037            (0x80004005, E_FAIL)
error: llvm::cast<X>() argument of incompatible type!
```

Byte-identical on `RWTexture2DMSArray`, with a constant sample index, and with a different
atomic — so this is *any* atomic reached through the `.sample[][]` subscript, not one spelling.

**This is an internal failure even though the exit code is E_FAIL.** `llvm::cast<>` failure in
DXC is not an `assert`: `llvm::llvm_cast_assert_internal` throws
`hlsl::Exception(DXC_E_LLVM_CAST_ERROR, …)` (`lib/Support/ErrorHandling.cpp:143`), which dxc
reports as a diagnostic and exits E_FAIL. Consequently the failure is *identical* in Debug and
in shipped Release binaries — verified: v1.7.2207's release build prints the same line
(`out-v1.7.2207.txt`). See `method-notes.md`; this class is invisible to an exit-code-only
`internal_failure` test and is caught only by the build-agnostic `cast<…>() argument` marker in
`INTERNAL_MARKERS`.

`control-sample-store.hlsl` — same resource, same `.sample[s][uv]` double subscript, a **store**
instead of an atomic — compiles clean. So the double subscript itself is fine; only the atomic
on it fails. `variant-diagnosed-error-not-ice` shows the converse: an ordinary diagnosed error
(`error: validator version 1,0 does not support target profile.`) also exits E_FAIL and scores
`no-repro`, so the predicate is not simply reading the exit code.

## Symptom A — "silent UB". Confirmed, and the DXIL settles it.

The reporter's file compiles with **exit 0 and no diagnostic at all** — not even a warning
(`variant-silent-ub-main-debug.txt`). What it emits:

```llvm
; tex                                   UAV     u32        2dMS      U0             u0     1
...
%6 = call i32 @dx.op.atomicBinOp.i32(i32 78, %dx.types.Handle %5, i32 7,
                                     i32 %3, i32 %4, i32 undef, i32 -559038737)
                                                     ^^^^^^^^^ c2
call void @dx.op.textureStoreSample.i32(i32 225, …, i32 %3, i32 %4, i32 undef,
                                        …, i8 15, i32 0)      ; sampleIdx = 0
call void @dx.op.textureStoreSample.i32(i32 225, …, i32 %3, i32 %4, i32 undef,
                                        …, i8 15, i32 %2)     ; sampleIdx = s
```

The two stores carry an explicit trailing `sampleIdx`. The atomic has no such operand and its
last coordinate is literally `undef`. The sample index is not defaulted to 0 — it is absent.

This is **not** merely an output observation; it is corroborated three ways from the tree:

1. **`docs/DXIL.rst:1876-1887`** — `AtomicBinOp`'s "Valid resource type" table lists
   RWTexture1D, RWTexture1DArray, RWTexture2D, RWTexture2DArray, RWTexture3D, RWTypedBuffer,
   RWRawBuffer, RWStructuredBuffer. **Texture2DMS and Texture2DMSArray are not in it.** DXC's
   own spec document says this operation is not defined for this resource kind.
2. **`lib/HLSL/HLOperationLower.cpp:4906-4949`** — `TranslateAtomicBinaryOperation` initialises
   all three coordinate operands to `undefI` and then overwrites only as many as the address
   vector has elements. There is no multisample branch anywhere in it, so no code path could
   supply a sample index.
3. **`lib/DxilValidation/DxilValidation.cpp:2412-2424`** — the validator's `AtomicBinOp` case
   checks the overload type and that the handle is a **UAV**. It does not check resource *kind*,
   so nothing rejects the module. `-Fo NUL` (full container, validation enabled — `NeedsValidation()`
   = `ProduceFullContainer() && !DisableValidation`) exits 0 and prints nothing;
   `-Fo` was demonstrably honoured, because the same command without it prints the whole
   disassembly.

So the compiler emits, and accepts, an operation whose sample index is undefined. The
reporter's *runtime* claim — that RGA lowers this using an uninitialised register — needs a
GPU toolchain and is not settled here; it does not need to be. The under-specification is
visible in the IR.

`control-rwtexture2d-atomic.hlsl` is what makes that argument non-vacuous. The identical
`InterlockedMax` on a **non**-multisampled `RWTexture2D` emits:

```llvm
; tex                                   UAV     u32          2d      U0             u0     1
%5 = call i32 @dx.op.atomicBinOp.i32(i32 78, %dx.types.Handle %4, i32 7,
                                     i32 %2, i32 %3, i32 undef, i32 -559038737)
```

— the same instruction, and correctly so, because DXIL.rst gives RWTexture2D two active
coordinates. **DXC lowers the multisampled and non-multisampled cases identically; the sample
index simply has nowhere to go.** This is also why `match-silent-ub.json` must require `2dMS`
in the resource table as well as the `undef` c2: the `undef` alone matches a perfectly good
shader.

## `RWTexture2DMSArray` is worse, not merely also-broken

The reporter's "Do not forget about RWTexture2DMSArray" is right, and the array case is not
the same defect wearing a hat. `RWTexture2DMSArray` subscripts with a `uint3`, so:

```llvm
; tex                                   UAV     u32   2darrayMS      U0             u0     1
%7 = call i32 @dx.op.atomicBinOp.i32(i32 78, …, i32 %3, i32 %4, i32 %5, i32 -559038737)
call void @dx.op.textureStoreSample.i32(i32 225, …, i32 %3, i32 %4, i32 %5, …, i8 15, i32 %2)
```

All three coordinate slots are consumed by x/y/slice. There is no `undef` slot left — the sample
index cannot be encoded even in principle, which is exactly why `textureStoreSample` needed a
*separate* trailing operand. `match-silent-ub.json` deliberately scores this `no-match`
(`variant-msarray-implicit-ub-main-debug.txt`, `--expect no-match`), because calling it the same
signature would be wrong.

## Is this valid input in the first place?

No, and that reframes the fix. `RWTexture2DMSMethods` in `utils/hct/gen_intrin_main.txt:927-934`
declares only `GetDimensions`, `GetSamplePosition` and `Load` — there is no interlocked method on
the type. Both forms in the issue reach the *free function* `InterlockedMax(ref int32_only, …)`
applied to whatever lvalue the subscript produced, so Sema never inspects the resource kind.
Combined with DXIL.rst's resource-type table, the position is:

> This is invalid input that DXC does not diagnose — not valid input that DXC miscompiles.

The reporter's "Desired Outcome" (reject with a clear error) is therefore the right ask, and no
codegen change can substitute for it while `atomicBinOp` has no sample-index variant. Nothing in
the repo documents atomics on writable MSAA textures as supported; of the 8 files under
`tools/clang/test` that mention `RWTexture2DMS`, **none** also mentions `Interlocked`
(`manual-testsuite-search.txt`).

## History

`bisect --linear` on the ICE (`match.json`, `cmd.txt`):

```
v1.4.1907 … v1.6.2112   n/a  (error: invalid profile ps_6_7 — 5 releases skipped as unprobeable)
v1.7.2207 … v1.9.2607   repro  (15/15)
result: always-repro'd across v1.7.2207..v1.9.2607 (5 release(s) skipped as unprobeable)
```

Symptom A was probed separately, because `bisect` drives `cmd.txt` and `cmd.txt` is the ICE
case. `repro-implicit-sample.hlsl` was run against **all 15** SM 6.7-capable releases with
`match-silent-ub.json` and `--expect match` (`variant-silent-ub-<tag>.txt`): repro on every one.

v1.7.2207 (published 2022-07-14, per the release catalogue) is the first release with SM 6.7 —
v1.6.2112 rejects the profile outright (`out-v1.6.2112.txt`) and v1.7.2207 compiles it
(`out-v1.7.2207.txt`) — so **both symptoms have existed for as long as `RWTexture2DMS` has**.
This is not a regression; it is an unimplemented case that was never diagnosed. The five skipped
releases are genuine `invalid-probe`s — `error: invalid profile ps_6_7`, verified in
`out-v1.6.2112.txt` — not clean runs.

## Compiler Explorer

<https://godbolt.org/z/ea91a6vnj> — publishes `repro-implicit-sample.hlsl` (recorded in
`godbolt-source.txt`), i.e. the silent case, because that is the half a link can *show*: the ICE
is a single line already quoted in the issue, whereas the wrong-code evidence is in the DXIL.
Panes: `dxc_1_7_2207` (oldest CE build with SM 6.7), `dxc_1_10_2605_24` (**the reporter's exact
version**), `dxc_trunk`. All three re-verified after publishing, and captured to
`manual-godbolt-verification.txt`: shortlink `GET` returns HTTP 200, and every pane gives exit 0,
`2dMS` in the resource table, `atomicBinOp(… i32 undef, i32 -559038737)`, and exactly two
`textureStoreSample` **call sites** each carrying its `sampleIdx`. Comment-only filtering is off,
so the resource table is visible.

Worth noting from that capture: `dxc_1_7_2207` emits
`warning: DXIL.dll not found.  Resulting DXIL will not be signed for use in release environments.`
on stderr while the other two panes are silent. That is the exact warning `match-silent-ub.json`'s
fourth conjunct is deliberately narrowed to tolerate — a blanket "no warnings at all" predicate
would have scored every release binary as fixed.

**No Clang pane.** `hlsl_clang_trunk` answers
`error: no template named 'RWTexture2DMS'; did you mean 'RWTexture2D'?` (full output in
`manual-godbolt-rejected-panes.txt`) — the type is not implemented in the new front end, so the
pane would say nothing about this issue. Per SKILL.md, a translated variant is not available
either: the construct is inherently about a resource type Clang does not have.

**No RGA pane**, although CE carries `rga290_dxctrunk` and the reporter's headline claim is
about RGA's output. CE's RGA integration compiles for Vulkan — the shader fails there with
`fatal error: generated SPIR-V is invalid: [VUID-StandaloneSpirv-UniformConstant-04655] …
'7[%tex]' has illegal type` — and it forwards user arguments straight to dxc, so both `-s dx12`
and `--dx12` come back as `dxc failed : Unknown argument`. All three probes are captured in
`manual-godbolt-rejected-panes.txt`. The DX12 ISA view the reporter used is not reachable from
Compiler Explorer.

## Labels

Now `bug`, `needs-triage`. Proposed: **add** `crash`, `incorrect-code`, `diagnostic`, `sm6.7`;
**remove** `needs-triage`.

- `crash` — "DXC crashing or hitting an assert". `llvm::cast<X>() argument of incompatible type!`
  is an internal failure, not a diagnosed error; `bug` alone understates it.
- `incorrect-code` — "Issues relating to handling of incorrect code". The input is invalid and
  DXC's handling of it is the defect. This is the label that states the finding.
- `diagnostic` — the requested outcome is a clear error message; there is currently none.
- `sm6.7` — the feature is SM 6.7 writable MSAA textures, and both symptoms date to the first
  SM 6.7 release.
- `needs-triage` removed: repro confirmed on current `main`, both symptoms characterised,
  history established back to the feature's introduction.

Deliberately **not** proposed, with reasons:

- `correctness` ("bugs that impact shader correctness") — tempting, but it implies DXC should
  generate *correct* atomics here, which is impossible while `atomicBinOp` has no sample-index
  operand. The fix is rejection, and `incorrect-code` says that.
- `validation` — this label means DXIL validation specifically, and there *is* a real gap
  (`DxilValidation.cpp:2412`, resource kind unchecked). But the reporter asks for a front-end
  diagnostic, and adding the label would mis-route the issue. Raised in the comment as an
  observation instead.
- `check-in-clang` — checked and answered already: Clang has no `RWTexture2DMS`.

I may be missing history that motivated the current labels; the draft says so.

## Limits of this triage

- The runtime consequence (RGA emitting an uninitialised register, actual GPU behaviour) was not
  reproduced; only the compiler-visible under-specification was. The verdict does not depend on it.
- The `main` build measured is Debug. It makes no difference for either symptom here, because the
  failure path is a thrown `hlsl::Exception` rather than an `assert`, and the release binaries
  produce identical output.
- History is release-granular. No attempt was made to attribute either symptom to a commit; both
  are present in the first release that has the feature, so there is no window to search.
