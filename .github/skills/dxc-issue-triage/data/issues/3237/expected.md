# #3237 — Library Reflection: Listing parameters return E_FAIL

*Written before running anything.*

## What the issue reports

Filed 2020-11-03 by @mrvux, split out of #657 at a maintainer's request (pow2clk: *"The
`GetFunctionParameter` issue looks unexpected. I notice we have no testing for it."*;
tex3d: *"I agree we should create a new issue for `GetFunctionParameter`."*).

Input — a library with one ordinary free function taking one parameter:

```hlsl
float3 Apply(float3 input)
{
   return input * 2.0f;
}
```

Reflection sequence, verbatim from the body:

```cpp
D3D12_FUNCTION_DESC func_desc;
auto fr = lib_ref->GetFunctionByIndex(0);
fr->GetDesc(&func_desc);

D3D12_PARAMETER_DESC pdesc;
auto p = fr->GetFunctionParameter(0);
HRESULT hr = p->GetDesc(&pdesc);
```

> hr for the parameter returns E_FAIL

## The symptom is an API HRESULT, not a process exit code

`E_FAIL` here is `HRESULT` `0x80004005` returned from
`ID3D12FunctionParameterReflection::GetDesc`, inside a host process that has loaded
`dxcompiler.dll` and driven `IDxcContainerReflection` → `ID3D12LibraryReflection` →
`ID3D12FunctionReflection` → `ID3D12FunctionParameterReflection`.

`dxc.exe` also exits with `0x80004005` for any ordinary diagnosed error (a syntax error, a
bad profile, a validation failure). **These two are unrelated.** Nothing about `dxc.exe`'s
exit status can confirm or refute this issue, and a `nonzero_exit` predicate over `dxc.exe`
would be measuring a different quantity that happens to share a numeric value.

## What "reproduces" means

Against a library container built from the shader above, driving the real reflection API:

| step | reproduces (bug present) | does not reproduce (fixed) |
| --- | --- | --- |
| `IDxcContainerReflection::GetPartReflection(DXIL part, IID_ID3D12LibraryReflection)` | S_OK | S_OK |
| `ID3D12LibraryReflection::GetDesc` → `FunctionCount` | ≥ 1 | ≥ 1 |
| `ID3D12FunctionReflection::GetDesc` → S_OK | S_OK (mangled `Name`) | S_OK |
| `D3D12_FUNCTION_DESC::FunctionParameterCount` | **0** *(expected, see below)* | 1 |
| `ID3D12FunctionReflection::GetFunctionParameter(0)` | non-null (a "null object" stub) | a real parameter |
| `ID3D12FunctionParameterReflection::GetDesc(&pdesc)` | **`E_FAIL` (0x80004005)** | `S_OK` |
| `pdesc.Name` / `.Type` / `.Class` / `.Rows` / `.Columns` / `.Flags` | never populated | `input`, `D3D_SVT_FLOAT`, `D3D_SVC_VECTOR`, 1, 3, `D3D_PF_IN` |

**The primary observable is the HRESULT from `ID3D12FunctionParameterReflection::GetDesc`.**
`E_FAIL` = reproduces. `S_OK` with a populated `D3D12_PARAMETER_DESC` = fixed.

`FunctionParameterCount` is the secondary observable and the more diagnostic one: if it is
`0`, then no parameter reflection exists at all and the `E_FAIL` is a *consequence* rather
than the defect. Capture it either way — it distinguishes "`GetDesc` is broken" from
"parameter reflection was never implemented for DXIL libraries", and those want different
fixes and different issue text.

## The reference behaviour

`ID3D11FunctionParameterReflection::GetDesc` (FXC/DXBC, D3D11 shader-linking libraries)
populates `D3D11_PARAMETER_DESC` fully. The reporter's stated use case is exactly that: scan
a DXIL library's function signatures to decide what may be linked, which their existing D3D11
path does through the D3D11 interface. So "should" here is *the D3D11 counterpart's
behaviour*, which is what the report compares against — not a written D3D12 spec.

Note tex3d's standing position in #657, which bears on the verdict but not on the
measurement: *"It may not be worth it to attempt to make reflection match in more than some
useful subset of ways. The implementation of DXIL library reflection in this interface was
limited to known use cases that were needed for developers using them at the time (for
DXR)."* If measurement shows parameter reflection was simply never populated, this is a
**gap, deliberately scoped**, rather than a regression — and the issue label `bug` may be
worth revisiting. That judgement is a maintainer's; the measurement is not.

## Repro quality

`partial`. The issue supplies the exact shader and the exact API call sequence, but no
compile command line, no host program, and no build of one. The shader is complete and
unambiguous; the driver has to be constructed. Everything needed to write it is in the issue.

## What would make this `not-compiler-verifiable`

Nothing about a GPU, driver or D3D runtime is involved: `IDxcContainerReflection` and
`ID3D12LibraryReflection` are implemented **inside `dxcompiler.dll`** and need no device.
So this is compiler-verifiable *in principle*. It is only `not-compiler-verifiable` if I
cannot build a harness that drives those interfaces with evidence — in which case the
verdict must say so plainly and specify exactly what the harness would have to do, rather
than substituting something `dxc.exe` prints.

## What I will NOT accept as evidence

- `dxc.exe` exiting `0x80004005`. Different quantity, same number.
- `dxc.exe -dumpbin` or `-Fre` succeeding. Those show a reflection *part exists*; the issue
  is about what the reflection *interface* returns when asked for a parameter.
- A successful compile of the library. The report never says the compile fails.
