# #8732 — triage notes

**Ground truth:** `main-debug`, commit `ab5400907`
(`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)`),
verified before any probe was run. `ab5400907` is a merge of `upstream/main` at `13730886e`,
which includes `ec2ba18da` "Update SPIRV-Tools to 1c336172"; `external/SPIRV-Tools` is at
`1c336172` (`v2026.3.rc1-25-g1c336172`) to match.

**Verdict:** `inconclusive` — the reported defect is not present in the compiler under test,
because it is not present in `main` at all. See "Why not `does-not-repro`" below.

**Compiler Explorer:** https://godbolt.org/z/bcn4zoTdM (3 panes, all verified by recompiling
the published shortlink — see `godbolt-note.txt` for what each pane is for).

---

## 1. The single most important fact: the code being reported on is unmerged

The issue opens "Apart of #8517" and its Steps to Reproduce say "Compiled with #8517 branch."
**#8517 is an open pull request** — *[SPIR-V] Add SPV_EXT_descriptor_heap +
SPV_KHR_untyped_pointers codegen*, opened 2026-06-04, still `OPEN` — not an issue and not
merged.

Every symbol the issue names as the cause is absent from `main` at `ab5400907`. Grep over
`tools/` finds **zero** occurrences of:

```
descriptorHeapImageAliasVars      descriptorHeapBufferAliasVars
createDescriptorHeapIndexVar      tryToAssignDescriptorHeapImageAlias
tryToAssignDescriptorHeapBufferAlias                registerFnVarAlias (for this use)
emitDescriptorHeapImageTexelPointer                 diagnoseDescriptorHeapAliasMixing
descriptorHeapVarState
```

The line numbers in the report (`SpirvEmitter.cpp:5267`, `:5329`, `:5368`, `:5428`,
`:1299-1301`) are #8517-branch line numbers.

What `main` has instead is one much smaller thing:
`SpirvEmitter::doCXXOperatorCallExpr` (`tools/clang/lib/SPIRV/SpirvEmitter.cpp:6609`), whose
`isDescriptorHeap(expr)` block at `:6642` lowers `ResourceDescriptorHeap[i]` **at the point of
use** into `OpUntypedAccessChainKHR` + `OpLoad`, and hands the loaded handle back as an
ordinary SSA value. There is no alias map, nothing keyed on a `VarDecl`, and nothing that
survives across statements — so the *mechanism* the issue describes cannot occur.

That block also emits `warning: SPV_EXT_descriptor_heap support is incomplete.` (`:6658`) on
every heap access, and `error: UAV support not implemented with non-emulated heaps.` (`:6663`)
for any structured/byte-address buffer.

## 2. What `main` does with each reported case

