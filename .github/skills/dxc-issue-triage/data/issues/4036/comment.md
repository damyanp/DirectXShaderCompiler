> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4036](https://github.com/microsoft/DirectXShaderCompiler/issues/4036).

Still broken on `main` (1.9.0.5433, 13730886e) — but not in the way it was
reported. The compile error in the original post is gone; since **v1.7.2207** this
input crashes the compiler instead.

```
$ dxc -T ps_6_6 -E PSMain repro.hlsl
Internal Compiler error: llvm::cast<X>() argument of incompatible type!
[exit] 0x80AA001D
```

No source diagnostic or file/line/column; compilation dies in code generation.

**Compiler Explorer, the two states side by side:** https://godbolt.org/z/f59x8P75v
(1.6.2112 gives the reported diagnostic; trunk gives the internal error.)

### Where it fails

```
dxcompiler!llvm::llvm_cast_assert_internal
dxcompiler!llvm::cast<llvm::LoadInst,llvm::User>
dxcompiler!`anonymous namespace'::LowerGetResourceFromHeap
dxcompiler!CGHLSLMSHelper::FinishIntrinsics
dxcompiler!`anonymous namespace'::CGMSHLSLRuntime::FinishCodeGen
```

`LowerGetResourceFromHeap` in `tools/clang/lib/CodeGen/CGHLSLMSFinishCodeGen.cpp`
walks the users of the heap-subscript result assuming each is a `BitCastInst`
whose users are `LoadInst`s, and casts unconditionally. A member call on the cast
expression produces a different user, and the `cast<>` throws. That function is
byte-identical between v1.6.2112 and v1.7.2207, so what changed in that window is
upstream of code generation: the construct started reaching a lowering that was
never written to handle it.

### Scope

Only the member call directly on the cast is affected. Both of these compile
cleanly on `main`:

```hlsl
StructuredBuffer<float> buf = (StructuredBuffer<float>)ResourceDescriptorHeap[i];
return buf.Load(0);                                     // cast, then call
```
```hlsl
tex.Sample((SamplerState)SamplerDescriptorHeap[0], uv); // cast as an argument
```

So does the workaround suggested in the 2021-11-08 comment (assign the subscript to
a local and drop the cast). The construct itself appears in three tests, but all
three are `-ast-dump` or `-verify` and stop before code generation, which is why
nothing caught this.

The `[hlsl 2021]` in the original title looks incidental: output is byte-identical
with and without `-HV 2021` on every release that accepts the flag, and the
diagnostic reproduces on v1.6.2104 (2021-04), six months before the report.

### History

| | |
|---|---|
| v1.6.2104 – v1.6.2112 | reported diagnostic, `0x80004005` |
| v1.7.2207 – v1.9.2607, `main` | internal compiler error, `0x80AA001D` |

18 stable releases, every one that supports Shader Model 6.6 — for as long as it is
possible to check. v1.4.1907 and v1.5.2010 predate the feature and reject
`ps_6_6` outright, so they cannot answer. (Prereleases were not probed.)

### Suggested labels

`bug`, `crash` — currently unlabelled, and an unhandled internal cast failure is a
crash however the language question is eventually settled. Whether this spelling
should compile is a language decision this triage does not make; either way, an
internal compiler error is not an acceptable answer to it.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
