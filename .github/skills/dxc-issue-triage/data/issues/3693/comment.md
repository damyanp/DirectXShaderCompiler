> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3693](https://github.com/microsoft/DirectXShaderCompiler/issues/3693).

Still reproduces on `main` (1.9.0.5433, ab5400907), and on every release back to v1.6.2104
(the oldest that accepts `lib_6_6`).

**DXC already has this diagnostic, but does not reach it in this position.** Hoisting the
access out of the subscript makes the same compiler reject the same expression:

```
error: vector element index '3' is out of bounds
    const uint oob = indices[3];
                             ^
```

In `g_vertices[indices[3]]` the out-of-bounds element becomes `undef`, which is then used as
the buffer index:

```
call %dx.types.ResRet.f32 @dx.op.rawBufferLoad.f32(
    i32 139, %dx.types.Handle %31, i32 undef, i32 12, i8 7, i32 4)  ; line:124 col:118
```

Validation passes.

Across eleven positions, the front end diagnoses every one — local initializer, call argument,
assignment target, arithmetic operand, `.w` swizzle — except **when the access is the index
operand of another subscript**. That hole is not vector-specific: `g_vertices[a[3]]` on a
3-element *array* behaves identically, while `uint x = a[3];` errors with
`array index 3 is out of bounds`. When the resulting `undef` stays inside the shader the DXIL
validator sometimes catches it late (`Access to out-of-bounds memory is disallowed`), but when
it becomes a resource index, as here, nothing objects.

Source-wise the check is in `CheckHLSLArrayAccess`
(`tools/clang/lib/Sema/SemaHLSL.cpp:16904`), which recurses into `getArg(0)`, the object
being subscripted, but never into `getArg(1)`, the index.

Repro: https://godbolt.org/z/7KGrq6xMe (restated as a compute shader so FXC can compile it —
the behaviour is the same).

- **FXC** rejects it: `error X3504: array index out of bounds`, both in this position and
  hoisted.
- **clang-dxc trunk** accepts *both* forms — no diagnostic even for the hoisted
  `uint oob = indices[3];`, and the load index becomes `poison`. As a control, the same
  shader written with `indices.w` does error there
  (`vector component access exceeds type 'const uint3'`), so this is a real gap in the new
  front end rather than the flags being ignored. Possibly worth an issue there.

One note for anyone spot-checking the attached `DefaultRT.zip`: it uses
`RootFlags(XBOX_RAYTRACING)`, which public dxc rejects outright — the resulting error is the
root signature parser, not this bug. Replacing that token with `0` compiles the file
unchanged otherwise.

Whether this should be an error or a warning, and whether the check should cover statically
out-of-range indices generally, is a language/product call.

Suggested labels: `fxc-disagrees`, `incorrect-code`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
