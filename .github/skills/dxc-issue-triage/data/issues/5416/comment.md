> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5416](https://github.com/microsoft/DirectXShaderCompiler/issues/5416).

Still reproduces on `main` (commit
[`89e2f98e2`](https://github.com/microsoft/DirectXShaderCompiler/commit/89e2f98e29c289ae8ad9e00dd310104fea9fd7df)).

Your exact command line, run against an ordinary valid `lib_6_7` shader: exits 0, prints
nothing, writes `source.d`, and never writes `source.cso`. Without `-MD -MF` the same shader
compiles to a normal object file.

Root cause, in `DxcContext::ActOnBlob` (`tools/clang/tools/dxclib/dxc.cpp`):

```cpp
if (m_Opts.DumpDependencies) {
  // ...writes the depfile...
  return retVal;                    // <-- returns here
}
// Write the output blob.
if (!m_Opts.OutputObject.empty()) { // <-- -Fo is handled here, never reached
```

Any of `-M`, `-MD`, `-MF` makes the compiler take a preprocess-only path and return
immediately after writing the depfile, before the `-Fo` write ever runs — regardless of whether
the shader is valid. This has been the case since `-M`/`-MD`/`-MF` were added
([#4017](https://github.com/microsoft/DirectXShaderCompiler/pull/4017), Dec 2021): every stable
release since (`v1.7.2207` through `v1.9.2607`, 15 releases) reproduces it, plus a local
`main-debug` build, with zero clean releases in between. Releases before that reject `-MD` outright with `Unknown argument: '-MD'`.

Compiler Explorer's `dxc_trunk` shows the same thing on the identical command —
`<No output file>` at exit 0:
https://godbolt.org/z/3jn1eM9K4

This is a different visible symptom from the same code path as
[#5117](https://github.com/microsoft/DirectXShaderCompiler/issues/5117) (which loses a
diagnostic for *invalid* source under `-MD`/`-MF`) — fixing that one wouldn't by itself restore
the `-Fo` output here, since the early return happens unconditionally. It's also distinct from
[#4723](https://github.com/microsoft/DirectXShaderCompiler/issues/4723), which is specifically
about `-MD`/`-MF` combined with `-P`.

Suggest keeping `bug` and `high-impact`, and adding `diagnostic` — the compiler gives no
indication at all that the requested `-Fo` output was skipped.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
