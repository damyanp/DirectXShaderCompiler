> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5172](https://github.com/microsoft/DirectXShaderCompiler/issues/5172).

Still an open gap on current `main` (`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
`1.9.0.5465`). `IDxcIndex::ParseTranslationUnit`'s parameter list
(`include/dxc/dxcisense.h:802-808`) still has no per-request include callback like
`IDxcIncludeHandler` — the only related parameter is `IDxcUnsavedFile **unsaved_files`, and the
implementation (`tools/clang/tools/libclang/dxcisenseimpl.cpp`) still binds unconditionally to a
disk filesystem otherwise.

A small harness confirms the gap on this build, same DLL, same repro:

```
[pti-absent]   file removed, no unsaved-file override  -> "'myinclude.hlsli' file not found"
[pti-unsaved]  file removed, pre-declared via IDxcUnsavedFile -> resolves (0 diagnostics)
[compile-handler] IDxcCompiler::Compile, file removed, served only by a custom
                  IDxcIncludeHandler -> handler invoked once, content served with zero
                  disk backing
```

`IDxcUnsavedFile` is the only substitute `ParseTranslationUnit` has, and it is static: content
must be pre-declared under its exact path before the call, not served per-request the way
`Compile`'s `IDxcIncludeHandler::LoadSource` is. The last case shows that same dynamic callback
genuinely working on this build's `Compile` — confirming the gap is specific to
`ParseTranslationUnit`, not a general limitation.

This behaviour predates the issue: the disk-only implementation and its "TODO: until an
interface to file access is defined" comment trace back to the project's original 2016 commit,
confirmed as an ancestor of `v1.4.1907` (2019-08-30) — unchanged since.

@llvm-beanz's 2023-07-13 comment still reads as the project's position: unlikely to be
prioritized, patches welcome, and the longer-term direction is to retire the IntelliSense
interface in favor of upstream LSP-based tooling rather than extend it with this mechanism.
Nothing here contradicts that.

Suggest adding `api` (currently only `enhancement`).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
