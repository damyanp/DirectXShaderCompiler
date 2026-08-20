# #5748 -- Groupshared memory used through patch constant function allowed in hull shaders

## Repro

Reporter's Compiler Explorer link (https://godbolt.org/z/es4EY9hrY, confirmed via
`https://godbolt.org/api/shortlinkinfo/es4EY9hrY`) uses `-T lib_6_5` on a shader with:

- `[shader("hull")]` entry point `main` (does not touch `groupshared`)
- patch-constant function `HSPatch` (named via `[patchconstantfunc("HSPatch")]`) that reads
  `groupshared float4 gs`

`repro.hlsl` is a verbatim copy of that shader. `cmd.txt` uses `-T lib_6_3` instead of the
reporter's `-T lib_6_5` -- the library-target profile number is not the subject under test,
and `lib_6_3` is expressible by far more of the release catalog, which is what makes the
history bisection below possible. This is a deliberate deviation from the filed configuration;
`-T lib_6_5` was also spot-checked locally and behaves identically.

`control-no-groupshared.hlsl` is the same hull/patch-constant shape with no `groupshared`
variable at all, used as a negative control.

Repro quality: **complete** (exact reporter repro, args confirmed from the CE shortlink).

## Predicate

`match.json` is an `all_of`:

1. `contains "target datalayout"` -- positive anchor. `dxc` only prints the full LLVM-IR
   disassembly once the entire compile+validation pipeline succeeds; a validation failure
   prints only the error/note block, never the module dump. Without this anchor, the other
   two absence-style clauses below would be satisfied for free by any unrelated failed
   compile (the exact `not_regex`-satisfied-by-a-parse-failure hazard the skill documents).
2. `contains "addrspace(3)"` -- proves the groupshared load reached codegen rather than being
   optimized away. Not itself discriminating (it can also appear inside the validator's own
   `note:` line), but combined with clause 1 it establishes that a *successful* compile still
   contains the groupshared access.
3. `not_regex "Thread Group Shared Memory not supported"` -- absence of the specific validator
   diagnostic. This is the actual "bug present" signal.

Verified empirically: a failing (fixed-behavior) compile's captured output has no
"target datalayout" line at all, only the error/note text -- so clause 1 cannot be satisfied
by a failed run, which is what makes the `not_regex` clause safe to use here.

## Controls

- `control-no-gs` (`control-no-groupshared.hlsl`, same `cmd.txt` args, `--expect no-match`):
  scored no-match as expected on ground truth -- a shader with no groupshared use never
  satisfies clause 2, confirming the predicate does not fire on unrelated hull/patch-constant
  shaders.
- `control-hs-direct` (repro compiled directly as `-T hs_6_0 -E main` via `--args`,
  `--expect no-match`): scored no-match as expected -- compiling the same source directly as a
  hull-shader target (rather than as a library) correctly fails validation on ground truth,
  which corroborates the reporter's claim that only the *library*-target code path skips the
  patch-constant function.
- Positive-direction confirmation of the predicate's true-positive branch (clause 2 alone
  cannot prove clause 1+3 together indicate a real reproduction) comes from the bisection
  below: 19 stable releases plus every intermediate probed release score `repro`, and
  `out-v1.9.2602.24.txt` (the last reproducing release) was manually inspected and shows a
  genuine `addrspace(3)` load inside `HSPatch`, exit 0, full disassembly, and no validator
  error -- not an artifact of a failed/incomplete compile.

## Ground truth result

`main-debug` @ `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`: **no-repro**. The captured output
(`out-main-debug.txt`) shows validation correctly failing with
`Thread Group Shared Memory not supported from non-compute entry points.`, and the emitted
`note:` lines name the function
`?HSPatch@@YA?AUPCStruct@@...` (i.e. `HSPatch`) explicitly -- the validator now checks the
patch-constant function, not only the `[shader("hull")]` entry point, confirming the reported
defect is fixed on this ground truth.

## History

`bisect --linear` (full release catalog, monotonic/clean, no invalid probes, 5 prereleases
correctly excluded by policy):

- **`repro`** on every stable release from v1.4.1907 (2019-07) through v1.9.2602.24
  (built 2026-05-27) -- 19 stable releases plus a spot-checked disassembly confirming a genuine
  reproduction, not a probing artifact.
- **`no-repro`** starting at v1.9.2607 (built 2026-07-29).

`--linear` was used (rather than binary search) because the transition needed to be located
precisely and to rule out a non-monotonic fix/revert/re-fix shape; the result is a single,
clean step with no intermediate disagreement.

**History: fixed-in v1.9.2607.**

## Source attribution

