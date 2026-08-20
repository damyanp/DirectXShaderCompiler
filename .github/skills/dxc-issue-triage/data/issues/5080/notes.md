# Issue 5080 triage

## Assessment

The complete, as-filed repro (`repro.hlsl` + `cmd.txt`: cbuffer, `-fvk-use-dx-layout`,
`-fspv-target-env=vulkan1.3`, `-fspv-debug=vulkan-with-source`) no longer crashes current
`main-debug`. It exits 0 and emits valid SPIR-V, including a `DebugTypeComposite` /
`DebugGlobalVariable` pair for the cbuffer (`out-main-debug.txt`). The maintainer-suggested
negative control — the same command without `-fvk-use-dx-layout` — also exits 0
(`variant-no-dx-layout-main-debug.txt`), matching s-perron's own report in the thread that
dropping the flag avoids the crash.

Status is `does-not-repro`, repro quality `complete`. The measured stable-release history is
**non-monotonic**, not "regressed-in": `bisect` alone reported both endpoints (v1.6.2112,
v1.9.2607) clean and warned that the issue's filing date (2023-03-06) falls inside that
range, so `--linear` was used instead. The scan shows v1.7.2207 through v1.8.2403.2 crashing
with an access violation (`0xC0000005`) and v1.8.2405 onward clean.

**v1.6.2112 needed a correction.** Its automatic capture (`out-v1.6.2112.txt`) also looked
clean, but for the wrong reason: the release rejects the reporter's
`-fspv-target-env=vulkan1.3` outright (`error: unknown SPIR-V target environment
'vulkan1.3'`; it only recognises vulkan1.0/1.1/1.2/universal1.5), so the run never reached
the code under test — a variant of the "release rejects an unrecognised option value" trap
already known for `-fspv-debug=vulkan-with-source` (see #7300), here hitting
`-fspv-target-env` instead. Re-run by hand with the otherwise-identical command but
`-fspv-target-env=vulkan1.0` (`measure-target-env-v1.6.2112.py`,
`manual-case-target-env-v1.6.2112.txt`), v1.6.2112 does crash with the same access
violation. v1.6.2112 is therefore the **first stable release able to even parse
`-fspv-debug=vulkan-with-source`**, and it reproduces once probed correctly; the true
history is "reproduces from v1.6.2112 through v1.8.2403.2, fixed at v1.8.2405", not a
regression window starting at v1.7.2207. See `method-notes.md` for the full writeup of this
trap.

`fixed-in`: **v1.8.2405** (the boundary; `out-v1.8.2405.txt` spot-checked to confirm it is a
genuine clean pass — accepts `vulkan1.3` and emits the debug records — not another masked
invalid probe). Suggested action: `close-fixed`; the issue remains open with no maintainer
follow-up confirming the fix in-thread.

## Invalid and excluded probes

- v1.4.1907, v1.5.2010, v1.6.2104, v1.6.2106: `invalid-probe`. SPIR-V codegen is absent
  and/or `vulkan-with-source` is rejected as an unrecognised debug-info control parameter
  (the already-documented #7300 trap).
- v1.6.2112: corrected to `repro` by hand (see above); the tool's own capture, taken at face
  value, would have read as `no-repro` for the wrong reason.

## Fix-commit attribution (strong, not certain)

`git log --oneline v1.8.2403.2..v1.8.2405 -- tools/clang/lib/SPIRV/LowerTypeVisitor.cpp`
returns four commits touching that file in the window. One,
`1e59ce9185485535011e1f706d1ab3c1b349eac1` ("[SPIR-V] Fix debug instruction with cbuffer +
FXC (#6531)"), removes the exact assert quoted in the issue body —
`assert(isa<SpirvDebugGlobalVariable>(debugInstruction) && isa<HybridType>(debugSpirvType));`
— and its message discusses DX-layout-driven complex-type lowering of cbuffers, matching
s-perron's in-thread diagnosis and the `-fvk-use-dx-layout` control exactly.

This attribution was **not** confirmed by building the candidate commit and its first
parent and running the repro directly (the skill's preferred, stronger method). That attempt
was made and abandoned: the parent commit's build fails to configure under the only CMake
available on this machine (4.3.1, which has dropped `cmake_policy(SET CMP0051 OLD)` — `main`
has since made the identical removal, independently), and after patching that identically in
both worktrees, compiling further fails under `/WX` on `warning C5285` from
`include/llvm/ADT/StringRef.h` against the installed MSVC 14.51 standard library — a
toolchain-drift issue unrelated to the defect and too broad to patch narrowly and
identically across both comparison arms. Full detail in
`manual-case-fix-commit-attempt.txt` and `method-notes.md`. The attribution therefore rests
on the exact-text assert match plus a two-stable-release window (v1.8.2403.2 fails,
v1.8.2405 does not) and is called **strong, not certain**, per the skill's own allowance for
that weaker evidence tier when a build-and-test comparison is not practical.

## Provenance and corroboration

`dxc --version` on `main-debug` matches the registered ground truth
(`main-debug.json`: `git_commit=89e2f98e29c289ae8ad9e00dd310104fea9fd7df`). The binary
self-reports a local `triage` branch merge commit (`7665270b9`), not the public SHA directly;
`git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df` reports zero files
changed outside `.github/skills/dxc-issue-triage`, establishing tree-equivalence to the
registered public commit. A control diff against `HEAD~50` reports 97 files changed outside
the skill directory, confirming the check is not vacuous.

Compiler Explorer corroborates the history at https://godbolt.org/z/9rshx68rz: `dxc_1_6_2112`
(given `-fspv-target-env=vulkan1.0`, the oldest value that release accepts, in place of the
reporter's `vulkan1.3` — the same substitution used locally) crashes with `SIGSEGV`
(exit 139); `dxc_trunk` exits 0 and emits SPIR-V with the expected debug records. Full panes
are archived in `manual-case-godbolt-verify.txt`; `godbolt-note.txt` explains the
substitution to a reader. CE runs Release Linux builds and never overrules the local Debug
corroboration; here the two agree.

## Cross-references and timeline

Issue #5441 was filed against the same symptom and closed as a duplicate of #5080
(confirmed via `gh api` read of #5441's state and comments); it is the one pre-existing
cross-reference on this issue's timeline. A later in-thread comment (Goshido, 2023-08-03)
reports the same assert/access-violation manifesting on a different real-world shader using
the same flags, on a release after the original filing — consistent with the measured
history (the bug was still present at that date; v1.8.2405 was not released until later).
Last thread activity is 2023-09-12 (a contributor investigating); no maintainer comment
confirms the fix in-thread.

## Labels

Current labels are `bug`, `spirv` (`triage.py labels --issue 5080`). The measurements
(confirmed internal-failure/access-violation crash on affected releases) support adding
`crash`; this is a proposal only and was not applied.
