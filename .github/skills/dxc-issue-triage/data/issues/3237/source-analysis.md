# #3237 -- what the source says

Read-only investigation of the DXC tree at ground truth `ab5400907`. Every
line below is quoted from the repository; nothing here is inferred from
program output. Commands are given so each can be re-checked.

## 1. The E_FAIL is hardcoded and unconditional

`lib/HLSL/DxilContainerReflection.cpp:719`

    class CInvalidFunctionParameter final
        : public ID3D12FunctionParameterReflection {
      STDMETHOD(GetDesc)(D3D12_PARAMETER_DESC *pDesc) { return E_FAIL; }
    };
    CInvalidFunctionParameter g_InvalidFunctionParameter;

There is no branch, no data lookup and no failure condition. This object
returns E_FAIL always.

## 2. The real GetFunctionParameter always hands back that object

`lib/HLSL/DxilContainerReflection.cpp:2834`, inside `CFunctionReflection` --
the class actually used for DXIL library reflection, not a stub:

    // Use D3D_RETURN_PARAMETER_INDEX to get description of the return value.
    STDMETHOD_(ID3D12FunctionParameterReflection *, GetFunctionParameter)
    (INT ParameterIndex) { return &g_InvalidFunctionParameter; }

`ParameterIndex` is never read. Every index, including
`D3D_RETURN_PARAMETER_INDEX`, yields the same always-E_FAIL singleton. So the
reported symptom is not a lookup that fails for some inputs -- it is the only
behaviour this method has.

    git grep -n "GetFunctionParameter" -- lib tools include

returns exactly two hits: this one and the identical line in `CInvalidFunction`
(line 744), the null-object used when a function cannot be found. In other
words the "valid" path and the "invalid" path are the same path.

## 3. FunctionParameterCount is deliberately left unset

`CFunctionReflection::GetDesc` (line 2838 onward) zeroes the output struct and
then fills in Version, ConstantBuffers, BoundResources, RequiredFeatureFlags
and Name. A long list of remaining fields is left alone, each with a comment
recording that fact; the two that matter here are:

    git grep -n "Unset:" -- lib/HLSL/DxilContainerReflection.cpp
    ... (36 hits in this file; the two relevant to this issue are) ...
    lib/HLSL/DxilContainerReflection.cpp:2904:  // Unset: INT FunctionParameterCount; // Number of logical parameters in the
    lib/HLSL/DxilContainerReflection.cpp:2906:  // Unset: BOOL HasReturn; // TRUE, if function returns a value, false - it is

This is why `FunctionParameterCount` reads 0 and `HasReturn` reads FALSE for a
function that plainly has both: the fields are never written, so the caller
sees the zeroes from `ZeroMemoryToOut`. It also means the 0 is not a computed
answer that happens to be wrong -- it is the absence of an answer, and a
caller has no way to tell those apart.

Most of the other `Unset:` fields are instruction-count statistics that do not
apply to DXIL; `FunctionParameterCount` and `HasReturn` are different in kind,
because they describe the function's signature rather than its code, and the
signature is exactly what this issue asks for.

## 4. The container format carries no parameter data to reflect

`include/dxc/DxilContainer/RDAT_LibraryTypes.inl`, `RuntimeDataFunctionInfo`
(the RDAT record that backs library reflection) declares:

    Name, UnmangledName, Resources, FunctionDependencies, ShaderKind,
    PayloadSizeInBytes, AttributeSizeInBytes, FeatureInfo, ShaderStageFlag,
    MinShaderTarget

There is no parameter list, no parameter types and no return type. The
neighbouring `SignatureElementTable` exists but describes entry-point shader
signatures (semantics, registers, component masks), not free-function
parameters.

This is the load-bearing fact. Points 1-3 could in principle be fixed by
writing some code in the reflection layer; point 4 means the information is
not present in the compiled container at all, so a fix has to add data to the
RDAT part -- a container format change -- not just fill in a getter.

## 5. It has never behaved differently

    git log -S "GetFunctionParameter" -- lib/HLSL/DxilContainerReflection.cpp

returns exactly one commit:

    c1b6627843a7cead9af67e4cca8da5e5c353167a  2018-04-11  Support ID3DLibraryReflection

The stub arrived in its present form in the commit that introduced DXIL
library reflection and has not been edited since. There is no regression to
find and nothing for `git bisect` to land on: the feature was never
implemented. That is consistent with what @tex3d wrote in #657 -- "The
implementation of DXIL library reflection in this interface was limited to
known use cases that were needed for developers using them at the time (for
DXR)".

## 6. There is no test coverage, and the current tests assert the zero

    git grep -n "GetFunctionParameter"     # 2 hits, both implementations
    git grep -ln "D3D12_PARAMETER_DESC"    # 1 file, the implementation

No test, sample or tool in the repository ever calls `GetFunctionParameter` or
names `D3D12_PARAMETER_DESC`. @pow2clk's remark in #657 -- "I notice we have
no testing for it" -- is still accurate.

Meanwhile `FunctionParameterCount: 0` is baked in as the *expected* value in
ten CHECK lines across nine lit tests:

    git grep -c "FunctionParameterCount" -- tools/clang/test
    tools/clang/test/HLSLFileCheck/d3dreflect/amp-groupshared.hlsl:1
    tools/clang/test/HLSLFileCheck/d3dreflect/comp-groupshared.hlsl:1
    tools/clang/test/HLSLFileCheck/d3dreflect/empty_broadcasting_nodes.hlsl:1
    tools/clang/test/HLSLFileCheck/d3dreflect/empty_thread_nodes.hlsl:1
    tools/clang/test/HLSLFileCheck/d3dreflect/lib_cb_matrix_array.hlsl:1
    tools/clang/test/HLSLFileCheck/d3dreflect/lib_global.hlsl:2
    tools/clang/test/HLSLFileCheck/d3dreflect/mesh-groupshared.hlsl:1
    tools/clang/test/HLSLFileCheck/d3dreflect/raytracing_traceray.hlsl:1
    tools/clang/test/HLSLFileCheck/d3dreflect/raytracing_traceray_readback.hlsl:1

Most of those reflect entry points that genuinely take no parameters, so the
0 is not wrong there -- these are not tests of the defect. The point is only
that anyone fixing this should expect to update expected output, and that no
existing test would notice today's behaviour changing.

## What this implies for the verdict

The issue reproduces exactly as reported and on every release measured. But
the shape of the defect is "never implemented, and the data is not in the
container" rather than "implemented and broken". That distinction is not
cosmetic: it is the difference between a getter fix and an RDAT format
addition, and it is what @tex3d's question in #657 -- how high a priority is
this for developers who want it -- was asking about.
