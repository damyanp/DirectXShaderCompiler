> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4888](https://github.com/microsoft/DirectXShaderCompiler/issues/4888).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`): compiling the
shader above with `-T ps_6_6 -E PSMain` still fails DXIL validation with the same class of
error, only the metadata slot number differs from the original report:

```
error: validation errors
error: All metadata must be used by dxil.!21 = !{i32 1}
Validation failed.
```

This has been true on every stable release checkable back to v1.6.2104 (2021-04-20, the oldest
release that even accepts `-T ps_6_6`) — every one of them fails the same way, so this has
never worked. [Compiler Explorer](https://godbolt.org/z/fhjbK7r4x) confirms the same error on
today's `dxc_trunk` and on CE's oldest DXC (1.6.2112), using a compute-shader restatement of the
same pattern (the pixel-shader repro's stage isn't relevant to the defect).

@tex3d's comment above is still the best statement of what's going on: `dxc` doesn't legalize a
static array of `ResourceDescriptorHeap`-backed resource *objects* indexed by
`NonUniformResourceIndex`, and per that comment the intended fix is a proper diagnostic naming
the unsupported pattern, not (yet) making the code legal. That diagnostic hasn't landed — the
compiler still surfaces the internal validator's generic complaint instead.

One thing has changed since 2023: @Keenuts' separate report that adding `-spirv` crashes with an
`isa<>` assertion no longer reproduces. It crashed on every stable release through v1.8.2403.2
(2024-03-29) and stopped crashing at v1.8.2405 (2024-05-24) onward, where it now fails with an
ordinary diagnosed error instead (currently `error: Cannot cast initializer type
'Texture2D<vector<float, 4> >' into variable type 'const Texture2D<vector<float, 4> >'`). Worth
noting so nobody re-files a redundant crash report against that specific symptom.

Suggested label: add `diagnostic`, alongside the existing `bug` — this is exactly the "add a
diagnostic for the unsupported pattern" work tex3d described.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag
anything that looks wrong.</sub>
