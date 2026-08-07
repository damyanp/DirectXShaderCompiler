# #2918 — expected symptom

*Written before any compiler was run, from the issue text alone.*

## What the issue says

> Repro: Run the pix file mentioned in PIX bug 26308011. Attempt to recompile the shader in
> question with /Od. (Ask jeffnn/jeffno for details on how to do this)

and then an assert dump:

```
!dbg attachment points at wrong subprogram for function
!78 = !DISubprogram(name: "ClusterAirprobeVolumesCS", ... function: void ()* @ClusterAirprobeVolumesCS)
void ()* @ClusterAirprobeVolumesCS
  call void @llvm.dbg.declare(metadata [1 x float]* %126, metadata !964, metadata !604), !dbg !970
!970 = !DILocation(line: 96, column: 1, scope: !965)
!965 = distinct !DILexicalBlock(scope: !966, file: !79, line: 90, column: 3)
!109 = !DISubprogram(name: "CullAirprobeVolumes", linkageName: "\01?CullAirprobeVolumes@@...", ...)
Exception thrown at 0x00007FFE881C361C in WinPixEngineHost.exe: Microsoft C++ exception: std::exception
```

Title: *PIX: Numbering pass fails with /Od when subroutines are used.*

## Decomposition

The report names four conditions, all of which must hold together:

1. **A PIX pass** — the "numbering pass" — is run over an already-compiled DXIL module. This is
   not something a plain `dxc file.hlsl` command line does; PIX drives it through the
   optimizer/`IDxc*` API from `WinPixEngineHost.exe`.
2. **`/Od`**, i.e. optimisations disabled, so nothing is cleaned up before the pass runs.
3. **"Subroutines"** — user functions that survive as real `llvm::Function`s rather than being
   inlined into the entry point. `/Od` is what makes that likely.
4. **Debug information present** (`llvm.dbg.declare`, `!DISubprogram`, `!DILocation` all appear
   in the dump), so `-Zi` or equivalent.

The failure itself is the LLVM module verifier's
`!dbg attachment points at wrong subprogram for function` check: an instruction inside
function `A` carries a `!dbg` whose `DILocation` scope chain terminates at the `DISubprogram`
of a *different* function `B`. In the dump, code attributed to `CullAirprobeVolumes`
(line 90/96 — the `DISubprogram` at line 71) is sitting inside
`@ClusterAirprobeVolumesCS` (the `DISubprogram` at line 153) without being marked inlined.
The `std::exception` is the verifier failure being turned into an error by the caller.

## What "this reproduces" means

**Reproduces** = running the PIX numbering pass over a DXIL module built with `/Od` and debug
info, whose HLSL contains a non-inlined user function, causes an **internal failure** —
an assert, a trapped exception, a `report_fatal_error`, a structured exception, or a
verifier-driven `std::exception`/E_FAIL — instead of completing cleanly. Per `SKILL.md` this
is a crash-shaped symptom, so the predicate is `internal_failure` and **not** a text match on
the assert wording: the same defect wears different text and different exit codes across
builds and across the API vs. command-line entry points.

**Does not reproduce** = the same pipeline runs to completion and emits a module the verifier
accepts.

Explicitly *not* the symptom:
- an ordinary diagnosed error from the front end (E_FAIL + an `error:` line);
- a refusal by the tooling to run the pass at all (that is `invalid-probe` — it measured
  nothing);
- anything observed without the PIX pass in the pipeline. Plain `dxc /Od /Zi` compiling
  cleanly says nothing about this issue, because the pass that fails never ran.

## Repro quality, as filed

**`none`.** The issue supplies *no* shader, no command line and no DXIL — the repro is
"run the pix file mentioned in PIX bug 26308011" and "ask jeffnn/jeffno". That is an
**internal Microsoft bug number and a private customer shader**, and neither is available
here or publishable. Only the assert dump is public, and a dump is a symptom, not an input.

If a public repro can be constructed from the four conditions above it will be marked
`agent-constructed` and labelled as a reconstruction, never as the reporter's shader.

## Predicted difficulties (recorded before measuring)

- The PIX passes live in `lib/DxilPIXPasses/` and are not reachable from a plain
  `dxc file.hlsl` invocation, so the harness's `cmd.txt` (one dxc invocation per line) may not
  be able to express the repro at all.
- The reporter's stack is inside `WinPixEngineHost.exe`, i.e. the pass was driven through the
  API. Whatever drives it here will be a different harness than theirs, so a negative result
  is weaker evidence than a positive one.
- A 2020 report against an internal shader means the exact `/Od` + subroutine shape that
  triggered it is unknown; failing to reproduce does not establish the defect is fixed.
