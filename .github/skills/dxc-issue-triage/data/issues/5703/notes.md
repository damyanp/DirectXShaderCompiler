# #5703 -- RDAT part is missing when linking a compute shader

Issue: https://github.com/microsoft/DirectXShaderCompiler/issues/5703
Filed: 2023-09-13, by EricLasotaRSE. No comments. Labels at fetch time:
`bug`, `reflection`, `shader-linking`.

## What was tested

Ground truth: `main-debug` (Debug `<repo>/build/Debug/bin/dxc.exe`), which
self-reports commit `7665270b9`. That commit is verified tree-identical to
the recorded upstream `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (the
build's own commit is an ancestor of it; `git diff --name-only
89e2f98e2 7665270b9` touches nothing outside `.github/skills/`).

The reported symptom needs three tool stages `triage.py run` cannot express
as one `cmd.txt` line -- compile a library, link it to a concrete profile,
then read the *linked* container's part table. Per SKILL.md ("When the
symptom is in a pass dxc.exe cannot run, register the harness as a
compiler"), `link5703.py` is registered as compiler `main-debug-link5703`
(`run-link5703.cmd` wraps it). It runs:

  1. `dxc.exe -T lib_6_3 -Fo lib.dxo repro.hlsl` (a library compile),
  2. `dxl.exe -T cs_6_3 -E main -Fo linked.dxo lib.dxo` (link to a compute
     shader, matching the issue's `IDxcLinker::Link(L"main", L"cs_6_3",
     ...)` call),
  3. its own container-part reader (parses `DxilContainerHeader` /
     `DxilPartHeader` directly per
     `include/dxc/DxilContainer/DxilContainer.h`, not through `dxa` or
     `IDxcContainerReflection`) over both the intermediate library
     container and the final linked container.

`dxl.exe` is not built in the local Debug tree, and no cached stable
release ships one either (established for #4168). `dxc.exe`/`dxl.exe` are
therefore taken from the local **Release** build instead
(`<repo>/build/Release/bin`), which both self-report `dxcompiler.dll:
1.10(5440-677a02a1)(1.9.0.15438) - 1.9.0.15438 (main, 89e2f98e2)` --
an *exact* match to the recorded ground-truth commit, not merely a
tree-equivalent one. This is not an assert/crash issue, so a Release build
does not weaken the measurement the way it would for a Debug-only assert.

## Result

Primary capture (`out-main-debug-link5703.txt`, `--O3`, matching the
issue's own `-O3` flags on both compile and link):

- unlinked library container: `SFI0, VERS, RDAT(232), STAT, HASH, DXIL` --
  RDAT present (this is the harness's own anti-vacuity self-test, folded
  into `match.json` as a required clause: it proves the compiler/reader
  pair being used can produce and detect an RDAT part in the same run).
- linked (`cs_6_3`, finalized) container: `SFI0, ISG1, OSG1, PSV0(132),
  STAT, ILDN, HASH, DXIL` -- **no RDAT part**, `PSV0` present instead.

This reproduces the reported symptom exactly.

## Why: RDAT is a library-only container part, by source-level design

`lib/DxilContainer/DxilContainerAssembler.cpp` (~line 1990-2020) writes
the container's reflection-adjacent parts in one of two mutually
exclusive branches, keyed on `pModule->GetShaderModel()->IsLib()`:

- **library** (`IsLib() == true`): writes `VERS` (compiler version) and
  `RDAT` (`DxilRDATWriter`) -- no `PSV0` in this branch at all.
- **non-library / finalized shader** (`IsLib() == false`): writes `PSV0`
  (`DxilPSVWriter`, `DxilPipelineStateValidation`) -- no `RDAT`, ever, in
  this branch.

`IDxcLinker::Link(entry, targetProfile, ...)` with a concrete profile
(`cs_6_3`, not a `lib_6_x` profile) produces exactly the second kind of
container: a finalized, non-library shader module. There is no code path
in the assembler that can attach `RDAT` to that container's part table --
the two are mutually exclusive by construction, not merely omitted for
this input.

## Control: this is not linker-specific -- it is inherent to any non-library container

`variant-control-direct-compile-main-debug-link5703.txt` compiles the
*same* source **directly** to `cs_6_3` with no library step and no linker
involved at all (`dxc.exe -T cs_6_3 -E main -Fo direct.dxo repro.hlsl`):
`direct-RDAT: MISSING`, with the identical `PSV0`-bearing part set as the
linked container. This isolates the cause to "the container is a
finalized, non-library shader" rather than to anything specific about
`IDxcLinker`/`dxl.exe` -- a directly-compiled `cs_6_3` shader that was
never linked at all has exactly the same part table shape.

## Control: relinking to a library profile keeps RDAT (proves the harness/reader, not just the source, is sound)

`variant-control-relink-as-lib-main-debug-link5703.txt` links the same
library to `lib_6_3` instead of `cs_6_3` (`--expect no-match`, confirmed):
the resulting (still-a-library) container keeps its `RDAT` part. This is
the positive control the "absence" finding needs (SKILL.md: "make the
instrument prove it can detect a presence... put that self-test in
match.json" / here, exercised as a labelled variant): the reader correctly
reports `RDAT` present whenever the container is still a library, and
absent only once it is finalized to a concrete shader profile -- so the
absence is a property of the container kind, not a reader defect.

## Corroboration across time: the reporter's own build shows the same shape

`manual-case-release-1.7.2308.txt` repeats the same two-stage measurement
against the exact build named in the issue (`dxcompiler.dll: 1.7 -
1.7.2308.7 (69e54e290)`, catalogued locally as release `v1.7.2308`, dated
2023-08-14 -- the closest stable release to the issue's 2023-09-13 filing
date). No stable release ships `dxl.exe`; per #4168's established
equivalence, `dxl` is run as `dxc.exe <args> -link`
(`tools/clang/tools/dxl/dxl.cpp` literally appends `-link` to argv and
calls `dxc::main`). Result: identical shape -- `RDAT` present in the
unlinked library, `PSV0` present and `RDAT` absent in the linked
container. This is the reporter's own compiler reproducing its own
reported "actual behavior" precisely, which is strong evidence that
nothing about this has changed since the report: it is not a regression,
and there is no fix to look for or historical boundary to bisect.

A full stable-release bisection was not run: the finding is a mutually
exclusive branch in the container assembler keyed on a single boolean
(`IsLib()`), not an implementation detail likely to have drifted
release-to-release, and it is corroborated at both ends of the interval
that matters (the reporter's own 2023 build, and the current `main`
ground truth). Given the source-level mechanism and the double
corroboration, a 20-release sweep was judged to add cost without adding
confidence for what is, on this evidence, a design property rather than a
regression search.

## Corroboration that reflection itself is not actually lost: `ID3D12ShaderReflection` on the linked container

`manual-case-dxa-reflection.txt` runs `dxa.exe -dumpreflection` (which
drives `ID3D12ShaderReflection`, the ordinary non-library reflection
interface, distinct from `ID3D12LibraryReflection` which is what RDAT
feeds) over the same linked container. It resolves both bound resources
correctly: `texResource` (`D3D_SIT_TEXTURE`, `t900`/space0) and
`rwTexResource` (`D3D_SIT_UAV_RWTYPED`, `u0`/space2400), with instruction
counts matching the repro body (1 texture load, 1 typed UAV store). This
shows the resource-binding information the reporter's own repro presumably
wants is not gone -- it lives in `PSV0` + DXIL metadata and is reachable
through the standard (non-library) reflection interface. Only the
library-specific `RDAT`/`ID3D12LibraryReflection` surface, which by design
does not apply to a finalized single-stage shader, is absent.

## A secondary, unrelated observation about the as-filed repro

The issue's literal HLSL (`[numthreads(8,8,1)] void main(...)`, no
`[shader("compute")]` attribute) triggers `warning: attribute
'numthreads' ignored without accompanying shader attribute
[-Wmisplaced-attributes]` on every build tested (v1.7.2308 through
`main`), and on **current `main`'s** `dxl.exe`, linking it to `cs_6_3`
fails outright (`error: Cannot find definition of function main`,
`variant-as-filed-main-debug-link5703.txt`) -- while at v1.7.2308 the
identical as-filed source links successfully
(`manual-case-release-1.7.2308.txt`). `repro.hlsl` (the file actually used
for the primary capture and both controls above) adds
`[shader("compute")]` to restore a linkable entry point;
`repro-as-filed.hlsl` preserves the reporter's literal text for the
record. **This entry-point-resolution difference is not part of this
issue's finding** -- it was not bisected, dated, or otherwise
investigated beyond the two data points above, and is called out here
only so a reader does not mistake the as-filed variant's link failure for
evidence about RDAT. It may be worth a separate issue if not already
known/intentional, but that determination is out of scope here.

## Assessment

Repro quality: **complete** as filed, modulo the unrelated entry-point
attribute noted above (needed only to make the source link at all on
`main`; irrelevant to the RDAT finding, which reproduces identically with
or without it -- see the as-filed variant capture, which still shows
`unlinked-lib-RDAT: PRESENT` before the link failure).

Status: **repros** -- the described "actual behavior" (no RDAT part after
linking to a concrete profile) is exactly what happens, on the ground
truth and unchanged since the reporter's own build.

History: **always-repro'd**, on the strength of source-level design
(a single mutually-exclusive branch, not a bug fixed/reintroduced over
time) plus matching measurements at both the reporter's 2023 build and
current `main`. Not a regression; there is no fix boundary to look for.

Suggested action: this reads as **working as designed, not a bug** --
`RDAT` is exclusively a library-reflection part
(`ID3D12LibraryReflection`), never present in any finalized/non-library
container regardless of whether it arrived via direct compilation or via
`IDxcLinker::Link`, and the equivalent per-resource information for a
finalized shader is available through the ordinary
`ID3D12ShaderReflection` path (`PSV0` + DXIL metadata), confirmed above by
`dxa -dumpreflection` succeeding on the same linked container. The `bug`
label does not appear supported by the evidence; `reflection` and
`shader-linking` still describe the subject accurately. A short doc note
(or a comment in `IDxcLinker::Link`'s public header) stating that a
linked/finalized container never carries `RDAT` and that
`ID3D12ShaderReflection` (not `ID3D12LibraryReflection`) is the correct
interface post-link would likely have prevented this report.
