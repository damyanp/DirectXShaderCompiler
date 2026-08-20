# Method notes -- #5448

**A "reorganize this code" tech-debt issue has a concrete, checkable claim
even without a `dxc.exe` repro: whether the described structure still exists
in the current source.** #5448 asks for a rename/refactor
(`GetResourceFromHandle` -> validation-only `ValidateResourceHandle`,
downstream callers switched to `GetResourceFromVal`+`isValid()`). That claim
is falsifiable by reading the file at ground truth, exactly like an
API-absence claim (cf. #5175): if the rename had happened, grepping for the
old name or the described double-call pattern would come back empty. It
did not.

**`git log --all --oneline -i --grep=<name>` is a cheap, decisive check for
"has anyone ever done this refactor."** Zero hits across the whole history
(including for the issue number itself) is strong corroboration alongside
reading the current source, and costs four commands.

**Even a pure-refactor issue can still name one observable, testable
consequence -- and it's worth trying to build that repro before writing off
the issue as `not-compiler-verifiable`.** #5448's duplicate-diagnostic claim
is in principle a dxc.exe-observable symptom (two identical errors for one
bad handle). It turned out unreachable from ordinary HLSL, but only after
trying: DXC's own legalizer already rejects the one HLSL-level construct
(a dynamically-selected resource handle) that could produce the malformed
`Value` the validator's bad-handle path needs, with a fast, cheap control
probe (`control-dynamic-handle-select.hlsl`, exit 0x80004005, an ordinary
diagnosed error). Recording that control cost one probe and turns "no repro
possible" from an assumption into a measurement, per SKILL.md's control
discipline. Reaching the validator's own code path would require
hand-authored malformed DXIL run through the standalone `dxv` validator,
which is not built in this environment; building it would be a new shared
build target, which this task's constraints (no rebuilds) rule out.

**Filing-time context worth checking for any `tech-debt` issue with zero
comments: is it a same-day self-follow-up to the reporter's own merged PR?**
`gh pr view <N> --json mergedAt,state` plus the issue's own `createdAt` from
`fetch` settled this in two calls (#5399 merged 2023-07-22T01:06:04Z, #5448
filed 2023-07-22T01:12:41Z) and explains why the issue has no comments or
maintainer discussion to check the text against -- it is the reporter noting
scope they deliberately left out of their own PR, not an independent bug
report that might have been triaged or discussed elsewhere.
