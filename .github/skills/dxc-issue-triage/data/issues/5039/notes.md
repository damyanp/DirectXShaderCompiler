# Notes — #5039 "Nonsensical error message when using undef offset in structured buffer"

## Ground truth

Local Debug compiler `main-debug`, registered at public commit
[`89e2f98e2`](https://github.com/microsoft/DirectXShaderCompiler/commit/89e2f98e29c289ae8ad9e00dd310104fea9fd7df).
The binary self-reports `1.9.0.5465 (triage, 7665270b9)`, a fork-local commit
that resolves for nobody else; `89e2f98e2` is the public upstream commit the
source corresponds to. Verified by tree, not hash: `git diff --name-only
HEAD 89e2f98e29c289ae8ad9e00dd310104fea9fd7df` reports **zero** files
outside `.github/skills/dxc-issue-triage/`; the control
`git diff --name-only HEAD v1.4.1907` (an old release tag, as a query that
can positively detect a difference) reports 7067 such files, so the
zero-result above is a real equivalence and not a query that cannot see
differences. `dxc --version` matches the registered `main-debug.json`
exactly.

No DXC source was modified. Nothing was posted, edited, labelled, closed or
reacted to on GitHub. The issue's only comment ("Related: #5040") produced
no `cross-referenced` timeline event on #5039 itself
(`gh api .../issues/5039/timeline` lists only `commented`, `labeled`,
`milestoned` and project-board events — no `cross-referenced`), so nothing
this triage did could be confused with that mention.

## Repro and predicate

`repro.hlsl` / `cmd.txt` reproduce the issue body's shader and command
(`dxc -T ps_6_0 repro.hlsl`) verbatim — `X` is read uninitialized as the
index into the fixed-size array member `S::A` of a `RWStructuredBuffer<S>`
element.

`match.json` is `internal_failure`. The reported symptom is a bad
internal-error diagnostic, not silence or a crash to merely suppress, but
`internal_failure` is still the right instrument: SKILL.md documents that a
bad `llvm::cast` throws `hlsl::Exception(DXC_E_LLVM_CAST_ERROR, ...)`, which
a Debug build traps as an assert and a Release build reports as plain
E_FAIL with the `llvm::cast<X>()` text — the same defect, two signatures,
both covered by `is_internal_failure()` (the exit-code path for the Debug
trap, the text-marker fallback for the Release/E_FAIL text). The ask is "say
something else instead", so fixed = this predicate stops matching, whether
that is because the compile now succeeds or because it now fails with a
different, comprehensible diagnostic.

**Control:** `control-initialized.hlsl` is the identical shader with
`uint X = 0;` instead of `uint X;`. It compiles cleanly on `main-debug`
(exit 0, valid DXIL emitted, `variant-initialized-main-debug.txt`), which is
`--expect no-match` and passed. This proves the predicate is discriminating
on the uninitialized-index defect specifically, not on structured-buffer
array-member codegen in general — the array-member path itself works.

## Ground-truth run

```
main-debug: exit=3758096385 (0xE0000001, STATUS_LLVM_ASSERT) -> repro
stderr: Internal compiler error: LLVM Assert
```

(`out-main-debug.txt`.) The Debug build traps the assert behind the bad cast
rather than reaching the driver's E_FAIL/text path a Release build would —
consistent with the Debug/Release signature split the predicate is written
to cover, not a different bug.

## History: `bisect --linear`, v1.4.1907..v1.9.2607

Full linear scan (chosen over binary search because the failure's *text*
changes shape release to release, which is exactly the situation where
endpoint agreement would hide a mid-history window if one existed):

| release | exit | signature |
| --- | --- | --- |
| v1.4.1907 | 0xC0000005 | access violation, empty stderr |
| v1.5.2010 | 0xC0000005 | access violation |
| v1.6.2104 | 0xC0000005 | access violation, `Internal compiler error: access violation. Attempted to read from address 0x0000000000000028` |
| v1.6.2106 | 0x80AA001D (DXC_E_LLVM_CAST_ERROR) | `Internal Compiler error: llvm::cast<X>() argument of incompatible type!` |
| v1.6.2112 | 0x80AA001D | same text as v1.6.2106 |
| v1.7.2207 | 0x80004005 (E_FAIL) | `error: llvm::cast<X>() argument of incompatible type!` |
| v1.7.2212 .. v1.9.2607 (12 releases) | 0x80004005 | same E_FAIL text as v1.7.2207, unchanged through the newest stable release |

Result: **`always-repro'd`** across every probeable stable release
v1.4.1907..v1.9.2607, plus the `main-debug` ground truth. 5 prereleases
(v1.5.2003, v1.8.2306-preview, v1.8.2405-mesh-nodes-preview, v1.10.2605.2,
v1.10.2605.24) and 1 unusable release (v1.2.0-alpha, no dxc asset) were
excluded by policy; none is named by the issue text, so no
`release-policy.json` opt-in applies. The captured signature drifts three
times (access-violation with growing detail -> `DXC_E_LLVM_CAST_ERROR` HRESULT
with "Internal Compiler error:" wording -> plain E_FAIL with "error:"
wording) but `is_internal_failure()` classifies every one of them as the
same reproducing defect, which is exactly why the exit-code-first,
text-as-backstop design in SKILL.md step 4 matters here: a predicate keyed
to any one of those three wordings would have invented a fix boundary at
whichever release changed the wording.

**Reporter fidelity:** the issue was filed 2023-02-16 and quotes
`error: llvm::cast<X>() argument of incompatible type!` verbatim. The
captured `out-v1.7.2207.txt` (2023-08 build, the first stable release after
filing) and every later stable release through `out-v1.9.2607.txt` print
that identical line (Windows spelling, `llvm::` included), which is a
mechanical match against the reporter's own quoted output, not merely "the
shader looks similar".

No `--repeat` was used: the defect is a compile-time type-unification bug
over an `undef` SSA value the front end/CodeGen substitutes for the
uninitialized read, not a runtime memory race or ASLR-sensitive corruption,
so there is no reason to expect run-to-run variance in *whether* it fires
(only in *how it is worded*, which the linear scan already covers release
by release).

## Compiler Explorer

https://godbolt.org/z/aM54EnbzT (`dxc_1_6_2112`, `dxc_trunk`; verified by
read-back, full pane text in `manual-case-godbolt-verify.txt`).

