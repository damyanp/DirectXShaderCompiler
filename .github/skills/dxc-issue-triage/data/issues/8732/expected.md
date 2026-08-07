# #8732 — what "this reproduces" means

*Written before any compiler was run, from the issue text alone
(`issue.json`, fetched 2026-08-06; issue created 2026-08-04, zero comments).*

## What is reported

`[SPIR-V] SPV_EXT_descriptor_heap mixed bound/heap aliasing causes silent miscompilation or
ICE`, filed as "Apart of #8517" and explicitly **"Compiled with #8517 branch."**

Under `-fspv-use-descriptor-heap`, a local resource variable initialised from
`ResourceDescriptorHeap` is not lowered to a stored descriptor handle. Instead the `VarDecl`
is recorded in a compile-time alias map (`descriptorHeapImageAliasVars`,
`descriptorHeapBufferAliasVars`, `registerFnVarAlias`) and *every* later use of that variable
is re-lowered as a fresh `OpUntypedAccessChainKHR` over the recorded heap index. The map is
keyed on the declaration, has no notion of control flow, and is never cleared. So whenever the
variable does not hold a heap descriptor on every path reaching a use, the lowering is unsound.

The report enumerates four filed defects plus one explicitly-still-open case.

### Filed defects (D1–D4)

| # | Source shape | Reported expectation |
| --- | --- | --- |
| D1 | `mixed = boundTex;` then `if (tid.x==0) mixed = ResourceDescriptorHeap[1];` then `InterlockedAdd(mixed[...])` | correct code on both paths, or a diagnostic |
| D2 | `mixed = ResourceDescriptorHeap[2];` then `mixed = boundTex;` then `InterlockedAdd(mixed[...])` | atomic targets `boundTex` (straight-line code, no control flow) |
| D3 | `mixed = boundTex;` then `for(...) mixed = ResourceDescriptorHeap[i];` then `InterlockedAdd(...)` | `boundTex` when the loop body never runs |
| D4 | `mixedBuf = ResourceDescriptorHeap[2];` then `mixedBuf = boundBuf;` then `mixedBuf.Load(0)` | load targets `boundBuf`; report says D4 also produced an **ICE** |

### The report's own "Actual Behavior (current build)"

The issue body already states that on the reporter's build **all four are now diagnosed**:

```
error: mixing bound and descriptor heap resources in the same variable is not
supported with SPV_EXT_descriptor_heap
```

by `diagnoseDescriptorHeapAliasMixing` / `descriptorHeapVarState`. This is a statement about
the #8517 branch, not necessarily about `main`. **It must be checked, not assumed** — the
whole point of the ground-truth run.

### D5 — the remaining unsound case, stated by the reporter as NOT diagnosed

```hlsl
RWTexture2D<uint> mixed;          // never assigned a bound resource
if (cond)
    mixed = ResourceDescriptorHeap[1];
InterlockedAdd(mixed[uint2(0,0)], 1, original);   // undefined index on the else path
```

`wasBound` is never set, so the mixing diagnostic does not fire. The alias is registered
inside the branch and applied unconditionally to uses outside it. The reporter notes that for
image-like resources the silent window is narrow: the variable's only uses must be
`Interlocked*`, because adding an ordinary read/write keeps the image function variable live
and then hits a *separate*, pre-existing `OpPhi` of image type failure. For buffer-like
resources every load and store is affected.

## Therefore: "this reproduces" means

There is **no exit code to key on** — a silent miscompile exits 0 and prints plausible SPIR-V.
The predicate must read the disassembly. Two distinct questions, so two predicates:

1. **`match.json` (D5, the still-open case).** Given a heap-only *conditional* assignment,
   the emitted SPIR-V performs the atomic through a heap `OpUntypedAccessChainKHR` derived
   from an index variable that is **`OpUndef` / never stored on the fall-through path**, with
   no branch on which descriptor kind is live and no diagnostic. Concretely: the module
   compiles successfully (exit 0), and the descriptor index feeding the heap access chain
   traces to an undefined/unstored value. **Reproduces** = compiles clean *and* the heap
   access is taken unconditionally from an index that is undefined on one path.

2. **`match-mixing.json` (D1–D4, the filed defects).** Reproduces in the *originally filed*
   sense = the shader compiles successfully (exit 0) and the atomic/load is lowered through
   the heap alias, silently dropping the bound resource. It **does not** reproduce in that
   sense if the compiler emits the `mixing bound and descriptor heap resources` diagnostic —
   that is the reporter's own described current behaviour, i.e. `changed-behavior` relative to
   the title's "silent miscompilation or ICE".

## Predicted outcome, recorded so it can be wrong

I expect one of:

- **(a)** `-fspv-use-descriptor-heap` does not exist on `main` at `ab5400907` at all, because
  #8517 is unmerged. Then nothing here is measurable on the ground truth build, every release
  probe is an `invalid-probe`, and the verdict is `inconclusive` / `not-compiler-verifiable`
  pending the branch landing.
- **(b)** the flag exists and D1–D4 are diagnosed, matching the report's own update, while D5
  still silently miscompiles. Verdict `repros` for D5, `changed-behavior` for D1–D4.
- **(c)** the flag exists and none of it is diagnosed — the original silent miscompile as
  titled. Verdict `repros`.

## History is very likely unmeasurable

`SPV_EXT_descriptor_heap` is a **recent** extension. The bisection floor is v1.4.1907, which
answers `SPIR-V CodeGen not available`, and every shipping release older than the extension
will reject `-fspv-use-descriptor-heap` or `ResourceDescriptorHeap` outright. Those are
`invalid-probe`s. If **every** release is an invalid probe, `never-repro'd-in-releases` is
**not a fix** and must not be reported as one; the honest finding is that history is
unmeasurable and the value of this triage is the diagnosis.

## Repro quality

`partial`. The issue supplies four HLSL fragments; D1 is a complete, compilable shader with
its own command line. D2–D4 and D5 are snippets that must be completed into whole shaders
(entry point, `[numthreads]`, resource declarations, `original`). D5 — the case that matters
most, being the one the reporter says is still undiagnosed — is a fragment only.

## Command line, and the reporter's configuration

The report's command is:

```
dxc -T cs_6_6 -E main -fspv-use-descriptor-heap -fspv-target-env=vulkan1.3 -spirv repro.hlsl
```

No `-fcgl` and no `-Vd`, so there is no legalization/validation workaround to strip. Use it
exactly. Note that leaving validation **on** is load-bearing here: the reporter's own note
about the `OpPhi` of image type failure is a validator diagnosis, and disabling it would hide
the boundary between the loud and the silent failure.
