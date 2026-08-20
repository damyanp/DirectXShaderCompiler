# #5987 -- Error assigning struct into amplification payload

## Ground-truth provenance

`main-debug`'s binary self-reports `7665270b9`, which is a local/dirty tree hash, not a
publicly resolvable identifier. The registered build commit and this task's stated ground
truth, `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`, resolves directly on `origin/main` (not
orphaned). Verified by tree, not by trusting the SHA alone:
`git diff --name-only 89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD -- . ':(exclude).github/skills/'`
returns nothing (source outside the skill directory is identical), while the same diff against
a commit 50 revisions earlier returns 115 changed files (control: the diff command does detect
real differences, so the empty result above is meaningful). Cite
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df` publicly.

## Repro

`repro.hlsl` is the reporter's shader verbatim (an amplification shader with a nested
`struct s { float4x4 mat; int array[3]; float2 vec; };` wrapped in
`payloadType { s data; }`, held in `groupshared payloadType payload;`, with a whole-struct
assignment `payload.data = blah;` before `DispatchMesh`). `cmd.txt` is the reporter's own
`-T as_6_7 -E main` (repro quality: **complete**).

## Ground truth (Debug, main-debug, 89e2f98e29c289ae8ad9e00dd310104fea9fd7df)

`run --issue 5987` (`out-main-debug.txt`): exit `2147483651` = `0x80000003` (assert trap,
no debugger attached), matching the reporter's statement that a Debug build hits an assert.
Only line printed to stderr is `Internal compiler error: Terminal Error 0x80000003` -- an
assert with no debugger attached prints nothing else, per this skill's exit-code table.

Captured with `cdb -c "g;kn 40;q"` (`manual-case-assert-stack.txt`):

```
Error: 	!(onlyUsedByLifetimeMarkers(BCI))
File:
<repo>\lib\Transforms\Scalar\ScalarReplAggregatesHLSL.cpp(2630)
Func:	`anonymous-namespace'::SROA_Helper::RewriteBitCast.
	expected struct bitcast to only be used by lifetime intrinsics
```

Top of stack: `SROA_Helper::RewriteBitCast` -> `RewriteForScalarRepl` ->
`DoScalarReplacement` -> `SROAGlobalAndAllocas` -> `SROA_Parameter_HLSL::runOnModule`. This
is the HLSL-specific scalar-replacement pass that lowers a whole-struct copy (`payload.data
= blah;`) into a `memcpy`/bitcast sequence over the `groupshared` global; the assert fires
because the rewritten bitcast has a non-lifetime-marker use that the pass did not expect.

**Note for collation, not asserted in the draft:** this is the identical assert -- same file,
same line (`ScalarReplAggregatesHLSL.cpp(2630)`), same `Error:` text, same `Func:` -- as the
one captured for #5338 (`data/issues/5338/manual-case-assert-stack.txt`). The reporter of
#5987 raised the possibility of this being a duplicate of #5338 themselves but noted the two
repros look different (5338 has an explicit array-reinterpret cast; 5987 has none, only a
whole-struct assignment). Per this skill's single-writer rule, whether these two issues are
the same root cause is a cross-issue judgement for collation, not for this per-issue session
-- see `method-notes.md`.

## Release history (`bisect --linear`)

```
skipped 1 release (no usable dxc asset): v1.2.0-alpha
skipped 5 prereleases from search by policy: v1.5.2003, v1.8.2306-preview,
  v1.8.2405-mesh-nodes-preview, v1.10.2605.2, v1.10.2605.24
v1.4.1907      invalid-probe (error: invalid profile as_6_7)
v1.5.2010      invalid-probe (same)
v1.6.2104      invalid-probe (same)
v1.6.2106      invalid-probe (same)
v1.6.2112      invalid-probe (same, out-v1.6.2112.txt)
v1.7.2207      repro  (error: llvm::cast<X>() argument of incompatible type!)
v1.7.2212      repro
v1.7.2212.1    repro
v1.7.2308      repro   <- release the reporter's environment (1.7.2308.7) shipped from
v1.8.2403      repro
v1.8.2403.1    repro
v1.8.2403.2    repro
v1.8.2405      repro
v1.8.2407      repro
v1.8.2502      repro
v1.8.2505      repro
v1.8.2505.1    repro
v1.9.2602      repro
v1.9.2602.24   repro
v1.9.2607      repro
```

