> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3695](https://github.com/microsoft/DirectXShaderCompiler/issues/3695).

**Still reproduces.** The attached `shader.txt` crashes `main` at `1.9.0.5433` (`13730886e`)
with the filed command line, and all 20 bisectable release binaries measured from v1.4.1907
to v1.9.2607.

Debug build, `dxc -T cs_6_0 -E main shader.txt` — exit `0xE0000001`, and this is the entire
output:

```
Internal compiler error: LLVM Assert
```

Under a debugger the assert is `assert(Val && "isa<> used on a null pointer")` at
`include/llvm/Support/Casting.h(96)`, reached from
`DxilLowerCreateHandleForLib::ReplaceResourceUserWithHandle`.

It is not Debug-only. Release v1.9.2607 exits `0xC0000005`:

```
Internal compiler error: access violation. Attempted to read from address 0x0000000000000019
```

All 20 measured releases crash. **v1.4.1907 and v1.5.2010 produce no output at all** — empty
stdout and stderr, exit `0xC0000005`.

### Smaller repro, and a correction

The body's guess that this is *"assigning one `RWTexture2D<float4>` global variable to another"*
turns out not to be the trigger. That construct on its own is diagnosed correctly:

```
error: local resource not guaranteed to map to unique global resource.
```

The 10-line crashing reduction passes a global resource through a function and assigns the
result back to **the same** global:

```hlsl
RWTexture2D<float4> A;

RWTexture2D<float4> pick(RWTexture2D<float4> tex) {
  tex[uint2(0, 0)] = 1.0;
  return tex;
}

[numthreads(8, 8, 1)]
void main(uint3 id : SV_DispatchThreadID) {
  RWTexture2D<float4> local = pick(A);
  A = local;
}
```

The straight assignment and the different-global function variant are diagnosed, not crashed.

### Compiler Explorer

<https://godbolt.org/z/aqPedMGE4> — `dxc_1_6_2112`, `dxc_trunk` and `hlsl_clang_trunk`, all at
`-T cs_6_0 -E main`. Both DXC panes exit 139 (SIGSEGV). CE runs Release Linux builds, so the
assert above cannot appear there.

Clang rejects the same source cleanly, with a location:

```
<source>:84:14: error: assignment to global resource variable '_blurResult' is not allowed
   84 |         _blurResult = filterFog;
<source>:35:21: note: variable '_blurResult' is declared here
```

(Checked against a control: a valid version of the same shader passes `hlsl_clang_trunk`
`-fsyntax-only` cleanly, so the error is specific to this construct.)

Suggested label: **`diagnostic`**, alongside the existing `bug`/`crash`/`incorrect-code` — the
defect is that invalid code produces no diagnostic, and #5681, #6016, #6964 and #7582 already
carry that combination.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
