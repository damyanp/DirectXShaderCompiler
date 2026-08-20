# Notes — #4871

## Summary of what was measured

`Func(--i)` -- calling an empty `inout` function with a pre-decremented argument
-- still miscompiles on `main-debug` (public upstream commit
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`, self-reporting fork-local build id
`7665270b9`; version string verified against the registered compiler before
use, see Provenance below). The generated DXIL/LLVM IR lowers the single
pre-decrement to a magnitude-**2** subtraction (`add i32 %N, -2`) instead of
magnitude-1, exactly as the issue describes. This is a wrong-code miscompile:
no error, warning, or crash accompanies it either way.

```
$ dxc -T ps_6_0 -E PSMain -Zi -Qembed_debug repro.hlsl
...
  %dec1 = add i32 %0, -2, !dbg !38 ; line:7 col:10
```
(full capture: `out-main-debug.txt`)

## Repro

`repro.hlsl` is the issue body verbatim (the reporter's Compiler Explorer
short link `https://godbolt.org/z/73so7qzzW` resolves via
`GET godbolt.org/api/shortlinkinfo/73so7qzzW` to the identical source, target
`ps_6_7`, entry `PSMain`, and the extra flag `-fspv-target-env=universal1.5`).

**Two deliberate deviations from the filed configuration, both controlled:**

1. **Dropped `-fspv-target-env=universal1.5`.** No `-spirv` flag was ever
   present, so the compile targets DXIL the whole time -- the issue's own
   `add i32 ..., -2` text is DXIL/LLVM IR, not SPIR-V disassembly. Captured
   control `variant-as-filed-main-debug.txt` runs the reporter's exact
   arguments (`--expect match`, since the symptom must still be present) and
   is byte-identical to `out-main-debug.txt` except for the `!dx.source.args`
   metadata line recording the extra flag. The flag is inert here; dropping
   it changes nothing about what is measured.

2. **Lowered the profile from the reporter's `ps_6_7` to `ps_6_0`.** This is
   an AST/CodeGen defect in inout-parameter handling with no dependency on
   shader-model version, and `ps_6_7` does not exist before v1.7.2207 --
   using it as filed would make every earlier stable release an
   `invalid-probe` (SKILL.md step 6's "target the repro at the oldest
   profile" guidance) and hide whatever history actually exists. Confirmed
   locally that `ps_6_0` reproduces the identical defect before adopting it.

`cmd-as-filed.txt` preserves the reporter's literal invocation for reference.

## Predicate and controls (`match.json`)

`all_of`: (1) `define void @PSMain\(` -- proves the compile reached codegen,
so a rejected/failed compile cannot vacuously satisfy clause 2; (2)
`add i32 %[\w.]+,\s*-2\b` -- the wrong-code constant, anchored on the general
LLVM SSA-name form rather than a specific register number or name, since SSA
numbering is not stable across dxc versions (confirmed: v1.4.1907 uses
plain `%1`/`%2`, current builds use `%0`/`%dec1`).

Three controls, all captured with `--expect no-match` and all passing as
declared:

| control | source | result |
| --- | --- | --- |
| `control-plain-decrement.hlsl` | `--i; return i;`, no `Func` call at all | single `add i32 %0, -1` |
| `control-separate-decrement.hlsl` | `--i;` as its own statement, then `Func(i)` with the already-decremented value | single `add i32 %0, -1` |
| `control-no-decrement-call.hlsl` | `Func(i); return i;`, no decrement anywhere | no `add i32` line at all |

These three controls jointly localise the defect precisely: it is **not**
that `Func` (an `inout` call) ever fabricates a spurious subtraction (ruled
out by `control-no-decrement-call` and `control-separate-decrement`), and it
is **not** that pre-decrement itself is broken (ruled out by
`control-plain-decrement`). The defect needs the specific combination of a
decrement/increment expression written directly as the argument to an
`inout` parameter -- consistent with the maintainer's own diagnosis ("check
against my development branch that is rewriting parameter passing"): HLSL's
AST models an `inout` argument as pass-by-value with a compiler-generated
copy-in/copy-out around the call, and the copy-in step evidently re-applies
the argument expression's side effect a second time when that expression is
itself a pre/post increment or decrement.

## History

```
python scripts\triage.py bisect --issue 4871           # binary search
python scripts\triage.py bisect --issue 4871 --linear  # every stable release
```

Binary search: **regressed-in v1.5.2010** (last good: v1.4.1907). 5 releases
(v1.4.1907..v1.6.2112) were probed at the reporter's original `ps_6_7` in an
earlier pass and scored `invalid-probe` there purely because `ps_6_7` did not
exist yet -- resolved by lowering the profile to `ps_6_0`, which every stable
release back to v1.4.1907 accepts.

The `--linear` scan (mandatory per SKILL.md whenever a population or
monotonicity claim is made) visited all 20 probeable stable releases from
v1.4.1907 through v1.9.2607 individually (5 further prereleases excluded by
policy -- none named explicitly in the issue text, so none opt in via
`release-policy.json`) and found exactly **one** transition: clean at
v1.4.1907, `repro` at every single release from v1.5.2010 onward with no
reversion. The tool labels any scan with more than one run as
"non-monotonic history" (its literal `runs`-count check), but the underlying
per-release captures (`out-v*.txt`) show a plain, single, still-standing
regression -- not an oscillating one.

**Validity of the v1.4.1907 "clean" result is not an accident of an
unexercised code path.** `out-v1.4.1907.txt` is a genuine positive control:
the disassembly shows `Func` inlined into `PSMain`'s debug-info scope
(`!41 = !DILocation(..., inlinedAt: !42)`) and a real `add i32 %1, -1`
computing the correct decrement -- i.e. the release actually compiled the
`inout` call and got the arithmetic right, not that it silently skipped
something. `out-v1.5.2010.txt` is likewise a genuine `repro`, not a crash or
rejection standing in for one.

**Window size**: v1.4.1907 (2019-07) to v1.5.2010 (2020-10) is over a year
and multiple internal snapshots; no attempt was made to bisect inside that
window to a specific commit (no local release-branch checkouts exist for
that span in this environment), so "regressed in v1.5.2010" describes the
release boundary, not a commit.

## Compiler Explorer

Published as a compute-shader restatement (`repro-cs.hlsl`) because
`hlsl_clang_trunk` cannot lower a pixel shader returning `uint` through
`SV_Target` (`error: attribute 'SV_TARGET' only applies to a field or
parameter of type 'float/float1/float2/float3/float4'` -- an unrelated Sema
rule in the new front end, confirmed with the original `repro.hlsl` pane
before switching sources). The construct under test -- an inout call with a
decrement written as its argument -- is not stage-specific; confirmed the
translation reproduces on `main-debug` before publishing
(`variant-cs-restatement-main-debug--match-cs.txt`, `match-cs.json` retargets
the same predicate at `CSMain`).

Link: https://godbolt.org/z/4318d6hbY (verified by shortlink readback --
`api/shortlinkinfo` returned exactly the three panes and arguments sent).
Full pane text archived at `manual-case-godbolt-verify.txt`.

