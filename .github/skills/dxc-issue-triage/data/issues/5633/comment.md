> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5633](https://github.com/microsoft/DirectXShaderCompiler/issues/5633).

Still reproduces on `main` (local Debug build, commit `89e2f98e2`) and on every stable
release back to v1.5.2010 (2020-10-22, before v1.4.1907 SPIR-V codegen didn't exist yet) --
this has never diagnosed the reported access.

`dxc -T ps_6_0 -E main -spirv` on the exact repro compiles to completion, exit 0, empty
stderr, and bakes the literal straight into the access chain:
```
%23 = OpAccessChain %_ptr_Uniform_uint %lineStyles %int_0 %uint_45 %int_1 %int_2000
```
against `%_arr_uint_uint_1` (a one-element array). Plain DXIL codegen (no `-spirv`) folds
the same literal into a constant byte offset with no diagnostic either. Verified the same
way on Compiler Explorer against `dxc_1_6_2112`, `dxc_trunk`, and `hlsl_clang_trunk` (the
Clang-based successor front end): https://godbolt.org/z/KG9b5j1f8 -- none of the three warn.

Worth noting: DXC already has a diagnostic for exactly this
(`err_hlsl_array_element_index_out_of_bounds`, "array index N is out of bounds",
exercised by `tools/clang/test/SemaHLSL/array-index-out-of-bounds.hlsl`) -- it's just not
reaching this shape. Reading `Sema::CheckArrayAccess` in
`tools/clang/lib/Sema/SemaChecking.cpp` turned up two things that both apply here:

1. The full-expression entry point only looks through parens/implicit casts, `*`/`&`, and
   `?:` before checking for an array subscript; anything else wrapping the subscript
   (including a swizzle like `.xxxx`) silently exits without checking.
2. A size-1 array that's a struct field is deliberately exempted, to avoid warning on the
   classic C89 flexible-array-member idiom. `_pad` is declared `uint _pad[1]`, which
   matches that exemption even though it's being used here as plain (if oversized) padding,
   not a flexible array.

Either one alone would already hide this; the repro combines both (a struct-member array
of size 1, indexed and then swizzled), so it's fully silent rather than partially caught.

Suggest keeping `bug` + `enhancement` + `diagnostic` as-is, and treating this as narrowing
the existing check's two exemptions rather than adding a new one from scratch.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