`-T cs_6_6 -E main -fspv-use-descriptor-heap -fspv-target-env=vulkan1.3 -spirv` (the
reporter's exact command; no `-fcgl`/`-Vd` were filed, so there was no workaround to strip).

| case | file | capture | result on `main-debug` |
| --- | --- | --- | --- |
| D1 conditional assignment | `repro.hlsl` | `out-main-debug.txt` | `fatal error: generated SPIR-V is invalid: [VUID-StandaloneSpirv-OpTypeImage-06924] Cannot store to OpTypeImage…` |
| D2 reassign to bound | `defect2.hlsl` | `variant-defect2-main-debug.txt` | same VUID-06924 fatal error |
| D3 assignment in a loop | `defect3.hlsl` | `variant-defect3-main-debug.txt` | same VUID-06924 fatal error |
| D4 buffer reassignment | `defect4.hlsl` | `variant-defect4-main-debug.txt` | `error: UAV support not implemented with non-emulated heaps.` |
| D5 heap-only conditional | `defect5.hlsl` | `variant-defect5-main-debug--match-invalid-spirv.txt` | same VUID-06924 fatal error |

Nothing is silent. Every case exits `0x80004005` with a diagnostic. **No case produces a
crash or an assert** on the Debug ground-truth build, so the "or ICE" half of the title is
also not observable here.

### The cause of the loud failure, and why it is not this issue

`Interlocked*` lowers to `OpImageTexelPointer`, which requires a **pointer to an image
variable**. A heap descriptor on `main` is an SSA value, so DXC materialises a
`Function`-storage image variable, stores the handle into it, and takes
`OpImageTexelPointer` of that. `OpStore` to an `OpTypeImage` object is illegal SPIR-V, so
spirv-val rejects it. `mem2reg` cannot rescue it, because `OpImageTexelPointer` needs the
variable's address and so keeps it un-promotable.

This has nothing to do with mixing. A control with **no bound resource at all** —
`RWTexture2D<uint> h = ResourceDescriptorHeap[1]; InterlockedAdd(h[…], …)` — fails
identically. `Interlocked*` on a heap-loaded texture is simply not supported on `main`.

### `main` does not miscompile: the `-Vd` evidence

Because a validator rejection could be masking a wrong module underneath, the repro was
re-run with `-Vd` (`variant-vd-repro-main-debug.txt`, `variant-vd-defect2-main-debug.txt`).
The generated module is *semantically what the shader asked for*:

```
   %boundTex = OpVariable %_ptr_UniformConstant_type_2d_image UniformConstant
        %29 = OpVariable %_ptr_Function_type_2d_image Function
        %30 = OpLoad %type_2d_image %boundTex
              OpStore %29 %30              ; bound descriptor
        %36 = OpUntypedAccessChainKHR … %resource_heap %uint_1
              OpStore %29 %37              ; heap descriptor, inside the `if`
        %40 = OpImageTexelPointer %_ptr_Image_uint %29 %39 %uint_0
        %41 = OpAtomicIAdd %uint %40 %uint_1 %uint_0 %uint_1
```

Both descriptors go into the *same* variable and last-store-wins, which is exactly the
source semantics. `%boundTex` is preserved and still in `OpEntryPoint`. It is **illegal, not
wrong**. So `main` is not silently miscompiling this; the reported silent miscompile is a
property of #8517's alias-map lowering.

D5's `-Vd` module (`variant-vd-defect5-main-debug--match-invalid-spirv.txt`) shows the
analogous shape: an uninitialised `Function` image variable read after the merge — the
undefined-descriptor hazard the reporter describes does exist structurally on `main` too, but
it is caught loudly by validation rather than shipped silently.

## 3. History: only one release can run this repro at all

All 20 releases in the bisection sequence were probed under both predicates — 40 release
captures, `out-<tag>.txt` and `out-<tag>--match-invalid-spirv.txt`. **19 of 20 are
`invalid-probe`**, all with `dxc failed : Unknown argument: '-fspv-use-descriptor-heap'` —
v1.4.1907 through v1.9.2602.24 inclusive, verified by reading the last line of every capture,
not inferred from the bisect summary. Only **v1.9.2607** knows the flag, and it behaves
identically to `main-debug`, down to the same VUID:

```
fatal error: generated SPIR-V is invalid: [VUID-StandaloneSpirv-OpTypeImage-06924]
Cannot store to OpTypeImage, … OpStore %29 %30
```

`bisect` correctly refuses to conclude: `fewer than two releases can run this repro; no
history conclusion is possible`. Recorded as `history: unmeasurable (only v1.9.2607 of 20
releases can run the repro)`.

**This is emphatically not `never-repro'd-in-releases`, and must not be read as a fix.** Nor
does the SPIR-V floor (v1.4.1907 answers `SPIR-V CodeGen not available` for SPIR-V issues
generally) even come into play here — the flag is far newer than that.

## 4. The SPIRV-Tools dependency — a real, separate regression

The reporter's own documented workaround is "use separate variables for bound and
heap-loaded resources". `control-separate-vars.hlsl` is exactly that. It is the one place
where the two compilers **disagree**:

| compiler | capture | result |
| --- | --- | --- |
| v1.9.2607 | `variant-separate-vars-v1.9.2607.txt` | **exit 0** — valid module, atomic correctly on `%boundTex`, heap write via `OpUntypedAccessChainKHR` |
| main-debug | `variant-separate-vars-main-debug.txt` | `fatal error: generated SPIR-V is invalid: Array must be explicitly laid out with ArrayStride or ArrayStrideIdEXT decorations … in the UniformConstant storage class` |

This is the SPIRV-Tools bump, not a DXC codegen change: `ec2ba18da` (SPIRV-Tools →
`1c336172`) newly enforces explicit layout on `UniformConstant` arrays
(KhronosGroup/SPIRV-Tools#6792) and DXC does not emit `ArrayStride` on the heap runtime array.
The same commit XFAILed `tools/clang/test/CodeGenSPIRV/resource-heap-ext-texture.hlsl` for
this reason and its message names the consequence explicitly. It is **already tracked as
#8740** and is not reported here as new.

`-fvk-use-scalar-layout` does not help — retried by hand, same error under scalar layout
rules.

Net effect on `main` today: *no* shader that touches `ResourceDescriptorHeap` under
`-fspv-use-descriptor-heap` validates. Non-atomic uses die on ArrayStride (#8740); atomic
uses die first on VUID-06924. Had this triage been run against a build predating
`ec2ba18da`, the separate-variable workaround would have compiled cleanly and section 4
would not exist — so the SPIRV-Tools version *is* load-bearing for this issue's feature area,
exactly as flagged.

## 5. Why not `does-not-repro`

`does-not-repro` means "the repro runs clean; the symptom is gone". Neither half holds:

- The repro does not run clean — it fails, loudly, on every case.
- The symptom is not "gone". It was never in the measured compiler: it belongs to an
  unmerged branch. Reporting `does-not-repro` would invite closing an issue that is a live
  design note against work still in review, which is the opposite of what the evidence says.

`changed-behavior` was considered and rejected: `main` *does* misbehave on these inputs, but
it misbehaves identically without any mixing at all (the heap-only control fails the same
way), so the misbehaviour is not this issue's defect — it is the base feature being
incomplete.

`inconclusive` with `repro_quality: partial` is the honest record: a precise, well-evidenced
statement of what could and could not be measured, and why.

## 6. Assessment

The report is unusually high quality — it names the data structures, the call sites, the
consumption points per resource class, an explicit list of cases it verified as *not*
affected, a workaround, and a design sketch for the fix. Its one checkable aside also holds:
`control-phi-image-no-heap.hlsl` (a conditional between two **bound** textures, no
`-fspv-use-descriptor-heap`) fails with `fatal error: generated SPIR-V is invalid: Result type
cannot be OpTypeImage / %33 = OpPhi %type_2d_image …`
(`variant-phi-image-no-heap-main-debug--match-invalid-spirv.txt`), confirming that the
`OpPhi`-of-image limitation is real and independent of descriptor heaps. The issue is best read
as a **design review note on PR #8517**, not as a defect report against shipped or `main`
behaviour.

The one thing a reader cannot tell from the issue is that **none of it is reachable on
`main`**, and that anyone spot-checking it against `main` or against v1.9.2607 will see a
loud validation failure and reasonably conclude "cannot reproduce". That is recorded as
`text_stale`. The title compounds it: "causes silent miscompilation or ICE" is contradicted
by the issue's own *Actual Behavior* section, which says all four filed defects are now
diagnosed at compile time and that D4 no longer ICEs — only D5 (heap-only conditional
assignment) is still described as silent, and only on the #8517 branch.

**Suggested action:** `needs-human-judgement`. The decisions are for a SPIR-V maintainer:
whether this stays an issue or becomes review feedback on #8517; and whether the residual D5
case is tracked separately, since it is the only part the reporter says is still undiagnosed
and it needs dataflow analysis rather than the per-variable state check that catches D1–D4.

## 7. What was not tested

- **Runtime behaviour.** No GPU or Vulkan runtime was involved. Everything here is compile
  output.
- **PR #8517's branch.** Not built. Building it would have replaced the ground-truth compiler
  that other issues in this batch are measured against, so every claim about #8517 in these
  notes comes from the issue text and from the *absence* of those symbols in `main` — not
  from running that branch. **This is the main gap**: the reported silent miscompile has not
  been reproduced by anyone but the reporter, and confirming or refuting it requires a build
  of #8517.
- **`RaytracingAccelerationStructure`** (the third alias class the issue names). Not exercised;
  `main` has no `registerFnVarAlias` heap path to exercise.
- **The emulated heap path** (`-fspv-use-emulated-descriptor-heap`, the default). The issue is
  explicitly about the non-emulated path.

## 8. File index

| file | what it is |
| --- | --- |
| `repro.hlsl`, `cmd.txt` | defect 1, verbatim from the issue, with the reporter's exact command line. No `cmd-as-filed.txt`: nothing was changed, because nothing was filed to change — no `-fcgl`, no `-Vd` |
| `match.json` | the silent-miscompile predicate, with its precondition and both controls named in the note |
| `match-invalid-spirv.json` | the loud-failure predicate, for the behaviour actually seen |
| `defect2/3/4/5.hlsl` | the other reported cases, completed into whole shaders |
| `control-bound-only.hlsl` | negative control: `repro.hlsl` minus the heap line. Compiles cleanly on `main-debug`, so it is the control that exercises `match.json` against real emitted SPIR-V |
| `control-separate-vars.hlsl` | negative control: the reporter's workaround. On v1.9.2607 it carries **both** of `match.json`'s positive markers (`OpAtomicIAdd` and `OpUntypedAccessChainKHR`) and still scores `no-match`, which is what proves the predicate discriminates rather than matching everything |
| `control-phi-image-no-heap.hlsl` | corroborates the reporter's `OpPhi`-of-image aside |
| `variant-vd-*.txt` | `-Vd` runs, showing the module `main-debug` really generates |
