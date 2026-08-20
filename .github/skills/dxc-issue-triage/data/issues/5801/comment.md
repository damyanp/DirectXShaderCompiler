> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5801](https://github.com/microsoft/DirectXShaderCompiler/issues/5801).

Still reproduces on `main` (commit `89e2f98e2`, `1.9.0.5465`). The repro shader compiles
cleanly at `-T ps_6_7` with the offset `int2(12, -14)` embedded verbatim in the DXIL `Sample`
op, no diagnostic and no validation error:

```
%7 = call %dx.types.ResRet.f32 @dx.op.sample.f32(..., i32 12, i32 -14, ...)
```

The same source at `-T ps_6_6` still correctly rejects it:
`error: Offsets to texture access operations must be between -8 and 7.`

Bisecting the stable release history: every release that can target `ps_6_7` reproduces
(`v1.7.2207` through `v1.9.2607`, and current `dxc_trunk` on Compiler Explorer:
https://godbolt.org/z/WT19a1jbM). No earlier stable release can even select the profile, so this
has never worked rather than having regressed — it dates to SM 6.7's introduction.

@python3kgae's diagnosis is confirmed by reading the source: both guards that key off
`IsSM67Plus()` bypass their range check unconditionally, rather than only for the non-constant
("programmable") offsets SM 6.7 was meant to permit:

- `lib/HLSL/DxilLegalizeSampleOffsetPass.cpp:88-90` skips `FinalCheck` (the front-end/legalizer
  diagnostic) entirely once `IsSM67Plus()`.
- `lib/DxilValidation/DxilValidation.cpp:369-372` (`ValidateResourceOffset`'s `ValidateOffset`)
  returns before checking the `ConstantInt` case once `IsSM67Plus()`, even though the comment
  right above it ("6.7 Advanced Textures allow programmable offsets") only motivates skipping
  the non-constant branch below it.

Suggesting `sm6.7` in addition to the current labels, since both root-cause sites and the first
reproducing release are keyed on that shader model specifically.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
