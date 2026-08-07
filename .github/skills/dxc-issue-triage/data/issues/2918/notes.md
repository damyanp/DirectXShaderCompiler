# #2918 PIX: Numbering pass fails with /Od when subroutines are used

**Verdict: does not reproduce — fixed between v1.5.2010 and v1.6.2104, and the issue was never
closed.** Filed 2020-05-27. Measured on `main-debug`
(`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433)`, commit `ab5400907`) and on 16 cached
releases either side of the transition.

The repro named in the issue — a `.pix` capture behind internal bug 26308011, plus "ask
jeffnn/jeffno" — is a private customer shader and is not available here. It was not sought.
Everything below rests on a **reconstruction** built from the four conditions the report
states, and is labelled as such throughout.

## The failure, from the dump alone

The report quotes the LLVM module verifier:

```
!dbg attachment points at wrong subprogram for function
!78  = !DISubprogram(name: "ClusterAirprobeVolumesCS", ... function: void ()* @ClusterAirprobeVolumesCS)
  call void @llvm.dbg.declare(metadata [1 x float]* %126, metadata !964, metadata !604), !dbg !970
!970 = !DILocation(line: 96, column: 1, scope: !965)
!965 = distinct !DILexicalBlock(scope: !966, file: !79, line: 90, column: 3)
!109 = !DISubprogram(name: "CullAirprobeVolumes", ...)
```

An `llvm.dbg.declare` **inside `@ClusterAirprobeVolumesCS`** carries a `!dbg` whose scope chain
ends at the `DISubprogram` for a *different* function, `CullAirprobeVolumes`, with no
`inlinedAt:`. That is illegal, and `Verifier::visitDISubprogram` says so. Two details in the
dump identify who built that location: **`column: 1`**, which no front end emits for a
declaration, and the **absence of `inlinedAt:`**.

## How the PIX passes are driven (no previous batch had done this)

They are DXIL module passes in `lib/DxilPIXPasses/`, registered in `lib/HLSL/DxcOptimizer.cpp`
and reachable only through `IDxcOptimizer::RunOptimizer` over an **already-compiled** module.
A plain `dxc file.hlsl` never runs them; `-opt-enable` / `-opt-disable` / `/Odump` do not reach
them either. Three things can drive them:

| driver | what it is |
| --- | --- |
| `IDxcOptimizer::RunOptimizer` | what PIX itself uses — `WinPixEngineHost.exe` in the report |
| `dxopt.exe` | the command-line front end for exactly that interface (built by this repo) |
| `opt.exe` | this repo's LLVM `opt`, which also has the passes registered |

The "numbering pass" of the title is `-dxil-annotate-with-virtual-regs`
(`DxilAnnotateWithVirtualRegister`). PIX runs it after `-dxil-dbg-value-to-dbg-declare`; that
pairing is what the in-tree tests use
(`tools/clang/unittests/HLSL/PixTestUtils.cpp` `RunAnnotationPasses`,
`tools/clang/test/HLSLFileCheck/pix/*.hlsl`), and it is the pairing used here:

```
stage 1: dxc  -T cs_6_0 -E main -Od -Zi -Qembed_debug repro.hlsl        > module.ll
stage 2: dxopt module.ll -opt-mod-passes -dxil-dbg-value-to-dbg-declare -dxil-annotate-with-virtual-regs
```

Stage 1 **must** produce disassembly text. A container written with `-Fo` carries a stripped
DXIL part, so `dxopt` on it sees no debug info and the defect is unreachable — a silent
false negative.

`lib/HLSL/DxcOptimizer.cpp:555` appends `createVerifierPass()` to every module pass pipeline,
and `lib/Support/ErrorHandling.cpp:117` turns the resulting `report_fatal_error` into a thrown
`hlsl::Exception`. That is the `Microsoft C++ exception: std::exception` in the report: the
verifier failing inside `RunOptimizer`.

## How this was measured (a human can repeat it)

`run-pix-passes.py`, committed beside this file:

```
cd data/issues/2918
python run-pix-passes.py              # ground truth only
python run-pix-passes.py --history    # every cached release
```

Paths come from `DXC` / `DXOPT` / `OPT` / `DXC_TRIAGE_CACHE` with repo-relative fallbacks.
Captured output: `manual-case-history.txt`. Source evidence: `manual-case-source-evidence.txt`.

**Releases ship no `dxopt.exe`** — only `dxc.exe`, `dxcompiler.dll`, `dxil.dll`. Each release
is therefore driven by copying *this repo's* `dxopt.exe` next to *that release's*
`dxcompiler.dll`. `dxopt` uses nothing but `DxcCreateInstance` and `IDxcOptimizer`, so the
pairing is sound in principle — but "in principle" is not evidence, which is what the controls
below are for.

### Harness controls (declared in `expected.md` before anything ran)

Per build, three runs, not one:

| run | input | required |
| --- | --- | --- |
| **baseline** | that build's own module, **no passes** | must **succeed** — proves the module went in verifier-clean, so a failure is the pass's doing |
| **control** | same module, `inlinedAt:` deleted from one lexical-block-scoped `!DILocation`, **no passes** | must **fail** — proves this build still performs the wrong-subprogram check and that the mixed dxopt/dxcompiler pairing propagates a failure |
| **PIX passes** | same module, both passes | the measurement |

Both controls held on every build probed. Without them, "v1.9 does not fail" is
indistinguishable from "the old DLL never ran the check" or "this pairing cannot report
failure".

