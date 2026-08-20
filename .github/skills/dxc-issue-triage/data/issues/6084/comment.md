> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#6084](https://github.com/microsoft/DirectXShaderCompiler/issues/6084).

This is a CI/pipeline request rather than a compiler-behaviour bug, so it was
checked against the pipeline definition rather than by compiling a shader.

At current `main` (`89e2f98e2`), `azure-pipelines.yml` has no `clang-cl` build
job at all — not even the release-only one the issue describes — and none of
the `.github/workflows/` files build DXC either. The `x64-clang-cl-*` presets in
`CMakeSettings.json` are local Visual Studio configurations, not something CI
exercises.

PR [#6107](https://github.com/microsoft/DirectXShaderCompiler/pull/6107) ("Fixes:
#6084") would have added this, including a follow-up commit toward "normal"
(non-release) builds as this issue asks for. It was never merged; it was closed
on 2026-01-22 by a maintainer as part of a stale-PR sweep ("has not been updated
in the last two years"), not because the change was rejected or done elsewhere.

So the request is still fully open: no clang-cl Windows build exists in CI today,
and the prior attempt to add one lapsed for inactivity rather than being
resolved. `enhancement` and `ci` both still look right; no label change
proposed.

---
<sub>Triaged with AI assistance. Findings were verified by reading the CI
pipeline definition at the cited commit and the public issue/PR history; please
flag anything that looks wrong.</sub>
