# Triage note - #3873

**Infinite loop related to struct inheritance and empty struct**

- URL: https://github.com/microsoft/DirectXShaderCompiler/issues/3873
- Batch: 002
- Repro quality: `complete`
- Status vs clean `main` Debug: `repros`
- History: `always-repro'd`
- Confidence: high
- Suggested action: `still-valid-keep-open`
- Godbolt: https://godbolt.org/z/6z6j7Ma36

## Summary

Empty-struct inheritance hangs the compiler. Release builds spin unbounded (still running at 300s); Debug builds trip an LLVM assert in ~2s on the same input. Reproduces v1.4.1907..v1.9.2607 at ps_6_0.

## Labels

- now: bug,crash
- proposed add: type-system
- proposed remove: -

## Runs

| Compiler | Exit | Timed out | Verdict |
| --- | --- | --- | --- |
| v1.5.2010 | 0x80004005 | no | no-repro |
| v1.6.2104 | 0x80004005 | no | no-repro |
| v1.6.2112 | 0x80004005 | no | no-repro |
| main-debug | 0xE0000001 | no | repro |
| v1.4.1907 | 0 | yes | repro |
| v1.9.2607 | 0 | yes | repro |

## Evidence

- `expected.md` - symptom pinned down before running anything
- `repro.hlsl` - exact source tested
- `cmd.txt` - exact command line
- `match.json` - symptom predicate, with its control documented
- `out-<compiler>.txt` - captured output per compiler
- `comment.md` - draft comment (NOT posted)
