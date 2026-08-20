> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5040](https://github.com/microsoft/DirectXShaderCompiler/issues/5040).

Still reproduces on `main` (Debug build at commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`):

```
$ dxc -T ps_6_0 -E main repro.hlsl
$ dxc -dumpbin out.dxil
  %2 = call %dx.types.ResRet.i32 @dx.op.bufferLoad.i32(i32 68, %dx.types.Handle %1, i32 undef, i32 undef)
```

Exit 0, no warning or error printed, and the default (non-`-Vd`) DXIL validator raises no
complaint either — the load index is emitted as `undef` exactly as originally reported.
Confirmed across every stable release from `v1.4.1907` (2019) through `v1.9.2607` (current
newest) plus [Compiler Explorer](https://godbolt.org/z/cP8cW1v3x) (older DXC + `dxc_trunk`; see
the banner comment for what to look for): this has never once been diagnosed in DXC's shipped
history.

`-Wuninitialized` still catches it today (as @llvm-beanz noted in 2023), and it is still not on
by default.

@damyanp's 2024-08-27 comment re-scoped this onto the validator ("the validator should have
caught it") — that gap is exactly what's confirmed still open here: the bundled validator
accepts an `undef` resource-load index silently on every measured build. Given that this is a
documented FXC/DXC divergence (FXC's `error X4575`, quoted in the original report, was not
independently re-verified here but is not in dispute), consider adding `fxc-disagrees` in
addition to the existing `bug`, `dxil`, `incorrect-code`, `validation` labels.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
