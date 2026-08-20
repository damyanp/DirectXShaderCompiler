# #5436 -- [Validation] Add an assert to make sure no dxil opcodes are left unvalidated.

## What the issue asks

Filed 2023-07-18 by bob80905 (Joshua Batista) -- confirmed both from the fetched
`issue.json` and independently from a live `gh api repos/.../issues/5436` call, so this is
the real creation date, not a fetch artifact. Labels `enhancement`, `tech-debt`,
`validation`. No comments on the issue itself.

It observes that two functions then in `DxilValidation.cpp` dispatch per-DXIL-opcode
validation through a `switch (Opcode)` whose `default:` case is empty, so an opcode that
falls through is silently treated as "nothing to validate" with no signal that it was
never covered:

- `ValidateDxilOperationCallInProfile`
- `ValidateHandleArgsForInstruction`

Ask: add a `DXAssert` in each default case, or -- if a function can be proven never to
reach its default for certain opcodes -- leave a comment explaining why.

This is a request to add defensive/diagnostic code, not a report of a wrong compile or a
crash. There is no HLSL input whose `dxc` output would change if the assert were added:
an opcode silently skipped by an empty default produces byte-identical output today, with
or without an assert (asserts only fire, they never change codegen), so no shader
predicate can observe "was this assert added". `triage.py godbolt --skip` was used for
this reason and the reasoning is recorded on the issue's database row (no `godbolt.txt` /
link exists, by design).

## GitHub confirms the issue is a live, acknowledged gap, not a stale one-off

The issue's only timeline cross-reference is dated 2023-11-08T00:47:21Z, from PR #5982
("Shader Model 6.8", merged 2023-11-09). Reading that PR's review comments
(`gh api repos/microsoft/DirectXShaderCompiler/pulls/5982/comments`) shows why: reviewer
llvm-beanz asked "Do we have an issue tracking this?" directly on the `default:` case
of the (then newly-touched) handle-argument validation switch in
`lib/HLSL/DxilValidation.cpp`, and bob80905 -- the PR author and #5436's own reporter --
replied with exactly "This issue:" followed by the #5436 URL (review comment id
`1385806407`, in reply to `1384238568`). So this is not merely a self-filed idea sitting
unconfirmed; a second engineer (a maintainer) independently flagged the same gap in
review four months later, and the reporter confirmed #5436 as its tracker. This is
sourced entirely from GitHub's live API (issue timeline + PR review comments), not from
local git history.

## What is actually on `main` at ground truth (89e2f98e2)

