> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4805](https://github.com/microsoft/DirectXShaderCompiler/issues/4805).

The core report — a custom `IDxcIncludeHandler`'s content is not what ends up
embedded as an included file's SPIR-V debug source — still reproduces today
on `main` (`89e2f98e2`). The specific 2022 crash does not reproduce as
originally described, and a different, more severe failure mode was found
during this triage that the original report did not describe.

## What's confirmed

A minimal custom `IDxcIncludeHandler` that serves one `#include` purely from
memory (no matching file on disk at all — the reported scenario) compiles
successfully, but the resulting container carries **no trace** of the
handler's content for that file's `DebugSource`. This isolates to
`EmitVisitor.cpp`'s `ReadSourceCode`, which does its own independent raw disk
read for debug-source text rather than reusing the buffer the supplied
include handler already returned to the parser — there is no fallback path to
the handler's content anywhere in that file.

A positive control (a real on-disk file byte-identical to what the handler
serves) does show the marker present, confirming the harness and the API path
both work, and that the reported case's absence is a real finding.

## The crash from 2022

Not reproduced. The disk-read failure has been wrapped in a `catch (...)`
since 2020 (predating this issue), and no build tested — including the
release current when this was filed — crashes on the reported scenario; it
compiles cleanly with the include's content silently missing from debug info.
This matches [@leozzyzheng's comment](https://github.com/microsoft/DirectXShaderCompiler/issues/4805#issuecomment-3552522826)
more closely than the original report: "ignored," not "crashes."

## A newly-found, worse failure mode

If a file happens to exist on disk at the resolved include path but with
*different* text than what the handler actually served (plausible for anyone
layering a custom handler over an otherwise-normal project tree — exactly the
use case described in this issue), the compile now **fails outright**:

```
fatal error: generated SPIR-V is invalid: NonSemantic.Shader.DebugInfo.100
DebugTypeMember: operand Column End (41) is larger then Line 3 column length
of 2 found in the DebugSource text
```

This does not happen on the release current when this issue was filed
(v1.7.2207) or as late as v1.8.2502 (2025-02) — only on `main`. The boundary
brackets PR #7662 (`97b5edbc4`, merged 2025-07-24, "Fix DebugSource for files
which are not found"), which narrowed a fallback that previously (silently,
incorrectly) substituted the *main file's* text for any file whose raw
disk-read failed. The narrowing looks correct in isolation, but it changed
this case from a quiet wrong-content substitution into a hard compile
failure.

## Suggestion

`ReadSourceCode` in `tools/clang/lib/SPIRV/EmitVisitor.cpp` needs to consult
the buffer the caller's `IDxcIncludeHandler` already supplied during parsing
for an included file's debug-source text, instead of (or before) doing its
own independent disk read. `debug info` might be worth adding alongside the
existing `bug`/`api` labels, since this is squarely a debug-info generation
defect.

Compiler Explorer was not used: its `dxc` panes can only drive `dxc.exe`'s own
disk-backed default include handler, so there is no way to exercise a
caller-supplied `IDxcIncludeHandler` through CE at all.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
