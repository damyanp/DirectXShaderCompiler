# #4307 — expected symptom

**Written before running any compiler.** Derived from the issue text only.

Issue: "Have a more explicit error when trying to use a struct member output interpolator as an
input", filed 2022-03-03 by `lamogui`. Label: `diagnostic`. One comment (2023-11-20,
`BartmanAbyss`) with a second, SPIRV-Cross-generated mesh shader showing the same thing.
No maintainer comment in the thread; no cross-reference events at all.

## What the issue actually asks for

This is **not** a "the compiler is broken" report. The reporter accepts that the construct is
rejected; the complaint is that the *diagnostic* is unhelpful. Quoting the body:

- Compiling the mesh shader with
  `dxc.exe main.hlsl /Zi /E"main" /Od /Fo test.mso /Tms_6_6 -Qembed_debug` produces

  > `main.hlsl:11: error: Function main with parameter is not permitted, it should be inlined. Validation failed.`

- The reporter says this "is not very explicit, in a huge shader I would really appreciate to
  have something like":

  > `main.hlsl:22: error: you use semantic output member m_value as an input which is forbbiden`

- Final paragraph: "The same kind of error happen when you use for instance
  `_vertices[ _sv_groupthreadid.x ].m_value` as a function parameter even if the parameter of
  the function is marked as **out**."

So there are **three** asks, and they should be scored separately:

| ask | what would satisfy it |
| --- | --- |
| A. the message should name the real problem | a diagnostic that says something about reading/using a mesh output member, instead of a generic "entry has a parameter" validation failure |
| B. the message should point at the offending line | a location on the offending statement (body line 22 in the reporter's numbering), not on the entry-point signature (line 11) |
| C. same for passing an output member to an `out` parameter | the same quality of diagnostic when the member is passed as a function argument |

## What "this reproduces" means

`repros` — the compile of the unmodified repro still fails with the **generic DXIL-validation
message** `Function main with parameter is not permitted, it should be inlined`, i.e. the
diagnostic quality the issue complains about is unchanged.

`does-not-repro` — the compiler now emits a source-level diagnostic that names the actual
problem (a mesh output member being read), i.e. the enhancement has been implemented.

`changed-behavior` — the compile still fails, but with a different message than the one quoted,
whether better or worse; or the compile now succeeds (which would mean the construct was made
legal rather than diagnosed, a different outcome from either of the above).

Because the request is for a *better message*, the interesting measurement is the **text** the
compiler produces today versus the text quoted in 2022, plus **where that text is emitted from**
(front end vs DXIL validator). A nonzero exit is expected and is not a crash: on Windows dxc
returns E_FAIL (0x80004005) for any diagnosed error, validation failures included.

## Predicate plan

`match.json` = the literal quoted validation text is present in the output. This is a positive
predicate, so the "absence predicate satisfied by a failed parse" trap does not apply; the
mirror hazard for a diagnostic-quality issue (#3055) does — a release that emits a *better*
diagnostic scores `no-repro`, which is exactly what "fixed here" looks like, and is correct.

Controls planned:
- **negative**: the same shader with the read-back of the output member removed. Must score
  `no-match` — proves the predicate is keyed to the construct under test and not to mesh
  shaders in general.
- **ask C**: the output member passed to an `out` parameter of a user function, to score that
  ask independently.
- an `-O3`/default-optimisation variant, to establish whether `/Od` is load-bearing for the
  message (the quoted text is about inlining, so this is not a safe assumption either way).

## Repro quality

`complete` — the issue body contains a self-contained shader and the exact command line. The
comment adds a second complete shader. Nothing has to be reconstructed.

## What would make this `not-compiler-verifiable`

Nothing: the whole subject is compiler output. But note that the *verdict* on an enhancement
request is not settled by "it still reproduces" — `enhancement-not-bug` remains available and
the deciding evidence is what the compiler says today and whether a maintainer has taken a
position (none has, in this thread).
