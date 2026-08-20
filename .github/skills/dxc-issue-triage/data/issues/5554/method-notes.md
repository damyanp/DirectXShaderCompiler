# Method notes — #5554 (batch-019)

Per-issue observations only; not applied to `SKILL.md` or `triage.py` from this session
(single-issue task, no shared edits).

## A release can register a new *reserved builtin name in the global namespace* and that is
## its own invalid-probe class, distinct from the documented "unknown profile / unsupported
## flag / undeclared identifier" markers.

`bisect --linear` on #5554 reported a clean `v1.8.2405` sandwiched between reproducing
releases on both sides — the classic fix-then-regress shape SKILL.md already warns needs
`--linear`, not binary search. But the "clean" result was itself an artifact: v1.8.2405 shipped
a builtin template literally named `integral_constant` (added for `vk::SpirvType` /
`vk::SpirvOpaqueType`, PR #6156) registered in the *default namespace* rather than a properly
scoped one, so any repro that happens to declare its own top-level `integral_constant` collides
and gets a completely unrelated "too many template parameters in template redeclaration"
diagnostic — which our `match.json` (correctly) does not recognize, so the release scores
`no-repro` rather than `invalid-probe`. That collision bug was itself fixed one release later
by PR #6700 ("Avoid adding types to default namespace"), which is why the diagnostic reappears
unchanged at v1.8.2407.

This is a new instance of a class SKILL.md documents ("`invalid-probe` on the repro is
ambiguous on its own; a feature-presence control resolves it" / "an ordinary diagnosed error ...
still scores repro" in the opposite direction) but not a case any existing marker in
`triage.UNSUPPORTED_MARKER_RE` would catch, because the collision is not about a missing
*feature* — the release supports everything the repro needs — it is about an unrelated,
now-fixed *name-collision* bug shadowing the question being asked. The fix here was local: pick
a repro identifier ("`integral_constant`", "`SpirvType`", ...) that cannot exist inside a
built-in reserved list of any probed release only by luck; there is no way to know that in
advance. What generalises: **when a non-monotonic bisect isolates a single-release "fix",
read that release's raw capture before accepting it, not just the classifier's verdict** — a
single word ("redeclaration") was enough to show this was not the same error at all. Whether
this is worth a generic classifier improvement (e.g., a heuristic that a diagnostic naming
"redeclaration"/"already declared" alongside a symbol matching the repro's own top-level
declaration is suspicious) is a question for collation; it would be the second sighting only if
another batch hits the same shape, which has not happened yet as far as this issue-local
session can tell.

## A godbolt Clang pane can retire a `check-in-clang` label question rather than motivate one

The duplicate #6706 already carried a maintainer statement predicting the successor Clang
front end does not have this gap. Running the `hlsl_clang_trunk` CE pane confirmed it
directly (clean compile, valid DXIL). SKILL.md's existing "do not add check-in-clang after the
comparison has already been run" guidance applied cleanly here — worth reinforcing at
collation as an example where the Clang pane's job was to *retire* a label question already
raised elsewhere in the thread, not to open one.
