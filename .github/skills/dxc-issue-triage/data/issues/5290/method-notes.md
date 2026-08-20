# Method notes from #5290

Observations for collation. Nothing here is a claim about #5290 itself --
that is in `notes.md`. This issue is the third in batch-019 to exercise the
standalone `dxr` rewriter, alongside #4273 (an earlier batch) and #5255
(same batch, triaged earlier in the same session).

## 1. A footnote in a sibling issue's `notes.md` predicted this issue's headline defect

#5255's `notes.md` (same batch, same session, triaged first) has a section
titled "An unrelated second gap, not scored by `match.json`" that reads:

> the entry function's own parameters are never marked as "used types"
> unless a field of the parameter is dereferenced in the body... Nothing in
> `CollectRewriteHelper` walks `entryFnDecl->parameters()` to mark their
> types used.

That is #5290's ask 1, word for word, discovered as a side observation while
triaging a different issue (#5255's own headline defect is unrelated: a
struct used as a cbuffer *array* member). Per the skill's rule ("A worker
that finds itself wanting to say 'this is the same as #NNNN' should say so
in `method-notes.md` and leave the draft silent"), this is recorded here
rather than in #5290's `comment.md`/`verdict.json` -- collation is where two
independently-reached findings about the same code path should be
cross-checked and, if warranted, linked. Concretely: is #5290 a duplicate of
#5255, or a separate issue that happens to share one root-cause class with
it? #5255's own title and reported symptom are about cbuffer array members,
not entry-point parameters, so treating #5290 as a straight duplicate would
likely be wrong -- but the two share enough of the underlying code path that
a maintainer fixing one should be pointed at the other. Left as a collation
judgement call, not asserted in either issue's draft.

## 2. Two reported "bugs" in one issue turned out to be one root cause

Decomposing the issue's two asks (per the skill's guidance) into separate
`match.json`/`match-nested.json` predicates and separate controls was the
right mechanical move, but it was worth then asking whether the two asks are
actually independent defects. Code reading showed they are not: both trace
to the same gap in `VarReferenceVisitor` (declaring/casting to a type is not
itself treated as "using" it; only a later `DeclRefExpr` referencing an
already-declared variable is). Suggestion for future rewriter issues: when
an issue's second ask looks structurally similar to its first (same tool,
same kind of "declared but not referenced" shape), check for a shared root
cause via code reading *before* concluding two independent defects need two
independent fixes recommended in the draft. Here it changed nothing about
the verdict (both still score `repros`, `always-repro'd`), but it does
change what a maintainer should expect from a single patch: fixing
`entryFnDecl->parameters()` traversal and fixing local-`VarDecl`-declaration
traversal are naturally the same code change (both are "a `Decl` being typed
without a `DeclRefExpr`"), not two separate patches.

## 3. `git log --all -S "parameters()"` as a cheap "was this ever handled" check

Before asserting "the rewriter never walks the entry function's own
parameters", `git log --all -S "parameters()" --
tools/clang/tools/libclang/dxcrewriteunused.cpp` (repo-wide, not path-scoped
to avoid the #2952 current-path trap noted in `SKILL.md`) returned **zero**
commits touching that call in this file, across the entire history. That is
stronger evidence than reading the current `HEAD` alone: it rules out "this
was handled once and regressed" as well as "never handled". Worth reaching
for whenever a `notes.md` draft is about to say a code path "was never
walked" -- the claim is cheap to falsify and expensive to get wrong.

## 4. Reused #5255's `dxr`-as-harness machinery verbatim, and it held up cleanly

`main-debug-rw.json`'s registered Debug `dxr.exe` is stale (points at a path
that no longer exists after this checkout's Debug tree was rebuilt for `dxc`
only). #5255 solved this by registering `dxr-5255-release` against the
already-present, untouched `build/Release/bin/dxr.exe` (self-reporting the
exact ground-truth commit `89e2f98e2`) rather than rebuilding. This issue
registered a second, non-colliding id (`dxr-5290-release`) against the same
binary and reused #5255's `measure.py` staging pattern
(`.cache/rw5290/<tag>/`, dxr.exe copied beside each release's own
`dxcompiler.dll`) essentially unchanged, generalised to six probes instead of
four (two ask/control pairs instead of one). No new tooling gap found here;
this is a confirmation that the #4273/#5255 pattern generalises cleanly to a
second, structurally similar rewriter issue.
