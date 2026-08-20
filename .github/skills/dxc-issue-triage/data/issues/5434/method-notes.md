# Method notes — issue 5434

Batch-scoped observation, not promoted to `SKILL.md` by this single-issue session (per the
skill: a per-issue worker records observations here; only collation promotes).

## `dxv.exe` can be pointed at a different `dxcompiler.dll` without a rebuild

This batch's shared ground-truth build only produced `dxc.exe` (matching the batch
instruction not to rebuild the shared build tree). `dxv.exe` — the standalone validator
CLI, needed here because the defect can only be exercised with hand-constructed DXIL that
no HLSL compile can produce — was never built for `main-debug`.

`tools/clang/tools/dxv/dxv.cpp` loads its validator through `DxcCreateInstance` against
whichever `dxcompiler.dll` sits beside the `.exe` at run time (delay-loaded). So copying
an already-downloaded release's `dxv.exe` + `dxil.dll` into a scratch directory, then
copying `main-debug`'s own already-built `dxcompiler.dll` in beside them, runs
ground-truth's validator through an unmodified, already-existing host binary — no
`cmake`/`msbuild` invocation, no touch to the registered `main-debug` `dxc.exe`. This is
the same idea `SKILL.md` already documents for `dxopt -external -external-fn
DxcCreateInstance`, just applied to `dxv` instead of `dxopt`.

**Proved, not assumed, that the swap takes effect**: with `dxcompiler.dll` renamed out of
the scratch directory, `dxv.exe` fails immediately with `0x8007007E`
(`ERROR_MOD_NOT_FOUND`) rather than silently falling back to a system copy or a
statically-linked validator (`manual-case-dll-swap-proof.txt`). And a Debug (main-debug)
`dxcompiler.dll` paired with a Release `dxv.exe`/`dxil.dll` from a different build
(different CRT, different toolchain) ran without incident across every probe in this
issue — worth noting as a fact for the next `Annotate*Handle`-adjacent issue, since it
was not obvious in advance that mixing configs this way would work.

This generalises beyond this one issue: any future issue whose symptom lives in the
validator, and where the only DXC binary built for ground truth is `dxc.exe`, can reuse
this pattern instead of registering a whole harness-as-compiler or rebuilding `dxv`.

## A "does not exist" test on the checked opcodes still needs its own control

`validate_undef_arg.ll` already exists in-tree and is the ideal positive control for "the
general handle-uninitialized check still fires" — but it does **not** cover
`AnnotateHandle`/`AnnotateNodeHandle`/`AnnotateNodeRecordHandle` at all (its own comment
only claims to test "various dxil ops that take in one of three handle types", not these
three specifically). Confirming the absence finding still needed a same-shape, dedicated
negative probe (`variant-annotatehandle-zero.ll`, `variant-annotatenodehandles-zero.ll`)
plus its own positive control (`control-bufferupdatecounter-zero.ll`, the identical zero/
undef `%dx.types.Handle` value fed to a checked opcode) — reusing an existing test file
as *background* corroboration is not a substitute for a dedicated control when the
existing test's own scope statement doesn't cover the opcode in question.
