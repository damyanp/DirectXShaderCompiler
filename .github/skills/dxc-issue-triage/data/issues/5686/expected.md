# Expected symptom (#5686)

Reported by dmpots (2023-09-11), against `dxcompiler.dll: 1.7 - 1.7.0.14071 (main, 9a0768d66);
dxil.dll: 1.6(101.6.2104.33)`.

Repro (verbatim from the issue):

```
> cat as.hlsl
struct payloadStruct
{
    uint myArbitraryData;
};

groupshared payloadStruct p;

[shader("amplification")]
[RootSignature("")]
[numthreads(1,1,1)]
void main(in uint3 groupID : SV_GroupID)
{
    p.myArbitraryData = groupID.z;
    DispatchMesh(1,1,1,p);
}

> dxc /Tas_6_6 as.hlsl
... outputs an amplification shader as expected ...
> dxc /Tlib_6_x /Fo as.lib as.hlsl
> dxc.exe /Tas_6_6 -link as.lib
Link failed:
error: validation errors
Function: main: error: For amplification shader with entry 'main', payload size 8 is greater than declared size of 4 bytes.
note: at 'call void @dx.op.dispatchMesh.struct.payloadStruct(...)' in block '#0' of function 'main'.
Validation failed.
```

**Claim:** compiling `as.hlsl` directly to `as_6_6` succeeds. Compiling the same source to a
`lib_6_x` library and then linking it to an `as_6_6` target fails DXIL validation with a
payload-size mismatch: the validator reports the payload is 8 bytes while the shader's own
`payloadStruct` (one `uint`) is 4 bytes. The direct-compile and link-then-compile paths are
claimed to produce different validation outcomes for byte-identical source.

**This reproduces** if:
- direct `-T as_6_6` compile of `as.hlsl` succeeds (validates clean), AND
- `-T lib_6_x` compile to a `.lib` followed by `dxc -T as_6_6 -link as.lib` fails DXIL
  validation with a "payload size ... is greater than declared size ..." error (any byte
  values, since exact sizes may differ across builds as long as the *mismatch* is present and
  the two paths disagree).

**Does not reproduce** if both paths succeed, or both paths fail identically (which would
suggest the issue is elsewhere / already fixed and this description is stale), or if the
link path succeeds while the direct path is the one that fails (an inversion, would be
`changed-behavior`).

Repro quality: **complete** — the issue gives the exact shader and exact command lines.
