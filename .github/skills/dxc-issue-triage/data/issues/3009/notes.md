# Triage note - #3009

**dxc silently passes uninitialized value as undef**

- URL: https://github.com/microsoft/DirectXShaderCompiler/issues/3009
- Batch: 002
- Repro quality: `complete`
- Status vs clean `main` Debug: `repros`
- History: `always-repro'd`
- Confidence: high
- Suggested action: `still-valid-keep-open`
- Godbolt: https://godbolt.org/z/5bdo83bTY

## Summary

Uninitialized local silently reaches arithmetic: dxc exits 0, emits 'i32 undef' as an IMad operand, no diagnostic. Reproduces in all 20 releases v1.4.1907..v1.9.2607. Maintainer's SV_Position variant behaves the same with float undef into FMad.

## Labels

- now: bug,validation
- proposed add: diagnostic, fxc-disagrees, check-in-clang
- proposed remove: -

## Runs

| Compiler | Exit | Timed out | Verdict |
| --- | --- | --- | --- |
| main-debug | 0 | no | repro |
| v1.4.1907 | 0 | no | repro |
| v1.5.2010 | 0 | no | repro |
| v1.6.2104 | 0 | no | repro |
| v1.6.2106 | 0 | no | repro |
| v1.6.2112 | 0 | no | repro |
| v1.7.2207 | 0 | no | repro |
| v1.7.2212 | 0 | no | repro |
| v1.7.2212.1 | 0 | no | repro |
| v1.7.2308 | 0 | no | repro |
| v1.8.2403 | 0 | no | repro |
| v1.8.2403.1 | 0 | no | repro |
| v1.8.2403.2 | 0 | no | repro |
| v1.8.2405 | 0 | no | repro |
| v1.8.2407 | 0 | no | repro |
| v1.8.2502 | 0 | no | repro |
| v1.8.2505 | 0 | no | repro |
| v1.8.2505.1 | 0 | no | repro |
| v1.9.2602 | 0 | no | repro |
| v1.9.2602.24 | 0 | no | repro |
| v1.9.2607 | 0 | no | repro |

## Evidence

- `expected.md` - symptom pinned down before running anything
- `repro.hlsl` - exact source tested
- `cmd.txt` - exact command line
- `match.json` - symptom predicate, with its control documented
- `out-<compiler>.txt` - captured output per compiler
- `comment.md` - draft comment (NOT posted)