Read both functions directly (`lib/DxilValidation/DxilValidation.cpp`, `main-debug` at
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`):

**`ValidateDxilOperationCallInProfile`** (function starts line 2256). Its opcode switch's
default case, lines 2802-2806:

```cpp
  default:
    // TODO: make sure every Opcode is checked.
    // Skip opcodes don't need special check.
    break;
  }
}
```

No assert; only a TODO acknowledging the exact gap the issue describes.

**`ValidateHandleArgsForInstruction`** (lines 562-583) now performs the generic
per-operand handle checks, and is invoked from a separate dispatcher,
**`ValidateHandleArgs`** (lines 585-602), whose own default case is:

```cpp
void ValidateHandleArgs(CallInst *CI, DXIL::OpCode Opcode,
                        ValidationContext &ValCtx) {
  switch (Opcode) {
    // TODO: add case DXIL::OpCode::IndexNodeRecordHandle:
  case DXIL::OpCode::AnnotateHandle:
  case DXIL::OpCode::AnnotateNodeHandle:
  case DXIL::OpCode::AnnotateNodeRecordHandle:
  case DXIL::OpCode::CreateHandleForLib:
    // TODO: add custom validation for these intrinsics
    break;
  default:
    ValidateHandleArgsForInstruction(CI, Opcode, ValCtx);
    break;
  }
}
```

Unlike the first function, this default is not a no-op: every opcode not in the four
explicitly-excluded cases still gets `ValidateHandleArgsForInstruction`'s generic
handle-argument checks (uninitialized-handle and `GetResourceFromHandle` validation) run
against it. In practice this is closer to the issue's own second, cheaper alternative
("logically prove it will never be called on opcodes with no *Handle argument, and
comment why") -- except no comment records that reasoning, and no `DXAssert` was added
either, so the specific ask (an explicit signal, one way or the other) is still unmet
even though the default path does real, non-trivial work.

No `static_assert` or table-driven opcode-completeness check exists anywhere else in the
file as a substitute (`grep -n "static_assert"` in `DxilValidation.cpp`: no hits). The one
other opcode-switch `DXASSERT` in the file, `GetOpCodeName` at lines 2216-2234's
`default: DXASSERT(false, "Unexpected op code");`, is an unrelated small helper naming
only a handful of `HitObject_*` opcodes and is not one of the two functions the issue
names.

## Source history, scoped correctly, and a method caveat

`git log -S` scoped to actual ancestors of the ground-truth commit (i.e.
`git log ... 89e2f98e29c289ae8ad9e00dd310104fea9fd7df -- <path>`, **not** `--all`) shows
both the `ValidateDxilOperationCallInProfile` default-with-TODO and the
`ValidateHandleArgsForInstruction`/`ValidateHandleArgs` pair entering this repository's
ground-truth lineage together, as part of one very large commit that adds
`lib/DxilValidation/DxilValidation.cpp` as a single ~6390-line file
(`8a8b29f96`, "[spirv] AMD work graphs extension", #7353). 24 later commits between that
point and ground truth touch this file, all adding explicit new `case` labels for new
opcodes (the LinAlg/BFloat16/SM6.10 additions visible directly above the default block);
none touches the default case itself (`git log -p 8a8b29f96..89e2f98e2 -- ...cpp` shows
the TODO/default lines only ever appear as unchanged diff *context* around those
additions, never as `+`/`-`). So, **within this repository's own history**, the gap has
been present, unmodified, since the file entered the ground-truth lineage, through 24
subsequent opportunities to add exactly the missing coverage.

**Caveat, stated rather than silently resolved:** an unscoped `git log --all -S` search
finds superficially-plausible real-world-looking origin commits for this same code --
`4ade2fccc` (2018-06-20) for the `ValidateDxilOperationCallInProfile` TODO, and PR #5982
itself, `ceff9b8043d` (2023-11-08), for the `ValidateHandleArgs` split -- both of which
would place the code's origin appropriately before or around the issue's real filing
date. But neither commit is an ancestor of the ground-truth commit
(`git merge-base --is-ancestor 4ade2fccc... 89e2f98e2...` and the same check for
`ceff9b8043d` both exit 1), so they live on a disconnected branch/remote in this local
clone (it carries many remotes, e.g. `origin/cv_api`, `origin/damyanp/*`) and are not part
of the history that actually produced ground truth. Trusting `--all` here would have
manufactured a false, precisely-dated origin story. The corrected, ancestor-scoped
history above is coarser (one large synthetic commit rather than the real per-PR
history) but is the only claim actually supported by ground truth's own ancestry.
Nothing in this correction changes the verdict, which rests on directly reading the
current source, not on when it was introduced.

No commit message or PR title in the ground-truth ancestry references issue #5436 by
number.

## Verdict

The requested change has not been made. Both named functions' opcode dispatch still lets
an unmatched opcode fall through with no assert; `ValidateDxilOperationCallInProfile`'s
default carries only a TODO acknowledging the gap, and `ValidateHandleArgs`'s default
(functionally doing real generic validation) still has neither an assert nor a comment
justifying the omission. A maintainer independently raised the same concern in a PR
review four months after filing, and the reporter pointed back at this same issue as its
tracker -- it is a live, acknowledged, unresolved request, not one that has quietly
lapsed.

- **status**: `not-compiler-verifiable` -- no dxc invocation's output would differ based
  on whether this assert exists; the only available instrument is source reading, which
  is what this triage did.
- **repro-quality**: `prose-only`.
- **history**: n/a in the compile-history sense; source reading above establishes both
  named default cases are unchanged and open at ground truth.
- **suggested action**: `still-valid-keep-open` -- this is a live, unaddressed tech-debt
  request; nothing about it is resolved or contradicted by current source.
- **labels**: current (`enhancement`, `tech-debt`, `validation`) already describe this
  accurately; no change proposed.
- **text_stale**: not applied. The issue's own prose still accurately describes the
  current state of both functions (an empty/no-assert default case); nothing here
  contradicts it.

## Caveats

- This triage did not enumerate every `DXIL::OpCode` enumerator against the `case`
  labels in both switches to find a live example of a currently-unvalidated opcode
  slipping through silently today (that would be the distinct, harder claim "opcode X is
  unvalidated today," which the issue does not itself make; it asks for the *mechanism*
  to catch that class of bug in general, present or future). The absence of the requested
  assert is establishable directly from the two switch bodies quoted above without that
  enumeration.
- The local repository's commit history for this file does not reproduce the real-world
  per-PR chronology (see the method caveat above); dates attributed to source changes in
  this write-up come only from commits confirmed as actual ancestors of the ground-truth
  ID, and the live-GitHub facts (issue creation date, PR #5982 cross-reference) are
  sourced from the GitHub API independently of local git history.
