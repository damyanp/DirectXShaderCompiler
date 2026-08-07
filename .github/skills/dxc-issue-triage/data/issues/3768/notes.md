# Triage note - #3768

**[SPIR-V] crash compiling shader using printf**

- URL: https://github.com/microsoft/DirectXShaderCompiler/issues/3768
- Batch: 002
- Repro quality: `complete`
- Status vs clean `main` Debug: `does-not-repro`
- History: `regressed-in v1.6.2104; fixed-in v1.6.2112`
- Confidence: high
- Suggested action: `close-fixed`
- Godbolt: https://godbolt.org/z/e5KT1E6W9

## Summary

SPIR-V printf heap corruption. Crash (STATUS_HEAP_CORRUPTION 0xC0000374) confined to v1.6.2104
and v1.6.2106; clean from v1.6.2112 through v1.9.2607. v1.4.1907 is unprobeable (no SPIR-V).

**Nondeterministic**: measured 68-82% of runs in the affected releases. Single-run probes are
therefore unsound - a live `--repeat 10` probe of v1.6.2106 needed 4 attempts before the crash
appeared. Current builds clean over 110 runs (55 on `main` Debug, 55 on the v1.9.2607 release
binary; both ps_6_0 as reported and cs_6_0). Output inspected on `main`: DebugPrintf import,
six OpStrings, six matching OpExtInst calls.

**Not a SPIR-V-lowering bug.** The reported stack is BumpPtrAllocator slab teardown under
Sema::BuildOverloadedCallExpr - the front end. The `-fcgl -Vd` in the original report was
avoiding an unrelated spirv-tools crash (KhronosGroup/SPIRV-Tools#4219, fixed by #4280, merged
2021-05-13, the day after this was filed). Those flags were dropped from cmd.txt; all four flag
combinations crash at similar rates at v1.6.2104/v1.6.2106, so they were not masking this.
Original preserved as cmd-as-filed.txt.

Confidence raised medium -> high once the per-run failure rate was measured: against a ~70%
rate, 55 consecutive clean release-binary runs is a real result. Residual risk is only latent
corruption visible under page heap, which needs elevation and was not run.

## Labels

- now: spirv
- proposed add: -
- proposed remove: -

## Runs

| Compiler | Exit | Timed out | Verdict |
| --- | --- | --- | --- |
| main-debug | 0 | no | no-repro |
| v1.4.1907 | 0x00000001 | no | invalid-probe |
| v1.5.2010 | 0 | no | no-repro |
| v1.6.2104 | 0xC0000374 | no | repro |
| v1.6.2106 | 0xC0000374 | no | repro |
| v1.6.2112 | 0 | no | no-repro |
| v1.7.2207 | 0 | no | no-repro |
| v1.7.2212 | 0 | no | no-repro |
| v1.7.2212.1 | 0 | no | no-repro |
| v1.7.2308 | 0 | no | no-repro |
| v1.8.2403 | 0 | no | no-repro |
| v1.8.2403.1 | 0 | no | no-repro |
| v1.8.2403.2 | 0 | no | no-repro |
| v1.8.2405 | 0 | no | no-repro |
| v1.8.2407 | 0 | no | no-repro |
| v1.8.2502 | 0 | no | no-repro |
| v1.8.2505 | 0 | no | no-repro |
| v1.8.2505.1 | 0 | no | no-repro |
| v1.9.2602 | 0 | no | no-repro |
| v1.9.2602.24 | 0 | no | no-repro |
| v1.9.2607 | 0 | no | no-repro |

## Evidence

- `expected.md` - symptom pinned down before running anything
- `repro.hlsl` - exact source tested
- `cmd.txt` - exact command line
- `match.json` - symptom predicate, with its control documented
- `out-<compiler>.txt` - captured output per compiler
- `comment.md` - draft comment (NOT posted)

