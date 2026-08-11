# Issue 4701 — expected symptom

**Written before any compiler was run.** Everything below is derived from the issue text only.

Issue: <https://github.com/microsoft/DirectXShaderCompiler/issues/4701>
"DXC not optimizing out code related to groupshared", filed 2022-10-03 by python3kgae (Xiang Li).
Labels at fetch time: `performance`. No comments.

## What the reporter claims

Source (verbatim from the body, modulo the markdown mangling of the leading spaces):

```hlsl
groupshared float a[10];
[numthreads(8,8,1)]
void main() {
  a[0] = 1;
}
```

Reported output:

```llvm
@"\01?a@@3PAMA" = external addrspace(3) global [10 x float], align 4

define void @main() {
  store float 1.000000e+00, float addrspace(3)* getelementptr inbounds ([10 x float], [10 x float] addrspace(3)* @"\01?a@@3PAMA", i32 0, i32 0), align 4, !tbaa !7
  ret void
}
```

> "Expect the store and the global variable to be removed because there's only store on the
> global variabl[e]."

So the claim is **not** that the compiler is wrong. It is that a groupshared array which is
**only ever stored to, and never loaded anywhere in the module**, is dead — nothing inside or
outside the thread group can observe it — and DXC keeps both the allocation and the store.
This is a **code-quality / missed-optimisation** report.

## No command line was given

The body quotes IR but no `dxc` invocation. Two things follow, and both must be settled by
measurement rather than assumption:

1. **Optimisation level.** DXC's default is not `-Od`. The probe must use the default
   (whatever it is) and must additionally record `-Od` and an explicit `-O3` so the reader can
   see the level the measurement was taken at. A missed optimisation observed at `-Od` would
   be meaningless.
2. **Pipeline stage.** The quoted IR carries `!tbaa` and a Microsoft-mangled global name
   (`\01?a@@3PAMA`) with `external` linkage. That is the shape of DXC's *high-level* IR
   (what `-fcgl` prints), not necessarily of final DXIL. If final DXIL differs from the quote,
   that is a finding about the issue text, not a reason to declare the report wrong — the
   substantive claim (allocation + store survive) has to be checked against final DXIL, and
   the quote checked separately.

## Definition of "not optimised" (the thing being counted)

An eyeball comparison of two IR dumps is not a verdict, so the symptom is defined as two
countable structural facts in the **final DXIL disassembly** that `dxc` prints to stdout:

| symbol | counted thing | matched by |
| --- | --- | --- |
| **G** | module-level globals of type `[10 x float]` in **address space 3** (TGSM / groupshared) | a line matching `addrspace\(3\) global \[10 x float\]` |
| **S** | `store` instructions whose pointer operand is in address space 3 | `store float <val>, float addrspace(3)*` |

**The symptom is present (repro) iff G >= 1 and S >= 1**, in a capture that also proves a real
DXIL module was emitted (anti-vacuity anchor: `!dx.entryPoints`). The anchor is required
because both clauses are presence clauses; without it a compile that emitted nothing could
not be told from a compile that emitted an optimised module, and a *failed* compile must not
be scoreable either way.

**The symptom is absent (does-not-repro) iff G == 0 and S == 0** — i.e. exactly what the
reporter asked for: "the store and the global variable ... removed".

`match.json` encodes exactly that. A second, address-space-agnostic predicate
`match-deadarray.json` ("a `[10 x float]` module global survives **and** some `store`
survives") exists so that the reported case and the reference case below can be measured with
the *same* instrument.

## The reference case (this is a two-sided measurement)

A one-sided history probe on a code-quality issue cannot tell "this case got worse" from "the
comparison case got better". So a second shader is measured on **every** release alongside the
repro:

* `control-static.hlsl` — byte-identical to `repro.hlsl` except `groupshared` is replaced by
  `static`. A file-scope `static float a[10]` that is only stored to is dead for the same
  reason, and LLVM's ordinary global optimisation handles it. **Expectation: fully removed —
  G/array-global == 0 and no `store` in `main`.**

If both arms survive on old releases and only the `static` arm improves later, the correct
reading is "the comparison case got better", not "groupshared regressed". If the `static` arm
is clean on every release and the groupshared arm is dirty on every release, the correct
reading is a persistent, groupshared-specific gap. Either way the pair, not the repro alone,
is the evidence.

## Controls (each must behave as declared, or the instrument is not trusted)

| shader | role | declared expectation |
| --- | --- | --- |
| `control-static.hlsl` | reference case; known-good input the optimiser should clean up | `no-match` |
| `control-local.hlsl` | function-local `float a[10]` — dead local, must be SROA'd/DSE'd away | `no-match` |
| `control-gs-live.hlsl` | groupshared array genuinely read back and written to a UAV | **`match`** — instrument self-test: proves the two regexes *can* see a groupshared global and an addrspace(3) store when one legitimately exists. If this stops matching on some release, that release is unmeasurable, not clean. |
| `control-hello.hlsl` | trivial `cs_6_0` shader with a UAV store, no arrays | `no-match`; also the feature-presence probe that tells "this release predates something" from "this release rejected my repro" |

## Predicted outcome, recorded now so it can be wrong

I expect the symptom to still be present on `main` and on every probeable release
(`always-repro'd`), because the reported IR shows the groupshared global with **`external`**
linkage, and LLVM's `GlobalOpt` "global is never loaded" transform only fires on globals with
local linkage. I expect `control-static.hlsl` to be clean everywhere. **If either prediction
fails, the measurement wins.**

## Legitimate reasons a groupshared allocation could survive

To be checked before calling this a compiler defect rather than a design choice:

* TGSM is shared across the thread group; a store is only dead if **no** load exists anywhere
  in the final module. That holds here (there are no loads at all), but it does not hold in
  general, so a fix has to be a real reachability/liveness analysis.
* Removing the allocation changes the shader's reported TGSM usage, which is part of the
  compiled artifact's metadata and is validated against a 32 KB budget.
* An `external` groupshared global is, at the IR level, potentially referenced by another
  module (library / `-T lib_6_x` linking). For a compute entry point that cannot happen, but
  the front end may be assigning linkage without knowing that.

None of these makes the *reported* case non-dead; they only bound how a fix would be written.
They belong in the write-up, not in the verdict.

## Repro quality

`complete` — the body gives compilable HLSL and the expected transformation, with no ambiguity
about what should have happened. The only missing piece is the command line, which is
recovered by measuring at default / `-O3` / `-Od` and saying which was used.

## What each status would mean here

| status | when |
| --- | --- |
| `repros` | G >= 1 and S >= 1 on `main` at the default optimisation level |
| `does-not-repro` | G == 0 and S == 0 on `main` at the default optimisation level, **and** the same at `-O3` |
| `changed-behavior` | the array or the store survives but in a different form than reported (e.g. store remains but allocation is gone, or the mangled `external` global is now internal) |
| `inconclusive` | the answer depends on an optimisation level that cannot be attributed to the reporter |
