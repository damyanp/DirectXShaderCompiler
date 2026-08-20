> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5848](https://github.com/microsoft/DirectXShaderCompiler/issues/5848).

Tried to reproduce this from the code in the report against current
`main` (`89e2f98e2`) and against the exact build named here, `1.7.2308.7`.
Neither produces the described warning.

The reconstruction follows the snippet as closely as it can: `ddxRay`/
`ddyRay` are written in `RaygenShader` (both a member-wise and a
whole-struct cast-assignment version were tried), and `TraceRay` is
invoked one function away, through a helper like `TraceRadianceRay`. On
both compilers this compiles clean, with no `-Wpayload-access-trace`
warning at all.

Reading `SemaDXR.cpp` explains why, and it isn't the reported false
positive — it's the opposite problem. `raygeneration` shaders are given
a null `Info.Payload` (raygen has no incoming payload parameter, only a
local variable), and the entire "field never written for TraceRay call"
check — including the recursion needed to look inside a helper function
— is gated on `Info.Payload` being non-null. So for any `TraceRay` call
reached through a helper from raygen, that check never runs, whether or
not the fields are actually written. A [genuinely broken
control](https://godbolt.org/z/d1a7E9Mxj) (fields never written anywhere,
`TraceRay` called through the same kind of helper) confirms this: it
compiles silently on `dxc_trunk` too, where the same violation with a
*direct* `TraceRay` call does get diagnosed correctly.

So the snippet in this issue, reconstructed as written, doesn't produce
a false positive on either build — it produces no diagnostic at all,
correct or not. That could mean the real project code differs from the
snippet in some way that matters, or that the warning came from a
different configuration. Without the minimal repro requested above,
there isn't enough to tell which.

Suggest `needs repro steps` (a minimal, buildable case would settle
this) and `diagnostic`, alongside the existing `bug`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
