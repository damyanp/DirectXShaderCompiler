> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#3038](https://github.com/microsoft/DirectXShaderCompiler/issues/3038).

**Fixed:** the crash is present in **v1.5.2010 through v1.8.2502**, absent from **v1.8.2505**
onward, and does not reproduce on `main` (1.9.0.15422, eff900d5).

Because the body elides the arguments, the repro was reconstructed using @tex3d's observation
that both calls must share one `RayDesc`. It reproduces both reported signatures:

| build | result |
| --- | --- |
| v1.5.2010 | access violation (`0xC0000005`) - matches the original report |
| v1.8.2502 | `error: llvm::cast<X>() argument of incompatible type!` - matches @donguklim's 2022 report |
| `main` | compiles cleanly |

On v1.8.2502, the shared-`RayDesc` version crashes while the copied-`RayDesc` control
compiles. Both compile on current builds, so **the workaround is no longer needed**.

Before/after on Compiler Explorer: https://godbolt.org/z/6s1W5rfKx (`dxc_1_6_2112` crashes,
`dxc_trunk` is clean).

#7440 ("Refactor udt intrinsic arg copy to before SROA, flatten RayDesc") is in v1.8.2505 but
not v1.8.2502. It says RayDesc args "weren't copied in when necessary" and was filed against
#7434, whose repro also reuses one `RayDesc` across two intrinsics. Because the fix window
contains 162 commits, #7440 is a strong candidate, not a proven attribution.

Suggested action: close as fixed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag anything that looks wrong.</sub>