## Result 1 — the reconstruction does reproduce, on the right releases

`repro.hlsl` is a compute shader with one local array inside a helper function
(`float CullValues(float3 v)` holding `float accum[1]`), called from `main`, built `-Od -Zi`.
It is **agent-constructed**; it is not the reporter's shader and cannot be.

| build | baseline | control | PIX passes | |
| --- | --- | --- | --- | --- |
| v1.4.1907 | — | — | — | **invalid-probe** — no `dxil-dbg-value-to-dbg-declare` in this build |
| **v1.5.2010** | 0 | fails | **exit 1, `0x80004005`** | **repro** |
| **v1.6.2104** | 0 | fails | 0, `InstructionCount:67` | **no-repro** |
| v1.6.2106 … v1.9.2607 (13 releases) | 0 | fails | 0 | no-repro |
| main-debug | 0 | fails | 0, `InstructionRange: 0 56 main cs` | no-repro |

Running only `-dxil-annotate-with-virtual-regs` on v1.5.2010 succeeds, so the failure is in
`-dxil-dbg-value-to-dbg-declare` — the pass the *title* does not name.

`dxopt` reports the failure as `Operation failed - error code 0x80004005.` and prints nothing
else: it discards `RunOptimizer`'s text blob on the failure path, so the verifier's message is
invisible through that route even in a Debug build. The message text in
`manual-case-history.txt` therefore comes from this repo's `opt.exe -verify` on the *control*,
and is labelled as such — the pass/fail decision is always the release's own `dxopt` run.

Four releases were not probed because they were absent from the shared cache
(v1.6.2112, v1.7.2308, v1.8.2502, v1.8.2505.1). All four postdate the transition, which is
bracketed by two releases that *were* probed.

## Result 2 — the fix, and it is the reported failure

`manual-case-source-evidence.txt`. 268 commits sit in `v1.5.2010..v1.6.2104`; three touch
`lib/DxilPIXPasses/DxilDbgValueToDbgDeclare.cpp`, and one changes the debug location:

**`ac5630e8e` — "Fixes for adding -Od (#3292)", Jeff Noyle, 2020-12-03.**

> A customer couldn't recompile their large shader with -Od for debugging in PIX.
> -The symbol manager would quit early, so now it continues to discover other variables
> -**The value-to-declare pass was adding an incorrect debug location, which tripped up the verifier.**

```diff
-  DbgDeclare->setDebugLoc(GetVariableLocation());
+  DbgDeclare->setDebugLoc(m_dbgLoc);
```

and the helper it removed:

```cpp
llvm::DILocation *VariableRegisters::GetVariableLocation() const {
  const unsigned DefaultColumn = 1;
  return llvm::DILocation::get(m_B.getContext(), m_Variable->getLine(),
                               DefaultColumn, m_Variable->getScope());
}
```

That is the four-argument `DILocation::get` — **`InlinedAt` is null** — and the column is a
hard-coded `1`. It produced precisely the metadata the issue quotes:
`!DILocation(line: 96, column: 1, scope: <lexical block in the callee>)`, attached to a
`llvm.dbg.declare` the pass had just synthesised in the *entry* function. The helper now sits
`#if 0`'d as "unused" at `DxilDbgValueToDbgDeclare.cpp:1331-1342`; the call site uses the
originating instruction's own `DebugLoc`, which carries a correct `inlinedAt:`.

Same author as the "ask jeffnn/jeffno" in the issue body, same `-Od`-in-PIX scenario, six
months after the report.

**Strength: strong, not certain.** The behaviour change was measured on release binaries either
side of the window; `ac5630e8e` was not built in isolation. This is source reasoning that
narrows a 268-commit window to one commit whose message independently describes the same
failure — not a bisect.

## Against `expected.md`

The pre-committed predicate was `internal_failure` — "an assert, a trapped exception, a
`report_fatal_error`, a structured exception, or a verifier-driven `std::exception`/E_FAIL —
instead of completing cleanly" — deliberately *not* a text match on the assert wording. That
is what was measured, and it is what made the result readable: the observed shape on v1.5.2010
is an `E_FAIL` from `dxopt` with no message at all, which a text predicate would have scored
as no-repro. `expected.md` also fixed repro quality as filed at `none` and ruled out reading
anything into a plain `dxc /Od /Zi` run, which stays clean on every release.

The third predicted difficulty — "failing to reproduce does not establish the defect is fixed"
— is the one that would have limited this triage, and it is answered not by the negative
result but by Result 2: the constructed repro *positively* reproduces on the last release
before the fix, and the fix is identified in source.

## Assessment

Fixed six months after it was filed, by the person the issue tells you to ask. It has been
open for five and a half years since, was moved to dormant in 2024, and the maintainer comment
already invites closing it:

> @jeffnn - moved this to dormant (ie we're not planning to schedule anyone to work on it).
> If you happen to know that this is no longer relevant please feel free to close it.

The residual risk is honest and small: the reporter's shader was large and real, and a
reconstruction cannot prove *their* module is clean today — only that the mechanism the dump
shows was removed. If a maintainer wants certainty rather than a strong inference, the ask is
narrow and stated in `comment.md`: re-run the same `.pix` capture against any DXC ≥ 1.6.2104,
or attach the failing DXIL module text (not the shader source) with the offending `!DILocation`
in it. Neither requires the private shader to leave Microsoft.

Recommended action: **close as fixed**.
