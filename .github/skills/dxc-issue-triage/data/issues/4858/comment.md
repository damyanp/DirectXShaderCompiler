> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#4858](https://github.com/microsoft/DirectXShaderCompiler/issues/4858).

Still reproduces on `main` (1.9.0.5465, `89e2f98e2`), and in every stable release from v1.4.1907
through v1.9.2607 — this has never once compiled correctly. (The local build's `--version`
self-reports a fork-local `7665270b9`; its source has been verified identical to public
`89e2f98e2` outside this repo's triage-skill directory, which is the commit cited here.)

Repro (verbatim from the issue): https://godbolt.org/z/1h4fff5Ef — both `dxc_1_6_2112` and
`dxc_trunk` place the `CalculateLOD` op inside the block reached only by the branch's true arm,
even though the source computes it unconditionally before that branch:

```
br i1 %3, label %4, label %10
; ...
%4:
  %5 = call float @dx.op.calculateLOD.f32(...)
```

The second (`sin(uv)`) repro from the comments reproduces identically locally.

`-Od` (disable optimizations) suppresses it — the `CalculateLOD` call then stays in the
unconditional entry block, before the branch — which is what let us build a control confirming
the finding is about this specific code motion and not an artifact of the check.

**`check-in-clang` is still open, not answered.** The new Clang HLSL front end can't be compared
yet: it rejects this shader before reaching codegen, with `use of undeclared identifier
'InterlockedMin'` — a missing, unrelated front-end feature, not a verdict on the sinking.

No label changes suggested; `bug`, `correctness` and `check-in-clang` all still describe this
accurately.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
