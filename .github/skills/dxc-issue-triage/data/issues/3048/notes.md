# Triage note - #3048

**Casting subclass to parent of three class heirarchy causes crashes**

- URL: https://github.com/microsoft/DirectXShaderCompiler/issues/3048
- Batch: 002
- Repro quality: `complete`
- Status vs clean `main` Debug: `repros`
- History: `always-repro'd`
- Confidence: high
- Suggested action: `still-valid-keep-open`
- Godbolt: https://godbolt.org/z/1o5Exs9YP

## Summary

Derived-to-base conversion crashes codegen (LLVM assert, 0xE0000001, in CGMSHLSLRuntime::ConvertAndStoreElements). Reproduces in all 20 releases v1.4.1907..v1.9.2607.

## Labels

- now: bug,crash,check-in-clang
- proposed add: type-system
- proposed remove: check-in-clang

## Runs

| Compiler | Exit | Timed out | Verdict |
| --- | --- | --- | --- |
| main-debug | 0xE0000001 | no | repro |
| v1.4.1907 | 0xC0000005 | no | repro |
| v1.5.2010 | 0xC0000005 | no | repro |
| v1.6.2104 | 0xC0000005 | no | repro |
| v1.6.2106 | 0xC0000005 | no | repro |
| v1.6.2112 | 0xC0000005 | no | repro |
| v1.7.2207 | 0xC0000005 | no | repro |
| v1.7.2212 | 0xC0000005 | no | repro |
| v1.7.2212.1 | 0xC0000005 | no | repro |
| v1.7.2308 | 0xC0000005 | no | repro |
| v1.8.2403 | 0xC0000005 | no | repro |
| v1.8.2403.1 | 0xC0000005 | no | repro |
| v1.8.2403.2 | 0xC0000005 | no | repro |
| v1.8.2405 | 0xC0000005 | no | repro |
| v1.8.2407 | 0xC0000005 | no | repro |
| v1.8.2502 | 0xC0000005 | no | repro |
| v1.8.2505 | 0xC0000005 | no | repro |
| v1.8.2505.1 | 0xC0000005 | no | repro |
| v1.9.2602 | 0xC0000005 | no | repro |
| v1.9.2602.24 | 0xC0000005 | no | repro |
| v1.9.2607 | 0xC0000005 | no | repro |

## Evidence

- `expected.md` - symptom pinned down before running anything
- `repro.hlsl` - exact source tested
- `cmd.txt` - exact command line
- `match.json` - symptom predicate, with its control documented
- `out-<compiler>.txt` - captured output per compiler
- `comment.md` - draft comment (NOT posted)
