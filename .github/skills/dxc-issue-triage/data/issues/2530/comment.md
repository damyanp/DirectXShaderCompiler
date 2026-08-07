> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2530](https://github.com/microsoft/DirectXShaderCompiler/issues/2530).

Both cases still reproduce on `main` (1.9.0.5433, `ab5400907`). Case 1 fails on
all 20 releases from v1.4.1907 through v1.9.2607, and case 2 was checked at both
endpoints and fails there too — v1.4.1907 (2019-07) is the oldest release
shipping a usable `dxc`, so that is as far back as it is possible to check. FXC
still accepts both.

**[Compiler Explorer: FXC / DXC 1.6.2112 / DXC trunk / clang](https://godbolt.org/z/Yzd9KjcaG)**

```
$ dxc -T ps_6_0 -E main repro.hlsl
repro.hlsl:7:16: error: variable length arrays are not supported in HLSL
    float array[uint(ARRAY_SIZE)] = { 1.0f };
               ^
```

### Where the line is drawn

The array and the `static const` are incidental. The bound is not an *integer
constant expression* under the C++03 ICE rules DXC inherited from clang, so the
declaration becomes a VLA:

| | |
| --- | --- |
| `float array[uint(ARRAY_SIZE)]`, `ARRAY_SIZE` a `static const float` | **error** |
| `float array[uint(1.0f)]` | compiles |
| `float array[ARRAY_SIZE]`, `ARRAY_SIZE` a `static const uint` | compiles |

`CheckICE` accepts an explicit cast only when its operand is a `FloatingLiteral`
(`tools/clang/lib/AST/ExprConstant.cpp:9317`); a `CK_FloatingToIntegral` applied
to a `DeclRefExpr` falls through to `IK_NotICE`, so `Sema::BuildArrayType`
builds a `VariableArrayType` and the HLSL check at
`tools/clang/lib/Sema/SemaType.cpp:2143` emits `err_hlsl_vla`. The second case
is the same rule one level out — `ARRAY_SIZE_UINT` is a const integral whose
*initializer* is not an ICE, so it cannot be used in one either. The
constant-expression evaluation is not HLSL-aware; only the diagnostic is.

Adjacent but not the same defect: dropping the cast (`float array[ARRAY_SIZE]`
with `ARRAY_SIZE` still `float`) takes a different path and gives
`error: size of array has non-integer type 'float'`.

### On "Related to #2188" — related, not the same defect

[#2188](https://github.com/microsoft/DirectXShaderCompiler/issues/2188) reaches
the same `err_hlsl_vla` from a different `CheckICE` case: a component of a
`const` vector. Measured here — `static const uint2 SIZE2 = uint2(1,1);
float array[SIZE2.x];` fails identically, with no float or conversion in the
bound:

```
crossref-vector-component.hlsl:16:16: error: variable length arrays are not supported in HLSL
    float array[SIZE2.x] = { 1.0f };
```

Neither construct appears in the other issue's repro, so **fixing either leaves
the other broken**. Same diagnostic, same FXC divergence, same area of
`CheckICE`; two rules.

### clang

clang's HLSL front end rejects both cases too, and names the cause:

```
<source>:7:22: note: read of non-constexpr variable 'ARRAY_SIZE' is not allowed in a constant expression
<source>:7:16: error: variable length arrays are not supported for the current target
```

That pane needs `-fsyntax-only`: clang's DXIL backend cannot yet lower a pixel
shader writing `SV_Target`, so without it a known-good control fails there too
and the pane says nothing about this issue. With it, the control compiles clean.

### Suggested labels

Keep `bug` and `fxc-disagrees` — FXC 10.1 compiles both cases and emits
`ps_5_0` code, verified in the link rather than taken from the report. Consider
adding `diagnostic`: the message reports a VLA, which HLSL does not have and
nobody here wrote, and names neither the conversion nor the constant-expression
rule. That is worth improving independently of whether HLSL's rules should
change to match FXC, which is a language decision this triage does not settle.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
