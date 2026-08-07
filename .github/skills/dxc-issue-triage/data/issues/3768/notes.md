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

SPIR-V printf heap corruption. A captured repeated-run set observed
`STATUS_HEAP_CORRUPTION` (`0xC0000374`) in 33/40 v1.6.2104 runs and 28/40
v1.6.2106 runs. v1.5.2010 and v1.6.2112 were each clean in 30/30 runs, and every
later release probe through v1.9.2607 was clean. v1.4.1907 is unprobeable because
that binary has no SPIR-V codegen.

The failure is nondeterministic, so a single clean run does not rule it out.
v1.9.2607 was clean in 55/55 release-binary runs, split across `cs_6_0` (30) and
the originally reported `ps_6_0` (25). Current `main` Debug was also clean in
55/55, though that carries less weight because the reporter's local Debug build
also worked. Output inspected on `main` has the DebugPrintf import, six
`OpString`s, and six matching `OpExtInst` calls with the expected operands.

The report's retail-heap stack detected the bad free during
`Sema::BuildOverloadedCallExpr`, before SPIR-V legalization; that identifies the
detection point, not necessarily the original write. The report used
`-fcgl -Vd` to avoid the separate KhronosGroup/SPIRV-Tools#4219 crash, fixed by
KhronosGroup/SPIRV-Tools#4280 on 2021-05-13. The current command omits both flags
so legalization and validation run. In the captured affected-release matrix,
every one of the four flag combinations reproduced repeatedly, so the flags did
not suppress this crash. `cmd-as-filed.txt` preserves the original command.

Confidence is high because the first clean boundary release was 30/30 and the
latest release binary was 55/55 under the current command. The reporter's more
sensitive Application Verifier/page-heap check was not repeated because the
shell was not elevated, so latent corruption remains a limitation.

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
- `match.json` - symptom predicate and rationale
- `out-<compiler>.txt` - captured output per compiler
- `manual-case-repeat-measurements.txt` - every repeated attempt backing the quoted rates
- `external-spirv-tools-4219.json` - captured upstream issue and merged-fix metadata
- `method-notes.md` - parallel-batch tooling finding
- `comment.md` - draft comment (NOT posted)
