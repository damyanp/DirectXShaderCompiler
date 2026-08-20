# Notes — #5261: DXIL: Deadlock when loading `RayDesc` from `ByteAddressBuffer`

## Ground truth

`main-debug`, commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (verified: `git merge-base
--is-ancestor` succeeds against current HEAD, and `git diff --name-only
89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD` touches nothing outside
`.github/skills/dxc-issue-triage/`, i.e. only triage-batch commits sit on top of it). The
locally built binary self-reports a fork-local commit (`7665270b9`) rather than the public
sha, so provenance was confirmed by tree, not by the self-reported hash: diffing
`7665270b9` against `89e2f98e2...` shows no files outside the skill directory, while the same
diff against a commit 50 back (control) does show real source changes
(`docs/DXIL.rst`, `docs/ReleaseNotes.md`, `azure-pipelines.yml`, ...). `dxc --version` reports
`dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)`, matching the
compiler registry.

## Repro

The issue body's shader and command are used verbatim (repro quality: **complete**):

```hlsl
[numthreads(32, 8, 1)] void main(uint2 threadId
                                 : SV_DispatchThreadID) {
    ByteAddressBuffer buffer = ResourceDescriptorHeap[NonUniformResourceIndex(10)];
    RayDesc result = buffer.Load<RayDesc>(sizeof(RayDesc) * 1);
}
```
`-E main -T cs_6_6 repro.hlsl -Fo test`

## The symptom has two build-dependent signatures (same shape as #3873)

The thread itself documents both:
- 2023-06-01 (filing, reporter's release build): the command "runs indefinitely" (a hang), on
  both Windows and Linux downloads.
- 2023-06-30 (`llvm-beanz`, maintainer, own Debug build):
  `Assertion failed: (false && "cannot flatten hlsl intrinsic."), function RewriteCall, file
  ScalarReplAggregatesHLSL.cpp, line 2761`.
- 2023-07-11 and 2023-11-17 (reporter): confirmed still an assert on two later builds.
- 2024-09-03 (`damyanp`): "still repros" via a Compiler Explorer link (CE ships Release
  builds, so this corroborates the hang/no-diagnostic side, not the assert).

`match.json` is `any_of(timeout, internal_failure)` for exactly this reason: a bare
`internal_failure` predicate would score every Release release binary in the regressed range
as clean (they hang, they do not trap), inventing a fix boundary that isn't there; a bare
`timeout` predicate would do the reverse to a Debug/assertions build. The captured releases
below confirm both arms fire as predicted: every `repro` verdict in the regressed range below
is a `TIMEOUT`, not a trapped assert — because the cached release archives are Release builds.
No hand-run Debug build of an old commit was built for this triage (rebuilds of a different
commit are out of scope here), so the assert side is corroborated by the maintainer's own
2023-06-30 comment rather than independently reproduced, but the Release-side hang matches the
originally reported symptom exactly and the source location the maintainer names
(`ScalarReplAggregatesHLSL.cpp`, `RewriteCall`) still exists in the tree at the equivalent
`DXASSERT(0, "cannot flatten hlsl intrinsic.")` (currently line 2918; the file was
substantially refactored by the fix below, so the line number has moved since 2023).

## Ground-truth result: does not reproduce

```
main-debug: exit=0 timed_out=False -> no-repro
```

The repro compiles cleanly to `ret void` (the unused `result` is dead-code-eliminated before
any RayDesc-flattening pass runs). Because the filed repro never uses `result`, a clean exit
alone under-tests the code path the bug is actually in, so a control was added that consumes
the loaded fields (`control-used.hlsl`, `RWStructuredBuffer<float> Out; ... Out[0] =
result.TMin + result.TMax + result.Origin.x + result.Direction.x;`, same `-T cs_6_6` command,
`--expect no-match`). This also compiles cleanly and its disassembly
(`used_out.ll`, generated locally, not committed as a capture) shows the `RayDesc` load
correctly flattened into four `dx.op.rawBufferLoad.f32` calls at the expected byte offsets
(32/44/48/60, i.e. `Origin`, `TMin`, `Direction`, `TMax`) feeding the arithmetic — i.e. the SROA
pass the assert used to come from now flattens this call path successfully rather than merely
skipping it.

## History: regressed, then fixed (non-monotonic — `--linear` scan, 2 invalid probes, 5
prereleases excluded by policy)