Result: **always-repro'd across every probeable release, v1.7.2207..v1.9.2607** (5 releases
skipped as unprobeable, 5 probeable prereleases excluded by policy). `as_6_7` is a
Shader-Model-6.7-specific amplification-shader profile string; releases through v1.6.2112
reject it outright with `error: invalid profile as_6_7` (`out-v1.6.2112.txt`) before reaching
any code the bug lives in -- correctly classified `invalid-probe`, not a fix. v1.7.2207 is
the oldest release that can even compile the repro, and it reproduces the reporter's exact
quoted diagnostic text verbatim (`out-v1.7.2207.txt`): `error: llvm::cast<X>() argument of
incompatible type!`, at exit `0x80004005` (E_FAIL) -- the E_FAIL-but-still-internal shape
this skill's `is_internal_failure` text-marker fallback exists for. main-debug (built from a
tree equivalent to upstream `main`) still crashes today, so the bug has never been fixed:
**always-repro'd for as long as `as_6_7` has existed to test it.**

## Controls (reporter's own workarounds, run against main-debug)

- `control-no-assign.hlsl` -- identical shader with `payload.data = blah;` commented out
  (the reporter's first described workaround). `variant-no-assign-main-debug.txt`: exit 0,
  clean DXIL emitted (`--expect no-match`, satisfied).
- `control-unwrapped.hlsl` -- `payloadType`'s members made loose instead of nested inside
  `s` (the reporter's second described workaround), each assigned individually.
  `variant-unwrapped-main-debug.txt`: exit 0, clean DXIL emitted (`--expect no-match`,
  satisfied).

Both of the reporter's own negative controls pass: the predicate does not fire on either
workaround, confirming the trigger is specifically a **whole-struct assignment into a member
that is itself a nested struct**, inside a `groupshared` amplification-shader payload, and
that the predicate discriminates rather than firing on every `as_6_7` compile.

## Compiler Explorer

`godbolt --issue 5987` (`manual-case-godbolt-verify.txt`, link
https://godbolt.org/z/YoavsEvns, shortlink read back and verified to match):

- `dxc_1_6_2112`: `error: invalid profile as_6_7` -- same invalid-probe reason as the local
  release sweep; expected, not evidence of a fix.
- `dxc_trunk`: `error: cast<X>() argument of incompatible type!` (CRASH, CE's Linux build
  omits the `llvm::` prefix Windows prints for the same `DXC_E_LLVM_CAST_ERROR` failure) --
  confirms the bug is still present on a rolling trunk build today, corroborating main-debug.

The one existing comment on the issue (damyanp, 2024-10-28) is only a Compiler Explorer link
(`https://godbolt.org/z/a1vsvfhPz`) to `dxc_trunk` with the identical shader and no verdict
text of its own; `api/shortlinkinfo` confirms it holds the reporter's exact shader against
`dxc_trunk -T as_6_7`, consistent with "still reproduces" rather than any recorded fix.

## Assessment

- Status: **repros**.
- History: **always-repro'd** across every release that can compile `as_6_7` (v1.7.2207
  onward) and on main-debug; older releases are `invalid-probe` because the profile itself
  did not exist yet, not because the bug was absent.
- Repro quality: **complete**.
- Confidence: **high** -- exact reported diagnostic text reproduced verbatim on a Release
  release binary, exact reported assert reproduced on Debug main-debug, both reporter-supplied
  workarounds independently confirmed as negative controls, and Compiler Explorer trunk
  corroborates today.
- Labels: current `bug, dxil, crash` already fit; no change proposed.
- Text staleness: none -- the issue text (Nov 2023) still accurately describes current
  behavior.
- Suggested action: **still-valid-keep-open**.
