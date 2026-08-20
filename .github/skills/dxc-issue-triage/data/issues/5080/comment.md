> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5080](https://github.com/microsoft/DirectXShaderCompiler/issues/5080).

This complete repro is fixed on current main
(`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`). The as-filed command exits 0 and
emits SPIR-V, including a `DebugTypeComposite`/`DebugGlobalVariable` pair for the
cbuffer. Dropping `-fvk-use-dx-layout` (as @s-perron suggested) also exits 0, matching
the workaround given in-thread.

The stable-release boundary is v1.8.2403.2 → v1.8.2405:

```text
v1.8.2403.2: exit 0xC0000005
Internal compiler error: access violation. Attempted to read from address ...

v1.8.2405: exit 0
; SPIR-V
```

The bug actually goes back further than that boundary alone suggests: v1.6.2112,
the oldest release able to parse `-fspv-debug=vulkan-with-source` at all, also
crashes once probed with a target-env value it accepts (its native rejection of
`vulkan1.3` had made it look clean). [Compiler Explorer](https://godbolt.org/z/9rshx68rz)
shows the same thing — DXC 1.6.2112 (`-fspv-target-env=vulkan1.0` substituted for the
unsupported `vulkan1.3`) terminates with `SIGSEGV`, and trunk compiles successfully.

The likely fix is commit
[`1e59ce9185`](https://github.com/microsoft/DirectXShaderCompiler/commit/1e59ce9185485535011e1f706d1ab3c1b349eac1)
(#6531), which removes exactly the assert this issue quotes and discusses DX-layout-driven
cbuffer lowering. This is not build-verified against its parent (a local toolchain
incompatibility blocked building that old a commit), so call it strong, not certain,
attribution rather than a settled one.

I suggest adding `crash`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
