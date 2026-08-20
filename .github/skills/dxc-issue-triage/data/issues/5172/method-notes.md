# Method notes — #5172

## A shallow clone's graft boundary can make `--is-ancestor` answer a different question
than intended, without erroring

This repo is a shallow clone (`.git/shallow` names one boundary commit per fetched remote-tracking
ref). Checking whether an old, real commit (`6ee4074a4b43fa23bf5ad27e4f6cafc6b835e437`,
2016-12-28, the project's actual first commit, confirmed reachable via `--all` and via
`upstream`'s deep tag history) is an ancestor of the **local, shallow** `origin/main` returns
exit 1 ("not an ancestor") — but the command did not error, and the commit object resolves fine
via `git cat-file -t`. This is not the `#3038` trap (an unresolved ref causing a *different* kind
of failure); it is a graft-boundary artifact: `origin/main`'s shallow fetch is grafted at
`8a8b29f967b5925a970949984442b3783d730551` (2025-06-03), so nothing before that boundary is
locally an ancestor of `origin/main`, *regardless* of the real historical DAG. `git log -S ...`
found `8a8b29f...` as if it introduced the searched string, but `git show --stat` on it shows the
whole file as `new file mode 100644` — the graft's synthetic "everything starts here" artifact,
not a real edit.

The repo also carries a separately, more deeply fetched `upstream` remote whose old release tags
(`refs/tags/v1.4.1907`, etc.) retain real history back to the actual 2016 root. Checking ancestry
against one of those tags instead of the shallow `origin/main`/`upstream/main` gave the correct,
ungrafted answer (exit 0).

**Possible generalisation for SKILL.md**: the existing "verify by tree, not by SHA" guidance
covers a *rewritten* history; this is a *shallow-boundary* hazard and is a different failure
shape — the SHA is genuine and unchanged, but the checked ref's local reachability is truncated
at a graft point that has nothing to do with the real project history. A cheap discriminator
before trusting a negative `--is-ancestor` result on a suspiciously "first commit"-shaped or
very-old candidate: check `.git/shallow` for a graft boundary on the ref being checked against,
and if the repo has a deeper-fetched sibling remote (e.g. an old release tag under a second
remote), re-check ancestry against that instead before concluding the candidate is unrelated.
Not promoting this into SKILL.md myself (single-issue session; shared-file edits are collation's
job) — leaving it here per the parallel-batch rule.

## `--is-ancestor` on a "new file" graft commit found by `git log -S --all`

When a repo-wide `-S` search (used to date a string's introduction, per the #2952 lesson) turns
up a commit that shows the whole containing file as newly added (`git show --stat`), that is a
signal to suspect a shallow-fetch graft rather than a genuine introduction, especially when the
same search also returns an older, more plausible "first commit"/root-shaped candidate. Checking
`git show --stat <candidate>` for a whole-file add is a cheap way to catch this before dating a
symbol's introduction to the wrong commit.