```
dxc_1_6_2112  exit=29 (low byte of 0x80AA001D)  Internal Compiler error: cast<X>() argument of incompatible type!
dxc_trunk     exit=5  (low byte of 0x80004005)  error: cast<X>() argument of incompatible type!
```

CE's Linux builds print the bare `cast<X>()` spelling rather than
`llvm::cast<X>()` (SKILL.md's documented Windows/Linux wording split for
this exact marker); same underlying defect. CE runs Release builds and its
oldest DXC is 1.6.2112, so this corroborates the local Debug ground truth
and the newest stable-release capture; it does not push the dateable
history earlier than `bisect` already did, and it cannot show the Debug
assert signature.

## Assessment

- **Status:** `repros`. **History:** `always-repro'd` v1.4.1907..v1.9.2607
  and on `main` (`89e2f98e2`) — this has never been fixed, only reworded.
- **Repro quality:** `complete`.
- **Text staleness:** none. The title and body still describe current
  behaviour exactly; only the literal wording of the bad diagnostic has
  drifted twice (access-violation text -> "Internal Compiler error:" ->
  "error:"), and none of those rewordings satisfies the reporter's actual
  ask, which is a comprehensible diagnostic naming the real problem.
- **Suggested action:** `still-valid-keep-open`.
- **Labels:** current `bug, crash, incorrect-code` all still apply — this is
  a real bug, it is crash-shaped (an internal LLVM-cast failure, trapped as
  an assert in Debug and reported via a dedicated internal HRESULT in
  Release, not an ordinary diagnosed error), and it is about the compiler's
  handling of incorrect (uninitialized) input. Proposing to add `diagnostic`
  ("Issues for diagnostics"): the entire ask is that the *diagnostic text*
  should name the real problem instead of leaking an internal LLVM
  type-mismatch message, which is squarely what that label is for.

## Related issue, not folded in

The sole comment links "Related: #5040" (`Undefined value allowed for
buffer load index`, still open). #5040 is a different construct
(`ByteAddressBuffer.Load` with an uninitialized index) and a different
symptom (silent success with `undef` baked into the DXIL operands, no
diagnostic at all, contrasted against FXC's `X4575`), not the bad-diagnostic
symptom reported here. Per SKILL.md, a same-area relationship is not the
same defect until resolution history says so, and cross-issue judgement is
collation's job — recorded here as background only, not asserted in
`comment.md` or the verdict.
