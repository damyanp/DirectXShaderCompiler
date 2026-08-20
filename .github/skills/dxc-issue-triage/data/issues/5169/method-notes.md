# Method notes — #5169

Scoped to this issue only. No shared files (`SKILL.md`, `scripts/`) were
touched.

## Ground-truth verification performed for this issue

Registered `main-debug` compiler already existed
(`.cache/compilers/main-debug.json`), with `git_commit` recorded as
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df` — the exact commit named in this
task's brief. I independently re-verified rather than trusting the cached
record:

- `dxc --version` on `build\Debug\bin\dxc.exe` prints
  `dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage,
  7665270b9)` — matches the cached `version` field exactly (no version-header
  staleness).
- `git merge-base --is-ancestor 89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD`
  → exit 0.
- Fetched `upstream/main` (`microsoft/DirectXShaderCompiler`) and confirmed
  `git merge-base --is-ancestor 89e2f98e... upstream/main` → exit 0, i.e. this
  is a real public upstream commit, not a fork-local rewrite.
- Tree-equivalence: `git diff --name-only 89e2f98e... HEAD -- .
  ':(exclude).github/skills/dxc-issue-triage'` is **empty**. Control:
  `git diff --name-only HEAD~50 HEAD -- . ':(exclude)...'` returns 97 files,
  proving the query can detect a real difference when one exists. So the
  current working tree/HEAD is source-identical to the named public commit
  outside the triage skill directory, which is what makes `HEAD` usable as
  `89e2f98e...` for citation purposes.
- I did **not** rebuild `dxc`; the existing `build\Debug\bin\dxc.exe`
  (timestamp 2026-08-18 20:36) already matches this commit's tree and its
  self-reported version string, so no rebuild was needed or performed.

I noticed the cached `main-debug.json`'s `provenance_note` field still says
the binary self-reports `ab5400907` — a stale value from an earlier
registration; the current binary actually self-reports `7665270b9` (visible
in the `--version` output above) and the `git_commit` field itself already
correctly says `89e2f98e...`. I did not edit `.cache/compilers/main-debug.json`
(shared cache state, out of scope for a per-issue session) — flagging it here
only so collation can decide whether to refresh that one field.

## Issue-specific method observation: `git log -S` over renamed/merged files
overcounts, and restricting `git show` to explicit paths hides rename
detection

This issue is a pure "does the header still lack the enum value" question, so
its evidence is source citation rather than a `dxc` probe — worth flagging
because it is a shape this skill's checklists (built for compile-probe
issues) do not cover: there is no `cmd.txt`, no `match.json`, and no `run`
capture for this issue's directory, by design (see `expected.md` and
`evidence-source-citations.txt` for why).

While building the citation, `git log --all -S"D3D_SVC_BIT_FIELD" -- <two
paths>` returned **three** commits, and my first draft of the evidence
mis-described this as "two commits, `5cadb2589` and `8a8b29f96`" — silently
dropping `daf138616` (#5232). This was flagged by the step-10 model review's
arithmetic check (comparing the notes' count against the evidence file's own
`git log` output) and confirmed by re-running the underlying commands. Root
cause: `daf138616` is a pure rename (`git show --stat daf138616
--find-renames` reports `0` insertions/deletions for the file) of
`tools/clang/unittests/HLSLTestLib/D3DReflectionStrings.cpp` to
`lib/DxilContainer/D3DReflectionStrings.cpp`, and `8a8b29f96` is a
single-parent (non-merge) commit whose diff against its immediate parent
shows both files added in full, because that parent predates them on
whatever branch history was integrated — neither is a real content edit, but
both satisfy `-S` because path-restricted `git show`/`git log -S` does not
apply rename detection the way an unrestricted `git show <commit>` does (the
unrestricted `--stat` for the same commit reports the rename as `0`/`0`,
while the path-restricted view of the *destination* path shows the full
content as freshly added "+" lines).

**Takeaway for a future citation of "this text was introduced/only ever
touched by commit X":** when `git log --all -S<token>` returns more than one
commit for what is expected to be a single introduction, check
`git show --stat <commit>` (unrestricted, so rename detection applies) for
each hit before asserting a commit count in a draft — a renamed or
merge-integrated file can inflate the count without the underlying text ever
having been edited. This generalises the existing "cherry-picked commit has
two SHAs" caution in `SKILL.md` step 11 to renames and branch-integration
commits, not just cherry-picks. I have not promoted this to `SKILL.md`
myself — that is collation's call, and it may already be adequately covered
by the existing cherry-pick note; flagging for collation to decide whether it
is a distinct-enough trap to add explicitly.

## Step-10 review

As a diligence check I ran a different-model review (`gpt-5.3-codex`) of
`notes.md`, `comment.md` and `evidence-source-citations.txt` against
SKILL.md's step-10 criteria. It correctly flagged a real "two commits"
miscount in the first draft (see the git-history section above — accepted
and fixed) and several concision points (accepted with light editing, since
some of its proposed literal replacement text dropped context needed to keep
the surrounding sentence accurate; I applied the substance of each accepted
suggestion rather than pasting its wording verbatim in every case). It found
no speculative-diagnosis language and no issues with the quoted source text
or the disclosure trailer.

Per this batch's explicit instructions, `reviewed_by` is left **unset**
(`verdict --reviewed-by ""`) rather than stamped with the model above: the
formal step-10 review is a batch-level activity that runs once over every
draft in batch-019, and this per-issue session does not own that gate. The
review recorded here should not be read as a substitute for that batch
review — it is retained only because it already surfaced and fixed a real
defect (the commit miscount), and removing that record would make the fix
look unmotivated.
