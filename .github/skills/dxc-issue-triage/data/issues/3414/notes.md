# #3414 — DXIL Modifying recursive payload does not work

**Status: `does-not-repro` on `main`; history `fixed`. Regressed in v1.6.2104, fixed in
v1.8.2505.** The reported defect was real, was visible in the generated DXIL, and is gone.

## What was measured

Ground truth: `main-debug`, Debug build, `dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) -
1.9.0.5433 (triage, ab5400907)`. The binary self-reports a fork-local merge; its compiler
source is identical to upstream `13730886e`, which is the commit to cite.

Repro: the issue body's shader, unmodified, with `#define BUGGED 1` as filed. Target
`-T lib_6_3` — the oldest profile that can express a `closesthit` shader calling `TraceRay`,
and the same profile llvm-beanz used in his 2023 Compiler Explorer link (read back from
`https://godbolt.org/api/shortlinkinfo/WPxh67onv`).

## The defect, in one line of IR

`TraceRay(..., ray, payload)` passes the shader's `inout` payload. HLSL parameter passing is
copy-in/copy-out, so the recursive trace must be given a **copy**; DXR gives caller and callee
separate payload storage. On the affected releases DXC instead handed `dx.op.traceRay` the
caller's own payload object:

```llvm
; v1.8.2502 — the payload parameter and the traceRay operand are the SAME value
define void @"\01?main@@..."(%struct.Payload* noalias %payload, ...) {
  ...
  call void @dx.op.traceRay.struct.Payload(i32 157, ..., %struct.Payload* %payload)
```

```llvm
; v1.8.2505 and main — a distinct temporary, written before the call and read back after
  %34 = getelementptr inbounds %struct.Payload, %struct.Payload* %2, i32 0, i32 0
  store <4 x i32> %20, <4 x i32>* %34, align 8
  call void @dx.op.traceRay.struct.Payload(i32 157, ..., %struct.Payload* nonnull %2)
  %35 = load <4 x i32>, <4 x i32>* %34, align 8
  store <4 x i32> %35, <4 x i32>* %7, align 4
```

The parameter attributes move in step: `noalias` alone while the pointer is passed on,
`noalias nocapture` once it is not.

## Why this is the reported symptom and not an unrelated difference

The reporter's own two variants differ in exactly this, and nothing else. Measured on the same
release with the same flags (`manual-case-release-matrix.txt`):

| v1.6.2104 | payload param | `dx.op.traceRay` operand |
| --- | --- | --- |
| `repro.hlsl` (their `BUGGED 1`) | `%payload` | `%payload` — aliased |
| `control-workaround.hlsl` (their `BUGGED 0`) | `%payload` | `%2` — a distinct temporary |

Introducing `Payload new_payload` gives SROA an alloca to work on, which is what produced the
copy. That is the whole mechanism of their workaround, and it is why it worked.

## Corroboration from source

Pre-fix, the payload copy-in/copy-out was generated **inside SROA's per-value rewrite**
(`lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp`, `RewriteCallArg(CI,
HLOperandIndex::kTraceRayPayLoadOpIdx, /*bIn*/…, /*bOut*/…)` reached from the
`OldVal`/`NewElts`/`DeadInsts` rewrite loop). It therefore only ran when the payload argument
was a value SROA was scalar-replacing — an alloca or a global. The entry function's payload
*pointer parameter* is neither, so no copy was ever created and the intrinsic kept the
caller's object.

`053e7ac65` "Refactor udt intrinsic arg copy to before SROA, flatten RayDesc (#7440)",
Tex Riddell, 2025-05-16, replaces that with a standalone `copyIntrinsicAggArgs(HLModule&)`
run before SROA, which materialises a fresh alloca and a copy for every UDT intrinsic argument
unconditionally:

```cpp
memcpyAggCallArg(CI, HLOperandIndex::kTraceRayPayloadPreOpIdx,
                 /*CopyIn*/ true, /*CopyOut*/ true);
```

