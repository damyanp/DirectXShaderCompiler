# Expected symptom (written before running anything)

Issue: dxc page-faults (access violation reading address 0x0) when a
**non-library** (ordinary compute-shader) compiled container is fed back into
the linker via `-link`.

Reporter's exact repro (as filed, dxc 1.7.2207.3):

```
Texture2D<uint> texResource : register(t900);
RWTexture2D<uint> rwTexResource[] : register(u0, space2400);
[numthreads(8, 8, 1)]
void main(uint3 dtid : SV_DispatchThreadID, uint3 gtid : SV_GroupThreadID, uint3 gid : SV_GroupID, uint gindex : SV_GroupIndex)
{
    rwTexResource[0][dtid.xy] = texResource.Load(dtid.xyz);
}
```

```
dxc.exe -T cs_6_3 -Fo test.bin test.hlsl
dxc.exe -link -T cs_6_3 -Fo test2.bin test.bin
```

Reported actual behavior: the second (`-link`) invocation crashes with
`Internal compiler error: access violation. Attempted to read from address
0x0000000000000000`.

Comment from the reporter (elasota, 2024-07-30) gives a root-cause theory:
a compute-shader module emits no resource global variables the way a
`lib_6_x` module does, so `DxilLinkJob::AddGlobals` never adds the CS's
resources to the link's resource list; later `GetResourcePropertyFromHandleCall`
(from `CollectShaderFlagsForModule`) indexes out of bounds into that resource
list because the CS module's DXIL still uses `createHandle` (not
`createHandleForLib`), and the OOB read null-derefs.

**"This reproduces" means:** running the two-step repro (compile a non-library
compute shader, then run `dxc -link -T cs_6_3 ...` against the resulting
container) crashes dxc with an internal failure (any internal-failure exit
status: access violation, LLVM assert, etc. -- the exact HRESULT/text may
differ by build per the skill's exit-code portability notes). "Does not
reproduce" means that second `-link` invocation completes (exit 0, or an
ordinary diagnosed error refusing the non-library input) with no internal
failure.

Repro quality: **complete** (reporter gave exact source, exact commands, exact
error).
