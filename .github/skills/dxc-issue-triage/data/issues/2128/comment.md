> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2128](https://github.com/microsoft/DirectXShaderCompiler/issues/2128).

**Still reproduces on `main` (1.9.0.5433, `ab5400907`), and the original report's numbers hold to
within a few points.**

Compiled three pixel shaders with both compilers (`dxc -T ps_6_0 -E main -O3`,
`fxc /T ps_5_1 /E main /O3`) and deflated each object the way a `.zip` member is compressed.
Totals below are the two representative shaders; the third is a 32×-unrolled outlier that
flatters both compilers and is broken out under Method:

| | raw | zipped | ratio | reported in 2019 |
| --- | --- | --- | --- | --- |
| fxc | 5516 | 1825 | **0.33** | ~0.30 |
| dxc | 11152 | 6833 | 0.61 | — |
| dxc `-Qstrip_reflect` | 6992 | 5389 | **0.77** | 0.80–0.85 |

Zipped, dxc is **3.7× larger** for the same shaders — the reported ~3×. Measured alone, the DXIL
part deflates to `0.848` on the mid-size shader, inside the reported 0.80–0.85 band, and `0.900`
on the small one, just above it. fxc's `SHEX` chunk for that mid-size shader deflates to `0.271`.

The two containers encode code differently: DXIL is LLVM 3.7 bitcode (`docs/DXIL.rst:151`),
bit-packed VBR with abbreviations, where DXBC's `SHEX` is byte-aligned 32-bit tokens with heavy
repetition. Raw size is the smaller factor — on the two representative shaders dxc is 2.0× fxc
raw against 3.7× zipped, and on the 32×-unrolled shader dxc is *smaller* raw (35,364 vs 41,708
bytes). That is the shape @Division described in 2022.

**Half of @BitMD's 2019 comment was delivered.** Between v1.4.1907 and v1.5.2010 the reflection
metadata moved out of the module into a separate `STAT` part
(`DxilContainerAssembler.cpp:2085-2115`): the large shader's DXIL part went 68,700 → 32,844
bytes, and corpus size fell 39% raw / 34% zipped. Compressibility barely moved — the mid-size
shader's DXIL part deflates to `0.839` at v1.4.1907, `0.851` at v1.5.2010 and `0.848` today, and
across all 20 releases to v1.9.2607 the corpus ratio stays between 0.523 and 0.568.

**@Division — there is no PC equivalent of `__XBOX_DISABLE_SHADER_OBJECT_COMPRESSION`, and
nothing to disable.** DXC's compression helper `ZlibCompressAppend` has exactly two call sites,
and neither touches the shader object: the PDB writer
(`lib/DxilPdbInfo/DxilPdbInfoWriter.cpp:31`) and the `SRCI` embedded-source part
(`tools/clang/tools/dxcompiler/dxcshadersourceinfo.cpp:425`). `DxilContainerAssembler` writes
every part uncompressed; the density you measured is the bitcode encoding itself.

What is available is `-Qstrip_reflect` (also `-Qstrip_debug`, `-Qstrip_rootsignature`,
`-Qstrip_priv`, `-Qstrip_reflect_from_dxil`). Worth 13.5% raw and 8.7% zipped here — real, but
it does not close a 3.7× gap, which is what @BitMD said in 2019.

One caveat for re-measuring: `STAT` is a clone of the module, so whole-container deflate
deduplicates it against `DXIL`. The *ratio* improves while the zipped byte count gets worse —
the small shader zips to 2,393 bytes today versus 2,106 at v1.4.1907. For a fixed shader set,
compare zipped bytes, not ratios.

**Suggested labels:** add `fxc-disagrees` (a measured fxc/dxc difference) and `enhancement` (the
emitted code is correct; the ask is a different container encoding, not a bug fix). `dxil` and
`revisit-sooner` both still fit.

Three follow-up comments (2020, 2020, 2022) went unanswered. Whether to change the container
encoding is a product decision; a stated position, even "no change planned", would close out a
seven-year-old question.

<details>
<summary>Method — repeatable</summary>

Corpus is agent-constructed; the issue contains no code. Ratio is
`len(raw_deflate(bytes)) / len(bytes)` at level 9 (`wbits=-15`), i.e. a `.zip` member, and a
`.zip` compresses members independently. Containers are split using
`DxilContainerHeader`/`DxilPartHeader` from `include/dxc/DxilContainer/DxilContainer.h`; DXIL
reuses the DXBC container format, so the per-part figures are directly comparable. fxc is
10.0.26100.0 from the Windows SDK. The harness pins both ends of the scale on every run — 4 KiB
of sha256-chain bytes must measure ≥ 0.98 (got 1.001) and HLSL source text ≤ 0.50 (got 0.398).

The table above excludes a third, 32×-unrolled shader: 32 near-identical blocks flatter both
compilers (fxc reaches 0.059 on it) and it is not representative. Including it the zipped
multiple is 5.72×, not 3.7×.

</details>

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
