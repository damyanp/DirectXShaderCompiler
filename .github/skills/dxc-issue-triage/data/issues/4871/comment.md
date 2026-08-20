> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4871](https://github.com/microsoft/DirectXShaderCompiler/issues/4871).

Still reproduces on `main` (public commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
Debug build; `dxc --version` self-reports fork-local build id `7665270b9`).
`Func(--i)` — an empty `inout` function called with a pre-decremented argument —
still lowers to a subtraction of 2 rather than 1:

```
$ dxc -T ps_6_0 -E PSMain -Zi -Qembed_debug repro.hlsl
  %dec1 = add i32 %0, -2, !dbg !38 ; line:7 col:10
```

Controls isolate exactly where the extra subtraction comes from: neither an
`inout` call by itself, nor a pre-decrement by itself, produces it — only a
decrement/increment expression written *directly* as the `inout` argument
does. That matches the copy-in/copy-out semantics `inout` currently has at
the AST level.

History (20 stable releases, v1.4.1907–v1.9.2607, linear scan): clean at
v1.4.1907, reproduces at every release from **v1.5.2010** onward with no
reversion — a genuine, still-open regression, not something that was always
broken.

One update since the last comment here: the fix path named above (`#5377`
"out and inout should always be references") was closed `not planned` in
September 2024, and the draft PR it points to (`#5249`) is still open and
unmerged — so that rewrite never reached `main`, consistent with every probe
above still reproducing. Separately, though, Compiler Explorer's
`hlsl_clang_trunk` — the new Clang-based HLSL front end DXC's HLSL support is
migrating to — already gets this exact case right (`add i32 ..., -1`, used
once). Compiler Explorer link (compute-shader restatement, since the new
front end can't yet lower a pixel shader returning `SV_Target` as `uint`):
https://godbolt.org/z/4318d6hbY

Suggested labels: keep `bug`, add `correctness` (this is a silent
shader-correctness miscompile, not a diagnostic or crash issue).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
