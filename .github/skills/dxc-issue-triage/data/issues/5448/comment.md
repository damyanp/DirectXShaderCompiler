> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5448](https://github.com/microsoft/DirectXShaderCompiler/issues/5448).

Confirmed still current on `main` (`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`):
`GetResourceFromHandle` (`lib/DxilValidation/DxilValidation.cpp`) still both
looks up resource properties and emits `InstrHandleNotFromCreateHandle` as a
side effect, and `GetSamplerKind`, `GetResourceKindAndCompTy` and
`GetCBufSize` still all call it rather than the silent `GetResourceFromVal`.
Since the up-front handle-argument pass from #5399 and these per-op
accessors both run against the same operand with no early return between
them, an invalid handle reaching e.g. `GetDimensions` can still emit
`InstrHandleNotFromCreateHandle` twice. No `ValidateResourceHandle`
function exists, and `DxilResourceProperties::isValid()` is never called
from the validator — every call site still hand-repeats
`getResourceClass() == Invalid`.

Worth noting: `ValidateASHandle` (for `TraceRay`'s acceleration-structure
handle) already uses exactly the pattern this issue asks for everywhere —
`GetResourceFromVal` plus a manual validity check and a single specific
diagnostic — so both styles already coexist, and the target pattern is
already proven out in this file.

No `dxc.exe` command line or Compiler Explorer link is included: this is a
request to reorganize validator source, and the one observable consequence
(a duplicate diagnostic) needs a resource handle that isn't a recognised
`CreateHandle` result reaching a resource op. Ordinary HLSL can't construct
that — dxc's own legalizer rejects a dynamically-selected resource handle
(`local resource not guaranteed to map to unique global resource`) before
DXIL validation ever runs, confirmed directly against a control shader that
selects between two `Texture2D` locals.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the
repro; please flag anything that looks wrong.</sub>
