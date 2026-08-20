# #5849 notes.md

## Summary

Reproduces on main (ground truth `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`), and has
reproduced identically on every stable release since `lib_6_7` first became
available. This is a real, still-open gap, not a stale/superseded report: RDAT gives
the runtime zero indication that Payload Access Qualifiers (PAQs) were used on a DXR
entry point, so `MaxPayloadSizeInBytes` validation cannot be relaxed for PAQ-only
payloads the way the reporter and amarpMSFT agreed it should be.

## Ground truth

`main-debug`'s registered `git_commit` in `.cache/compilers/main-debug.json` already
equals the supplied ground truth SHA exactly, and `dxc --version` matches the
registry. The binary self-reports a different fork-local commit
(`7665270b9`/`ab5400907`) in its `provenance_note`; per SKILL.md's "verify by tree,
not by SHA" guidance, `git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
returns **zero** files outside `.github/skills/dxc-issue-triage/`, so the already-built
Debug binary is valid ground truth for the cited commit. No rebuild was performed or
needed anywhere in this triage, per the session's constraints.

## Method

No shader is attached to the issue; the reporter's description is entirely prose
about RDAT/runtime behaviour. `repro.hlsl` is an agent-constructed minimal DXR
library (`lib_6_7`) with a `[raypayload]`-qualified 20-byte payload
(`float4 color` + `uint hitKind`), fully PAQ-annotated across closesthit/miss/raygen
so PAQs actually engage without warnings (`write(caller, closesthit)` had to be added
to `hitKind` to silence a `-Wpayload-access-trace` "value will be undefined" warning
unrelated to the issue under triage -- a real PAQ usability quirk, not the bug itself).

The symptom lives in the `RDAT` container part (`RuntimeDataFunctionInfo::
PayloadSizeInBytes`), produced only at container-assembly time
(`lib/DxilContainer/DxilContainerAssembler.cpp`), not in `-Fc`/LLVM-IR text. The
SKILL.md-recommended `dxa.exe -dumprdat`/`-dumpreflection` tool is **not built** in
this checkout's `build/Debug/bin` (only `dxc.exe`, `FileCheck.exe`, and the tblgen
tools are present), and building it would be a "rebuild", which this session may not
do. Instead, `manual-case-rdat-payload.py` parses the compiled container's `RDAT`
`FunctionTable` directly in Python, using the documented on-disk layout from
`include/dxc/DxilContainer/DxilContainer.h`, `DxilRuntimeReflection.h`, and
`RDAT_LibraryTypes.inl`: DXIL container header (32 bytes) -> part offsets -> `RDAT`
part -> `RuntimeDataHeader` -> sub-part offsets -> `FunctionTable` sub-part ->
`RuntimeDataTableHeader{RecordCount, RecordStride}` -> fixed-stride
`RuntimeDataFunctionInfo` records. `PayloadSizeInBytes` is always at byte offset 20
and `ShaderKind` at offset 16 of every record, regardless of stride/version
extensions, because new fields are only ever appended (`RuntimeDataFunctionInfo2`).

Two controls corroborate the harness itself, not just the conclusion:
- **Self-test anchor:** the closest-hit entry point's `AttributeSizeInBytes` reads
  as exactly 8 in every run -- the true size of `BuiltInTriangleIntersectionAttributes`
  (`float2`), a value the harness never special-cases. If the record layout/offsets
  were wrong, this would not land on the right answer by chance.
- **PAQ-engagement control (`paq-engagement-control.txt`):** disassembling both
  builds confirms `!dx.dxrPayloadAnnotations` module metadata is present for the
  default (PAQ-enabled) build and **absent** for the `-disable-payload-qualifiers`
  build, so the two measured variants really do differ in whether PAQs engaged --
  this is the same metadata `tools/clang/test/DXC/disable_paq.hlsl` asserts
  `CHECK-NOT` on for its disabled case.

## Evidence

`manual-case-rdat-payload-history.txt` sweeps `repro.hlsl` through `main-debug` and
every cached stable release (`v1.4.1907` through `v1.9.2607`), each compiled twice
(default PAQ-enabled, and `-disable-payload-qualifiers`), per SKILL.md's population-claim
rule for "always/never" symptoms (visit every release, not a sample):

- `v1.4.1907`, `v1.5.2003`, `v1.5.2010`, `v1.6.2104`, `v1.6.2106`, `v1.6.2112`: both
  variants fail with `error: invalid profile lib_6_7` -- correctly classified as
  **invalid-probe** (feature absent: `lib_6_7` did not exist yet), not `no-repro`.
