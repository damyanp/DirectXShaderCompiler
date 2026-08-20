# Expected symptom (written before any probe is run)

Issue #5633: "DXC should warn on statically checkable out-of-bounds".

The repro (from the linked Compiler Explorer link, godbolt.org/z/frv3neY5x, embedded
verbatim in `repro.hlsl`) declares:

```hlsl
struct LineStyle { float phaseShift; uint _pad[1u]; };
StructuredBuffer<LineStyle> lineStyles : register(t1);
...
return float(lineStyles[45]._pad[2000]).xxxx;
```

Two indexing operations are present:

1. `lineStyles[45]` — indexes the *StructuredBuffer* itself, which SPIR-V/DXIL represents
   as an unbounded (runtime-sized) array. This index is **not** statically checkable and
   the reporter explicitly says so ("if I were to index using some runtime variable...
   impossible to bounds-check"). This is not the ask.
2. `._pad[2000]` — indexes a **fixed-size** array member (`uint _pad[1]`) declared inside
   the struct, using a compile-time integer literal (`2000`). The array bound (1) and the
   index (2000) are both known at compile time. This is the ask: the reporter wants DXC to
   emit a warning or error for this specific, statically-provable out-of-bounds access,
   analogous to how many C/C++ compilers warn on `int a[1]; a[2000];`.

**"Reproduces" means:** `dxc` compiles this shader (either DXIL or SPIR-V, `-spirv`) to
completion (exit 0) while emitting **no diagnostic (warning or error) whatsoever** that
mentions the out-of-bounds constant array access on `_pad`. Ordinary successful codegen
with zero diagnostic text is the reported (mis)behavior — there is nothing to bounds-check
at runtime here, the request is purely about a missing *compile-time* diagnostic.

**"Does not reproduce" / "fixed" means:** `dxc` now emits a warning or error identifying
the statically out-of-bounds constant index into `_pad`.

**"Not compiler-verifiable"** would apply if the request turned out to hinge on a
runtime/driver contract (e.g., "is this UB per the SPIR-V spec") rather than on the
compiler's own diagnostic output — but the literal ask ("compiler should emit warning or
error") is answerable purely from `dxc`'s own diagnostic stream, so this is compiler
verifiable.

Repro quality: **complete** — the exact reporter shader is available verbatim via the
Compiler Explorer permalink embedded in the issue body, and it is reproduced byte-for-byte
in `repro.hlsl` (only the CE HTML entity escaping of `<`/`>` was undone).

This is fundamentally a **feature request for a new diagnostic**, not a report of a crash
or miscompile. `enhancement-not-bug` and `still-valid-keep-open` are both plausible
suggested actions depending on whether the underlying array-indexing sanitizer already
exists in some other form; that will be checked, not assumed, before running anything.
