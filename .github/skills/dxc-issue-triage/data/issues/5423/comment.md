> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5423](https://github.com/microsoft/DirectXShaderCompiler/issues/5423).

Still reproduces on `main` (dxcompiler.dll self-reports commit `89e2f98e2`).

- `dxc -T ps_6_0 -E PSMain -D float4=0 repro.hlsl` still fails with
  `error: expected member name or ';' after declaration specifiers` — confirming `-D`
  expansion itself works fine. [Compiler Explorer](https://godbolt.org/z/GzETMvxvs).
- `dxr -D float4=0 -E PSMain repro.hlsl` still exits 0 with no error or warning and leaves
  `float4` unsubstituted. Same `-D`-ignoring behavior across all 20 cached stable releases,
  `v1.4.1907` through `v1.9.2607` (plain `-D float4=0 -E PSMain`), and, on the current build
  only, also with `-decl-global-cb` and `-line-directive` added.

Root cause: `tools/clang/tools/dxr/dxr.cpp` calls
`RewriteWithOptions(pSource, wName.c_str(), argv_, argc, nullptr, 0, ...)` — it always passes
`nullptr, 0` for `RewriteWithOptions`'s separate defines parameter. `-D` is parsed into
`opts.Defines` from `argv_` inside that call, but the parsed value is never forwarded to the
rewrite functions (`DoRewriteGlobalCB`, `DoReWriteWithLineDirective`, `DoSimpleReWrite`), which
use only the always-empty `pDefines`/`defineCount` pair.

#5424 already implements the fix (pass `opts.Defines.data()/size()` at those three call
sites) and adds a FileCheck test matching the diagnostic above. It was never merged — a
reviewer raised an open design question about interactions with `#ifdef`-driven
`-remove-unused-globals` (see #4357), and the thread stopped there; the PR was closed in 2026
as inactive, not as rejected.

Suggest keeping this open pending that product decision, rather than closing as fixed or
stale.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