- `v1.7.2207` (2022-07-18) through `v1.9.2607` (2026-07-29), and `main-debug`: **14
  data points**, all agreeing. In every one, `MyClosestHit` reports
  `PayloadSizeInBytes=20`, `MyMiss` reports `PayloadSizeInBytes=20`, in **both** the
  PAQ-enabled and `-disable-payload-qualifiers` builds -- byte-for-byte identical
  RDAT output regardless of whether PAQs engaged.
- `DxilFeatureInfo1`/`DxilFeatureInfo2` (`RDAT_LibraryTypes.inl:48-95`) were also
  read in full: there is no PAQ-related bit in either feature-flag enum, so RDAT
  carries no alternate signal (e.g. a feature flag) that a runtime could use instead
  of a zeroed size. The gap is total, not just in the one field the reporter named.

So the symptom has reproduced identically on **every** `lib_6_7`-capable release ever
cataloged here, plus main -- an always-repro'd-since-`lib_6_7` finding, not a
regression with a bisectable boundary.

## Source-level corroboration

`lib/DxilContainer/DxilContainerAssembler.cpp` (~line 1502-1535) unconditionally
copies `props.ShaderProps.Ray.payloadSizeInBytes` into the RDAT function record, with
no PAQ-conditional branch anywhere in that function or nearby. `git log --all -i
--grep="payload.*qualif"`, `--grep="MaxPayloadSize"`, and `--grep="5849"` across all
branches found no commit implementing the reporter's or amarpMSFT's proposal.
`docs/ReleaseNotes.md` has no mention of it. The existing test
`tools/clang/test/DXC/disable_paq.hlsl` only checks the ignored-PAQ warning/metadata
suppression path and has no RDAT/`PayloadSizeInBytes` assertion at all -- there is no
test that would catch this either way. This is consistent with: the fix was
maintainer-agreed in principle but never implemented.

## Timeline signal (not decisive on its own, but corroborating)

Per the issue's `gh api .../timeline`: `work-item` label was added, then removed, and
the issue was milestoned **"Dormant"** on 2024-10-23 (same day as the label removal),
about a year after filing, with no PR or commit ever cross-referencing it. No
cross-references exist in the timeline. This is circumstantial (a milestone is not
proof of non-implementation by itself) but is consistent with, and reinforces, the
source-level finding that the fix was simply never picked up.

## Numbering caveat

The issue body's own bullet list is literally numbered "1.", "3.", "5." (not "1.",
"2.", "3." -- a markdown numbering artifact in the original post, not a
transcription error here). amarpMSFT's "Agreed, option 3 makes sense" is read as
agreeing with the reporter's own closing statement "(3) zeroing the payload size
looks like the best option" -- i.e., the same "zero `PayloadSizeInBytes` for
PAQ-using entry points" proposal this triage measured -- since that is the option the
reporter had just called "the best option" immediately before amarpMSFT's one-line
reply. This reading is very likely correct but rests on interpreting the reporter's
own inconsistent numbering rather than an unambiguous source, and is flagged here so
a reviewer can re-check it independently.

## Compiler Explorer

Skipped (`godbolt_skip` recorded in `verdict.json`): the symptom lives in the `RDAT`
container part, which is a binary sub-container assembled after DXIL/IR generation.
Compiler Explorer's DXC panes show `-Fc`-style disassembly of the DXIL/LLVM-IR text,
which does not carry `RuntimeDataFunctionInfo::PayloadSizeInBytes` at all (confirmed
locally: PAQ metadata is visible in `-Fc` output, but the RDAT byte value is not). A
CE link would not demonstrate the symptom to a reader, so none was published.

## reviewed_by

Left unset by the user's explicit instruction: step 10's independent cross-model
review is a batch-collation step, out of scope for this single-issue session.
`triage.py audit --issue 5849` was run **without** `--collated`, matching the
per-issue worker's view (SKILL.md: "a correctly-executed worker session cannot
satisfy [reviewed_by] and reporting it as a gap teaches the worker that audit output
is noise").

## Verdict

- **status:** repros
- **repro_quality:** agent-constructed
- **confidence:** high (source-confirmed root cause + full 14-release/main
  population sweep, both in full agreement; two independent controls corroborate the
  measurement instrument itself)
- **suggested_action:** still-valid-keep-open (a genuine, maintainer-agreed,
  unimplemented enhancement; not a duplicate, not fixed, not stale/invalid)
