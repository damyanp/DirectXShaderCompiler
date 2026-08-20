# Method notes -- #5115

For collation to review; per-issue sessions do not edit `SKILL.md` or `scripts/`.

## Ground-truth provenance verification worked exactly as documented

`main-debug` self-reports commit `7665270b9` / branch `triage`, not the registered
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`. This is the documented "verify by tree, not by
SHA" situation (SKILL.md, "The ground-truth compiler must be a clean Debug build"): the local
build is on the triage working branch, which carries this skill's own data on top of the cited
upstream commit. The controlled-diff check worked as prescribed:

```
git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df   -> 0 files outside .github/skills/dxc-issue-triage/
git diff --name-only 7665270b9 13730886e6a9019e4e0823746470f3ab75341d6b  -> 33 files outside .github/skills/dxc-issue-triage/ (control)
```

No new observation here -- just confirming the documented procedure is sufficient and worked
cleanly on the first try, including finding a usable "older" commit for the control from
another compiler row already in the `compilers` table (`main-debug-rw` /
`13730886e6a9019e4e0823746470f3ab75341d6b`) rather than trying to walk parents of a
shallow-fetched upstream commit (`89e2f98e2^` fails locally with "unknown revision" -- the
fetched commit has no local parent history, which is expected for a single-commit fetch and is
not itself a problem, but a worker who doesn't already know an older reference to diff against
would need to be told where to find one; the `compilers` table's `git_commit` column is exactly
that source, and it's not obvious from a first reading of SKILL.md that it doubles as a
control-diff source of older SHAs).

## `godbolt --source` cleanly supports a second, throwaway comparison pane without losing evidence

Publishing a control shader (`control-genuine-ambiguity.hlsl`) via `godbolt --source` to check
that Clang's overload resolution isn't merely permissive, then re-publishing the primary repro
afterward to restore the "canonical" link, worked exactly as SKILL.md describes: the
content-hashed archive (`manual-case-godbolt-verify-<hash>.txt`) preserved both the
primary-repro panes and the control panes with nothing lost, and no evidence needed
hand-editing. No method gap found here -- flagging it only because it is a positive
confirmation of "Re-running godbolt with different panes no longer destroys the previous
evidence," which the doc states but which this issue is (as far as I can tell from a read of
`data/issues/*/manual-case-godbolt-verify*.txt` file listings) among the first to actually
exercise deliberately, rather than only via an accidental re-run.

## A Clang-side "already fixed" finding needed a second, self-authored control

`godbolt`'s built-in `--expect` control is issue-agnostic (single shader, single compiler); it
does not have a way to assert "this cross-compiler diagnostic difference is a real fix, not a
generic Clang permissiveness gap" without a second, hand-designed input. Nothing to promote
into the tool here -- SKILL.md's step 7 warning ("A Clang error is not evidence until you have
a control" / "confirm the difference does not survive") already anticipates exactly this and
was sufficient to design `control-genuine-ambiguity.hlsl` (a call that is ambiguous even under
real C++ rules) without further guidance. Recording only because it is the mirror case of the
documented warning -- that one is about a spurious Clang *error*; this one is about a spurious
Clang *silence* -- and both were resolved by the same "compile something whose correct answer
you already know" technique.

## No parallel-batch friction observed

`git status` at the end of this session shows several sibling issue directories
(4766/4786/4792/4805/4858/4871/4888/4914/4958/4965/5039/5040/5059/5064/5072/5079/5080/5116)
already untracked in the working tree from concurrent batch-019 workers, plus a handful of
pre-existing modified `issue.json` files (2128, 2427, 3092, 3150, 7033, 8732, 8737) that this
session did not touch. `scripts/` and `SKILL.md` show no changes from this session. This is
consistent with the documented single-writer discipline holding under real parallelism; `git
status` scoped to `.github/skills/dxc-issue-triage/data/issues/5115/` shows only this issue's
new files, and `check_paths.py`'s findings are entirely inside other issues' directories, not
this one.
