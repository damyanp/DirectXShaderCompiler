# Expected symptom — #4871

## What the issue claims

Reporter (Adam Miles, 2022-12-12): given

```hlsl
void Func(inout uint byteOffset)
{
}

uint PSMain(uint i : I) : SV_TARGET
{
    Func(--i);  // Subtracts 2...
    return i;
}
```

the generated DXIL contains an "add minus two" instruction (`%2 = add i32 %1, -2, !dbg !37`)
where the source only pre-decrements `i` once. `Func` is an empty `inout` function — its body
never touches `byteOffset` — so the only place a `-1` should appear is the pre-decrement
expression itself, and it should appear exactly once. `Func(--i)` being lowered to a `-2`
constant means the decrement is effectively applied twice: once for the `--i` expression, and
again somewhere in the inout-parameter copy-in/copy-out machinery DXC generates because HLSL
`inout` parameters are passed by value at the AST level (copy-in before the call, copy-out
after).

The issue body links a now-defunct Compiler Explorer short link
(`https://godbolt.org/z/73so7qzzW`), which resolves (checked via
`api/shortlinkinfo`) to compiler `dxc_trunk` with arguments
`-T ps_6_7 -E PSMain -fspv-target-env=universal1.5`. Compiler Explorer's DXC panes always
append `-Zi -Qembed_debug -Fc -` (see SKILL.md step 7), which explains the `!dbg !37` in the
quoted line — the reporter did not need to type `-Zi` themselves.

## Timeline / maintainer position

- 2023-07-08: `llvm-beanz` (maintainer) assigns self "to check against my development branch
  that is rewriting parameter passing."
- 2023-07-08 (same day): `llvm-beanz` states "This will be fixed by #5377. I've verified this
  is fixed against the draft PR #5249. I'll keep this assigned to me to construct a test case
  to include with the final PR." — i.e. the claimed fix is **not on `main`**; it was verified
  only against an unlanded rewrite branch.
- **#5377** ("`out` and `inout` should always be references") is an umbrella *issue*, not a PR.
  It was closed `not_planned` on 2024-09-16 — the effort was abandoned, not completed.
- **#5249** ("[Draft] Rewrite output parameters") is a draft PR. As of this triage it is still
  `open` and unmerged (checked via `gh api .../pulls/5249`).
- 2024-09-26: #4871 itself was unassigned from `llvm-beanz` and milestoned `Dormant`, shortly
  after #5377 closed as not-planned. No further comment was left explaining the unassignment.
- No GitHub cross-reference event points *at* #4871 from any commit or PR (checked via the
  issue timeline API), so there is no evidence any change specifically targeting this bug ever
  merged.

This matches the SKILL.md "issue filed against code that is not merged" hazard: the maintainer's
"verified fixed" statement was scoped to a draft branch that never landed, and the umbrella
issue tracking that branch was later closed as not planned. The prior expectation before running
anything is therefore that **the miscompile still reproduces on `main`**, because the only
described fix vehicle was abandoned. This is a prediction to be checked against ground truth,
not an assumed conclusion.

## Symptom predicate (informal, before probing)

"Reproduces" means: compiling the repro at `-Od` (no optimization, matching the reporter's use
of a debug-info build with no explicit `-O` flag) and inspecting the generated IR/DXIL for the
call site of `Func(--i)` shows the pre-decrement lowered to a constant of magnitude **2**
(`add i32 %N, -2` or equivalent), rather than magnitude **1**. "Fixed" means the same
inspection shows magnitude 1 (a single decrement), with a control confirming the reader/anchor
can tell the difference (see `match.json`).

This is a compiler-verifiable, deterministic front-end/CodeGen miscompile — no GPU/runtime
needed. Repro quality: **complete** (the issue body contains the entire shader and target
profile via the CE short link).
