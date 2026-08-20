# Expected symptom — #5172 "IDxcIndex::ParseTranslationUnit has no mechanism to honor an IDxcIncludeHandler"

*Process note, stated honestly per SKILL.md step 2: this file was written **after** the
source inspection and the harness (`isense5172.cpp`) had already run, not before, which is a
deviation from the prescribed order. It is written now because the skill treats `expected.md`
as write-once and requires reconciling any discrepancy explicitly rather than silently
rewriting the criterion. There is no discrepancy to reconcile: the prediction below is the
same unambiguous claim implied by the issue and the maintainer's own 2023 reply, and every
harness/source result recorded in `manual-case-isense5172.txt` and
`manual-case-source-evidence.txt` matches it. Recording it now, rather than not at all, is the
honest option available.*

Reporter: `jeremyong` (Jeremy Ong), 2023-04-23. Label: `enhancement`.
Maintainer comment: `llvm-beanz`, 2023-07-13.

## What the issue claims

1. `IDxcCompiler::Compile` accepts a caller-supplied `IDxcIncludeHandler*`, which is invoked
   per `#include` and can serve content that does not exist on disk.
2. `IDxcIndex::ParseTranslationUnit` (the libclang-style IntelliSense/indexing API) has **no**
   such parameter and instead uses `llvm::sys::fs::MSFileSystem` (per `dxcisenseimpl.cpp`)
   — i.e. it can only resolve includes from the real filesystem.
3. The reporter asks whether the same filesystem-proxy mechanism used by `Compile` could be
   leveraged for the IntelliSense interface too.
4. The maintainer's reply (2023-07-13): unlikely to be prioritized — the project's long-term
   goal is to move away from the IntelliSense interface **entirely**, in favour of upstream
   LSP-based tooling, not to extend it. Patches would be accepted. Separately, `MSFileSystem`
   itself will not be ported into the eventual Clang-based front end; Clang's own VFS
   abstractions will be used there instead.

## What "this reproduces" means

This is a capability-absence claim about a public COM interface, not a shader defect, so there
is no `dxc.exe` command line whose output can affirm or refute it (per SKILL.md step 5's
guidance for absence-from-surface-API claims, direct interface/emitter inspection plus a
contrasting compiler path is the strongest evidence, stronger than any single shader probe).
`repros` here means **all** of the following still hold against the pinned ground-truth build:

* **S1 — no parameter exists.** `IDxcIndex::ParseTranslationUnit`'s declared signature (in
  `include/dxc/dxcisense.h`) has no `IDxcIncludeHandler` (or any other virtual-filesystem)
  parameter, in contrast to both `IDxcCompiler::Compile` and `IDxcCompiler3::Compile`, which do.
* **S2 — the implementation is disk-only.** The implementation in
  `tools/clang/tools/libclang/dxcisenseimpl.cpp` unconditionally constructs
  `CreateMSFileSystemForDisk()` with no caller-supplied alternative, and still carries the
  original "TODO: until an interface to file access is defined" comment.
* **S3 — no dynamic substitute exists.** The one documented workaround
  (`IDxcUnsavedFile`, exercised by DXC's own `DXIsenseTest.cpp`) is a static, pre-declared,
  exact-literal-path array supplied once at `ParseTranslationUnit` call time — not a per-request
  callback — so it cannot serve content whose path is not already known in full.
* **S4 — the gap is real relative to a compiler that has the callback.** `IDxcCompiler::Compile`
  (or `IDxcCompiler3::Compile`) can be shown, on the same build, invoking a caller's
  `IDxcIncludeHandler::LoadSource` dynamically, with zero disk backing for the served content —
  demonstrating the exact mechanism `ParseTranslationUnit` lacks is not a general engine
  limitation, only a gap in this one entry point's surface.

`does-not-repro` / fixed = `ParseTranslationUnit`'s signature (or a sibling overload) now
accepts a caller-supplied include/VFS handler and the implementation honours it dynamically.

`changed-behavior` = a partial closing of the gap that stops short of a real dynamic callback —
e.g. a richer static pre-declaration mechanism, still not equivalent to `Compile`'s handler.

Repro quality (recorded honestly, after the fact per the note above, but reflecting the
category the evidence turned out to need): **agent-constructed** — no HLSL shader repro is
provided or applicable; the evidence is a from-scratch COM harness
(`isense5172.cpp`) plus direct source/history inspection, in the same style as #2604's
API-surface investigation.

## Why the compiler binary alone (a single `dxc.exe` probe) is not the instrument

No `-T`/`-E` command line can show the absence of a parameter from a COM vtable. `match.json`
and `cmd.txt` are deliberately not present for that reason (SKILL.md step 5's explicit
allowance); the evidentiary artifacts are `isense5172.cpp`/`measure-5172.py` and their captured
output instead.

## Known limitations to state up front

* This is a maintainer-already-answered enhancement request, not a bug; the expected suggested
  action is `enhancement-not-bug`, matching #2604's precedent for a similar API-surface gap.
* The maintainer's stated direction is not "extend `ParseTranslationUnit`" but "replace it with
  LSP-based tooling" — a fix in the shape the reporter asked for (route through the same
  filesystem-proxy mechanism as `Compile`) is explicitly not the direction the project intends
  to take, independent of priority.
* History here is not release-bisectable in the usual sense (no shader regression to walk);
  "history" is instead the file's provenance — see `manual-case-source-evidence.txt` for the
  dated evidence that this TODO/behaviour predates the issue by years and is unchanged in the
  pinned ground-truth build.
