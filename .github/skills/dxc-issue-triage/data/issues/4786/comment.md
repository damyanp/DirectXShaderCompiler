> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4786](https://github.com/microsoft/DirectXShaderCompiler/issues/4786).

Still reproduces on `main` (measured against commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`).
This is a regression, not a standing bug — and it's been broken for over three years.

## What's still there

`projects/dxilconv/lib/DxbcConverter/DxbcConverter.cpp` still builds the `"dx.icb"` global with
`ArrayRef<float>((float *)Inst.m_CustomData.pData, Size)`, and
`lib/Bitcode/Writer/BitcodeWriter.cpp` still round-trips each element through
`getElementAsFloat()` (returned by value) and a `union{float;uint32_t;}` bit-cast — the exact
two-hop reinterpret this issue describes, unchanged.

## History

- PR #4790 (this issue's own fix) merged 2022-11-23, first shipped in `v1.7.2212`.
- PR #5253 reverted it on a release branch, and PR #5279 reverted it on `main` too (merged
  2023-06-08), "to be re-evaluated once AMD root-causes the issue and updates the drivers." No
  re-fix has landed since — every stable release from `v1.7.2308` (2023-08-14) through the
  current `v1.9.2607` still has the `float`-cast version, matching `main`.

So the fix window was `v1.7.2212`–`v1.7.2212.1` only (roughly Dec 2022–Aug 2023); everything
before and everything since is broken.

## Mechanism, confirmed on this machine

The x86-vs-x64 ABI difference this issue attributes the corruption to is directly
reproducible: a minimal function that reads `0xffbfffca`, bit-casts it to `float`, and returns
it by value produces `0xffffffca` when compiled for x86 (matching this issue's reported bit
flip exactly) and is unchanged when compiled for x64, with the same MSVC toolchain. Two extra
canonical signalling NaNs corrupt the same way on x86; two non-NaN controls are unaffected on
both architectures.

## What I couldn't test directly

`dxc.exe`'s own HLSL pipeline never calls `DxbcConverter` (it only converts legacy DXBC, via
the D3D12 runtime or a standalone `dxbc2dxil`), and this checkout doesn't build `dxilconv`, so
I couldn't run the reporter's DXBC through the converter end-to-end here. I also can't
independently confirm the separate WARP-side fix @jenatali mentioned (that's about WARP
accepting integer-typed `"dx.icb"`, a different claim from whether the corruption itself is
gone). @ben-clayton's 2023-09-06 reopen request is accurate and the issue is still open.

## Suggested labels

Keep `dxilconv`; add `bug` and `correctness` — this is a currently-reproducing data-corruption
defect, not just a subsystem tag.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