| release | build date | result |
|---|---|---|
| v1.4.1907 | 2019-07-15 | invalid-probe — `error: invalid profile cs_6_6` (SM6.6 not yet supported) |
| v1.5.2010 | 2020-10 | invalid-probe — same `invalid profile cs_6_6` |
| v1.6.2104 | 2021-04-20 | no-repro |
| v1.6.2106 | 2021-07-01 | no-repro |
| v1.6.2112 | 2021-12-08 | no-repro |
| v1.7.2207 | 2022-07-18 | no-repro |
| **v1.7.2212** | **2022-12-16** | **repro (TIMEOUT)** |
| v1.7.2212.1 | 2023-03-01 | repro (TIMEOUT) |
| v1.7.2308 | 2023-08-14 | repro (TIMEOUT) |
| v1.8.2403 | 2024-03-07 | repro (TIMEOUT) |
| v1.8.2403.1 | 2024-03-22 | repro (TIMEOUT) |
| v1.8.2403.2 | 2024-03-29 | repro (TIMEOUT) |
| v1.8.2405 | 2024-05-24 | repro (TIMEOUT) |
| v1.8.2407 | 2024-07-31 | repro (TIMEOUT) |
| v1.8.2502 | 2025-02-20 | repro (TIMEOUT) |
| **v1.8.2505** | **2025-05-24** | **no-repro** |
| v1.8.2505.1 | 2025-07-14 | no-repro |
| v1.9.2602 | 2026-02-20 | no-repro |
| v1.9.2602.24 | 2026-05-27 | no-repro |
| v1.9.2607 | 2026-07-29 | no-repro |
| main-debug | (this triage) | no-repro |

`v1.4.1907` and `v1.5.2010` reject `cs_6_6` outright (`invalid profile cs_6_6`), so the
effective floor for this repro is `v1.6.2104` (SM6.6/`ResourceDescriptorHeap` postdates both).

This history matches the reporter's own account precisely: their "previous… worked fine"
compiler was built from `0392e60dbc8` (2022-11-10 — inside the `v1.7.2207..v1.7.2212` window,
consistent with the regression landing between those two dates), and their broken build was
`ea3623fdf71` (2023-05-30 — inside the `repro` range). The 156-commit regression window was
not narrowed to a single commit: doing so with confidence would need an isolated before/after
build of a candidate inside that window, which this triage does not perform (no rebuilds are
in scope here beyond the already-registered `main-debug` ground truth), and no commit message
in that range names `RayDesc`, `ByteAddressBuffer::Load` or "flatten".

## Fix attribution: strong, not proven

The `v1.8.2502..v1.8.2505` fix window holds 162 commits, but only **one** touches
`lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp` (the exact file the maintainer's 2023
assert names):

```
053e7ac65 Refactor udt intrinsic arg copy to before SROA, flatten RayDesc (#7440)
```
(full sha `053e7ac656e01d90aa9931c4d8b8a89c14741027`, 2025-05-16, author Tex Riddell)

Verified: `git merge-base --is-ancestor 053e7ac65 v1.8.2505` succeeds (exit 0);
`git merge-base --is-ancestor 053e7ac65 v1.8.2502` fails (exit 1). Its own message:
"There were RayDesc arguments that weren't treated consistently, and weren't copied in when
necessary, leading to problems. ... This change flattens RayDesc args for all intrinsics that
use them [and] separates the copy-in/copy-out generation into a separate operation before
SROA." It states `Fixes #7434`, a different, closed issue ("Unflattened RayDesc breaking
HL->DXIL lowering") whose own repro is the ray-tracing `HitObject::MakeMiss`/`TraceRay`
pattern, not `ByteAddressBuffer::Load<RayDesc>` — so #5261 is not literally the tracked repro
for PR #7440, and the current `RewriteCall` switch (read after the fix, `lib/Transforms/Scalar/
ScalarReplAggregatesHLSL.cpp` around line 2850) still only special-cases `TraceRay`,
`HitObject::TraceRay`, `HitObject::MakeMiss` and `TraceRayInline` by name — there is no
`Load`-specific case. The fix's second half, moving copy-in/copy-out generation for aggregate
intrinsic arguments to a separate pass **before** SROA runs, is the systemic part of the change
and is the more likely reason #5261's pattern (a RayDesc alloca receiving an sret-style return
from the templated `Load<T>` call, then flattened by SROA) stopped hitting the old
per-intrinsic switch's `default: DXASSERT(0, "cannot flatten hlsl intrinsic.")` path — but this
triage did not build the isolated parent/candidate pair needed to prove that mechanism
directly, so the attribution is **strong** (single relevant commit in a narrow window, on-topic
commit message, corroborating symptom-class match with #7434) but not certain.

## Compiler Explorer

https://godbolt.org/z/1K9zo9Mnc (`dxc_1_6_2112`, `dxc_trunk`; both exit 0, matching the local
`v1.6.2112` no-repro result and the `main-debug` fix). CE's oldest DXC (`dxc_1_6_2112`) cannot
date the fix — the regression/fix pair both postdate it — so this link corroborates the
current-vs-old-CE-baseline agreement rather than adding history. Read-back of the shortlink
matched what was sent; no warning was printed. Full pane text is in
`manual-case-godbolt-verify.txt`; both panes disassemble to `ret void` because the CE command
line does not use the loaded value either.

## Labels

`bug`, `crash` remain accurate — the issue really was a crash-class defect for its whole open
lifetime. No label change proposed; the fix is not yet reflected by any label and there is no
narrower label (e.g. a "fixed" state) in the current taxonomy for an open issue.

## Confidence: high

Complete, verbatim repro; full non-monotonic release history captured with `--linear`
(no reliance on a binary-search short-circuit); both endpoints and the interior transitions
directly observed; fix commit identified with a documented, checkable ancestry proof; CE
corroborates. The only unresolved detail is the exact regression commit and the exact
mechanism by which PR #7440 fixes a pattern it does not name — both flagged above rather than
asserted.
