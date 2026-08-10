> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4351](https://github.com/microsoft/DirectXShaderCompiler/issues/4351).

Still reproduces on `main` (1.9.0.5433, `13730886e`), using the command from the
report unchanged.

```
$ dxr -E InitArgs -remove-unused-globals repro.hlsl
struct Parent {
  Child MultipleChildren[2];
};
RWStructuredBuffer<Parent> ParentBuffer;
[numthreads(1, 1, 1)]
void InitArgs() {
  ParentBuffer[0] = (Parent)0;
}
```

The output does not compile:

```
$ dxc -T cs_6_0 -E InitArgs rewritten.hlsl
rewritten.hlsl:2:3: error: unknown type name 'Child'
```

`dxr -no-warnings` turns on the rewriter's accounting (the flag is inverted in
`dxr.cpp`), which shows the removal is deliberate rather than a printing bug —
`//found 1 types to remove` for the array form, `//found 0 types to remove` when
the same member is declared as plain `Child SingleChild;`. So the title's
attribution to the array is right: only the array form is affected.

The 2022-08-15 comment about unused function parameters also reproduces. That
comment had no repro, so this shader is mine — `Helper` takes two struct
parameters, one read and one not:

```
uint Helper(ParamUnused notRead, ParamUsed isRead) { return isRead.B; }
```

`struct ParamUsed` survives, `struct ParamUnused` is removed while the signature
that names it stays. Reading the parameter is what saves its type.

In `DoRewriteUnused` (`tools/clang/tools/libclang/dxcrewriteunused.cpp`), type
liveness is computed from *value references*. `SaveTypeDecl`'s field loop calls
`fieldDecl->getType()->getAsTagDecl()` (`:113`), which is null for a
`ConstantArrayType`, so an array member's element type is never marked used;
and nothing walks `FunctionDecl::params()` for type usage at all.

History: reproduces on every stable release that can express the option — 19 of
20, v1.5.2010 through v1.9.2607. v1.4.1907 is excluded rather than negative: its
`HLSLOptions.td` has no rewriter options, so the repro cannot be run there. Each
release was probed with the same `dxr.exe` loading that release's
`dxcompiler.dll`, with the non-array case as a per-release control.

Suggested label: **`rewriter`**, which is exactly what this is and currently
missing.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
