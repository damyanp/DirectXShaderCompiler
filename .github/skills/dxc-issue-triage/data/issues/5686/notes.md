# #5686 — Validation fails when linking to amplification shader target

## Summary

Reproduces on `main-debug` (`89e2f98e2`, self-reports `1.9.0.5465 (triage, 7665270b9)`,
provenance note: fork-local build, tree identical to upstream `main`).

The reporter's exact repro (`repro.hlsl` + `cmd.txt`, verbatim from the issue): compile
`repro.hlsl` directly to `-T as_6_6` and it validates cleanly; compile the same source to
`-T lib_6_x -Fo as.lib`, then `dxc -T as_6_6 -link as.lib`, and DXIL validation rejects it:

```
$ dxc -T lib_6_x -Fo as.lib repro.hlsl
$ dxc -T as_6_6 -link as.lib
Link failed:
error: validation errors
Function: main: error: For amplification shader with entry 'main', payload size 8 is greater than declared size of 4 bytes.
note: at 'call void @dx.op.dispatchMesh.struct.payloadStruct(...)' in block '#0' of function 'main'.
Validation failed.
```

(`out-main-debug.txt`; exit 1, identical text to the issue's paste, including the "8 ... 4"
numbers.) The negative control, the direct `-T as_6_6` compile of the identical source, exits
0 and validates clean (`variant-direct-compile-main-debug.txt`, `--expect no-match`,
confirmed). So the divergence reported in 2023 is exactly reproduced today: same source, same
struct, different validation outcome depending only on whether it went through `-link`.

## History

`bisect --issue 5686 --linear`: `-link` is `Unknown argument` on v1.4.1907, v1.5.2010 and
v1.6.2104 (confirmed genuinely absent, not a spelling issue: `--help` on the cached v1.6.2104
binary has no `-link` entry at all; the cached v1.6.2106 binary's `--help` does — first
shipped release with the driver-level `-link` flag). Excluding those three as `invalid-probe`,
every one of the 18 probeable releases from **v1.6.2106 (2021-07-01) through v1.9.2607
(2026-07-29)** reproduces — a full linear scan, not just endpoint agreement — and so does
`main-debug`. No clean release exists anywhere in the probeable range — this has always
reproduced for as long as `-link` has existed, predating the 2023-09-11 report by over two
years. 5 prereleases were excluded from the search by policy (none named in the issue text).

`godbolt` was deliberately skipped (`--skip`, recorded): the whole subject is the difference
between one dxc invocation and a two-invocation lib-then-link pipeline, and Compiler Explorer
compiles exactly one command per pane with no way to hand one pane's artifact to another, so
it cannot express `-link` against an intermediate `.lib` at all.

## Root cause (source-grounded, not just observed)

Two independent defects combine to produce exactly this symptom, and reading the source
explains why the direct-compile path is silently fine while the linked path is not.

**1. The amplification-shader payload-size check measures the payload *pointer*, not the
payload *struct*.** `lib/DxilValidation/DxilValidation.cpp`:

```cpp
// ValidateAsIntrinsics, ~line 3234-3238 (amplification shader / DispatchMesh):
DxilInst_DispatchMesh DispatchMeshCall(DispatchMesh);
Value *OperandVal = DispatchMeshCall.get_payload();
Type *PayloadTy = OperandVal->getType();                 // <-- the POINTER type
const DataLayout &DL = F->getParent()->getDataLayout();
unsigned PayloadSize = DL.getTypeAllocSize(PayloadTy);
```

`DxilInst_DispatchMesh::get_payload()` (`include/dxc/DXIL/DxilInstructions.h:6201`) returns the
call's payload operand directly — for our shader that operand's LLVM type is
`%struct.payloadStruct addrspace(3)*`, a pointer, not `%struct.payloadStruct`. `PayloadSize` is
therefore always the ABI size of a pointer in this address space, never the actual payload
struct's size, regardless of the real payload's contents.

Three lines above, the mesh-shader (`GetMeshPayload`) branch of the *same function* does this
correctly:

```cpp
// ~line 3200-3205:
PointerType *PayloadPTy = cast<PointerType>(GetMeshPayload->getType());
StructType *PayloadTy = cast<StructType>(PayloadPTy->getPointerElementType());  // dereferenced
unsigned PayloadSize = DL.getTypeAllocSize(PayloadTy);
```

So the mesh-shader check measures the pointee struct; the three-lines-away amplification-shader
check measures the pointer itself. This looks like a copy/paste omission of
`->getPointerElementType()`.

**2. The DXIL linker never sets the linked module's data layout.**
`lib/HLSL/DxilLinker.cpp`, `DxilLinkJob::Link` (~line 752-758):

```cpp
std::unique_ptr<Module> pM =
    llvm::make_unique<Module>(entryFunc->getName(), entryDM.GetCtx());
pM->setTargetTriple(entryDM.GetModule()->getTargetTriple());   // triple copied
// ... no pM->setDataLayout(...) anywhere in this function or file
```

`git log -S DataLayout -- lib/HLSL/DxilLinker.cpp` returns no commits: the file has never once
called `setDataLayout`. A freshly constructed `llvm::Module` with no explicit data layout falls
back to LLVM's built-in default (`lib/IR/DataLayout.cpp`, `DataLayout::reset("")`), whose
`setPointerAlignment(0, 8, 8, 8)` gives every pointer an 8-byte size — versus DXIL's own layout
strings (`kLegacyLayoutString`/`kNewLayoutString` in `lib/DXIL/DxilModule.cpp:67-72`), both of
which declare `p:32:32`, a 4-byte pointer. The captured disassembly confirms this directly:
compiling `repro.hlsl` straight to `as_6_6` emits `target datalayout = "e-m:e-p:32:32-..."`
(`variant-direct-compile-main-debug.txt:58`), but the linked module (disassembled with `-Vd` to
see it despite the validation failure) has no `target datalayout` line at all — disassembly
goes straight from the PSV comment block to `target triple`
(`manual-case-linked-vd-disasm.txt`, generated by `capture-vd-disasm.py`; compare line 58 in
the direct capture to line 54 in the linked one, where the datalayout line is simply absent).

**Together:** for a direct compile, defect #1's `PayloadSize` is always exactly the DXIL
pointer size (4 bytes), so the check `declared < PayloadSize` only ever fires if the reporter's
struct is under 4 bytes — effectively never in practice, so the check is silently vacuous for
every direct-compiled amplification shader, not just this one (no test in
`tools/clang/test/` exercises the "greater than declared size" message text for either mesh or
amplification shaders — `grep` finds none). For a linked compile, defect #2 changes the
baseline pointer size defect #1 measures from 4 to 8, so the same vacuous check now fires for
any linked amplification shader whose declared payload is under 8 bytes — which is exactly what
happened here (4 < 8). The reporter's 4-byte struct is otherwise completely irrelevant to the
failure; any struct under 8 bytes would trigger the identical message post-link, and any struct
of 8 bytes or more would validate whether or not it was actually correctly sized, in both the
linked and unlinked paths, because the check never inspects the real payload type either way.

This is corroboration from source, not merely an output observation: it explains why the issue
is real, reproducible, deterministic, present since `-link` was introduced, and why "the same
shader validates when compiled directly" is not evidence the payload size itself is fine — the
check was never actually testing it.

## Text staleness

None. The issue's title, body and repro are accurate and still describe current behaviour
exactly; no maintainer comment (there are no comments) and nothing in the thread contradicts
the report.

## Labels

Current: `bug`, `shader-linking`, `validation`. All three are accurate and no change is
proposed — this is exactly a linking bug that surfaces as a validation error.
