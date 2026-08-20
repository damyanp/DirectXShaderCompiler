> [!WARNING]
> **Draft -- not a maintainer decision.** AI-assisted triage for
> [#5546](https://github.com/microsoft/DirectXShaderCompiler/issues/5546).

DXC output supports the compiler-behavior claim. Two otherwise-identical pixel shaders differ
only inside `if (pos.x < 0) { ... }`:

```hlsl
// A: discard;
// B: return float4(0,0,0,0);
```
```hlsl
buf[0] = 42;          // RWStructuredBuffer<uint>
return float4(1,1,1,1);
```

`discard` (`-T ps_6_0`, DXIL):

```
call void @dx.op.discard(i32 82, i1 true)
br label %5
; <label>:5           ; preds = %4, %0
call void @dx.op.bufferStore.i32(... i32 42 ...)     ; reached from BOTH arms
call void @dx.op.storeOutput.f32(... 1.0 ...)        ; unconditional, x4
```

`return` (same command, same structure otherwise):

```
br i1 %3, label %5, label %4
; <label>:4           ; preds = %0 (only when NOT taking the early exit)
call void @dx.op.bufferStore.i32(... i32 42 ...)     ; SKIPPED on the early-return arm
br label %5
```

`discard` reaches the write/output block from both branch arms. `return` reaches the write
block from one arm, so the early-return arm skips it. `discard` is a non-terminating intrinsic
that falls through; it does not jump past later statements the way the
[Flow Control](https://learn.microsoft.com/en-us/windows/win32/direct3dhlsl/dx-graphics-hlsl-flow-control)
page's own definition ("jump...to an instruction other than the one on the next line")
describes. Any UAV/export elision happens after this compiled control flow, not as a branch
here.

That Learn page (last updated 2025-03-11) still groups `discard` in the same bullet list as
`break`/`continue`/`do`/`for`/`if`/`switch`/`while` as of this writing, so the reported text
hasn't changed.

Scope note: that page is not in this repository (`original_content_git_url` ->
`github.com/MicrosoftDocs/win32-pr`), so edit requests belong there; this repo can only confirm
compiler behavior.

Same shape holds on Compiler Explorer's oldest published DXC (1.6.2112) and on trunk:
https://godbolt.org/z/rnEKhGWcY

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
