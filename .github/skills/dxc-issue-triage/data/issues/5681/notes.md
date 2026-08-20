# #5681 -- Segmentation fault/ICE when attempting a particular (invalid) code pattern

## What was tested

Repro (`repro.hlsl`, `cmd.txt`): the exact statements from the issue body
(`InterlockedMax(b.Load<T>(0).value, 1, original)` on a `RWByteAddressBuffer` obtained through
`ResourceDescriptorHeap[0]`), wrapped in the `[numthreads(1,1,1)] void main()` entry point that
maintainer llvm-beanz posted as a Compiler Explorer reconstruction of the same issue
(https://godbolt.org/z/5n31h354h). Compiled with `-T cs_6_6 -E main repro.hlsl` (SM 6.6 is
required for `ResourceDescriptorHeap`).

`match.json` uses `internal_failure` (exit-status class: trapped assert / access violation /
DXC internal-error HRESULT), per the skill's standing rule for anything crash-shaped -- a
message-keyed predicate would be fooled by the different crash text an assert-enabled Debug
build and a Release/CE build print for the same underlying defect.

## Ground truth (main-debug, commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`)

```
$ dxc -T cs_6_6 -E main repro.hlsl
warning: function 'RWByteAddressBuffer::Load<T, unsigned int>' has internal linkage but is not
defined [-Wundefined-internal]
...
error: cannot map resource to handle.
repro.hlsl:9:3: error: Atomic operation targets must be groupshared, Node Record or UAV.
  InterlockedMax(b.Load<T>(0).value, 1, original);
  ^
```
Exit `2147500037` = `0x80004005` (E_FAIL) -- an ordinary diagnosed error per the skill's exit
table, not a crash. **Does not reproduce**: `main` cleanly rejects the construct with a
diagnostic instead of ICEing, which is exactly the fix the reporter asked for ("since the
compiler ICEd instead of reporting a diagnostic").

## History (`triage.py bisect --issue 5681`)

| release | result |
| --- | --- |
| v1.4.1907, v1.5.2010 | `invalid-probe` -- `error: invalid profile cs_6_6` (SM 6.6 / `cs_6_6` did not exist yet; correctly excluded, not a clean run) |
| v1.6.2104 | **repro** -- `Internal compiler error: access violation. Attempted to read from address 0x0000000000000008` (exit `0xC0000005`) |
| v1.8.2403.1, v1.8.2502 | **repro** -- same access violation |
| v1.8.2505, v1.8.2505.1, v1.9.2607 | **no-repro** -- clean `error: Atomic operation targets must be groupshared, Node Record or UAV.` |

`fixed-in v1.8.2505` (last reproducing release `v1.8.2502`). The access-violation text and
address are identical across every reproducing release, which is corroborating evidence this
is one defect rather than several coincidentally-crashing releases.

The bisection floor is v1.4.1907; both skipped releases there are `invalid-probe` (predate
`cs_6_6`/`ResourceDescriptorHeap`), not clean runs, so "always reproduced as far back as SM 6.6
existed" is the honest framing rather than "regressed at v1.6.2104".

## Compiler Explorer (https://godbolt.org/z/vfcsj3ThG)

`dxc_1_6_2112` (CE's oldest DXC): `exit=139 CRASH`, `Program terminated with signal: SIGSEGV`.
`dxc_trunk`: `exit=5` (CE truncates the Windows HRESULT `0x80004005` to its low byte on
Linux), and prints the same `Atomic operation targets must be groupshared, Node Record or UAV.`
diagnostic seen locally on `main`. This corroborates both ends of the local bisection with an
independently-built, Linux/Release toolchain -- CE's oldest DXC still crashes, current trunk
does not.

## Candidate fix commit (unverified by a build)

The 162-commit window between `v1.8.2502` and `v1.8.2505` narrows to 19 commits touching
`lib/HLSL/HLOperationLower.cpp` (`git log --oneline v1.8.2502..v1.8.2505 --
lib/HLSL/HLOperationLower.cpp`). The most plausible candidate is `053e7ac65` ("Refactor udt
intrinsic arg copy to before SROA, flatten RayDesc", #7440, fixes #7434): it rewrites how
UDT-typed intrinsic arguments are copied and flattened *before* `ScalarReplAggregatesHLSL`
runs, which is exactly the machinery a templated `Load<T>()` result (a UDT temporary) goes
through before reaching the atomic-target validation this issue's repro fails at. This is a
plausible mechanism, not a confirmed one: it was not isolated by building the candidate commit
and its parent per the skill's "if the exact commit matters, build it" guidance, because that
would require rebuilding a Debug `dxc` in a separate worktree, which was out of scope for this
session's boundary (no rebuilds/relinks of shared targets). Treat the attribution as
**plausible, not certain**, and the window itself (`v1.8.2502`..`v1.8.2505`) as the safe claim.

## Labels

Current (`bug, crash, diagnostic, incorrect-code`) all still fit: the report is accurately
described by all four even after the fix -- `crash` and `bug` describe what was reported and
confirmed by this triage's history search, `diagnostic` and `incorrect-code` describe the
now-emitted error path and the fact the input is invalid. No label changes proposed.

## What could not be determined

- The exact fixing commit (see above) -- only the release window is confirmed.
- The reporter's closing question ("is there a way to express this with valid HLSL today?") is
  a language-capability question the thread itself already answers (comments propose
  `RWByteAddressBuffer::InterlockedMax(byteOffset, ...)` with manual `sizeof`/`offsetof`
  arithmetic); it is not a compiler-behaviour claim this triage's tooling measures, and is left
  to the draft comment as context only.
- No cross-reference events exist on this issue's timeline (`gh api .../timeline`), so no
  related/duplicate issue was found that way.

## Sampling note

This is a single-issue batch (batch-019, issue #5681 only); no cross-issue or backlog-wide
claim is made.
