> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5704](https://github.com/microsoft/DirectXShaderCompiler/issues/5704).

Re-tested this against the reporter's own v1.7.2308 and against current
`main` (89e2f98e29c289ae8ad9e00dd310104fea9fd7df).

**The reported defect reproduced exactly as filed on v1.7.2308**: compiling
the repro to `lib_6_3` with `-Qstrip_reflect`, linking to `cs_6_3` with
`-Qstrip_reflect`, and disassembling shows both `texResource` and
`rwTexResource` still present.

**It is fixed as of v1.8.2403** (no stable release exists between v1.7.2308
and v1.8.2403 to narrow the window further). To measure this, the repro had
to be adapted: the reported function has no `[shader("compute")]` attribute,
and current `dxc` now gives an attribute-less, `numthreads`-only function in
a `lib_6_3` compile internal linkage, so it is dead-code-eliminated before it
can even be linked (`error: Cannot find definition of function main`). That
appears to be a separate, newer change from the reported bug, worth its own
issue if it isn't already tracked — it means today's `dxc` can't even run
your exact repro, let alone show the original symptom. Adding
`[shader("compute")]`, which the current front end requires regardless of
this issue, restores a working pipeline, and in that form `-Qstrip_reflect`
now correctly produces an empty resource name and an `undef` global in the
linked disassembly. A direct (non-library) compile strips cleanly on both
old and current builds, confirming the difference is specific to the
lib→link path this issue is about.

Suggested labels: no change — `bug`, `reflection`, `shader-linking` still
describe this correctly.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
