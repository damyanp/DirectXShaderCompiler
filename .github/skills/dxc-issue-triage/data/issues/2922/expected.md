# #2922 — what "this reproduces" means

Written before running anything.

## The report

Title: *" value-to-declare pass not handling pointer case under -O1"* (filed 2020-05-27 by
`jeffnn`, a DXC/PIX maintainer).

Body, in full:

> Repro: e.g., open PixTest.cpp, find the "Compile" function and change the -Od to -O1, then
> run the taef tests with `/name:PixTest::PixStructAnnotation_*`

One comment, 2024-06-27, from `damyanp`: *"@jeffnn - is this something we still need to
track?"* — never answered.

So the repro is **not a `dxc` command line**. It is: recompile the PIX unit tests' shaders at
`-O1` instead of `-Od`, and run the `PixStructAnnotation_*` TAEF cases.

## What the "pointer case" is

`value-to-declare` is the PIX pass `-dxil-dbg-value-to-dbg-declare`
(`lib/DxilPIXPasses/DxilDbgValueToDbgDeclare.cpp`). It rewrites `llvm.dbg.value` records into
`llvm.dbg.declare` plus stores into synthetic allocas, so that PIX's shader debugger can show
local variables.

At `-Od` the `llvm.dbg.value` operands are scalars. At `-O1` some of them are **pointers**
(the `mem2reg`/`sroa`-shaped debug info hands the pass an address rather than a value). The
issue says the pass does not handle that.

## The predicate: what I must observe for "repros"

Reproduces if **either** of these holds against ground truth:

1. **Test-level.** `PixTest::PixStructAnnotation_*`, run against `-O1`-compiled shaders, fail.
2. **Pass-level.** Given `-O1` debug IR that contains a pointer-typed `llvm.dbg.value`, the
   value-to-declare pass drops the variable — it emits no `dbg.declare`/alloca stores for it —
   where at `-Od` it emits them.

Does **not** reproduce if the `PixStructAnnotation_*` cases pass at `-O1`, **and** the pass
converts pointer-typed `llvm.dbg.value`s rather than bailing out on them.

Anything crash-shaped (assert, access violation, `llvm_unreachable`) in the pass under `-O1`
also counts as reproducing, and is a distinct enough signature to deserve its own predicate.

## Traps I expect

* **The repro instruction has decayed.** `PixTest.cpp`'s `Compile` no longer hardcodes `-Od`,
  so "change the -Od to -O1" cannot be followed literally. Whatever the current file does, I
  must say what I actually ran.
* **A green test run is weaker evidence than it looks.** If the tests were updated at the same
  time as a fix, "the tests pass" only says current behaviour matches current expectations. I
  need the pass-level observation (2) as well, not just (1).
* **`dxc.exe` cannot run this pass.** Release packages ship only `dxc.exe`, `dxcompiler.dll`
  and `dxil.dll` — no `opt.exe`/`dxopt.exe`. So `cmd.txt` can only cover the *compile* half,
  and any release history has to be measured by driving `dxcompiler.dll`'s `IDxcOptimizer`
  directly. `bisect` over `cmd.txt` alone would measure the wrong thing; if I run it, its
  result must not be read as symptom history.
* **`-O1` may not even produce a pointer-typed `dbg.value` today.** If it does not, the
  pointer path is unreachable from this repro and I must say so rather than claim "handled".

## Repro quality

`prose-only` as filed: the issue supplies an instruction to edit a test file, not code. The
shaders themselves exist in-tree (`tools/clang/unittests/HLSL/PixTest.cpp`), so anything I run
standalone is `agent-constructed` from them.
