# Expected behaviour — #4958

**Title:** Compiling hull shader with unused globals causes internal compiler error

## What the reporter says

Filed against `v1.7.2212`. Compiling the attached hull shader (`-T hs_6_6 -E mainHS -Fo
output.dxil debug_hs.hlsl`) crashes with an **access violation**. The shader declares two
module-scope globals that are never referenced by any function in the file:

- `static const float3x3 g_ACESRRTDesaturationMatrix = ...` — initialised from arithmetic on a
  `float3` literal (`g_ACESAP1ToY`) and a scalar constant. Commenting this out alone makes the
  crash go away.
- `static Texture2D<float4> gProjTextureMaps[ARRAY_SIZE];` — a thread-local (`static`) array of
  resource descriptors. Commenting this out alone *also* makes the crash go away, independently
  of the first global.

The reporter also says the crash's exact address/shape is sensitive to `ARRAY_SIZE`: 0 and 2
"appear to succeed", 1 read-access-violates at `0xFFFFFFFFFFFFFFFF`, and any value greater than 2
read-access-violates at `0x0000000000000000`. That table of sizes is itself part of what
"reproduces" means here — a symptom that is present only for some array sizes is a weaker/
different claim than a symptom present for every ARRAY_SIZE, and both directions should be
checked, not just ARRAY_SIZE=1.

The one maintainer comment (Keenuts, 2023-01-26) narrows this further:

- Does **not** trigger when targeting SPIR-V (`-spirv`) — DXIL-only.
- The crash is inside `ScalarReplAggregatesHLSL.cpp`, in SROA, and — per the comment — SROA
  attempts to run the transform on the `Texture2D` array *before* it is eliminated as unused.

No PR or branch is named anywhere in the issue body, the comment, or the timeline (checked via
`gh api .../timeline`; only `commented`, `labeled`, `milestoned` (→ "Dormant"),
`added_to_project_v2` and `project_v2_item_status_changed` events exist — zero
`cross-referenced` events). So this is a claim about `main`/mainline DXC in general, not about
unmerged work.

## What "reproduces" means for this triage

The reported symptom is a **crash** (access violation) compiling a `hs_6_6` hull shader that
contains two specific *unused* module-scope globals, when targeting **DXIL** (not SPIR-V).
Per the exit-code table in the skill, an access violation is `0xC0000005`, which is an
`internal_failure` regardless of what text (if any) is printed — use `internal_failure` as the
predicate, not a message-text match, and do not treat "no message" as "does not reproduce".

"Still reproduces" = ground truth crashes (internal-failure exit code) on the DXIL repro built
from the issue's exact source and exact command line (profile `hs_6_6`, entry `mainHS`).

"Fixed" = ground truth compiles the same input to a normal exit (0, or an ordinary diagnosed
error like `E_FAIL` with a diagnostic — not a crash status) for every `ARRAY_SIZE` value the
reporter says crashes (i.e. not just the one arbitrarily currently set in the file, `1`).

"Changed behaviour" = still an internal failure but only for some subset of the reported
`ARRAY_SIZE` values, or a different internal-failure signature (e.g. now an assert/trap instead
of an AV, or vice versa) — worth recording separately since a Debug ground truth may trap on an
assert where the reporter's presumably-Release build access-violated.

## Repro quality

`complete` — the issue body contains the full, self-contained `.hlsl` source and the exact
command line used to compile it (as a header comment inside the code block). No extra files,
no project context needed.

## Not yet run

Nothing has been compiled yet. This file is written before any probe, per skill step 2.
