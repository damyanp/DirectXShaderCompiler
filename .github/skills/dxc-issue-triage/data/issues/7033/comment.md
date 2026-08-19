> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#7033](https://github.com/microsoft/DirectXShaderCompiler/issues/7033).

This is fixed on current `main` (source-equivalent to
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`; the local Debug binary self-reports
`7665270b9`). The exact filed command now exits 0 and emits rich debug information for the
ray-query variable.

Stable-release testing places the fix in **v1.9.2602**: v1.8.2505.1 still access-violates,
while v1.9.2602 compiles successfully.
[Compiler Explorer](https://godbolt.org/z/EbMbKx9d9) shows dxc 1.6.2112 terminating with
SIGSEGV, while trunk succeeds.

Release `dxc` built at
[`61de7411f`](https://github.com/microsoft/DirectXShaderCompiler/commit/61de7411f952cb0c4b6c73091555dad6419180ee)
("lower spirv ray query type to opaque debug type") compiles the filed command
successfully, while the same build at its parent `b0245e32f` fails it with
`0xE0000001` (`Internal compiler error: LLVM Assert`). A control shader with no
`RayQuery` compiles on both, so the failure is specific to ray-query debug-type
lowering.

The existing `bug` and `spirv` labels remain accurate; no label change is suggested. The
issue can be closed as fixed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
