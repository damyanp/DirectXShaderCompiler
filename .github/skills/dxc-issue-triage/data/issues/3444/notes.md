# Triage note - #3444

**[DXIL] Decorating CS float argument with SV_DispatchThreadID semantic crashes the compiler (float2, float3 and float4 works)**

- URL: https://github.com/microsoft/DirectXShaderCompiler/issues/3444
- Batch: 002
- Repro quality: `complete`
- Status vs clean `main` Debug: `repros`
- History: `always-repro'd`
- Confidence: high
- Suggested action: `still-valid-keep-open`
- Godbolt: https://godbolt.org/z/d6jG8Yjrr

## Summary

Float-typed SV_DispatchThreadID hits a bad llvm::cast. Never fixed in any release; severity softened from silent access violation (v1.4-v1.6.2104) to a caught internal error, but the leaked cast<X>() text is still not a real diagnostic. Issue title is REFUTED: float, float2, float3 and float4 all fail identically; uint3 control compiles clean.

## Labels

- now: bug,tech-debt,diagnostic
- proposed add: crash, fxc-disagrees
- proposed remove: -

## Runs

| Compiler | Exit | Timed out | Verdict |
| --- | --- | --- | --- |
| main-debug | 0x80000003 | no | repro |
| v1.4.1907 | 0xC0000005 | no | repro |
| v1.5.2010 | 0xC0000005 | no | repro |
| v1.6.2104 | 0xC0000005 | no | repro |
| v1.6.2106 | 0x80AA001D | no | repro |
| v1.6.2112 | 0x80AA001D | no | repro |
| v1.7.2207 | 0x80004005 | no | repro |
| v1.7.2212 | 0x80004005 | no | repro |
| v1.7.2212.1 | 0x80004005 | no | repro |
| v1.7.2308 | 0x80004005 | no | repro |
| v1.8.2403 | 0x80004005 | no | repro |
| v1.8.2403.1 | 0x80004005 | no | repro |
| v1.8.2403.2 | 0x80004005 | no | repro |
| v1.8.2405 | 0x80004005 | no | repro |
| v1.8.2407 | 0x80004005 | no | repro |
| v1.8.2502 | 0x80004005 | no | repro |
| v1.8.2505 | 0x80004005 | no | repro |
| v1.8.2505.1 | 0x80004005 | no | repro |
| v1.9.2602 | 0x80004005 | no | repro |
| v1.9.2602.24 | 0x80004005 | no | repro |
| v1.9.2607 | 0x80004005 | no | repro |

## Evidence

- `expected.md` - symptom pinned down before running anything
- `repro.hlsl` - exact source tested
- `cmd.txt` - exact command line
- `match.json` - symptom predicate, with its control documented
- `out-<compiler>.txt` - captured output per compiler
- `comment.md` - draft comment (NOT posted)
