> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5804](https://github.com/microsoft/DirectXShaderCompiler/issues/5804).

Checked against `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`): the suppression
this issue is about is still in place.

`cmake/modules/HandleLLVMOptions.cmake` still excludes `alignment` from both UBSAN
configurations:

```
append("-fsanitize=undefined -fno-sanitize=vptr,function,alignment -fno-sanitize-recover=all" ...)
append("-fsanitize=address,undefined -fno-sanitize=vptr,function,alignment -fno-sanitize-recover=all" ...)
```

That's exactly the pair added by #5803 and its follow-up #6431 ("Disable ubsan alignment
errors properly", which covered the `Address;Undefined` config #5803 missed).
`DxilPipelineStateValidation::CheckedReaderWriter` carries no narrower in-code suppression
either, so the blanket CMake exclusion described here is still the only thing standing between
this build and the alignment failures.

No shader repro applies — this is a build-configuration issue, not a compile-time one — so
"reproduces" here means the exclusion is still present, which it is.

Suggested labels: add `sanitizer` (fault detected by sanitizer run) and `build` (build/setup);
current `bug` and `tech-debt` are also accurate.

---
<sub>Triaged with AI assistance. The source excerpt above was read directly from the
repository at the cited commit; please flag anything that looks wrong.</sub>
