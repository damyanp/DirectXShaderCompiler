## #5436 -- `git log --all -S` can find disconnected-branch commits that are not ancestors
of the ground-truth commit, and their dates can look deceptively real-world-plausible.

While dating the origin of the two functions this issue names
(`ValidateDxilOperationCallInProfile`'s default-case TODO,
`ValidateHandleArgsForInstruction`/`ValidateHandleArgs`), `git log --all -S <text>`
returned commits (`4ade2fccc`, 2018-06-20; `ceff9b8043d` / PR #5982, 2023-11-08) whose
dates line up neatly with real-world DXC history and with this issue's own filing date --
plausible enough that I initially wrote them into `notes.md` as the origin story before
double-checking. Neither commit is actually an ancestor of the ground-truth ID
(`git merge-base --is-ancestor <sha> 89e2f98e29c289ae8ad9e00dd310104fea9fd7df` exits 1 for
both), even though `git merge-base --is-ancestor 89e2f98e2... HEAD` succeeds and the
non-skill tree is provably identical between the registered build commit and ground
truth. This repo clone carries many unrelated remotes (`origin/cv_api`,
`origin/damyanp/*`, etc.), and at least for `lib/DxilValidation/DxilValidation.cpp` the
ground-truth-ancestor history is a large synthetic reconstruction: one ~6390-line commit
(`8a8b29f96`, "[spirv] AMD work graphs extension", #7353, dated 2025-06-03 in this
repo's clock) adds the entire file, including both switches' still-empty default cases,
well after this issue's real 2023 filing date -- the opposite ordering from what the
`--all` search suggested.

**The check that catches this:** scope every `git log -S`/`git log -p` history query used
for dating source changes to the ground-truth commit itself
(`git log ... <ground-truth-sha> -- <path>`), not `--all` and not bare `HEAD`, and verify
with `git merge-base --is-ancestor <found-sha> <ground-truth-sha>` before writing any
commit into a triage write-up as "the origin". A plausible date is not evidence of
ancestry. This is a variant of the skill's existing rewritten-history warning
("Verify by tree, not by SHA"), but the failure mode here isn't a rewrite of the same
line of history -- it's multiple genuinely different lines of history (real remotes)
coexisting in one local clone, where the wrong one is trivially reachable by `--all` and
looks completely ordinary until ancestry is checked.
