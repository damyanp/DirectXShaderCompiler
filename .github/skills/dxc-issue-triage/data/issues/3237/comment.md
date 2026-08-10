> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3237](https://github.com/microsoft/DirectXShaderCompiler/issues/3237).

**Still reproduces on `main`** (`13730886e`; the local build reports
`1.9.0.5433`) and on all 21 releases I could measure, **v1.4.1907
(2019-07-15) through v1.9.2607 (2026-07-29)**.

`dxc.exe` cannot show this, so I drove the API directly. For
`export float3 Apply(float3 input)` compiled at `lib_6_3`:

```
ID3D12FunctionReflection::GetDesc -> 0x00000000 (S_OK)
  D3D12_FUNCTION_DESC.Name="\x01?Apply@@YA?AV?$vector@M$02@@V1@@Z"
  D3D12_FUNCTION_DESC.FunctionParameterCount=0
  D3D12_FUNCTION_DESC.HasReturn=FALSE
ID3D12FunctionParameterReflection::GetDesc(param 0) -> 0x80004005 (E_FAIL)
ID3D12FunctionParameterReflection::GetDesc(D3D_RETURN_PARAMETER_INDEX) -> 0x80004005 (E_FAIL)
```

That name is byte-for-byte the one @mrvux quoted in #657
(`^A?Apply@@YA?AV?$vector@M$02@@V1@@Z`, where `^A` is the leading `0x01`), so
the walk is landing where the report says. Note the two extra findings
alongside the `E_FAIL`: `FunctionParameterCount` is **0** for a function with
one parameter, and `HasReturn` is **FALSE** for one returning `float3`. DXC's
own `dxa -dumpreflection` agrees, so this is not an artefact of my harness —
with two parameters and a return value it still prints
`FunctionParameterCount: 0`, `HasReturn: FALSE`.

### It was never implemented, rather than broken

On `13730886e`:

1. `CFunctionReflection::GetFunctionParameter` (`lib/HLSL/DxilContainerReflection.cpp:2834`)
   ignores its index and always returns `&g_InvalidFunctionParameter`.
2. That object's `GetDesc` is `{ return E_FAIL; }` — unconditional (line 719).
3. `CFunctionReflection::GetDesc` carries `// Unset: INT FunctionParameterCount;`
   and `// Unset: BOOL HasReturn;` (lines 2904, 2906), which is why those read 0
   and FALSE — they are never written, not computed wrongly.
4. **`RuntimeDataFunctionInfo` in `RDAT_LibraryTypes.inl` has no parameter
   records at all** — no parameter list, types or return type. The data is not
   in the container, so this is an RDAT format addition, not a getter fix.

`git log -S GetFunctionParameter -- lib/HLSL/DxilContainerReflection.cpp` returns
exactly one commit, `c1b662784` (2018-04-11, "Support ID3DLibraryReflection").
The stub has never been edited. This matches what @tex3d wrote in #657: library
reflection here "was limited to known use cases that were needed for developers
using them at the time (for DXR)". @pow2clk's remark in the same thread — "I
notice we have no testing for it" — also still holds: `GetFunctionParameter`
has no caller anywhere in the repository, tests included.

### One note for anyone re-checking

The source in the issue body needs `export` to be reachable. Without it the
function has internal linkage and `D3D12_LIBRARY_DESC.FunctionCount` is **0**,
so the reported call is never reached — I confirmed that on all 21 releases,
including v1.5.2010, current when this was filed. That is a gap in the repro,
not in the report: with `export` added, it reproduces exactly as described.

Whether this is worth implementing remains the product question raised in
#657; these measurements do not address priority.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