| pane | result |
| --- | --- |
| `dxc_1_6_2112` (CE's oldest DXC) | reproduces: `add i32 %1, -2` |
| `dxc_trunk` (current rolling DXC) | reproduces: `add i32 %1, -2` |
| `hlsl_clang_trunk` (new Clang-based HLSL front end) | **does not reproduce**: `%3 = add i32 %2, -1` |

**This is the single most useful finding in this triage.** The maintainer's
2023-07-08 comment says the fix would come from a "development branch that
is rewriting parameter passing" (tracked by umbrella issue #5377, draft PR
#5249). #5377 was closed `not_planned` on 2024-09-16 and #5249 is still an
unmerged open draft, so that specific rewrite never reached classic DXC's
`main` -- consistent with every classic-DXC probe above still reproducing.
But Compiler Explorer's `hlsl_clang_trunk` pane is a *different* rewrite
effort (DXC's HLSL support being reimplemented on top of upstream Clang) and
it independently gets this exact case right: one `add i32 ..., -1`, used
once, stored once. Whether that front end's parameter-passing model is the
literal continuation of the abandoned #5249 branch or an independent
reimplementation was not determined here (out of scope for a compiler-only
probe); what is established is that the *symptom* is already fixed in the
compiler DXC's HLSL support is migrating to, while still present in the one
that ships today.

## Maintainer-comment / timeline reconciliation

- 2023-07-08: `llvm-beanz` assigns self, then states the fix is verified
  against draft PR #5249 and will land via #5377.
- #5377 ("`out` and `inout` should always be references") is a tracking
  *issue*, not a PR; closed `not_planned` 2024-09-16
  (`gh api repos/.../issues/5377 --jq '{state,state_reason,closed_at}'`).
- #5249 ("[Draft] Rewrite output parameters") is still `state: open`,
  unmerged (`gh api repos/.../pulls/5249`).
- 2024-09-26: #4871 unassigned from `llvm-beanz` and milestoned `Dormant`
  (`gh api repos/.../issues/4871 --jq '.milestone.title'`), 10 days after
  #5377 closed as not planned. No comment explains the unassignment.
- No GitHub cross-reference event points *at* #4871 from any commit, PR, or
  issue (`gh api repos/.../issues/4871/timeline`, filtered on
  `event=="cross-referenced"`, returns nothing) -- there is no evidence any
  change specifically targeting this bug ever merged into classic DXC.

The maintainer's "this will be fixed" was accurate about a branch that
existed at the time, and is now stale: that branch was abandoned. The issue
text itself (title, body) is not stale -- it still accurately describes
current `main` -- but the two comments read, top-to-bottom, as an open
question moving toward resolution when the actual outcome (recorded only in
a different issue's `state_reason`) was the opposite.

## Provenance

`main-debug` registered at public upstream commit
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`; the binary self-reports
fork-local build id `7665270b9`, confirmed with `dxc --version` before use
and matching the compiler registry (`.cache/compilers/main-debug.json`) and
`triage.py sql "SELECT * FROM compilers"` exactly.

```
$ dxc --version
dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)
```

Equivalence check (this triage session, not re-derived from the registry's
`provenance_note`, which names older SHAs from a prior registration cycle
and was left as-is per the strict per-issue write boundary):

```
git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df \
  | Where-Object { $_ -notlike ".github/skills/dxc-issue-triage/*" }
# (no output -- no compiler-source difference outside the skill tree)
```

Negative control, to prove the diff can detect a real difference (comparing
against a commit ~2000 commits back):

```
git diff --name-only 7665270b9 HEAD~2000 | Select-String -NotMatch "^\.github/skills/dxc-issue-triage/"
# .github/CODEOWNERS, .github/ISSUE_TEMPLATE/bug_report.md, ... (real diffs, as expected)
```

## What could not be determined

- The exact commit that introduced the regression between v1.4.1907 and
  v1.5.2010 (a 15-month window with no local mainline history available at
  the release-branch granularity in this environment).
- Whether `hlsl_clang_trunk`'s correct behaviour descends from the abandoned
  #5249 branch or is independent; not answerable from compiler output alone.
- Whether the double-subtraction generalises to post-decrement (`i--`),
  increment (`++i`/`i++`), or compound-assignment (`i -= 1`) written as an
  inout argument -- only the exact reported pre-decrement shape was probed,
  per SKILL.md's caution against speculative scope expansion beyond the
  reported symptom.