The obvious candidate is **PR #5749** ("Validate patchconst functions for GS/update test"),
opened by the same reporter (`pow2clk`) three minutes after this issue and declaring
`Fixes #5748` in its body. It was **never merged**: it sat open for over two years and was
auto-closed by an inactivity sweep on 2026-01-22 ("closed as it has not been updated in the
last two years") -- the same "agreed fix lapsed via bot closure" pattern documented in
SKILL.md's #2427 case. Its diff (a 3-line `else if (M.IsPatchConstantShader(F))` added
directly in the raw per-function loop of the pre-2024-08 `lib/HLSL/DxilValidation.cpp`) is
*not* what is present in the ground-truth source.

GitHub GraphQL blame on `lib/DxilValidation/DxilValidation.cpp` at the ground-truth commit
attributes the lines implementing the library-target patch-constant-function TGSM check
(including the `M.IsPatchConstantShader(&F)` disjunct in the entry-function filter used for
library targets) to commit `c44a383b49d38e4fc64c8f66cbb5ac9e2fd88a79`
("Add GroupSharedLimit attribute support for Mesh, Amp and Node shaders", **PR #8140**,
merged 2026-02-13T17:23:58Z, confirmed via `gh pr view 8140`). That PR's own diff, read
directly, changes exactly the missing check:

```
-      if (F.isDeclaration() || !M.HasDxilEntryProps(&F))
+      if (F.isDeclaration() ||
+          !(M.HasDxilEntryProps(&F) || M.IsPatchConstantShader(&F)))
```

Before this change, the library-target loop in `ValidateGlobalVariables` only visited
functions with `HasDxilEntryProps` (i.e. declared entry points); a patch-constant function has
no `DxilEntryProps` of its own in a library target, so it was silently skipped -- which is
exactly this issue's reported defect. PR #8140 also adds a dedicated regression test,
`tools/clang/test/LitDXILValidation/GroupShared/groupshared_patchconstant.hlsl`. The PR's
primary, titled purpose is unrelated (GroupSharedLimit for Mesh/Amplification/Node shaders);
this fix appears to have landed as an incidental side effect of a broader refactor of the same
validation loop, not as a change targeting #5748 or referencing it.

**Caveat on dating:** PR #8140 merged 2026-02-13, which is *before* the build date of
v1.9.2602.24 (2026-05-27) -- the release that the empirical bisection shows still reproduces
the bug. This is not a contradiction in the bisection (which is a direct behavioral
measurement of shipped binaries and is not in question), but it does mean the mainline-merge
date and the release-binary fix date are about five months apart. The `v1.9.2602.24` naming
(major.minor.YYMM.patch) suggests it is a servicing/patch build of a `2602` (February 2026)
snapshot that predates the Feb 13 merge and did not pick up mainline changes made after its
branch point, consistent with SKILL.md's documented pattern that release trains can lag
mainline by a substantial margin. No DXC source was rebuilt to verify this directly (out of
scope / forbidden for this triage); the source attribution to PR #8140/commit `c44a383b4` is
**strong but not proven to be the exact commit that reached the release train** -- the
authoritative, unambiguous finding is the release-binary bisection itself
(v1.9.2602.24 -> v1.9.2607).

## Compiler Explorer

`godbolt --issue 5748` (default panes `dxc_1_6_2112`, `dxc_trunk`; `godbolt-note.txt` explains
what to look for): https://godbolt.org/z/daqY8a3x8

- `dxc_1_6_2112` (2021, i.e. within the always-reproducing release range): exit 0, full
  disassembly, `addrspace(3)` loads inside `HSPatch`, no validator error -- reproduces.
- `dxc_trunk`: exit 5, `Thread Group Shared Memory not supported from non-compute entry
  points.` naming `HSPatch` -- fixed, matching ground truth.

Shortlink read back and verified by the tool; full pane text archived in
`manual-case-godbolt-verify.txt`.

## Labels

`labels --refresh` + `labels --issue 5748`: current labels (`bug`, `shader-linking`,
`diagnostic`, `validation`) all still fit -- this is a validation-diagnostic bug specific to
library/shader-linking targets. No additions or removals proposed.

## Text staleness

The issue's title and body describe the defect accurately as of filing and are not stale
relative to what the compiler *did* at the time; they simply predate the fix. Not flagging
`--text-stale`, since the description is not inaccurate, only out of date -- the issue is
simply open past its fix.

## Assessment

- Status: **does-not-repro** (fixed on ground truth).
- Repro quality: **complete**.
- History: **fixed-in v1.9.2607** (last reproducing: v1.9.2602.24).
- Confidence: **high** for the behavioral verdict and release boundary (clean linear
  bisection, spot-checked evidence, matching controls in both directions). The specific
  fixing *commit* attribution (PR #8140) is a strong candidate corroborated by blame + diff
  reading, but not confirmed by building at that commit (forbidden for this triage), and its
  merge date does not line up cleanly with the release boundary -- caveated above.
- Suggested action: **close-fixed**.
