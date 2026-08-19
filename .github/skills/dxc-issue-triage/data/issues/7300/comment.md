> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#7300](https://github.com/microsoft/DirectXShaderCompiler/issues/7300).

This complete repro is fixed on current main
(`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`). The as-filed command exits 0 and
emits SPIR-V; the local Debug binary self-reports fork-local merge `7665270b9`.

The stable-release boundary is v1.8.2505.1 → v1.9.2602:

```text
v1.8.2505.1: exit 0xC0000005
Internal compiler error: access violation. Attempted to read from address 0x0000000000000008

v1.9.2602: exit 0
; SPIR-V
```

[Compiler Explorer](https://godbolt.org/z/zbP5qasd3) likewise shows DXC
1.6.2112 terminating with `SIGSEGV` and trunk compiling successfully.

The fix is commit
[`61de7411f`](https://github.com/microsoft/DirectXShaderCompiler/commit/61de7411f952cb0c4b6c73091555dad6419180ee)
("lower spirv ray query type to opaque debug type"). Building Release `dxc` at
that commit and at its parent `b0245e32f`,
the parent fails the as-filed command with `0xE0000001`
(`Internal compiler error: LLVM Assert`) while the commit exits 0 and emits
SPIR-V. Dropping `-fspv-debug=vulkan-with-source` makes both builds exit 0, so
the failure is specific to ray-query debug-type lowering.

I suggest adding `crash` and removing `needs-triage`; this issue is already closed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
