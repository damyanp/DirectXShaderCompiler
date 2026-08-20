# #5737 -- Link fails when using -Fd with -Qstrip_debug

## Ground truth

`main-debug`, commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (public alias
`13730886e`; the binary self-reports fork-local `ab5400907`, resolved to
this SHA per `.cache/compilers/main-debug.json`'s recorded provenance),
version string `dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) -
1.9.0.5465 (triage, 7665270b9)`.

## What the issue asks

Two-step compile-then-link build (issue body, verbatim):

    dxc.exe -T lib_6_3 -Zi -Qstrip_reflect -Qembed_debug -Fd testc.pdb -Fo test.lib test.hlsl
    dxc.exe -link -T lib_6_3 -Zi -Qstrip_reflect -Qstrip_debug -Fd test.pdb -Fo test.bin test.lib

The link step is reported to fail with
`dxc failed : DXIL container does not contain the given part.` The reporter
says this is inconsistent because ordinary (non-link) compilation still
produces a PDB when debug info is stripped from the object.

## Repro construction

The reporter's shader (`repro-as-filed.hlsl`, verbatim) does not itself
reproduce the *reported* failure on this ground truth: `main` warns
`attribute 'numthreads' ignored without accompanying shader attribute` on
the lib compile, and the link step instead fails earlier with
`error: Library has no functions to export` (`variant-as-filed-main-debug.txt`,
captured with `--expect no-match` -- confirmed no-repro, i.e. that is *not*
the symptom this issue is about). A numthreads-only entry point is no
longer auto-detected as an export for a `lib_6_x` target; adding
`[shader("compute")]` above `main` (kept as `repro.hlsl`, the primary
repro) restores export detection without touching anything -Fd/-Qstrip_debug
related, and the reported failure reappears exactly as filed
(`out-main-debug.txt`, exit 1, `dxc failed : DXIL container does not
contain the given part.`). This looks like an unrelated tightening between
2022 (the reporter's v1.7.2207.3) and today, not investigated further here.

## Ground-truth result

`triage.py run --issue 5737` on `main-debug`: **repro** (`out-main-debug.txt`,
exit 1). Verbatim match of the issue's quoted error text.

## Controls

- `variant-no-strip-debug-main-debug.txt` (`generate-control-no-strip-debug.py`,
  `--expect no-match`, confirmed **no-repro**): same two-step build, same
  shader, `-Qstrip_debug` removed from the link line only. Link succeeds
  (exit 0). This isolates the failure to the link step's
  `-Qstrip_debug` handling rather than to linking `lib_6_3` containers in
  general.
- `variant-strip-debug-no-fd-main-debug.txt`
  (`generate-control-strip-debug-no-fd.py`, `--expect match`, confirmed
  **repro**): same two-step build, same shader, `-Fd` removed from the link
  line entirely (`-Qstrip_debug` kept). **Still fails identically** --
  `dxc failed : DXIL container does not contain the given part.`

  This is a real finding beyond the issue's own framing: the title and body
  describe the defect as specifically combining `-Fd` *with*
  `-Qstrip_debug`, but on this ground truth plain `-link -Qstrip_debug`
  (with no `-Fd` at all) already fails the same way. The defect is broader
  than "the interaction between the two flags" -- `-Qstrip_debug` alone at
  link time is sufficient. Not marking this `text_stale`: the issue's
  description is still accurate as far as it goes (that exact combination
  does still fail), just narrower than the actual reproducing surface.

## Source corroboration (read-only; not investigated further)

`tools/clang/tools/dxclib/dxc.cpp:1553-1557` maps the exact quoted string to
`DXC_E_MISSING_PART`. `DxcContext::Link()` (line 944) forwards the raw CLI
arguments -- including `-Qstrip_debug` -- straight into
`IDxcLinker::Link(...)` (lines 966-977), then calls the single-argument
`ActOnBlob(pContainer.p)` (line 985) with no debug blob. Inside `ActOnBlob`
(line 305), `UpdatePart()` (line 336, definition at line 452) unconditionally
calls `pContainerBuilder->RemovePart(DFCC_ShaderDebugInfoDXIL)` whenever
`m_Opts.StripDebug` is set (lines 468-471), with no check for whether the
part is present -- unlike the ordinary-compile path just above it (lines
889-894), which explicitly resets `m_Opts.StripDebug = false` when there was
never any embedded debug info to strip, precisely to avoid this. If the
linker itself already omits the debug part for a stripped link (consistent
with PR #6833's own description, below), `RemovePart` (or the later
`WritePartToFile` at line 359 for `-Fd`) throwing `DXC_E_MISSING_PART` on an
already-absent part is a plausible mechanism for both the `-Fd` and no-`-Fd`
failures observed above. Not built or tested at this commit; offered as
corroboration, not as an established root cause.

## Related threads

- **#5739** ("DXC linker debug output isn't a valid PDB (and doesn't work
  with PIX)"), filed the same day by the same reporter, same shader, same
  two commands minus `-Qstrip_debug`. Separate defect (a malformed, not a
  missing, PDB); not investigated here beyond confirming it is a different
  symptom.
- **PR #6833** ("Fix -link -Qstrip_debug failing"), cross-referenced onto
  this issue on 2024-07-30 and says "Fixes #5737" in its body. As of this
  triage (`gh pr view 6833`) the PR is **OPEN / not merged / not draft**,
  last updated 2024-10-22. Its description says the fix is to stop emitting
  the ILDB chunk in the link output when `-Qstrip_debug` is used "in the
  first place", and separately notes "this will cause -Fd -Qstrip_debug to
  fail" for an unrelated reason it attributes to #5739. Since the PR is
  unmerged, its existence is not evidence of a fix on `main`; the
  ground-truth run above shows the defect still present.

## History

`triage.py bisect --issue 5737`: v1.4.1907, v1.5.2010 and v1.6.2104 all
reject the `-link` option itself (`Unknown argument: '-link'`, confirmed in
`out-v1.4.1907.txt`, `out-v1.5.2010.txt`, `out-v1.6.2104.txt`) -- the
built-in linker mode did not exist yet, so these are `invalid-probe`, not
clean results. From **v1.6.2106** (2021-07-01, the first release where
`-link` is recognized) through **v1.9.2607** (2026-07-29) and `main-debug`,
every probeable release reproduces. `always-repro'd` across the entire
`-link`-capable release history; the issue (filed 2023-09-15 against
v1.7.2207.3) sits well inside that range.

## Labels

Current (`bug`, `shader-linking`) are accurate and not proposed for change.

## Verdict

- status: `repros`
- repro-quality: `complete` (issue's own shader and commands, modified only
  by adding `[shader("compute")]` -- see Repro construction above -- to
  restore export detection lost to an unrelated, later behavior change)
- history: `always-repro'd` across every `-link`-capable release
  (v1.6.2106..v1.9.2607) and `main-debug`; v1.4.1907/v1.5.2010/v1.6.2104
  predate the `-link` flag itself and are invalid probes
- confidence: high
- suggested-action: `still-valid-keep-open` (an unmerged PR, #6833, already
  proposes a fix)
- Compiler Explorer: skipped -- the repro is an inherently two-invocation
  compile-then-link chain over an intermediate DXIL container, which a
  single CE pane cannot express (see `godbolt_skip` reason recorded via
  `triage.py godbolt --skip`).