Its own commit message states the rule the old code broke: *"Intrinsics that take UDT arguments
need copy-in/copy-out… weren't copied in when necessary, leading to problems."* The test it
adds, `tools/clang/test/DXC/Passes/ScalarReplHLSL/traceray_scalarrepl.ll`, checks precisely the
case at issue — a payload passed as a **pointer parameter** (`%struct.Payload* noalias %p`) —
and requires the lowered call to receive a new local rather than `%p`.

Attribution strength: the fix window `v1.8.2502..v1.8.2505` holds **162 commits**, 6 of which
touch `ScalarReplAggregatesHLSL.cpp`. `053e7ac65` is confirmed present in `v1.8.2505` and
absent from `v1.8.2502` (`git merge-base --is-ancestor`), and is an ancestor of
`upstream/main`. This is a **strong** attribution, not a certain one — no build was made at
that commit. PR #7440 was written for #7434 ("Unflattened RayDesc breaking HL->DXIL lowering")
and never referenced #3414, which is why this issue was not closed with it.

The regression side is left as a window: `v1.5.2010..v1.6.2104` holds 268 commits, 11 of them
touching `ScalarReplAggregatesHLSL.cpp` and 8 of those landing before the 2021-02-01 filing
date. No single commit is named, because none was tested.

## Release history

`bisect --linear`, 20 stable releases, **0 invalid probes**:

```
v1.4.1907 v1.5.2010                                                   clean
v1.6.2104 v1.6.2106 v1.6.2112 v1.7.2207 v1.7.2212 v1.7.2212.1
v1.7.2308 v1.8.2403 v1.8.2403.1 v1.8.2403.2 v1.8.2405 v1.8.2407
v1.8.2502                                                             REPRO (13 releases)
v1.8.2505 v1.8.2505.1 v1.9.2602 v1.9.2602.24 v1.9.2607                clean
```

