# #4501 — what "this reproduces" means

Issue: [#4501](https://github.com/microsoft/DirectXShaderCompiler/issues/4501),
"[SPIR-V] Debug info should use DebugBuildIdentifier and DebugStoragePath with -Fd flag",
filed 2022-06-03 by `baldurk`. Label: `spirv`. Milestone: `Dormant`.

Written **before** any compiler run on the repro.

## What the issue asks for

The `NonSemantic.Shader.DebugInfo.100` debug information DXC emits for SPIR-V should use two
extended instructions so that split (non-embedded) debug info works the way the DXIL path's
`-Fd` already does:

* **Ask A — `DebugBuildIdentifier`**: the *stripped* output module should carry a hash
  identifier for the matching unstripped debug module, plus a flags operand
  (`IdentifierPossibleDuplicates`, corresponding to `-Zsb` semantics on the DXIL path).
* **Ask B — `DebugStoragePath`**: the module should optionally carry the directory path where
  the unstripped debug module was written, so a tool can find it later. Separate from A so the
  debug file can be relocated.
* **Precondition P — `-Fd` with `-spirv`**: the whole request is phrased "with `-Fd` flag", so
  it presupposes that the SPIR-V backend can be asked to write a separate debug module to a
  directory at all, and that `-Fo` then receives a stripped module.

This is a **feature request**, not a defect report: nothing in the text claims DXC ever emitted
these instructions, and there is no reported miscompile, crash or wrong output. The one comment
(kuhar, 2022-06-03) only routes it: "This is assigned to @greg-lunarg."

## Repro quality

**prose-only** in the issue — no shader, no command line, no output. Any repro here is
**agent-constructed** and must be labelled as such.

## The symptom, stated so it can be scored

"Still reproduces" = *the requested capability is still absent*:

1. A shader compiled with `-spirv` and the richest debug-info mode DXC offers
   (`-fspv-debug=vulkan-with-source`, i.e. the `NonSemantic.Shader.DebugInfo.100` instruction
   set) produces a module that **contains no `DebugBuildIdentifier` and no `DebugStoragePath`
   extended instruction**, and
2. that same module **does** contain the `NonSemantic.Shader.DebugInfo.100` import and real
   NonSemantic debug instructions — i.e. the compile succeeded and rich debug info really was
   generated. Without clause 2 the finding is worthless.

"Does not reproduce" = either instruction appears in the emitted module under some documented
flag combination, or `-Fd` produces a usable split debug module for SPIR-V.

## This is an ABSENCE claim — the traps it carries

An absence predicate is satisfied for free by *any* run that failed to produce SPIR-V. Named
hazards for this issue specifically, all of which must be closed before a verdict:

* **`-Fd` itself is a candidate false positive.** If `-spirv -Fd <dir>` is rejected, that run
  emits no SPIR-V, therefore no `DebugBuildIdentifier`, and an unanchored predicate scores it
  as a textbook reproduction while measuring nothing. The predicate must require positive
  evidence of a successful SPIR-V debug-info compile (clause 2).
* **Old releases predating SPIR-V codegen.** v1.4.1907 and v1.5.2003 answer
  `SPIR-V CodeGen not available` (v1.5.2003 is a prerelease and out of scope anyway). These are
  `invalid-probe`, not clean results, so the SPIR-V floor is above the usual v1.4.1907. Any
  "always" claim must be phrased "for as long as it is possible to check".
* **Old releases predating `-fspv-debug=vulkan-with-source`.** The `vulkan*` values select the
  NonSemantic.Shader.DebugInfo.100 set; releases that do not accept that spelling cannot answer
  the question at all, and a clean-looking result from them is not evidence.
* **Source echo.** With `vulkan-with-source`, the shader text is embedded in the module
  (`OpString`/`DebugSource`). The repro must therefore **not** contain the literal strings
  `DebugBuildIdentifier` or `DebugStoragePath` anywhere, or the absence clauses become
  unfalsifiable. The mirror of that is the control: a shader that *does* contain those tokens
  in a comment must make the absence clauses fail, proving they can fail at all.

## Controls planned

| control | expectation | what it proves |
| --- | --- | --- |
| a shader whose comment contains both opcode names, same flags | predicate must **not** match | the absence clauses can be falsified — they are not dead regexes |
| `-spirv` with no debug flags | predicate must **not** match | clause 2 is load-bearing: no NonSemantic debug info means the probe cannot answer the question |
| `-spirv -Fd <dir>` | predicate must **not** match | the exact false-positive above is closed: a rejected `-Fd` run scores no-match, not "repro" |

## Prediction (recorded so it can be wrong)

Source reading done before running anything: `git grep DebugBuildIdentifier` and
`git grep DebugStoragePath` over the whole DXC tree return **nothing**, while
`DebugSourceContinued` (102), `DebugFunctionDefinition` (101) and `DebugEntryPoint` (107) are
all implemented in `tools/clang/lib/SPIRV/`. So I expect both instructions to be absent on
ground truth and on every probeable release, i.e. `never-implemented` rather than a regression.
I also expect `-Fd` to be rejected outright, because
`hasUnsupportedSpirvOption()` in `lib/DxcSupport/HLSLOptions.cpp` lists `OPT_Fd`.

If the runs disagree with any of that, the runs win.
