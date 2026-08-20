Symptom (from the issue body, verbatim steps): a two-step lib+link compile,

    dxc.exe -T lib_6_3 -Zi -Qstrip_reflect -Qembed_debug -Fd testc.pdb -Fo test.lib test.hlsl
    dxc.exe -link -T lib_6_3 -Zi -Qstrip_reflect -Qstrip_debug -Fd test.pdb -Fo test.bin test.lib

"reproduces" means: the second (link) invocation fails with

    dxc failed : DXIL container does not contain the given part.

on stderr/stdout and a nonzero exit code, i.e. the link step that combines
-Fd (dump a PDB) with -Qstrip_debug (strip embedded debug info from the
container before writing the final binary) errors out instead of producing
test.bin (and, per the reporter, a PDB -- the compiler itself is said to
still emit a PDB when debug info is stripped from the object, so the
reporter expects the linker to do the same rather than erroring).

"does not reproduce" means: the second invocation exits 0 and produces
test.bin (whether or not the emitted test.pdb is a well-formed PDB is the
separate, already-filed #5739 and is out of scope for this predicate).

Repro quality: complete -- both commands and the shader are given verbatim
in the issue body. The commands themselves are unmodified (only the input
filename changes, to repro.hlsl per this tool's convention); the shader
source needed one addition to actually exercise the reported defect on the
ground-truth build: `[shader("compute")]` above `main`. Without it, `dxc`
warns `attribute 'numthreads' ignored without accompanying shader
attribute` and the link step fails earlier, with `error: Library has no
functions to export` -- an unrelated failure, because a numthreads-only
entry point is no longer auto-detected as an export for a lib_6_x target
(confirmed: `repro-as-filed.hlsl`, the reporter's file verbatim, reproduces
that different, earlier error under `cmd-as-filed.txt`; the -Fd/-Qstrip_debug
interaction the issue is actually about is never reached). This is exercised
without the shader source in question ever being altered by anything the
issue asked about -- it is a separate, plausible tightening of a lib-export
default between 2022 (v1.7.2207.3, the reporter's build) and now, is
orthogonal to -Fd/-Qstrip_debug, and is not otherwise investigated here.

Known related threads (read during step 1, not acted on beyond noting them):
  - #5739 ("DXC linker debug output isn't a valid PDB (and doesn't work
    with PIX)"), filed the same day by the same reporter against the
    non-strip variant of the same two commands. Separate defect, not this
    predicate's subject.
  - PR #6833 ("Fix -link -Qstrip_debug failing"), cross-referenced onto this
    issue on 2024-07-30, claims "Fixes #5737" in its body. As of this triage
    the PR is still OPEN (unmerged) -- confirmed via `gh issue view 6833`
    (state: OPEN) -- so its existence is not evidence of a fix landing on
    main and must be checked against the ground-truth build, not assumed.
