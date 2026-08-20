# Method notes — #5292 (batch-019)

For collation to consider promoting into `SKILL.md` / `triage.py`. Not
edited into shared files from this per-issue session.

## "Harness-as-COM-client instead of registering a harness-as-compiler" is a
   distinct pattern from the one already documented

`SKILL.md` documents "register the harness as a compiler" for a symptom
`dxc.exe` cannot reach (PIX passes via `IDxcOptimizer`). This issue needed
the same class of workaround (`dxr`'s `RewriteOption`-only flags, unreachable
from `dxc.exe`) but under a constraint that specifically forbade writing to
`.cache/compilers/` or the shared DB (a parallel-batch "no shared edits"
brief). The already-sanctioned fallback for that situation
("issue-local `measure.py --history`") worked cleanly and is worth
promoting to a first-class example next to the PIX one, since a per-issue
worker cannot always tell whether registering a new compiler counts as a
forbidden "shared edit" under a strict brief — an explicit worked example
(a ctypes wrapper around one COM entry point, reading the shared `releases`
table read-only for `--history`) would remove that judgement call.

## `RewriteWithOptions`'s argv convention differs from `main()`'s

`dxr.cpp` passes the *raw* process argv (program name at index 0) straight
into `RewriteWithOptions`, which builds its internal `MainArgs` with
`skipArgCount=0` — i.e. it does **not** skip the program name at this API
layer, unlike the `skipArgCount=1` convention used elsewhere in the
codebase for normal `main()`-style argv handling. Getting this wrong
produces a "multiple input files"-shaped parse error that looks like a
repro problem rather than a plumbing bug. Worth a one-line note in
`SKILL.md`'s `IDxcRewriter`/rewriter-tool guidance if that section grows
beyond the current PIX example, since the next issue against `dxr` will hit
this immediately.

## A reachability-analysis gap can be broader than what a reporter's pasted
   transcript shows, and the difference should not be over-read as reporter
   error

`VarReferenceVisitor` in `dxcrewriteunused.cpp` marks a type "used" only via
`VisitDeclRefExpr`/`VisitMemberExpr`/`VisitCXXMemberCallExpr`/
`VisitHLSLBufferDecl` — never by walking a retained function's own
parameter/return type, and never merely by a local variable's declaration
(only by a subsequent `DeclRefExpr` reading something of that type). This
meant the actual ground-truth output was *more* broken than the issue's
quoted "here is dxr output" (which still shows `struct VSOutput {};`) — no
measured release or main-debug retains it. This is recorded as an ancillary
finding rather than folded into the primary predicate, and the draft
describes the discrepancy neutrally (two measured facts side by side)
rather than diagnosing the reporter, per the existing "never diagnose the
reporter" guidance for `does-not-repro` verdicts — worth extending that rule
explicitly to "quoted output does not match every measured release" too,
since this is the same asymmetry in a different shape (a `repros` verdict,
not a `does-not-repro` one).

## Engagement-witness controls for a reachability/dead-code-elimination
   defect need a *read*, not a declaration

`control-typedef-used.hlsl` (declaring `PSPointOutput unused_local;` but
never reading it) was meant as a positive "this type is used" control and
instead reproduced the *same* removal as the primary repro — because a bare
declaration never triggers `AddRecordType` in this visitor; only an
expression-level reference to an *existing* declaration does. Worth noting
in `SKILL.md`'s engagement-witness guidance: for a removal/DCE-style
defect, an engagement control must include an actual *read* (a `DeclRefExpr`
to something already declared), not just a fresh declaration of the type
in question, or the control silently measures the same code path as the
defect and can be mistaken for a second confirmation of it.
