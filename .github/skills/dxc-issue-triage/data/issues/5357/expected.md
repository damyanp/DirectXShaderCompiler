# Expected symptom — #5357

**Title:** Ensure type annotations are added for reference returning intrinsics/operators

**Claim (issue body, llvm-beanz):** If an intrinsic returns a reference to a new object/UDT
that isn't guaranteed to already be annotated, current code fails to add a type annotation for
that type when the reference is used directly (chained) rather than first being
assigned/copied into a temporary variable. A non-reference return gets its annotation added
later, in `EmitAutoVarAlloca`, which only runs when a temp is created. The action requested is
open-ended tech debt: "find what else this type annotation gap might impact, write a test for
that, and fix it" — not a single fixed defect with one closing repro.

**Concrete repro (tex3d, 2024-01-31, comment
https://github.com/microsoft/DirectXShaderCompiler/issues/5357#issuecomment-1918255108):**

```hlsl
struct RECORD1 {
    uint value;
};

[Shader("node")]
[NodeLaunch("broadcasting")]
[NodeDispatchGrid(1, 1, 1)]
[NumThreads(128, 1, 1)]
void node_1_1(
    [NodeArraySize(128)] [MaxRecords(64)] NodeOutputArray<RECORD1> OutputArray
) {
    OutputArray[1].GetThreadNodeOutputRecords(2).OutputComplete();
}
```

Quoted claim: "I was able to crash the current code due to a missing annotation still with
this". This chains `GetThreadNodeOutputRecords(2)` straight into `.OutputComplete()` with no
intermediate `ThreadNodeOutputRecords<RECORD1>` local — the shape the thread says skips the
annotation path. `tools/clang/test/HLSLFileCheck/hlsl/workgraph/nodeoutputarray.hlsl` covers
the *same* API but always through an intermediate variable, so it does not exercise this gap.

**"Reproduces" means:** compiling this source at `-T lib_6_8` on the local Debug `main-debug`
build produces an internal failure (the thread describes it as a crash from a missing type
annotation, not a diagnosed HLSL error) — `internal_failure` per the skill's crash predicate
table (assert trap 0x80000003/0xE0000001, access violation 0xC0000005, or an
`llvm::cast<X>()` message under E_FAIL).

**"Does not reproduce" means:** the same command exits 0 and the reporter's exact source
compiles cleanly (or reports only an ordinary diagnosed error unrelated to a missing
annotation), i.e. the specific instance tex3d posted is now fixed even though the issue itself
is scoped as broader tech-debt ("find what else this gap might impact") that a single clean
compile cannot fully close.

**Known related, not this issue's fix:** #5358 (NodeOutputArray's own `operator[]` returning a
reference) was fixed separately and is explicitly described in this thread as resolving the
*triggering* case, while the underlying annotation gap "remains ... might impact some other
operator". PR #6227 ("Add type annotations for missing HLSL object cases") is linked from this
thread and, per the timeline, is still open — record its state, do not assume it landed.

**Repro quality:** complete (reporter-provided, exact source and exact profile inferred from
the sibling FileCheck test using the identical API).