`--linear` was mandatory: both endpoints are clean, so a binary search short-circuits to
"never reproduced" and erases a four-year window (the SKILL.md #3768 trap).

Skipped: 1 release with no usable `dxc` asset (`v1.2.0-alpha`) and 5 prereleases by policy
(`v1.5.2003`, `v1.8.2306-preview`, `v1.8.2405-mesh-nodes-preview`, `v1.10.2605.2`,
`v1.10.2605.24`). No release was demoted to `invalid-probe`, and this is not an assumption:
`control-hello.hlsl` — a minimal `raygeneration` shader that calls `TraceRay` — compiled
successfully on **all 20** stable releases, so every clean probe was a real negative rather
than a release that could not express DXR.

The window explains the thread's timeline. The issue was filed 2021-02-01, before v1.6.2104
shipped (2021-04-20) and after the clean v1.5.2010 (2020-10) — consistent with a source build
from within the regression window; the reporter's organisation builds DXC from source (the
issue's only cross-reference, from 2021-02-01, is `Traverse-Research/opensource-ecosystem#2`).
The 2021-10-01 comment reporting it as a regression "after updating DXC to the latest release"
lands on v1.6.2104/v1.6.2106.

## Predicate and controls

`match.json` is a conjunction of two **positive** clauses, so there is no absence clause and
no way for a failed compile to score as a reproduction:

1. a backreference binding the payload parameter name from the `define` line to the payload
   operand of `dx.op.traceRay` — the aliasing itself;
2. `add i32 %[\w.]+, 1` — proof the source's `payload.data0 += 1` reached DXIL.

Clause 2's register class had to be widened from `%\d+`: v1.4.1907 emits named SSA values
(`%.i09 = add i32 %.i08, 1`), and the numeric-only form scored that release no-match for a
reason unrelated to the symptom. Anchors need validating across the release range, not only
against ground truth.

Controls, all captured:

| control | result | what it establishes |
| --- | --- | --- |
| `control-workaround.hlsl` (the reporter's working variant) | no-match on ground truth **and on all 20 releases** | the predicate fires on the reported distinction, not on every DXR shader |
| `control-increment-after-trace.hlsl` | no-match on ground truth; matches on the 13 affected releases | the predicate is keyed on payload *aliasing*, not on "the traced payload lacks the increment" — and that shader is subject to the same defect, correctly |
| `control-hello.hlsl` | no-match, compiles on all 20 releases | feature-presence: no clean probe is a disguised feature-absence |

## What the pre-registered rules said, and where this diverges

`expected.md` fixed three verdict rules before anything was compiled. Read literally against
ground truth alone, the second one fires: on `main` the BUGGED form *does* store into exactly
the memory `dx.op.traceRay` receives, and the workaround form's DXIL is equivalent, which that
rule maps to `not-compiler-verifiable`. That is where this triage was heading after the first
compile.

What overrode it was evidence that rule did not anticipate. Its premise is that a
correct-looking module means there was never a compiler defect to see; the release scan
falsified the premise by exhibiting the defect — on the 13 releases the report spans — and its
repair. Once the defect has been observed and localised, `not-compiler-verifiable` is the wrong
description of `main`: the issue proved compiler-verifiable, and simply no longer reproduces.
The third rule, "if the two forms differ in some other way that still looks wrong", is the one
that actually matches what was found, and it is why the predicate is keyed on aliasing rather
than on a missing store.

The order matters and is worth stating plainly: the aliasing theory was formed from the
v1.6.2104 output, i.e. *after* measuring, not before. It is not a pre-registered prediction.
What keeps it from being a post-hoc story is that it is falsifiable and was tested against
cases chosen by the reporter rather than by this triage — the workaround variant separates
from the filed variant on the same broken binary, in the direction the report describes, and
the separation disappears on both sides of the four-year window.

## What this triage did not measure

No shader was executed. The evidence is that the compiler emitted a module whose recursive
`TraceRay` aliased the caller's payload, on exactly the releases the report spans, and that the
reporter's workaround is the source-level change that removed the aliasing. That the aliasing
is what the reporter *saw on a GPU* is consistent with everything measured but was not
observed directly, and the write-up should not claim otherwise.

## Thread state

The last technical word in the thread is llvm-beanz's 2023-07-14 comment — "The DXIL generation
looks correct to me. We are generating a store to the payload" — with a `dxc_trunk` Compiler
Explorer link. Both halves of that observation are borne out by the affected releases: the
module does contain a store to the payload (`store <4 x i32> %19, <4 x i32>* %6` on v1.7.2308,
the release nearest that date, and on every other affected release), and the same module hands
`dx.op.traceRay` the payload parameter itself. The 2024-04-16 comment moving the issue to
Dormant names answering that question as the next step; the linked CE session now recompiles on
today's `dxc_trunk`, which is fixed, so opening it today shows the corrected form.

## Suggested action

`close-fixed`. Fixed in v1.8.2505 and in every stable release since.

## Files

| file | what it is |
| --- | --- |
| `expected.md` | symptom written down before any compiler was run |
| `repro.hlsl`, `cmd.txt` | the issue's shader, unmodified, `-T lib_6_3` |
| `control-workaround.hlsl` | the reporter's `BUGGED 0` variant |
| `control-increment-after-trace.hlsl` | traces with an un-incremented payload but a distinct temporary |
| `control-hello.hlsl` | minimal DXR shader; feature-presence control |
| `match.json` | the predicate, with its note and control rationale |
| `out-*.txt` | 21 probes: ground truth + 20 stable releases |
| `variant-*-main-debug.txt` | the three controls at ground truth |
| `manual-case-release-matrix.txt` | all four shaders on all 21 compilers, commands echoed |
| `measure-controls.py` | generator for the matrix |
| `manual-case-godbolt-verify.txt` | full text of the four Compiler Explorer panes |
| `godbolt-note.txt` | the CE banner |
