> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4629](https://github.com/microsoft/DirectXShaderCompiler/issues/4629).

Still reproduces on `main` (1.9.0.5433, `13730886e`). The filed command also
reproduces; the release-history scan used `ps_6_0` without `-HV 2021` after
controls showed those flags do not change the failing stack.

The Debug build stops at:

```
Assertion failed: !(onlyUsedByLifetimeMarkers(BCI))
  "expected struct bitcast to only be used by lifetime intrinsics"
  lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp(2630)
```

Under `NDEBUG`, that check disappears and the same value reaches the
`cast<IntrinsicInst>` two lines later:

```
error: llvm::cast<X>() argument of incompatible type!
```

All 20 stable releases fail on this shader. Eighteen fail internally: 17 emit
the reported cast message and v1.6.2104 access-violates. The two oldest,
v1.4.1907 and v1.5.2010, instead run for 240 seconds with no output while
using one full CPU core; a trivial shader compiles on both in 0.3 seconds.

The trigger is the shader shape: a derived class adds a field and implements
an interface over a base class that also has a field. Removing the interface
from the inheritance list compiles on every release tested.

[Compiler Explorer](https://godbolt.org/z/KcoeM9sra) shows DXC 1.6.2112 and
trunk failing. The Clang pane rejects the `interface` keyword at parse time,
so it does not test this SROA defect.

`bug` and `crash` remain appropriate. `hlsl-next` is worth considering because
hlsl-specs#291 proposes removing `interface`; that makes the disposition a
language decision as well as a codegen one.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
